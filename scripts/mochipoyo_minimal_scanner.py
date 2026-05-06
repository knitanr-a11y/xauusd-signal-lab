#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Initial Mochipoyo minimal scanner skeleton.

This first version intentionally does not reimplement Mochipoyo signal logic yet.
Its purpose is to establish the safe live-scanner data path:

- allowed_slices -> required pairs only
- read only the required pair CSVs through the safe reader
- build confirmed-time base/context joined frames
- return structured scan results with empty candidate DataFrames

Later commits will add pair-specific raw candidate generation on top of this
foundation, then risk/spread enrichment, then comparison against full strict
scan outputs.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

try:  # Package import from repository root.
    from scripts.mochipoyo_candidate_normalizer import ensure_normalized_columns
    from scripts.mochipoyo_minimal_config import (
        DEFAULT_ALLOWED_SLICES,
        build_csv_overrides_from_args,
        filter_allowed_slices_for_pair,
        get_pair_config,
        get_required_pair_names,
        normalize_allowed_slices,
        resolve_csv_path,
        validate_allowed_slices_against_pair_configs,
    )
    from scripts.mochipoyo_safe_csv_reader import CsvReadResult, read_ohlc_csv_safe
except ModuleNotFoundError:  # Direct execution from scripts/.
    from mochipoyo_candidate_normalizer import ensure_normalized_columns  # type: ignore
    from mochipoyo_minimal_config import (  # type: ignore
        DEFAULT_ALLOWED_SLICES,
        build_csv_overrides_from_args,
        filter_allowed_slices_for_pair,
        get_pair_config,
        get_required_pair_names,
        normalize_allowed_slices,
        resolve_csv_path,
        validate_allowed_slices_against_pair_configs,
    )
    from mochipoyo_safe_csv_reader import CsvReadResult, read_ohlc_csv_safe  # type: ignore

SCAN_STATUS_OK = "OK"
SCAN_STATUS_ERROR = "ERROR"
SCAN_STATUS_SKIPPED = "SKIPPED"

ERR_PAIR_CONFIG_MISSING = "PAIR_CONFIG_MISSING"
ERR_BASE_CSV_READ_FAILED = "BASE_CSV_READ_FAILED"
ERR_CONTEXT_CSV_READ_FAILED = "CONTEXT_CSV_READ_FAILED"
ERR_CONFIRMED_TIME_JOIN_FAILED = "CONFIRMED_TIME_JOIN_FAILED"
ERR_NO_BASE_ROWS = "NO_BASE_ROWS"
ERR_NO_CONTEXT_ROWS = "NO_CONTEXT_ROWS"


@dataclass
class MinimalScanError:
    pair_name: str
    error_reason: str
    detail: str | None = None
    csv_key: str | None = None
    path: str | None = None


@dataclass
class MinimalPairScanResult:
    scan_status: str
    pair_name: str
    symbol: str | None
    base_timeframe: str | None
    latest_base_close_time: pd.Timestamp | None
    raw_candidates_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    normalized_candidates_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    risk_ok_candidates_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    risk_ng_candidates_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    base_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    context_frames: dict[str, pd.DataFrame] = field(default_factory=dict)
    joined_frames: dict[str, pd.DataFrame] = field(default_factory=dict)
    errors: list[MinimalScanError] = field(default_factory=list)
    reader_metadata: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class MinimalScanBatchResult:
    results: list[MinimalPairScanResult]
    allowed_slices: list[dict[str, str]]

    @property
    def ok(self) -> bool:
        return all(r.scan_status == SCAN_STATUS_OK for r in self.results)

    def summary_frame(self) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for r in self.results:
            rows.append(
                {
                    "pair_name": r.pair_name,
                    "symbol": r.symbol,
                    "base_timeframe": r.base_timeframe,
                    "scan_status": r.scan_status,
                    "latest_base_close_time": r.latest_base_close_time,
                    "base_rows": int(len(r.base_df)),
                    "context_frames": ",".join(sorted(r.context_frames.keys())),
                    "raw_candidates": int(len(r.raw_candidates_df)),
                    "normalized_candidates": int(len(r.normalized_candidates_df)),
                    "risk_ok_candidates": int(len(r.risk_ok_candidates_df)),
                    "risk_ng_candidates": int(len(r.risk_ng_candidates_df)),
                    "error_count": int(len(r.errors)),
                    "errors": ";".join(e.error_reason for e in r.errors),
                }
            )
        return pd.DataFrame(rows)


