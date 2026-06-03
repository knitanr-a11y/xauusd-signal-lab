#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build GOLD latest-candle candidate packet from audited runtime candidates.

This is an audit-only bridge. It does not regenerate CoreA/CoreB/MEDIUM rules
from raw candles yet. It filters the audited runtime candidate table by the
latest M15 candle timestamp or by an explicitly supplied --eval-time.

Outputs NO_SIGNAL when no audited candidate matches the evaluated candle time.
No external notification, order execution, AI API, or live hook is called.
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
PRIORITY_ORDER = {
    "HIGH_CONFLUENCE": 0,
    "HIGH_A": 1,
    "HIGH_B": 2,
    "MEDIUM": 3,
}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build GOLD latest-candle candidate packet from audited candidates")
    parser.add_argument("--candidate-csv", default=None)
    parser.add_argument("--candles-m15", default=None)
    parser.add_argument("--eval-time", default=None, help="Explicit eval time, e.g. 2026-06-02 01:15:00. Overrides latest candle time.")
    parser.add_argument("--dataset", default="2026")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--symbol", default="GOLD")
    parser.add_argument("--pips-to-price", type=float, default=PIPS_TO_PRICE_DEFAULT)
    return parser.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    if len(root.parents) >= 2:
        return root.parents[1]
    return root.parent


def default_candidate_csv() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_runtime_signal_candidates_audit_only" / "gold_v2_runtime_signal_candidates.csv"


def default_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_latest_candle_candidate_audit_only"


def default_core_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_ABC_stack_cap_2025_2026_validation_outputs"


def find_default_m15_csv() -> Optional[Path]:
    base = files_dir_from_repo()
    candidates = [
        base / "gold#_m15.csv",
        base / "goldsharp_m15.csv",
        base / "candles_history_M15.csv",
        base / "FX_OUTPUTS" / "gold#_m15.csv",
        base / "FX_OUTPUTS" / "goldsharp_m15.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def detect_time_col(columns: Sequence[str]) -> Optional[str]:
    lowered = {str(c).lower(): c for c in columns}
    for name in ["time", "datetime", "date", "open_time", "timestamp", "gmt time", "time_open"]:
        if name in lowered:
            return lowered[name]
    return columns[0] if columns else None


def detect_close_col(columns: Sequence[str]) -> Optional[str]:
    lowered = {str(c).lower(): c for c in columns}
    for name in ["close", "bidclose", "bid_close"]:
        if name in lowered:
            return lowered[name]
    return None


def read_candles(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, sep=None, engine="python")
    except Exception:
        return pd.read_csv(path)


def normalize_ts(value: Any) -> Optional[str]:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def latest_candle_info(path: Optional[Path], explicit_eval_time: Optional[str]) -> Dict[str, Any]:
    if explicit_eval_time:
        ts = normalize_ts(explicit_eval_time)
        if ts is None:
            raise ValueError(f"Invalid --eval-time: {explicit_eval_time}")
        return {"eval_time": ts, "source": "explicit_eval_time", "candle_path": None, "entry_price": None}
    if path is None or not path.exists():
        raise FileNotFoundError("M15 candle CSV not found. Use --candles-m15 or --eval-time.")
    df = read_candles(path)
    time_col = detect_time_col(list(df.columns))
    close_col = detect_close_col(list(df.columns))
    if time_col is None:
        raise ValueError(f"No time column found in {path}")
    work = df.copy()
    work["__time"] = pd.to_datetime(work[time_col], errors="coerce")
    work = work.dropna(subset=["__time"]).sort_values("__time")
    if work.empty:
        raise ValueError(f"No valid candle times in {path}")
    last = work.iloc[-1]
    entry_price = None
    if close_col is not None:
        try:
            entry_price = float(last[close_col])
        except Exception:
            entry_price = None
    return {
        "eval_time": last["__time"].strftime("%Y-%m-%d %H:%M:%S"),
        "source": "latest_m15_csv_row",
        "candle_path": str(path),
        "entry_price": entry_price,
        "time_column": time_col,
        "close_column": close_col,
    }


def fmt_float(value: Any, digits: int = 2) -> str:
    if value is None:
        return "-"
    try:
        v = float(value)
    except Exception:
        return str(value)
    if math.isnan(v):
        return "-"
    return f"{v:.{digits}f}"


def fmt_r(value: Any) -> str:
    if value is None:
        return "未評価"
    try:
        v = float(value)
    except Exception:
        return str(value)
    if math.isnan(v):
        return "未評価"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.2f}R"


def title_icon(direction: str) -> str:
    d = str(direction).upper()
    if d == "BUY":
        return "🟢"
    if d == "SELL":
        return "🔴"
    return "⚪"


def priority_label(priority: str) -> str:
    return {
        "HIGH_A": "HIGH_A / CoreA本命",
        "HIGH_B": "HIGH_B / CoreB RR1.25",
        "HIGH_CONFLUENCE": "HIGH_CONFLUENCE / CoreA+CoreB合流",
        "MEDIUM": "MEDIUM / 補助候補",
    }.get(str(priority), str(priority))


