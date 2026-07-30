from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "btc_ml_v1"
    / "BCR04_outcome_blind_decision_universe"
    / "python"
    / "run_bcr04_core_reproduction.py"
)
spec = importlib.util.spec_from_file_location("bcr04_core", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_rci_monotone_extremes() -> None:
    assert module.rci(np.arange(1.0, 10.0)) == 100.0
    assert module.rci(np.arange(9.0, 0.0, -1.0)) == -100.0


def test_event_class_separates_events_and_state_controls() -> None:
    assert module.event_class("PRIMARY_LONG", "IDLE") == "PRIMARY_LONG_EVENT"
    assert module.event_class("SHORT_EXIT", "ACTIVE_SHORT") == "VALID_SHORT_EXIT_EVENT"
    assert module.event_class("REENTRY_LONG", "ACTIVE_LONG") == "REENTRY_EVENT"
    assert module.event_class(None, "IDLE") == "IDLE_NON_EVENT_CONTROL"
    assert module.event_class(None, "ACTIVE_LONG") == "ACTIVE_LONG_NON_EVENT_CONTROL"
    assert module.event_class(None, "ACTIVE_SHORT") == "ACTIVE_SHORT_NON_EVENT_CONTROL"
