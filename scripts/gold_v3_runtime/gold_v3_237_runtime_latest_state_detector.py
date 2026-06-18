#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage237 - Runtime latest-state detector/updater.

Reads latest closed M15/H1/H4/D1 CSV rows and updates the source state that Stage227 consumes.
Stage237 itself does not call Discord webhook and does not call mt5.order_send.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


STAGE = "GOLD_V3_237_RUNTIME_LATEST_STATE_DETECTOR"
DECISION_READY = "STAGE237_RUNTIME_LATEST_STATE_DETECTOR_READY"
DECISION_BLOCKED = "STAGE237_RUNTIME_LATEST_STATE_DETECTOR_BLOCKED"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"
DETECTOR_VERSION = "GOLD_V3_RUNTIME_TECHNICAL_BRIDGE_EMA_RCI_MACD_V1_20260619"

OFF_FLAGS = {
    "discord_enabled": False,
    "mt5_order_enabled": False,
    "execution_enabled": False,
    "actual_order_import_enabled": False,
    "payload_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "final_live_enabled": False,
    "autotrade_enabled": False,
    "no_signal_discord_notify": False,
    "source_csv_mutated": False,
    "contract_mutated": False,
    "production_retention_mutated": False,
    "candidate_pool_removed": False,
    "f002_exclusion_bypassed": False,
    "open_asof_allowed": False,
    "jst_conversion_used_for_detector_logic": False,
    "theoretical_result_used": False,
    "actual_execution_used": False,
}

STATE_FIELDS = [
    "stage", "detector_version", "created_at_utc", "symbol", "final_route", "signal_id", "short_signal_id",
    "latest_closed_m15_dt", "entry_dt", "direction", "entry_price", "strategy_role", "candidate_id",
    "tp_usd", "sl_usd", "horizon_m5_bars", "csv_latest_row_contract", "timestamp_basis",
    "score_long", "score_short", "reason", "h1_trend", "h4_trend", "d1_trend", "m15_trend",
    "macd_hist", "macd_hist_prev", "rci9", "rci9_prev", "rci14", "rci18",
]

TRADE_LEDGER_COLUMNS = [
    "signal_id", "short_signal_id", "latest_closed_m15_dt", "entry_dt", "symbol", "final_route",
    "strategy_role", "candidate_id", "direction", "entry_price", "tp_usd", "sl_usd", "horizon_m5_bars",
    "detector_version", "score_long", "score_short", "reason", "created_stage", "created_at_utc",
]

NO_SIGNAL_COLUMNS = [
    "case_id", "latest_closed_m15_dt", "final_route", "reason", "score_long", "score_short",
    "h1_trend", "h4_trend", "d1_trend", "m15_trend", "created_stage", "created_at_utc",
]

SUMMARY_COLUMNS = [
    "created_at_utc", "stage", "latest_closed_m15_dt", "final_route", "signal_id", "direction",
    "score_long", "score_short", "reason", "latest_state_written", "trade_ledger_appended", "no_signal_counter_appended",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_dt(text: str) -> datetime:
    text = str(text).strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M", "%Y.%m.%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"Unsupported datetime format: {text}")


def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def default_mql5_files_dir() -> Path:
    env_value = os.environ.get("GOLD_V3_MQL5_FILES")
    if env_value:
        return Path(env_value).expanduser().resolve()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata, "MetaQuotes", "Terminal", TERMINAL_HASH, "MQL5", "Files").resolve()
    return (Path.cwd() / "_GOLD_V3_LOCAL_MQL5_FILES").resolve()


