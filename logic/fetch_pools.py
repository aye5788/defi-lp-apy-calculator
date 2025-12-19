from __future__ import annotations

import time
import requests
import pandas as pd
import streamlit as st

YIELDS_URL = "https://yields.llama.fi/pools"


def _fetch_raw() -> dict:
    resp = requests.get(YIELDS_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=60 * 15)  # cache 15 minutes
def get_pools_df(force_refresh: bool = False) -> pd.DataFrame:
    """
    Returns DeFiLlama yields pools as a DataFrame.

    force_refresh exists to provide a UI refresh button, but Streamlit cache keys on args
    so toggling it will refresh cache.
    """
    _ = force_refresh  # used only for cache-busting

    data = _fetch_raw()
    if "data" not in data or not isinstance(data["data"], list):
        raise ValueError(f"Unexpected response shape from {YIELDS_URL}")

    df = pd.DataFrame(data["data"]).copy()

    # Ensure common fields exist
    for col in ["project", "chain", "symbol", "tvlUsd", "apy", "apyBase", "apyReward", "volumeUsd7d", "pool"]:
        if col not in df.columns:
            df[col] = None

    # Coerce numeric fields
    for col in ["tvlUsd", "apy", "apyBase", "apyReward", "volumeUsd7d"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Normalize text fields
    for col in ["project", "chain", "symbol", "pool"]:
        df[col] = df[col].astype(str)

    # Some rows may have "None" as string after astype; normalize to empty for text display
    df["project"] = df["project"].replace({"None": ""})
    df["chain"] = df["chain"].replace({"None": ""})
    df["symbol"] = df["symbol"].replace({"None": ""})
    df["pool"] = df["pool"].replace({"None": ""})

    # Drop obviously broken rows (no pool id)
    df = df[df["pool"].str.len() > 0].reset_index(drop=True)

    return df

