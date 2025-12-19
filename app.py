import streamlit as st
import pandas as pd

from logic.fetch_pools import get_pools_df
from logic.calculations import (
    project_growth_table,
    build_il_table,
    apy_to_daily_rate,
)

# ------------------------------------------------------------
# Page config
# ------------------------------------------------------------
st.set_page_config(
    page_title="DeFi LP APY Calculator",
    layout="wide",
)

# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
st.title("DeFi LP APY Calculator")
st.caption(
    "APY-first projection using DeFiLlama pool yields. "
    "Impermanent loss shown as a conservative stress test."
)
st.divider()

# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------
with st.sidebar:
    st.header("Settings")

    refresh = st.button("🔄 Refresh pool data")

    st.subheader("Position")
    position_usd = st.number_input(
        "Position size (USD)",
        min_value=0.0,
        value=100.0,
        step=10.0,
        format="%.2f",
    )

    horizon_days = st.slider(
        "Time horizon (days)",
        min_value=1,
        max_value=365,
        value=30,
    )

    compounding = st.selectbox(
        "Compounding method",
        ["Daily (compounded)", "Simple (non-compounded)"],
    )
    compounded = compounding.startswith("Daily")

    st.subheader("Pool filter")
    search = st.text_input("Search (symbol / project / chain)", "")
    max_results = st.slider("Max results", 5, 100, 50)

# ------------------------------------------------------------
# Load pools
# ------------------------------------------------------------
pools_df = get_pools_df(force_refresh=refresh)

# Optional search filter
if search.strip():
    mask = (
        pools_df["symbol"].str.contains(search, case=False, na=False)
        | pools_df["project"].str.contains(search, case=False, na=False)
        | pools_df["chain"].str.contains(search, case=False, na=False)
    )
    pools_df = pools_df[mask]

pools_df = pools_df.head(max_results)

# ------------------------------------------------------------
# Formatting helper
# ------------------------------------------------------------
def format_pools_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["TVL"] = df["tvlUsd"].map(lambda x: f"${x:,.0f}" if pd.notna(x) else "—")
    df["APY"] = df["apy"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
    df["Base APY"] = df["apyBase"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
    df["Reward APY"] = df["apyReward"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")

    return df[
        [
            "project",
            "chain",
            "symbol",
            "TVL",
            "APY",
            "Base APY",
            "Reward APY",
            "volumeUsd7d",
            "pool",
        ]
    ].rename(columns={"volumeUsd7d": "7d Volume"})

# ------------------------------------------------------------
# Pool table
# ------------------------------------------------------------
st.subheader("1) Pick a pool")

st.dataframe(
    format_pools_df(pools_df),
    height=360,
    width="stretch",
)

if pools_df.empty:
    st.warning("No pools match your search.")
    st.stop()

# ------------------------------------------------------------
# Pool selection
# ------------------------------------------------------------
pool_labels = (
    pools_df["symbol"]
    + " | "
    + pools_df["chain"]
    + " | "
    + pools_df["project"]
)

selected_label = st.selectbox(
    "Select pool (by DeFiLlama pool id)",
    pool_labels,
)

selected_pool = pools_df.loc[pool_labels == selected_label].iloc[0]

st.divider()

# ------------------------------------------------------------
# Pool snapshot
# ------------------------------------------------------------
st.subheader("2) Pool snapshot")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Project", selected_pool["project"])
col2.metric("Chain", selected_pool["chain"])
col3.metric("TVL (USD)", f"${selected_pool['tvlUsd']:,.0f}")
col4.metric("APY (%)", f"{selected_pool['apy']:.2f}")

daily_rate = apy_to_daily_rate(selected_pool["apy"]) * 100
st.caption(f"Implied daily rate: **{daily_rate:.4f}%**")

st.divider()

# ------------------------------------------------------------
# Position projection
# ------------------------------------------------------------
st.subheader("3) Position projection")

projection_df = project_growth_table(
    position_usd=position_usd,
    apy_percent=selected_pool["apy"],
    horizon_days=horizon_days,
    compounded=compounded,
)

st.dataframe(
    projection_df,
    hide_index=True,
    width="stretch",
)

end_value = projection_df.iloc[-1]["End Value ($)"]
profit = projection_df.iloc[-1]["Profit ($)"]

col1, col2, col3 = st.columns(3)
col1.metric("Start ($)", f"{position_usd:,.2f}")
col2.metric("End ($)", f"{end_value:,.2f}")
col3.metric("Profit ($)", f"{profit:,.2f}")

st.divider()

# ------------------------------------------------------------
# Impermanent loss stress test
# ------------------------------------------------------------
st.subheader("4) Impermanent loss stress test (± price moves)")

st.caption(
    "Assumes a 50/50 constant-product (v2-style) pool. "
    "APY projection and IL are intentionally shown separately."
)

il_df = build_il_table(
    position_usd=position_usd,
    step=0.05,
    max_move=0.50,
)

il_df_display = il_df.copy()
il_df_display["IL (%)"] = il_df_display["IL (%)"].map(lambda x: f"{x:.2f}%")
il_df_display["IL ($)"] = il_df_display["IL ($)"].map(lambda x: f"${x:,.2f}")

st.dataframe(
    il_df_display,
    hide_index=True,
    height=360,
    width="stretch",
)

# ------------------------------------------------------------
# Footer
# ------------------------------------------------------------
st.caption(
    "Note: This tool uses DeFiLlama pool APY as the primary yield signal. "
    "Impermanent loss is modeled independently and does not account for "
    "v3 ranges, active management, or fee reinvestment effects."
)
