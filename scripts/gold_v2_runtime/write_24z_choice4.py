#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOD_PATH = HERE / "audit_gold_v2_24z_choice_intake_audit_only.py"
TEMPLATE_FILE = "gold_v2_24z_human_decision_input_template.json"
OUTPUT_FILE = "gold_v2_24z_human_decision_input.json"
CHOICE_INDEX = 3


def load_mod():
    spec = importlib.util.spec_from_file_location("m24z", MOD_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load 24z module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    mod = load_mod()
    out = mod.fx() / mod.OUT_DIR
    mod.lp(out).mkdir(parents=True, exist_ok=True)
    template_path = out / TEMPLATE_FILE
    template = json.loads(mod.lp(template_path).read_text(encoding="utf-8"))
    allowed = template.get("allowed_decision_values", [])
    selected = str(allowed[CHOICE_INDEX]).strip()
    payload = {
        "created_by_helper": "write_24z_choice4.py",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "audit_only": True,
        "selected_decision_value": selected,
        "human_operator_notes": "operator selected template option index 3; later checks remain audit-only",
    }
    target = out / OUTPUT_FILE
    mod.lp(target).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"written": str(target), "selected_decision_value": selected}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
