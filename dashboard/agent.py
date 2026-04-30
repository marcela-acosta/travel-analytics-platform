import os
import re
import json
import sqlite3
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

PROJECT_ID = os.environ.get("GCP_PROJECT", "pipeline-health-mon-2026")
USE_MOCK = os.environ.get("USE_MOCK", "true").lower() == "true"
_DBT_PATH = Path(__file__).parent.parent / "dbt" / "dbt_health_monitor"


def _get_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set — add it to your .env file")
    return OpenAI(api_key=api_key)


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
        "MOCK mode: only gld_dashboard_opportunities is available (no other tables). "
        "Always query gld_dashboard_opportunities."
        if USE_MOCK
        else "Connected to live BigQuery. All gold tables are available."
    )
    return f"""You are a sales pipeline analyst for a travel company. {mode_note}

Available dbt gold table columns in gld_dashboard_opportunities:
opportunity_id, stage, region, product, agent, value,
days_since_update, days_until_expected_close, is_stale

Key definitions (use these exact SQL conditions):
- OVERDUE deal: days_until_expected_close < 0
- STALE deal: days_since_update > 14  (or is_stale = 1)
- Closing this week: days_until_expected_close BETWEEN 0 AND 7
- Closing this month: days_until_expected_close BETWEEN 0 AND 30

Pipeline stages: Prospecting, Qualified, Proposal, Negotiation, Won, Lost
Regions: CDMX, GDL, MTY, CUN, TIJ
Products: Flight, Hotel, Car Rental, Package 2x, Package 3x
Win probabilities: Prospecting 10%, Qualified 25%, Proposal 45%, Negotiation 70%, Won 100%

ALWAYS use run_query to answer data questions. Use table name:
  `{PROJECT_ID}.gold.gld_dashboard_opportunities`

When computing rates or percentages in SQL, always use CAST(numerator AS FLOAT) to avoid integer division.
Be concise and business-friendly in your answers."""


_TOOL = {
    "type": "function",
    "function": {
        "name": "run_query",
        "description": "Execute a SQL query and return the results as JSON.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "A BigQuery SQL query using fully-qualified table names.",
                }
            },
            "required": ["sql"],
        },
    },
}


def _execute(sql: str, mock_df) -> str:
    if USE_MOCK and mock_df is not None:
        clean = re.sub(r'`[^`]*\.(gld_\w+)`', r'\1', sql)
        clean = re.sub(r'`', '', clean)
        # Normalize booleans for SQLite
        clean = re.sub(r'\bTRUE\b', '1', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\bFALSE\b', '0', clean, flags=re.IGNORECASE)
        conn = sqlite3.connect(":memory:")
        try:
            df = mock_df.copy()
            df["stage"] = df["stage"].astype(str)
            df.to_sql("gld_dashboard_opportunities", conn, index=False, if_exists="replace")
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
    """Send a message to the OpenAI agent and return its reply.

    history: list of {"role": "user"|"assistant", "content": "..."}.
    """
    client = _get_client()

    messages = [{"role": "system", "content": _system_prompt()}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    for i in range(6):
        # Force tool use on the first call so the model always queries data
        tool_choice = "required" if i == 0 else "auto"
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=[_TOOL],
            tool_choice=tool_choice,
            temperature=0.1,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content or "No response generated."

        messages.append(msg)
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = _execute(args["sql"], mock_df)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return msg.content or "No response generated."
