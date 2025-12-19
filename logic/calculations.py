from __future__ import annotations

import math
import pandas as pd


def apy_to_daily_rate(apy_percent: float) -> float:
    """
    Convert APY (%) to implied daily compounded rate.
    daily_rate = (1 + apy)^(1/365) - 1
    """
    apy = max(float(apy_percent), 0.0) / 100.0
    return (1.0 + apy) ** (1.0 / 365.0) - 1.0


def simple_daily_rate_from_apy(apy_percent: float) -> float:
    """
    Convert APY (%) to a simple (non-compounded) daily rate: apy/365.
    """
    apy = max(float(apy_percent), 0.0) / 100.0
    return apy / 365.0


def project_end_value(position_usd: float, apy_percent: float, days: int, compounded: bool = True) -> float:
    position = max(float(position_usd), 0.0)
    d = max(int(days), 0)

    if compounded:
        r = apy_to_daily_rate(apy_percent)
        return position * ((1.0 + r) ** d)
    else:
        r = simple_daily_rate_from_apy(apy_percent)
        return position * (1.0 + r * d)


def project_growth_table(position_usd: float, apy_percent: float, horizon_days: int, compounded: bool = True) -> pd.DataFrame:
    """
    Returns a small projection table at key milestones up to horizon_days.
    """
    horizon = max(int(horizon_days), 1)
    milestones = sorted(set([1, 7, 14, 30, 60, 90, 180, 365, horizon]))
    milestones = [m for m in milestones if m <= horizon]

    rows = []
    for d in milestones:
        end_value = project_end_value(position_usd, apy_percent, d, compounded=compounded)
        rows.append(
            {
                "Day": d,
                "Start Value ($)": round(float(position_usd), 2),
                "End Value ($)": round(float(end_value), 2),
                "Profit ($)": round(float(end_value - float(position_usd)), 2),
            }
        )

    return pd.DataFrame(rows)
import numpy as np
import pandas as pd


def impermanent_loss(price_change: float) -> float:
    """
    price_change: decimal (e.g. 0.05 = +5%, -0.10 = -10%)
    Returns IL vs HODL as decimal (negative = loss).
    Assumes a 50/50 constant-product (v2-style) pool.
    """
    return (2 * np.sqrt(1 + price_change) / (2 + price_change)) - 1


def build_il_table(
    position_usd: float,
    step: float = 0.05,
    max_move: float = 0.50
) -> pd.DataFrame:
    """
    Builds an impermanent loss stress table from -max_move to +max_move.
    Default: +/-50% in 5% increments.
    """
    moves = np.arange(-max_move, max_move + step, step)
    rows = []

    for m in moves:
        il = impermanent_loss(m)
        rows.append({
            "Price move (%)": int(m * 100),
            "IL (%)": round(il * 100, 2),
            "IL ($)": round(position_usd * il, 2)
        })

    return pd.DataFrame(rows)