def _reader_metadata(csv_key: str, result: CsvReadResult) -> dict[str, Any]:
    return {
        "csv_key": csv_key,
        "path": result.path,
        "timeframe": result.timeframe,
        "read_status": result.read_status,
        "error_reason": result.error_reason,
        "rows_raw": result.rows_raw,
        "rows_valid": result.rows_valid,
        "rows_dropped_parse": result.rows_dropped_parse,
        "rows_dropped_incomplete": result.rows_dropped_incomplete,
        "duplicate_time_count": result.duplicate_time_count,
        "duplicate_time_ohlc_conflict_count": result.duplicate_time_ohlc_conflict_count,
        "latest_time": result.latest_time,
        "latest_close_time": result.latest_close_time,
        "separator": result.separator,
    }


def _empty_pair_result(pair_name: str, cfg: Mapping[str, Any] | None, status: str, errors: list[MinimalScanError]) -> MinimalPairScanResult:
    return MinimalPairScanResult(
        scan_status=status,
        pair_name=pair_name,
        symbol=str(cfg.get("symbol")) if cfg else None,
        base_timeframe=str(cfg.get("base_timeframe")) if cfg else None,
        latest_base_close_time=None,
        raw_candidates_df=pd.DataFrame(),
        normalized_candidates_df=ensure_normalized_columns(pd.DataFrame()),
        risk_ok_candidates_df=ensure_normalized_columns(pd.DataFrame()),
        risk_ng_candidates_df=ensure_normalized_columns(pd.DataFrame()),
        errors=errors,
    )


def confirmed_time_join_base_context(
    base_df: pd.DataFrame,
    context_df: pd.DataFrame,
    *,
    context_label: str,
) -> pd.DataFrame:
    """Join context rows to base rows using context_close_time <= base_close_time.

    Input frames must already contain `time` and `close_time`.
    The returned frame contains base_* columns and context_* columns.
    """
    if base_df.empty:
        return pd.DataFrame()
    if context_df.empty:
        out = pd.DataFrame(
            {
                "base_time": base_df["time"],
                "base_close_time": base_df["close_time"],
            }
        )
        return out

    base = base_df.copy().sort_values("close_time").reset_index(drop=True)
    context = context_df.copy().sort_values("close_time").reset_index(drop=True)

    base = base.rename(columns={"time": "base_time", "close_time": "base_close_time"})
    context = context.rename(columns={"time": "context_time", "close_time": "context_close_time"})

    joined = pd.merge_asof(
        base,
        context,
        left_on="base_close_time",
        right_on="context_close_time",
        direction="backward",
        suffixes=("", f"_{context_label.lower()}"),
    )
    joined["context_label"] = context_label
    return joined


