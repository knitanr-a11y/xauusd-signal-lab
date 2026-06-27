from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest


def load_module(repo_root: Path):
    path = repo_root / "scripts/gold_ml_v1/research_challenger/verify_final_research_challenger.py"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("verify_final_research_challenger", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_final_research_challenger_manifest_is_fail_closed() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    manifest_path = repo_root / "config/gold_ml_v1/research_challenger/final_20260627/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["final_stage"]["last_change"].startswith("GML1-WATCH-024-A")
    assert manifest["final_stage"]["components"]["A_CORE"] == "GML1-WATCH-022-C"
    assert manifest["ml_lineage"]["candidate_local_model_artifacts_present"] is False
    assert manifest["controls"] == {
        "audit_only": True,
        "model_promoted": False,
        "shadow_ready": False,
        "live_ready": False,
        "final_signal": False,
        "discord": False,
        "mt5_order": False,
    }
    assert len(manifest["artifact_names"]) == 15


def test_final_research_challenger_artifact_parity(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    package_root = repo_root / "config/gold_ml_v1/research_challenger/final_20260627"
    artifact_dir = package_root / "artifacts"
    manifest = json.loads((package_root / "manifest.json").read_text(encoding="utf-8"))
    if not all((artifact_dir / name).is_file() for name in manifest["artifact_names"]):
        pytest.skip("Exact local audit artifact pack is not installed in this checkout")
    module = load_module(repo_root)
    exit_code = module.run(artifact_dir, package_root / "manifest.json", tmp_path)
    assert exit_code == 0
    report = json.loads((tmp_path / "parity_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert all(item["passed"] for item in report["checks"])
    metrics = pd.read_csv(tmp_path / "final_metrics_by_year.csv").set_index("year")
    expected = {
        2024: {"trades": 271, "win_rate": 0.6568265682656826, "pf": 2.494488621652696, "R": 137.48083552627205, "DD": 5.907692307692287},
        2025: {"trades": 402, "win_rate": 0.5920398009950248, "pf": 2.0121618989110295, "R": 148.09279029902123, "DD": 7.384615384615387},
        2026: {"trades": 101, "win_rate": 0.6138613861386139, "pf": 1.8772867024210496, "R": 42.055774842215214, "DD": 6.7997924973867985},
    }
    for year, values in expected.items():
        for key, value in values.items():
            assert abs(float(metrics.loc[year, key]) - float(value)) <= 1e-9 * max(1.0, abs(float(value)))
    normalized = pd.read_csv(tmp_path / "normalized_final/final_research_challenger_2025.csv")
    assert not normalized["candidate_id"].isna().any()
    assert not normalized["w"].isna().any()
    assert set(normalized.loc[normalized["comp"].eq("A_CORE"), "candidate_id"]) == {"GML1-WATCH-022-C"}
