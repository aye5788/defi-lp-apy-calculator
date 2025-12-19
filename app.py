import streamlit as st
import pandas as pd

from logic.fetch_pools import get_pools_df
from logic.validation import assess_pool_quality, format_warnings
from logic.calculations import apy_to_daily_rate, project_growth_table
from ui.components import metric_row, warning_box

st.set_page_config(
    page_title="DeFi LP APY Calculator (DeFiLlama)",
    page_icon="📈",
    layout="wide",
)

st.title("📈 DeFi LP APY Calculator")
st.caption("APY-first, volume-optional. Powered by DeFiLlama pool yields.")

with st.sidebar:
    st.header("Settings")
    refresh = st.button("🔄 Refresh pool data")
    st.divider()

    position_usd = st.number_input("Position size (USD)", min_value=0.0, value=100.0, step=25.0)
    horizon_days = st.number_input("Time horizon (days)", min_value=1, value=30, step=1)

    compounding = st.selectbox(
        "Compounding",
        options=["Daily (compounded)", "Simple (no compounding)"],
        index=0,
        help="Compounded uses (1 + daily_rate)^days. Simple uses daily_rate * days.",
    )

    st.divider()
    st.subheader("Pool filter")
    query = st.text_input("Search (symbol / project / chain)", value="eth usdc bsc pancakeswap")
    max_rows = st.slider("Max results", min_value=10, max_value=500, value=50, step=10)

# Load data
try:
    pools = get_pools_df(force_refresh=refresh)
except Exception as e:
    st.error(f"Failed to load pools from DeFiLlama: {e}")
    st.stop()

# Basic search
q = (query or "").strip().lower()
if q:
    tokens = [t for t in q.replace("/", " ").replace("-", " ").split() if t]
else:
    tokens = []

filtered = pools.copy()
for t in tokens:
    mask = (
        filtered["symbol"].astype(str).str.lower().str.contains(t, na=False)
        | filtered["project"].astype(str).str.lower().str.contains(t, na=False)
        | filtered["chain"].astype(str).str.lower().str.contains(t, na=False)
    )
    filtered = filtered[mask]

filtered = filtered.sort_values(by=["tvlUsd"], ascending=False)

st.subheader("1) Pick a pool")
st.write(
    "Search for a pool, then select it. If volume is missing (NaN), the calculator still works (APY-first)."
)

cols_to_show = ["project", "chain", "symbol", "tvlUsd", "apy", "apyBase", "apyReward", "volumeUsd7d", "pool"]
show_df = filtered[cols_to_show].head(int(max_rows)).copy()

# friendly formatting
for c in ["tvlUsd", "volumeUsd7d"]:
    show_df[c] = pd.to_numeric(show_df[c], errors="coerce")
for c in ["apy", "apyBase", "apyReward"]:
    show_df[c] = pd.to_numeric(show_df[c], errors="coerce")

st.dataframe(show_df, use_container_width=True, hide_index=True)

if show_df.empty:
    st.warning("No pools matched your search. Try fewer keywords (e.g., 'eth usdc bsc').")
    st.stop()

# Select by pool id (unique)
pool_id = st.selectbox(
    "Select pool (by DeFiLlama pool id)",
    options=show_df["pool"].tolist(),
    format_func=lambda pid: f"{show_df.loc[show_df['pool'] == pid, 'symbol'].values[0]} | "
                            f"{show_df.loc[show_df['pool'] == pid, 'chain'].values[0]} | "
                            f"{show_df.loc[show_df['pool'] == pid, 'project'].values[0]}",
)

row = pools.loc[pools["pool"] == pool_id].iloc[0].to_dict()

st.subheader("2) Pool snapshot")
quality = assess_pool_quality(row)
warnings = format_warnings(quality)

if warnings:
    warning_box(warnings)

apy = float(row.get("apy") or 0.0)
daily_rate = apy_to_daily_rate(apy)

metric_row(
    metrics=[
        ("Project", str(row.get("project", ""))),
        ("Chain", str(row.get("chain", ""))),
        ("Symbol", str(row.get("symbol", ""))),
        ("TVL (USD)", f"{float(row.get('tvlUsd') or 0):,.0f}"),
        ("APY (%)", f"{apy:,.2f}"),
        ("Daily rate", f"{daily_rate*100:,.4f}%"),
    ]
)

st.subheader("3) Position projection")
is_compounded = compounding.startswith("Daily")
table = project_growth_table(
    position_usd=position_usd,
    apy_percent=apy,
    horizon_days=int(horizon_days),
    compounded=is_compounded,
)

st.dataframe(table, use_container_width=True, hide_index=True)

final_value = float(table.iloc[-1]["End Value ($)"])
profit = float(table.iloc[-1]["Profit ($)"])

metric_row(
    metrics=[
        ("Start ($)", f"{position_usd:,.2f}"),
        ("End ($)", f"{final_value:,.2f}"),
        ("Profit ($)", f"{profit:,.2f}"),
        ("Method", "Compounded daily" if is_compounded else "Simple"),
    ]
)

st.caption(
    "Note: This tool uses DeFiLlama’s pool APY as the primary yield signal. "
    "It does not model impermanent loss in v1."
)

