"""
Builds a Superset-importable ZIP (YAML format) for the Pipeline Health dashboard.
Run: python3 build_import.py  -> produces pipeline_dashboard.zip
Then import via Superset UI: Settings > Import Dashboards
Or via API (run_import.py).
"""
import io, json, zipfile, uuid, yaml

DB_UUID   = "bq-pipeline-health-db"
DASH_UUID = str(uuid.uuid4())

SA_PATH   = "/app/gcp/sa.json"
PROJECT   = "pipeline-health-mon-2026"
SQLURI    = f"bigquery://{PROJECT}?credentials_path={SA_PATH}"

# ── Dataset definitions ───────────────────────────────────────────────────────
DATASETS = {
    "gld_dashboard_opportunities": {
        "uuid": str(uuid.uuid4()), "schema": "layer_gold",
        "columns": [
            {"column_name": "opportunity_id",           "type": "STRING",  "is_dttm": False},
            {"column_name": "stage",                    "type": "STRING",  "is_dttm": False},
            {"column_name": "region",                   "type": "STRING",  "is_dttm": False},
            {"column_name": "product",                  "type": "STRING",  "is_dttm": False},
            {"column_name": "agent",                    "type": "STRING",  "is_dttm": False},
            {"column_name": "value",                    "type": "FLOAT64", "is_dttm": False},
            {"column_name": "days_since_update",        "type": "INT64",   "is_dttm": False},
            {"column_name": "days_until_expected_close","type": "INT64",   "is_dttm": False},
            {"column_name": "is_stale",                 "type": "BOOL",    "is_dttm": False},
        ],
    },
    "gld_pipeline_by_stage": {
        "uuid": str(uuid.uuid4()), "schema": "layer_gold",
        "columns": [
            {"column_name": "stage",                "type": "STRING",  "is_dttm": False},
            {"column_name": "total_opportunities",  "type": "INT64",   "is_dttm": False},
            {"column_name": "total_value",          "type": "FLOAT64", "is_dttm": False},
            {"column_name": "weighted_value",       "type": "FLOAT64", "is_dttm": False},
            {"column_name": "stale_opportunities",  "type": "INT64",   "is_dttm": False},
        ],
    },
    "gld_conversion_by_agent": {
        "uuid": str(uuid.uuid4()), "schema": "layer_gold",
        "columns": [
            {"column_name": "agent",                  "type": "STRING",  "is_dttm": False},
            {"column_name": "total_opportunities",    "type": "INT64",   "is_dttm": False},
            {"column_name": "won_opportunities",      "type": "INT64",   "is_dttm": False},
            {"column_name": "lost_opportunities",     "type": "INT64",   "is_dttm": False},
            {"column_name": "win_rate_pct",           "type": "FLOAT64", "is_dttm": False},
            {"column_name": "total_pipeline_value",   "type": "FLOAT64", "is_dttm": False},
            {"column_name": "won_value",              "type": "FLOAT64", "is_dttm": False},
        ],
    },
    "gld_conversion_by_product": {
        "uuid": str(uuid.uuid4()), "schema": "layer_gold",
        "columns": [
            {"column_name": "product",                "type": "STRING",  "is_dttm": False},
            {"column_name": "total_opportunities",    "type": "INT64",   "is_dttm": False},
            {"column_name": "won_opportunities",      "type": "INT64",   "is_dttm": False},
            {"column_name": "win_rate_pct",           "type": "FLOAT64", "is_dttm": False},
            {"column_name": "total_pipeline_value",   "type": "FLOAT64", "is_dttm": False},
            {"column_name": "won_value",              "type": "FLOAT64", "is_dttm": False},
        ],
    },
    "gld_stale_opportunities": {
        "uuid": str(uuid.uuid4()), "schema": "layer_gold",
        "columns": [
            {"column_name": "opportunity_id",           "type": "STRING",  "is_dttm": False},
            {"column_name": "stage",                    "type": "STRING",  "is_dttm": False},
            {"column_name": "agent",                    "type": "STRING",  "is_dttm": False},
            {"column_name": "product",                  "type": "STRING",  "is_dttm": False},
            {"column_name": "region",                   "type": "STRING",  "is_dttm": False},
            {"column_name": "value",                    "type": "FLOAT64", "is_dttm": False},
            {"column_name": "days_since_update",        "type": "INT64",   "is_dttm": False},
            {"column_name": "days_until_expected_close","type": "INT64",   "is_dttm": False},
        ],
    },
}

