from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pandas as pd
import pytest


def load_builder(repo_root: Path):
    path = repo_root / "scripts/gold_ml_v1/research_challenger/build_local_runtime.py"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("build_local_runtime", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_runtime_contract_keeps_live_disabled() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    contract = json.loads((repo_root / "config/gold_ml_v1/research_challenger/runtime_20260628/runtime_contract.json").read_text(encoding="utf-8"))
    assert contract["mode"] == "historical_parity_audit_only"
    assert contract["controls"]["audit_only"] is True
    assert contract["controls"]["live_ready"] is False
    assert contract["controls"]["final_signal"] is False
    assert contract["controls"]["discord"] is False
    assert contract["controls"]["mt5_order"] is False
    assert contract["controls"]["p16_live"] is False
    assert contract["controls"]["p19_live"] is False


def test_historical_truth_registry_counts() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    registry_dir = repo_root / "config/gold_ml_v1/research_challenger/runtime_20260628/registries"
    p16 = pd.read_csv(registry_dir / "p16_ml_gate_historical_truth.csv")
    p19 = pd.read_csv(registry_dir / "p19_ml_gate_historical_truth.csv")
    assert p16.groupby("ml_gate_status").size().to_dict() == {"KEEP": 247, "REJECT": 40}
    assert p19.groupby("ml_gate_status").size().to_dict() == {"KEEP": 82, "REJECT": 14}


def test_full_raw_parity_when_local_csvs_are_available(tmp_path: Path) -> None:
    raw_dir_value = os.environ.get("GML1_RAW_DIR")
    if not raw_dir_value:
        pytest.skip("Set GML1_RAW_DIR to run the full 2023-2026 raw parity integration test")
    repo_root = Path(__file__).resolve().parents[2]
    module = load_builder(repo_root)
    raw_dir = Path(raw_dir_value)
    artifact_dir = repo_root / "config/gold_ml_v1/research_challenger/final_20260627/artifacts"
    truth_dir = repo_root / "config/gold_ml_v1/research_challenger/runtime_20260628/registries"
    rows, details = module.build(raw_dir, artifact_dir, truth_dir)
    module.write_outputs(rows, details, tmp_path, raw_dir, artifact_dir, truth_dir)
    assert details["passed"] is True
    assert details["raw_counts_all_available"] == {
        "A_CORE": 116,
        "B_STATE": 204,
        "P16_pre_ml": 287,
        "P16_historical_keep": 247,
        "P18": 166,
        "P19_pre_ml": 96,
        "P19_historical_keep": 82,
        "W024A": 46,
    }
    report = json.loads((tmp_path / "parity_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert all(item["passed"] for item in report["details"]["year_checks"].values())
