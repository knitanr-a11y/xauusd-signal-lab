from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

EXPECTED = {
    "trades": 113,
    "long_trades": 83,
    "short_trades": 30,
    "strong_total_r": 11.6373977593109,
    "strong_profit_factor": 1.1848033711294401,
    "extreme_total_r": 6.169841678618901,
    "strong_maximum_drawdown_r": 6.25765586492,
}
EXPECTED_FOLDS = {
    "F1": 0.036156274829999946,
    "F2": -0.7647191974699996,
    "F3": 10.6485166797919,
    "F4": 1.7174440021590003,
}


def close(actual: float, expected: float, tolerance: float = 1e-9) -> bool:
    return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=tolerance)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    conservative = summary["conservative_one_position"]
    errors: list[str] = []
    for key, expected in EXPECTED.items():
        actual = conservative[key]
        if isinstance(expected, int):
            if int(actual) != expected:
                errors.append(f"{key}: expected {expected}, got {actual}")
        elif not close(actual, expected):
            errors.append(f"{key}: expected {expected}, got {actual}")
    for fold, expected in EXPECTED_FOLDS.items():
        actual = summary["fold_conservative_strong_r"][fold]
        if not close(actual, expected):
            errors.append(f"{fold}: expected {expected}, got {actual}")
    if summary["all_promotion_gates_passed"] is not False:
        errors.append("reference model unexpectedly passed all promotion gates")
    if summary["deployment_blocked"] is not True:
        errors.append("deployment block is not active")
    if errors:
        raise SystemExit("REFERENCE REPLAY FAILED\n" + "\n".join(errors))
    print("REFERENCE REPLAY PASSED: architecture reproduced; deployment remains blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