def read_pair_frames(
    pair_name: str,
    cfg: Mapping[str, Any],
    *,
    csv_dir: str | Path,
    csv_overrides: Mapping[str, str | Path | None] | None,
    as_of_time: object | None,
    tail_bars_override: Mapping[str, int] | None = None,
    csv_sep: str = "auto",
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], list[dict[str, Any]], list[MinimalScanError]]:
    """Read base/context frames required by one pair."""
    reader_meta: list[dict[str, Any]] = []
    errors: list[MinimalScanError] = []

    base_tf = str(cfg["base_timeframe"]).upper()
    base_csv_key = str(cfg["base_csv_key"])
    base_tail = int((tail_bars_override or {}).get(base_tf, cfg.get("tail_bars", {}).get(base_tf, 0)))
    base_path = resolve_csv_path(csv_dir, base_csv_key, csv_overrides)
    base_result = read_ohlc_csv_safe(
        base_path,
        base_tf,
        tail_bars=base_tail,
        requires_spread=bool(cfg.get("requires_spread", False) and cfg.get("spread_source_csv_key") == base_csv_key),
        as_of_time=as_of_time,
        csv_sep=csv_sep,
    )
    reader_meta.append(_reader_metadata(base_csv_key, base_result))
    if not base_result.ok:
        errors.append(
            MinimalScanError(
                pair_name=pair_name,
                error_reason=ERR_BASE_CSV_READ_FAILED,
                detail=base_result.error_reason,
                csv_key=base_csv_key,
                path=str(base_path),
            )
        )
        return pd.DataFrame(), {}, reader_meta, errors
    base_df = base_result.df
    if base_df.empty:
        errors.append(MinimalScanError(pair_name=pair_name, error_reason=ERR_NO_BASE_ROWS, csv_key=base_csv_key, path=str(base_path)))
        return pd.DataFrame(), {}, reader_meta, errors

    context_frames: dict[str, pd.DataFrame] = {}
    for context_tf, context_csv_key in dict(cfg.get("context", {})).items():
        tf = str(context_tf).upper()
        csv_key = str(context_csv_key)
        tail = int((tail_bars_override or {}).get(tf, cfg.get("tail_bars", {}).get(tf, 0)))
        path = resolve_csv_path(csv_dir, csv_key, csv_overrides)
        result = read_ohlc_csv_safe(
            path,
            tf,
            tail_bars=tail,
            requires_spread=bool(cfg.get("requires_spread", False) and cfg.get("spread_source_csv_key") == csv_key),
            as_of_time=as_of_time,
            csv_sep=csv_sep,
        )
        reader_meta.append(_reader_metadata(csv_key, result))
        if not result.ok:
            errors.append(
                MinimalScanError(
                    pair_name=pair_name,
                    error_reason=ERR_CONTEXT_CSV_READ_FAILED,
                    detail=result.error_reason,
                    csv_key=csv_key,
                    path=str(path),
                )
            )
            continue
        if result.df.empty:
            errors.append(MinimalScanError(pair_name=pair_name, error_reason=ERR_NO_CONTEXT_ROWS, csv_key=csv_key, path=str(path)))
            continue
        context_frames[tf] = result.df

    return base_df, context_frames, reader_meta, errors


