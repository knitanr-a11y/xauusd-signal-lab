from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

EXPECTED_PROPOSAL_SHA = "b5e017f2e8b08b8fdad3bcd9ca603155510d23cf2385bbcde2a36bdeff456c0b"
EXPECTED_COUNTS = {
    "GML1-EVT-001-L": 239,
    "GML1-EVT-002-S": 153,
    "GML1-EVT-003-L": 256,
    "GML1-EVT-003-S": 183,
}
EXPECTED_STANDARD = {
    "trades": 319,
    "long_trades": 213,
    "short_trades": 106,
    "strong_total_r": 36.978322539153,
    "strong_mean_r": 0.115919506392,
    "strong_profit_factor": 1.211214,
    "extreme_total_r": 17.307978687831,
    "strong_maximum_drawdown_r": 12.0471574024,
}


def close(actual: float, expected: float, tolerance: float = 1e-6) -> bool:
    return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=tolerance)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal-summary", type=Path, required=True)
    parser.add_argument("--policy-metrics", type=Path, required=True)
    args = parser.parse_args()

    summary = json.loads(args.proposal_summary.read_text(encoding="utf-8"))
    errors: list[str] = []
    if summary["proposal_registry_sha256"] != EXPECTED_PROPOSAL_SHA:
        errors.append("proposal registry SHA mismatch")
    counts = {item["candidate_id"]: int(item["events"]) for item in summary["candidate_counts"]}
    if counts != EXPECTED_COUNTS:
        errors.append(f"candidate counts mismatch: {counts}")
    if int(summary["unique_decisions"]) != 831 or int(summary["same_time_overlap"]) != 0:
        errors.append("event uniqueness mismatch")

    metrics = pd.read_csv(args.policy_metrics)
    selected = metrics.loc[
        (metrics["fold"] == "AGGREGATE_OOS")
        & (metrics["policy"] == "standard")
        & (metrics["view"] == "ONE_POSITION")
    ]
    if len(selected) != 1:
        errors.append("standard aggregate row missing")
    else:
        row = selected.iloc[0]
        for key, expected in EXPECTED_STANDARD.items():
            actual = row[key]
            if isinstance(expected, int):
                if int(actual) != expected:
                    errors.append(f"{key}: expected {expected}, got {actual}")
            elif not close(actual, expected):
                errors.append(f"{key}: expected {expected}, got {actual}")

    if errors:
        raise SystemExit("ACTIVE EVENT CORE REFERENCE FAILED\n" + "\n".join(errors))
    print("ACTIVE EVENT CORE REFERENCE PASSED; deployment remains disabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
