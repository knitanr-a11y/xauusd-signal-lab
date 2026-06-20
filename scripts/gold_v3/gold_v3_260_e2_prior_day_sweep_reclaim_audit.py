#!/usr/bin/env python3
"""GOLD V3 Stage260 E2 prior-session sweep/reclaim audit-only entry point."""
from __future__ import annotations
import sys
from pathlib import Path
_THIS = str(Path(__file__).resolve().parent)
if _THIS not in sys.path:
    sys.path.insert(0, _THIS)
from stage260_e2_common import *
from stage260_e2_event import *
from stage260_e2_evaluation import *
from stage260_e2_runner import main, readiness_audit, run_e2

if __name__ == "__main__":
    raise SystemExit(main())
