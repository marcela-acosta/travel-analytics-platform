import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

load_dotenv(Path(__file__).parent.parent / ".env")

USE_MOCK = os.environ.get("USE_MOCK", "true").lower() == "true"

STAGE_ORDER = ["Prospecting", "Qualified", "Proposal", "Negotiation", "Won", "Lost"]
REGIONS = ["CDMX", "GDL", "MTY", "CUN", "TIJ"]
PRODUCTS = ["Flight", "Hotel", "Car Rental", "Package 2x", "Package 3x"]
AGENTS = [f"Agent {i:02d}" for i in range(1, 21)]

STAGE_COUNTS = {
    "Prospecting": 120, "Qualified": 85, "Proposal": 52,
    "Negotiation": 30, "Won": 18, "Lost": 22,
}
STAGE_WIN_PROB = {
    "Prospecting": 0.10, "Qualified": 0.25, "Proposal": 0.45,
    "Negotiation": 0.70, "Won": 1.00, "Lost": 0.00,
}
CLOSE_BUCKET_ORDER = ["Overdue", "This Week", "This Month", "Later"]
PRODUCT_COLORS = {
    "Flight": "#1a3d6e", "Hotel": "#1e5fa8", "Car Rental": "#4a9eed",
    "Package 2x": "#f4a261", "Package 3x": "#e76f51",
}
PRIMARY   = "#1e5fa8"
STAGE_BLUES = ["#06b6d4", "#3b82f6", "#6366f1", "#8b5cf6", "#10b981", "#ef4444"]


def get_mock_data() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    for stage, count in STAGE_COUNTS.items():
        for i in range(count):
            days_since = int(rng.integers(0, 30))
            rows.append({
                "opportunity_id": f"OPP-{stage[:3].upper()}-{i:04d}",
                "stage": stage, "region": rng.choice(REGIONS),
                "product": rng.choice(PRODUCTS), "agent": rng.choice(AGENTS),
                "value": round(float(rng.uniform(500, 15000)), 2),
                "days_since_update": days_since,
                "days_until_expected_close": int(rng.integers(-10, 60)),
                "is_stale": days_since > 14,
            })
    df = pd.DataFrame(rows)
    df["stage"] = pd.Categorical(df["stage"], categories=STAGE_ORDER, ordered=True)
    return df.sort_values("stage").reset_index(drop=True)


@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    if USE_MOCK:
        return get_mock_data()
    from google.cloud import bigquery
    project_id = os.environ.get("GCP_PROJECT", "pipeline-health-mon-2026")
    client = bigquery.Client()
    df = client.query(f"""
        SELECT opportunity_id, stage, region, product, agent, value,
               days_since_update, days_until_expected_close, is_stale
        FROM `{project_id}.gold.gld_dashboard_opportunities`
    """).to_dataframe()
    df["stage"] = pd.Categorical(df["stage"], categories=STAGE_ORDER, ordered=True)
    return df.sort_values("stage").reset_index(drop=True)


def get_mock_conversion_by_agent() -> pd.DataFrame:
    raw = get_mock_data()
    won     = raw[raw["stage"] == "Won"].groupby("agent").size().reset_index(name="won_opportunities")
    lost    = raw[raw["stage"] == "Lost"].groupby("agent").size().reset_index(name="lost_opportunities")
    won_val = raw[raw["stage"] == "Won"].groupby("agent")["value"].sum().reset_index(name="won_value")
    agg = (
        raw.groupby("agent")
        .agg(total_opportunities=("value", "count"), total_pipeline_value=("value", "sum"))
        .reset_index()
    )
    agg = (agg.merge(won, on="agent", how="left")
               .merge(lost, on="agent", how="left")
               .merge(won_val, on="agent", how="left"))
    agg = agg.fillna({"won_opportunities": 0, "lost_opportunities": 0, "won_value": 0.0})
    agg[["won_opportunities", "lost_opportunities"]] = agg[["won_opportunities", "lost_opportunities"]].astype(int)
    closed = agg["won_opportunities"] + agg["lost_opportunities"]
    agg["win_rate_pct"] = (agg["won_opportunities"] / closed.replace(0, pd.NA) * 100).fillna(0.0).round(2)
    return agg


def get_mock_conversion_by_product() -> pd.DataFrame:
    raw = get_mock_data()
    won     = raw[raw["stage"] == "Won"].groupby("product").size().reset_index(name="won_opportunities")
    lost    = raw[raw["stage"] == "Lost"].groupby("product").size().reset_index(name="lost_opportunities")
    won_val = raw[raw["stage"] == "Won"].groupby("product")["value"].sum().reset_index(name="won_value")
    agg = (
        raw.groupby("product")
        .agg(total_opportunities=("value", "count"), total_pipeline_value=("value", "sum"))
        .reset_index()
    )
    agg = (agg.merge(won, on="product", how="left")
               .merge(lost, on="product", how="left")
               .merge(won_val, on="product", how="left"))
    agg = agg.fillna({"won_opportunities": 0, "lost_opportunities": 0, "won_value": 0.0})
    agg[["won_opportunities", "lost_opportunities"]] = agg[["won_opportunities", "lost_opportunities"]].astype(int)
    closed = agg["won_opportunities"] + agg["lost_opportunities"]
    agg["win_rate_pct"] = (agg["won_opportunities"] / closed.replace(0, pd.NA) * 100).fillna(0.0).round(2)
    return agg


