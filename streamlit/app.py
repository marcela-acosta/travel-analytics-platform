import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import numpy as np
import pandas as pd
import streamlit as st

load_dotenv(Path(__file__).parent.parent / ".env")

USE_MOCK = os.environ.get("USE_MOCK", "true").lower() == "true"

STAGE_ORDER = ["Prospecting", "Qualified", "Proposal", "Negotiation", "Won", "Lost"]

_SUPERSET_EXTERNAL = os.environ.get("SUPERSET_EXTERNAL_URL", "http://34.70.112.25:8088")
_SUPERSET_INTERNAL = os.environ.get("SUPERSET_INTERNAL_URL", "http://localhost:8088")
_SUPERSET_USER = os.environ.get("SUPERSET_USER", "admin")
_SUPERSET_PASSWORD = os.environ.get("SUPERSET_PASSWORD", "admin")
_EMBED_UUID = "805478cb-4c36-4be2-aedf-c7ae9f21d2b1"
REGIONS = ["CDMX", "GDL", "MTY", "CUN", "TIJ"]
PRODUCTS = ["Flight", "Hotel", "Car Rental", "Package 2x", "Package 3x"]
AGENTS = [f"Agent {i:02d}" for i in range(1, 21)]

STAGE_COUNTS = {
    "Prospecting": 120,
    "Qualified": 85,
    "Proposal": 52,
    "Negotiation": 30,
    "Won": 18,
    "Lost": 22,
}
STAGE_WIN_PROB = {
    "Prospecting": 0.10,
    "Qualified": 0.25,
    "Proposal": 0.45,
    "Negotiation": 0.70,
    "Won": 1.00,
    "Lost": 0.00,
}
CLOSE_BUCKET_ORDER = ["Overdue", "This Week", "This Month", "Later"]
PRODUCT_COLORS = {
    "Flight": "#1a3d6e",
    "Hotel": "#1e5fa8",
    "Car Rental": "#4a9eed",
    "Package 2x": "#f4a261",
    "Package 3x": "#e76f51",
}
PRIMARY = "#1e5fa8"
STAGE_BLUES = ["#06b6d4", "#3b82f6", "#6366f1", "#8b5cf6", "#10b981", "#ef4444"]


def get_mock_data() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    for stage, count in STAGE_COUNTS.items():
        for i in range(count):
            days_since = int(rng.integers(0, 30))
            rows.append(
                {
                    "opportunity_id": f"OPP-{stage[:3].upper()}-{i:04d}",
                    "stage": stage,
                    "region": rng.choice(REGIONS),
                    "product": rng.choice(PRODUCTS),
                    "agent": rng.choice(AGENTS),
                    "value": round(float(rng.uniform(500, 15000)), 2),
                    "days_since_update": days_since,
                    "days_until_expected_close": int(rng.integers(-10, 60)),
                    "is_stale": days_since > 14,
                }
            )
    df = pd.DataFrame(rows)
    df["stage"] = pd.Categorical(df["stage"], categories=STAGE_ORDER, ordered=True)
    return df.sort_values("stage").reset_index(drop=True)


@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    if USE_MOCK:
        return get_mock_data()
    from google.cloud import bigquery

    project_id = os.environ.get("GCP_PROJECT", "pipeline-health-mon-2026")
    dataset = os.environ.get("GCP_DATASET", "layer_gold")
    client = bigquery.Client(project=project_id)
    rows = client.query(f"""
        SELECT opportunity_id, stage, region, product, agent, value,
               days_since_update, days_until_expected_close, is_stale
        FROM `{project_id}.{dataset}.gld_dashboard_opportunities`
    """).result()
    df = pd.DataFrame([dict(r) for r in rows])
    df["stage"] = pd.Categorical(df["stage"], categories=STAGE_ORDER, ordered=True)
    return df.sort_values("stage").reset_index(drop=True)


