#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepare only verifiably exact Stage289 models.

Stage281 is reproducible and may be trained locally. Stage280 is never rebuilt
from an approximate reconstruction: an original model artifact plus a
provenance-bearing contract is required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from gold_v3_289_train_live_models_audit import (
    EXP281,
    SCORE281,
    TIME281,
    close,
    stage281,
)

STAGE280_THRESHOLD = 0.5927349103795366
STAGE280_FIXTURE_SCORE = 0.5949591748604749
STAGE280_FIXTURE_TIME = "2026-06-19 08:00:00"
STAGE280_MODEL_NAME = "STAGE280_REV_LONG_2026"
STAGE281_MODEL_NAME = "STAGE281_MED4H_CONT_LONG_2026"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--model-dir", default="")
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_existing_stage281(model_dir: Path) -> tuple[bool, dict[str, Any]]:
    model_path = model_dir / "stage281_med4h_cont_long_2026_model.txt"
    contract_path = model_dir / "stage281_med4h_cont_long_2026_contract.json"
    if not model_path.exists() or not contract_path.exists():
        return False, {"reason": "artifact_missing"}
    try:
        contract = read_json(contract_path)
    except Exception as exc:  # pragma: no cover - defensive filesystem path
        return False, {"reason": "contract_unreadable", "error": str(exc)}
    expected_hash = contract.get("model_sha256")
    actual_hash = file_sha256(model_path)
    valid = bool(
        contract.get("model") == STAGE281_MODEL_NAME
        and close(contract.get("score_threshold"), EXP281)
        and close(contract.get("fixture_score"), SCORE281)
        and contract.get("fixture_time") == TIME281
        and isinstance(expected_hash, str)
        and expected_hash == actual_hash
    )
    return valid, {
        "reason": "valid" if valid else "contract_or_hash_mismatch",
        "model_sha256": actual_hash,
        "contract": contract,
    }


def write_stage281(candle_dir: Path, model_dir: Path) -> dict[str, Any]:
    feature_list = Path(__file__).resolve().with_name(
        "gold_v3_stage281_live_feature_list.txt"
    )
    model, features, threshold, fixture_score, counts = stage281(
        candle_dir, feature_list
    )
    parity = close(threshold, EXP281) and close(fixture_score, SCORE281)
    if not parity:
        return {
            "status": "BLOCKED_STAGE281_PARITY_MISMATCH",
            "threshold": threshold,
            "fixture_score": fixture_score,
            "expected_threshold": EXP281,
            "expected_fixture_score": SCORE281,
            "counts": counts,
        }

    model_path = model_dir / "stage281_med4h_cont_long_2026_model.txt"
    contract_path = model_dir / "stage281_med4h_cont_long_2026_contract.json"
    model_path.write_text(model.booster_.model_to_string(), encoding="utf-8")
    model_hash = file_sha256(model_path)
    contract = {
        "model": STAGE281_MODEL_NAME,
        "features": features,
        "fit_start": "2024-01-01",
        "fit_end_exclusive": "2025-07-01",
        "cal_start": "2025-07-01",
        "cal_end_exclusive": "2026-01-01",
        "score_quantile": "q85",
        "score_threshold": threshold,
        "fixture_time": TIME281,
        "fixture_score": fixture_score,
        "model_sha256": model_hash,
        "source_provenance": {
            "kind": "exact_local_reproduction",
            "verified": True,
            "fit_uses_2026": False,
        },
    }
    contract_path.write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "status": "PASS_STAGE281_EXACT_SAVED",
        "threshold": threshold,
        "fixture_score": fixture_score,
        "counts": counts,
        "model_sha256": model_hash,
    }


