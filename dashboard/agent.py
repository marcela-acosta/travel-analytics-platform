import os
import re
import json
import sqlite3
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).parent.parent / ".env")

PROJECT_ID = os.environ.get("GCP_PROJECT", "pipeline-health-mon-2026")
USE_MOCK = os.environ.get("USE_MOCK", "true").lower() == "true"
_DBT_PATH = Path(__file__).parent.parent / "dbt" / "dbt_health_monitor"


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set — add it to your .env file")
    return genai.Client(api_key=api_key)


def _dbt_context() -> str:
    schema_file = _DBT_PATH / "models" / "gold" / "gold_schema.yml"
    if not schema_file.exists():
        return "(schema file not found)"
    data = yaml.safe_load(schema_file.read_text())
    lines = []
    for m in data.get("models", []):
        cols = ", ".join(c["name"] for c in m.get("columns", []))
        col_str = f" - columns: {cols}" if cols else ""
        lines.append(f"- `{PROJECT_ID}.gold.{m['name']}`: {m.get('description', '')}{col_str}")
    return "\n".join(lines)


def _system_prompt() -> str:
    mode_note = (
        "Running in MOCK mode with sample data - only gld_dashboard_opportunities is available."
        if USE_MOCK
        else "Connected to live BigQuery."
    )
    return f"""You are a sales pipeline analyst for a travel company. {mode_note}

Available dbt gold tables in BigQuery:
{_dbt_context()}

Business context:
- Pipeline stages (in order): Prospecting -> Qualified -> Proposal -> Negotiation -> Won / Lost
- Regions: CDMX, GDL, MTY, CUN, TIJ
- Products: Flight, Hotel, Car Rental, Package 2x, Package 3x
- Win probabilities by stage: Prospecting 10%, Qualified 25%, Proposal 45%, Negotiation 70%, Won 100%
- Stale opportunity = not updated in more than 14 days
- Weighted Forecast = pipeline value x win probability

When answering questions about the data, use the run_query tool with fully-qualified table names:
  `{PROJECT_ID}.gold.<model_name>`

Keep SQL simple and efficient. Summarize results in clear, business-friendly language. Be concise."""


_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="run_query",
            description="Execute a SQL query against BigQuery and return the results as JSON.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "sql": types.Schema(
                        type=types.Type.STRING,
                        description="A valid BigQuery SQL query using fully-qualified table names.",
                    )
                },
                required=["sql"],
            ),
        )
    ]
)


def _execute(sql: str, mock_df) -> str:
    if USE_MOCK and mock_df is not None:
        clean = re.sub(r'`[^`]*\.(gld_\w+)`', r'\1', sql)
        clean = re.sub(r'`', '', clean)
        conn = sqlite3.connect(":memory:")
        try:
            mock_df.to_sql("gld_dashboard_opportunities", conn, index=False, if_exists="replace")
            result = pd.read_sql(clean, conn)
            return result.to_json(orient="records", indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "attempted_sql": clean})
        finally:
            conn.close()
    try:
        from google.cloud import bigquery
        result = bigquery.Client(project=PROJECT_ID).query(sql).to_dataframe()
        return result.to_json(orient="records", indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def chat(user_message: str, history: list, mock_df=None) -> str:
    """Send a message to the Gemini agent and return its reply.

    history: list of {"role": "user"|"assistant", "content": "..."}.
    """
    client = _get_client()

    contents = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(msg["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(user_message)]))

    config = types.GenerateContentConfig(
        system_instruction=_system_prompt(),
        tools=[_TOOL],
        temperature=0.1,
    )

    for _ in range(5):
        response = client.models.generate_content(
            model="gemini-2.0-flash", contents=contents, config=config
        )
        candidate = response.candidates[0]
        fn_call = next(
            (p.function_call for p in candidate.content.parts if p.function_call), None
        )
        if fn_call is None:
            break

        query_result = _execute(fn_call.args["sql"], mock_df)
        contents.append(candidate.content)
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_function_response(
                        name=fn_call.name, response={"result": query_result}
                    )
                ],
            )
        )

    text_parts = [p.text for p in response.candidates[0].content.parts if p.text]
    return "\n".join(text_parts) if text_parts else "No response generated."
