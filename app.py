import streamlit as st
import pandas as pd

from logic.fetch_pools import fetch_pools
from logic.calculations import (
    project_position_value,
    build_il_table,
)
from logic.validation import assess_pool_quality


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="DeFi LP APY Calculator",
    page_icon="📈",
    layout="wide",
)


# -----------------------------
# Header
# -----------------------------
st.title("DeFi LP APY Calculator")
st.caption(
    "APY-first, volume-optional. Powered by DeFiLlama pool yields. "
    "Includes impermanent loss stress testing."
)


# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Settings")

refresh = st.sidebar.button("🔄 Refresh pool data")

position_size = st.sidebar.number_input(
    "Position size (USD)",
    min_value=1.0,
    value=100.0,
    step=10.0,
)

time_horizon = st.sidebar.number_input(
    "Time horizon (days)",
    min_value=1,
    value=30,
    step=1,
)

compounding = st.sidebar.selectbox(
    "Compounding",
    options=["None", "Daily (compounded)"],
    index=1,
)

st.sidebar.markdown("---")

search = st.sidebar.text_input(
    "Pool filter",
    value="eth usdc bsc pancakeswap",
    help="Search by symbol / project / chain",
)

max_results = st.sidebar.slider(
    "Max results",
    min_value=10,
    max_value=200,
    value=50,
    step=10,
)


# -----------------------------
# Load pool data
# -----------------------------
@st.cache_data(ttl=900)
def load_pools():
    return fetch_pools()


if refresh:
    load_pools.clear()

pools = load_pools()

if pools.empty:
    st.error("No pool data returned from DeFiLlama.")
    st.stop()


# -----------------------------
# Filter pools
# -----------------------------
mask = (
    pools["symbol"].str.contains(search, case=False, na=False)
    | pools["project"].str.contains(search, case=False, na=False)
    | pools["chain"].str.contains(search, case=False, na=False)
)

filtered = pools[mask].head(max_results)

st.subheader("1) Pick a pool")
st.caption(
    "Search for a pool, then select it. "
    "If volume is missing (NaN), the calculator still works (APY-first)."
)

st.dataframe(
    filtered[
        [
            "project",
            "chain",
            "symbol",
            "tvlUsd",
            "apy",
            "apyBase",
            "apyReward",
            "volumeUsd7d",
            "pool",
        ]
    ],
    use_container_width=True,
)

if filtered.empty:
    st.warning("No pools match your filter.")
    st.stop()


pool_options = {
    f"{row['symbol']} | {row['chain']} | {row['project']}": row["pool"]
    for _, row in filtered.iterrows()
}

selected_label = st.selectbox(
    "Select pool (by DeFiLlama pool id)",
    options=list(pool_options.keys()),
)

selected_pool_id = pool_options[selected_label]
pool = pools[pools["pool"] == selected_pool_id].iloc[0]


# -----------------------------
# Pool snapshot
# -----------------------------
st.subheader("2) Pool snapshot")

quality = assess_pool_quality(pool)

if quality.warnings:
    st.warning("**Data quality notes**")
    for w in quality.warnings:
        st.write(f"• {w}")

cols = st.columns(5)

cols[0].metric("Project", pool["project"])
cols[1].metric("Chain", pool["chain"])
cols[2].metric("Symbol", pool["symbol"])
cols[3].metric("TVL (USD)", f"${pool['tvlUsd']:,.0f}")
cols[4].metric("APY (%)", f"{pool['apy']:.2f}")

daily_rate = pool["apy"] / 100 / 365
st.caption(f"Daily rate: **{daily_rate:.4%}**")


# -----------------------------
# Position projection
# -----------------------------
st.subheader("3) Position projection")

projection = project_position_value(
    start_value=position_size,
    apy=pool["apy"],
    days=time_horizon,
    compound=(compounding != "None"),
)

st.dataframe(projection, use_container_width=True)

end_value = projection.iloc[-1]["End Value ($)"]
profit = end_value - position_size

cols = st.columns(4)
cols[0].metric("Start ($)", f"{position_size:,.2f}")
cols[1].metric("End ($)", f"{end_value:,.2f}")
cols[2].metric("Profit ($)", f"{profit:,.2f}")
cols[3].metric("Method", compounding)


# -----------------------------
# Impermanent Loss section
# -----------------------------
st.markdown("---")
st.subheader("4) Impermanent Loss stress test")

st.caption(
    "Assumes a 50/50 constant-product pool (Uniswap v2 / PancakeSwap v2 style). "
    "Shows loss vs HODL for ±50% price moves in 5% steps. "
    "This does NOT include fee offsets."
)

il_table = build_il_table(position_size)

st.dataframe(il_table, use_container_width=True)

st.info(
    "Note: This tool uses DeFiLlama APY as the primary yield signal. "
    "Impermanent loss is modeled independently and conservatively. "
    "v3 range behavior is intentionally NOT modeled."
)

