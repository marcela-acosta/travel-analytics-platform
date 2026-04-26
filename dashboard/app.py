import os
from datetime import datetime
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

USE_MOCK = os.environ.get("USE_MOCK", "true").lower() == "true"

STAGE_ORDER = ["Prospecting", "Qualified", "Proposal", "Negotiation", "Won", "Lost"]
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

PRIMARY = "#1e5fa8"


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
    client = bigquery.Client()
    df = client.query(
        f"""
        SELECT
            opportunity_id, stage, region, product, agent, value,
            days_since_update, days_until_expected_close, is_stale
        FROM `{project_id}.gold.gld_dashboard_opportunities`
        """
    ).to_dataframe()
    df["stage"] = pd.Categorical(df["stage"], categories=STAGE_ORDER, ordered=True)
    return df.sort_values("stage").reset_index(drop=True)


def close_bucket(days: int) -> str:
    if days < 0:
        return "Overdue"
    if days <= 7:
        return "This Week"
    if days <= 30:
        return "This Month"
    return "Later"


def hbar(df: pd.DataFrame, x: str, y: str, title: str = "", height: int = 280) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar(color=PRIMARY, cornerRadiusEnd=4)
        .encode(
            x=alt.X(f"{x}:Q", title=""),
            y=alt.Y(f"{y}:N", sort="-x", title=""),
            tooltip=[y, x],
        )
        .properties(title=title, height=height)
    )


