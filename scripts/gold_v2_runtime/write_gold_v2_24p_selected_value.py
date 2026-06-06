#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

VALUE = "APPROVE_SOURCE_RECOVERY_READINESS_FOR_LATER_INTAKE"
OUT_DIR = "gold_v2_24p_source_recovery_readiness_decision_intake_audit_only"
OUT_FILE = "gold_v2_24p_human_decision_input.json"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx_outputs_root() -> Path:
    root = repo_root()
    files_root = root.parents[1] if len(root.parents) >= 2 else root.parent
    return files_root / "FX_OUTPUTS"


def lp(path: Path) -> Path:
    path = path if path.is_absolute() else path.resolve()
    if os.name != "nt":
        return path
    raw = str(path)
    if raw.startswith("\\\\?\\"):
        return Path(raw)
    if raw.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + raw[2:])
    return Path("\\\\?\\" + raw)


def main() -> int:
    out = fx_outputs_root() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    payload = {
        "created_by_helper": "write_gold_v2_24p_selected_value.py",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "audit_only": True,
        "selected_decision_value": VALUE,
        "human_operator_notes": "selected by operator; 24P validates for later routing audit only",
    }
    target = out / OUT_FILE
    lp(target).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"written": str(target), "selected_decision_value": VALUE}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
