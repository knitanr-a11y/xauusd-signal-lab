#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).with_name("gold_v3_99_recent_closed_candle_signal_replay_audit.py")
NEEDLE = '    "68_rank_dedup_selection_repro_audit_only",\n'
INSERT = '    "67_health_gate_rehydration_audit_only",\n'


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if INSERT in text:
        print("Stage67 dependency already present")
        return 0
    if NEEDLE not in text:
        print("Target insertion point not found")
        return 1
    text = text.replace(NEEDLE, NEEDLE + INSERT, 1)
    TARGET.write_text(text, encoding="utf-8")
    print(f"Patched: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