def get_mock_conversion_by_agent() -> pd.DataFrame:
    raw = get_mock_data()
    won = (
        raw[raw["stage"] == "Won"]
        .groupby("agent")
        .size()
        .reset_index(name="won_opportunities")
    )
    lost = (
        raw[raw["stage"] == "Lost"]
        .groupby("agent")
        .size()
        .reset_index(name="lost_opportunities")
    )
    won_val = (
        raw[raw["stage"] == "Won"]
        .groupby("agent")["value"]
        .sum()
        .reset_index(name="won_value")
    )
    agg = (
        raw.groupby("agent")
        .agg(
            total_opportunities=("value", "count"),
            total_pipeline_value=("value", "sum"),
        )
        .reset_index()
    )
    agg = (
        agg.merge(won, on="agent", how="left")
        .merge(lost, on="agent", how="left")
        .merge(won_val, on="agent", how="left")
    )
    agg = agg.fillna(
        {"won_opportunities": 0, "lost_opportunities": 0, "won_value": 0.0}
    )
    agg[["won_opportunities", "lost_opportunities"]] = agg[
        ["won_opportunities", "lost_opportunities"]
    ].astype(int)
    closed = agg["won_opportunities"] + agg["lost_opportunities"]
    agg["win_rate_pct"] = (
        (agg["won_opportunities"] / closed.replace(0, pd.NA) * 100).fillna(0.0).round(2)
    )
    return agg


def get_mock_conversion_by_product() -> pd.DataFrame:
    raw = get_mock_data()
    won = (
        raw[raw["stage"] == "Won"]
        .groupby("product")
        .size()
        .reset_index(name="won_opportunities")
    )
    lost = (
        raw[raw["stage"] == "Lost"]
        .groupby("product")
        .size()
        .reset_index(name="lost_opportunities")
    )
    won_val = (
        raw[raw["stage"] == "Won"]
        .groupby("product")["value"]
        .sum()
        .reset_index(name="won_value")
    )
    agg = (
        raw.groupby("product")
        .agg(
            total_opportunities=("value", "count"),
            total_pipeline_value=("value", "sum"),
        )
        .reset_index()
    )
    agg = (
        agg.merge(won, on="product", how="left")
        .merge(lost, on="product", how="left")
        .merge(won_val, on="product", how="left")
    )
    agg = agg.fillna(
        {"won_opportunities": 0, "lost_opportunities": 0, "won_value": 0.0}
    )
    agg[["won_opportunities", "lost_opportunities"]] = agg[
        ["won_opportunities", "lost_opportunities"]
    ].astype(int)
    closed = agg["won_opportunities"] + agg["lost_opportunities"]
    agg["win_rate_pct"] = (
        (agg["won_opportunities"] / closed.replace(0, pd.NA) * 100).fillna(0.0).round(2)
    )
    return agg


@st.cache_data(ttl=60)
def load_conversion_by_agent() -> pd.DataFrame:
    if USE_MOCK:
        return get_mock_conversion_by_agent()
    from google.cloud import bigquery

    project_id = os.environ.get("GCP_PROJECT", "pipeline-health-mon-2026")
    dataset = os.environ.get("GCP_DATASET", "layer_gold")
    client = bigquery.Client(project=project_id)
    rows = client.query(f"""
        SELECT agent, total_opportunities, won_opportunities, lost_opportunities,
               win_rate_pct, total_pipeline_value, won_value
        FROM `{project_id}.{dataset}.gld_conversion_by_agent`
    """).result()
    return pd.DataFrame([dict(r) for r in rows])


@st.cache_data(ttl=60)
def load_conversion_by_product() -> pd.DataFrame:
    if USE_MOCK:
        return get_mock_conversion_by_product()
    from google.cloud import bigquery

    project_id = os.environ.get("GCP_PROJECT", "pipeline-health-mon-2026")
    dataset = os.environ.get("GCP_DATASET", "layer_gold")
    client = bigquery.Client(project=project_id)
    rows = client.query(f"""
        SELECT product, total_opportunities, won_opportunities, lost_opportunities,
               win_rate_pct, total_pipeline_value, won_value
        FROM `{project_id}.{dataset}.gld_conversion_by_product`
    """).result()
    return pd.DataFrame([dict(r) for r in rows])


@st.cache_data(ttl=240)
def _get_guest_token() -> str:
    import requests as _req
    import re as _re

    s = _req.Session()
    page = s.get(f"{_SUPERSET_INTERNAL}/login/")
    csrf = _re.search(r'id="csrf_token"[^>]+value="([^"]+)"', page.text).group(1)
    s.post(
        f"{_SUPERSET_INTERNAL}/login/",
        data={
            "username": _SUPERSET_USER,
            "password": _SUPERSET_PASSWORD,
            "csrf_token": csrf,
        },
        allow_redirects=False,
    )
    api_csrf = s.get(f"{_SUPERSET_INTERNAL}/api/v1/security/csrf_token/").json()[
        "result"
    ]
    resp = s.post(
        f"{_SUPERSET_INTERNAL}/api/v1/security/guest_token/",
        headers={"X-CSRFToken": api_csrf, "Content-Type": "application/json"},
        json={
            "resources": [{"type": "dashboard", "id": _EMBED_UUID}],
            "rls": [],
            "user": {"username": "guest", "first_name": "Guest", "last_name": "User"},
        },
    )
    return resp.json()["token"]