def scan_pair_minimal_skeleton(
    pair_name: str,
    *,
    csv_dir: str | Path,
    csv_overrides: Mapping[str, str | Path | None] | None = None,
    allowed_slices: Iterable[Mapping[str, Any] | str] | None = None,
    as_of_time: object | None = None,
    tail_bars_override: Mapping[str, int] | None = None,
    csv_sep: str = "auto",
) -> MinimalPairScanResult:
    """Scan one pair through the current skeleton data path.

    Candidate generation is intentionally not implemented yet, so candidate
    frames are empty but normalized.
    """
    try:
        cfg = get_pair_config(pair_name)
    except Exception as exc:
        return _empty_pair_result(
            pair_name,
            None,
            SCAN_STATUS_ERROR,
            [MinimalScanError(pair_name=pair_name, error_reason=ERR_PAIR_CONFIG_MISSING, detail=str(exc))],
        )

    pair_allowed_slices = filter_allowed_slices_for_pair(allowed_slices, pair_name)
    if not pair_allowed_slices:
        return _empty_pair_result(pair_name, cfg, SCAN_STATUS_SKIPPED, [])

    base_df, context_frames, reader_meta, errors = read_pair_frames(
        pair_name,
        cfg,
        csv_dir=csv_dir,
        csv_overrides=csv_overrides,
        as_of_time=as_of_time,
        tail_bars_override=tail_bars_override,
        csv_sep=csv_sep,
    )
    if errors:
        return MinimalPairScanResult(
            scan_status=SCAN_STATUS_ERROR,
            pair_name=pair_name,
            symbol=str(cfg.get("symbol")),
            base_timeframe=str(cfg.get("base_timeframe")),
            latest_base_close_time=pd.Timestamp(base_df["close_time"].iloc[-1]) if not base_df.empty and "close_time" in base_df.columns else None,
            base_df=base_df,
            context_frames=context_frames,
            raw_candidates_df=pd.DataFrame(),
            normalized_candidates_df=ensure_normalized_columns(pd.DataFrame()),
            risk_ok_candidates_df=ensure_normalized_columns(pd.DataFrame()),
            risk_ng_candidates_df=ensure_normalized_columns(pd.DataFrame()),
            errors=errors,
            reader_metadata=reader_meta,
        )

    joined_frames: dict[str, pd.DataFrame] = {}
    join_errors: list[MinimalScanError] = []
    for context_tf, context_df in context_frames.items():
        try:
            joined_frames[context_tf] = confirmed_time_join_base_context(base_df, context_df, context_label=context_tf)
        except Exception as exc:
            join_errors.append(
                MinimalScanError(pair_name=pair_name, error_reason=ERR_CONFIRMED_TIME_JOIN_FAILED, detail=str(exc))
            )

    status = SCAN_STATUS_ERROR if join_errors else SCAN_STATUS_OK
    all_errors = errors + join_errors
    return MinimalPairScanResult(
        scan_status=status,
        pair_name=pair_name,
        symbol=str(cfg.get("symbol")),
        base_timeframe=str(cfg.get("base_timeframe")),
        latest_base_close_time=pd.Timestamp(base_df["close_time"].iloc[-1]) if not base_df.empty else None,
        base_df=base_df,
        context_frames=context_frames,
        joined_frames=joined_frames,
        raw_candidates_df=pd.DataFrame(),
        normalized_candidates_df=ensure_normalized_columns(pd.DataFrame()),
        risk_ok_candidates_df=ensure_normalized_columns(pd.DataFrame()),
        risk_ng_candidates_df=ensure_normalized_columns(pd.DataFrame()),
        errors=all_errors,
        reader_metadata=reader_meta,
    )


def scan_allowed_pairs_minimal_skeleton(
    *,
    csv_dir: str | Path,
    csv_overrides: Mapping[str, str | Path | None] | None = None,
    allowed_slices: Iterable[Mapping[str, Any] | str] | None = None,
    as_of_time: object | None = None,
    tail_bars_override: Mapping[str, int] | None = None,
    csv_sep: str = "auto",
) -> MinimalScanBatchResult:
    normalized_allowed = validate_allowed_slices_against_pair_configs(normalize_allowed_slices(allowed_slices or DEFAULT_ALLOWED_SLICES))
    pair_names = get_required_pair_names(normalized_allowed)
    results = [
        scan_pair_minimal_skeleton(
            pair_name,
            csv_dir=csv_dir,
            csv_overrides=csv_overrides,
            allowed_slices=normalized_allowed,
            as_of_time=as_of_time,
            tail_bars_override=tail_bars_override,
            csv_sep=csv_sep,
        )
        for pair_name in pair_names
    ]
    return MinimalScanBatchResult(results=results, allowed_slices=normalized_allowed)


def reader_metadata_frame(batch: MinimalScanBatchResult) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for result in batch.results:
        for meta in result.reader_metadata:
            rows.append({"pair_name": result.pair_name, **meta})
    return pd.DataFrame(rows)


def errors_frame(batch: MinimalScanBatchResult) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for result in batch.results:
        for err in result.errors:
            rows.append(
                {
                    "pair_name": err.pair_name,
                    "error_reason": err.error_reason,
                    "detail": err.detail,
                    "csv_key": err.csv_key,
                    "path": err.path,
                }
            )
    return pd.DataFrame(rows)


