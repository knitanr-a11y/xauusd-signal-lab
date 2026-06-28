from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


def load_builder(repo_root: Path):
    path = repo_root / "scripts/gold_ml_v1/research_challenger/build_local_runtime.py"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("build_local_runtime", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runtime_contract_keeps_execution_disabled() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "config/gold_ml_v1/research_challenger/runtime_20260628/runtime_contract.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    controls = contract["controls"]
    assert controls["audit_only"] is True
    assert controls["live_ready"] is False
    assert controls["final_signal"] is False
    assert controls["discord"] is False
    assert controls["mt5_order"] is False
    assert controls["p16_live"] is False
    assert controls["p19_live"] is False


def test_frozen_exclusion_contract() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    registry = repo_root / "config/gold_ml_v1/research_challenger/runtime_20260628/registries"
    p16 = pd.concat([pd.read_csv(path) for path in sorted(registry.glob("p16_exclusions_*.csv"))], ignore_index=True)
    p19 = pd.read_csv(registry / "p19_exclusions.csv")
    assert len(p16) == 40 and not p16["decision_time"].duplicated().any()
    assert len(p19) == 14 and not p19["decision_time"].duplicated().any()


def test_embedded_final_contract() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    builder = load_builder(repo_root)
    assert {year: item["rows"] for year, item in builder.FINAL_ROW_CONTRACT.items()} == {2024: 271, 2025: 402, 2026: 101}
    assert builder.EXPECTED_FINAL[2024]["pf"] == 2.494488621652696
    assert builder.EXPECTED_FINAL[2025]["pf"] == 2.0121618989110295
    assert builder.EXPECTED_FINAL[2026]["pf"] == 1.8772867024210496
