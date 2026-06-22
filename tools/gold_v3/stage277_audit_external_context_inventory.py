#!/usr/bin/env python3
"""GOLD V3 Stage277 external causal-context availability auditor.

This tool consumes the read-only MT5 inventory CSVs produced by
ExportGoldV3ExternalContextInventory.mq5. It never downloads, fills, maps, or
substitutes a source. It produces availability artifacts only; it does not
create features, candidates, thresholds, performance grids, or live signals.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

DATE_FMT = "%Y.%m.%d %H:%M:%S"
TIMEFRAMES: tuple[str, ...] = ("M1", "M5", "M15", "H1", "H4", "D1")
TIMEFRAME_SECONDS: dict[str, int] = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "H1": 3600,
    "H4": 14400,
    "D1": 86400,
}
EXPECTED_SOURCE_GROUPS: tuple[str, ...] = (
    "XAGUSD",
    "USDJPY",
    "EURUSD",
    "US500_RISK_PROXY",
    "NAS100_RISK_PROXY",
    "USD_INDEX_PROXY",
    "YIELD_PROXY",
    "ECONOMIC_CALENDAR",
)

STATUS_PARTIAL = "GOLD_V3_277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_PARTIAL_AUDIT_ONLY"
STATUS_BLOCKED = "GOLD_V3_277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_BLOCKED_AUDIT_ONLY"
STATUS_INVENTORIED = "GOLD_V3_277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_INVENTORIED_AUDIT_ONLY"


class InventoryError(RuntimeError):
    """Raised when the supplied inventory violates a Stage277 contract."""


@dataclass(frozen=True)
class InputFiles:
    symbols: Path
    coverage: Path
    sessions: Path
    run_metadata: Path


@dataclass(frozen=True)
class AuditConfig:
    input_dir: Path
    output_dir: Path
    prefix: str
    expected_server: str | None
    expected_company: str | None
    expected_baseline_symbol: str | None


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit GOLD V3 Stage277 MT5 external-context inventory CSVs."
    )
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--prefix",
        default="gold_v3_stage277_external_context_inventory",
        help="MT5 output file prefix.",
    )
    parser.add_argument(
        "--expected-server",
        default=None,
        help="Optional exact MT5 account server, e.g. XMTrading-MT5 3.",
    )
    parser.add_argument(
        "--expected-company",
        default=None,
        help="Optional exact broker company string.",
    )
    parser.add_argument(
        "--expected-baseline-symbol",
        default=None,
        help="Optional exact GOLD baseline symbol, e.g. GOLD#.",
    )
    return parser.parse_args(argv)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise InventoryError(f"required input file is missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise InventoryError(f"CSV has no header: {path}")
        rows = [dict(row) for row in reader]
    return rows


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _require_columns(rows: Sequence[Mapping[str, str]], required: Sequence[str], label: str) -> None:
    if not rows:
        raise InventoryError(f"{label} CSV has no data rows")
    missing = [name for name in required if name not in rows[0]]
    if missing:
        raise InventoryError(f"{label} CSV is missing columns: {missing}")


def _parse_bool(value: str, *, field: str) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise InventoryError(f"invalid boolean for {field}: {value!r}")


def _parse_int(value: str, *, field: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise InventoryError(f"invalid integer for {field}: {value!r}") from exc


def _parse_dt(value: str, *, field: str, allow_empty: bool = False) -> datetime | None:
    text = str(value).strip()
    if not text and allow_empty:
        return None
    try:
        return datetime.strptime(text, DATE_FMT)
    except ValueError as exc:
        raise InventoryError(f"invalid datetime for {field}: {value!r}") from exc


def _resolve_inputs(config: AuditConfig) -> InputFiles:
    prefix = config.prefix
    return InputFiles(
        symbols=config.input_dir / f"{prefix}_symbols.csv",
        coverage=config.input_dir / f"{prefix}_timeframe_coverage.csv",
        sessions=config.input_dir / f"{prefix}_sessions.csv",
        run_metadata=config.input_dir / f"{prefix}_run_metadata.csv",
    )


def _unique_values(rows: Sequence[Mapping[str, str]], key: str) -> set[str]:
    return {str(row.get(key, "")).strip() for row in rows}


def _validate_common_identity(
    symbols: Sequence[Mapping[str, str]],
    coverage: Sequence[Mapping[str, str]],
    sessions: Sequence[Mapping[str, str]],
    run: Mapping[str, str],
    config: AuditConfig,
) -> tuple[str, str, str, list[str]]:
    issues: list[str] = []
    server = str(run["account_server"]).strip()
    company = str(run["broker_company"]).strip()
    baseline = str(run["baseline_symbol"]).strip()

    if not server:
        issues.append("run metadata account_server is empty")
    if not company:
        issues.append("run metadata broker_company is empty")
    if not baseline:
        issues.append("run metadata baseline_symbol is empty")

    for label, rows in (("symbols", symbols), ("coverage", coverage), ("sessions", sessions)):
        servers = _unique_values(rows, "account_server")
        companies = _unique_values(rows, "broker_company")
        if servers != {server}:
            issues.append(f"{label} account_server mismatch: {sorted(servers)!r} vs {server!r}")
        if companies != {company}:
            issues.append(f"{label} broker_company mismatch: {sorted(companies)!r} vs {company!r}")

    if config.expected_server is not None and server != config.expected_server:
        issues.append(
            f"expected exact account_server {config.expected_server!r}, observed {server!r}"
        )
    if config.expected_company is not None and company != config.expected_company:
        issues.append(
            f"expected exact broker_company {config.expected_company!r}, observed {company!r}"
        )
    if config.expected_baseline_symbol is not None and baseline != config.expected_baseline_symbol:
        issues.append(
            f"expected exact baseline symbol {config.expected_baseline_symbol!r}, observed {baseline!r}"
        )

    return server, company, baseline, issues


def _validate_safety(run: Mapping[str, str], coverage: Sequence[Mapping[str, str]]) -> list[str]:
    issues: list[str] = []
    expected_run_flags = {
        "closed_only": True,
        "gap_fill_applied": False,
        "nearest_future_applied": False,
        "fallback_source_applied": False,
        "performance_grid_run": False,
        "candidate_created": False,
        "router_changed": False,
        "live_ready": False,
        "final_signal": False,
        "mt5_order": False,
        "discord_notify": False,
        "partial_close": False,
        "audit_only": True,
    }
    for field, expected in expected_run_flags.items():
        try:
            observed = _parse_bool(run[field], field=field)
        except (KeyError, InventoryError) as exc:
            issues.append(str(exc))
            continue
        if observed is not expected:
            issues.append(f"run flag {field}={observed!r}, expected {expected!r}")

    for index, row in enumerate(coverage, start=2):
        if str(row.get("csv_time_semantics", "")) != "broker_server_bar_open_time":
            issues.append(f"coverage row {index}: invalid csv_time_semantics")
        for field, expected in (
            ("gap_fill_applied", False),
            ("nearest_future_applied", False),
            ("fallback_source_applied", False),
            ("audit_only", True),
        ):
            try:
                observed = _parse_bool(row[field], field=f"coverage[{index}].{field}")
            except (KeyError, InventoryError) as exc:
                issues.append(str(exc))
                continue
            if observed is not expected:
                issues.append(
                    f"coverage row {index}: {field}={observed!r}, expected {expected!r}"
                )
    return issues


def _coverage_index(
    coverage: Sequence[Mapping[str, str]],
) -> tuple[dict[tuple[str, str], dict[str, str]], list[str]]:
    indexed: dict[tuple[str, str], dict[str, str]] = {}
    issues: list[str] = []
    for row in coverage:
        symbol = str(row["symbol"]).strip()
        timeframe = str(row["timeframe"]).strip().upper()
        key = (symbol, timeframe)
        if timeframe not in TIMEFRAMES:
            issues.append(f"unexpected timeframe {timeframe!r} for symbol {symbol!r}")
            continue
        if key in indexed:
            issues.append(f"duplicate coverage row for {symbol} {timeframe}")
            continue
        expected_seconds = TIMEFRAME_SECONDS[timeframe]
        observed_seconds = _parse_int(row["timeframe_seconds"], field="timeframe_seconds")
        if observed_seconds != expected_seconds:
            issues.append(
                f"{symbol} {timeframe}: timeframe_seconds={observed_seconds}, expected {expected_seconds}"
            )
        rows_total = _parse_int(row["rows_total"], field="rows_total")
        first_bar = _parse_dt(row["first_bar_open_time"], field="first_bar_open_time", allow_empty=True)
        last_bar = _parse_dt(row["last_bar_open_time"], field="last_bar_open_time", allow_empty=True)
        captured = _parse_dt(row["captured_at_server"], field="captured_at_server")
        if rows_total > 0:
            if first_bar is None or last_bar is None:
                issues.append(f"{symbol} {timeframe}: nonzero rows with empty first/last time")
            else:
                if first_bar > last_bar:
                    issues.append(f"{symbol} {timeframe}: first bar is after last bar")
                if last_bar + timedelta(seconds=expected_seconds) > captured:
                    issues.append(
                        f"{symbol} {timeframe}: last bar was not closed at captured_at_server"
                    )
        indexed[key] = dict(row)
    return indexed, issues


def _symbol_rows_by_group(
    symbols: Sequence[Mapping[str, str]],
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in symbols:
        grouped[str(row["source_group_candidate"]).strip()].append(dict(row))
    return grouped


def _status_has_rows(row: Mapping[str, str] | None) -> bool:
    return row is not None and _parse_int(row["rows_total"], field="rows_total") > 0


def _status_is_clean_available(row: Mapping[str, str] | None) -> bool:
    if row is None:
        return False
    return (
        str(row["status"]).strip() == "AVAILABLE"
        and _parse_int(row["rows_total"], field="rows_total") > 0
        and _parse_int(row["copy_errors"], field="copy_errors") == 0
        and _parse_int(row["duplicate_count"], field="duplicate_count") == 0
        and _parse_int(row["non_monotonic_count"], field="non_monotonic_count") == 0
    )


def _group_observation_status(
    group: str,
    candidates: Sequence[Mapping[str, str]],
    coverage_index: Mapping[tuple[str, str], Mapping[str, str]],
) -> str:
    if group == "ECONOMIC_CALENDAR":
        return "BLOCKED_SEPARATE_NON_SYMBOL_SOURCE_NOT_AUDITED"
    if not candidates:
        return "NO_BROKER_SYMBOL_OBSERVED"

    available_rows = 0
    clean_rows = 0
    expected_rows = len(candidates) * len(TIMEFRAMES)
    for candidate in candidates:
        symbol = str(candidate["symbol"]).strip()
        for timeframe in TIMEFRAMES:
            row = coverage_index.get((symbol, timeframe))
            if _status_has_rows(row):
                available_rows += 1
            if _status_is_clean_available(row):
                clean_rows += 1

    if clean_rows == expected_rows and expected_rows > 0:
        return "OBSERVED_ALL_TIMEFRAMES_AVAILABLE"
    if available_rows > 0:
        return "OBSERVED_PARTIAL_TIMEFRAME_AVAILABILITY"
    return "BROKER_SYMBOL_OBSERVED_NO_RATES_RETURNED"


def _build_source_inventory(
    grouped_symbols: Mapping[str, Sequence[Mapping[str, str]]],
    coverage_index: Mapping[tuple[str, str], Mapping[str, str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in EXPECTED_SOURCE_GROUPS:
        candidates = list(grouped_symbols.get(group, []))
        status = _group_observation_status(group, candidates, coverage_index)
        if not candidates:
            rows.append(
                {
                    "source_group": group,
                    "exact_symbol": "",
                    "match_basis": "",
                    "symbol_observed": False,
                    "selection_status": "UNRESOLVED_NO_EXACT_SYMBOL_SELECTED",
                    "availability_status": status,
                    "available_timeframes": "",
                    "unavailable_timeframes": ";".join(TIMEFRAMES),
                    "server_source_only": True,
                    "fallback_used": False,
                    "notes": (
                        "Economic calendar requires a separate explicit source audit."
                        if group == "ECONOMIC_CALENDAR"
                        else "No exact broker symbol candidate was observed; no substitute was guessed."
                    ),
                }
            )
            continue

        for candidate in sorted(candidates, key=lambda item: str(item["symbol"])):
            symbol = str(candidate["symbol"]).strip()
            available = [
                tf for tf in TIMEFRAMES if _status_has_rows(coverage_index.get((symbol, tf)))
            ]
            unavailable = [tf for tf in TIMEFRAMES if tf not in available]
            rows.append(
                {
                    "source_group": group,
                    "exact_symbol": symbol,
                    "match_basis": candidate.get("match_basis", ""),
                    "symbol_observed": True,
                    "selection_status": "INVENTORY_CANDIDATE_ONLY_NOT_AUTO_SELECTED",
                    "availability_status": status,
                    "available_timeframes": ";".join(available),
                    "unavailable_timeframes": ";".join(unavailable),
                    "server_source_only": True,
                    "fallback_used": False,
                    "notes": "Exact broker symbol retained. Similar symbols are not silently substituted.",
                }
            )
    return rows


def _build_availability_matrix(
    symbols: Sequence[Mapping[str, str]],
    coverage_index: Mapping[tuple[str, str], Mapping[str, str]],
    baseline_symbol: str,
) -> list[dict[str, Any]]:
    candidate_symbols = [
        row
        for row in symbols
        if str(row["source_group_candidate"]).strip() != "UNCLASSIFIED"
    ]
    result: list[dict[str, Any]] = []
    baseline_m15 = coverage_index.get((baseline_symbol, "M15"))
    baseline_start = (
        _parse_dt(baseline_m15["first_bar_open_time"], field="baseline.first", allow_empty=True)
        if baseline_m15
        else None
    )
    baseline_last = (
        _parse_dt(baseline_m15["last_bar_open_time"], field="baseline.last", allow_empty=True)
        if baseline_m15
        else None
    )
    baseline_end = (
        baseline_last + timedelta(seconds=TIMEFRAME_SECONDS["M15"])
        if baseline_last is not None
        else None
    )

    for symbol_row in sorted(candidate_symbols, key=lambda row: str(row["symbol"])):
        symbol = str(symbol_row["symbol"]).strip()
        out: dict[str, Any] = {
            "source_group": str(symbol_row["source_group_candidate"]).strip(),
            "exact_symbol": symbol,
            "match_basis": symbol_row.get("match_basis", ""),
            "baseline_symbol": baseline_symbol,
        }
        overlap_any = False
        for tf in TIMEFRAMES:
            row = coverage_index.get((symbol, tf))
            prefix = tf.lower()
            if row is None:
                out[f"{prefix}_status"] = "NOT_PROBED"
                out[f"{prefix}_rows"] = 0
                out[f"{prefix}_first_open"] = ""
                out[f"{prefix}_last_open"] = ""
                out[f"{prefix}_last_close_available"] = ""
                continue
            out[f"{prefix}_status"] = row["status"]
            out[f"{prefix}_rows"] = _parse_int(row["rows_total"], field="rows_total")
            out[f"{prefix}_first_open"] = row["first_bar_open_time"]
            out[f"{prefix}_last_open"] = row["last_bar_open_time"]
            last_open = _parse_dt(
                row["last_bar_open_time"], field="last_bar_open_time", allow_empty=True
            )
            last_close = (
                last_open + timedelta(seconds=TIMEFRAME_SECONDS[tf])
                if last_open is not None
                else None
            )
            out[f"{prefix}_last_close_available"] = (
                last_close.strftime(DATE_FMT) if last_close is not None else ""
            )

            first_open = _parse_dt(
                row["first_bar_open_time"], field="first_bar_open_time", allow_empty=True
            )
            if (
                first_open is not None
                and last_close is not None
                and baseline_start is not None
                and baseline_end is not None
                and max(first_open, baseline_start) < min(last_close, baseline_end)
            ):
                overlap_any = True

        out["coverage_overlap_with_gold_m15"] = overlap_any
        out["asof_join_rule"] = "source_close_time<=decision_time"
        out["forming_bar_allowed"] = False
        out["nearest_future_allowed"] = False
        out["fallback_allowed"] = False
        result.append(out)
    return result


def _build_history_coverage(
    coverage: Sequence[Mapping[str, str]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in sorted(coverage, key=lambda item: (item["source_group"], item["symbol"], item["timeframe"])):
        for year in (2023, 2024, 2025, 2026):
            result.append(
                {
                    "source_group": row["source_group"],
                    "exact_symbol": row["symbol"],
                    "timeframe": row["timeframe"],
                    "year": year,
                    "rows": _parse_int(row[f"rows_{year}"], field=f"rows_{year}"),
                    "first_bar_open_time": row[f"first_{year}"],
                    "last_bar_open_time": row[f"last_{year}"],
                    "status": row["status"],
                    "copy_errors": _parse_int(row["copy_errors"], field="copy_errors"),
                    "duplicate_count": _parse_int(
                        row["duplicate_count"], field="duplicate_count"
                    ),
                    "non_monotonic_count": _parse_int(
                        row["non_monotonic_count"], field="non_monotonic_count"
                    ),
                    "raw_gap_intervals_gt_one_period": _parse_int(
                        row["raw_gap_intervals_gt_one_period"],
                        field="raw_gap_intervals_gt_one_period",
                    ),
                    "raw_gap_interpretation": (
                        "Raw interval only; weekends/sessions are not automatically labeled missing."
                    ),
                }
            )
    return result


def _build_causal_contract() -> list[dict[str, Any]]:
    return [
        {
            "timeframe": tf,
            "bar_time_semantics": "broker_server_bar_open_time",
            "close_availability_seconds": TIMEFRAME_SECONDS[tf],
            "source_close_time_formula": f"bar_open_time+{TIMEFRAME_SECONDS[tf]}s",
            "decision_join_rule": "source_close_time<=decision_time",
            "forming_bar_allowed": False,
            "nearest_future_allowed": False,
            "gap_fill_allowed": False,
            "fallback_source_allowed": False,
            "entry_outcome_allowed_in_features": False,
            "audit_only": True,
        }
        for tf in TIMEFRAMES
    ]


def _build_unavailable_ledger(
    source_inventory: Sequence[Mapping[str, Any]],
    coverage: Sequence[Mapping[str, str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in source_inventory:
        status = str(item["availability_status"])
        if status in {
            "NO_BROKER_SYMBOL_OBSERVED",
            "BROKER_SYMBOL_OBSERVED_NO_RATES_RETURNED",
            "BLOCKED_SEPARATE_NON_SYMBOL_SOURCE_NOT_AUDITED",
        }:
            rows.append(
                {
                    "source_group": item["source_group"],
                    "exact_symbol": item["exact_symbol"],
                    "timeframe": "",
                    "classification": (
                        "BLOCKED"
                        if status == "BLOCKED_SEPARATE_NON_SYMBOL_SOURCE_NOT_AUDITED"
                        else "UNAVAILABLE"
                    ),
                    "reason": status,
                    "fallback_attempted": False,
                    "replacement_symbol_used": False,
                    "next_allowed_action": (
                        "Run a separate explicit MT5 economic-calendar availability audit."
                        if item["source_group"] == "ECONOMIC_CALENDAR"
                        else "Review exact broker inventory or provide an explicit exact symbol; do not guess."
                    ),
                }
            )

    for row in coverage:
        if str(row["status"]) in {"PARTIAL_COPY_ERRORS", "COPY_FAILED", "NO_RATES_RETURNED"}:
            rows.append(
                {
                    "source_group": row["source_group"],
                    "exact_symbol": row["symbol"],
                    "timeframe": row["timeframe"],
                    "classification": (
                        "PARTIAL" if str(row["status"]) == "PARTIAL_COPY_ERRORS" else "UNAVAILABLE"
                    ),
                    "reason": row["status"],
                    "fallback_attempted": False,
                    "replacement_symbol_used": False,
                    "next_allowed_action": "Record the observed status; rerun only after an explicit data-access fix.",
                }
            )
    return rows


def _determine_status(
    validation_issues: Sequence[str],
    source_inventory: Sequence[Mapping[str, Any]],
) -> tuple[str, str]:
    if validation_issues:
        return STATUS_BLOCKED, "BLOCKED"
    statuses = {str(row["availability_status"]) for row in source_inventory}
    incomplete = {
        "NO_BROKER_SYMBOL_OBSERVED",
        "BROKER_SYMBOL_OBSERVED_NO_RATES_RETURNED",
        "OBSERVED_PARTIAL_TIMEFRAME_AVAILABILITY",
        "BLOCKED_SEPARATE_NON_SYMBOL_SOURCE_NOT_AUDITED",
    }
    if statuses & incomplete:
        return STATUS_PARTIAL, "PARTIAL"
    return STATUS_INVENTORIED, "INVENTORIED"


def _render_report(
    *,
    status: str,
    classification: str,
    server: str,
    company: str,
    baseline: str,
    source_inventory: Sequence[Mapping[str, Any]],
    validation_issues: Sequence[str],
    output_files: Sequence[str],
) -> str:
    lines = [
        "# GOLD V3 Stage277 External Causal Context Data Availability Audit",
        "",
        f"正式状態: `{status}`",
        "",
        "## 実測identity",
        "",
        f"- broker company: `{company}`",
        f"- account server: `{server}`",
        f"- GOLD baseline exact symbol: `{baseline}`",
        f"- classification: `{classification}`",
        "",
        "## Source inventory",
        "",
        "| source group | exact symbol | availability | selection |",
        "|---|---|---|---|",
    ]
    for row in source_inventory:
        lines.append(
            "| {source_group} | {exact_symbol} | {availability_status} | {selection_status} |".format(
                source_group=row["source_group"],
                exact_symbol=row["exact_symbol"] or "—",
                availability_status=row["availability_status"],
                selection_status=row["selection_status"],
            )
        )

    lines.extend(
        [
            "",
            "## Causal contract",
            "",
            "- CSV time is broker/server bar OPEN time.",
            "- Only closed bars are inventoried.",
            "- Join rule is `source_close_time <= decision_time`.",
            "- Forming bars, nearest-future rows, interpolation, gap fill, and silent source fallback are prohibited.",
            "- This stage does not create features, candidates, thresholds, performance grids, or live signals.",
            "",
            "## Validation",
            "",
        ]
    )
    if validation_issues:
        lines.extend(f"- BLOCKED: {issue}" for issue in validation_issues)
    else:
        lines.append("- PASS: identity and safety flags are internally consistent.")

    lines.extend(["", "## Outputs", ""])
    lines.extend(f"- `{name}`" for name in output_files)
    lines.extend(
        [
            "",
            "## Safety state",
            "",
            "`audit_only=ON / live_ready=OFF / final_signal=OFF / MT5_order=OFF / Discord_notify=OFF / partial_close=OFF`",
            "",
        ]
    )
    return "\n".join(lines)


def run_audit(config: AuditConfig) -> dict[str, Any]:
    files = _resolve_inputs(config)
    symbols = _read_csv(files.symbols)
    coverage = _read_csv(files.coverage)
    sessions = _read_csv(files.sessions)
    run_rows = _read_csv(files.run_metadata)

    _require_columns(
        symbols,
        (
            "account_server",
            "broker_company",
            "symbol",
            "source_group_candidate",
            "match_basis",
            "audit_only",
        ),
        "symbols",
    )
    _require_columns(
        coverage,
        (
            "captured_at_server",
            "account_server",
            "broker_company",
            "symbol",
            "source_group",
            "timeframe",
            "timeframe_seconds",
            "rows_total",
            "first_bar_open_time",
            "last_bar_open_time",
            "rows_2023",
            "first_2023",
            "last_2023",
            "rows_2024",
            "first_2024",
            "last_2024",
            "rows_2025",
            "first_2025",
            "last_2025",
            "rows_2026",
            "first_2026",
            "last_2026",
            "duplicate_count",
            "non_monotonic_count",
            "raw_gap_intervals_gt_one_period",
            "copy_errors",
            "status",
            "csv_time_semantics",
            "gap_fill_applied",
            "nearest_future_applied",
            "fallback_source_applied",
            "audit_only",
        ),
        "coverage",
    )
    _require_columns(
        sessions,
        ("account_server", "broker_company", "symbol", "source_group_candidate", "audit_only"),
        "sessions",
    )
    _require_columns(
        run_rows,
        (
            "account_server",
            "broker_company",
            "baseline_symbol",
            "closed_only",
            "gap_fill_applied",
            "nearest_future_applied",
            "fallback_source_applied",
            "performance_grid_run",
            "candidate_created",
            "router_changed",
            "live_ready",
            "final_signal",
            "mt5_order",
            "discord_notify",
            "partial_close",
            "audit_only",
        ),
        "run metadata",
    )
    if len(run_rows) != 1:
        raise InventoryError(f"run metadata must contain exactly one row, observed {len(run_rows)}")
    run = run_rows[0]

    server, company, baseline, identity_issues = _validate_common_identity(
        symbols, coverage, sessions, run, config
    )
    safety_issues = _validate_safety(run, coverage)
    coverage_index, coverage_issues = _coverage_index(coverage)

    symbol_names = {str(row["symbol"]).strip() for row in symbols}
    baseline_rows = [
        row
        for row in symbols
        if str(row["symbol"]).strip() == baseline
        and str(row["source_group_candidate"]).strip() == "GOLD_BASELINE"
    ]
    baseline_issues: list[str] = []
    if baseline not in symbol_names:
        baseline_issues.append(f"baseline symbol {baseline!r} is absent from broker symbol inventory")
    if len(baseline_rows) != 1:
        baseline_issues.append(
            f"baseline symbol must have exactly one GOLD_BASELINE inventory row, observed {len(baseline_rows)}"
        )
    if (baseline, "M15") not in coverage_index:
        baseline_issues.append("baseline M15 coverage row is missing")

    validation_issues = identity_issues + safety_issues + coverage_issues + baseline_issues
    grouped_symbols = _symbol_rows_by_group(symbols)
    source_inventory = _build_source_inventory(grouped_symbols, coverage_index)
    availability_matrix = _build_availability_matrix(symbols, coverage_index, baseline)
    history_coverage = _build_history_coverage(coverage)
    causal_contract = _build_causal_contract()
    unavailable_ledger = _build_unavailable_ledger(source_inventory, coverage)
    status, classification = _determine_status(validation_issues, source_inventory)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    source_inventory_name = "stage277_source_inventory.csv"
    availability_name = "stage277_source_availability_matrix.csv"
    history_name = "stage277_history_coverage_matrix.csv"
    causal_name = "stage277_causal_availability_contract.csv"
    unavailable_name = "stage277_rejected_unavailable_source_ledger.csv"
    summary_name = "stage277_summary.json"
    report_name = "GOLD_V3_STAGE277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_AUDIT_ONLY.md"

    _write_csv(
        config.output_dir / source_inventory_name,
        (
            "source_group",
            "exact_symbol",
            "match_basis",
            "symbol_observed",
            "selection_status",
            "availability_status",
            "available_timeframes",
            "unavailable_timeframes",
            "server_source_only",
            "fallback_used",
            "notes",
        ),
        source_inventory,
    )

    availability_fields = [
        "source_group",
        "exact_symbol",
        "match_basis",
        "baseline_symbol",
    ]
    for tf in TIMEFRAMES:
        prefix = tf.lower()
        availability_fields.extend(
            [
                f"{prefix}_status",
                f"{prefix}_rows",
                f"{prefix}_first_open",
                f"{prefix}_last_open",
                f"{prefix}_last_close_available",
            ]
        )
    availability_fields.extend(
        [
            "coverage_overlap_with_gold_m15",
            "asof_join_rule",
            "forming_bar_allowed",
            "nearest_future_allowed",
            "fallback_allowed",
        ]
    )
    _write_csv(config.output_dir / availability_name, availability_fields, availability_matrix)
    _write_csv(
        config.output_dir / history_name,
        (
            "source_group",
            "exact_symbol",
            "timeframe",
            "year",
            "rows",
            "first_bar_open_time",
            "last_bar_open_time",
            "status",
            "copy_errors",
            "duplicate_count",
            "non_monotonic_count",
            "raw_gap_intervals_gt_one_period",
            "raw_gap_interpretation",
        ),
        history_coverage,
    )
    _write_csv(
        config.output_dir / causal_name,
        (
            "timeframe",
            "bar_time_semantics",
            "close_availability_seconds",
            "source_close_time_formula",
            "decision_join_rule",
            "forming_bar_allowed",
            "nearest_future_allowed",
            "gap_fill_allowed",
            "fallback_source_allowed",
            "entry_outcome_allowed_in_features",
            "audit_only",
        ),
        causal_contract,
    )
    _write_csv(
        config.output_dir / unavailable_name,
        (
            "source_group",
            "exact_symbol",
            "timeframe",
            "classification",
            "reason",
            "fallback_attempted",
            "replacement_symbol_used",
            "next_allowed_action",
        ),
        unavailable_ledger,
    )

    group_status = {
        group: sorted(
            {
                str(row["availability_status"])
                for row in source_inventory
                if row["source_group"] == group
            }
        )
        for group in EXPECTED_SOURCE_GROUPS
    }
    summary: dict[str, Any] = {
        "status": status,
        "classification": classification,
        "audit_only": True,
        "broker_company": company,
        "account_server": server,
        "gold_baseline_symbol": baseline,
        "csv_time_semantics": "broker_server_bar_open_time",
        "closed_only": True,
        "causal_join_rule": "source_close_time<=decision_time",
        "source_group_status": group_status,
        "validation_issue_count": len(validation_issues),
        "validation_issues": list(validation_issues),
        "source_inventory_rows": len(source_inventory),
        "availability_matrix_rows": len(availability_matrix),
        "history_coverage_rows": len(history_coverage),
        "unavailable_ledger_rows": len(unavailable_ledger),
        "performance_grid_run": False,
        "candidate_created": False,
        "specialist_health_router_v3_changed": False,
        "phase2_hv_retest_state": "SHADOW_ONLY_UNCHANGED",
        "continuous_tick_collection_required": False,
        "candidate_tick_collection_required": False,
        "live_ready": False,
        "final_signal": False,
        "mt5_order": False,
        "discord_notify": False,
        "partial_close": False,
        "operating_state": "NO_LIVE_PROMOTION_AUDIT_ONLY",
        "outputs": [
            source_inventory_name,
            availability_name,
            history_name,
            causal_name,
            unavailable_name,
            summary_name,
            report_name,
        ],
    }
    _write_json(config.output_dir / summary_name, summary)

    report = _render_report(
        status=status,
        classification=classification,
        server=server,
        company=company,
        baseline=baseline,
        source_inventory=source_inventory,
        validation_issues=validation_issues,
        output_files=summary["outputs"],
    )
    (config.output_dir / report_name).write_text(report, encoding="utf-8")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = AuditConfig(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        prefix=args.prefix,
        expected_server=args.expected_server,
        expected_company=args.expected_company,
        expected_baseline_symbol=args.expected_baseline_symbol,
    )
    try:
        summary = run_audit(config)
    except InventoryError as exc:
        print(f"Stage277 audit BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["classification"] != "BLOCKED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
