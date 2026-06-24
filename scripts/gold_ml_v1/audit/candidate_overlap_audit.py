#!/usr/bin/env python3
"""GOLD_ML_V1 six-candidate overlap and independence audit.

Audit-only. This module never creates trading signals, changes candidate logic,
or uses post-entry outcomes as entry-time filters. Realized R is read only for
retrospective overlap/correlation diagnostics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


CANONICAL_REQUIRED = (
    "decision_close_time",
    "entry_time",
    "exit_time",
    "r_value",
    "direction",
)


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    lane: str
    direction: str
    decision_bar_minutes: int
    parent_id: str | None
    lineage_root: str
    expected_registry_sha256: str | None


@dataclass
class LoadedRegistry:
    spec: CandidateSpec
    path: Path
    sha256: str
    frame: pd.DataFrame
    column_resolution: dict[str, str]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (pd.Timestamp, pd.Period)):
        return str(value)
    return value


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(_json_safe(payload), handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def csv_dump(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def parse_registry_args(values: Iterable[str]) -> dict[str, Path]:
    parsed: dict[str, Path] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"--registry must be CANDIDATE_ID=PATH: {raw!r}")
        candidate_id, raw_path = raw.split("=", 1)
        candidate_id = candidate_id.strip()
        path = Path(raw_path.strip()).expanduser()
        if not candidate_id or not raw_path.strip():
            raise ValueError(f"invalid --registry value: {raw!r}")
        if candidate_id in parsed:
            raise ValueError(f"duplicate registry argument for {candidate_id}")
        parsed[candidate_id] = path
    return parsed


def load_config(path: Path) -> tuple[dict[str, Any], dict[str, CandidateSpec]]:
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    if config.get("audit_only") is not True:
        raise ValueError("config must explicitly set audit_only=true")
    specs: dict[str, CandidateSpec] = {}
    for item in config["candidates"]:
        spec = CandidateSpec(
            candidate_id=item["candidate_id"],
            lane=item["lane"],
            direction=item["direction"].upper(),
            decision_bar_minutes=int(item["decision_bar_minutes"]),
            parent_id=item.get("parent_id"),
            lineage_root=item["lineage_root"],
            expected_registry_sha256=item.get("expected_registry_sha256"),
        )
        if spec.candidate_id in specs:
            raise ValueError(f"duplicate candidate in config: {spec.candidate_id}")
        specs[spec.candidate_id] = spec
    return config, specs


def _resolve_column(columns: list[str], canonical: str, aliases: dict[str, list[str]]) -> str:
    candidates = [canonical, *aliases.get(canonical, [])]
    found = [name for name in candidates if name in columns]
    if len(found) == 0:
        raise ValueError(f"missing required column {canonical!r}; accepted={candidates}")
    if len(found) > 1:
        raise ValueError(f"ambiguous columns for {canonical!r}: {found}")
    return found[0]


def _parse_naive_timestamp(series: pd.Series, name: str) -> pd.Series:
    parsed = pd.to_datetime(series, errors="raise")
    tz = getattr(parsed.dt, "tz", None)
    if tz is not None:
        raise ValueError(f"{name} must preserve naive MT5 server time, got timezone-aware values")
    if parsed.isna().any():
        raise ValueError(f"{name} contains NaT")
    return parsed


def load_registry(
    spec: CandidateSpec,
    path: Path,
    aliases: dict[str, list[str]],
    verify_hash: bool,
) -> LoadedRegistry:
    if not path.is_file():
        raise FileNotFoundError(f"registry not found for {spec.candidate_id}: {path}")
    actual_hash = sha256_file(path)
    if verify_hash and spec.expected_registry_sha256 and actual_hash != spec.expected_registry_sha256:
        raise ValueError(
            f"registry SHA256 mismatch for {spec.candidate_id}: "
            f"expected={spec.expected_registry_sha256} actual={actual_hash}"
        )

    raw = pd.read_csv(path)
    columns = list(raw.columns)
    resolution = {name: _resolve_column(columns, name, aliases) for name in CANONICAL_REQUIRED}
    optional_canonical = ("session", "regime", "atr_regime", "volatility_regime")
    for name in optional_canonical:
        candidates = [name, *aliases.get(name, [])]
        found = [col for col in candidates if col in columns]
        if len(found) > 1:
            raise ValueError(f"ambiguous optional columns for {name!r}: {found}")
        if found:
            resolution[name] = found[0]

    frame = pd.DataFrame(index=raw.index)
    for canonical, source in resolution.items():
        frame[canonical] = raw[source]
    for name in ("decision_close_time", "entry_time", "exit_time"):
        frame[name] = _parse_naive_timestamp(frame[name], name)
    frame["r_value"] = pd.to_numeric(frame["r_value"], errors="raise")
    if not np.isfinite(frame["r_value"].to_numpy(dtype=float)).all():
        raise ValueError(f"non-finite r_value in {spec.candidate_id}")
    frame["direction"] = frame["direction"].astype(str).str.upper().str.strip()
    invalid_direction = ~frame["direction"].isin(["LONG", "SHORT"])
    if invalid_direction.any():
        values = sorted(frame.loc[invalid_direction, "direction"].unique().tolist())
        raise ValueError(f"invalid direction values in {spec.candidate_id}: {values}")
    if not frame["direction"].eq(spec.direction).all():
        values = sorted(frame["direction"].unique().tolist())
        raise ValueError(
            f"direction mismatch for {spec.candidate_id}: config={spec.direction} registry={values}"
        )
    if frame["entry_time"].duplicated().any():
        duplicates = frame.loc[frame["entry_time"].duplicated(False), "entry_time"].head(10).tolist()
        raise ValueError(f"duplicate entry_time in {spec.candidate_id}: {duplicates}")
    if (frame["decision_close_time"] > frame["entry_time"]).any():
        raise ValueError(f"decision_close_time after entry_time in {spec.candidate_id}")
    if (frame["exit_time"] < frame["entry_time"]).any():
        raise ValueError(f"exit_time before entry_time in {spec.candidate_id}")

    frame["candidate_id"] = spec.candidate_id
    frame = frame.sort_values(["entry_time", "exit_time"], kind="mergesort").reset_index(drop=True)
    return LoadedRegistry(spec, path, actual_hash, frame, resolution)


def window_mask(frame: pd.DataFrame, window: dict[str, Any]) -> pd.Series:
    ts = frame[window.get("timestamp_column", "decision_close_time")]
    mask = pd.Series(True, index=frame.index)
    if window.get("start_exclusive"):
        mask &= ts > pd.Timestamp(window["start_exclusive"])
    if window.get("start_inclusive"):
        mask &= ts >= pd.Timestamp(window["start_inclusive"])
    if window.get("end_exclusive"):
        mask &= ts < pd.Timestamp(window["end_exclusive"])
    if window.get("end_inclusive"):
        mask &= ts <= pd.Timestamp(window["end_inclusive"])
    return mask


def subset_for_window(registry: LoadedRegistry, window: dict[str, Any]) -> pd.DataFrame:
    return registry.frame.loc[window_mask(registry.frame, window)].copy()


def exact_pair_metrics(a: pd.DataFrame, b: pd.DataFrame) -> dict[str, Any]:
    a_times = set(a["entry_time"])
    b_times = set(b["entry_time"])
    intersection = a_times & b_times
    union = a_times | b_times
    if intersection:
        a_dir = a.set_index("entry_time")["direction"]
        b_dir = b.set_index("entry_time")["direction"]
        same_direction = sum(a_dir.loc[t] == b_dir.loc[t] for t in intersection)
    else:
        same_direction = 0
    return {
        "a_count": len(a_times),
        "b_count": len(b_times),
        "matched_count": len(intersection),
        "jaccard": (len(intersection) / len(union)) if union else math.nan,
        "a_match_fraction": (len(intersection) / len(a_times)) if a_times else math.nan,
        "b_match_fraction": (len(intersection) / len(b_times)) if b_times else math.nan,
        "same_direction_matches": same_direction,
        "opposite_direction_matches": len(intersection) - same_direction,
    }


def greedy_fuzzy_match(a_times: pd.Series, b_times: pd.Series, tolerance: pd.Timedelta) -> list[tuple[int, int, float]]:
    a_values = pd.DatetimeIndex(a_times).asi8
    b_values = pd.DatetimeIndex(b_times).asi8
    tol_ns = int(tolerance.value)
    candidate_pairs: list[tuple[int, int, int]] = []
    for i, value in enumerate(a_values):
        left = int(np.searchsorted(b_values, value - tol_ns, side="left"))
        right = int(np.searchsorted(b_values, value + tol_ns, side="right"))
        for j in range(left, right):
            candidate_pairs.append((abs(int(value - b_values[j])), i, j))
    candidate_pairs.sort(key=lambda item: (item[0], a_values[item[1]], b_values[item[2]]))
    used_a: set[int] = set()
    used_b: set[int] = set()
    matches: list[tuple[int, int, float]] = []
    for delta_ns, i, j in candidate_pairs:
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        matches.append((i, j, delta_ns / 60_000_000_000.0))
    return matches


def fuzzy_pair_metrics(a: pd.DataFrame, b: pd.DataFrame, tolerance_minutes: int) -> dict[str, Any]:
    # searchsorted requires sorted decision timestamps. Entry order is normally the
    # same, but sorting here makes the matching contract explicit and fail-safe.
    a = a.sort_values("decision_close_time", kind="stable").reset_index(drop=True)
    b = b.sort_values("decision_close_time", kind="stable").reset_index(drop=True)
    matches = greedy_fuzzy_match(
        a["decision_close_time"],
        b["decision_close_time"],
        pd.Timedelta(minutes=tolerance_minutes),
    )
    matched = len(matches)
    union = len(a) + len(b) - matched
    deltas = [m[2] for m in matches]
    same_direction = sum(
        a.iloc[i]["direction"] == b.iloc[j]["direction"] for i, j, _ in matches
    )
    return {
        "a_count": len(a),
        "b_count": len(b),
        "matched_count": matched,
        "jaccard": (matched / union) if union else math.nan,
        "a_match_fraction": (matched / len(a)) if len(a) else math.nan,
        "b_match_fraction": (matched / len(b)) if len(b) else math.nan,
        "same_direction_matches": same_direction,
        "opposite_direction_matches": matched - same_direction,
        "mean_abs_delta_minutes": float(np.mean(deltas)) if deltas else math.nan,
        "max_abs_delta_minutes": float(np.max(deltas)) if deltas else math.nan,
    }


def concurrent_exposure_metrics(a: pd.DataFrame, b: pd.DataFrame) -> dict[str, Any]:
    pair_count = 0
    total_overlap_minutes = 0.0
    a_hit: set[int] = set()
    b_hit: set[int] = set()
    for i, row_a in a.reset_index(drop=True).iterrows():
        for j, row_b in b.reset_index(drop=True).iterrows():
            start = max(row_a["entry_time"], row_b["entry_time"])
            end = min(row_a["exit_time"], row_b["exit_time"])
            if start < end:
                pair_count += 1
                a_hit.add(i)
                b_hit.add(j)
                total_overlap_minutes += (end - start).total_seconds() / 60.0
    return {
        "a_count": len(a),
        "b_count": len(b),
        "concurrent_trade_pairs": pair_count,
        "a_trades_with_any_concurrency": len(a_hit),
        "b_trades_with_any_concurrency": len(b_hit),
        "a_concurrent_fraction": (len(a_hit) / len(a)) if len(a) else math.nan,
        "b_concurrent_fraction": (len(b_hit) / len(b)) if len(b) else math.nan,
        "summed_overlap_minutes": total_overlap_minutes,
    }


def pf_from_series(values: pd.Series) -> float:
    positive = float(values[values > 0].sum())
    negative = float(values[values < 0].sum())
    if negative == 0.0:
        return math.inf if positive > 0 else math.nan
    return positive / abs(negative)


def concentration_rows(
    registry: LoadedRegistry,
    window_name: str,
    frame: pd.DataFrame,
    session_bins: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    work = frame.copy()
    work["year"] = work["decision_close_time"].dt.year.astype(str)
    work["quarter"] = work["decision_close_time"].dt.to_period("Q").astype(str)
    if "session" not in work.columns:
        hour = work["decision_close_time"].dt.hour
        labels = pd.Series("UNMAPPED", index=work.index, dtype="object")
        for item in session_bins:
            lo, hi = int(item["start_hour_inclusive"]), int(item["end_hour_inclusive"])
            if lo <= hi:
                mask = hour.between(lo, hi)
            else:
                mask = (hour >= lo) | (hour <= hi)
            labels.loc[mask] = item["name"]
        work["session"] = labels
    regime_col = next(
        (name for name in ("regime", "atr_regime", "volatility_regime") if name in work.columns),
        None,
    )
    dimensions = ["year", "quarter", "session"]
    if regime_col:
        dimensions.append(regime_col)
    total_trades = len(work)
    total_abs_r = float(work["r_value"].abs().sum())
    rows: list[dict[str, Any]] = []
    for dimension in dimensions:
        grouped = work.groupby(dimension, dropna=False, sort=True)
        for value, group in grouped:
            rows.append(
                {
                    "candidate_id": registry.spec.candidate_id,
                    "window": window_name,
                    "dimension": "regime" if dimension == regime_col else dimension,
                    "bucket": str(value),
                    "trades": len(group),
                    "trade_share": len(group) / total_trades,
                    "total_r": float(group["r_value"].sum()),
                    "abs_r_share": (
                        float(group["r_value"].abs().sum()) / total_abs_r if total_abs_r > 0 else math.nan
                    ),
                    "profit_factor": pf_from_series(group["r_value"]),
                    "win_rate": float((group["r_value"] > 0).mean()),
                }
            )
    if not regime_col:
        rows.append(
            {
                "candidate_id": registry.spec.candidate_id,
                "window": window_name,
                "dimension": "regime",
                "bucket": "UNAVAILABLE_IN_REGISTRY",
                "trades": total_trades,
                "trade_share": 1.0,
                "total_r": float(work["r_value"].sum()),
                "abs_r_share": 1.0 if total_abs_r > 0 else math.nan,
                "profit_factor": pf_from_series(work["r_value"]),
                "win_rate": float((work["r_value"] > 0).mean()),
            }
        )
    return rows


def monthly_r_table(registries: dict[str, LoadedRegistry], window: dict[str, Any]) -> pd.DataFrame:
    series: dict[str, pd.Series] = {}
    min_month: pd.Period | None = None
    max_month: pd.Period | None = None
    for candidate_id, registry in registries.items():
        frame = subset_for_window(registry, window)
        if frame.empty:
            series[candidate_id] = pd.Series(dtype=float)
            continue
        month = frame["entry_time"].dt.to_period("M")
        grouped = frame.groupby(month)["r_value"].sum().sort_index()
        series[candidate_id] = grouped
        min_month = grouped.index.min() if min_month is None else min(min_month, grouped.index.min())
        max_month = grouped.index.max() if max_month is None else max(max_month, grouped.index.max())
    if min_month is None or max_month is None:
        return pd.DataFrame(columns=sorted(registries))
    full_index = pd.period_range(min_month, max_month, freq="M")
    table = pd.DataFrame(index=full_index)
    for candidate_id in sorted(registries):
        table[candidate_id] = series[candidate_id].reindex(full_index, fill_value=0.0)
    table.index = table.index.astype(str)
    table.index.name = "month"
    return table


def effective_rank_from_corr(corr: pd.DataFrame) -> float:
    if corr.empty:
        return math.nan
    work = corr.fillna(0.0).to_numpy(dtype=float)
    work = (work + work.T) / 2.0
    np.fill_diagonal(work, 1.0)
    eigenvalues = np.linalg.eigvalsh(work)
    eigenvalues = np.clip(eigenvalues, 0.0, None)
    total = float(eigenvalues.sum())
    if total <= 0:
        return math.nan
    probabilities = eigenvalues / total
    entropy = -float(np.sum(probabilities[probabilities > 0] * np.log(probabilities[probabilities > 0])))
    return float(np.exp(entropy))


def connected_components(nodes: list[str], edges: list[tuple[str, str]]) -> list[list[str]]:
    adjacency = {node: set() for node in nodes}
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    components: list[list[str]] = []
    unseen = set(nodes)
    while unseen:
        start = min(unseen)
        stack = [start]
        component: list[str] = []
        unseen.remove(start)
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in sorted(adjacency[node], reverse=True):
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=lambda group: (group[0], len(group)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/gold_ml_v1/candidate_overlap_audit_20260624.json"),
    )
    parser.add_argument(
        "--registry",
        action="append",
        default=[],
        metavar="CANDIDATE_ID=CSV",
        help="repeat exactly once for every configured candidate",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("FX_OUTPUTS/gold_ml_v1/audits/GML1-BATCH-015-overlap"),
    )
    parser.add_argument(
        "--skip-hash-check",
        action="store_true",
        help="diagnostic only; never use for a formal exact-registry audit",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    config, specs = load_config(args.config)
    registry_paths = parse_registry_args(args.registry)
    required_ids = set(specs)
    provided_ids = set(registry_paths)
    missing = sorted(required_ids - provided_ids)
    unexpected = sorted(provided_ids - required_ids)
    if missing or unexpected:
        raise ValueError(f"registry set mismatch; missing={missing} unexpected={unexpected}")

    aliases = config.get("column_aliases", {})
    registries = {
        candidate_id: load_registry(
            spec,
            registry_paths[candidate_id],
            aliases,
            verify_hash=not args.skip_hash_check,
        )
        for candidate_id, spec in specs.items()
    }
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_ids = sorted(registries)
    windows = config["reporting_windows"]

    candidate_rows: list[dict[str, Any]] = []
    exact_rows: list[dict[str, Any]] = []
    fuzzy_rows: list[dict[str, Any]] = []
    concurrency_rows: list[dict[str, Any]] = []
    retention_rows: list[dict[str, Any]] = []
    concentration: list[dict[str, Any]] = []

    for window_name, window in windows.items():
        subsets = {
            candidate_id: subset_for_window(registry, window)
            for candidate_id, registry in registries.items()
        }
        for candidate_id, frame in subsets.items():
            candidate_rows.append(
                {
                    "window": window_name,
                    "candidate_id": candidate_id,
                    "trades": len(frame),
                    "wins": int((frame["r_value"] > 0).sum()),
                    "losses": int((frame["r_value"] < 0).sum()),
                    "zero_r": int((frame["r_value"] == 0).sum()),
                    "win_rate": float((frame["r_value"] > 0).mean()) if len(frame) else math.nan,
                    "profit_factor": pf_from_series(frame["r_value"]),
                    "total_r": float(frame["r_value"].sum()),
                    "first_entry_time": frame["entry_time"].min() if len(frame) else None,
                    "last_entry_time": frame["entry_time"].max() if len(frame) else None,
                }
            )
            concentration.extend(
                concentration_rows(
                    registries[candidate_id], window_name, frame, config["session_buckets"]
                )
            )

        for i, candidate_a in enumerate(candidate_ids):
            for candidate_b in candidate_ids[i + 1 :]:
                a, b = subsets[candidate_a], subsets[candidate_b]
                exact = exact_pair_metrics(a, b)
                exact_rows.append(
                    {"window": window_name, "candidate_a": candidate_a, "candidate_b": candidate_b, **exact}
                )
                tolerance = max(
                    specs[candidate_a].decision_bar_minutes,
                    specs[candidate_b].decision_bar_minutes,
                )
                fuzzy = fuzzy_pair_metrics(a, b, tolerance)
                fuzzy_rows.append(
                    {
                        "window": window_name,
                        "candidate_a": candidate_a,
                        "candidate_b": candidate_b,
                        "tolerance_minutes": tolerance,
                        **fuzzy,
                    }
                )
                concurrency_rows.append(
                    {
                        "window": window_name,
                        "candidate_a": candidate_a,
                        "candidate_b": candidate_b,
                        **concurrent_exposure_metrics(a, b),
                    }
                )

        for child_id, child_spec in specs.items():
            parent_id = child_spec.parent_id
            if not parent_id:
                continue
            if parent_id not in subsets:
                retention_rows.append(
                    {
                        "window": window_name,
                        "parent_id": parent_id,
                        "child_id": child_id,
                        "parent_registry_available": False,
                        "parent_trades": math.nan,
                        "child_trades": len(subsets[child_id]),
                        "exact_overlap": math.nan,
                        "retention_vs_parent": math.nan,
                        "child_contained_fraction": math.nan,
                        "parent_only": math.nan,
                        "unexpected_child_only": math.nan,
                    }
                )
                continue
            parent_times = set(subsets[parent_id]["entry_time"])
            child_times = set(subsets[child_id]["entry_time"])
            overlap = parent_times & child_times
            retention_rows.append(
                {
                    "window": window_name,
                    "parent_id": parent_id,
                    "child_id": child_id,
                    "parent_registry_available": True,
                    "parent_trades": len(parent_times),
                    "child_trades": len(child_times),
                    "exact_overlap": len(overlap),
                    "retention_vs_parent": len(overlap) / len(parent_times) if parent_times else math.nan,
                    "child_contained_fraction": len(overlap) / len(child_times) if child_times else math.nan,
                    "parent_only": len(parent_times - child_times),
                    "unexpected_child_only": len(child_times - parent_times),
                }
            )

    candidate_df = pd.DataFrame(candidate_rows)
    exact_df = pd.DataFrame(exact_rows)
    fuzzy_df = pd.DataFrame(fuzzy_rows)
    concurrency_df = pd.DataFrame(concurrency_rows)
    retention_df = pd.DataFrame(retention_rows)
    concentration_df = pd.DataFrame(concentration)
    csv_dump(output_dir / "candidate_window_metrics.csv", candidate_df)
    csv_dump(output_dir / "exact_entry_overlap.csv", exact_df)
    csv_dump(output_dir / "plus_minus_one_decision_bar_overlap.csv", fuzzy_df)
    csv_dump(output_dir / "concurrent_exposure.csv", concurrency_df)
    csv_dump(output_dir / "parent_derivative_retention.csv", retention_df)
    csv_dump(output_dir / "concentration_breakdown.csv", concentration_df)

    # Export true square Jaccard matrices in addition to auditable long-form rows.
    for window_name in windows:
        for prefix, source in (
            ("exact_entry", exact_df),
            ("plus_minus_one_decision_bar", fuzzy_df),
        ):
            matrix = pd.DataFrame(
                np.eye(len(candidate_ids), dtype=float),
                index=candidate_ids,
                columns=candidate_ids,
            )
            rows = source[source["window"] == window_name]
            for _, row in rows.iterrows():
                a, b = row["candidate_a"], row["candidate_b"]
                matrix.loc[a, b] = row["jaccard"]
                matrix.loc[b, a] = row["jaccard"]
            matrix.insert(0, "candidate_id", matrix.index)
            csv_dump(
                output_dir / f"{prefix}_jaccard_matrix_{window_name}.csv",
                matrix.reset_index(drop=True),
            )

    correlation_long_rows: list[dict[str, Any]] = []
    correlation_matrices: dict[str, pd.DataFrame] = {}
    monthly_tables: dict[str, pd.DataFrame] = {}
    for window_name, window in windows.items():
        table = monthly_r_table(registries, window)
        monthly_tables[window_name] = table
        csv_dump(output_dir / f"monthly_r_{window_name}.csv", table.reset_index())
        if table.empty or len(table) < 2:
            corr = pd.DataFrame(index=candidate_ids, columns=candidate_ids, dtype=float)
        else:
            corr = table.corr()
        correlation_matrices[window_name] = corr
        matrix_out = corr.copy()
        matrix_out.insert(0, "candidate_id", matrix_out.index)
        csv_dump(output_dir / f"monthly_r_correlation_{window_name}.csv", matrix_out.reset_index(drop=True))
        for a in candidate_ids:
            for b in candidate_ids:
                value = corr.loc[a, b] if a in corr.index and b in corr.columns else math.nan
                correlation_long_rows.append(
                    {
                        "window": window_name,
                        "candidate_a": a,
                        "candidate_b": b,
                        "pearson_monthly_r_zero_filled": value,
                        "months": len(table),
                    }
                )
    csv_dump(output_dir / "monthly_r_correlation_long.csv", pd.DataFrame(correlation_long_rows))

    all_exact = exact_df[exact_df["window"] == "all"].copy()
    all_fuzzy = fuzzy_df[fuzzy_df["window"] == "all"].copy()
    all_corr = correlation_matrices.get("all", pd.DataFrame())
    thresholds = config["redundancy_diagnostic_thresholds"]
    redundant_edges: list[dict[str, Any]] = []
    graph_edges: list[tuple[str, str]] = []
    for _, row in all_exact.iterrows():
        a, b = row["candidate_a"], row["candidate_b"]
        fuzzy_row = all_fuzzy[(all_fuzzy["candidate_a"] == a) & (all_fuzzy["candidate_b"] == b)].iloc[0]
        corr = (
            float(all_corr.loc[a, b])
            if a in all_corr.index and b in all_corr.columns and pd.notna(all_corr.loc[a, b])
            else math.nan
        )
        reasons: list[str] = []
        if pd.notna(row["jaccard"]) and row["jaccard"] >= thresholds["exact_entry_jaccard_gte"]:
            reasons.append("EXACT_ENTRY_JACCARD")
        if pd.notna(fuzzy_row["jaccard"]) and fuzzy_row["jaccard"] >= thresholds["fuzzy_entry_jaccard_gte"]:
            reasons.append("FUZZY_ENTRY_JACCARD")
        if pd.notna(corr) and corr >= thresholds["monthly_r_correlation_gte"]:
            reasons.append("MONTHLY_R_CORRELATION")
        if reasons:
            graph_edges.append((a, b))
            redundant_edges.append(
                {
                    "candidate_a": a,
                    "candidate_b": b,
                    "reasons": reasons,
                    "exact_jaccard": row["jaccard"],
                    "fuzzy_jaccard": fuzzy_row["jaccard"],
                    "monthly_r_correlation": corr,
                }
            )

    lineage_groups: dict[str, list[str]] = {}
    for spec in specs.values():
        lineage_groups.setdefault(spec.lineage_root, []).append(spec.candidate_id)
    for group in lineage_groups.values():
        group.sort()

    summary = {
        "audit_id": config["audit_id"],
        "status": "OUTPUTS_GENERATED_AUDIT_ONLY",
        "audit_only": True,
        "candidate_logic_changed": False,
        "candidate_ids": candidate_ids,
        "structural_lineage_groups": dict(sorted(lineage_groups.items())),
        "structural_lineage_group_count": len(lineage_groups),
        "empirical_effective_rank_monthly_r_all": effective_rank_from_corr(all_corr),
        "threshold_flagged_redundancy_edges": redundant_edges,
        "threshold_flagged_components": connected_components(candidate_ids, graph_edges),
        "interpretation_warning": (
            "Structural lineage count and monthly-R effective rank are diagnostics, not permission "
            "to register, activate, combine, or retune candidates."
        ),
        "2026_policy": config["2026_policy"],
        "fresh_prospective_cutoff_mt5_server_close": config[
            "fresh_prospective_cutoff_mt5_server_close"
        ],
    }
    json_dump(output_dir / "independence_summary.json", summary)

    manifest = {
        "audit_id": config["audit_id"],
        "config_path": str(args.config),
        "config_sha256": sha256_file(args.config),
        "hash_verification_skipped": bool(args.skip_hash_check),
        "inputs": {
            candidate_id: {
                "path": str(reg.path),
                "sha256": reg.sha256,
                "expected_sha256": reg.spec.expected_registry_sha256,
                "rows": len(reg.frame),
                "column_resolution": reg.column_resolution,
            }
            for candidate_id, reg in sorted(registries.items())
        },
        "outputs": {},
    }
    for path in sorted(output_dir.iterdir()):
        if path.name == "manifest.json" or not path.is_file():
            continue
        manifest["outputs"][path.name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    json_dump(output_dir / "manifest.json", manifest)
    print(json.dumps({"status": "ok", "output_dir": str(output_dir)}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run(args)
    except Exception as exc:  # fail closed with concise operator-facing error
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
