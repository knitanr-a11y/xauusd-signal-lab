from __future__ import annotations

import importlib.util
import sys
from itertools import product
from pathlib import Path

import pandas as pd

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "btc_ml_v1"
    / "BCR05B_outcome_blind_finite_entry_grammar"
    / "python"
    / "run_bcr05b_finite_entry_grammar.py"
)
spec = importlib.util.spec_from_file_location("bcr05b", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_exact_twelve_grammar_ids_per_direction() -> None:
    for direction in ("LONG", "SHORT"):
        ids = {
            f"A_{direction}_{ema}_{zone}_{ret}"
            for ema, zone, ret in product(("E0", "E1"), ("Z0", "Z1", "Z2"), ("P0", "P1"))
        }
        assert len(ids) == 12


def test_recall_tiers_are_frozen() -> None:
    assert module.tier(1.0) == "FULL_COVERAGE"
    assert module.tier(0.9) == "HIGH_COVERAGE"
    assert module.tier(0.899999) == "BALANCED_COVERAGE"
    assert module.tier(0.75) == "BALANCED_COVERAGE"
    assert module.tier(0.749999) is None


def test_pareto_dominance() -> None:
    table = pd.DataFrame(
        {
            "source_event_recall": [1.0, 0.9, 0.9, 0.8],
            "control_fire_rate": [0.10, 0.05, 0.07, 0.01],
        }
    )
    assert module.pareto(table).tolist() == [True, True, False, True]


def test_script_has_no_forbidden_source_distance_predicate() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "distance_to_nearest_source_event" not in source
    assert "bars_until_next_source_event" not in source
    assert "source_state_age" not in source