def parse_tail_overrides(args: argparse.Namespace) -> dict[str, int]:
    values = {
        "M5": args.tail_m5,
        "M15": args.tail_m15,
        "H1": args.tail_h1,
        "H4": args.tail_h4,
        "D1": args.tail_d1,
    }
    return {tf: int(v) for tf, v in values.items() if v is not None and int(v) > 0}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the initial Mochipoyo minimal scanner skeleton.")
    parser.add_argument("--csv-dir", required=True, help="MQL5/Files directory containing exported OHLC CSVs.")
    parser.add_argument("--out-dir", required=True, help="Output directory for skeleton scan diagnostics.")
    parser.add_argument("--as-of-time", default=None)
    parser.add_argument("--csv-sep", default="auto")
    parser.add_argument("--tail-m5", type=int, default=6000)
    parser.add_argument("--tail-m15", type=int, default=5000)
    parser.add_argument("--tail-h1", type=int, default=1500)
    parser.add_argument("--tail-h4", type=int, default=1500)
    parser.add_argument("--tail-d1", type=int, default=800)
    parser.add_argument("--gold-m5-csv")
    parser.add_argument("--gold-m15-csv")
    parser.add_argument("--gold-h1-csv")
    parser.add_argument("--gold-h4-csv")
    parser.add_argument("--gold-d1-csv")
    parser.add_argument("--btc-m5-csv")
    parser.add_argument("--btc-m15-csv")
    parser.add_argument("--btc-h1-csv")
    parser.add_argument("--btc-h4-csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    batch = scan_allowed_pairs_minimal_skeleton(
        csv_dir=args.csv_dir,
        csv_overrides=build_csv_overrides_from_args(args),
        as_of_time=args.as_of_time,
        tail_bars_override=parse_tail_overrides(args),
        csv_sep=args.csv_sep,
    )

    summary = batch.summary_frame()
    metadata = reader_metadata_frame(batch)
    errors = errors_frame(batch)

    summary.to_csv(out_dir / "minimal_skeleton_summary.csv", index=False, encoding="utf-8-sig")
    metadata.to_csv(out_dir / "minimal_skeleton_reader_metadata.csv", index=False, encoding="utf-8-sig")
    errors.to_csv(out_dir / "minimal_skeleton_errors.csv", index=False, encoding="utf-8-sig")

    # Write per-pair joined frame samples only.  These are diagnostic files, not
    # signal candidates.
    for result in batch.results:
        for context_tf, joined in result.joined_frames.items():
            sample = joined.tail(200).copy() if len(joined) > 200 else joined.copy()
            safe_pair = result.pair_name.lower()
            sample.to_csv(out_dir / f"minimal_skeleton_joined_{safe_pair}_{context_tf.lower()}.csv", index=False, encoding="utf-8-sig")

    print(summary.to_string(index=False))
    print(f"out_dir: {out_dir}")
    return 0 if batch.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ERR_BASE_CSV_READ_FAILED",
    "ERR_CONFIRMED_TIME_JOIN_FAILED",
    "ERR_CONTEXT_CSV_READ_FAILED",
    "ERR_NO_BASE_ROWS",
    "ERR_NO_CONTEXT_ROWS",
    "ERR_PAIR_CONFIG_MISSING",
    "MinimalPairScanResult",
    "MinimalScanBatchResult",
    "MinimalScanError",
    "SCAN_STATUS_ERROR",
    "SCAN_STATUS_OK",
    "SCAN_STATUS_SKIPPED",
    "confirmed_time_join_base_context",
    "errors_frame",
    "read_pair_frames",
    "reader_metadata_frame",
    "scan_allowed_pairs_minimal_skeleton",
    "scan_pair_minimal_skeleton",
]
