#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build GOLD DISC8 operational candidate pack from fixed source of truth.

This script does NOT call OpenAI, MT5, Discord, or OHLC redetection.
It converts the fixed SAFE group-tag-filtered source of truth into:
- operational strategy manifest
- runtime group-tag gate rules
- Discord notification templates and preview messages
- audit JSON

Important:
The runtime gate rules assume that a pre-send tagger will provide the same
strategy-specific tag names/groups before notification. This builder only freezes
the gate spec; it does not implement feature-derived tag classification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOT_DIR = REPO_ROOT / "data" / "gold_disc8" / "source_of_truth" / "group_tag_filtered"
DEFAULT_RULE_JSON = REPO_ROOT / "data" / "gold_disc8" / "config" / "disc8_ai_group_tag_filter_rules_20260531.json"
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "gold_disc8" / "operational_candidate" / "group_tag_filtered"
EXPECTED_DISC8_IDS = [
    "DISC_01_BUY_TP200_SL100_RR2",
    "DISC_02_BUY_TP80_SL50_RR1p6",
    "DISC_04_BUY_TP150_SL100_RR1p5",
    "DISC_05_BUY_TP80_SL50_RR1p6",
    "DISC_06_SELL_TP80_SL50_RR1p6",
    "DISC_08_BUY_TP200_SL100_RR2",
    "DISC_09_BUY_TP80_SL50_RR1p6",
    "DISC_11_SELL_TP80_SL50_RR1p6",
]


