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
    agg["win_rate_pct"] = (agg["won_opportunities"] / closed.replace(0, pd.NA) * 100).round(2).fillna(0.0).infer_objects(copy=False)
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
    agg["win_rate_pct"] = (agg["won_opportunities"] / closed.replace(0, pd.NA) * 100).round(2).fillna(0.0).infer_objects(copy=False)
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
st.subheader("Conversión por Agente y Producto")

conv_agents   = load_conversion_by_agent().sort_values("win_rate_pct", ascending=False)
conv_products = load_conversion_by_product().sort_values("win_rate_pct", ascending=False)

def _highlight_low_conversion(val):
    return "background-color: #ffcccc" if isinstance(val, float) and val < 20 else ""

cv_left, cv_right = st.columns(2)
with cv_left:
    st.markdown("**Conversión por Agente**")
    st.dataframe(
        conv_agents.style
        .applymap(_highlight_low_conversion, subset=["win_rate_pct"])
        .format({"win_rate_pct": "{:.2f}%", "total_pipeline_value": "${:,.0f}", "won_value": "${:,.0f}"}),
        use_container_width=True, hide_index=True,
    )
with cv_right:
    st.markdown("**Conversión por Producto**")
    st.dataframe(
        conv_products.style
        .applymap(_highlight_low_conversion, subset=["win_rate_pct"])
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
