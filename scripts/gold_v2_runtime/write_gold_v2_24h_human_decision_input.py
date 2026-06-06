#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_DECISIONS = [
    "KEEP_SOURCE_RECOVERY_BLOCKED",
    "REQUEST_MORE_SOURCE_RECOVERY_AUDIT",
    "REJECT_SOURCE_RECOVERY_EXECUTION",
    "APPROVE_SOURCE_RECOVERY_EXECUTION",
]

OUT_DIR = "gold_v2_24h_source_recovery_execution_decision_intake_audit_only"
TEMPLATE_FILE = "gold_v2_24h_human_decision_input_template.json"
INPUT_FILE = "gold_v2_24h_human_decision_input.json"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs_root() -> Path:
    return files_root() / "FX_OUTPUTS"


def long_path(path: Path) -> Path:
    path = path if path.is_absolute() else path.resolve()
    if os.name != "nt":
        return path
    raw = str(path)
    if raw.startswith("\\\\?\\"):
        return Path(raw)
    if raw.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + raw[2:])
    return Path("\\\\?\\" + raw)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(long_path(path).read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict[str, Any]) -> None:
    long_path(path.parent).mkdir(parents=True, exist_ok=True)
    long_path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write GOLD V2 24H human decision input JSON without manual editing.")
    parser.add_argument("--decision", required=True, choices=ALLOWED_DECISIONS, help="Exact 24H decision value to write.")
    parser.add_argument("--notes", default="", help="Optional human/operator note.")
    args = parser.parse_args()

    out_dir = fx_outputs_root() / OUT_DIR
    template_path = out_dir / TEMPLATE_FILE
    input_path = out_dir / INPUT_FILE

    if not long_path(template_path).exists():
        raise SystemExit(
            "24H template is missing. Run scripts\\gold_v2_runtime\\bat\\24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_AUDIT_ONLY.bat first."
        )

    template = read_json(template_path)
    allowed = template.get("allowed_decision_values", ALLOWED_DECISIONS)
    if args.decision not in allowed:
        raise SystemExit(f"Decision is not in template allowed_decision_values: {args.decision}")

    payload = dict(template)
    payload["selected_decision_value"] = args.decision
    payload["human_operator_notes"] = args.notes
    payload["written_by_helper"] = "write_gold_v2_24h_human_decision_input.py"
    payload["written_utc"] = datetime.now(timezone.utc).isoformat()
    payload["source_recovery_execution_allowed_now"] = False
    payload["source_recovery_approved_by_24h"] = False
    payload["source_recovery_approved"] = False
    payload["source_recovery_executed"] = False
    payload["source_identity_finalized"] = False
    payload["source_identity_recovered"] = False
    payload["live_enabled"] = False
    payload["final_signal_allowed"] = False
    payload["discord_sent"] = False
    payload["mt5_order_sent"] = False
    payload["ai_api_called"] = False
    payload["live_hook_enabled"] = False
    payload["discord_send_allowed"] = False
    payload["mt5_order_allowed"] = False
    payload["ai_api_allowed"] = False
    payload["live_hook_allowed"] = False

    write_json(input_path, payload)
    print(json.dumps({
        "status": "24H_HUMAN_DECISION_INPUT_WRITTEN_AUDIT_ONLY",
        "decision": args.decision,
        "input_path": str(input_path),
        "source_recovery_execution_allowed_now": False,
        "source_recovery_approved_by_24h": False,
        "next_step": "Run 24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_AUDIT_ONLY.bat again to validate the input.",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
