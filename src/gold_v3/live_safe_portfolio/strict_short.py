from __future__ import annotations

from typing import Any

from .config import StrictShortConfig


def strict_short_passes(raw: dict[str, Any], cfg: StrictShortConfig) -> tuple[bool, str]:
    """Validate the fixed Stage286 SHORT thresholds using current features."""
    if raw.get("source_candidate") != cfg.base_candidate_name:
        return False, "BASE_NAME_MISMATCH"
    if not bool(raw.get("base_short_exhaust_q90", False)):
        return False, "BASE_CONDITION_FALSE"
    try:
        score = float(raw["score"])
        risk_mean = (float(raw["sp_m15_ret4_atr"]) + float(raw["nq_m15_ret4_atr"])) / 2.0
    except (KeyError, TypeError, ValueError):
        return False, "FEATURE_MISSING"
    if score > cfg.score_max:
        return False, "SCORE_ABOVE_MAX"
    if risk_mean > cfg.risk_m15_ret4_mean_max:
        return False, "RISK_MEAN_ABOVE_MAX"
    return True, "PASS"