def vbar(df: pd.DataFrame, x: str, y: str, order: list | None = None, title: str = "", height: int = 280) -> alt.Chart:
    sort = order if order else "-y"
    return (
        alt.Chart(df)
        .mark_bar(color=PRIMARY, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(f"{x}:N", sort=sort, title=""),
            y=alt.Y(f"{y}:Q", title=""),
            tooltip=[x, y],
        )
        .properties(title=title, height=height)
    )


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pipeline Health Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { background-color: #0f2744; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span { color: #d6e4f7 !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #8aafd4 !important; font-size: 0.8rem;
    }
    [data-testid="stMetric"] {
        background-color: #f0f5fb;
        border-left: 4px solid #1e5fa8;
        padding: 16px 20px;
        border-radius: 8px;
    }
    [data-testid="stMetricLabel"] { color: #4a6b8a; font-size: 0.85rem; }
    [data-testid="stMetricValue"] { color: #0f2744; font-weight: 700; }
    [data-baseweb="tag"] { background-color: #1e5fa8 !important; }
    [data-baseweb="tag"] span { color: #ffffff !important; }
    h2 { color: #0f2744 !important; border-bottom: 2px solid #e0ebf8; padding-bottom: 6px; }
    hr { border-color: #e0ebf8; }
    </style>
    """,
    unsafe_allow_html=True,
)

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

# Apply filters
df = raw[
    raw["region"].isin(selected_regions)
    & raw["product"].isin(selected_products)
    & raw["agent"].isin(selected_agents)
].copy()

if show_stale_only:
    df = df[df["is_stale"]].copy()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# Pipeline Health Monitor")
st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if df.empty:
    st.error("No data matches the selected filters.")
    st.stop()

# Derived columns
df["win_prob"] = df["stage"].astype(str).map(STAGE_WIN_PROB).fillna(0).astype(float)
df["weighted_value"] = df["value"].astype(float) * df["win_prob"]
df["close_bucket"] = df["days_until_expected_close"].apply(close_bucket)
df["close_bucket"] = pd.Categorical(df["close_bucket"], categories=CLOSE_BUCKET_ORDER, ordered=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
won_opps = len(df[df["stage"] == "Won"])
lost_opps = len(df[df["stage"] == "Lost"])
closed = won_opps + lost_opps
win_rate = (won_opps / closed * 100) if closed > 0 else 0
avg_deal = df[df["stage"] == "Won"]["value"].mean() if won_opps > 0 else 0
stale_count = int(df["is_stale"].sum())
stale_pct = round(stale_count / len(df) * 100, 1) if len(df) > 0 else 0
weighted_total = df["weighted_value"].sum()

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Opportunities", f"{len(df):,}")
k2.metric("Pipeline Value", f"${df['value'].sum():,.0f}")
k3.metric("Weighted Forecast", f"${weighted_total:,.0f}")
k4.metric("Win Rate", f"{win_rate:.1f}%")
k5.metric("Avg Won Deal", f"${avg_deal:,.0f}")
k6.metric("Stale", f"{stale_count:,}", delta=f"{stale_pct}% of total", delta_color="inverse")

st.divider()

# ── Funnel overview ───────────────────────────────────────────────────────────
st.subheader("Funnel Overview")

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

left, right = st.columns(2)
with left:
    st.altair_chart(
        vbar(stage_agg, "stage", "total_opportunities", order=STAGE_ORDER, title="Opportunities by Stage"),
        use_container_width=True,
    )
with right:
    st.altair_chart(
        vbar(stage_agg, "stage", "total_value", order=STAGE_ORDER, title="Pipeline Value by Stage ($)"),
        use_container_width=True,
    )

st.divider()

# ── Stage conversion rates ────────────────────────────────────────────────────
st.subheader("Stage Conversion Rates")

counts = stage_agg.set_index("stage")["total_opportunities"].to_dict()
conversion_rows = []
active_stages = [s for s in STAGE_ORDER[:-1] if s in counts]
for i in range(len(active_stages) - 1):
    src, dst = active_stages[i], active_stages[i + 1]
    rate = (counts.get(dst, 0) / counts[src] * 100) if counts.get(src, 0) > 0 else 0
    conversion_rows.append({"Transition": f"{src} → {dst}", "Conversion Rate": f"{rate:.1f}%"})

if closed > 0:
    conversion_rows.append({"Transition": "Closed Won Rate (Won / Won+Lost)", "Conversion Rate": f"{win_rate:.1f}%"})

st.dataframe(pd.DataFrame(conversion_rows), use_container_width=True, hide_index=True)

st.divider()

# ── Weighted forecast ─────────────────────────────────────────────────────────
st.subheader("Weighted Revenue Forecast")

forecast_data = stage_agg[stage_agg["stage"] != "Lost"][["stage", "total_value", "weighted_value"]].copy()
forecast_melted = forecast_data.melt(
    id_vars="stage",
    value_vars=["total_value", "weighted_value"],
    var_name="type",
    value_name="amount",
)
forecast_melted["type"] = forecast_melted["type"].map(
    {"total_value": "Total Pipeline", "weighted_value": "Weighted Forecast"}
)

forecast_chart = (
    alt.Chart(forecast_melted)
    .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
    .encode(
        x=alt.X("stage:N", sort=STAGE_ORDER, title=""),
        y=alt.Y("amount:Q", title="$ Value"),
        color=alt.Color(
            "type:N",
            scale=alt.Scale(domain=["Total Pipeline", "Weighted Forecast"], range=["#a8d4f5", PRIMARY]),
            legend=alt.Legend(orient="top-right", title=""),
        ),
        xOffset="type:N",
        tooltip=["stage", "type", alt.Tooltip("amount:Q", format="$,.0f")],
    )
    .properties(height=300)
)

fc_left, fc_right = st.columns([2, 1])
with fc_left:
    st.altair_chart(forecast_chart, use_container_width=True)
with fc_right:
    st.markdown("**Win probability by stage**")
    prob_df = pd.DataFrame(
        [{"Stage": s, "Win Prob": f"{int(p*100)}%"} for s, p in STAGE_WIN_PROB.items() if s not in ("Won", "Lost")]
    )
    st.dataframe(prob_df, use_container_width=True, hide_index=True)
    st.caption("Weighted Forecast = Pipeline Value × Win Probability per stage")

st.divider()

# ── Regional breakdown + Product mix + Heatmap ───────────────────────────────
st.subheader("Regional Breakdown & Product Mix")

reg_col, prod_col = st.columns(2)

with reg_col:
    region_agg = (
        df.groupby("region")
        .agg(total_opportunities=("value", "count"))
        .reset_index()
        .sort_values("total_opportunities", ascending=False)
    )
    st.altair_chart(hbar(region_agg, "total_opportunities", "region", title="Opportunities by Region"), use_container_width=True)

with prod_col:
    product_agg = (
        df.groupby("product")
        .agg(total_opportunities=("value", "count"))
        .reset_index()
        .sort_values("total_opportunities", ascending=False)
    )
    st.altair_chart(hbar(product_agg, "total_opportunities", "product", title="Opportunities by Product"), use_container_width=True)

# Stacked bar: Product mix per Region
mix_data = (
    df.groupby(["region", "product"])
    .agg(opportunities=("value", "count"), total_value=("value", "sum"))
    .reset_index()
)

PRODUCT_COLORS = {
    "Flight":     "#1a3d6e",
    "Hotel":      "#1e5fa8",
    "Car Rental": "#4a9eed",
    "Package 2x": "#f4a261",
    "Package 3x": "#e76f51",
}

stacked_bar = (
    alt.Chart(mix_data)
    .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
    .encode(
        x=alt.X("region:N", sort=REGIONS, title="",
                axis=alt.Axis(labelFontSize=12, labelFontWeight="bold")),
        y=alt.Y("opportunities:Q", title="Opportunities",
                axis=alt.Axis(labelFontSize=11)),
        color=alt.Color(
            "product:N",
            sort=PRODUCTS,
            scale=alt.Scale(
                domain=list(PRODUCT_COLORS.keys()),
                range=list(PRODUCT_COLORS.values()),
            ),
            legend=alt.Legend(title="Product", orient="right", labelFontSize=11),
        ),
        order=alt.Order("product:N", sort="ascending"),
        tooltip=[
            alt.Tooltip("region:N", title="Region"),
            alt.Tooltip("product:N", title="Product"),
            alt.Tooltip("opportunities:Q", title="Opportunities"),
            alt.Tooltip("total_value:Q", title="Pipeline Value", format="$,.0f"),
        ],
    )
    .properties(
        title=alt.TitleParams("Product Mix by Region", fontSize=14, fontWeight="bold", anchor="start"),
        height=300,
    )
)

st.altair_chart(stacked_bar, use_container_width=True)

st.divider()

# ── Closing timeline ──────────────────────────────────────────────────────────
st.subheader("Closing Timeline")

bucket_agg = (
    df[df["stage"].isin(["Prospecting", "Qualified", "Proposal", "Negotiation"])]
    .groupby("close_bucket", observed=True)
    .agg(opportunities=("value", "count"), pipeline_value=("value", "sum"), weighted_value=("weighted_value", "sum"))
    .reset_index()
)
bucket_agg["close_bucket"] = bucket_agg["close_bucket"].astype(str)

BUCKET_COLORS = {"Overdue": "#c0392b", "This Week": "#e67e22", "This Month": PRIMARY, "Later": "#7ab8f5"}

ct_left, ct_right = st.columns([1, 1])
with ct_left:
    bucket_chart = (
        alt.Chart(bucket_agg)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("close_bucket:N", sort=CLOSE_BUCKET_ORDER, title=""),
            y=alt.Y("opportunities:Q", title="Opportunities"),
            color=alt.Color(
                "close_bucket:N",
                scale=alt.Scale(domain=list(BUCKET_COLORS.keys()), range=list(BUCKET_COLORS.values())),
                legend=None,
            ),
            tooltip=["close_bucket", "opportunities", alt.Tooltip("pipeline_value:Q", format="$,.0f")],
        )
        .properties(title="Open Opportunities by Expected Close", height=280)
    )
    st.altair_chart(bucket_chart, use_container_width=True)

with ct_right:
    st.markdown("**Pipeline at risk**")
    overdue = bucket_agg[bucket_agg["close_bucket"] == "Overdue"]
    this_week = bucket_agg[bucket_agg["close_bucket"] == "This Week"]
    overdue_val = overdue["pipeline_value"].sum() if not overdue.empty else 0
    week_val = this_week["pipeline_value"].sum() if not this_week.empty else 0
    overdue_n = int(overdue["opportunities"].sum()) if not overdue.empty else 0
    week_n = int(this_week["opportunities"].sum()) if not this_week.empty else 0

    st.markdown(f"""
    <div style="display:flex;gap:12px;margin-bottom:4px;">
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
    st.divider()
    st.dataframe(
        bucket_agg.rename(columns={
            "close_bucket": "Bucket",
            "opportunities": "Opps",
            "pipeline_value": "Pipeline Value",
            "weighted_value": "Weighted",
        }).style.format({"Pipeline Value": "${:,.0f}", "Weighted": "${:,.0f}"}),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# ── Agent leaderboard ─────────────────────────────────────────────────────────
st.subheader("Agent Leaderboard")

agent_agg = (
    df.groupby("agent")
    .agg(opportunities=("value", "count"), total_value=("value", "sum"))
    .reset_index()
)
won_by_agent = df[df["stage"] == "Won"].groupby("agent").size().reset_index(name="won")
agent_agg = agent_agg.merge(won_by_agent, on="agent", how="left").fillna({"won": 0})
agent_agg["won"] = agent_agg["won"].astype(int)
agent_agg["win_rate"] = (agent_agg["won"] / agent_agg["opportunities"] * 100).round(1)

top_value = agent_agg.sort_values("total_value", ascending=False).head(10)
top_opps = agent_agg.sort_values("opportunities", ascending=False).head(10)

lb_left, lb_right = st.columns(2)
with lb_left:
    st.altair_chart(hbar(top_value, "total_value", "agent", title="Top 10 Agents by Pipeline Value"), use_container_width=True)
with lb_right:
    st.altair_chart(hbar(top_opps, "opportunities", "agent", title="Top 10 Agents by Opportunities"), use_container_width=True)

st.divider()

# ── Avg deal size + Stale by stage ────────────────────────────────────────────
st.subheader("Deal Size & Pipeline Health")

avg_deal_stage = (
    df.groupby("stage", observed=True)["value"]
    .mean()
    .reset_index()
    .rename(columns={"value": "avg_deal_size"})
)
avg_deal_stage["stage"] = avg_deal_stage["stage"].astype(str)

ds_left, ds_right = st.columns(2)
with ds_left:
    st.altair_chart(
        vbar(avg_deal_stage, "stage", "avg_deal_size", order=STAGE_ORDER, title="Avg Deal Size by Stage ($)"),
        use_container_width=True,
    )
with ds_right:
    stale_chart_data = stage_agg[["stage", "stale_opportunities"]].copy()
    st.altair_chart(
        alt.Chart(stale_chart_data)
        .mark_bar(color="#e05c2d", cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("stage:N", sort=STAGE_ORDER, title=""),
            y=alt.Y("stale_opportunities:Q", title=""),
            tooltip=["stage", "stale_opportunities"],
        )
        .properties(title="Stale Opportunities by Stage (>14 days)", height=280),
        use_container_width=True,
    )

st.divider()

# ── Tables ────────────────────────────────────────────────────────────────────
with st.expander("Stage Breakdown Table"):
    st.dataframe(
        stage_agg.style.format(
            {
                "total_value": "${:,.0f}",
                "weighted_value": "${:,.0f}",
                "total_opportunities": "{:,}",
                "stale_opportunities": "{:,}",
                "avg_days_since_update": "{:.1f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

with st.expander("Agent Detail Table"):
    st.dataframe(
        agent_agg.sort_values("total_value", ascending=False).style.format(
            {"total_value": "${:,.0f}", "win_rate": "{:.1f}%"}
        ),
        use_container_width=True,
        hide_index=True,
    )

with st.expander("Stale Opportunities Detail"):
    stale_df = df[df["is_stale"]].copy()
    if stale_df.empty:
        st.info("No stale opportunities with current filters.")
    else:
        st.dataframe(
            stale_df[
                ["opportunity_id", "stage", "agent", "product", "region", "value", "days_since_update", "days_until_expected_close"]
            ]
            .sort_values("days_since_update", ascending=False)
            .style.format({"value": "${:,.0f}"}),
            use_container_width=True,
            hide_index=True,
        )
