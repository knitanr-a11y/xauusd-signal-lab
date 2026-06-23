from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "scripts" / "gold_v3_runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from gold_v3_301_prepare_exact_models import validate_stage280_original


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stage280_missing_original_artifact_blocks(tmp_path):
    result = validate_stage280_original(tmp_path)
    assert result["status"] == "BLOCKED_STAGE280_EXACT_SOURCE_MISSING"
    assert "335 reconstructions" in result["reason"]


def test_stage280_unverified_contract_blocks(tmp_path):
    model = tmp_path / "stage280_rev_long_2026_model.txt"
    contract = tmp_path / "stage280_rev_long_2026_contract.json"
    model.write_text("not-the-original-model", encoding="utf-8")
    contract.write_text(
        json.dumps(
            {
                "model": "STAGE280_REV_LONG_2026",
                "score_threshold": 0.5927349103795366,
                "fixture_time": "2026-06-19 08:00:00",
                "fixture_score": 0.5949591748604749,
                "model_sha256": sha256(model),
                "source_provenance": {
                    "kind": "approximate_reconstruction",
                    "verified": False,
                },
            }
        ),
        encoding="utf-8",
    )
    result = validate_stage280_original(tmp_path)
    assert result["status"] == "BLOCKED_STAGE280_SOURCE_UNVERIFIED"


def test_stage280_original_provenance_and_hash_can_pass(tmp_path):
    model = tmp_path / "stage280_rev_long_2026_model.txt"
    contract = tmp_path / "stage280_rev_long_2026_contract.json"
    model.write_text("fixture-original-model-placeholder", encoding="utf-8")
    contract.write_text(
        json.dumps(
            {
                "model": "STAGE280_REV_LONG_2026",
                "score_threshold": 0.5927349103795366,
                "fixture_time": "2026-06-19 08:00:00",
                "fixture_score": 0.5949591748604749,
                "model_sha256": sha256(model),
                "source_provenance": {
                    "kind": "original_model_artifact",
                    "verified": True,
                },
            }
        ),
        encoding="utf-8",
    )
    result = validate_stage280_original(tmp_path)
    assert result["status"] == "PASS_STAGE280_EXACT_SOURCE_VERIFIED"


def test_stage292_runner_uses_source_guard_every_time():
    runner = (
        RUNTIME / "bat" / "run_gold_v3_292_safe_portfolio_live.bat"
    ).read_text(encoding="utf-8")
    assert "gold_v3_301_prepare_exact_models.py" in runner
    assert "Verifying exact Stage289 model sources" in runner
    assert "gold_v3_289_train_live_models_audit.py" not in runner
    assert "Approximate Stage280 models are not accepted" in runner
