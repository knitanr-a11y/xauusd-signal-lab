#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage289 local LightGBM artifact validation and loading.

Only locally trained raw LightGBM text files are accepted. There is no model
network download, compressed legacy fallback, or alternate-model fallback.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb

EXPECTED = {
    "stage280": {
        "model_file": "stage280_rev_long_2026_model.txt",
        "contract_file": "stage280_rev_long_2026_contract.json",
        "model_name": "STAGE280_REV_LONG_2026",
        "threshold": 0.5927349103795366,
        "fixture_time": "2026-06-19 08:00:00",
        "fixture_score": 0.5949591748604749,
    },
    "stage281": {
        "model_file": "stage281_med4h_cont_long_2026_model.txt",
        "contract_file": "stage281_med4h_cont_long_2026_contract.json",
        "model_name": "STAGE281_MED4H_CONT_LONG_2026",
        "threshold": 0.5525199124029727,
        "fixture_time": "2026-06-17 10:00:00",
        "fixture_score": 0.6586538142862226,
    },
}
PARITY_TOLERANCE = 1e-12
REPORT_FILE = "stage289_model_training_report.json"


class ArtifactValidationError(RuntimeError):
    """Raised when a Stage289 local model bundle is missing or inconsistent."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ArtifactValidationError(f"invalid JSON: {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _close(actual: Any, expected: float, tolerance: float = PARITY_TOLERANCE) -> bool:
    try:
        return abs(float(actual) - float(expected)) <= tolerance
    except Exception:
        return False


def validate_model_bundle(model_dir: Path) -> dict[str, Any]:
    """Validate report, contracts, parity values and hashes on every cycle."""
    model_dir = Path(model_dir)
    report_path = model_dir / REPORT_FILE
    if not report_path.exists():
        raise ArtifactValidationError(f"missing training report: {report_path}")
    report = read_json(report_path)
    if report.get("status") != "PASS":
        raise ArtifactValidationError(
            f"training report status is not PASS: {report.get('status')!r}"
        )
    if report.get("fit_uses_2026") is not False:
        raise ArtifactValidationError(
            "training report does not prove pre-2026 fit/calibration"
        )

    checks = report.get("checks") or {}
    expected_checks = {
        "stage280_threshold": EXPECTED["stage280"]["threshold"],
        "stage281_threshold": EXPECTED["stage281"]["threshold"],
        "stage280_fixture_score": EXPECTED["stage280"]["fixture_score"],
        "stage281_fixture_score": EXPECTED["stage281"]["fixture_score"],
    }
    for key, expected in expected_checks.items():
        if not _close(checks.get(key), expected):
            raise ArtifactValidationError(
                f"training report parity mismatch {key}: "
                f"got={checks.get(key)!r} expected={expected!r}"
            )

    report_hashes = report.get("artifact_sha256") or {}
    validated: dict[str, Any] = {
        "status": "PASS",
        "model_dir": str(model_dir),
        "report": report,
        "models": {},
    }
    for key, spec in EXPECTED.items():
        model_path = model_dir / str(spec["model_file"])
        contract_path = model_dir / str(spec["contract_file"])
        if not model_path.exists() or not contract_path.exists():
            raise ArtifactValidationError(
                f"missing {key} artifact: model={model_path.exists()} "
                f"contract={contract_path.exists()}"
            )
        contract = read_json(contract_path)
        if contract.get("model") != spec["model_name"]:
            raise ArtifactValidationError(f"{key} model name mismatch")
        if (
            contract.get("fit_start") != "2024-01-01"
            or contract.get("fit_end_exclusive") != "2025-07-01"
        ):
            raise ArtifactValidationError(f"{key} fit window mismatch")
        if (
            contract.get("cal_start") != "2025-07-01"
            or contract.get("cal_end_exclusive") != "2026-01-01"
        ):
            raise ArtifactValidationError(f"{key} calibration window mismatch")
        if not _close(contract.get("score_threshold"), float(spec["threshold"])):
            raise ArtifactValidationError(f"{key} threshold mismatch")
        if contract.get("fixture_time") != spec["fixture_time"]:
            raise ArtifactValidationError(f"{key} fixture time mismatch")
        if not _close(contract.get("fixture_score"), float(spec["fixture_score"])):
            raise ArtifactValidationError(f"{key} fixture score mismatch")
        features = contract.get("features")
        if (
            not isinstance(features, list)
            or not features
            or len(features) != len(set(features))
        ):
            raise ArtifactValidationError(
                f"{key} feature contract is empty or duplicated"
            )

        model_hash = sha256_file(model_path)
        if contract.get("model_sha256") != model_hash:
            raise ArtifactValidationError(
                f"{key} model SHA256 mismatch against contract"
            )
        if report_hashes.get(model_path.name) != model_hash:
            raise ArtifactValidationError(
                f"{key} model SHA256 mismatch against training report"
            )
        contract_hash = sha256_file(contract_path)
        if report_hashes.get(contract_path.name) != contract_hash:
            raise ArtifactValidationError(
                f"{key} contract SHA256 mismatch against training report"
            )
        validated["models"][key] = {
            "model_path": model_path,
            "contract_path": contract_path,
            "contract": contract,
            "model_sha256": model_hash,
        }
    return validated


def load_frozen_booster(path: Path) -> lgb.Booster:
    """Load only a validated raw local LightGBM text model."""
    path = Path(path)
    if path.suffix.lower() != ".txt":
        raise ArtifactValidationError(
            f"only raw local .txt models are allowed: {path}"
        )
    if not path.exists():
        raise FileNotFoundError(path)
    return lgb.Booster(model_file=str(path))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Stage289 local model bundle"
    )
    parser.add_argument("--model-dir", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = validate_model_bundle(
            Path(args.model_dir).expanduser().resolve()
        )
    except Exception as exc:
        print(
            json.dumps(
                {"status": "BLOCKED", "reason": repr(exc)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "status": "PASS",
                "model_dir": result["model_dir"],
                "models": {
                    key: {
                        "model_sha256": value["model_sha256"],
                        "score_threshold": value["contract"]["score_threshold"],
                    }
                    for key, value in result["models"].items()
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
