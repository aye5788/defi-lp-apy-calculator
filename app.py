import streamlit as st
import pandas as pd

from logic.fetch_pools import get_pools_df
from logic.calculations import (
    project_end_value,
    project_growth_table,
    build_il_table,
)

# --------------------------------------------------
# Page setup
# --------------------------------------------------

st.set_page_config(
    page_title="DeFi LP APY Calculator",
    page_icon="📈",
    layout="wide",
)

st.title("DeFi LP APY Calculator")
st.caption("APY-first projection using DeFiLlama pool yields. IL shown as a stress test.")

# --------------------------------------------------
# Sidebar controls
# --------------------------------------------------

st.sidebar.header("Settings")

if st.sidebar.button("Refresh pool data"):
    pools_df = get_pools_df(force_refresh=True)
else:
    pools_df = get_pools_df()

position_usd = st.sidebar.number_input(
    "Position size (USD)",
    min_value=0.0,
    value=100.0,
    step=50.0,
)

horizon_days = st.sidebar.number_input(
    "Time horizon (days)",
    min_value=1,
    value=30,
    step=1,
)

compounded = st.sidebar.selectbox(
    "Compounding",
    options=[True, False],
    format_func=lambda x: "Daily (compounded)" if x else "Simple (non-compounded)",
)

st.sidebar.divider()

search = st.sidebar.text_input(
    "Pool filter (symbol / project / chain)",
    value="",
)

max_results = st.sidebar.slider("Max results", 10, 200, 50)

# --------------------------------------------------
# Pool filtering
# --------------------------------------------------

df = pools_df.copy()

if search:
    mask = (
        df["symbol"].str.contains(search, case=False, na=False)
        | df["project"].str.contains(search, case=False, na=False)
        | df["chain"].str.contains(search, case=False, na=False)
    )
    df = df[mask]

df = df.sort_values("tvlUsd", ascending=False).head(max_results)

st.subheader("1) Pick a pool")

st.dataframe(
    df[
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
    width="stretch",
)

pool_ids = df["pool"].tolist()

if not pool_ids:
    st.warning("No pools match your filter.")
    st.stop()

selected_pool_id = st.selectbox(
    "Select pool (by DeFiLlama pool id)",
    pool_ids,
    format_func=lambda pid: df.loc[df["pool"] == pid, "symbol"].iloc[0],
)

pool = df[df["pool"] == selected_pool_id].iloc[0]

# --------------------------------------------------
# Pool snapshot
# --------------------------------------------------

st.subheader("2) Pool snapshot")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Project", pool["project"])
col2.metric("Chain", pool["chain"])
col3.metric("TVL (USD)", f"${pool['tvlUsd']:,.0f}")
col4.metric("APY (%)", f"{pool['apy']:.2f}")

# --------------------------------------------------
# Position projection
# --------------------------------------------------

st.subheader("3) Position projection")

end_value = project_end_value(
    position_usd=position_usd,
    apy_percent=pool["apy"],
    days=horizon_days,
    compounded=compounded,
)

growth_table = project_growth_table(
    position_usd=position_usd,
    apy_percent=pool["apy"],
    horizon_days=horizon_days,
    compounded=compounded,
)

st.dataframe(growth_table, width="stretch")

c1, c2, c3 = st.columns(3)

c1.metric("Start ($)", f"{position_usd:,.2f}")
c2.metric("End ($)", f"{end_value:,.2f}")
c3.metric("Profit ($)", f"{end_value - position_usd:,.2f}")

# --------------------------------------------------
# Impermanent loss stress test
# --------------------------------------------------

st.subheader("4) Impermanent loss stress test (± price moves)")

il_table = build_il_table(
    position_usd=position_usd,
    step=0.05,     # 5% increments (your request)
    max_move=0.50, # ±50%
)

st.dataframe(il_table, width="stretch")

st.caption(
    "IL assumes a 50/50 constant-product (v2-style) pool. "
    "APY projection and IL are intentionally shown separately."
)