# ── Chart definitions ─────────────────────────────────────────────────────────
def metric(col, agg="COUNT", label=None):
    return {"expressionType": "SIMPLE",
            "column": {"column_name": col},
            "aggregate": agg,
            "label": label or f"{agg}({col})",
            "hasCustomLabel": bool(label)}

def flt(col, op, val):
    return {"clause": "WHERE", "expressionType": "SIMPLE",
            "filterOptionName": f"f_{col}", "comparator": val,
            "operator": op, "subject": col}

OPP = "gld_dashboard_opportunities"
STG = "gld_pipeline_by_stage"
AGT = "gld_conversion_by_agent"
PRD = "gld_conversion_by_product"
STL = "gld_stale_opportunities"

CHARTS = [
    {
        "slice_name": "Pipeline Funnel", "uuid": str(uuid.uuid4()),
        "viz_type": "funnel", "dataset": OPP,
        "params": {"viz_type": "funnel", "groupby": ["stage"],
                   "metric": metric("opportunity_id", "COUNT", "Opportunities"),
                   "adhoc_filters": [flt("stage", "!=", "Lost")],
                   "row_limit": 5, "sort_by_metric": True,
                   "color_scheme": "supersetColors"},
    },
    {
        "slice_name": "Pipeline Value by Stage", "uuid": str(uuid.uuid4()),
        "viz_type": "echarts_bar", "dataset": STG,
        "params": {"viz_type": "echarts_bar", "x_axis": "stage",
                   "metrics": [metric("total_value", "SUM", "Pipeline Value ($)")],
                   "adhoc_filters": [], "row_limit": 10, "order_desc": True,
                   "show_value": True, "color_scheme": "supersetColors"},
    },
    {
        "slice_name": "Win Rate by Agent", "uuid": str(uuid.uuid4()),
        "viz_type": "echarts_bar", "dataset": AGT,
        "params": {"viz_type": "echarts_bar", "x_axis": "agent",
                   "metrics": [metric("win_rate_pct", "AVG", "Win Rate (%)")],
                   "adhoc_filters": [], "row_limit": 10, "order_desc": True,
                   "show_value": True, "orientation": "horizontal",
                   "color_scheme": "supersetColors"},
    },
    {
        "slice_name": "Win Rate by Product", "uuid": str(uuid.uuid4()),
        "viz_type": "echarts_bar", "dataset": PRD,
        "params": {"viz_type": "echarts_bar", "x_axis": "product",
                   "metrics": [metric("win_rate_pct", "AVG", "Win Rate (%)")],
                   "adhoc_filters": [], "row_limit": 10, "order_desc": True,
                   "show_value": True, "color_scheme": "supersetColors"},
    },
    {
        "slice_name": "Opportunities by Region", "uuid": str(uuid.uuid4()),
        "viz_type": "echarts_bar", "dataset": OPP,
        "params": {"viz_type": "echarts_bar", "x_axis": "region",
                   "metrics": [metric("opportunity_id", "COUNT", "Opportunities")],
                   "adhoc_filters": [], "row_limit": 10, "order_desc": True,
                   "show_value": True, "color_scheme": "supersetColors"},
    },
    {
        "slice_name": "Product Mix", "uuid": str(uuid.uuid4()),
        "viz_type": "pie", "dataset": OPP,
        "params": {"viz_type": "pie", "groupby": ["product"],
                   "metric": metric("opportunity_id", "COUNT", "Opportunities"),
                   "adhoc_filters": [], "row_limit": 10, "donut": True,
                   "label_type": "key_percent", "show_legend": True,
                   "color_scheme": "supersetColors"},
    },
    {
        "slice_name": "Stale Opportunities by Stage", "uuid": str(uuid.uuid4()),
        "viz_type": "echarts_bar", "dataset": STG,
        "params": {"viz_type": "echarts_bar", "x_axis": "stage",
                   "metrics": [metric("stale_opportunities", "SUM", "Stale")],
                   "adhoc_filters": [], "row_limit": 10, "order_desc": False,
                   "show_value": True, "color_scheme": "bnbColors"},
    },
    {
        "slice_name": "Stale Opportunities Detail", "uuid": str(uuid.uuid4()),
        "viz_type": "table", "dataset": STL,
        "params": {"viz_type": "table",
                   "all_columns": ["opportunity_id", "stage", "agent", "product",
                                   "region", "value", "days_since_update",
                                   "days_until_expected_close"],
                   "adhoc_filters": [], "row_limit": 100,
                   "order_desc": True, "page_length": 25, "include_search": True},
    },
]

