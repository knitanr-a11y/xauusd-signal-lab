from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frozen_trigger_kernel_validation_core as core


class FrozenObservationContractError(core.FrozenKernelContractError):
    pass


def _freeze_samples(
    samples: list[core.DecisionSample], manifest: dict[str, Any]
) -> tuple[list[core.DecisionSample], dict[str, Any]]:
    contract = manifest.get("observation_contract")
    if not isinstance(contract, dict):
        raise FrozenObservationContractError("observation_contract missing")
    windows = contract.get("ticker_windows")
    expected_ids_by_ticker = contract.get("frozen_raw_alert_ids")
    expected_counts = contract.get("expected_counts")
    if not isinstance(windows, dict) or not isinstance(expected_ids_by_ticker, dict):
        raise FrozenObservationContractError("frozen window or event IDs missing")
    if not isinstance(expected_counts, dict):
        raise FrozenObservationContractError("frozen expected counts missing")

    frozen: list[core.DecisionSample] = []
    later_event_ids: list[int] = []
    for ticker, window in sorted(windows.items()):
        start = datetime.strptime(str(window["start_utc"]), "%Y-%m-%dT%H:%M:%SZ")
        end = datetime.strptime(str(window["end_utc"]), "%Y-%m-%dT%H:%M:%SZ")
        expected_ids = [int(value) for value in expected_ids_by_ticker[ticker]]
        allowed_ids = set(expected_ids)
        ticker_rows = [row for row in samples if row.ticker == ticker]
        unexpected = [
            int(row.raw_alert_id)
            for row in ticker_rows
            if row.transition != "NO_EVENT"
            and row.raw_alert_id is not None
            and int(row.raw_alert_id) not in allowed_ids
            and row.decision_time_utc <= end
        ]
        if unexpected:
            raise FrozenObservationContractError(
                f"delayed/new source events alter frozen window for {ticker}: {unexpected}"
            )
        for row in ticker_rows:
            if start <= row.decision_time_utc <= end:
                frozen.append(row)
            elif (
                row.transition != "NO_EVENT"
                and row.raw_alert_id is not None
                and row.decision_time_utc > end
            ):
                later_event_ids.append(int(row.raw_alert_id))
        actual_ids = [
            int(row.raw_alert_id)
            for row in frozen
            if row.ticker == ticker
            and row.transition != "NO_EVENT"
            and row.raw_alert_id is not None
        ]
        if actual_ids != expected_ids:
            raise FrozenObservationContractError(
                f"frozen source event IDs changed for {ticker}: "
                f"actual={actual_ids} expected={expected_ids}"
            )

    frozen.sort(key=lambda row: (row.ticker, row.decision_time_utc, row.raw_alert_id or -1))
    counts = {
        "decision_sample_count": len(frozen),
        "event_decision_count": sum(row.transition != "NO_EVENT" for row in frozen),
        "no_event_decision_count": sum(row.transition == "NO_EVENT" for row in frozen),
    }
    for key, actual in counts.items():
        expected = int(expected_counts[key])
        if actual != expected:
            raise FrozenObservationContractError(
                f"frozen observation count changed for {key}: {actual} != {expected}"
            )

    ticker_coverage = []
    for ticker, window in sorted(windows.items()):
        rows = [row for row in frozen if row.ticker == ticker]
        ticker_coverage.append(
            {
                "ticker": ticker,
                "offset_hours": float(window["offset_hours"]),
                "observation_start_utc": window["start_utc"],
                "observation_end_utc": window["end_utc"],
                "decision_count": len(rows),
                "event_count": sum(row.transition != "NO_EVENT" for row in rows),
                "no_event_count": sum(row.transition == "NO_EVENT" for row in rows),
                "negative_labels_outside_observation_window_used": False,
            }
        )
    return frozen, {
        **counts,
        "ticker_coverage": ticker_coverage,
        "post_freeze_event_ids_excluded_from_m7b": sorted(set(later_event_ids)),
        "post_freeze_events_used_for_formula_change": False,
    }


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="M7B frozen Mochipoyo trigger-kernel validation (audit-only)."
    )
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--mt5-files-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--built-at-utc", default=_utc_now_text())
    args = parser.parse_args()

    manifest = core.load_and_validate_manifest(args.manifest)
    connection = sqlite3.connect(args.database)
    connection.row_factory = sqlite3.Row
    try:
        all_samples, upstream_coverage = core.build_decision_samples(
            connection,
            mt5_files_root=args.mt5_files_root,
            built_at_utc=args.built_at_utc,
        )
        frozen_samples, frozen_coverage = _freeze_samples(all_samples, manifest)
        original_builder = core.build_decision_samples
        core.build_decision_samples = lambda *unused_args, **unused_kwargs: (
            frozen_samples,
            frozen_coverage,
        )
        try:
            report = core.audit_frozen_trigger_kernels(
                connection,
                mt5_files_root=args.mt5_files_root,
                built_at_utc=args.built_at_utc,
                manifest=manifest,
            )
        finally:
            core.build_decision_samples = original_builder
        report["upstream_current_coverage"] = upstream_coverage
        report["frozen_observation_enforced"] = True
    except (
        core.FrozenKernelContractError,
        core.TriggerSignatureContractError,
        FrozenObservationContractError,
    ) as exc:
        raise SystemExit(f"M7B fail-closed: {exc}") from exc
    finally:
        connection.close()

    paths = core.write_outputs(args.output_dir, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "m7c_decision": report["m7c_decision"],
                "outputs": paths,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
