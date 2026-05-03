"""
Creates the full Travel Analytics dashboard in Superset via API.
Run inside the superset container:
  docker exec superset-superset-1 python3 /app/superset/create_dashboard.py
"""
import json
import os
import requests

BASE = "http://localhost:8088"
_ADMIN_PASSWORD = os.environ["SUPERSET_ADMIN_PASSWORD"]

# ── Auth ──────────────────────────────────────────────────────────────────────
def get_session():
    s = requests.Session()
    tok = s.post(f"{BASE}/api/v1/security/login", json={
        "username": "admin", "password": _ADMIN_PASSWORD,
        "provider": "db", "refresh": True,
    }).json()["access_token"]
    csrf = s.get(f"{BASE}/api/v1/security/csrf_token/",
                 headers={"Authorization": f"Bearer {tok}"}).json()["result"]
    s.headers.update({
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "X-CSRFToken": csrf,
        "Referer": BASE,
    })
    return s


# ── Dataset IDs ───────────────────────────────────────────────────────────────
def get_dataset_ids(s):
    resp = s.get(f"{BASE}/api/v1/dataset/?q=(page_size:100)").json()
    return {d["table_name"]: d["id"] for d in resp.get("result", [])}


# ── Metric helpers ────────────────────────────────────────────────────────────
def count(col="*", label=None):
    return {
        "expressionType": "SIMPLE",
        "column": {"column_name": col} if col != "*" else None,
        "aggregate": "COUNT",
        "label": label or f"COUNT({col})",
        "hasCustomLabel": bool(label),
    }

def sum_col(col, label=None):
    return {
        "expressionType": "SIMPLE",
        "column": {"column_name": col},
        "aggregate": "SUM",
        "label": label or f"SUM({col})",
        "hasCustomLabel": bool(label),
    }

def avg_col(col, label=None):
    return {
        "expressionType": "SIMPLE",
        "column": {"column_name": col},
        "aggregate": "AVG",
        "label": label or f"AVG({col})",
        "hasCustomLabel": bool(label),
    }

def sql_metric(sql, label):
    return {"expressionType": "SQL", "sqlExpression": sql,
            "label": label, "hasCustomLabel": True}

def simple_filter(col, op, val):
    return {
        "clause": "WHERE", "expressionType": "SIMPLE",
        "filterOptionName": f"filter_{col}_{op}",
        "comparator": val, "operator": op, "subject": col,
    }


# ── Chart factory ─────────────────────────────────────────────────────────────
def create_chart(s, name, viz_type, ds_id, params):
    payload = {
        "slice_name": name,
        "viz_type": viz_type,
        "datasource_id": ds_id,
        "datasource_type": "table",
        "params": json.dumps(params),
        "owners": [],
    }
    r = s.post(f"{BASE}/api/v1/chart/", json=payload)
    if r.status_code in (200, 201):
        cid = r.json()["id"]
        print(f"  ✓ {name} (id={cid})")
        return cid
    print(f"  ✗ {name}: {r.status_code} {r.text[:120]}")
    return None