@st.cache_data(ttl=60)
def load_conversion_by_agent() -> pd.DataFrame:
    if USE_MOCK:
        return get_mock_conversion_by_agent()
    from google.cloud import bigquery
    project_id = os.environ.get("GCP_PROJECT", "pipeline-health-mon-2026")
    client = bigquery.Client()
    return client.query(f"""
        SELECT agent, total_opportunities, won_opportunities, lost_opportunities,
               win_rate_pct, total_pipeline_value, won_value
        FROM `{project_id}.gold.gld_conversion_by_agent`
    """).to_dataframe()


@st.cache_data(ttl=60)
def load_conversion_by_product() -> pd.DataFrame:
    if USE_MOCK:
        return get_mock_conversion_by_product()
    from google.cloud import bigquery
    project_id = os.environ.get("GCP_PROJECT", "pipeline-health-mon-2026")
    client = bigquery.Client()
    return client.query(f"""
        SELECT product, total_opportunities, won_opportunities, lost_opportunities,
               win_rate_pct, total_pipeline_value, won_value
        FROM `{project_id}.gold.gld_conversion_by_product`
    """).to_dataframe()


def close_bucket(days: int) -> str:
    if days < 0:     return "Overdue"
    if days <= 7:    return "This Week"
    if days <= 30:   return "This Month"
    return "Later"