def wpath(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(wpath(path), encoding="utf-8-sig")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(wpath(path), index=False, encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON not found: {path}")
    with open(wpath(path), "r", encoding="utf-8-sig") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise RuntimeError(f"JSON root must be object: {path}")
    return obj


def write_json(obj: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(wpath(path), "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    s = str(value).strip()
    return s if s else default


def as_bool(value: Any) -> bool:
    return clean(value).lower() in {"true", "1", "yes", "y"}


def as_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def direction_jp(direction: str) -> str:
    d = clean(direction).upper()
    if d == "BUY":
        return "買い"
    if d == "SELL":
        return "売り"
    return d or "不明"


def risk_reward_from_strategy_id(strategy_id: str) -> tuple[str, str, str]:
    text = clean(strategy_id)
    tp = ""
    sl = ""
    rr = ""
    for part in text.split("_"):
        up = part.upper()
        if up.startswith("TP") and len(up) > 2:
            tp = up[2:]
        if up.startswith("SL") and len(up) > 2:
            sl = up[2:]
        if up.startswith("RR") and len(up) > 2:
            rr = up[2:].replace("P", ".")
    return tp, sl, rr


def format_pct(value: Any) -> str:
    v = as_float(value)
    if v is None:
        return ""
    return f"{v * 100:.2f}%"


def format_num(value: Any, digits: int = 3) -> str:
    v = as_float(value)
    if v is None:
        return ""
    return f"{v:.{digits}f}"


def build_manifest(selected: pd.DataFrame, strategy_summary: pd.DataFrame, audit: dict[str, Any]) -> pd.DataFrame:
    metric_map = {clean(r.get("strategy_id")): r for _, r in strategy_summary.iterrows()}
    rows = []
    for _, row in selected.iterrows():
        sid = clean(row.get("strategy_id"))
        m = metric_map.get(sid, {})
        direction = clean(row.get("direction"))
        tp, sl, rr = risk_reward_from_strategy_id(sid)
        rows.append({
            "enabled": True,
            "asset": "GOLD",
            "symbol": "XAUUSD",
            "strategy_id": sid,
            "candidate_id": clean(row.get("candidate_id"), sid),
            "strategy_key": clean(row.get("strategy_key"), sid),
            "strategy_alias": clean(row.get("strategy_alias"), sid),
            "condition_id": clean(row.get("condition_id"), sid),
            "direction": direction,
            "direction_jp": direction_jp(direction),
            "tp_pips": tp,
            "sl_pips": sl,
            "rr": rr,
            "filter_profile": clean(row.get("filter_profile"), "safe"),
            "source_of_truth_version": clean(row.get("source_of_truth_version"), clean(audit.get("source_of_truth_version"))),
            "source_trade_count": int(m.get("trade_count", row.get("trade_count", 0))) if clean(m.get("trade_count", row.get("trade_count", 0))) else 0,
            "source_win_rate": m.get("win_rate", row.get("win_rate")),
            "source_profit_factor": m.get("profit_factor", row.get("profit_factor")),
            "source_avg_r": m.get("avg_r", row.get("avg_r")),
            "source_total_r": m.get("total_r", row.get("total_r")),
            "source_avg_trades_per_month": m.get("avg_trades_per_base_month", row.get("avg_trades_per_base_month")),
            "notification_title": clean(row.get("notification_title"), f"GOLD DISC8 {direction_jp(direction)}候補 {sid}"),
            "notification_reason_jp": clean(row.get("notification_reason_jp"), "DISC8 SAFEグループタグフィルタ通過候補"),
            "runtime_gate_required": True,
            "runtime_gate_rule_json": "data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_runtime_group_tag_gate_rules.json",
            "send_enabled_default": False,
            "order_send_enabled_default": False,
            "notes": "Audit-only operational candidate. Connect to live notification only after pre-send tagger audit passes.",
        })
    return pd.DataFrame(rows)


def build_runtime_gate_rules(rule_config: dict[str, Any], manifest: pd.DataFrame) -> dict[str, Any]:
    allowed_strategy_ids = manifest["strategy_id"].dropna().astype(str).tolist()
    block_rules = []
    watch_rules = []
    for r in rule_config.get("rules", []):
        if not isinstance(r, dict) or not r.get("enabled", True):
            continue
        strategy_id = clean(r.get("strategy_id"))
        if strategy_id not in allowed_strategy_ids:
            continue
        item = {
            "rule_id": clean(r.get("rule_id")),
            "strategy_id": strategy_id,
            "rule_group": clean(r.get("rule_group")),
            "tag_group": clean(r.get("tag_group")),
            "tag_name": clean(r.get("tag_name")),
            "configured_action": clean(r.get("action"), "block"),
            "source_step": r.get("source_step"),
            "source": clean(r.get("source")),
        }
        if clean(r.get("action"), "block") == "block":
            block_rules.append(item)
        elif clean(r.get("action")) == "watch_only":
            watch_rules.append(item)
    return {
        "schema_version": "gold_disc8_runtime_group_tag_gate_rules.v1",
        "asset": "GOLD",
        "symbol": "XAUUSD",
        "mode": "strategy_specific_pre_send_gate",
        "default_action": "allow",
        "allowed_strategy_ids": allowed_strategy_ids,
        "requires_pre_send_tagger": True,
        "pre_send_tagger_contract": {
            "required_fields": ["strategy_id", "tag_group", "tag_name"],
            "tag_group_values": ["risk", "execution", "positive", "system"],
            "matching_rule": "block if strategy_id, tag_group, tag_name exactly match an enabled block rule",
        },
        "block_rules": block_rules,
        "watch_only_rules": watch_rules,
        "actions": {
            "block": "do_not_send_discord_and_do_not_order_send; write gate audit",
            "watch_only": "allow notification but write watch audit",
            "allow": "allow candidate to continue",
        },
    }


def build_notification_templates(manifest: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]], str]:
    rows = []
    json_rows = []
    md_parts = ["# GOLD DISC8 Discord preview messages", "", "実送信はしません。文面プレビューのみです。", ""]
    for _, row in manifest.iterrows():
        sid = clean(row.get("strategy_id"))
        direction = clean(row.get("direction"))
        title = f"🟡 GOLD DISC8 {direction_jp(direction)}候補｜{sid}"
        body_lines = [
            title,
            f"方向: {direction_jp(direction)} ({direction})",
            f"TP/SL/RR: TP{clean(row.get('tp_pips'))} / SL{clean(row.get('sl_pips'))} / RR{clean(row.get('rr'))}",
            f"SAFE後成績: 勝率 {format_pct(row.get('source_win_rate'))} / PF {format_num(row.get('source_profit_factor'), 3)} / 平均R {format_num(row.get('source_avg_r'), 3)}",
            f"月平均: {format_num(row.get('source_avg_trades_per_month'), 2)}件 / source件数 {clean(row.get('source_trade_count'))}",
            "ゲート: DISC8 group-tag pre-send gate 通過時のみ通知",
            "注意: 現段階はaudit-only。実送信・発注は無効。",
        ]
        message = "\n".join(body_lines)
        rows.append({
            "strategy_id": sid,
            "title": title,
            "direction": direction,
            "discord_message_template": message,
            "send_enabled_default": False,
            "order_send_enabled_default": False,
        })
        json_rows.append({
            "strategy_id": sid,
            "title": title,
            "message_lines": body_lines,
            "send_enabled_default": False,
            "order_send_enabled_default": False,
        })
        md_parts.append(f"## {sid}")
        md_parts.append("")
        md_parts.append("```text")
        md_parts.append(message)
        md_parts.append("```")
        md_parts.append("")
    return pd.DataFrame(rows), json_rows, "\n".join(md_parts)


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    selected_csv = args.sot_dir / "selected_disc8_group_tag_filtered_strategies.csv"
    source_ledger_csv = args.sot_dir / "group_tag_filtered_source_trade_ledger.csv"
    sot_audit_json = args.sot_dir / "group_tag_filtered_source_trade_audit.json"
    strategy_summary_csv = args.sot_dir / "group_tag_filtered_strategy_summary.csv"
    for p in [selected_csv, source_ledger_csv, sot_audit_json, strategy_summary_csv, args.rule_json]:
        if not p.exists():
            raise FileNotFoundError(f"Required input not found: {p}")

    selected = read_csv(selected_csv)
    source_ledger = read_csv(source_ledger_csv)
    sot_audit = read_json(sot_audit_json)
    strategy_summary = read_csv(strategy_summary_csv)
    rule_config = read_json(args.rule_json)

    manifest = build_manifest(selected, strategy_summary, sot_audit)
    gate = build_runtime_gate_rules(rule_config, manifest)
    template_df, template_json_rows, preview_md = build_notification_templates(manifest)

    outputs = {
        "manifest_csv": args.output_dir / "gold_disc8_operational_strategy_manifest.csv",
        "manifest_json": args.output_dir / "gold_disc8_operational_strategy_manifest.json",
        "gate_rules_json": args.output_dir / "gold_disc8_runtime_group_tag_gate_rules.json",
        "discord_templates_csv": args.output_dir / "gold_disc8_discord_notification_templates.csv",
        "discord_templates_json": args.output_dir / "gold_disc8_discord_notification_templates.json",
        "discord_preview_md": args.output_dir / "gold_disc8_discord_preview_messages.md",
        "audit_json": args.output_dir / "gold_disc8_operational_candidate_audit.json",
    }
    write_csv(manifest, outputs["manifest_csv"])
    write_json({"strategies": manifest.to_dict("records")}, outputs["manifest_json"])
    write_json(gate, outputs["gate_rules_json"])
    write_csv(template_df, outputs["discord_templates_csv"])
    write_json({"templates": template_json_rows}, outputs["discord_templates_json"])
    write_text(preview_md, outputs["discord_preview_md"])

    present_ids = sorted(manifest["strategy_id"].dropna().astype(str).unique().tolist())
    missing_ids = [sid for sid in EXPECTED_DISC8_IDS if sid not in present_ids]
    extra_ids = [sid for sid in present_ids if sid not in EXPECTED_DISC8_IDS]
    audit = {
        "script": "build_gold_disc8_operational_candidate_pack.py",
        "no_ai_api_call": True,
        "no_mt5_order_send": True,
        "no_discord_send": True,
        "no_ohlc_redetection": True,
        "source_of_truth_version": clean(sot_audit.get("source_of_truth_version")),
        "profile": clean(sot_audit.get("profile")),
        "inputs": {
            "selected_csv": str(selected_csv),
            "selected_csv_sha256": sha256_file(selected_csv),
            "source_ledger_csv": str(source_ledger_csv),
            "source_ledger_csv_sha256": sha256_file(source_ledger_csv),
            "sot_audit_json": str(sot_audit_json),
            "sot_audit_json_sha256": sha256_file(sot_audit_json),
            "strategy_summary_csv": str(strategy_summary_csv),
            "strategy_summary_csv_sha256": sha256_file(strategy_summary_csv),
            "rule_json": str(args.rule_json),
            "rule_json_sha256": sha256_file(args.rule_json),
        },
        "outputs": {k: str(v) for k, v in outputs.items()},
        "checks": {
            "strategy_count": int(len(manifest)),
            "expected_strategy_count": 8,
            "present_strategy_ids": present_ids,
            "missing_expected_strategy_ids": missing_ids,
            "extra_strategy_ids": extra_ids,
            "source_trade_rows": int(len(source_ledger)),
            "sot_overall_ok": bool(sot_audit.get("checks", {}).get("overall_ok")),
            "block_rule_count": int(len(gate["block_rules"])),
            "watch_only_rule_count": int(len(gate["watch_only_rules"])),
            "send_enabled_any": bool(manifest["send_enabled_default"].astype(bool).any()) if "send_enabled_default" in manifest.columns else False,
            "order_send_enabled_any": bool(manifest["order_send_enabled_default"].astype(bool).any()) if "order_send_enabled_default" in manifest.columns else False,
            "overall_ok": len(manifest) == 8 and missing_ids == [] and extra_ids == [] and bool(sot_audit.get("checks", {}).get("overall_ok")) and not bool(manifest["send_enabled_default"].astype(bool).any()) and not bool(manifest["order_send_enabled_default"].astype(bool).any()),
        },
    }
    write_json(audit, outputs["audit_json"])

    print("=" * 80)
    print("GOLD DISC8 operational candidate pack")
    print("=" * 80)
    print(f"strategy_count: {audit['checks']['strategy_count']}")
    print(f"source_trade_rows: {audit['checks']['source_trade_rows']}")
    print(f"block_rule_count: {audit['checks']['block_rule_count']}")
    print(f"watch_only_rule_count: {audit['checks']['watch_only_rule_count']}")
    print(f"send_enabled_any: {audit['checks']['send_enabled_any']}")
    print(f"order_send_enabled_any: {audit['checks']['order_send_enabled_any']}")
    print(f"overall_ok: {audit['checks']['overall_ok']}")
    print("Outputs:")
    for key, path in outputs.items():
        print(f"  {key}: {path}")
    return 0 if audit["checks"]["overall_ok"] else 2


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build GOLD DISC8 operational candidate pack.")
    p.add_argument("--sot-dir", type=Path, default=DEFAULT_SOT_DIR)
    p.add_argument("--rule-json", type=Path, default=DEFAULT_RULE_JSON)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
