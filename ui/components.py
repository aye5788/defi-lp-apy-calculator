from __future__ import annotations

from typing import List, Tuple
import streamlit as st


def metric_row(metrics: List[Tuple[str, str]]) -> None:
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.metric(label, value)


def warning_box(warnings: List[str]) -> None:
    if not warnings:
        return
    st.warning("**Data quality notes**\n\n" + "\n".join([f"- {w}" for w in warnings]))

