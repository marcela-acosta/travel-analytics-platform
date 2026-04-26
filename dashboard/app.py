import os
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st

# Toggle: set USE_MOCK=false once gold.gld_dashboard_opportunities exists in BigQuery
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


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pipeline Health Monitor",
    page_icon="🟢",
    layout="wide",
)

# ── Sidebar filters ───────────────────────────────────────────────────────────
raw = load_data()

with st.sidebar:
    st.header("Filters")
    selected_regions = st.multiselect("Region", options=REGIONS, default=REGIONS)
    selected_products = st.multiselect("Product", options=PRODUCTS, default=PRODUCTS)
    selected_agents = st.multiselect("Agent", options=AGENTS, default=AGENTS)
    show_stale_only = st.checkbox("Stale only (>14 days without update)")
    st.divider()
    st.caption("Data refreshes every 60 seconds.")
    if USE_MOCK:
        st.warning("Mock data active.\nSet USE_MOCK=false to connect BigQuery.")

# Apply filters
df = raw[
    raw["region"].isin(selected_regions)
    & raw["product"].isin(selected_products)
    & raw["agent"].isin(selected_agents)
].copy()

if show_stale_only:
    df = df[df["is_stale"]].copy()

# ── Title ─────────────────────────────────────────────────────────────────────
st.title("Pipeline Health Monitor 🟢")
st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if df.empty:
    st.error("No data matches the selected filters.")
    st.stop()

# ── KPIs ──────────────────────────────────────────────────────────────────────
won_opps = len(df[df["stage"] == "Won"])
lost_opps = len(df[df["stage"] == "Lost"])
closed = won_opps + lost_opps
win_rate = (won_opps / closed * 100) if closed > 0 else 0
avg_deal = df[df["stage"] == "Won"]["value"].mean() if won_opps > 0 else 0
stale_count = int(df["is_stale"].sum())

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Opportunities", f"{len(df):,}")
k2.metric("Total Pipeline Value", f"${df['value'].sum():,.0f}")
k3.metric("Win Rate", f"{win_rate:.1f}%")
k4.metric("Avg Won Deal Size", f"${avg_deal:,.0f}")
k5.metric("Stale Opportunities", f"{stale_count:,}")

st.divider()

# ── Funnel overview ───────────────────────────────────────────────────────────
st.subheader("Funnel Overview")

stage_agg = (
    df.groupby("stage", observed=True)
    .agg(
        total_opportunities=("value", "count"),
        total_value=("value", "sum"),
        stale_opportunities=("is_stale", "sum"),
        avg_days_since_update=("days_since_update", "mean"),
    )
    .reset_index()
)

left, right = st.columns(2)
with left:
    st.caption("Opportunities by Stage")
    st.bar_chart(stage_agg.set_index("stage")["total_opportunities"])
with right:
    st.caption("Pipeline Value by Stage ($)")
    st.bar_chart(stage_agg.set_index("stage")["total_value"])

st.divider()

# ── Stage conversion rates ────────────────────────────────────────────────────
st.subheader("Stage Conversion Rates")

counts = stage_agg.set_index("stage")["total_opportunities"].to_dict()
conversion_rows = []
active_stages = [s for s in STAGE_ORDER[:-1] if s in counts]
for i in range(len(active_stages) - 1):
    src, dst = active_stages[i], active_stages[i + 1]
    rate = (counts.get(dst, 0) / counts[src] * 100) if counts.get(src, 0) > 0 else 0
    conversion_rows.append(
        {"Transition": f"{src} → {dst}", "Conversion Rate": f"{rate:.1f}%", "Rate": rate}
    )

if closed > 0:
    conversion_rows.append(
        {"Transition": "Closed Won Rate (Won / Won+Lost)", "Conversion Rate": f"{win_rate:.1f}%", "Rate": win_rate}
    )

conv_df = pd.DataFrame(conversion_rows)
st.dataframe(conv_df[["Transition", "Conversion Rate"]], use_container_width=True, hide_index=True)

st.divider()

# ── Regional breakdown + Product mix ─────────────────────────────────────────
st.subheader("Regional Breakdown & Product Mix")

reg_col, prod_col = st.columns(2)

with reg_col:
    st.caption("Opportunities by Region")
    region_agg = (
        df.groupby("region")
        .agg(total_opportunities=("value", "count"), total_value=("value", "sum"))
        .sort_values("total_opportunities", ascending=False)
    )
    st.bar_chart(region_agg["total_opportunities"])

with prod_col:
    st.caption("Opportunities by Product")
    product_agg = (
        df.groupby("product")
        .agg(total_opportunities=("value", "count"), total_value=("value", "sum"))
        .sort_values("total_opportunities", ascending=False)
    )
    st.bar_chart(product_agg["total_opportunities"])

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
    st.caption("Top 10 Agents by Pipeline Value")
    st.bar_chart(top_value.set_index("agent")["total_value"])
with lb_right:
    st.caption("Top 10 Agents by Opportunities")
    st.bar_chart(top_opps.set_index("agent")["opportunities"])

st.divider()

# ── Avg deal size by stage ────────────────────────────────────────────────────
st.subheader("Average Deal Size by Stage")

avg_deal_stage = (
    df.groupby("stage", observed=True)["value"]
    .mean()
    .reset_index()
    .rename(columns={"value": "avg_deal_size"})
)
st.bar_chart(avg_deal_stage.set_index("stage")["avg_deal_size"])

st.divider()

# ── Stale opportunities ───────────────────────────────────────────────────────
st.subheader("Stale Opportunities (>14 days without update)")

st.bar_chart(stage_agg.set_index("stage")["stale_opportunities"])

st.divider()

# ── Tables ────────────────────────────────────────────────────────────────────
with st.expander("Stage Breakdown Table"):
    st.dataframe(
        stage_agg.style.format(
            {
                "total_value": "${:,.0f}",
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
