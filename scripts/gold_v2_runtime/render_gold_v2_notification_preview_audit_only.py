#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Render GOLD V2 notification preview text from audited runtime candidates.

No external side effects are performed. The script only reads JSON files and
writes text/json preview files.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render GOLD V2 notification preview text")
    parser.add_argument("--input-dir", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--symbol", default="GOLD")
    parser.add_argument("--timeframe", default="M15")
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


def direction_icon(direction: str) -> str:
    d = str(direction).upper()
    if d == "BUY":
        return "UP"
    if d == "SELL":
        return "DOWN"
    return "-"


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


def safety_text(record: Dict[str, Any]) -> str:
    flags = []
    for key in ["audit_only", "ai_api_enabled", "discord_enabled", "mt5_order_enabled", "live_hook_enabled"]:
        flags.append(f"{key}={record.get(key)}")
    return ", ".join(flags)


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


def render_message(record: Dict[str, Any], *, symbol: str, timeframe: str) -> str:
    direction = str(record.get("direction", ""))
    priority = str(record.get("priority", ""))
    component = str(record.get("component", ""))
    lines = [
        f"【{symbol} V2】{direction_icon(direction)} {direction}｜{priority_label(priority)}",
        "━━━━━━━━━━━━━━━━━━━━",
        f"時刻: {record.get('entry_time', '-')}",
        f"足: {timeframe}",
        f"種別: {component}",
        f"根拠: {component_description(component)}",
        f"ロット候補: {fmt_float(record.get('lot_multiplier_candidate'), 2)}",
        f"検証R: {fmt_r(record.get('profit_r_audit'))}",
        f"signal_id: {record.get('signal_id', '-')}",
        "",
        "状態: AUDIT ONLY（外部送信なし）",
        f"安全フラグ: {safety_text(record)}",
        f"メモ: {risk_note(record)}",
    ]
    return "\n".join(lines)


def render_summary(summary: Dict[str, Any]) -> str:
    lines = [
        "GOLD V2 通知候補サマリー（AUDIT ONLY）",
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
    lines.append("安全状態: audit_only=True / ai=False / discord=False / mt5=False / live_hook=False")
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
    messages: List[Dict[str, Any]] = []
    text_blocks: List[str] = []
    md_blocks: List[str] = []
    for rec in latest.get("latest_by_dataset", []):
        msg = render_message(rec, symbol=args.symbol, timeframe=args.timeframe)
        messages.append({"dataset": rec.get("dataset"), "signal_id": rec.get("signal_id"), "message": msg, "record": rec})
        text_blocks.append(msg)
        md_blocks.append("```text\n" + msg + "\n```")

    summary_text = render_summary(summary)
    (output_dir / "gold_v2_notification_preview_latest.txt").write_text("\n\n".join(text_blocks) + "\n", encoding="utf-8")
    (output_dir / "gold_v2_notification_preview_latest.md").write_text("# GOLD V2 notification preview latest\n\n" + "\n\n".join(md_blocks) + "\n", encoding="utf-8")
    (output_dir / "gold_v2_notification_preview_summary.txt").write_text(summary_text + "\n", encoding="utf-8")
    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "AUDIT_ONLY_NOTIFICATION_PREVIEW",
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "message_count": len(messages),
        "messages": messages,
        "summary_text": summary_text,
        "safety": summary.get("safety", {}),
    }
    (output_dir / "gold_v2_notification_preview_latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    report = [
        "# GOLD V2 notification preview audit-only report",
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
