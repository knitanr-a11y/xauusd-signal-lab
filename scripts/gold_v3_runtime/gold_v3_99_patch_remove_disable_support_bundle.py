#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).with_name("gold_v3_99_recent_closed_candle_signal_replay_audit.py")
OLD = ', "--disable-auto-support-bundle"'


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if OLD not in text:
        print("No --disable-auto-support-bundle flag found; nothing to patch")
        return 0
    text = text.replace(OLD, "")
    TARGET.write_text(text, encoding="utf-8")
    print(f"Patched: removed --disable-auto-support-bundle from {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
