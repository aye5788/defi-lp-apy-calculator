from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import math


@dataclass
class PoolQuality:
    tvl_usd: float
    has_volume_7d: bool
    is_outlier: Optional[bool]
    apy: float

    # simple heuristics
    thin_tvl: bool
    very_thin_tvl: bool
    missing_or_zero_apy: bool


def assess_pool_quality(pool_row: Dict[str, Any]) -> PoolQuality:
    tvl = float(pool_row.get("tvlUsd") or 0.0)
    apy = float(pool_row.get("apy") or 0.0)

    vol = pool_row.get("volumeUsd7d")
    has_vol = False
    try:
        has_vol = (vol is not None) and (not math.isnan(float(vol)))
    except Exception:
        has_vol = False

    outlier = pool_row.get("outlier", None)
    if isinstance(outlier, str):
        outlier = outlier.lower() == "true"

    thin = tvl < 250_000
    very_thin = tvl < 100_000

    missing_or_zero_apy = (apy is None) or (float(apy) <= 0.0)

    return PoolQuality(
        tvl_usd=tvl,
        has_volume_7d=has_vol,
        is_outlier=outlier if isinstance(outlier, bool) else None,
        apy=apy,
        thin_tvl=thin,
        very_thin_tvl=very_thin,
        missing_or_zero_apy=missing_or_zero_apy,
    )


def format_warnings(q: PoolQuality) -> List[str]:
    warnings: List[str] = []

    if q.missing_or_zero_apy:
        warnings.append("APY is missing or ≤ 0 for this pool. Projections may be meaningless.")

    if q.very_thin_tvl:
        warnings.append(
            f"Very low TVL (~${q.tvl_usd:,.0f}). Small pools can have unstable APY and higher execution risk."
        )
    elif q.thin_tvl:
        warnings.append(
            f"Low TVL (~${q.tvl_usd:,.0f}). Treat APY as noisier than large pools."
        )

    if not q.has_volume_7d:
        warnings.append(
            "7-day volume is unavailable for this pool (NaN). This app still works (APY-first), "
            "but fee/volume-based breakdowns will be skipped."
        )

    if q.is_outlier is True:
        warnings.append("DeFiLlama flags this pool as an outlier. Be cautious interpreting APY.")

    return warnings

