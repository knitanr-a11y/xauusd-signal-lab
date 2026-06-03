#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 live rule evaluation audit gate.

This is the first live-rule evaluation gate after the latest-candle and feature
snapshot probes.

Non-negotiable safety behavior:
  * No Discord notification is sent.
  * No MT5 order is placed.
  * No AI API is called.
  * No live hook is enabled.
  * NO_SIGNAL never produces a notification message.

Non-negotiable correctness behavior:
  * CoreA/CoreB must not be approximated from historical ledgers.
  * If frozen CoreA/CoreB rule definition files are not present, CoreA/CoreB are
    marked RULE_SOURCE_MISSING and the final output cannot be SIGNAL.
  * MEDIUM feature gates may be evaluated, but they remain blocked until
    CoreA/CoreB arbitration is connected, because MEDIUM is subordinate to HIGH.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd


PIPS_TO_PRICE_DEFAULT = 0.1
VARIANT_RE = re.compile(r"^(BUY|SELL)_TP(?P<tp>[0-9.]+)_SL(?P<sl>[0-9.]+)_RR", re.IGNORECASE)

COREA_FROZEN_DEFAULT = "configs/gold_v2/frozen_coreA_fold4_ABC_CAP5_rules_20260603.json"
COREB_FROZEN_DEFAULT = "configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json"
MEDIUM_FROZEN_DEFAULT = "configs/gold_v2/frozen_medium_rules_20260603.json"

MEDIUM_RULES = [
    {
        "name": "RANGE96_REFINED",
        "direction": "SELL",
        "conditions": {"range96_min": 129.6835, "trend_eff96_max": 0.355591},
        "lot_multiplier_candidate": 0.5,
    },
    {
        "name": "VOL_TRMEAN32_REFINED",
        "direction": "PROBE",
        "conditions": {"tr_mean_32_min": 10.867578, "ret96_max": -2.725, "range96_min": 176.453},
        "lot_multiplier_candidate": 0.5,
    },
    {
        "name": "TIER2_HVT",
        "direction": "PROBE",
        "conditions": {"trend_eff96_max": 0.4, "ret96_max": -25.0, "tr_mean_32_min": 10.867578},
        "lot_multiplier_candidate": 0.5,
    },
]


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate GOLD V2 live rules in audit-only mode")
    p.add_argument("--candles-m15", default=None)
    p.add_argument("--eval-time", default=None)
    p.add_argument("--dataset", default="2026")
    p.add_argument("--output-dir", default=None)
    p.add_argument("--corea-rules", default=COREA_FROZEN_DEFAULT)
    p.add_argument("--coreb-rules", default=COREB_FROZEN_DEFAULT)
    p.add_argument("--medium-rules", default=MEDIUM_FROZEN_DEFAULT)
    p.add_argument("--pips-to-price", type=float, default=PIPS_TO_PRICE_DEFAULT)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    if len(root.parents) >= 2:
        return root.parents[1]
    return root.parent


def default_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_live_rule_evaluation_audit_only"


def resolve_path(text: str) -> Path:
    p = Path(text)
    if p.is_absolute():
        return p
    return (repo_root() / p).resolve()


