#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

TOLERANCE = 1e-12
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, repr(exc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def close(actual: Any, expected: float) -> bool:
    try:
        return abs(float(actual) - float(expected)) <= TOLERANCE
    except Exception:
        return False


def inspect_model(model_dir: Path, report: dict[str, Any] | None, key: str) -> dict[str, Any]:
    spec = EXPECTED[key]
    model_path = model_dir / spec["model_file"]
    contract_path = model_dir / spec["contract_file"]
    checks: dict[str, Any] = {
        "model_exists": model_path.exists(),
        "contract_exists": contract_path.exists(),
    }
    errors: list[str] = []
    contract: dict[str, Any] | None = None
    model_hash = None
    contract_hash = None

    if contract_path.exists():
        contract, error = read_json(contract_path)
        if error:
            errors.append(f"invalid_contract:{error}")
    if model_path.exists():
        try:
            model_hash = sha256_file(model_path)
        except Exception as exc:
            errors.append(f"model_hash_error:{exc!r}")
    if contract_path.exists():
        try:
            contract_hash = sha256_file(contract_path)
        except Exception as exc:
            errors.append(f"contract_hash_error:{exc!r}")

    report_checks = (report or {}).get("checks") or {}
    report_hashes = (report or {}).get("artifact_sha256") or {}
    checks.update(
        {
            "report_threshold_exact": close(report_checks.get(f"{key}_threshold"), spec["threshold"]),
            "report_fixture_exact": close(report_checks.get(f"{key}_fixture_score"), spec["fixture_score"]),
            "contract_model_name": bool(contract and contract.get("model") == spec["model_name"]),
            "contract_fit_window": bool(
                contract
                and contract.get("fit_start") == "2024-01-01"
                and contract.get("fit_end_exclusive") == "2025-07-01"
            ),
            "contract_cal_window": bool(
                contract
                and contract.get("cal_start") == "2025-07-01"
                and contract.get("cal_end_exclusive") == "2026-01-01"
            ),
            "contract_threshold_exact": bool(contract and close(contract.get("score_threshold"), spec["threshold"])),
            "contract_fixture_time": bool(contract and contract.get("fixture_time") == spec["fixture_time"]),
            "contract_fixture_exact": bool(contract and close(contract.get("fixture_score"), spec["fixture_score"])),
            "contract_features_valid": bool(
                contract
                and isinstance(contract.get("features"), list)
                and contract.get("features")
                and len(contract["features"]) == len(set(contract["features"]))
            ),
            "model_hash_matches_contract": bool(
                contract and model_hash and contract.get("model_sha256") == model_hash
            ),
            "model_hash_matches_report": bool(
                model_hash and report_hashes.get(spec["model_file"]) == model_hash
            ),
            "contract_hash_matches_report": bool(
                contract_hash and report_hashes.get(spec["contract_file"]) == contract_hash
            ),
        }
    )
    exact_ready = all(bool(value) for value in checks.values()) and not errors
    return {
        "key": key,
        "model_path": str(model_path),
        "contract_path": str(contract_path),
        "model_sha256": model_hash,
        "contract_sha256": contract_hash,
        "checks": checks,
        "errors": errors,
        "exact_ready": exact_ready,
    }


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    model_dir = repo_root / "scripts" / "gold_v3_runtime" / "models" / "gold_v3_289"
    report_path = model_dir / "stage289_model_training_report.json"
    report, report_error = read_json(report_path) if report_path.exists() else (None, None)

    models = {
        key: inspect_model(model_dir, report, key)
        for key in ("stage280", "stage281")
    }
    stage280_ready = bool(models["stage280"]["exact_ready"])
    stage281_ready = bool(models["stage281"]["exact_ready"])

    if not stage280_ready and stage281_ready:
        decision = "STAGE280_BLOCKED_STAGE281_EXACT_READY"
    elif not stage280_ready and not stage281_ready:
        decision = "STAGE280_BLOCKED_STAGE281_NOT_READY"
    elif stage280_ready and stage281_ready:
        decision = "BOTH_EXACT_READY_UNEXPECTED_RECHECK_STAGE280_PROVENANCE"
    else:
        decision = "STAGE280_READY_STAGE281_NOT_READY"

    report_out = {
        "status": "GOLD_V3_303_STAGE280_BLOCK_STAGE281_READINESS_READY",
        "repo_root": str(repo_root),
        "model_dir": str(model_dir),
        "training_report": {
            "path": str(report_path),
            "exists": report_path.exists(),
            "parse_error": report_error,
            "status": (report or {}).get("status"),
            "fit_uses_2026": (report or {}).get("fit_uses_2026"),
        },
        "parity_tolerance": TOLERANCE,
        "models": models,
        "decision": decision,
        "policy": {
            "stage280": "BLOCKED unless exact original artifact provenance and parity are both proven",
            "stage281": "may remain eligible only when its own artifact, contract, report values, and hashes are exact",
            "fallback": False,
            "approximate_model_promotion": False,
        },
        "safety_flags": {
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
        "note": "Diagnostic only. No model, threshold, expected value, signal, order, Discord, or partial-close state is changed.",
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report_out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