# ── Dashboard layout builder ──────────────────────────────────────────────────
def build_layout(chart_ids):
    """
    Grid layout: 12 columns, ~4 rows
    Row 0: funnel (8 cols) | pipeline_value (4 cols)
    Row 1: win_agent (6) | win_product (6)
    Row 2: region (4) | product_mix (4) | stale (4)
    Row 3: stale_table (12)
    """
    def row(row_id, children):
        return {row_id: {"type": "ROW", "id": row_id, "children": children,
                         "meta": {"background": "BACKGROUND_TRANSPARENT"}}}

    def chart(cid, width, height=300):
        uid = f"CHART-{cid}"
        return {uid: {"type": "CHART", "id": uid,
                      "children": [],
                      "meta": {"chartId": cid, "width": width,
                               "height": height, "sliceName": ""}}}

    ids = chart_ids
    layout = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID",
                    "children": ["ROW-0", "ROW-1", "ROW-2", "ROW-3"]},
    }

    rows_def = [
        ("ROW-0", [
            (ids.get("funnel"), 8, 320),
            (ids.get("pipeline_value"), 4, 320),
        ]),
        ("ROW-1", [
            (ids.get("win_agent"), 6, 300),
            (ids.get("win_product"), 6, 300),
        ]),
        ("ROW-2", [
            (ids.get("region_opps"), 4, 280),
            (ids.get("product_mix"), 4, 280),
            (ids.get("stale_by_stage"), 4, 280),
        ]),
        ("ROW-3", [
            (ids.get("stale_table"), 12, 360),
        ]),
    ]

    for row_id, charts in rows_def:
        children = []
        row_blocks = {}
        for entry in charts:
            if entry[0] is None:
                continue
            cid, w = entry[0], entry[1]
            h = entry[2] if len(entry) > 2 else 300
            uid = f"CHART-{cid}"
            children.append(uid)
            row_blocks[uid] = {
                "type": "CHART", "id": uid, "children": [],
                "meta": {"chartId": cid, "width": w,
                         "height": h, "sliceName": ""},
            }
        layout[row_id] = {
            "type": "ROW", "id": row_id, "children": children,
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        layout.update(row_blocks)

    return layout


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    s = get_session()
    ds = get_dataset_ids(s)
    print("Datasets found:", list(ds.keys()))

    opp  = ds.get("gld_dashboard_opportunities")
    stg  = ds.get("gld_pipeline_by_stage")
    agt  = ds.get("gld_conversion_by_agent")
    prd  = ds.get("gld_conversion_by_product")
    stale_ds = ds.get("gld_stale_opportunities")

    chart_ids = {}
    print("\nCreating charts...")

    # 1. Pipeline Funnel
    chart_ids["funnel"] = create_chart(s, "Pipeline Funnel", "funnel", opp, {
        "viz_type": "funnel",
        "groupby": ["stage"],
        "metric": count("opportunity_id", "Opportunities"),
        "adhoc_filters": [simple_filter("stage", "!=", "Lost")],
        "row_limit": 5,
        "sort_by_metric": True,
        "percent_metrics": [],
        "color_scheme": "supersetColors",
    })

    # 2. Pipeline Value by Stage (bar)
    chart_ids["pipeline_value"] = create_chart(s, "Pipeline Value by Stage", "echarts_bar", stg, {
        "viz_type": "echarts_bar",
        "groupby": ["stage"],
        "metrics": [sum_col("total_value", "Pipeline Value ($)")],
        "adhoc_filters": [],
        "row_limit": 10,
        "order_desc": True,
        "color_scheme": "supersetColors",
        "x_axis": "stage",
        "x_axis_title": "Stage",
        "y_axis_title": "Pipeline Value ($)",
        "show_value": True,
        "stack": False,
    })

    # 3. Win Rate by Agent (bar horizontal)
    chart_ids["win_agent"] = create_chart(s, "Win Rate by Agent", "echarts_bar", agt, {
        "viz_type": "echarts_bar",
        "groupby": ["agent"],
        "metrics": [{"expressionType": "SIMPLE",
                     "column": {"column_name": "win_rate_pct"},
                     "aggregate": "AVG",
                     "label": "Win Rate (%)",
                     "hasCustomLabel": True}],
        "adhoc_filters": [],
        "row_limit": 10,
        "order_desc": True,
        "color_scheme": "supersetColors",
        "x_axis": "agent",
        "x_axis_title": "Agent",
        "y_axis_title": "Win Rate (%)",
        "show_value": True,
        "orientation": "horizontal",
    })

    # 4. Win Rate by Product
    chart_ids["win_product"] = create_chart(s, "Win Rate by Product", "echarts_bar", prd, {
        "viz_type": "echarts_bar",
        "groupby": ["product"],
        "metrics": [{"expressionType": "SIMPLE",
                     "column": {"column_name": "win_rate_pct"},
                     "aggregate": "AVG",
                     "label": "Win Rate (%)",
                     "hasCustomLabel": True}],
        "adhoc_filters": [],
        "row_limit": 10,
        "order_desc": True,
        "color_scheme": "supersetColors",
        "x_axis": "product",
        "x_axis_title": "Product",
        "y_axis_title": "Win Rate (%)",
        "show_value": True,
    })

    # 5. Opportunities by Region (bar)
    chart_ids["region_opps"] = create_chart(s, "Opportunities by Region", "echarts_bar", opp, {
        "viz_type": "echarts_bar",
        "groupby": ["region"],
        "metrics": [count("opportunity_id", "Opportunities")],
        "adhoc_filters": [],
        "row_limit": 10,
        "order_desc": True,
        "color_scheme": "supersetColors",
        "x_axis": "region",
        "x_axis_title": "Region",
        "y_axis_title": "Opportunities",
        "show_value": True,
    })

    # 6. Product Mix (pie)
    chart_ids["product_mix"] = create_chart(s, "Product Mix", "pie", opp, {
        "viz_type": "pie",
        "groupby": ["product"],
        "metric": count("opportunity_id", "Opportunities"),
        "adhoc_filters": [],
        "row_limit": 10,
        "color_scheme": "supersetColors",
        "show_labels": True,
        "show_legend": True,
        "label_type": "key_percent",
        "outerRadius": 70,
        "innerRadius": 30,
        "donut": True,
    })

    # 7. Stale Opportunities by Stage (bar)
    chart_ids["stale_by_stage"] = create_chart(s, "Stale Opportunities by Stage", "echarts_bar", stg, {
        "viz_type": "echarts_bar",
        "groupby": ["stage"],
        "metrics": [sum_col("stale_opportunities", "Stale Opps")],
        "adhoc_filters": [],
        "row_limit": 10,
        "order_desc": False,
        "color_scheme": "bnbColors",
        "x_axis": "stage",
        "x_axis_title": "Stage",
        "y_axis_title": "Stale Opportunities",
        "show_value": True,
    })

    # 8. Stale Detail Table
    chart_ids["stale_table"] = create_chart(s, "Stale Opportunities Detail", "table", stale_ds, {
        "viz_type": "table",
        "groupby": [],
        "metrics": [],
        "all_columns": ["opportunity_id", "stage", "agent", "product",
                        "region", "value", "days_since_update",
                        "days_until_expected_close"],
        "adhoc_filters": [],
        "row_limit": 100,
        "order_desc": True,
        "table_timestamp_format": "%Y-%m-%d",
        "page_length": 25,
        "include_search": True,
        "align_pn": True,
        "color_pn": True,
    })

    # ── Create dashboard ──────────────────────────────────────────────────────
    print("\nCreating dashboard...")
    layout = build_layout(chart_ids)
    dash_payload = {
        "dashboard_title": "Travel Analytics Platform",
        "slug": "pipeline-health",
        "published": True,
        "owners": [],
        "position_json": json.dumps(layout),
    }
    r = s.post(f"{BASE}/api/v1/dashboard/", json=dash_payload)
    if r.status_code in (200, 201):
        dash_id = r.json()["id"]
        print(f"  ✓ Dashboard created (id={dash_id})")
    else:
        print(f"  ✗ Dashboard error: {r.status_code} {r.text[:200]}")
        return

    # ── Link charts to dashboard ──────────────────────────────────────────────
    valid_ids = [v for v in chart_ids.values() if v is not None]
    r2 = s.put(f"{BASE}/api/v1/dashboard/{dash_id}",
               json={"json_metadata": json.dumps({"chart_configuration": {}}),
                     "owners": []})

    # Add charts
    for cid in valid_ids:
        s.post(f"{BASE}/api/v1/chart/{cid}/favorites/")

    print(f"\nDone! Open: {BASE}/superset/dashboard/pipeline-health/")
    print(f"     Login: admin / (see SUPERSET_ADMIN_PASSWORD in .env)")


if __name__ == "__main__":
    main()