# ── Dashboard position layout ─────────────────────────────────────────────────
def build_position(chart_uuids):
    def cb(uid, cuuid, w, h, name):
        return {uid: {"type": "CHART", "id": uid, "children": [],
                      "meta": {"uuid": cuuid, "chartId": cuuid,
                               "width": w, "height": h, "sliceName": name}}}
    def rb(uid, children):
        return {uid: {"type": "ROW", "id": uid, "children": children,
                      "meta": {"background": "BACKGROUND_TRANSPARENT"}}}

    cu = chart_uuids  # list of uuids in order matching CHARTS
    pos = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID",
                    "children": ["R1", "R2", "R3", "R4"]},
    }
    pos.update(rb("R1", ["C0", "C1"]))
    pos.update(cb("C0", cu[0], 7, 80, "Pipeline Funnel"))
    pos.update(cb("C1", cu[1], 5, 80, "Pipeline Value by Stage"))
    pos.update(rb("R2", ["C2", "C3"]))
    pos.update(cb("C2", cu[2], 6, 75, "Win Rate by Agent"))
    pos.update(cb("C3", cu[3], 6, 75, "Win Rate by Product"))
    pos.update(rb("R3", ["C4", "C5", "C6"]))
    pos.update(cb("C4", cu[4], 4, 70, "Opportunities by Region"))
    pos.update(cb("C5", cu[5], 4, 70, "Product Mix"))
    pos.update(cb("C6", cu[6], 4, 70, "Stale by Stage"))
    pos.update(rb("R4", ["C7"]))
    pos.update(cb("C7", cu[7], 12, 90, "Stale Opportunities Detail"))
    return pos


# ── Build YAML files ──────────────────────────────────────────────────────────
def build_zip(path="pipeline_dashboard.zip"):
    buf = io.BytesIO()
    chart_uuids = [c["uuid"] for c in CHARTS]

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        # database
        db_yaml = {
            "database_name": "BigQuery Pipeline Health",
            "sqlalchemy_uri": SQLURI,
            "uuid": DB_UUID,
            "allow_run_async": False,
            "expose_in_sqllab": True,
            "version": "1.0.0",
        }
        zf.writestr("databases/BigQuery_Pipeline_Health.yaml",
                    yaml.dump(db_yaml, allow_unicode=True))

        # datasets
        for tname, dmeta in DATASETS.items():
            ds_yaml = {
                "table_name": tname,
                "schema": dmeta["schema"],
                "database_uuid": DB_UUID,
                "uuid": dmeta["uuid"],
                "columns": dmeta["columns"],
                "metrics": [],
                "version": "1.0.0",
            }
            zf.writestr(f"datasets/BigQuery_Pipeline_Health/{tname}.yaml",
                        yaml.dump(ds_yaml, allow_unicode=True))

        # charts
        for chart in CHARTS:
            ds_uuid = DATASETS[chart["dataset"]]["uuid"]
            chart_yaml = {
                "slice_name": chart["slice_name"],
                "uuid": chart["uuid"],
                "viz_type": chart["viz_type"],
                "dataset_uuid": ds_uuid,
                "params": json.dumps(chart["params"]),
                "cache_timeout": None,
                "version": "1.0.0",
            }
            safe = chart["slice_name"].replace(" ", "_")
            zf.writestr(f"charts/{safe}.yaml",
                        yaml.dump(chart_yaml, allow_unicode=True))

        # dashboard
        position = build_position(chart_uuids)
        dash_yaml = {
            "dashboard_title": "Pipeline Health Monitor",
            "uuid": DASH_UUID,
            "slug": "pipeline-health",
            "published": True,
            "position": position,
            "metadata": {"color_scheme": "supersetColors",
                         "refresh_frequency": 0},
            "version": "1.0.0",
        }
        zf.writestr("dashboards/Pipeline_Health_Monitor.yaml",
                    yaml.dump(dash_yaml, allow_unicode=True))

    with open(path, "wb") as f:
        f.write(buf.getvalue())
    print(f"ZIP created: {path}  ({len(buf.getvalue())} bytes)")


if __name__ == "__main__":
    build_zip()