def component_description(component: str) -> str:
    return {
        "CoreA_fold4_ABC_CAP5": "fold4_rules + ABCゲート + CAP5/CAP3 sizing",
        "RR125_BUY_CONFLUENCE": "RR1.0由来BUYをTP=1.25×SLで再評価、same_count>=15、CAP3",
        "CoreA_PLUS_RR125_BUY_CONFLUENCE": "CoreA BUYとCoreB RR1.25 BUYが同時刻で合流。初期はCoreB追加0.5。",
        "RANGE96_REFINED": "CoreA Reject補助: range96/trend_eff96/SELL条件で絞り込み、CAP3",
        "VOL_TRMEAN32_REFINED": "CoreA Reject補助: tr_mean_32/ret96/range96条件で絞り込み、CAP3",
        "TIER2_HVT": "CoreA Reject補助: Tier2 static + HIGH_VOL_TREND、CAP3",
    }.get(str(component), str(component))


def parse_variant(variant: Any) -> Tuple[Optional[float], Optional[float]]:
    if variant is None or pd.isna(variant):
        return None, None
    m = VARIANT_RE.search(str(variant))
    if not m:
        return None, None
    return float(m.group("tp")), float(m.group("sl"))


def load_core_variant_map(dataset: str) -> Dict[int, Dict[str, Any]]:
    paths = {
        "2025": default_core_dir() / "abc_stack_cap_2025_fold4_cluster_ledger.csv",
        "2026": default_core_dir() / "abc_stack_cap_2026_cluster_ledger.csv",
    }
    path = paths.get(dataset)
    out: Dict[int, Dict[str, Any]] = {}
    if path is None or not path.exists():
        return out
    df = pd.read_csv(path)
    if "cluster_id" not in df.columns:
        return out
    for _, r in df.iterrows():
        try:
            cid = int(float(r["cluster_id"]))
        except Exception:
            continue
        out[cid] = r.to_dict()
    return out


