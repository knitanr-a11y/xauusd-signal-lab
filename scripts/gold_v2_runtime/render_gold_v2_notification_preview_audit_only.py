#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Render GOLD notification preview text from audited runtime candidates.

No external side effects are performed. The script only reads local files and
writes preview text/json files.

Notification template changes:
  - Title does not include "V2".
  - BUY title uses a green circle; SELL title uses a red circle.
  - Footnote-like technical rows are omitted from the notification body.
  - Entry price, TP, and SL are shown immediately under the signal time when
    they can be derived from source ledgers and/or M15 candles.
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


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render GOLD notification preview text")
    parser.add_argument("--input-dir", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--symbol", default="GOLD")
    parser.add_argument("--timeframe", default="M15")
    parser.add_argument("--candles-m15", default=None, help="Optional M15 candle CSV for entry price lookup")
    parser.add_argument("--pips-to-price", type=float, default=PIPS_TO_PRICE_DEFAULT)
    return parser.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    if len(root.parents) >= 2:
        return root.parents[1]
    return root.parent


def default_input_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_runtime_signal_candidates_audit_only"


def default_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_notification_preview_audit_only"


def default_core_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_ABC_stack_cap_2025_2026_validation_outputs"


def default_rr125_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_rr125_second_core_probe_outputs"


def default_medium_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_coreb_refined_probe_outputs"


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


def risk_note(record: Dict[str, Any]) -> str:
    p = str(record.get("priority", ""))
    if p == "HIGH_CONFLUENCE":
        return "CoreA+CoreBの同方向合流。初期ロット候補は1.5相当。"
    if p == "HIGH_A":
        return "CoreA本命。単独ロット候補1.0。"
    if p == "HIGH_B":
        return "CoreB RR1.25。BUY専用の第二Core候補。単独ロット候補1.0。"
    if p == "MEDIUM":
        return "MEDIUM補助。HIGHと同時刻ならHIGH優先。初期ロット候補0.5。"
    return "監査候補。"


def read_csv_if_exists(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def as_int_or_none(value: Any) -> Optional[int]:
    try:
        if value is None or pd.isna(value):
            return None
        return int(float(value))
    except Exception:
        return None


def load_core_rows() -> Dict[Tuple[str, int], Dict[str, Any]]:
    rows: Dict[Tuple[str, int], Dict[str, Any]] = {}
    paths = {
        "2025": default_core_dir() / "abc_stack_cap_2025_fold4_cluster_ledger.csv",
        "2026": default_core_dir() / "abc_stack_cap_2026_cluster_ledger.csv",
    }
    for dataset, path in paths.items():
        df = read_csv_if_exists(path)
        if df is None or "cluster_id" not in df.columns:
            continue
        for _, r in df.iterrows():
            cid = as_int_or_none(r.get("cluster_id"))
            if cid is not None:
                rows[(dataset, cid)] = r.to_dict()
    return rows


def load_medium_rows() -> Dict[Tuple[str, int], Dict[str, Any]]:
    rows: Dict[Tuple[str, int], Dict[str, Any]] = {}
    path = default_medium_dir() / "coreb_refined_rule_ledgers.csv"
    df = read_csv_if_exists(path)
    if df is None or "cluster_id" not in df.columns:
        return rows
    dataset_map = {"2025_fold4": "2025", "2026_WF": "2026"}
    for _, r in df.iterrows():
        ds = dataset_map.get(str(r.get("dataset")), str(r.get("dataset")))
        cid = as_int_or_none(r.get("cluster_id"))
        if cid is not None:
            rows[(ds, cid)] = r.to_dict()
    return rows


def load_rr125_raw() -> pd.DataFrame:
    path = default_rr125_dir() / "rr125_raw_signal_ledger.csv"
    df = read_csv_if_exists(path)
    if df is None:
        return pd.DataFrame()
    if "entry_time" in df.columns:
        df["entry_time_norm"] = pd.to_datetime(df["entry_time"], errors="coerce").astype(str)
    return df


def detect_time_col(columns: Sequence[str]) -> Optional[str]:
    lowered = {c.lower(): c for c in columns}
    for name in ["time", "datetime", "date", "open_time", "timestamp", "gmt time", "time_open"]:
        if name in lowered:
            return lowered[name]
    return columns[0] if columns else None


def detect_close_col(columns: Sequence[str]) -> Optional[str]:
    lowered = {c.lower(): c for c in columns}
    for name in ["close", "Close", "bidclose", "bid_close"]:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def load_candle_close_map(path: Optional[Path]) -> Dict[str, float]:
    if path is None or not path.exists():
        return {}
    try:
        df = pd.read_csv(path, sep=None, engine="python")
    except Exception:
        try:
            df = pd.read_csv(path)
        except Exception:
            return {}
    time_col = detect_time_col(list(df.columns))
    close_col = detect_close_col(list(df.columns))
    if time_col is None or close_col is None:
        return {}
    t = pd.to_datetime(df[time_col], errors="coerce")
    c = pd.to_numeric(df[close_col], errors="coerce")
    out: Dict[str, float] = {}
    for ts, close in zip(t, c):
        if pd.isna(ts) or pd.isna(close):
            continue
        out[str(ts.to_pydatetime().replace(tzinfo=None))] = float(close)
        out[ts.strftime("%Y-%m-%d %H:%M:%S")] = float(close)
    return out


def parse_variant(variant: Any) -> Tuple[Optional[float], Optional[float]]:
    if variant is None or pd.isna(variant):
        return None, None
    m = VARIANT_RE.search(str(variant))
    if not m:
        return None, None
    return float(m.group("tp")), float(m.group("sl"))


def first_not_none(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except Exception:
            pass
        return value
    return None


def find_source_row(record: Dict[str, Any], core_rows: Dict[Tuple[str, int], Dict[str, Any]], medium_rows: Dict[Tuple[str, int], Dict[str, Any]], rr_raw: pd.DataFrame) -> Dict[str, Any]:
    dataset = str(record.get("dataset"))
    priority = str(record.get("priority"))
    source = str(record.get("source"))
    if priority in {"HIGH_A", "HIGH_CONFLUENCE"}:
        cid = as_int_or_none(record.get("core_cluster_id"))
        if cid is not None and (dataset, cid) in core_rows:
            return core_rows[(dataset, cid)]
    if priority == "MEDIUM":
        cid = as_int_or_none(record.get("medium_cluster_id"))
        if cid is not None and (dataset, cid) in medium_rows:
            return medium_rows[(dataset, cid)]
    if priority == "HIGH_B" or source == "CORE_B_ONLY":
        if rr_raw.empty:
            return {}
        entry_time = str(record.get("entry_time"))
        direction = str(record.get("direction"))
        cand = rr_raw[
            (rr_raw.get("dataset", "").astype(str) == dataset)
            & (rr_raw.get("direction", "").astype(str) == direction)
            & (rr_raw.get("policy", "").astype(str) == "RR125_from_RR1_rules")
            & (rr_raw.get("entry_time_norm", "").astype(str) == entry_time)
        ]
        if not cand.empty:
            return cand.iloc[0].to_dict()
    return {}


def compute_levels(record: Dict[str, Any], source_row: Dict[str, Any], candle_close: Dict[str, float], pips_to_price: float) -> Dict[str, Any]:
    direction = str(record.get("direction", "")).upper()
    entry_time = str(record.get("entry_time", ""))
    variant = first_not_none(source_row.get("top_variant"), source_row.get("variant"))
    tp_pips = first_not_none(source_row.get("tp_pips"), None)
    sl_pips = first_not_none(source_row.get("sl_pips"), None)
    if tp_pips is None or sl_pips is None:
        parsed_tp, parsed_sl = parse_variant(variant)
        tp_pips = first_not_none(tp_pips, parsed_tp)
        sl_pips = first_not_none(sl_pips, parsed_sl)
    entry_price = first_not_none(source_row.get("entry_price"), candle_close.get(entry_time))
    try:
        entry_price_f = float(entry_price) if entry_price is not None else None
    except Exception:
        entry_price_f = None
    try:
        tp_dist = float(tp_pips) * pips_to_price if tp_pips is not None else None
        sl_dist = float(sl_pips) * pips_to_price if sl_pips is not None else None
    except Exception:
        tp_dist = None
        sl_dist = None
    tp_price = None
    sl_price = None
    if entry_price_f is not None and tp_dist is not None and sl_dist is not None:
        if direction == "BUY":
            tp_price = entry_price_f + tp_dist
            sl_price = entry_price_f - sl_dist
        elif direction == "SELL":
            tp_price = entry_price_f - tp_dist
            sl_price = entry_price_f + sl_dist
    return {
        "variant": variant,
        "entry_price": entry_price_f,
        "tp_pips": None if tp_pips is None else float(tp_pips),
        "sl_pips": None if sl_pips is None else float(sl_pips),
        "tp_distance": tp_dist,
        "sl_distance": sl_dist,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "pips_to_price": pips_to_price,
    }


def price_line(label: str, price: Optional[float], distance: Optional[float], direction: str, kind: str) -> str:
    if price is None:
        if distance is None:
            return f"{label}: 未取得"
        return f"{label}: 未取得（幅 {fmt_float(distance)}）"
    if distance is None:
        return f"{label}: {fmt_float(price)}"
    sign = "+" if (kind == "tp" and direction == "BUY") or (kind == "sl" and direction == "SELL") else "-"
    if kind == "tp" and direction == "SELL":
        sign = "-"
    if kind == "sl" and direction == "BUY":
        sign = "-"
    return f"{label}: {fmt_float(price)}（{sign}{fmt_float(distance)}）"


def render_message(record: Dict[str, Any], levels: Dict[str, Any], *, symbol: str, timeframe: str) -> str:
    direction = str(record.get("direction", "")).upper()
    priority = str(record.get("priority", ""))
    component = str(record.get("component", ""))
    lines = [
        f"【{symbol}】{title_icon(direction)} {direction}｜{priority_label(priority)}",
        "━━━━━━━━━━━━━━━━━━━━",
        f"時刻: {record.get('entry_time', '-')}",
        f"エントリー: {fmt_float(levels.get('entry_price'))}",
        price_line("TP", levels.get("tp_price"), levels.get("tp_distance"), direction, "tp"),
        price_line("SL", levels.get("sl_price"), levels.get("sl_distance"), direction, "sl"),
        f"種別: {component}",
        f"根拠: {component_description(component)}",
        f"ロット候補: {fmt_float(record.get('lot_multiplier_candidate'), 2)}",
        f"検証R: {fmt_r(record.get('profit_r_audit'))}",
        "",
        "状態: AUDIT ONLY（外部送信なし）",
        f"メモ: {risk_note(record)}",
    ]
    return "\n".join(lines)


def render_summary(summary: Dict[str, Any]) -> str:
    lines = [
        "GOLD 通知候補サマリー（AUDIT ONLY）",
        "━━━━━━━━━━━━━━━━━━━━",
        f"作成UTC: {summary.get('created_utc', '-')}",
        f"view: {summary.get('view', '-')}",
        f"record_count: {summary.get('record_count', '-')}",
        "",
    ]
    for row in summary.get("summary", []):
        if row.get("priority") != "ALL":
            continue
        wr = row.get("win_rate")
        wr_text = "-" if wr is None else f"{float(wr) * 100:.2f}%"
        lines.append(
            f"{row.get('dataset')}: {row.get('count')}件 / WR {wr_text} / PF {fmt_float(row.get('pf'))} / Total {fmt_r(row.get('total_r'))} / MaxDD {fmt_r(row.get('maxdd'))}"
        )
    lines.append("")
    lines.append("安全状態: AUDIT ONLY / 外部送信なし")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    input_dir = Path(args.input_dir).expanduser().resolve() if args.input_dir else default_input_dir()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    latest_path = input_dir / "gold_v2_runtime_signal_candidates_latest.json"
    summary_path = input_dir / "gold_v2_runtime_signal_candidates_summary.json"
    if not latest_path.exists():
        print(f"[ERROR] latest json not found: {latest_path}")
        return 2
    if not summary_path.exists():
        print(f"[ERROR] summary json not found: {summary_path}")
        return 2

    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    candle_path = Path(args.candles_m15).expanduser().resolve() if args.candles_m15 else find_default_m15_csv()
    candle_close = load_candle_close_map(candle_path)
    core_rows = load_core_rows()
    medium_rows = load_medium_rows()
    rr_raw = load_rr125_raw()

    messages: List[Dict[str, Any]] = []
    text_blocks: List[str] = []
    md_blocks: List[str] = []
    for rec in latest.get("latest_by_dataset", []):
        source_row = find_source_row(rec, core_rows, medium_rows, rr_raw)
        levels = compute_levels(rec, source_row, candle_close, args.pips_to_price)
        msg = render_message(rec, levels, symbol=args.symbol, timeframe=args.timeframe)
        messages.append({"dataset": rec.get("dataset"), "message": msg, "levels": levels, "record": rec})
        text_blocks.append(msg)
        md_blocks.append("```text\n" + msg + "\n```")

    summary_text = render_summary(summary)
    (output_dir / "gold_v2_notification_preview_latest.txt").write_text("\n\n".join(text_blocks) + "\n", encoding="utf-8")
    (output_dir / "gold_v2_notification_preview_latest.md").write_text("# GOLD notification preview latest\n\n" + "\n\n".join(md_blocks) + "\n", encoding="utf-8")
    (output_dir / "gold_v2_notification_preview_summary.txt").write_text(summary_text + "\n", encoding="utf-8")
    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "AUDIT_ONLY_NOTIFICATION_PREVIEW",
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "candles_m15": None if candle_path is None else str(candle_path),
        "pips_to_price": args.pips_to_price,
        "message_count": len(messages),
        "messages": messages,
        "summary_text": summary_text,
        "safety": summary.get("safety", {}),
    }
    (output_dir / "gold_v2_notification_preview_latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    report = [
        "# GOLD notification preview audit-only report",
        "",
        f"Created UTC: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        "",
        "```text",
        summary_text,
        "```",
        "",
        "## Latest messages",
        "",
        *md_blocks,
        "",
        "Preview only. No external transmission is performed.",
    ]
    (output_dir / "GOLD_V2_NOTIFICATION_PREVIEW_AUDIT_ONLY_REPORT.md").write_text("\n".join(report), encoding="utf-8")

    print(f"[DONE] output_dir={output_dir}")
    print("\n\n".join(text_blocks))
    if candle_path is None:
        print("[WARN] M15 candle CSV was not found. Entry prices may be missing for CoreA/MEDIUM previews.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