def find_default_m15_csv() -> Optional[Path]:
    base = files_dir_from_repo()
    candidates = [
        base / "gold#_m15.csv",
        base / "goldsharp_m15.csv",
        base / "candles_history_M15.csv",
        base / "FX_OUTPUTS" / "gold#_m15.csv",
        base / "FX_OUTPUTS" / "goldsharp_m15.csv",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def detect_col(columns: Sequence[str], names: Sequence[str]) -> Optional[str]:
    lower = {str(c).lower(): c for c in columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None


def detect_time_col(columns: Sequence[str]) -> Optional[str]:
    return detect_col(columns, ["time", "datetime", "date", "open_time", "timestamp", "gmt time", "time_open"]) or (columns[0] if columns else None)


def read_candles(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, sep=None, engine="python")
    except Exception:
        df = pd.read_csv(path)
    cols = list(df.columns)
    time_col = detect_time_col(cols)
    open_col = detect_col(cols, ["open", "bidopen", "bid_open"])
    high_col = detect_col(cols, ["high", "bidhigh", "bid_high"])
    low_col = detect_col(cols, ["low", "bidlow", "bid_low"])
    close_col = detect_col(cols, ["close", "bidclose", "bid_close"])
    missing = [name for name, col in {"time": time_col, "open": open_col, "high": high_col, "low": low_col, "close": close_col}.items() if col is None]
    if missing:
        raise ValueError(f"Missing candle columns {missing}. columns={cols}")
    out = pd.DataFrame({
        "time": pd.to_datetime(df[time_col], errors="coerce"),
        "open": pd.to_numeric(df[open_col], errors="coerce"),
        "high": pd.to_numeric(df[high_col], errors="coerce"),
        "low": pd.to_numeric(df[low_col], errors="coerce"),
        "close": pd.to_numeric(df[close_col], errors="coerce"),
    })
    out = out.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").reset_index(drop=True)
    if out.empty:
        raise ValueError("No valid candle rows")
    return out


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    prev_close = out["close"].shift(1)
    tr1 = out["high"] - out["low"]
    tr2 = (out["high"] - prev_close).abs()
    tr3 = (out["low"] - prev_close).abs()
    out["tr"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    out["tr_mean_32"] = out["tr"].rolling(32, min_periods=32).mean()
    out["ret96"] = out["close"] - out["close"].shift(96)
    out["range96"] = out["high"].rolling(96, min_periods=96).max() - out["low"].rolling(96, min_periods=96).min()
    out["trend_eff96"] = (out["ret96"].abs() / out["range96"].replace(0, pd.NA)).astype("float64")
    out["ret32"] = out["close"] - out["close"].shift(32)
    out["range32"] = out["high"].rolling(32, min_periods=32).max() - out["low"].rolling(32, min_periods=32).min()
    out["body"] = (out["close"] - out["open"]).abs()
    out["direction_bar"] = out.apply(lambda r: "BUY" if r["close"] > r["open"] else ("SELL" if r["close"] < r["open"] else "FLAT"), axis=1)
    return out


def normalize_ts(value: Any) -> Optional[pd.Timestamp]:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts).tz_localize(None) if getattr(ts, "tzinfo", None) is not None else pd.Timestamp(ts)


def row_to_snapshot(row: pd.Series) -> Dict[str, Any]:
    snap: Dict[str, Any] = {"time": pd.Timestamp(row["time"]).strftime("%Y-%m-%d %H:%M:%S")}
    for k in ["open", "high", "low", "close", "tr", "tr_mean_32", "ret96", "range96", "trend_eff96", "ret32", "range32", "body", "direction_bar"]:
        v = row.get(k)
        if isinstance(v, (int, float)) and not pd.isna(v):
            snap[k] = float(v)
        elif pd.isna(v):
            snap[k] = None
        else:
            snap[k] = v
    return snap


def as_float(value: Any) -> Optional[float]:
    try:
        v = float(value)
    except Exception:
        return None
    if math.isnan(v):
        return None
    return v


def check_condition(snapshot: Dict[str, Any], field: str, op: str, expected: float) -> bool:
    actual = as_float(snapshot.get(field))
    if actual is None:
        return False
    if op == "min":
        return actual >= expected
    if op == "max":
        return actual <= expected
    raise ValueError(op)


def evaluate_medium_rule(snapshot: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
    checks: Dict[str, bool] = {}
    cond = rule["conditions"]
    for key, expected in cond.items():
        if key.endswith("_min"):
            field = key[:-4]
            checks[key] = check_condition(snapshot, field, "min", float(expected))
        elif key.endswith("_max"):
            field = key[:-4]
            checks[key] = check_condition(snapshot, field, "max", float(expected))
    return {
        "rule_name": rule["name"],
        "direction": rule.get("direction"),
        "feature_gate_hit": all(checks.values()) if checks else False,
        "checks": checks,
        "conditions": cond,
        "lot_multiplier_candidate": rule.get("lot_multiplier_candidate"),
        "signal_eligible": False,
        "blocked_reason": "CoreA/CoreB arbitration is not connected in this audit gate.",
    }


def load_optional_json(path: Path) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    if not path.exists():
        return False, None, f"missing: {path}"
    try:
        return True, json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return False, None, f"invalid json: {path}: {exc}"


def evaluate_core_stub(name: str, path: Path) -> Dict[str, Any]:
    ok, data, error = load_optional_json(path)
    if not ok:
        return {
            "component": name,
            "status": "RULE_SOURCE_MISSING",
            "signal_eligible": False,
            "blocked_reason": error,
        }
    return {
        "component": name,
        "status": "RULE_SOURCE_PRESENT_BUT_EVALUATOR_NOT_IMPLEMENTED",
        "signal_eligible": False,
        "rule_source": data.get("policy_id") or str(path),
        "blocked_reason": "Frozen rule source is present, but evaluator mapping has not been implemented yet.",
    }


def format_price(value: Any) -> str:
    v = as_float(value)
    if v is None:
        return "-"
    return f"{v:.2f}"


def render_notification_for_signal(signal: Dict[str, Any]) -> str:
    # Currently unreachable unless a future evaluator marks signal_eligible=True.
    direction = signal.get("direction", "")
    icon = "🟢" if direction == "BUY" else ("🔴" if direction == "SELL" else "⚪")
    return "\n".join([
        f"【GOLD】{icon} {direction}｜{signal.get('priority', '-')}",
        "━━━━━━━━━━━━━━━━━━━━",
        f"時刻: {signal.get('entry_time', '-')}",
        f"エントリー: {format_price(signal.get('entry_price'))}",
        f"TP: {format_price(signal.get('tp_price'))}",
        f"SL: {format_price(signal.get('sl_price'))}",
        f"種別: {signal.get('component', '-')}",
        f"根拠: {signal.get('reason', '-')}",
        f"ロット候補: {signal.get('lot_multiplier_candidate', '-')}",
        "",
        "状態: AUDIT ONLY（外部送信なし）",
    ])


def build_report(packet: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# GOLD V2 live rule evaluation audit-only report")
    lines.append("")
    lines.append(f"Created UTC: {packet['created_utc']}")
    lines.append(f"Status: {packet['status']}")
    lines.append(f"Dataset: {packet['dataset']}")
    lines.append(f"Eval time: {packet['eval_time']}")
    lines.append("")
    lines.append("## Final decision")
    lines.append("")
    lines.append(f"- final_signal_status: `{packet['final_signal_status']}`")
    lines.append(f"- notification_should_send: `{packet['notification_should_send']}`")
    lines.append(f"- mt5_order_allowed: `{packet['external_actions']['mt5_order_allowed']}`")
    lines.append("")
    lines.append("## Core evaluators")
    lines.append("")
    for item in packet["core_evaluators"]:
        lines.append(f"### {item['component']}")
        lines.append(f"- status: `{item['status']}`")
        lines.append(f"- signal_eligible: `{item['signal_eligible']}`")
        lines.append(f"- blocked_reason: {item.get('blocked_reason', '-')}")
        lines.append("")
    lines.append("## MEDIUM feature gates")
    lines.append("")
    for item in packet["medium_evaluators"]:
        lines.append(f"### {item['rule_name']}")
        lines.append(f"- feature_gate_hit: `{item['feature_gate_hit']}`")
        lines.append(f"- signal_eligible: `{item['signal_eligible']}`")
        lines.append(f"- blocked_reason: {item['blocked_reason']}")
        lines.append("- checks:")
        for ck, cv in item["checks"].items():
            lines.append(f"  - {ck}: `{cv}`")
        lines.append("")
    lines.append("## Snapshot")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(packet["snapshot"], ensure_ascii=False, indent=2, allow_nan=False))
    lines.append("```")
    lines.append("")
    lines.append("No external notification or order execution is performed.")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    candle_path = Path(args.candles_m15).expanduser().resolve() if args.candles_m15 else find_default_m15_csv()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    if candle_path is None or not candle_path.exists():
        print("[ERROR] M15 candle CSV not found. Use --candles-m15.")
        return 2
    candles = read_candles(candle_path)
    features = compute_features(candles)
    if args.eval_time:
        ts = normalize_ts(args.eval_time)
        if ts is None:
            print(f"[ERROR] invalid --eval-time: {args.eval_time}")
            return 2
        row_df = features[features["time"] == ts]
        if row_df.empty:
            print(f"[ERROR] eval time not found in candles: {args.eval_time}")
            return 2
        row = row_df.iloc[-1]
    else:
        row = features.iloc[-1]
    snapshot = row_to_snapshot(row)
    eval_time = snapshot["time"]

    core_evals = [
        evaluate_core_stub("HIGH_A_CoreA_fold4_ABC_CAP5", resolve_path(args.corea_rules)),
        evaluate_core_stub("HIGH_B_CoreB_RR125_BUY_CONFLUENCE", resolve_path(args.coreb_rules)),
    ]
    medium_evals = [evaluate_medium_rule(snapshot, r) for r in MEDIUM_RULES]

    eligible_core = [x for x in core_evals if x.get("signal_eligible")]
    eligible_medium = [x for x in medium_evals if x.get("signal_eligible")]
    final_signals = eligible_core + eligible_medium
    if final_signals:
        final_status = "SIGNAL"
        notification_should_send = False  # audit-only still blocks actual send
        notification_preview_text = render_notification_for_signal(final_signals[0])
    else:
        final_status = "NO_SIGNAL"
        notification_should_send = False
        notification_preview_text = ""

    packet = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "AUDIT_ONLY_LIVE_RULE_EVALUATION",
        "dataset": str(args.dataset),
        "eval_time": eval_time,
        "candle_path": str(candle_path),
        "audit_only": True,
        "external_actions": {
            "discord_send_allowed": False,
            "mt5_order_allowed": False,
            "ai_api_allowed": False,
            "live_hook_allowed": False,
        },
        "final_signal_status": final_status,
        "notification_should_send": notification_should_send,
        "notification_preview_text": notification_preview_text,
        "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL",
        "snapshot": snapshot,
        "core_evaluators": core_evals,
        "medium_evaluators": medium_evals,
        "important_note": "CoreA/CoreB are blocked unless frozen rule definition files and evaluator mappings are explicitly connected. No approximate reimplementation is allowed.",
    }

    out_json = output_dir / "gold_v2_live_rule_evaluation_packet.json"
    out_report = output_dir / "GOLD_V2_LIVE_RULE_EVALUATION_AUDIT_ONLY_REPORT.md"
    out_notification = output_dir / "gold_v2_live_rule_notification_preview.txt"
    out_medium = output_dir / "gold_v2_live_rule_medium_eval.csv"
    out_core = output_dir / "gold_v2_live_rule_core_eval.csv"
    out_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    out_report.write_text(build_report(packet), encoding="utf-8")
    out_notification.write_text(notification_preview_text, encoding="utf-8")
    pd.DataFrame(medium_evals).to_csv(out_medium, index=False, encoding="utf-8-sig")
    pd.DataFrame(core_evals).to_csv(out_core, index=False, encoding="utf-8-sig")

    print(f"[DONE] final_signal_status={final_status} output_dir={output_dir}")
    if notification_preview_text:
        print(notification_preview_text)
    else:
        print("NO_SIGNAL: Discord notification preview is intentionally empty.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