def validate_stage280_original(model_dir: Path) -> dict[str, Any]:
    model_path = model_dir / "stage280_rev_long_2026_model.txt"
    contract_path = model_dir / "stage280_rev_long_2026_contract.json"
    if not model_path.exists():
        return {
            "status": "BLOCKED_STAGE280_EXACT_SOURCE_MISSING",
            "missing": [str(model_path)],
            "reason": (
                "The original Stage280 model artifact was not committed. "
                "Stage300 evaluated 335 reconstructions and found zero exact matches."
            ),
        }
    if not contract_path.exists():
        return {
            "status": "BLOCKED_STAGE280_SOURCE_UNVERIFIED",
            "missing": [str(contract_path)],
            "reason": "A model without a provenance-bearing contract is not accepted.",
        }
    try:
        contract = read_json(contract_path)
    except Exception as exc:
        return {
            "status": "BLOCKED_STAGE280_SOURCE_UNVERIFIED",
            "reason": "Stage280 contract is unreadable.",
            "error": str(exc),
        }

    provenance = contract.get("source_provenance")
    expected_hash = contract.get("model_sha256")
    actual_hash = file_sha256(model_path)
    valid_provenance = bool(
        isinstance(provenance, dict)
        and provenance.get("verified") is True
        and provenance.get("kind")
        in {"original_model_artifact", "exact_training_reproduction"}
    )
    valid = bool(
        contract.get("model") == STAGE280_MODEL_NAME
        and close(contract.get("score_threshold"), STAGE280_THRESHOLD)
        and close(contract.get("fixture_score"), STAGE280_FIXTURE_SCORE)
        and contract.get("fixture_time") == STAGE280_FIXTURE_TIME
        and isinstance(expected_hash, str)
        and expected_hash == actual_hash
        and valid_provenance
    )
    return {
        "status": "PASS_STAGE280_EXACT_SOURCE_VERIFIED"
        if valid
        else "BLOCKED_STAGE280_SOURCE_UNVERIFIED",
        "model_sha256": actual_hash,
        "contract": contract,
        "reason": "valid" if valid else "contract, hash, or provenance mismatch",
    }


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    model_dir = (
        Path(args.model_dir).expanduser().resolve()
        if args.model_dir
        else Path(__file__).resolve().with_name("models") / "gold_v3_289"
    )
    model_dir.mkdir(parents=True, exist_ok=True)

    stage281_valid, stage281_existing = validate_existing_stage281(model_dir)
    stage281_result = (
        {"status": "PASS_STAGE281_EXACT_REUSED", **stage281_existing}
        if stage281_valid
        else write_stage281(candle_dir, model_dir)
    )
    if not stage281_result["status"].startswith("PASS_"):
        report = {
            "status": stage281_result["status"],
            "stage281": stage281_result,
            "stage280": {"status": "NOT_CHECKED"},
            "closed_csv_contract": True,
            "approximate_model_forbidden": True,
        }
        (model_dir / "stage301_exact_model_source_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 3

    stage280_result = validate_stage280_original(model_dir)
    ready = stage280_result["status"] == "PASS_STAGE280_EXACT_SOURCE_VERIFIED"
    report = {
        "status": "PASS_EXACT_MODELS_READY"
        if ready
        else stage280_result["status"],
        "stage280": stage280_result,
        "stage281": stage281_result,
        "evidence": {
            "stage300_evaluated_models": 335,
            "stage300_exact_matches": 0,
            "original_pr6_training_source_committed": False,
            "original_pr6_workflow_artifacts": 0,
            "original_pr6_comments": 0,
        },
        "required_stage280_recovery": [
            "original stage280_rev_long_2026_model.txt",
            "matching contract with model_sha256",
            "source_provenance.kind=original_model_artifact or exact_training_reproduction",
            "source_provenance.verified=true",
            f"score_threshold={STAGE280_THRESHOLD}",
            f"fixture_time={STAGE280_FIXTURE_TIME}",
            f"fixture_score={STAGE280_FIXTURE_SCORE}",
        ],
        "closed_csv_contract": True,
        "candidate_removed": False,
        "approximate_model_forbidden": True,
        "final_signal": False,
        "mt5_order": False,
        "discord": False,
    }
    (model_dir / "stage301_exact_model_source_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
