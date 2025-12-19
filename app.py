import streamlit as st
import pandas as pd

from logic.fetch_pools import get_pools_df
from logic.calculations import (
    project_position_value,
    build_il_table,
)

st.set_page_config(page_title="DeFi LP APY Calculator", layout="wide")

st.title("📈 DeFi LP APY Calculator")
st.caption("APY-first, volume-optional. Powered by DeFiLlama pool yields.")

# ----------------------------
# Sidebar controls
# ----------------------------
with st.sidebar:
    st.header("Settings")

    refresh = st.button("🔄 Refresh pool data")

    position_usd = st.number_input(
        "Position size (USD)",
        min_value=1.0,
        value=100.0,
        step=10.0,
    )

    horizon_days = st.number_input(
        "Time horizon (days)",
        min_value=1,
        value=30,
        step=1,
    )

    compounding = st.selectbox(
        "Compounding",
        ["Daily (compounded)", "Simple (no compounding)"],
    )

    st.divider()

    search = st.text_input(
        "Pool filter",
        placeholder="Search (symbol / project / chain)",
        value="eth usdc bsc pancakeswap",
    )

    max_results = st.slider("Max results", 10, 200, 50)

# ----------------------------
# Load pools
# ----------------------------
try:
    pools_df = get_pools_df(force_refresh=refresh)
except Exception as e:
    st.error(f"Failed to load pools: {e}")
    st.stop()

# ----------------------------
# Filter pools
# ----------------------------
filtered = pools_df.copy()

if search.strip():
    q = search.lower()
    filtered = filtered[
        filtered["project"].str.lower().str.contains(q)
        | filtered["chain"].str.lower().str.contains(q)
        | filtered["symbol"].str.lower().str.contains(q)
    ]

filtered = filtered.head(max_results)

st.subheader("1️⃣ Pick a pool")
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
    st.warning("No pools matched your filter.")
    st.stop()

pool_ids = filtered["pool"].tolist()
selected_pool = st.selectbox(
    "Select pool (by DeFiLlama pool id)",
    pool_ids,
    format_func=lambda pid: filtered.loc[filtered["pool"] == pid, "symbol"].iloc[0]
    + " | "
    + filtered.loc[filtered["pool"] == pid, "chain"].iloc[0]
    + " | "
    + filtered.loc[filtered["pool"] == pid, "project"].iloc[0],
)

row = filtered[filtered["pool"] == selected_pool].iloc[0]

# ----------------------------
# Pool snapshot
# ----------------------------
st.subheader("2️⃣ Pool snapshot")

warnings = []
if row["tvlUsd"] and row["tvlUsd"] < 250_000:
    warnings.append(f"Very low TVL (~${row['tvlUsd']:,.0f}). Execution risk may be higher.")
if pd.isna(row["volumeUsd7d"]):
    warnings.append("7-day volume unavailable (NaN). Fee-based estimates skipped.")

if warnings:
    st.warning("\n".join(f"• {w}" for w in warnings))

cols = st.columns(5)
cols[0].metric("Project", row["project"])
cols[1].metric("Chain", row["chain"])
cols[2].metric("Symbol", row["symbol"])
cols[3].metric("TVL (USD)", f"${row['tvlUsd']:,.0f}")
cols[4].metric("APY (%)", f"{row['apy']:.2f}")

# ----------------------------
# Position projection
# ----------------------------
st.subheader("3️⃣ Position projection")

compound_daily = compounding.startswith("Daily")

projection = project_position_value(
    start_usd=position_usd,
    apy=row["apy"],
    days=horizon_days,
    compound_daily=compound_daily,
)

st.dataframe(projection, use_container_width=True)

st.metric("Start ($)", f"{projection.iloc[0]['start_usd']:.2f}")
st.metric("End ($)", f"{projection.iloc[-1]['end_usd']:.2f}")
st.metric("Profit ($)", f"{projection.iloc[-1]['profit_usd']:.2f}")
st.caption(
    "Note: This tool uses DeFiLlama APY as the primary yield signal. "
    "Impermanent loss is not included in the main projection."
)

# ----------------------------
# IL sensitivity (optional)
# ----------------------------
st.subheader("4️⃣ Impermanent Loss sensitivity (±5% steps)")

il_table = build_il_table(
    start_usd=position_usd,
    price_steps_pct=5,
)

st.dataframe(il_table, use_container_width=True)
