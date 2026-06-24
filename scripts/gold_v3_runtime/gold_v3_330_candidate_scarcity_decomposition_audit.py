#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import gold_v3_311_mochipoyo_and_independent_candidate_research as stage311
import gold_v3_314_prospective_mochipoyo_watch as stage314
import gold_v3_329_persistent_router_prospective_shadow_runtime_audit as stage329

STATUS = "GOLD_V3_330_CANDIDATE_SCARCITY_DECOMPOSITION_AUDIT_ONLY"
STAGE329_STATUS = "GOLD_V3_329_PERSISTENT_ROUTER_PROSPECTIVE_SHADOW_RUNTIME_AUDIT_ONLY"
START = pd.Timestamp("2024-01-01 00:00:00")
END = pd.Timestamp("2026-01-01 00:00:00")
YEARS = (2024, 2025)
TOL = 1e-12
POINT_SIZE = 0.01
SPEC_SHA = "9c38b9241da9f00f5f65df3f5321517001c8cafed56fe4a4a100da043e9a76bc"
SPEC_PATH = Path(__file__).resolve().parent / "models" / "gold_v3_330" / "stage330_candidate_scarcity_decomposition_spec.json"
ANCHOR = "ANCHOR_STAGE329_EXACT"
TRACKS = (
    "MOCHI_EARLY_PULLBACK",
    "MOCHI_HIDDEN_PULLBACK",
    "MOCHI_HTF_RCI_RESUME",
    "MOCHI_ROLL_RETEST",
)


class AuditError(RuntimeError):
    pass


@dataclass(frozen=True)
class Variant:
    variant_id: str
    axis_changed: str
    direction: str
    atr_min: float
    exclude_round_number: bool
    lane_mode: str
    diagnostic_only: bool = False


