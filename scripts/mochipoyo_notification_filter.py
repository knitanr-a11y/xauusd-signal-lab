#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notification eligibility filter for Mochipoyo minimal scanner outputs.

This module does not send messages.  It only marks rows that are eligible to be
considered by the later Discord/ledger layer.

Rules:
- GOLD: live_risk_status == OK
- BTC: btc_live_risk_status == OK, spread_to_sl_ratio <= threshold, and
  effective_rr_after_spread >= threshold
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class NotificationEligibilityConfig:
    btc_max_spread_to_sl_ratio: float = 0.07
    btc_min_effective_rr_after_spread: float = 1.0


def finite_float(value: Any) -> float:
    try:
        x = float(value)
    except Exception:
        return float("nan")
    return x if math.isfinite(x) else float("nan")


def apply_notification_eligibility(
    df: pd.DataFrame,
    *,
    config: NotificationEligibilityConfig | None = None,
) -> pd.DataFrame:
    config = config or NotificationEligibilityConfig()
    out = df.copy()
    if out.empty:
        out["notification_eligible"] = pd.Series(dtype=bool)
        out["notification_reject_reason"] = pd.Series(dtype="string")
        return out

    eligible: list[bool] = []
    reasons: list[str] = []
    for _, row in out.iterrows():
        symbol = str(row.get("symbol", "")).upper()
        if symbol == "BTC":
            btc_status = str(row.get("btc_live_risk_status", "")).upper()
            if btc_status != "OK":
                eligible.append(False)
                reasons.append(f"BTC_RISK_STATUS_{btc_status or 'MISSING'}")
                continue
            spread_to_sl = finite_float(row.get("spread_to_sl_ratio"))
            if not math.isfinite(spread_to_sl):
                eligible.append(False)
                reasons.append("BTC_SPREAD_TO_SL_RATIO_MISSING")
                continue
            if spread_to_sl > config.btc_max_spread_to_sl_ratio:
                eligible.append(False)
                reasons.append("BTC_SPREAD_TO_SL_RATIO_HIGH")
                continue
            effective_rr = finite_float(row.get("effective_rr_after_spread"))
            if not math.isfinite(effective_rr):
                eligible.append(False)
                reasons.append("BTC_EFFECTIVE_RR_MISSING")
                continue
            if effective_rr < config.btc_min_effective_rr_after_spread:
                eligible.append(False)
                reasons.append("BTC_EFFECTIVE_RR_LOW")
                continue
            eligible.append(True)
            reasons.append("OK")
        else:
            live_status = str(row.get("live_risk_status", "")).upper()
            if live_status == "OK":
                eligible.append(True)
                reasons.append("OK")
            else:
                eligible.append(False)
                reasons.append(f"GOLD_RISK_STATUS_{live_status or 'MISSING'}")

    out["notification_eligible"] = eligible
    out["notification_reject_reason"] = reasons
    return out


def split_notification_eligible(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return df.copy(), df.copy()
    eligible = df.get("notification_eligible", pd.Series([False] * len(df), index=df.index)).fillna(False).astype(bool)
    return df.loc[eligible].copy(), df.loc[~eligible].copy()


__all__ = [
    "NotificationEligibilityConfig",
    "apply_notification_eligibility",
    "split_notification_eligible",
]
