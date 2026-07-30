from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "btc_ml_v1"
    / "BCR05A_outcome_blind_track_a_signature"
    / "python"
    / "run_bcr05a_core_reproduction.py"
)
spec = importlib.util.spec_from_file_location("bcr05a_core", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_bh_is_monotone_in_ranked_p_values() -> None:
    p = pd.Series([0.04, 0.001, 0.02, 0.9])
    q = module.bh(p)
    ordered = q.iloc[np.argsort(p.to_numpy())].to_numpy()
    assert np.all(np.diff(ordered) >= -1e-15)
    assert np.all((q >= 0) & (q <= 1))


def test_rci_zones_are_frozen_and_non_overlapping() -> None:
    values = [-100, -80, -79.9, -40, -39.9, 0, 0.1, 39.9, 40, 79.9, 80, 100]
    expected = [
        "LE_NEG80", "LE_NEG80", "NEG80_NEG40", "NEG80_NEG40",
        "NEG40_ZERO", "NEG40_ZERO", "ZERO_40", "ZERO_40",
        "40_80", "40_80", "GE_80", "GE_80",
    ]
    assert [module.zone(value) for value in values] == expected


def test_core_script_contains_no_event_distance_predictor() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "distance_to_nearest_source_event_bin" not in source
    assert "bars_until_next_source_event" not in source
    assert "label_derived_event_distance_tested':False" in source