VARIANTS = (
    Variant(ANCHOR, "NONE_ANCHOR", "SHORT", 1.00, True, "BALANCED_OR_PREMIUM"),
    Variant("RELAX_ATR_MIN_TO_0P90_ONLY", "ATR_MIN_ONLY", "SHORT", 0.90, True, "BALANCED_OR_PREMIUM"),
    Variant("ALLOW_ROUND_NUMBER_ONLY", "ROUND_EXCLUSION_ONLY", "SHORT", 1.00, False, "BALANCED_OR_PREMIUM"),
    Variant("ALLOW_OUTSIDE_FIXED_LANE_ONLY", "LANE_MEMBERSHIP_ONLY", "SHORT", 1.00, True, "ALL_CANONICAL"),
    Variant("LONG_MIRROR_DIAGNOSTIC_ONLY", "DIRECTION_MIRROR", "LONG", 1.00, True, "BALANCED_OR_PREMIUM", True),
)


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--candle-dir", required=True)
    p.add_argument("--stage329-watch", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--flow-csv", required=True)
    p.add_argument("--variant-summary-csv", required=True)
    p.add_argument("--near-miss-csv", required=True)
    p.add_argument("--incremental-trades-csv", required=True)
    p.add_argument("--context-summary-csv", required=True)
    p.add_argument("--point-size", type=float, default=POINT_SIZE)
    return p.parse_args()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def write_json(path: Path, obj: dict[str, Any]) -> None:
    atomic_text(path, json.dumps(stage314.json_safe(obj), ensure_ascii=False, indent=2) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    for c in ("decision_dt", "entry_dt", "exit_dt", "max_exit_dt"):
        if c in frame.columns:
            frame[c] = frame[c].map(stage314.iso)
    atomic_text(path, "\ufeff" + frame.to_csv(index=False, lineterminator="\n"))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_inputs(watch_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not SPEC_PATH.is_file() or sha(SPEC_PATH) != SPEC_SHA:
        raise AuditError("STAGE330_FROZEN_SPEC_MISSING_OR_SHA_MISMATCH")
    spec = load_json(SPEC_PATH)
    if spec.get("variants") != [asdict(v) for v in VARIANTS]:
        raise AuditError("STAGE330_SPEC_VARIANT_MISMATCH")
    if tuple(stage329.POOLED_TRACKS) != TRACKS or stage329.TOL != TOL:
        raise AuditError("STAGE329_IMPORTED_CONTRACT_CHANGED")
    if not watch_path.is_file():
        raise AuditError("STAGE329_WATCH_MISSING")
    watch = load_json(watch_path)
    if watch.get("status") != STAGE329_STATUS or watch.get("integrity", {}).get("pass") is not True:
        raise AuditError("STAGE329_WATCH_STATUS_OR_INTEGRITY_FAILED")
    fixed = watch.get("fixed_contract", {})
    expected = {
        "source_candidate": stage329.EXPECTED_SOURCE,
        "policy": stage329.EXPECTED_POLICY,
        "lane": stage329.EXPECTED_LANE,
        "cost_view": stage329.EXPECTED_COST_VIEW,
        "prospective_decision_dt_strictly_after": str(stage329.EXPECTED_CUTOFF),
    }
    if any(fixed.get(k) != v for k, v in expected.items()):
        raise AuditError("STAGE329_FIXED_CONTRACT_MISMATCH")
    if fixed.get("premium_subgroup_precedence") is not True or fixed.get("one_position_before_router") is not True:
        raise AuditError("STAGE329_PRECEDENCE_OR_ONE_POSITION_MISMATCH")
    lineage = watch.get("frozen_lineage", {})
    if lineage.get("contract_sha256") != stage329.EXPECTED_CONTRACT_SHA256:
        raise AuditError("STAGE329_CONTRACT_SHA_MISMATCH")
    if lineage.get("bootstrap_sha256") != stage329.EXPECTED_BOOTSTRAP_SHA256:
        raise AuditError("STAGE329_BOOTSTRAP_SHA_MISMATCH")
    if lineage.get("bootstrap_internal_state_sha256") != stage329.EXPECTED_BOOTSTRAP_STATE_SHA256:
        raise AuditError("STAGE329_BOOTSTRAP_STATE_SHA_MISMATCH")
    safety = watch.get("safety_flags", {})
    for k in ("gold_v3_audit_only", "closed_candles_only", "mt5_server_time", "resolved_only_state_updates", "pending_as_of_pnl_forbidden"):
        if safety.get(k) is not True:
            raise AuditError(f"STAGE329_REQUIRED_TRUE_MISSING:{k}")
    for k in ("stage329_live_ready", "stage329_final_signal_emission_enabled", "future_entry_or_router_leakage", "final_signal_changed", "mt5_order_enabled", "discord_enabled", "partial_close_enabled"):
        if safety.get(k) is not False:
            raise AuditError(f"STAGE329_REQUIRED_FALSE_MISSING:{k}")
    if watch.get("promotion", {}).get("automatic_promotion") is not False:
        raise AuditError("STAGE329_AUTOMATIC_PROMOTION_UNEXPECTED")
    return spec, watch


def raw_signals(frame: pd.DataFrame, pair: Any) -> list[dict[str, Any]]:
    lookup = {x.name: x for x in stage311.TRACK_SPECS}
    if any(t not in lookup or lookup[t].category != "MOCHIPOYO" for t in TRACKS):
        raise AuditError("FROZEN_MOCHIPOYO_TRACK_MISSING_OR_CHANGED")
    out: list[dict[str, Any]] = []
    for name in TRACKS:
        for row in stage311.generate_track_signals(frame, pair, lookup[name]):
            dt = pd.Timestamp(row["decision_dt"])
            if START <= dt < END:
                out.append(dict(row))
    out.sort(key=lambda x: (pd.Timestamp(x["decision_dt"]), str(x["direction"]), str(x["track"])))
    if not out:
        raise AuditError("NO_2024_2025_MOCHIPOYO_RAW_SIGNALS")
    return out


def event_id(v: Variant, dt: Any, direction: str) -> str:
    raw = f"STAGE330|{v.variant_id}|{direction}|{pd.Timestamp(dt).isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def filtered(raw: list[dict[str, Any]], v: Variant) -> tuple[list[dict[str, Any]], list[tuple[str, int]]]:
    d = [x for x in raw if x["direction"] == v.direction]
    a = [x for x in d if float(x["atr_ratio_signal"]) + TOL >= v.atr_min]
    r = [x for x in a if not v.exclude_round_number or not bool(x["round_number_near"])]
    return r, [
        ("RAW_ALL_POOLED_TRACK_ONSETS", len(raw)),
        (f"DIRECTION_{v.direction}", len(d)),
        (f"ATR_RATIO_GE_{v.atr_min:.2f}", len(a)),
        ("ROUND_NUMBER_EXCLUDED" if v.exclude_round_number else "ROUND_NUMBER_ALLOWED", len(r)),
    ]


def canonical(rows: list[dict[str, Any]], v: Variant) -> list[dict[str, Any]]:
    if not rows:
        return []
    frame = pd.DataFrame(rows)
    out: list[dict[str, Any]] = []
    parity_float = ("atr_entry_context", "last_swing_high", "last_swing_low", "atr_ratio_signal", "extension_atr_signal", "compression_ratio_signal", "range_atr_signal")
    for dt, group in frame.groupby("decision_dt", sort=True):
        for c in ("pair", "direction", "direction_num", "signal_index"):
            if group[c].nunique(dropna=False) != 1:
                raise AuditError(f"CANONICAL_PARITY_FAILED:{v.variant_id}:{c}")
        for c in parity_float:
            stage329.stage319.same_optional_float(group[c], c)
        best = group.sort_values(["quality_score", "track"], ascending=[False, True], kind="mergesort").iloc[0].to_dict()
        tracks = sorted(set(group.track.astype(str)))
        atr, rng = float(best["atr_ratio_signal"]), float(best["range_atr_signal"])
        comp = stage329.optional_float(best.get("compression_ratio_signal"))
        balanced = len(tracks) >= 2 or (1.10 <= atr <= 1.45 and 0.70 <= rng <= 1.05)
        premium = comp is not None and comp >= 0.95
        router_group = "PREMIUM_INVOLVED" if premium else "BALANCED_WITHOUT_PREMIUM" if balanced else None
        best.update({
            "variant_id": v.variant_id,
            "axis_changed": v.axis_changed,
            "source_candidate": f"STAGE330_RESEARCH|{v.variant_id}",
            "candidate_id": f"GOLD_V3_STAGE330_{v.variant_id}",
            "event_id": event_id(v, dt, str(best["direction"])),
            "priority": 0 if v.variant_id == ANCHOR else 10,
            "setup": "MOCHI_UNION",
            "track": "MOCHI_UNION",
            "category": "STAGE330_CANDIDATE_SCARCITY_RESEARCH_ONLY",
            "decision_dt": pd.Timestamp(dt),
            "quality_score": float(group.quality_score.max()),
            "pooled_tracks": "+".join(tracks),
            "pooled_track_count": len(tracks),
            "balanced_eligible": bool(balanced),
            "premium_eligible": bool(premium),
            "router_group": router_group,
            "exit_profile": "RR1_5",
        })
        out.append(best)
    return sorted(out, key=lambda x: (pd.Timestamp(x["decision_dt"]), str(x["direction"])))


def eligible(rows: list[dict[str, Any]], v: Variant) -> list[dict[str, Any]]:
    if v.lane_mode == "ALL_CANONICAL":
        return rows
    if v.lane_mode == "BALANCED_OR_PREMIUM":
        return [x for x in rows if x.get("router_group") is not None]
    raise AuditError(f"UNKNOWN_LANE_MODE:{v.lane_mode}")


def portfolio(rows: list[dict[str, Any]], frame: pd.DataFrame, m1: pd.DataFrame, pair: Any, point: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    prepared = [stage314.prepare_trade(x, frame, m1, pair, point) for x in rows]
    return prepared, stage314.apply_portfolio_policy(prepared)


def resolved(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [x for x in rows if x.get("portfolio_status") == "ACCEPTED" and x.get("trade_state") == "RESOLVED" and pd.Timestamp(x["entry_dt"]) < END and pd.Timestamp(x["exit_dt"]) < END]


def frame_for_metrics(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["entry_dt", "exit_dt", "direction_num", "spread_adjusted_pnl", "spread_adjusted_r"])
    f = pd.DataFrame(rows).copy()
    f["entry_dt"] = pd.to_datetime(f.entry_dt, errors="raise")
    f["exit_dt"] = pd.to_datetime(f.exit_dt, errors="raise")
    f["direction_num"] = pd.to_numeric(f.direction_num, errors="raise")
    return f


def wilson(wins: int, n: int) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    z, p = 1.959963984540054, wins / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    rad = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / den
    return max(0.0, mid - rad), min(1.0, mid + rad)


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    s = stage314.summarize_resolved(frame_for_metrics(rows))
    lo, hi = wilson(int(s["wins"]), int(s["trades"]))
    return {**s, "win_rate_wilson_low": lo, "win_rate_wilson_high": hi}


def yearly(rows: list[dict[str, Any]], year: int) -> dict[str, Any]:
    return metrics([x for x in rows if pd.Timestamp(x["entry_dt"]).year == year])


def pf(s: dict[str, Any]) -> float:
    value = s["spread_adjusted_profit_factor"]
    return float("inf") if value is None and s["spread_adjusted_total_usd"] > 0 else float(value or 0)


def delta(a: float, b: float) -> float | None:
    if math.isinf(a) and math.isinf(b):
        return 0.0
    return None if math.isinf(a) or math.isinf(b) else a - b


def bucket(v: Variant, inc: dict[str, Any], comb: dict[str, Any], anchor: dict[str, Any], y24: dict[str, Any], y25: dict[str, Any]) -> str:
    if v.diagnostic_only:
        return "DIAGNOSTIC_ONLY_NO_CANDIDATE_SELECTION"
    c_pf, a_pf = pf(comb), pf(anchor)
    total_up = comb["spread_adjusted_total_r"] > anchor["spread_adjusted_total_r"] + TOL
    if inc["trades"] >= 20 and y24["trades"] >= 5 and y25["trades"] >= 5 and comb["win_rate"] >= anchor["win_rate"] - 0.02 - TOL and c_pf >= a_pf - TOL and total_up and comb["spread_adjusted_max_drawdown_r"] <= anchor["spread_adjusted_max_drawdown_r"] + 2 + TOL:
        return "A_PROMISING_HUMAN_REVIEW_ONLY"
    pf95 = math.isinf(c_pf) if math.isinf(a_pf) else c_pf >= 0.95 * a_pf - TOL
    if inc["trades"] >= 10 and comb["win_rate"] >= anchor["win_rate"] - 0.03 - TOL and pf95 and total_up:
        return "B_MORE_SAMPLE_OR_MIXED_HUMAN_REVIEW_ONLY"
    return "C_WEAK_OR_INSUFFICIENT_NO_ACTION"


def flow(v: Variant, raw_flow: list[tuple[str, int]], can: list[dict[str, Any]], elig: list[dict[str, Any]], prepared: list[dict[str, Any]], port: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stages = raw_flow + [
        ("CANONICAL_DEDUPLICATED", len(can)),
        ("LANE_ELIGIBLE_CANONICAL", len(elig)),
        ("PREPARED_TRADABLE_RESOLVED_OR_PENDING", sum(x.get("trade_state") in {"RESOLVED", "PENDING_RESOLUTION"} and x.get("entry_dt") is not None for x in prepared)),
        ("SOURCE_ONE_POSITION_ACCEPTED", sum(x.get("portfolio_status") == "ACCEPTED" for x in port)),
        ("SOURCE_ONE_POSITION_ACCEPTED_RESOLVED", len(resolved(port))),
    ]
    out, previous = [], None
    for order, (name, count) in enumerate(stages, 1):
        out.append({"variant_id": v.variant_id, "stage_order": order, "stage": name, "count": count, "drop_from_previous": None if previous is None else previous - count, "retention_rate_from_previous": None if not previous else count / previous})
        previous = count
    return out


def summary(v: Variant, payload: dict[str, Any], anchor_rows: list[dict[str, Any]], combined_rows: list[dict[str, Any]], incremental: list[dict[str, Any]], overlap: int) -> dict[str, Any]:
    stand, anc, comb, inc = metrics(payload["resolved"]), metrics(anchor_rows), metrics(combined_rows), metrics(incremental)
    s24, s25, i24, i25 = yearly(payload["resolved"], 2024), yearly(payload["resolved"], 2025), yearly(incremental, 2024), yearly(incremental, 2025)
    c_pf, a_pf = pf(comb), pf(anc)
    return {
        "variant_id": v.variant_id,
        "axis_changed": v.axis_changed,
        "diagnostic_only": v.diagnostic_only,
        "raw_track_rows": len(payload["raw"]),
        "canonical_rows": len(payload["canonical"]),
        "eligible_canonical_rows": len(payload["eligible"]),
        "prepared_tradable_rows": sum(x.get("trade_state") in {"RESOLVED", "PENDING_RESOLUTION"} and x.get("entry_dt") is not None for x in payload["prepared"]),
        "standalone_accepted_resolved_trades": stand["trades"],
        "standalone_win_rate": stand["win_rate"],
        "standalone_win_rate_wilson_low": stand["win_rate_wilson_low"],
        "standalone_win_rate_wilson_high": stand["win_rate_wilson_high"],
        "standalone_profit_factor": stand["spread_adjusted_profit_factor"],
        "standalone_total_r": stand["spread_adjusted_total_r"],
        "standalone_max_drawdown_r": stand["spread_adjusted_max_drawdown_r"],
        "standalone_largest_win_share": stand["largest_win_share_of_positive_pnl"],
        "standalone_2024_trades": s24["trades"], "standalone_2024_win_rate": s24["win_rate"], "standalone_2024_profit_factor": s24["spread_adjusted_profit_factor"], "standalone_2024_total_r": s24["spread_adjusted_total_r"],
        "standalone_2025_trades": s25["trades"], "standalone_2025_win_rate": s25["win_rate"], "standalone_2025_profit_factor": s25["spread_adjusted_profit_factor"], "standalone_2025_total_r": s25["spread_adjusted_total_r"],
        "exact_decision_overlap_with_anchor": overlap,
        "combined_accepted_resolved_trades": comb["trades"],
        "combined_win_rate": comb["win_rate"], "combined_win_rate_wilson_low": comb["win_rate_wilson_low"], "combined_win_rate_wilson_high": comb["win_rate_wilson_high"],
        "combined_profit_factor": comb["spread_adjusted_profit_factor"], "combined_total_r": comb["spread_adjusted_total_r"], "combined_max_drawdown_r": comb["spread_adjusted_max_drawdown_r"], "combined_largest_win_share": comb["largest_win_share_of_positive_pnl"],
        "incremental_accepted_resolved_trades": inc["trades"], "incremental_trade_days": len({pd.Timestamp(x["entry_dt"]).date() for x in incremental}),
        "incremental_win_rate": inc["win_rate"], "incremental_win_rate_wilson_low": inc["win_rate_wilson_low"], "incremental_win_rate_wilson_high": inc["win_rate_wilson_high"],
        "incremental_profit_factor": inc["spread_adjusted_profit_factor"], "incremental_total_r": inc["spread_adjusted_total_r"], "incremental_max_drawdown_r": inc["spread_adjusted_max_drawdown_r"],
        "incremental_2024_trades": i24["trades"], "incremental_2025_trades": i25["trades"],
        "combined_win_rate_delta_vs_anchor": comb["win_rate"] - anc["win_rate"],
        "combined_profit_factor_delta_vs_anchor": delta(c_pf, a_pf),
        "combined_total_r_delta_vs_anchor": comb["spread_adjusted_total_r"] - anc["spread_adjusted_total_r"],
        "combined_max_drawdown_r_delta_vs_anchor": comb["spread_adjusted_max_drawdown_r"] - anc["spread_adjusted_max_drawdown_r"],
        "combined_win_rate_no_drop": comb["win_rate"] >= anc["win_rate"] - TOL,
        "combined_win_rate_within_2pp": comb["win_rate"] >= anc["win_rate"] - 0.02 - TOL,
        "combined_profit_factor_no_drop": c_pf >= a_pf - TOL,
        "combined_total_r_increased": comb["spread_adjusted_total_r"] > anc["spread_adjusted_total_r"] + TOL,
        "combined_drawdown_increase_le_2r": comb["spread_adjusted_max_drawdown_r"] <= anc["spread_adjusted_max_drawdown_r"] + 2 + TOL,
        "sample_sufficient_incremental_20": inc["trades"] >= 20,
        "both_years_incremental_ge_5": i24["trades"] >= 5 and i25["trades"] >= 5,
        "research_priority_bucket": bucket(v, inc, comb, anc, i24, i25),
    }


def reason(v: Variant) -> str:
    return {
        "ATR_MIN_ONLY": "ANCHOR_FAILED_ONLY_BECAUSE_ATR_RATIO_WAS_BELOW_1P00_BUT_AT_LEAST_0P90",
        "ROUND_EXCLUSION_ONLY": "ANCHOR_FAILED_ONLY_BECAUSE_ROUND_NUMBER_NEAR_WAS_TRUE",
        "LANE_MEMBERSHIP_ONLY": "ANCHOR_FAILED_ONLY_BECAUSE_CANONICAL_SIGNAL_WAS_OUTSIDE_BALANCED_OR_PREMIUM",
        "DIRECTION_MIRROR": "DIAGNOSTIC_LONG_MIRROR_NOT_AN_ANCHOR_RELAXATION",
    }.get(v.axis_changed, v.axis_changed)


def context(rows: list[dict[str, Any]], variant_id: str, scope: str) -> list[dict[str, Any]]:
    if not rows:
        return []
    f = pd.DataFrame(rows).copy()
    f["decision_dt"] = pd.to_datetime(f.decision_dt)
    f["ATR_RATIO_BAND"] = pd.cut(pd.to_numeric(f.atr_ratio_signal), [-np.inf, .9, 1, 1.1, 1.45, np.inf], right=False, labels=["LT_0P90", "0P90_TO_LT_1P00", "1P00_TO_LT_1P10", "1P10_TO_LT_1P45", "GE_1P45"]).astype(str)
    f["DECISION_HOUR_MT5"] = f.decision_dt.dt.hour.astype(str).str.zfill(2)
    f["POOLED_TRACK_COUNT"] = f.pooled_track_count.astype(int).astype(str)
    f["POOLED_TRACK_COMBINATION"] = f.pooled_tracks.astype(str)
    f["ROUTER_GROUP"] = f.router_group.fillna("OUTSIDE_FIXED_LANE")
    out: list[dict[str, Any]] = []
    for dimension in ("ATR_RATIO_BAND", "DECISION_HOUR_MT5", "POOLED_TRACK_COUNT", "POOLED_TRACK_COMBINATION", "ROUTER_GROUP"):
        for name, group in f.groupby(dimension, sort=True):
            m = metrics(group.to_dict("records"))
            out.append({"variant_id": variant_id, "sample_scope": scope, "dimension": dimension, "bucket": str(name), "trades": m["trades"], "wins": m["wins"], "win_rate": m["win_rate"], "win_rate_wilson_low": m["win_rate_wilson_low"], "win_rate_wilson_high": m["win_rate_wilson_high"], "profit_factor": m["spread_adjusted_profit_factor"], "total_r": m["spread_adjusted_total_r"], "max_drawdown_r": m["spread_adjusted_max_drawdown_r"]})
    return out


def main() -> int:
    a = args()
    candle, watch_path = Path(a.candle_dir).resolve(), Path(a.stage329_watch).resolve()
    paths = {"result_json": Path(a.output).resolve(), "flow_csv": Path(a.flow_csv).resolve(), "variant_summary_csv": Path(a.variant_summary_csv).resolve(), "near_miss_csv": Path(a.near_miss_csv).resolve(), "incremental_trades_csv": Path(a.incremental_trades_csv).resolve(), "context_summary_csv": Path(a.context_summary_csv).resolve()}
    spec, watch = validate_inputs(watch_path)
    m1, m5, h4, signal_frame, pair = stage314.read_closed_context(candle, float(a.point_size))
    m1_dev = m1.loc[m1.close_time < END].copy()
    if m1_dev.empty:
        raise AuditError("DEVELOPMENT_M1_EMPTY")
    raw = raw_signals(signal_frame, pair)
    payloads, flow_rows = {}, []
    for v in VARIANTS:
        r, raw_flow = filtered(raw, v)
        c = canonical(r, v)
        e = eligible(c, v)
        p, port = portfolio(e, signal_frame, m1_dev, pair, float(a.point_size))
        payloads[v.variant_id] = {"variant": v, "raw": r, "canonical": c, "eligible": e, "prepared": p, "portfolio": port, "resolved": resolved(port)}
        flow_rows += flow(v, raw_flow, c, e, p, port)
    anchor = payloads[ANCHOR]
    anchor_rows, anchor_can = anchor["resolved"], anchor["eligible"]
    anchor_keys = {(pd.Timestamp(x["decision_dt"]), x["direction"]) for x in anchor_can}
    summaries, near, increments, contexts = [], [], [], context(anchor_rows, ANCHOR, "ANCHOR_ACCEPTED_RESOLVED")
    for v in VARIANTS:
        p = payloads[v.variant_id]
        if v.variant_id == ANCHOR:
            comb, inc, overlap = anchor_rows, [], len(anchor_keys)
        else:
            merged = [dict(x) for x in anchor_can] + [dict(x) for x in p["eligible"]]
            _, combined_port = portfolio(merged, signal_frame, m1_dev, pair, float(a.point_size))
            comb = resolved(combined_port)
            inc = [x for x in comb if x.get("variant_id") == v.variant_id]
            sibling_keys = {(pd.Timestamp(x["decision_dt"]), x["direction"]) for x in p["eligible"]}
            overlap = len(anchor_keys & sibling_keys)
            new_keys = sibling_keys - anchor_keys
            for x in combined_port:
                key = (pd.Timestamp(x["decision_dt"]), x["direction"])
                if x.get("variant_id") == v.variant_id and key in new_keys:
                    near.append({**x, "near_miss_reason": reason(v), "incremental_after_anchor_precedence": x.get("portfolio_status") == "ACCEPTED" and x.get("trade_state") == "RESOLVED"})
            increments += [dict(x) for x in inc]
            contexts += context(inc, v.variant_id, "INCREMENTAL_AFTER_ANCHOR_PRECEDENCE")
        summaries.append(summary(v, p, anchor_rows, comb, inc, overlap))
        contexts += context(p["resolved"], v.variant_id, "STANDALONE_ACCEPTED_RESOLVED")
    order = {"A_PROMISING_HUMAN_REVIEW_ONLY": 0, "B_MORE_SAMPLE_OR_MIXED_HUMAN_REVIEW_ONLY": 1, "C_WEAK_OR_INSUFFICIENT_NO_ACTION": 2, "DIAGNOSTIC_ONLY_NO_CANDIDATE_SELECTION": 3}
    review = sorted([x for x in summaries if x["variant_id"] != ANCHOR], key=lambda x: (order[x["research_priority_bucket"]], -x["incremental_accepted_resolved_trades"], x["variant_id"]))
    write_csv(paths["flow_csv"], flow_rows)
    write_csv(paths["variant_summary_csv"], summaries)
    write_csv(paths["near_miss_csv"], near)
    write_csv(paths["incremental_trades_csv"], increments)
    write_csv(paths["context_summary_csv"], contexts)
    decision = "HUMAN_REVIEW_PROMISING_SINGLE_AXIS_SIBLING_FOUND_NO_PROMOTION" if any(x["research_priority_bucket"] == "A_PROMISING_HUMAN_REVIEW_ONLY" for x in summaries) else "SCARCITY_DECOMPOSED_CONTINUE_RESEARCH_NO_PROMOTION"
    report = {
        "status": STATUS,
        "mode": "AUDIT_ONLY_HISTORICAL_2024_2025_SINGLE_AXIS_CANDIDATE_RESEARCH",
        "decision": decision,
        "research_spec": {"path": str(SPEC_PATH), "sha256": SPEC_SHA, "spec_id": spec["spec_id"], "status": spec["status"]},
        "fixed_research_contract": {"anchor_stage329_source_candidate": stage329.EXPECTED_SOURCE, "anchor_stage329_policy": stage329.EXPECTED_POLICY, "anchor_stage329_lane": stage329.EXPECTED_LANE, "anchor_stage329_cost_view": stage329.EXPECTED_COST_VIEW, "anchor_candidate_pool_preserved": True, "anchor_precedence_in_combined_portfolio": True, "one_position_before_any_incremental_measurement": True, "router_not_retrained_or_applied_in_research": True, "development_start_inclusive": str(START), "development_end_exclusive": str(END), "selection_years": list(YEARS), "year_2026_outcomes_used_for_selection": False, "closed_candles_only": True, "time_basis": "MT5 server time", "same_m1_tp_sl_priority": "SL", "rr": 1.5, "maximum_hold_minutes": int(pair.max_hold_minutes), "numeric_tolerance": TOL},
        "stage329_anchor_lineage": {"watch_path": str(watch_path), "watch_sha256": sha(watch_path), "watch_status": watch["status"], "watch_decision": watch.get("decision"), "contract_sha256": stage329.EXPECTED_CONTRACT_SHA256, "bootstrap_sha256": stage329.EXPECTED_BOOTSTRAP_SHA256, "bootstrap_internal_state_sha256": stage329.EXPECTED_BOOTSTRAP_STATE_SHA256, "stage329_integrity_pass": True, "stage329_files_written_or_mutated_this_run": False},
        "closed_data_coverage": {"m1_first_open_time": stage314.iso(m1.time.iloc[0]), "m1_latest_close_time": stage314.iso(m1.close_time.iloc[-1]), "m5_first_open_time": stage314.iso(m5.time.iloc[0]), "m5_latest_close_time": stage314.iso(m5.close_time.iloc[-1]), "h4_first_open_time": stage314.iso(h4.time.iloc[0]), "h4_latest_close_time": stage314.iso(h4.close_time.iloc[-1]), "development_m1_latest_close_used": stage314.iso(m1_dev.close_time.iloc[-1])},
        "anchor_scarcity_flow": [x for x in flow_rows if x["variant_id"] == ANCHOR],
        "anchor_resolved_metrics_2024_2025": metrics(anchor_rows),
        "variants": [asdict(v) for v in VARIANTS],
        "ordered_for_human_review_2024_2025_only": review,
        "counts": {"development_raw_pooled_track_rows": len(raw), "anchor_accepted_resolved_trades": len(anchor_rows), "near_miss_rows": len(near), "sum_of_per_variant_pure_incremental_resolved_rows": len(increments)},
        "outputs": {k: str(v) for k, v in paths.items()},
        "promotion": {"performed": False, "automatic_promotion": False, "stage329_contract_runtime_and_journal": "UNCHANGED", "stage328_contract_and_bootstrap": "UNCHANGED_FROZEN", "stage319_contract": "UNCHANGED_FROZEN", "stage314_contract": "UNCHANGED_ACTIVE", "stage307_candidate": "UNCHANGED_RETAINED", "stage292_candidate_pool_changed": False, "stage280_exact_recovery": "BLOCKED_UNCHANGED", "stage281_exact_model": "UNCHANGED"},
        "safety_flags": {"gold_v3_audit_only": True, "stage330_live_ready": False, "stage330_final_signal_emission_enabled": False, "candidate_pool_removal_performed": False, "stage329_state_update_performed": False, "stage329_journal_append_performed": False, "year_2026_result_selection_performed": False, "future_tp_sl_exit_horizon_leakage": False, "open_or_asof_candle_used": False, "jst_conversion_used": False, "mt5_order_enabled": False, "discord_enabled": False, "partial_close_enabled": False},
    }
    for k in ("flow_csv", "variant_summary_csv", "near_miss_csv", "incremental_trades_csv", "context_summary_csv"):
        report["outputs"][f"{k}_sha256"] = sha(paths[k])
    write_json(paths["result_json"], report)
    print(f"status: {STATUS}")
    print(f"decision: {decision}")
    print(f"development raw pooled track rows: {len(raw)}")
    print(f"anchor accepted resolved: {len(anchor_rows)}")
    print(f"near-miss rows: {len(near)}")
    print(f"result: {paths['result_json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
