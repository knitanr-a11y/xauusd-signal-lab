#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build a GOLD live-audit packet from audited candidate and preview outputs.

This script has no external side effects. It only reads local audit outputs and
writes a packet that can be inspected before any future external integration.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build GOLD live-audit packet from local audit outputs")
    parser.add_argument("--candidate-dir", default=None)
    parser.add_argument("--preview-dir", default=None)
    parser.add_argument("--config", default="configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json")
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    if len(root.parents) >= 2:
        return root.parents[1]
    return root.parent


def default_candidate_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_runtime_signal_candidates_audit_only"


def default_preview_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_notification_preview_audit_only"


def default_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_live_audit_packet_audit_only"


def resolve_path(text: str) -> Path:
    p = Path(text)
    if p.is_absolute():
        return p
    return (repo_root() / p).resolve()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def safety_gate(policy: Dict[str, Any], candidate: Dict[str, Any], preview: Dict[str, Any]) -> Dict[str, Any]:
    policy_safety = policy.get("safety", {})
    candidate_safety = candidate.get("safety", {})
    preview_safety = preview.get("safety", {})
    checks = {
        "policy_audit_only_true": policy_safety.get("audit_only") is True,
        "policy_ai_false": policy_safety.get("ai_api_enabled") is False,
        "policy_discord_false": policy_safety.get("discord_enabled") is False,
        "policy_mt5_false": policy_safety.get("mt5_order_enabled") is False,
        "policy_live_hook_false": policy_safety.get("live_hook_enabled") is False,
        "candidate_ai_false": candidate_safety.get("ai_api_enabled") is False,
        "candidate_discord_false": candidate_safety.get("discord_enabled") is False,
        "candidate_mt5_false": candidate_safety.get("mt5_order_enabled") is False,
        "candidate_live_hook_false": candidate_safety.get("live_hook_enabled") is False,
        "preview_no_external_status": preview.get("status") == "AUDIT_ONLY_NOTIFICATION_PREVIEW",
    }
    return {
        "status": "BLOCK_EXTERNAL_ACTIONS" if all(checks.values()) else "REVIEW_REQUIRED",
        "checks": checks,
        "discord_send_allowed": False,
        "mt5_order_allowed": False,
        "ai_api_allowed": False,
        "live_hook_allowed": False,
        "reason": "Audit packet only. External actions remain disabled until an explicit future implementation changes the policy and passes a separate preflight.",
    }


def compact_candidate(record: Dict[str, Any]) -> Dict[str, Any]:
    keys = [
        "signal_id", "policy_id", "dataset", "entry_time", "direction", "priority", "component", "source",
        "lot_multiplier_candidate", "execution_mode", "profit_r_audit", "core_profit_r_audit", "coreb_profit_r_audit",
        "medium_profit_r_audit", "extra_coreb_exposure",
    ]
    return {k: record.get(k) for k in keys}


def build_markdown(packet: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# GOLD live-audit packet")
    lines.append("")
    lines.append(f"Created UTC: {packet.get('created_utc')}")
    lines.append(f"Status: {packet.get('status')}")
    lines.append("")
    lines.append("## Safety gate")
    lines.append("")
    gate = packet.get("safety_gate", {})
    lines.append(f"- gate_status: `{gate.get('status')}`")
    lines.append(f"- discord_send_allowed: `{gate.get('discord_send_allowed')}`")
    lines.append(f"- mt5_order_allowed: `{gate.get('mt5_order_allowed')}`")
    lines.append(f"- ai_api_allowed: `{gate.get('ai_api_allowed')}`")
    lines.append(f"- live_hook_allowed: `{gate.get('live_hook_allowed')}`")
    lines.append("")
    lines.append("## Latest candidates")
    lines.append("")
    for rec in packet.get("latest_candidates", []):
        lines.append(f"### {rec.get('dataset')} {rec.get('entry_time')} {rec.get('direction')} {rec.get('priority')}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(rec, ensure_ascii=False, indent=2, allow_nan=False))
        lines.append("```")
        lines.append("")
    lines.append("## Notification preview")
    lines.append("")
    lines.append("```text")
    lines.append(packet.get("notification_preview_text", ""))
    lines.append("```")
    lines.append("")
    lines.append("No external transmission is performed by this packet builder.")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    candidate_dir = Path(args.candidate_dir).expanduser().resolve() if args.candidate_dir else default_candidate_dir()
    preview_dir = Path(args.preview_dir).expanduser().resolve() if args.preview_dir else default_preview_dir()
    config_path = resolve_path(args.config)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    latest_candidate_path = candidate_dir / "gold_v2_runtime_signal_candidates_latest.json"
    summary_candidate_path = candidate_dir / "gold_v2_runtime_signal_candidates_summary.json"
    preview_json_path = preview_dir / "gold_v2_notification_preview_latest.json"
    preview_text_path = preview_dir / "gold_v2_notification_preview_latest.txt"
    preview_summary_path = preview_dir / "gold_v2_notification_preview_summary.txt"

    required = [config_path, latest_candidate_path, summary_candidate_path, preview_json_path, preview_text_path]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        print("[ERROR] missing required files:")
        for p in missing:
            print(f"  {p}")
        return 2

    policy = load_json(config_path)
    latest_candidate = load_json(latest_candidate_path)
    summary_candidate = load_json(summary_candidate_path)
    preview = load_json(preview_json_path)
    preview_text = read_text_if_exists(preview_text_path)
    preview_summary_text = read_text_if_exists(preview_summary_path)

    latest_records = [compact_candidate(r) for r in latest_candidate.get("latest_by_dataset", [])]
    gate = safety_gate(policy, summary_candidate, preview)
    packet = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "AUDIT_ONLY_LIVE_PACKET",
        "policy_id": policy.get("policy_id"),
        "candidate_dir": str(candidate_dir),
        "preview_dir": str(preview_dir),
        "config_path": str(config_path),
        "record_count": summary_candidate.get("record_count"),
        "view": summary_candidate.get("view"),
        "latest_candidates": latest_records,
        "notification_preview_text": preview_text,
        "notification_preview_summary_text": preview_summary_text,
        "safety_gate": gate,
        "aggregate_summary": summary_candidate.get("summary", []),
        "next_allowed_step": "Inspect packet only. Future Discord/MT5 integration requires a separate explicit implementation and preflight.",
    }

    out_json = output_dir / "gold_v2_live_audit_packet_latest.json"
    out_md = output_dir / "GOLD_V2_LIVE_AUDIT_PACKET_LATEST.md"
    out_txt = output_dir / "gold_v2_live_audit_packet_latest.txt"
    out_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    out_md.write_text(build_markdown(packet), encoding="utf-8")
    out_txt.write_text(preview_text + "\n\n" + preview_summary_text, encoding="utf-8")

    print(f"[DONE] output_dir={output_dir}")
    print(f"safety_gate={gate.get('status')}")
    print(preview_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