def close_bucket(days: int) -> str:
    if days < 0:
        return "Overdue"
    if days <= 7:
        return "This Week"
    if days <= 30:
        return "This Month"
    return "Later"


# ── PDF report builder ────────────────────────────────────────────────────────
def _build_pdf(df_snap, stage_snap, agent_snap, product_snap) -> bytes:
    from fpdf import FPDF
    from datetime import datetime as _dtnow
    import plotly.graph_objects as go
    from io import BytesIO as _BIO

    # Palette
    NAVY = (15, 39, 68)
    BLUE = (30, 95, 168)
    LBLUE = (224, 235, 248)
    GRAY = (74, 107, 138)
    LGRAY = (245, 248, 252)
    WHITE = (255, 255, 255)
    GREEN = (22, 163, 74)
    ORANGE = (234, 88, 12)
    RED = (220, 38, 38)

    _now = _dtnow.now().strftime("%Y-%m-%d %H:%M")

    class _PDF(FPDF):
        def header(self):
            # Dark banner
            self.set_fill_color(*NAVY)
            self.rect(0, 0, 210, 24, "F")
            # Accent stripe
            self.set_fill_color(*BLUE)
            self.rect(0, 22, 210, 2, "F")
            # Title
            self.set_xy(12, 6)
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(*WHITE)
            self.cell(120, 7, "Travel Analytics Platform", ln=False)
            # Date (right-aligned)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(160, 190, 220)
            self.cell(66, 7, f"Generated: {_now}", align="R")
            self.set_y(27)

        def footer(self):
            self.set_y(-12)
            self.set_draw_color(*LBLUE)
            self.line(12, self.get_y(), 198, self.get_y())
            self.ln(1)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*GRAY)
            self.cell(93, 5, "Travel Analytics Platform - Confidential", align="L")
            self.cell(93, 5, f"Page {self.page_no()}", align="R")

    pdf = _PDF()
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    won = len(df_snap[df_snap["stage"] == "Won"])
    lost = len(df_snap[df_snap["stage"] == "Lost"])
    cl = won + lost
    wr = (won / cl * 100) if cl > 0 else 0
    stale = int(df_snap["is_stale"].sum())
    weighted = (
        df_snap["value"].astype(float)
        * df_snap["stage"].astype(str).map(STAGE_WIN_PROB).fillna(0)
    ).sum()

    # ── Section header ────────────────────────────────────────────────────
    def section(title):
        pdf.ln(4)
        y = pdf.get_y()
        pdf.set_fill_color(*BLUE)
        pdf.rect(12, y, 3, 7, "F")
        pdf.set_x(17)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 7, title, ln=True)
        pdf.set_draw_color(*LBLUE)
        pdf.line(12, pdf.get_y(), 198, pdf.get_y())
        pdf.ln(3)

    # ── KPI card (3-per-row) ──────────────────────────────────────────────
    def kpi_card(x, y, label, value, accent=BLUE):
        w, h = 59, 18
        pdf.set_fill_color(*LGRAY)
        pdf.rect(x, y, w, h, "F")
        pdf.set_fill_color(*accent)
        pdf.rect(x, y, 2.5, h, "F")
        pdf.set_xy(x + 4.5, y + 2.5)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*GRAY)
        pdf.cell(w - 5, 4.5, label)
        pdf.set_xy(x + 4.5, y + 8)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*NAVY)
        pdf.cell(w - 5, 7, value)

    # ── Data table with alternating rows + optional color column ──────────
    def table(headers, widths, rows, color_col=None, hi=(40, 20)):
        # Header
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", "B", 8)
        for h, w in zip(headers, widths):
            pdf.cell(w, 7, h, fill=True, align="C")
        pdf.ln()
        # Rows
        pdf.set_font("Helvetica", "", 8)
        for idx, row in enumerate(rows):
            bg = LGRAY if idx % 2 == 0 else WHITE
            pdf.set_fill_color(*bg)
            for ci, (val, w) in enumerate(zip(row, widths)):
                if color_col is not None and ci == color_col:
                    try:
                        n = float(str(val).replace("%", ""))
                        pdf.set_text_color(
                            *(GREEN if n >= hi[0] else ORANGE if n >= hi[1] else RED)
                        )
                    except Exception:
                        pdf.set_text_color(30, 30, 30)
                else:
                    pdf.set_text_color(30, 30, 30)
                align = "L" if ci == 0 else "R"
                pdf.cell(w, 6, str(val), fill=True, align=align)
            pdf.ln()
        pdf.set_draw_color(*LBLUE)
        pdf.line(12, pdf.get_y(), 198, pdf.get_y())
        pdf.ln(3)

    # ── Chart helpers ─────────────────────────────────────────────────────
    _PLOTLY_BASE = dict(
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        font=dict(family="Arial"),
    )

    def _chart_funnel() -> _BIO:
        order = ["Prospecting", "Qualified", "Proposal", "Negotiation", "Won"]
        colors = ["#06b6d4", "#3b82f6", "#6366f1", "#8b5cf6", "#10b981"]
        data = (
            stage_snap[stage_snap["stage"].isin(order)]
            .set_index("stage")
            .reindex(order[::-1])
        )
        vals = data["total_opportunities"].tolist()
        fig = go.Figure(
            go.Bar(
                y=list(data.index),
                x=vals,
                orientation="h",
                marker_color=colors[::-1],
                text=[f"  {int(v):,}" for v in vals],
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(color="white", size=12, family="Arial Black"),
                hovertemplate="%{y}: %{x:,}<extra></extra>",
            )
        )
        fig.update_layout(
            **_PLOTLY_BASE,
            margin=dict(l=10, r=20, t=10, b=30),
            width=1100,
            height=260,
            xaxis=dict(
                title="Opportunities",
                gridcolor="#e0ebf8",
                showline=False,
                tickfont=dict(size=10, color="#4a6b8a"),
                title_font=dict(size=10, color="#4a6b8a"),
            ),
            yaxis=dict(tickfont=dict(size=12, color="#0f2744"), showgrid=False),
        )
        buf = _BIO(fig.to_image(format="png", scale=1.5))
        buf.seek(0)
        return buf

    def _chart_closing() -> _BIO:
        df_c = df_snap.copy()
        df_c["close_bucket"] = df_c["days_until_expected_close"].apply(close_bucket)
        bucket_counts = (
            df_c[
                df_c["stage"].isin(
                    ["Prospecting", "Qualified", "Proposal", "Negotiation"]
                )
            ]
            .groupby("close_bucket")["value"]
            .count()
            .reindex(CLOSE_BUCKET_ORDER, fill_value=0)
        )
        bcolors = {
            "Overdue": "#c0392b",
            "This Week": "#e67e22",
            "This Month": "#1e5fa8",
            "Later": "#7ab8f5",
        }
        vals = bucket_counts.values.tolist()
        fig = go.Figure(
            go.Bar(
                x=list(bucket_counts.index),
                y=vals,
                marker_color=[bcolors[b] for b in bucket_counts.index],
                text=[str(int(v)) for v in vals],
                textposition="outside",
                textfont=dict(color="#0f2744", size=13, family="Arial Black"),
                hovertemplate="%{x}: %{y:,}<extra></extra>",
            )
        )
        fig.update_layout(
            **_PLOTLY_BASE,
            title=dict(
                text="Closing Timeline",
                font=dict(size=12, color="#0f2744", family="Arial Black"),
                x=0.5,
            ),
            margin=dict(l=10, r=10, t=44, b=10),
            width=570,
            height=300,
            xaxis=dict(
                tickfont=dict(size=12, color="#4a6b8a"), showgrid=False, showline=False
            ),
            yaxis=dict(
                gridcolor="#e0ebf8",
                showline=False,
                tickfont=dict(size=9, color="#4a6b8a"),
                range=[0, max(vals) * 1.2 + 1],
            ),
        )
        buf = _BIO(fig.to_image(format="png", scale=1.5))
        buf.seek(0)
        return buf

    def _chart_agent_winrate() -> _BIO:
        top = agent_snap.sort_values("win_rate_pct", ascending=False).head(10)
        vals = top["win_rate_pct"].values
        bar_colors = [
            "#16a34a" if v >= 40 else "#ea580c" if v >= 20 else "#dc2626" for v in vals
        ]
        max_val = float(max(vals)) if len(vals) > 0 else 100
        fig = go.Figure(
            go.Bar(
                y=top["agent"].values[::-1].tolist(),
                x=vals[::-1].tolist(),
                orientation="h",
                marker_color=bar_colors[::-1],
                text=[f"{v:.1f}%" for v in vals[::-1]],
                textposition="outside",
                textfont=dict(color="#0f2744", size=11, family="Arial Black"),
                hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
            )
        )
        fig.add_vline(
            x=40,
            line_dash="dash",
            line_color="#16a34a",
            line_width=1.5,
            opacity=0.65,
            annotation_text="40%",
            annotation_position="top right",
            annotation_font=dict(size=9, color="#16a34a"),
        )
        fig.add_vline(
            x=20,
            line_dash="dash",
            line_color="#ea580c",
            line_width=1.5,
            opacity=0.65,
            annotation_text="20%",
            annotation_position="top right",
            annotation_font=dict(size=9, color="#ea580c"),
        )
        fig.update_layout(
            **_PLOTLY_BASE,
            margin=dict(l=10, r=70, t=10, b=30),
            width=1100,
            height=320,
            xaxis=dict(
                title="Win Rate (%)",
                range=[0, max_val * 1.3 + 5],
                gridcolor="#e0ebf8",
                showline=False,
                tickfont=dict(size=9, color="#4a6b8a"),
                title_font=dict(size=10, color="#4a6b8a"),
            ),
            yaxis=dict(tickfont=dict(size=12, color="#0f2744"), showgrid=False),
        )
        buf = _BIO(fig.to_image(format="png", scale=1.5))
        buf.seek(0)
        return buf

    # ── KPI cards ─────────────────────────────────────────────────────────
    section("Key Metrics")
    kpis = [
        ("Total Opportunities", f"{len(df_snap):,}", BLUE),
        ("Pipeline Value", f"${df_snap['value'].sum():,.0f}", NAVY),
        ("Weighted Forecast", f"${weighted:,.0f}", BLUE),
        ("Win Rate", f"{wr:.1f}%", GREEN if wr >= 40 else ORANGE if wr >= 20 else RED),
        ("Won Deals", f"{won:,}", GREEN),
        ("Stale Opportunities", f"{stale:,}", RED if stale > 20 else ORANGE),
    ]
    y0 = pdf.get_y()
    for i, (lbl, val, color) in enumerate(kpis):
        kpi_card(12 + (i % 3) * 62, y0 + (i // 3) * 21, lbl, val, color)
    pdf.set_y(y0 + 2 * 21 + 4)

    # ── Funnel chart ──────────────────────────────────────────────────────
    section("Pipeline Funnel")
    _buf = _chart_funnel()
    pdf.image(_buf, x=12, w=186)
    pdf.ln(4)

    # ── Pipeline by stage ─────────────────────────────────────────────────
    section("Pipeline by Stage")
    table(
        ["Stage", "Opportunities", "Pipeline Value", "Weighted Forecast", "Stale"],
        [40, 32, 44, 46, 24],
        [
            [
                r["stage"],
                f"{r['total_opportunities']:,}",
                f"${r['total_value']:,.0f}",
                f"${r['weighted_value']:,.0f}",
                int(r["stale_opportunities"]),
            ]
            for _, r in stage_snap.iterrows()
        ],
    )

    # ── Closing timeline chart ─────────────────────────────────────────────
    section("Closing Timeline")
    _buf = _chart_closing()
    pdf.image(_buf, x=57, w=96)
    pdf.ln(4)

    # ── Conversion by agent ───────────────────────────────────────────────
    section("Conversion by Agent (Top 10 by Win Rate)")
    table(
        ["Agent", "Opportunities", "Won", "Win Rate", "Pipeline Value"],
        [46, 34, 22, 30, 54],
        [
            [
                r["agent"],
                r["total_opportunities"],
                r["won_opportunities"],
                f"{r['win_rate_pct']:.1f}%",
                f"${r['total_pipeline_value']:,.0f}",
            ]
            for _, r in agent_snap.sort_values("win_rate_pct", ascending=False)
            .head(10)
            .iterrows()
        ],
        color_col=3,
    )

    # ── Agent win rate chart ───────────────────────────────────────────────
    _buf = _chart_agent_winrate()
    pdf.image(_buf, x=12, w=186)
    pdf.ln(4)

    # ── Conversion by product ─────────────────────────────────────────────
    section("Conversion by Product")
    table(
        ["Product", "Opportunities", "Won", "Win Rate", "Pipeline Value"],
        [46, 34, 22, 30, 54],
        [
            [
                r["product"],
                r["total_opportunities"],
                r["won_opportunities"],
                f"{r['win_rate_pct']:.1f}%",
                f"${r['total_pipeline_value']:,.0f}",
            ]
            for _, r in product_snap.sort_values(
                "win_rate_pct", ascending=False
            ).iterrows()
        ],
        color_col=3,
    )

    return bytes(pdf.output())


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Travel Analytics Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
[data-baseweb="tag"] { background-color:#1e5fa8 !important; }
[data-baseweb="tag"] span { color:#ffffff !important; }
h2 { color:#0f2744 !important; border-bottom:2px solid #e0ebf8; padding-bottom:6px; }
hr { border-color:#e0ebf8; }
</style>
""",
    unsafe_allow_html=True,
)

raw = load_data()
df = raw.copy()

st.markdown("# Travel Analytics Platform")
st.caption(
    f"🟢 LIVE · updated: {datetime.now().strftime('%H:%M:%S')} UTC · auto-refreshes every 60 s"
)

if df.empty:
    st.error("No data matches the selected filters.")
    st.stop()

# Derived columns
df["win_prob"] = df["stage"].astype(str).map(STAGE_WIN_PROB).fillna(0).astype(float)
df["weighted_value"] = df["value"].astype(float) * df["win_prob"]
df["close_bucket"] = df["days_until_expected_close"].apply(close_bucket)
df["close_bucket"] = pd.Categorical(
    df["close_bucket"], categories=CLOSE_BUCKET_ORDER, ordered=True
)

stage_agg = (
    df.groupby("stage", observed=True)
    .agg(
        total_opportunities=("value", "count"),
        total_value=("value", "sum"),
        weighted_value=("weighted_value", "sum"),
        stale_opportunities=("is_stale", "sum"),
        avg_days_since_update=("days_since_update", "mean"),
    )
    .reset_index()
)
stage_agg["stage"] = stage_agg["stage"].astype(str)


if st.button("📧 Invite via email", key="email_top"):
    st.session_state["_open_email_dlg"] = True

st.divider()

# ── Travel Analytics Platform (Superset embedded) ────────────────────────────
_embed_hdr, _embed_btn = st.columns([9, 1])
_embed_hdr.markdown("### Explore the Full Interactive Dashboard")
_embed_btn.link_button(
    "↗ Full screen",
    f"{_SUPERSET_EXTERNAL}/superset/dashboard/travel-analytics/?expand_filters=false",
    use_container_width=True,
)

try:
    _token = _get_guest_token()
    _embed_src = f"{_SUPERSET_EXTERNAL}/embedded/{_EMBED_UUID}?expand_filters=false"
    _embed_html = f"""<!DOCTYPE html><html><head><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;overflow:hidden}}
iframe{{width:100%;height:820px;border:none;border-radius:8px;display:block}}
</style></head><body>
<iframe id="sps" src="{_embed_src}" frameborder="0" allowfullscreen></iframe>
<script>(function(){{
  var tk="{_token}",or="{_SUPERSET_EXTERNAL}",fr=document.getElementById('sps');
  var channel=new MessageChannel(),port1=channel.port1;
  function sendToken(){{
    port1.postMessage({{switchboardAction:'emit',method:'guestToken',args:{{guestToken:tk}}}});
  }}
  fr.addEventListener('load',function(){{
    fr.contentWindow.postMessage(
      {{type:'__embedded_comms__',handshake:'port transfer'}},
      or,[channel.port2]);
    port1.start();
    sendToken();
    setTimeout(sendToken,500);
    setTimeout(sendToken,1500);
    setTimeout(sendToken,3500);
  }});
}})();</script></body></html>"""
    import streamlit.components.v1 as _cmp_embed

    _cmp_embed.html(_embed_html, height=830, scrolling=False)
except Exception as _embed_err:
    st.warning(f"Embedded dashboard unavailable: {_embed_err}")
    st.link_button(
        "🔗 Open in Superset",
        f"{_SUPERSET_EXTERNAL}/superset/dashboard/travel-analytics/",
    )

st.divider()

# ── AI Chat + Email dialog ──────────────────────────────────────────────────
import sys as _sys  # noqa: E402
import os as _os  # noqa: E402

_sys.path.insert(0, _os.path.dirname(__file__))
from agent import chat as _agent_chat  # noqa: E402
import streamlit.components.v1 as _components  # noqa: E402

for _k, _v in [
    ("chat_history", []),
    ("chat_open", False),
    ("_open_email_dlg", False),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

_SUGGESTIONS = [
    "How many deals are overdue?",
    "Which agent has the best win rate?",
    "What is the weighted forecast by stage?",
]


@st.dialog("Send invitation via email")
def _email_dialog():
    _platform_url = os.environ.get("PLATFORM_URL", "http://34.70.112.25:8501/")
    st.markdown("Send an invitation to visit the Travel Analytics Platform.")
    _from_name = st.text_input("Your name", placeholder="Jane Smith")
    _to = st.text_input("Recipient email", placeholder="colleague@company.com")
    _subj = st.text_input(
        "Subject", value="Invitation to the Travel Analytics Platform"
    )
    _c1, _c2 = st.columns(2)
    if _c1.button("Send", type="primary", use_container_width=True):
        if not _to:
            st.error("Please enter a recipient email.")
        else:
            _sh = os.environ.get("SMTP_HOST", "")
            _su = os.environ.get("SMTP_USER", "")
            _sp = os.environ.get("SMTP_PASSWORD", "")
            if not (_sh and _su and _sp):
                st.warning(
                    "SMTP not configured. Add **SMTP_HOST**, **SMTP_USER** and **SMTP_PASSWORD** to your `.env` file to enable sending."
                )
            else:
                import smtplib
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText

                _inviter = _from_name.strip() or _su
                _html = f"""
<html><body style="font-family:Arial,sans-serif;color:#0f2744;">
  <p>{_inviter} is inviting you to visit the <strong>Travel Analytics Platform</strong>.</p>
  <p>
    <a href="{_platform_url}" style="color:#1e5fa8;font-weight:600;">
      Click here to access the platform
    </a>
  </p>
</body></html>"""
                _plain = (
                    f"{_inviter} is inviting you to visit the Travel Analytics Platform.\n\n"
                    f"Access it here: {_platform_url}"
                )
                try:
                    _mail = MIMEMultipart("alternative")
                    _mail["From"], _mail["To"], _mail["Subject"] = _su, _to, _subj
                    _mail.attach(MIMEText(_plain, "plain"))
                    _mail.attach(MIMEText(_html, "html"))
                    with smtplib.SMTP_SSL(_sh, 465) as _srv:
                        _srv.login(_su, _sp)
                        _srv.sendmail(_su, _to, _mail.as_string())
                    st.success(f"Invitation sent to {_to} ✓")
                except Exception as _e:
                    st.error(f"Could not send: {_e}")
    if _c2.button("Cancel", use_container_width=True):
        st.session_state["_open_email_dlg"] = False
        st.rerun()


@st.dialog("Chat with the data", width="large")
def _chat_dialog():
    _raw = st.session_state.get("_chat_raw_data")

    # Suggestion buttons
    _s1, _s2, _s3 = st.columns(3)
    _clicked = None
    if _s1.button(_SUGGESTIONS[0], key="dlg_s1", use_container_width=True):
        _clicked = _SUGGESTIONS[0]
    if _s2.button(_SUGGESTIONS[1], key="dlg_s2", use_container_width=True):
        _clicked = _SUGGESTIONS[1]
    if _s3.button(_SUGGESTIONS[2], key="dlg_s3", use_container_width=True):
        _clicked = _SUGGESTIONS[2]

    # Message history — always shown before the input
    st.caption("Powered by GPT-4o mini · Ask anything about the data")
    for _msg in st.session_state.chat_history:
        with st.chat_message("user" if _msg["role"] == "user" else "assistant"):
            st.markdown(_msg["content"])

    if st.session_state.chat_history:
        if st.button("Clear chat", type="secondary", key="dlg_clear"):
            st.session_state.chat_history = []
            st.session_state.chat_open = True
            st.rerun()

    # Input LAST → renders at the bottom of the dialog
    _typed = st.chat_input("Chat with the data...", key="dlg_chat_input")
    _prompt = _clicked or _typed

    if _prompt:
        st.session_state.chat_history.append({"role": "user", "content": _prompt})
        with st.spinner("Analyzing the data..."):
            try:
                _reply = _agent_chat(_prompt, st.session_state.chat_history[:-1], _raw)
            except Exception as _e:
                _reply = f"Error: {_e}"
        st.session_state.chat_history.append({"role": "assistant", "content": _reply})
        st.session_state.chat_open = True
        st.rerun()  # dialog closes → page reruns → chat_open=True → reopens with full history


# ── Trigger dialogs ───────────────────────────────────────────────────────────
st.session_state["_chat_raw_data"] = raw

if st.session_state.get("_open_email_dlg"):
    st.session_state["_open_email_dlg"] = False
    _email_dialog()

if st.button("💬 Chat with the data", key="chat_fab"):
    st.session_state.chat_open = True

if st.session_state.chat_open:
    _chat_dialog()

# ── JS: float FAB + reposition chat dialog to bottom-right ───────────────────
_components.html(
    """
<script>
(function() {
    var doc = window.parent.document;

    function floatFab() {
        var btns = doc.querySelectorAll("button");
        for (var i = 0; i < btns.length; i++) {
            var b = btns[i];
            if (b.textContent.trim().indexOf("Chat with the data") !== -1
                    && !b.closest("[data-baseweb='dialog']")) {
                var wrap = b.closest("[data-testid='stButton']") || b.parentElement;
                if (wrap && !wrap._floated) {
                    wrap._floated  = true;
                    wrap.style.position = "fixed";
                    wrap.style.bottom   = "24px";
                    wrap.style.right    = "24px";
                    wrap.style.zIndex   = "99998";
                    wrap.style.width    = "auto";
                    b.style.background   = "#1e5fa8";
                    b.style.color        = "white";
                    b.style.border       = "none";
                    b.style.borderRadius = "50px";
                    b.style.padding      = "13px 22px";
                    b.style.fontSize     = "15px";
                    b.style.fontWeight   = "600";
                    b.style.boxShadow    = "0 4px 20px rgba(30,95,168,0.45)";
                    b.style.cursor       = "pointer";
                    b.style.whiteSpace   = "nowrap";
                }
                return true;
            }
        }
        return false;
    }

    function styleDialog() {
        var dialog = doc.querySelector("[data-baseweb='dialog']");
        if (!dialog || dialog._chatStyled) return;
        dialog._chatStyled = true;

        var layer = dialog.closest("[data-baseweb='layer']");
        if (layer && layer.firstElementChild)
            layer.firstElementChild.style.background = "rgba(0,0,0,0.10)";

        var blockList = dialog.closest("[data-baseweb='block-list']");
        if (blockList) {
            blockList.style.alignItems     = "flex-end";
            blockList.style.justifyContent = "flex-end";
            blockList.style.paddingBottom  = "90px";
            blockList.style.paddingRight   = "24px";
        }

        dialog.style.maxWidth      = "440px";
        dialog.style.width         = "440px";
        dialog.style.maxHeight     = "72vh";
        dialog.style.borderRadius  = "16px";
        dialog.style.boxShadow     = "0 8px 40px rgba(0,0,0,0.22)";
        dialog.style.overflow      = "hidden";
        dialog.style.display       = "flex";
        dialog.style.flexDirection = "column";

        var content = dialog.querySelector("[data-testid='stDialogContent']");
        if (content) {
            content.style.display       = "flex";
            content.style.flexDirection = "column";
            content.style.flex          = "1";
            content.style.overflowY     = "auto";
            content.style.maxHeight     = "calc(72vh - 56px)";
        }
    }

    function styleReportBtns() {
        var all = doc.querySelectorAll("button");
        for (var i = 0; i < all.length; i++) {
            var b = all[i];
            var txt = b.textContent.trim();
            var isDl    = txt.indexOf("Download Report") !== -1;
            var isEmail = txt.indexOf("Send via Email")  !== -1;
            if ((isDl || isEmail) && !b._rptStyled) {
                b._rptStyled        = true;
                b.style.borderRadius = "8px";
                b.style.fontWeight   = "600";
                b.style.fontSize     = "14px";
                b.style.padding      = "9px 18px";
                b.style.transition   = "opacity 0.15s, box-shadow 0.15s";
                b.style.border       = "none";
                if (isDl) {
                    b.style.background = "#0f2744";
                    b.style.color      = "#ffffff";
                    b.style.boxShadow  = "0 2px 8px rgba(15,39,68,0.30)";
                } else {
                    b.style.background = "#ffffff";
                    b.style.color      = "#0f2744";
                    b.style.outline    = "2px solid #0f2744";
                    b.style.boxShadow  = "none";
                }
                b.addEventListener("mouseover", function() { this.style.opacity = "0.82"; });
                b.addEventListener("mouseout",  function() { this.style.opacity = "1"; });
            }
        }
    }

    new MutationObserver(function() { styleDialog(); styleReportBtns(); })
        .observe(doc.body, { childList: true, subtree: true });

    var n = 0;
    var t = setInterval(function() {
        floatFab(); styleDialog(); styleReportBtns();
        if (++n > 60) clearInterval(t);
    }, 200);
})();
</script>
""",
    height=0,
)