def compute_price_levels(row: Dict[str, Any], candle_info: Dict[str, Any], pips_to_price: float, core_map: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    entry = candle_info.get("entry_price")
    direction = str(row.get("direction", "")).upper()
    tp_pips = None
    sl_pips = None
    variant = None
    if row.get("priority") in {"HIGH_A", "HIGH_CONFLUENCE"}:
        try:
            cid = int(float(row.get("core_cluster_id")))
            source = core_map.get(cid, {})
            variant = source.get("top_variant") or source.get("variant")
            tp_pips, sl_pips = parse_variant(variant)
        except Exception:
            pass
    # Fallback for current known CoreA default.
    if tp_pips is None or sl_pips is None:
        if row.get("component") == "CoreA_fold4_ABC_CAP5":
            tp_pips, sl_pips = 150.0, 150.0
    tp_dist = tp_pips * pips_to_price if tp_pips is not None else None
    sl_dist = sl_pips * pips_to_price if sl_pips is not None else None
    tp_price = None
    sl_price = None
    if entry is not None and tp_dist is not None and sl_dist is not None:
        if direction == "BUY":
            tp_price = float(entry) + tp_dist
            sl_price = float(entry) - sl_dist
        elif direction == "SELL":
            tp_price = float(entry) - tp_dist
            sl_price = float(entry) + sl_dist
    return {
        "entry_price": entry,
        "tp_pips": tp_pips,
        "sl_pips": sl_pips,
        "tp_distance": tp_dist,
        "sl_distance": sl_dist,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "variant": variant,
    }


def price_line(label: str, price: Optional[float], distance: Optional[float], direction: str, kind: str) -> str:
    if price is None:
        return f"{label}: 未取得"
    if distance is None:
        return f"{label}: {fmt_float(price)}"
    sign = "+" if (kind == "tp" and direction == "BUY") or (kind == "sl" and direction == "SELL") else "-"
    if kind == "tp" and direction == "SELL":
        sign = "-"
    if kind == "sl" and direction == "BUY":
        sign = "-"
    return f"{label}: {fmt_float(price)}（{sign}{fmt_float(distance)}）"


def risk_note(row: Dict[str, Any]) -> str:
    p = str(row.get("priority", ""))
    if p == "HIGH_CONFLUENCE":
        return "CoreA+CoreBの同方向合流。初期ロット候補は1.5相当。"
    if p == "HIGH_A":
        return "CoreA本命。単独ロット候補1.0。"
    if p == "HIGH_B":
        return "CoreB RR1.25。BUY専用の第二Core候補。単独ロット候補1.0。"
    if p == "MEDIUM":
        return "MEDIUM補助。HIGHと同時刻ならHIGH優先。初期ロット候補0.5。"
    return "監査候補。"


def render_notification(row: Dict[str, Any], levels: Dict[str, Any], eval_time: str) -> str:
    direction = str(row.get("direction", "")).upper()
    priority = str(row.get("priority", ""))
    component = str(row.get("component", ""))
    return "\n".join([
        f"【GOLD】{title_icon(direction)} {direction}｜{priority_label(priority)}",
        "━━━━━━━━━━━━━━━━━━━━",
        f"時刻: {eval_time}",
        f"エントリー: {fmt_float(levels.get('entry_price'))}",
        price_line("TP", levels.get("tp_price"), levels.get("tp_distance"), direction, "tp"),
        price_line("SL", levels.get("sl_price"), levels.get("sl_distance"), direction, "sl"),
        f"種別: {component}",
        f"根拠: {component_description(component)}",
        f"ロット候補: {fmt_float(row.get('lot_multiplier_candidate'))}",
        f"検証R: {fmt_r(row.get('profit_r_audit'))}",
        "",
        "状態: AUDIT ONLY（外部送信なし）",
        f"メモ: {risk_note(row)}",
    ])


def render_no_signal(eval_time: str, dataset: str) -> str:
    return "\n".join([
        "【GOLD】⚪ NO SIGNAL",
        "━━━━━━━━━━━━━━━━━━━━",
        f"時刻: {eval_time}",
        f"dataset: {dataset}",
        "状態: AUDIT ONLY（外部送信なし）",
        "メモ: 最新M15足に一致する監査済み候補はありません。",
    ])


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    candidate_csv = Path(args.candidate_csv).expanduser().resolve() if args.candidate_csv else default_candidate_csv()
    candle_path = Path(args.candles_m15).expanduser().resolve() if args.candles_m15 else find_default_m15_csv()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not candidate_csv.exists():
        print(f"[ERROR] candidate csv not found: {candidate_csv}")
        return 2
    try:
        candle_info = latest_candle_info(candle_path, args.eval_time)
    except Exception as exc:
        print(f"[ERROR] latest candle detection failed: {exc}")
        return 2

    candidates = pd.read_csv(candidate_csv)
    required = ["dataset", "entry_time", "direction", "priority", "component", "lot_multiplier_candidate"]
    missing = [c for c in required if c not in candidates.columns]
    if missing:
        print(f"[ERROR] missing candidate columns: {missing}")
        return 2
    candidates["entry_time_norm"] = pd.to_datetime(candidates["entry_time"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    matched = candidates[(candidates["dataset"].astype(str) == str(args.dataset)) & (candidates["entry_time_norm"] == candle_info["eval_time"])].copy()
    matched["priority_rank"] = matched["priority"].map(PRIORITY_ORDER).fillna(99)
    matched = matched.sort_values(["priority_rank", "lot_multiplier_candidate"], ascending=[True, False])
    core_map = load_core_variant_map(str(args.dataset))

    if matched.empty:
        status = "NO_SIGNAL"
        selected_records: List[Dict[str, Any]] = []
        notification = render_no_signal(candle_info["eval_time"], str(args.dataset))
        selected_levels = []
    else:
        status = "SIGNAL_CANDIDATE_FOUND"
        # Keep the top-priority candidate only for latest-candle notification. Save all matches separately.
        top = matched.iloc[0].to_dict()
        levels = compute_price_levels(top, candle_info, args.pips_to_price, core_map)
        notification = render_notification(top, levels, candle_info["eval_time"])
        selected_records = [top]
        selected_levels = [levels]

    packet = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "audit_only": True,
        "external_actions": {
            "discord_send_allowed": False,
            "mt5_order_allowed": False,
            "ai_api_allowed": False,
            "live_hook_allowed": False,
        },
        "dataset": str(args.dataset),
        "eval_time": candle_info["eval_time"],
        "candle_info": candle_info,
        "candidate_csv": str(candidate_csv),
        "match_count": int(len(matched)),
        "selected_candidates": selected_records,
        "selected_price_levels": selected_levels,
        "notification_preview_text": notification,
        "all_matches": matched.drop(columns=["priority_rank"], errors="ignore").to_dict(orient="records"),
    }

    out_json = output_dir / "gold_v2_latest_candle_candidate_packet.json"
    out_txt = output_dir / "gold_v2_latest_candle_notification_preview.txt"
    out_csv = output_dir / "gold_v2_latest_candle_candidate_matches.csv"
    out_report = output_dir / "GOLD_V2_LATEST_CANDLE_CANDIDATE_AUDIT_ONLY_REPORT.md"
    out_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    out_txt.write_text(notification + "\n", encoding="utf-8")
    matched.drop(columns=["priority_rank"], errors="ignore").to_csv(out_csv, index=False, encoding="utf-8-sig")
    report = [
        "# GOLD latest-candle candidate audit-only report",
        "",
        f"Created UTC: {packet['created_utc']}",
        f"Status: {status}",
        f"Dataset: {args.dataset}",
        f"Eval time: {candle_info['eval_time']}",
        f"Match count: {len(matched)}",
        "",
        "## Notification preview",
        "",
        "```text",
        notification,
        "```",
        "",
        "No external transmission or order execution is performed.",
    ]
    out_report.write_text("\n".join(report), encoding="utf-8")

    print(f"[DONE] status={status} output_dir={output_dir}")
    print(notification)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