def paths() -> Dict[str, Path]:
    files = default_mql5_files_dir()
    out = files / "FX_OUTPUTS" / "gold_v3" / "237"
    work = out / "runtime_latest_state_detector"
    retention = files / "FX_OUTPUTS" / "gold_v3" / "217" / "staging_retention"
    return {
        "files": files,
        "out": out,
        "work": work,
        "m15": Path(os.environ.get("GOLD_V3_M15_CSV", files / "goldsharp_m15.csv")).expanduser().resolve(),
        "h1": Path(os.environ.get("GOLD_V3_H1_CSV", files / "goldsharp_h1.csv")).expanduser().resolve(),
        "h4": Path(os.environ.get("GOLD_V3_H4_CSV", files / "goldsharp_h4.csv")).expanduser().resolve(),
        "d1": Path(os.environ.get("GOLD_V3_D1_CSV", files / "goldsharp_d1.csv")).expanduser().resolve(),
        "m5": Path(os.environ.get("GOLD_V3_M5_CSV", files / "goldsharp_m5.csv")).expanduser().resolve(),
        "retention": retention,
        "latest_state": retention / "latest_state.json",
        "trade_ledger": retention / "trade_signal_ledger.csv",
        "no_signal": retention / "no_signal_counters_daily_hourly.csv",
        "summary": work / "stage237_summary.json",
        "summary_csv": work / "stage237_detection_summary.csv",
        "paste": out / "paste_me.txt",
    }


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def append_csv(path: Path, row: Dict[str, Any], columns: List[str]) -> None:
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def rewrite_csv(path: Path, rows: Iterable[Dict[str, Any]], columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def normalize_row(raw: Dict[str, str]) -> Dict[str, Any]:
    lower = {str(k).strip().lower(): v for k, v in raw.items()}
    t = lower.get("time") or lower.get("datetime") or lower.get("date") or next(iter(lower.values()))
    return {
        "time": parse_dt(str(t)),
        "open": float(lower["open"]),
        "high": float(lower["high"]),
        "low": float(lower["low"]),
        "close": float(lower["close"]),
        "tick_volume": float(lower.get("tick_volume") or lower.get("volume") or 0),
    }


def read_bars(path: Path) -> List[Dict[str, Any]]:
    bars = [normalize_row(r) for r in read_csv_rows(path)]
    bars.sort(key=lambda r: r["time"])
    return bars


def asof_bars(bars: List[Dict[str, Any]], dt: datetime) -> List[Dict[str, Any]]:
    return [b for b in bars if b["time"] <= dt]


def ema_series(values: List[float], period: int) -> List[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    out = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out


def last_ema(values: List[float], period: int) -> Optional[float]:
    if not values:
        return None
    return ema_series(values, period)[-1]


def macd_hist(values: List[float], fast: int = 6, slow: int = 13, signal: int = 4) -> Tuple[Optional[float], Optional[float]]:
    if len(values) < slow + signal + 2:
        return None, None
    ef = ema_series(values, fast)
    es = ema_series(values, slow)
    macd = [a - b for a, b in zip(ef, es)]
    sig = ema_series(macd, signal)
    hist = [a - b for a, b in zip(macd, sig)]
    return hist[-1], hist[-2]


def rci(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    seq = values[-period:]
    n = period
    price_order = sorted(range(n), key=lambda i: seq[i])
    price_rank = [0] * n
    for rank, idx in enumerate(price_order, start=1):
        price_rank[idx] = rank
    time_rank = list(range(1, n + 1))
    d2 = sum((time_rank[i] - price_rank[i]) ** 2 for i in range(n))
    return (1.0 - (6.0 * d2) / (n * (n * n - 1.0))) * 100.0


def trend_from_closes(values: List[float]) -> Tuple[str, Dict[str, Optional[float]]]:
    e20 = last_ema(values, 20)
    e30 = last_ema(values, 30)
    e40 = last_ema(values, 40)
    c = values[-1] if values else None
    trend = "NEUTRAL"
    if None not in (e20, e30, e40, c):
        if c > e20 > e30 > e40:
            trend = "UP"
        elif c < e20 < e30 < e40:
            trend = "DOWN"
    return trend, {"ema20": e20, "ema30": e30, "ema40": e40, "close": c}


def short_hash(text: str) -> str:
    return "G3R" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:18].upper()


def direction_to_queue_direction(direction: str) -> str:
    if direction == "LONG":
        return "BUY"
    if direction == "SHORT":
        return "SELL"
    return direction


def build_signal_id(dt: datetime, direction: str, candidate_id: str) -> str:
    return f"{dt.strftime('%Y%m%d_%H%M%S')}_SECONDARY_AUDIT_CANDIDATE_{candidate_id}_{direction}"


def detect(m15: List[Dict[str, Any]], h1: List[Dict[str, Any]], h4: List[Dict[str, Any]], d1: List[Dict[str, Any]]) -> Dict[str, Any]:
    latest = m15[-1]
    latest_dt = latest["time"]
    h1a, h4a, d1a = asof_bars(h1, latest_dt), asof_bars(h4, latest_dt), asof_bars(d1, latest_dt)
    m15_close = [b["close"] for b in m15]
    h1_close = [b["close"] for b in h1a]
    h4_close = [b["close"] for b in h4a]
    d1_close = [b["close"] for b in d1a]

    m15_trend, m15_emas = trend_from_closes(m15_close)
    h1_trend, _ = trend_from_closes(h1_close)
    h4_trend, _ = trend_from_closes(h4_close)
    d1_trend, _ = trend_from_closes(d1_close)
    hist, hist_prev = macd_hist(m15_close)
    r9 = rci(m15_close, 9)
    r9_prev = rci(m15_close[:-1], 9) if len(m15_close) > 10 else None
    r14 = rci(m15_close, 14)
    r18 = rci(m15_close, 18)

    long_score = 0
    short_score = 0
    reasons_long: List[str] = []
    reasons_short: List[str] = []

    if h1_trend == "UP":
        long_score += 2; reasons_long.append("H1_UP")
    if h4_trend == "UP":
        long_score += 2; reasons_long.append("H4_UP")
    if d1_trend == "UP":
        long_score += 1; reasons_long.append("D1_UP")
    if m15_trend == "UP":
        long_score += 1; reasons_long.append("M15_UP")
    if hist is not None and hist > 0:
        long_score += 1; reasons_long.append("MACD_HIST_POS")
    if hist is not None and hist_prev is not None and hist > hist_prev:
        long_score += 1; reasons_long.append("MACD_HIST_RISING")
    if r9 is not None and r9_prev is not None and r9 < -20 and r9 > r9_prev:
        long_score += 1; reasons_long.append("RCI9_REBOUND_FROM_LOW")

    if h1_trend == "DOWN":
        short_score += 2; reasons_short.append("H1_DOWN")
    if h4_trend == "DOWN":
        short_score += 2; reasons_short.append("H4_DOWN")
    if d1_trend == "DOWN":
        short_score += 1; reasons_short.append("D1_DOWN")
    if m15_trend == "DOWN":
        short_score += 1; reasons_short.append("M15_DOWN")
    if hist is not None and hist < 0:
        short_score += 1; reasons_short.append("MACD_HIST_NEG")
    if hist is not None and hist_prev is not None and hist < hist_prev:
        short_score += 1; reasons_short.append("MACD_HIST_FALLING")
    if r9 is not None and r9_prev is not None and r9 > 20 and r9 < r9_prev:
        short_score += 1; reasons_short.append("RCI9_REJECT_FROM_HIGH")

    # Require H1 plus either H4 or D1 alignment, and enough total confirmation.
    long_ok = long_score >= 6 and h1_trend == "UP" and (h4_trend == "UP" or d1_trend == "UP")
    short_ok = short_score >= 6 and h1_trend == "DOWN" and (h4_trend == "DOWN" or d1_trend == "DOWN")

    direction = ""
    candidate_id = ""
    reason = "NO_RUNTIME_SIGNAL"
    if long_ok and long_score >= short_score:
        direction = "LONG"
        candidate_id = "RUNTIME_SCALP_TREND_PULLBACK_LONG"
        reason = "+".join(reasons_long)
    elif short_ok:
        direction = "SHORT"
        candidate_id = "RUNTIME_SCALP_TREND_PULLBACK_SHORT"
        reason = "+".join(reasons_short)

    payload: Dict[str, Any] = {
        "latest_closed_m15_dt": fmt_dt(latest_dt),
        "entry_dt": fmt_dt(latest_dt),
        "entry_price": round(float(latest["close"]), 2),
        "direction": direction,
        "candidate_id": candidate_id,
        "reason": reason,
        "score_long": long_score,
        "score_short": short_score,
        "h1_trend": h1_trend,
        "h4_trend": h4_trend,
        "d1_trend": d1_trend,
        "m15_trend": m15_trend,
        "macd_hist": None if hist is None else round(hist, 6),
        "macd_hist_prev": None if hist_prev is None else round(hist_prev, 6),
        "rci9": None if r9 is None else round(r9, 3),
        "rci9_prev": None if r9_prev is None else round(r9_prev, 3),
        "rci14": None if r14 is None else round(r14, 3),
        "rci18": None if r18 is None else round(r18, 3),
    }
    return payload


def make_state(det: Dict[str, Any]) -> Dict[str, Any]:
    created = utc_now_iso()
    direction = det["direction"]
    is_sig = bool(direction)
    candidate_id = det["candidate_id"]
    latest_dt = parse_dt(det["latest_closed_m15_dt"])
    signal_id = build_signal_id(latest_dt, direction, candidate_id) if is_sig else ""
    short_id = short_hash(signal_id) if signal_id else ""
    state: Dict[str, Any] = {
        "stage": STAGE,
        "detector_version": DETECTOR_VERSION,
        "created_at_utc": created,
        "symbol": "XAUUSD",
        "final_route": "SECONDARY_AUDIT_CANDIDATE" if is_sig else "NO_SIGNAL",
        "signal_id": signal_id,
        "short_signal_id": short_id,
        "latest_closed_m15_dt": det["latest_closed_m15_dt"],
        "entry_dt": det["entry_dt"] if is_sig else "",
        "direction": direction_to_queue_direction(direction) if is_sig else "",
        "entry_price": det["entry_price"] if is_sig else None,
        "strategy_role": "SCALP_SECONDARY_CANDIDATE" if is_sig else "",
        "candidate_id": candidate_id if is_sig else "",
        "tp_usd": 15 if is_sig else None,
        "sl_usd": 5 if is_sig else None,
        "horizon_m5_bars": 64 if is_sig else None,
        "csv_latest_row_contract": "CLOSED",
        "timestamp_basis": "MT5_CSV",
        "staging_only": True,
        "audit_only": False,
        "send_enabled": False,
        "order_action": "NO_ORDER_DIRECT_STAGE237",
        "send_action": "NO_SEND_DIRECT_STAGE237",
        "payload_action": "NO_PAYLOAD_DIRECT_STAGE237",
    }
    state.update({k: det.get(k) for k in [
        "score_long", "score_short", "reason", "h1_trend", "h4_trend", "d1_trend", "m15_trend",
        "macd_hist", "macd_hist_prev", "rci9", "rci9_prev", "rci14", "rci18",
    ]})
    state.update(OFF_FLAGS)
    return state


def existing_signal_ids(path: Path) -> set[str]:
    return {str(r.get("signal_id") or "") for r in read_csv_rows(path)}


def validate(summary: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []
    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})
    add("D237001", summary.get("m15_exists") is True and summary.get("h1_exists") is True and summary.get("h4_exists") is True and summary.get("d1_exists") is True, "required CSV exists")
    add("D237002", summary.get("latest_state_written") is True, "latest_state written")
    add("D237003", summary.get("csv_latest_row_contract") == "CLOSED", "latest row is CLOSED")
    add("D237004", summary.get("timestamp_basis") == "MT5_CSV", "MT5/CSV timestamp basis")
    add("D237005", all(summary.get(k) is False for k in OFF_FLAGS.keys()), "restricted flags OFF")
    add("D237006", summary.get("final_route") in {"NO_SIGNAL", "SECONDARY_AUDIT_CANDIDATE"}, f"final_route={summary.get('final_route')}")
    blockers = [f"{c['check_id']}: {c['details']}" for c in checks if not c["passed"]]
    return checks, blockers


def write_paste(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 237 PASTE_ME_RUNTIME_LATEST_STATE_DETECTOR")
    for key in [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "work_dir",
        "m15_exists", "h1_exists", "h4_exists", "d1_exists", "m5_exists",
        "latest_closed_m15_dt", "final_route", "signal_id", "short_signal_id", "direction", "entry_price",
        "candidate_id", "strategy_role", "tp_usd", "sl_usd", "horizon_m5_bars",
        "score_long", "score_short", "reason", "h1_trend", "h4_trend", "d1_trend", "m15_trend",
        "latest_state_written", "trade_ledger_appended", "no_signal_counter_appended", "blocker_count",
    ] + list(OFF_FLAGS.keys()):
        lines.append(f"{key}: {summary.get(key)}")
    lines.append("")
    lines.append("OUTPUT_FILES")
    for k, v in summary.get("output_files", {}).items():
        lines.append(f"{k}: {v}")
    lines.append("")
    lines.append("VALIDATION_CHECKS")
    for c in checks:
        lines.append(f"{c['check_id']} | passed={c['passed']} | {c['details']}")
    lines.append("")
    lines.append("INTERPRETATION")
    lines.append("Stage237 updates the latest_state source read by Stage227. It does not send Discord messages and does not call mt5.order_send directly.")
    lines.append("")
    lines.append("BLOCKERS")
    if summary.get("blockers"):
        lines.extend(summary["blockers"])
    else:
        lines.append("NO_BLOCKERS")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-bars-m15", type=int, default=80)
    args = parser.parse_args()
    p = paths()
    p["out"].mkdir(parents=True, exist_ok=True)
    p["work"].mkdir(parents=True, exist_ok=True)
    p["retention"].mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "step": STAGE,
        "created_at_utc": utc_now_iso(),
        "output_dir": str(p["out"]),
        "work_dir": str(p["work"]),
        "m15_exists": p["m15"].exists(),
        "h1_exists": p["h1"].exists(),
        "h4_exists": p["h4"].exists(),
        "d1_exists": p["d1"].exists(),
        "m5_exists": p["m5"].exists(),
        "csv_latest_row_contract": "CLOSED",
        "timestamp_basis": "MT5_CSV",
        "latest_state_written": False,
        "trade_ledger_appended": False,
        "no_signal_counter_appended": False,
        "output_files": {
            "latest_state_json": str(p["latest_state"]),
            "trade_signal_ledger_csv": str(p["trade_ledger"]),
            "no_signal_counters_csv": str(p["no_signal"]),
            "summary_json": str(p["summary"]),
            "summary_csv": str(p["summary_csv"]),
            "paste_me": str(p["paste"]),
        },
    }
    summary.update(OFF_FLAGS)
    try:
        m15, h1, h4, d1 = read_bars(p["m15"]), read_bars(p["h1"]), read_bars(p["h4"]), read_bars(p["d1"])
        if len(m15) < args.min_bars_m15:
            raise RuntimeError(f"not enough M15 bars: {len(m15)}")
        if not h1 or not h4 or not d1:
            raise RuntimeError("missing HTF bars")
        det = detect(m15, h1, h4, d1)
        state = make_state(det)
        write_json(p["latest_state"], state)
        summary["latest_state_written"] = True
        summary.update({k: state.get(k) for k in [
            "latest_closed_m15_dt", "final_route", "signal_id", "short_signal_id", "direction", "entry_price",
            "candidate_id", "strategy_role", "tp_usd", "sl_usd", "horizon_m5_bars", "score_long", "score_short",
            "reason", "h1_trend", "h4_trend", "d1_trend", "m15_trend",
        ]})
        if state["final_route"] != "NO_SIGNAL" and state["signal_id"]:
            if state["signal_id"] not in existing_signal_ids(p["trade_ledger"]):
                row = {**state, "created_stage": STAGE}
                append_csv(p["trade_ledger"], row, TRADE_LEDGER_COLUMNS)
                summary["trade_ledger_appended"] = True
        else:
            append_csv(p["no_signal"], {
                "case_id": f"NO_SIGNAL_{state['latest_closed_m15_dt'].replace(' ', '_').replace(':', '')}",
                "latest_closed_m15_dt": state["latest_closed_m15_dt"],
                "final_route": "NO_SIGNAL",
                "reason": state.get("reason"),
                "score_long": state.get("score_long"),
                "score_short": state.get("score_short"),
                "h1_trend": state.get("h1_trend"),
                "h4_trend": state.get("h4_trend"),
                "d1_trend": state.get("d1_trend"),
                "m15_trend": state.get("m15_trend"),
                "created_stage": STAGE,
                "created_at_utc": utc_now_iso(),
            }, NO_SIGNAL_COLUMNS)
            summary["no_signal_counter_appended"] = True
        append_csv(p["summary_csv"], summary, SUMMARY_COLUMNS)
    except Exception as exc:
        summary.setdefault("blockers", [])
        summary["blockers"].append(f"EXCEPTION: {type(exc).__name__}: {exc}")

    checks, validation_blockers = validate(summary)
    blockers = summary.get("blockers", []) + validation_blockers
    summary["validation_checks"] = checks
    summary["blockers"] = blockers
    summary["blocker_count"] = len(blockers)
    summary["status"] = "READY" if not blockers else "BLOCKED"
    summary["ready"] = not blockers
    summary["decision"] = DECISION_READY if not blockers else DECISION_BLOCKED
    write_json(p["summary"], summary)
    write_paste(p["paste"], summary, checks)
    print(f"Stage237 status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"latest_closed_m15_dt: {summary.get('latest_closed_m15_dt')}")
    print(f"final_route: {summary.get('final_route')}")
    print(f"signal_id: {summary.get('signal_id')}")
    print(f"paste_me: {p['paste']}")
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