# ── PDF report builder ────────────────────────────────────────────────────────
def _build_pdf(df_snap, stage_snap, agent_snap, product_snap) -> bytes:
    from fpdf import FPDF
    from datetime import datetime as _dtnow

    class _PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 13)
            self.set_text_color(15, 39, 68)
            self.cell(0, 9, "Pipeline Health Monitor - Report", ln=True, align="C")
            self.set_font("Helvetica", "", 8)
            self.set_text_color(100, 120, 140)
            self.cell(0, 5, f"Generated: {_dtnow.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
            self.ln(3)

        def footer(self):
            self.set_y(-13)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 8, f"Page {self.page_no()}", align="C")

    pdf = _PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=14)

    won  = len(df_snap[df_snap["stage"] == "Won"])
    lost = len(df_snap[df_snap["stage"] == "Lost"])
    cl   = won + lost
    wr   = (won / cl * 100) if cl > 0 else 0

    def section(title):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(15, 39, 68)
        pdf.cell(0, 7, title, ln=True)
        pdf.set_draw_color(200, 215, 235)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2)

    def table(headers, widths, rows):
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(240, 245, 251)
        pdf.set_text_color(30, 30, 30)
        for h, w in zip(headers, widths):
            pdf.cell(w, 6, h, border=1, fill=True)
        pdf.ln()
        pdf.set_font("Helvetica", "", 8)
        for row in rows:
            for val, w in zip(row, widths):
                pdf.cell(w, 5, str(val), border=1)
            pdf.ln()
        pdf.ln(3)

    # KPIs
    section("Key Metrics")
    kpis = [
        ("Total Opportunities", f"{len(df_snap):,}"),
        ("Pipeline Value", f"${df_snap['value'].sum():,.0f}"),
        ("Win Rate", f"{wr:.1f}%"),
        ("Won Deals", f"{won:,}"),
        ("Lost Deals", f"{lost:,}"),
        ("Stale Opportunities", f"{int(df_snap['is_stale'].sum()):,}"),
    ]
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(60, 80, 100)
    col = 95
    for j in range(0, len(kpis), 2):
        for k in range(2):
            if j + k < len(kpis):
                pdf.cell(col, 5, kpis[j + k][0])
        pdf.ln()
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 39, 68)
        for k in range(2):
            if j + k < len(kpis):
                pdf.cell(col, 7, kpis[j + k][1])
        pdf.ln(9)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(60, 80, 100)

    # Stage table
    section("Pipeline by Stage")
    table(
        ["Stage", "Opportunities", "Pipeline Value", "Weighted Forecast", "Stale"],
        [38, 33, 40, 44, 20],
        [
            [r["stage"], f"{r['total_opportunities']:,}", f"${r['total_value']:,.0f}",
             f"${r['weighted_value']:,.0f}", int(r["stale_opportunities"])]
            for _, r in stage_snap.iterrows()
        ],
    )

    # Agent table (top 10 by win rate)
    section("Conversion by Agent (Top 10 by Win Rate)")
    top_agents = agent_snap.sort_values("win_rate_pct", ascending=False).head(10)
    table(
        ["Agent", "Opps", "Won", "Win Rate", "Pipeline Value"],
        [38, 22, 18, 27, 50],
        [
            [r["agent"], r["total_opportunities"], r["won_opportunities"],
             f"{r['win_rate_pct']:.1f}%", f"${r['total_pipeline_value']:,.0f}"]
            for _, r in top_agents.iterrows()
        ],
    )

    # Product table
    section("Conversion by Product")
    table(
        ["Product", "Opps", "Won", "Win Rate", "Pipeline Value"],
        [38, 22, 18, 27, 50],
        [
            [r["product"], r["total_opportunities"], r["won_opportunities"],
             f"{r['win_rate_pct']:.1f}%", f"${r['total_pipeline_value']:,.0f}"]
            for _, r in product_snap.sort_values("win_rate_pct", ascending=False).iterrows()
        ],
    )

    return bytes(pdf.output())


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Pipeline Health Monitor", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #0f2744; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,[data-testid="stSidebar"] span { color: #d6e4f7 !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#8aafd4 !important; font-size:0.8rem; }
[data-testid="stMetric"] { background:#f0f5fb; border-left:4px solid #1e5fa8; padding:16px 20px; border-radius:8px; }
[data-testid="stMetricLabel"] { color:#4a6b8a; font-size:0.85rem; }
[data-testid="stMetricValue"] { color:#0f2744; font-weight:700; }
[data-baseweb="tag"] { background-color:#1e5fa8 !important; }
[data-baseweb="tag"] span { color:#ffffff !important; }
h2 { color:#0f2744 !important; border-bottom:2px solid #e0ebf8; padding-bottom:6px; }
hr { border-color:#e0ebf8; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
raw = load_data()

with st.sidebar:
    st.markdown("## 📊 Pipeline Health")
    st.markdown("---")
    st.markdown("**Filters**")
    selected_regions = st.multiselect("Region", options=REGIONS, default=REGIONS)
    selected_products = st.multiselect("Product", options=PRODUCTS, default=PRODUCTS)
    selected_agents = st.multiselect("Agent", options=AGENTS, default=AGENTS)
    st.markdown("---")
    show_stale_only = st.checkbox("Stale only (>14 days)")
    st.markdown(f"<p>Refreshes every 60 s · {datetime.now().strftime('%H:%M')}</p>", unsafe_allow_html=True)

df = raw[
    raw["region"].isin(selected_regions)
    & raw["product"].isin(selected_products)
    & raw["agent"].isin(selected_agents)
].copy()
if show_stale_only:
    df = df[df["is_stale"]].copy()

st.markdown("# Pipeline Health Monitor")
st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if df.empty:
    st.error("No data matches the selected filters.")
    st.stop()

# Derived columns
df["win_prob"]      = df["stage"].astype(str).map(STAGE_WIN_PROB).fillna(0).astype(float)
df["weighted_value"]= df["value"].astype(float) * df["win_prob"]
df["close_bucket"]  = df["days_until_expected_close"].apply(close_bucket)
df["close_bucket"]  = pd.Categorical(df["close_bucket"], categories=CLOSE_BUCKET_ORDER, ordered=True)

stage_agg = (
    df.groupby("stage", observed=True)
    .agg(total_opportunities=("value","count"), total_value=("value","sum"),
         weighted_value=("weighted_value","sum"), stale_opportunities=("is_stale","sum"),
         avg_days_since_update=("days_since_update","mean"))
    .reset_index()
)
stage_agg["stage"] = stage_agg["stage"].astype(str)

# ── KPIs ──────────────────────────────────────────────────────────────────────
won_opps    = len(df[df["stage"] == "Won"])
lost_opps   = len(df[df["stage"] == "Lost"])
closed      = won_opps + lost_opps
win_rate    = (won_opps / closed * 100) if closed > 0 else 0
avg_deal    = df[df["stage"] == "Won"]["value"].mean() if won_opps > 0 else 0
stale_count = int(df["is_stale"].sum())
stale_pct   = round(stale_count / len(df) * 100, 1) if len(df) > 0 else 0
weighted_total = df["weighted_value"].sum()

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Opportunities", f"{len(df):,}")
k2.metric("Pipeline Value",      f"${df['value'].sum():,.0f}")
k3.metric("Weighted Forecast",   f"${weighted_total:,.0f}")
k4.metric("Win Rate",            f"{win_rate:.1f}%")
k5.metric("Avg Won Deal",        f"${avg_deal:,.0f}")
k6.metric("Stale", f"{stale_count:,}", delta=f"{stale_pct}% of total", delta_color="inverse")

_pdf_bytes = _build_pdf(df, stage_agg, load_conversion_by_agent(), load_conversion_by_product())

_rb1, _rb2, _rb3 = st.columns([1.3, 1.3, 9.4])
with _rb1:
    st.download_button("📄 Download Report", data=_pdf_bytes,
        file_name=f"pipeline_report_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf", use_container_width=True, key="dl_top")
with _rb2:
    if st.button("📧 Send via Email", use_container_width=True, key="email_top"):
        st.session_state["_pdf_for_email"] = _pdf_bytes
        st.session_state["_open_email_dlg"] = True

st.divider()

# ── Funnel + Conversion rates ─────────────────────────────────────────────────
st.subheader("Pipeline Funnel")

funnel_data = stage_agg[stage_agg["stage"] != "Lost"].copy()
funnel_data["stage"] = pd.Categorical(funnel_data["stage"],
    categories=[s for s in STAGE_ORDER if s != "Lost"], ordered=True)
funnel_data = funnel_data.sort_values("stage")
funnel_data["color"] = STAGE_BLUES[:len(funnel_data)]

# Conversion rate between consecutive stages
conv_labels = []
for i in range(len(funnel_data) - 1):
    curr = funnel_data.iloc[i]["total_opportunities"]
    nxt  = funnel_data.iloc[i+1]["total_opportunities"]
    rate = round(nxt / curr * 100, 1) if curr > 0 else 0
    conv_labels.append({
        "stage": funnel_data.iloc[i+1]["stage"],
        "label": f"↓ {rate}%",
        "label_x": nxt * 0.55,  # 55% inside the destination bar
    })
conv_df = pd.DataFrame(conv_labels)

hover = alt.selection_point(on="mouseover", empty=False, fields=["stage"])

funnel_bars = (
    alt.Chart(funnel_data)
    .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6)
    .encode(
        y=alt.Y("stage:N", sort=[s for s in STAGE_ORDER if s != "Lost"],
                title="", axis=alt.Axis(labelFontSize=12, labelFontWeight="bold")),
        x=alt.X("total_opportunities:Q", title="Opportunities",
                axis=alt.Axis(labelFontSize=11)),
        color=alt.Color("stage:N",
            scale=alt.Scale(domain=funnel_data["stage"].tolist(), range=funnel_data["color"].tolist()),
            legend=None),
        opacity=alt.condition(hover, alt.value(1.0), alt.value(0.82)),
        tooltip=[
            alt.Tooltip("stage:N", title="Stage"),
            alt.Tooltip("total_opportunities:Q", title="Opportunities"),
            alt.Tooltip("total_value:Q", title="Pipeline Value", format="$,.0f"),
            alt.Tooltip("weighted_value:Q", title="Weighted Forecast", format="$,.0f"),
            alt.Tooltip("stale_opportunities:Q", title="Stale"),
        ],
    )
    .add_params(hover)
    .properties(height=300)
)

funnel_labels = (
    alt.Chart(funnel_data)
    .mark_text(align="right", dx=-8, fontSize=12, fontWeight="bold", color="#ffffff")
    .encode(
        y=alt.Y("stage:N", sort=[s for s in STAGE_ORDER if s != "Lost"]),
        x=alt.X("total_opportunities:Q"),
        text=alt.Text("total_opportunities:Q"),
    )
)

conv_text = (
    alt.Chart(conv_df)
    .mark_text(align="center", fontSize=11, color="#ffffff", fontWeight="bold")
    .encode(
        y=alt.Y("stage:N", sort=[s for s in STAGE_ORDER if s != "Lost"]),
        x=alt.X("label_x:Q"),
        text=alt.Text("label:N"),
    )
)

fn_left, fn_right = st.columns([3, 1])
with fn_left:
    st.altair_chart((funnel_bars + funnel_labels + conv_text), use_container_width=True)

with fn_right:
    st.markdown("**Conversion rates**")
    counts = stage_agg.set_index("stage")["total_opportunities"].to_dict()
    conv_rows = []
    active = [s for s in STAGE_ORDER[:-1] if s in counts]
    for i in range(len(active) - 1):
        src, dst = active[i], active[i+1]
        rate = (counts.get(dst,0) / counts[src] * 100) if counts.get(src,0) > 0 else 0
        color = "#16a34a" if rate >= 50 else "#ea580c" if rate >= 25 else "#dc2626"
        conv_rows.append(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:6px 0;border-bottom:1px solid #e0ebf8;">
          <span style="font-size:0.82rem;color:#4a6b8a;">{src} → {dst}</span>
          <span style="font-weight:700;color:{color};font-size:0.95rem;">{rate:.0f}%</span>
        </div>""")
    if closed > 0:
        color = "#16a34a" if win_rate >= 40 else "#ea580c" if win_rate >= 20 else "#dc2626"
        conv_rows.append(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;">
          <span style="font-size:0.82rem;color:#4a6b8a;">Won / Closed</span>
          <span style="font-weight:700;color:{color};font-size:0.95rem;">{win_rate:.0f}%</span>
        </div>""")
    st.markdown("".join(conv_rows), unsafe_allow_html=True)

st.divider()

# ── Weighted forecast ─────────────────────────────────────────────────────────
st.subheader("Weighted Revenue Forecast")

forecast_data = stage_agg[stage_agg["stage"] != "Lost"][["stage","total_value","weighted_value"]].copy()
forecast_melted = forecast_data.melt(
    id_vars="stage", value_vars=["total_value","weighted_value"],
    var_name="type", value_name="amount",
)
forecast_melted["type"] = forecast_melted["type"].map(
    {"total_value":"Total Pipeline","weighted_value":"Weighted Forecast"})

forecast_hover = alt.selection_point(on="mouseover", fields=["stage"], empty=False)

forecast_chart = (
    alt.Chart(forecast_melted)
    .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
    .encode(
        x=alt.X("stage:N", sort=STAGE_ORDER, title="",
                axis=alt.Axis(labelFontSize=11, labelFontWeight="bold")),
        y=alt.Y("amount:Q", title="$ Value", axis=alt.Axis(format="$,.0f")),
        color=alt.Color("type:N",
            scale=alt.Scale(domain=["Total Pipeline","Weighted Forecast"],
                            range=["#a8d4f5", PRIMARY]),
            legend=alt.Legend(orient="top-right", title="")),
        xOffset="type:N",
        opacity=alt.condition(forecast_hover, alt.value(1.0), alt.value(0.85)),
        tooltip=["stage","type", alt.Tooltip("amount:Q", format="$,.0f", title="Value")],
    )
    .add_params(forecast_hover)
    .properties(height=300)
)

fc_left, fc_right = st.columns([2, 1])
with fc_left:
    st.altair_chart(forecast_chart, use_container_width=True)
with fc_right:
    st.markdown("**Win probability by stage**")
    prob_df = pd.DataFrame(
        [{"Stage":s, "Win Prob":f"{int(p*100)}%"}
         for s,p in STAGE_WIN_PROB.items() if s not in ("Won","Lost")])
    st.dataframe(prob_df, use_container_width=True, hide_index=True)
    st.caption("Weighted Forecast = Pipeline Value × Win Probability")

st.divider()

# ── Product mix by region ─────────────────────────────────────────────────────
st.subheader("Regional Breakdown & Product Mix")

mix_data = (
    df.groupby(["region","product"])
    .agg(opportunities=("value","count"), total_value=("value","sum"))
    .reset_index()
)

region_hover = alt.selection_point(fields=["region"], on="mouseover", empty=False)

stacked_bar = (
    alt.Chart(mix_data)
    .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
    .encode(
        x=alt.X("region:N", sort=REGIONS, title="",
                axis=alt.Axis(labelFontSize=12, labelFontWeight="bold")),
        y=alt.Y("opportunities:Q", title="Opportunities"),
        color=alt.Color("product:N", sort=PRODUCTS,
            scale=alt.Scale(domain=list(PRODUCT_COLORS.keys()),
                            range=list(PRODUCT_COLORS.values())),
            legend=alt.Legend(title="Product", orient="right", labelFontSize=11)),
        order=alt.Order("product:N", sort="ascending"),
        opacity=alt.condition(region_hover, alt.value(1.0), alt.value(0.85)),
        tooltip=[
            alt.Tooltip("region:N", title="Region"),
            alt.Tooltip("product:N", title="Product"),
            alt.Tooltip("opportunities:Q", title="Opportunities"),
            alt.Tooltip("total_value:Q", title="Pipeline Value", format="$,.0f"),
        ],
    )
    .add_params(region_hover)
    .properties(title=alt.TitleParams("Product Mix by Region", anchor="start"), height=300)
)

# Value by region (line overlay on second axis)
region_value = (
    df.groupby("region").agg(total_value=("value","sum")).reset_index()
)
value_line = (
    alt.Chart(region_value)
    .mark_line(color="#e05c2d", strokeWidth=2.5, point=alt.OverlayMarkDef(filled=True, size=80, color="#e05c2d"))
    .encode(
        x=alt.X("region:N", sort=REGIONS),
        y=alt.Y("total_value:Q", title="Pipeline Value ($)",
                axis=alt.Axis(format="$,.0f")),
        tooltip=[alt.Tooltip("region:N"), alt.Tooltip("total_value:Q", format="$,.0f", title="Pipeline Value")],
    )
)

combo = alt.layer(stacked_bar, value_line).resolve_scale(y="independent")
st.altair_chart(combo, use_container_width=True)

st.divider()

# ── Closing timeline ──────────────────────────────────────────────────────────
st.subheader("Closing Timeline")

bucket_agg = (
    df[df["stage"].isin(["Prospecting","Qualified","Proposal","Negotiation"])]
    .groupby("close_bucket", observed=True)
    .agg(opportunities=("value","count"), pipeline_value=("value","sum"),
         weighted_value=("weighted_value","sum"))
    .reset_index()
)
bucket_agg["close_bucket"] = bucket_agg["close_bucket"].astype(str)
BUCKET_COLORS = {"Overdue":"#c0392b","This Week":"#e67e22","This Month":PRIMARY,"Later":"#7ab8f5"}

ct_left, ct_right = st.columns([1,1])
with ct_left:
    bucket_bars = (
        alt.Chart(bucket_agg)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("close_bucket:N", sort=CLOSE_BUCKET_ORDER, title="",
                    axis=alt.Axis(labelFontSize=12, labelFontWeight="bold")),
            y=alt.Y("opportunities:Q", title="Opportunities"),
            color=alt.Color("close_bucket:N",
                scale=alt.Scale(domain=list(BUCKET_COLORS.keys()),
                                range=list(BUCKET_COLORS.values())),
                legend=None),
            tooltip=["close_bucket","opportunities",
                     alt.Tooltip("pipeline_value:Q", format="$,.0f", title="Pipeline Value")],
        )
        .properties(height=260)
    )
    bucket_labels = (
        alt.Chart(bucket_agg)
        .mark_text(dy=-8, fontSize=13, fontWeight="bold", color="#ffffff")
        .encode(
            x=alt.X("close_bucket:N", sort=CLOSE_BUCKET_ORDER),
            y=alt.Y("opportunities:Q"),
            text=alt.Text("opportunities:Q"),
        )
    )
    st.altair_chart(bucket_bars + bucket_labels, use_container_width=True)

with ct_right:
    overdue   = bucket_agg[bucket_agg["close_bucket"] == "Overdue"]
    this_week = bucket_agg[bucket_agg["close_bucket"] == "This Week"]
    overdue_val = overdue["pipeline_value"].sum() if not overdue.empty else 0
    week_val    = this_week["pipeline_value"].sum() if not this_week.empty else 0
    overdue_n   = int(overdue["opportunities"].sum()) if not overdue.empty else 0
    week_n      = int(this_week["opportunities"].sum()) if not this_week.empty else 0

    st.markdown(f"""
    <div style="display:flex;gap:12px;margin-bottom:12px;">
        <div style="flex:1;background:#fef2f2;border-left:4px solid #c0392b;border-radius:8px;padding:16px 20px;">
            <p style="color:#9b2323;font-size:0.75rem;margin:0;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Overdue</p>
            <p style="color:#c0392b;font-size:2rem;font-weight:700;margin:6px 0 2px;">{overdue_n:,}</p>
            <p style="color:#c0392b;font-size:0.85rem;margin:0;">${overdue_val:,.0f} at risk</p>
        </div>
        <div style="flex:1;background:#fff7ed;border-left:4px solid #e67e22;border-radius:8px;padding:16px 20px;">
            <p style="color:#92400e;font-size:0.75rem;margin:0;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Closing This Week</p>
            <p style="color:#e67e22;font-size:2rem;font-weight:700;margin:6px 0 2px;">{week_n:,}</p>
            <p style="color:#e67e22;font-size:0.85rem;margin:0;">${week_val:,.0f} pipeline</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.dataframe(
        bucket_agg.rename(columns={"close_bucket":"Bucket","opportunities":"Opps",
            "pipeline_value":"Pipeline Value","weighted_value":"Weighted"})
        .style.format({"Pipeline Value":"${:,.0f}","Weighted":"${:,.0f}"}),
        use_container_width=True, hide_index=True,
    )

st.divider()

# ── Agent leaderboard — lollipop ──────────────────────────────────────────────
st.subheader("Agent Leaderboard")

agent_agg = (
    df.groupby("agent")
    .agg(opportunities=("value","count"), total_value=("value","sum"))
    .reset_index()
)
won_by_agent = df[df["stage"]=="Won"].groupby("agent").size().reset_index(name="won")
agent_agg = agent_agg.merge(won_by_agent, on="agent", how="left").fillna({"won":0})
agent_agg["won"]      = agent_agg["won"].astype(int)
agent_agg["win_rate"] = (agent_agg["won"] / agent_agg["opportunities"] * 100).round(1)

top_agents = agent_agg.sort_values("total_value", ascending=False).head(10)

zero_line = alt.Chart(top_agents).mark_rule(color="#dde6f0", strokeWidth=1.5).encode(
    y=alt.Y("agent:N", sort=alt.EncodingSortField("total_value", order="descending")),
    x=alt.X("total_value:Q", title="Pipeline Value ($)"),
    x2=alt.value(0),
)
lollipop_stem = alt.Chart(top_agents).mark_bar(height=3, color="#c8ddf5").encode(
    y=alt.Y("agent:N", sort=alt.EncodingSortField("total_value", order="descending"), title="",
            axis=alt.Axis(labelFontSize=11)),
    x=alt.X("total_value:Q", title="Pipeline Value ($)", axis=alt.Axis(format="$,.0f")),
)
lollipop_dot = alt.Chart(top_agents).mark_point(filled=True, size=120).encode(
    y=alt.Y("agent:N", sort=alt.EncodingSortField("total_value", order="descending")),
    x=alt.X("total_value:Q"),
    color=alt.Color("win_rate:Q",
        scale=alt.Scale(scheme="blues", domainMin=0, domainMax=100),
        legend=alt.Legend(title="Win Rate %", gradientLength=100, orient="right")),
    tooltip=[
        alt.Tooltip("agent:N", title="Agent"),
        alt.Tooltip("total_value:Q", title="Pipeline Value", format="$,.0f"),
        alt.Tooltip("opportunities:Q", title="Opportunities"),
        alt.Tooltip("won:Q", title="Won"),
        alt.Tooltip("win_rate:Q", title="Win Rate", format=".1f"),
    ],
)
lollipop_labels = alt.Chart(top_agents).mark_text(align="left", dx=10, fontSize=10, color="#4a6b8a").encode(
    y=alt.Y("agent:N", sort=alt.EncodingSortField("total_value", order="descending")),
    x=alt.X("total_value:Q"),
    text=alt.Text("win_rate:Q", format=".0f"),
)

lollipop = (lollipop_stem + lollipop_dot + lollipop_labels).properties(
    title=alt.TitleParams("Top 10 Agents by Pipeline Value  (dot color = win rate %)", anchor="start"),
    height=320,
)
st.altair_chart(lollipop, use_container_width=True)

st.divider()

# ── Conversion tables ─────────────────────────────────────────────────────────
st.subheader("Conversion by Agent and Product")

conv_agents   = load_conversion_by_agent().sort_values("win_rate_pct", ascending=False)
conv_products = load_conversion_by_product().sort_values("win_rate_pct", ascending=False)

def _highlight_low_conversion(val):
    return "background-color: #ffcccc" if isinstance(val, float) and val < 20 else ""

cv_left, cv_right = st.columns(2)
with cv_left:
    st.markdown("**Conversion by Agent**")
    st.dataframe(
        conv_agents.style
        .map(_highlight_low_conversion, subset=["win_rate_pct"])
        .format({"win_rate_pct": "{:.2f}%", "total_pipeline_value": "${:,.0f}", "won_value": "${:,.0f}"}),
        use_container_width=True, hide_index=True,
    )
with cv_right:
    st.markdown("**Conversion by Product**")
    st.dataframe(
        conv_products.style
        .map(_highlight_low_conversion, subset=["win_rate_pct"])
        .format({"win_rate_pct": "{:.2f}%", "total_pipeline_value": "${:,.0f}", "won_value": "${:,.0f}"}),
        use_container_width=True, hide_index=True,
    )

st.divider()

# ── Deal size + Stale ─────────────────────────────────────────────────────────
st.subheader("Deal Size & Pipeline Health")

avg_deal_stage = (
    df.groupby("stage", observed=True)["value"].mean()
    .reset_index().rename(columns={"value":"avg_deal_size"})
)
avg_deal_stage["stage"] = avg_deal_stage["stage"].astype(str)
stale_chart_data = stage_agg[["stage","stale_opportunities"]].copy()

ds_left, ds_right = st.columns(2)
with ds_left:
    deal_bars = (
        alt.Chart(avg_deal_stage)
        .mark_bar(color=PRIMARY, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("stage:N", sort=STAGE_ORDER, title="",
                    axis=alt.Axis(labelFontSize=11, labelFontWeight="bold")),
            y=alt.Y("avg_deal_size:Q", title="Avg Deal ($)", axis=alt.Axis(format="$,.0f")),
            tooltip=[alt.Tooltip("stage:N"), alt.Tooltip("avg_deal_size:Q", format="$,.0f", title="Avg Deal")],
        ).properties(title="Avg Deal Size by Stage", height=280)
    )
    deal_labels = (
        alt.Chart(avg_deal_stage)
        .mark_text(dy=-8, fontSize=10, color="#ffffff")
        .encode(
            x=alt.X("stage:N", sort=STAGE_ORDER),
            y=alt.Y("avg_deal_size:Q"),
            text=alt.Text("avg_deal_size:Q", format="$,.0f"),
        )
    )
    st.altair_chart(deal_bars + deal_labels, use_container_width=True)

with ds_right:
    stale_bars = (
        alt.Chart(stale_chart_data)
        .mark_bar(color="#e05c2d", cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("stage:N", sort=STAGE_ORDER, title="",
                    axis=alt.Axis(labelFontSize=11, labelFontWeight="bold")),
            y=alt.Y("stale_opportunities:Q", title="Stale Opportunities"),
            tooltip=["stage","stale_opportunities"],
        ).properties(title="Stale Opportunities by Stage (>14 days)", height=280)
    )
    stale_labels = (
        alt.Chart(stale_chart_data)
        .mark_text(dy=-8, fontSize=10, color="#ffffff")
        .encode(
            x=alt.X("stage:N", sort=STAGE_ORDER),
            y=alt.Y("stale_opportunities:Q"),
            text=alt.Text("stale_opportunities:Q"),
        )
    )
    st.altair_chart(stale_bars + stale_labels, use_container_width=True)

st.divider()

# ── Tables ────────────────────────────────────────────────────────────────────
with st.expander("Stage Breakdown Table"):
    st.dataframe(
        stage_agg.style.format({
            "total_value":"${:,.0f}","weighted_value":"${:,.0f}",
            "total_opportunities":"{:,}","stale_opportunities":"{:,}",
            "avg_days_since_update":"{:.1f}",
        }),
        use_container_width=True, hide_index=True,
    )

with st.expander("Agent Detail Table"):
    st.dataframe(
        agent_agg.sort_values("total_value", ascending=False)
        .style.format({"total_value":"${:,.0f}","win_rate":"{:.1f}%"}),
        use_container_width=True, hide_index=True,
    )

with st.expander("Stale Opportunities Detail"):
    stale_df = df[df["is_stale"]].copy()
    if stale_df.empty:
        st.info("No stale opportunities with current filters.")
    else:
        st.dataframe(
            stale_df[["opportunity_id","stage","agent","product","region",
                       "value","days_since_update","days_until_expected_close"]]
            .sort_values("days_since_update", ascending=False)
            .style.format({"value":"${:,.0f}"}),
            use_container_width=True, hide_index=True,
        )


st.divider()
_rb4, _rb5, _rb6 = st.columns([1.3, 1.3, 9.4])
with _rb4:
    st.download_button("📄 Download Report", data=_pdf_bytes,
        file_name=f"pipeline_report_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf", use_container_width=True, key="dl_bot")
with _rb5:
    if st.button("📧 Send via Email", use_container_width=True, key="email_bot"):
        st.session_state["_pdf_for_email"] = _pdf_bytes
        st.session_state["_open_email_dlg"] = True

# ── AI Chat + Email dialog ──────────────────────────────────────────────────
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(__file__))
from agent import chat as _agent_chat
import streamlit.components.v1 as _components

for _k, _v in [("chat_history", []), ("chat_open", False),
               ("_open_email_dlg", False), ("_pdf_for_email", None)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

_SUGGESTIONS = [
    "How many deals are overdue?",
    "Which agent has the best win rate?",
    "What is the weighted forecast by stage?",
]


@st.dialog("Send Report via Email")
def _email_dialog():
    _pdf = st.session_state.get("_pdf_for_email", b"")
    st.markdown("Enter the recipient's address and we'll attach the PDF report.")
    _to   = st.text_input("Recipient email", placeholder="colleague@company.com")
    _subj = st.text_input("Subject", value=f"Pipeline Report - {datetime.now().strftime('%Y-%m-%d')}")
    _body = st.text_area("Message (optional)",
                         placeholder="Hi, please find the pipeline report attached.", height=80)
    _c1, _c2 = st.columns(2)
    if _c1.button("Send", type="primary", use_container_width=True):
        if not _to:
            st.error("Please enter a recipient email.")
        else:
            _sh = os.environ.get("SMTP_HOST", "")
            _su = os.environ.get("SMTP_USER", "")
            _sp = os.environ.get("SMTP_PASSWORD", "")
            if not (_sh and _su and _sp):
                st.warning("SMTP not configured. Add **SMTP_HOST**, **SMTP_USER** and **SMTP_PASSWORD** to your `.env` file to enable sending.")
                st.download_button("📄 Download PDF instead", data=_pdf,
                    file_name=f"pipeline_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf", use_container_width=True)
            else:
                import smtplib
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText
                from email.mime.base import MIMEBase
                from email import encoders
                try:
                    _mail = MIMEMultipart()
                    _mail["From"], _mail["To"], _mail["Subject"] = _su, _to, _subj
                    _mail.attach(MIMEText(_body or "Please find the pipeline report attached.", "plain"))
                    _part = MIMEBase("application", "octet-stream")
                    _part.set_payload(_pdf)
                    encoders.encode_base64(_part)
                    _part.add_header("Content-Disposition",
                        f"attachment; filename=pipeline_report_{datetime.now().strftime('%Y%m%d')}.pdf")
                    _mail.attach(_part)
                    with smtplib.SMTP_SSL(_sh, 465) as _srv:
                        _srv.login(_su, _sp)
                        _srv.sendmail(_su, _to, _mail.as_string())
                    st.success(f"Report sent to {_to} ✓")
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
        with st.spinner("Analyzing your pipeline data..."):
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
_components.html("""
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
""", height=0)
