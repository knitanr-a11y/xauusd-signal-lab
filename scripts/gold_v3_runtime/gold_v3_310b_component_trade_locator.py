#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

PROFILES: dict[str, dict[int, int]] = {
    "STAGE284_286_SAFE": {2024: 242, 2025: 229, 2026: 102},
    "STAGE284_CORE": {2024: 228, 2025: 215, 2026: 99},
    "BASE_ROLLOVER": {2024: 188, 2025: 185, 2026: 86},
    "STAGE280_CANDIDATE": {2024: 12, 2025: 17, 2026: 11},
    "STAGE281_CANDIDATE": {2024: 39, 2025: 30, 2026: 14},
    "STAGE286_STRICT": {2024: 26, 2025: 28, 2026: 7},
}

BANNED_PATH_TOKENS = (
    "gold_v2",
    "old_gold",
    "旧gold",
    "disc8",
    "stage41",
)
SEARCH_PATTERNS = (
    "*trade*.csv",
    "*ledger*.csv",
    "*candidate*.csv",
    "*portfolio*.csv",
    "*stage280*.csv",
    "*stage281*.csv",
    "*stage284*.csv",
    "*stage286*.csv",
    "*rollover*.csv",
    "*shadow*.csv",
)
SKIP_NAME_TOKENS = (
    "goldsharp_m1",
    "goldsharp_m5",
    "goldsharp_m15",
    "goldsharp_h1",
    "goldsharp_h4",
    "goldsharp_d1",
    "candles",
    "ohlc",
    "training_history",
)

ENTRY_COLUMNS = ("entry_dt", "entry_time", "entry_datetime", "planned_entry_dt", "entry")
EXIT_COLUMNS = ("exit_dt", "exit_time", "exit_datetime", "resolved_dt", "close_dt", "exit")
PNL_COLUMNS = (
    "spread_adjusted_pnl",
    "net_pnl",
    "pnl_usd",
    "net_profit_usd",
    "realized_pnl_usd",
    "result_usd",
    "pnl",
    "profit_usd",
    "profit",
    "net_profit",
    "realized_pnl",
    "pnl_net",
    "pnl_raw",
    "pnl_net_cost3",
    "pnl_net_cost5",
    "cost2_pnl",
    "net_cost2",
    "gross_pnl",
    "sum",
)
R_COLUMNS = ("spread_adjusted_r", "net_r", "pnl_r", "r")
ENTRY_PRICE_COLUMNS = ("entry_price", "reference_price", "open_price", "entry_mid_price")
EXIT_PRICE_COLUMNS = ("exit_price", "close_price")
DIRECTION_COLUMNS = ("direction_num", "side_num", "sign", "direction", "side")
SOURCE_COLUMNS = (
    "source",
    "candidate_source",
    "stage",
    "candidate_type",
    "candidate_contract",
    "family",
    "role",
    "signal_family",
)
PRIORITY_COLUMNS = ("priority", "candidate_priority", "priority_order", "portfolio_rank")
ID_COLUMNS = ("candidate_id", "trade_id", "id", "candidate_key", "portfolio_trade_no")
GROUP_COLUMNS = (
    "portfolio",
    "portfolio_name",
    "variant",
    "profile",
    "profile_id",
    "output_set",
    "rule",
    "candidate_contract",
    "candidate_name",
    "strategy_label",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--copy-to", default="")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def path_allowed(path: Path) -> bool:
    lowered = str(path).replace("\\", "/").lower()
    return not any(token in lowered for token in BANNED_PATH_TOKENS)


def search_roots(candle_dir: Path) -> list[Path]:
    candidates = [
        candle_dir,
        candle_dir.parent,
        candle_dir.parent.parent,
        candle_dir.parents[2] if len(candle_dir.parents) > 2 else candle_dir,
        Path(__file__).resolve().parents[2],
        Path(__file__).resolve().parents[2] / "docs" / "gold_v3",
    ]
    roots: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists() and path_allowed(resolved) and resolved not in roots:
            roots.append(resolved)
    return roots


def discover_paths(roots: list[Path]) -> list[Path]:
    found: set[Path] = set()
    for root in roots:
        for pattern in SEARCH_PATTERNS:
            for path in root.rglob(pattern):
                if not path.is_file() or path.suffix.lower() != ".csv":
                    continue
                if not path_allowed(path):
                    continue
                lower_name = path.name.lower()
                if any(token in lower_name for token in SKIP_NAME_TOKENS):
                    continue
                if path.stat().st_size > 250 * 1024 * 1024:
                    continue
                found.add(path.resolve())
    return sorted(found, key=lambda item: str(item).lower())


def read_csv(path: Path, nrows: int | None = None) -> tuple[pd.DataFrame, str]:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(path, encoding=encoding, nrows=nrows), encoding
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"CSV_READ_FAILED: {path}: {last_error}")


def find_column(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    lookup = {str(column).strip().lower(): str(column) for column in columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def direction_num(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    text = series.astype(str).str.upper().str.strip()
    mapped = text.map(
        {
            "LONG": 1.0,
            "BUY": 1.0,
            "B": 1.0,
            "1": 1.0,
            "SHORT": -1.0,
            "SELL": -1.0,
            "S": -1.0,
            "-1": -1.0,
        }
    )
    return numeric.where(numeric.isin([-1, 1]), mapped)


def normalize_source_value(value: Any) -> str:
    text = str(value if value is not None else "").upper()
    if "BASE" in text or "ROLLOVER" in text or "ROUTER" in text:
        return "BASE"
    if "280" in text or "REV_LONG_Q95" in text:
        return "STAGE280"
    if "281" in text or "M15_CONT_LONG" in text:
        return "STAGE281"
    if "286" in text or "SHORT_EXHAUST" in text:
        return "STAGE286"
    return "EXISTING_UNKNOWN"


def source_priority(source: str) -> int:
    return {
        "BASE": 0,
        "STAGE280": 10,
        "STAGE281": 20,
        "STAGE286": 60,
    }.get(source, 40)


def schema(path: Path) -> dict[str, Any]:
    try:
        header, encoding = read_csv(path, nrows=5)
    except Exception as exc:
        return {"path": str(path), "readable": False, "error": str(exc)}
    columns = [str(column) for column in header.columns]
    entry = find_column(columns, ENTRY_COLUMNS)
    exit_column = find_column(columns, EXIT_COLUMNS)
    pnl = find_column(columns, PNL_COLUMNS)
    r_column = find_column(columns, R_COLUMNS)
    entry_price = find_column(columns, ENTRY_PRICE_COLUMNS)
    exit_price = find_column(columns, EXIT_PRICE_COLUMNS)
    direction = find_column(columns, DIRECTION_COLUMNS)
    source = find_column(columns, SOURCE_COLUMNS)
    priority = find_column(columns, PRIORITY_COLUMNS)
    candidate_id = find_column(columns, ID_COLUMNS)
    groups = [column for column in GROUP_COLUMNS if column in columns]
    compatible = bool(
        entry
        and exit_column
        and (pnl or (entry_price and exit_price and direction))
    )
    return {
        "path": str(path),
        "readable": True,
        "encoding": encoding,
        "columns": columns,
        "entry_column": entry,
        "exit_column": exit_column,
        "pnl_column": pnl,
        "r_column": r_column,
        "entry_price_column": entry_price,
        "exit_price_column": exit_price,
        "direction_column": direction,
        "source_column": source,
        "priority_column": priority,
        "candidate_id_column": candidate_id,
        "group_columns": groups,
        "compatible": compatible,
    }


def profile_match(year_counts: dict[int, int]) -> list[str]:
    return [
        name
        for name, expected in PROFILES.items()
        if all(int(year_counts.get(year, 0)) == count for year, count in expected.items())
        and sum(int(year_counts.get(year, 0)) for year in expected) == sum(expected.values())
    ]


def summarize_subset(
    path: Path,
    frame: pd.DataFrame,
    spec: dict[str, Any],
    filter_column: str | None,
    filter_value: str | None,
) -> dict[str, Any] | None:
    entry = pd.to_datetime(frame[spec["entry_column"]], errors="coerce")
    exit_dt = pd.to_datetime(frame[spec["exit_column"]], errors="coerce")
    valid = entry.notna() & exit_dt.notna() & exit_dt.ge(entry)
    clean = frame.loc[valid].copy()
    entry = entry.loc[valid]
    if clean.empty:
        return None
    years = entry.dt.year
    year_counts = {year: int((years == year).sum()) for year in (2024, 2025, 2026)}
    outside = int((~years.isin([2024, 2025, 2026])).sum())
    matches = profile_match(year_counts) if outside == 0 else []
    return {
        "path": str(path),
        "filter_column": filter_column,
        "filter_value": filter_value,
        "rows": int(len(clean)),
        "outside_2024_2026_rows": outside,
        "year_counts": {str(key): value for key, value in year_counts.items()},
        "profile_matches": matches,
        "first_entry": str(entry.min()),
        "last_entry": str(entry.max()),
        "schema": spec,
    }


def inspect_file(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    spec = schema(path)
    if not spec.get("compatible"):
        return [], spec
    try:
        frame, encoding = read_csv(path)
    except Exception as exc:
        spec["full_read_error"] = str(exc)
        return [], spec
    spec["encoding"] = encoding
    if len(frame) > 250_000:
        spec["skipped_reason"] = "too many rows for a historical component ledger"
        return [], spec

    subsets: list[dict[str, Any]] = []
    whole = summarize_subset(path, frame, spec, None, None)
    if whole is not None:
        subsets.append(whole)

    for group_column in spec["group_columns"][:4]:
        values = frame[group_column].dropna().astype(str)
        if values.nunique() > 100:
            continue
        for value in sorted(values.unique()):
            selected = frame[frame[group_column].astype(str).eq(value)].copy()
            summary = summarize_subset(path, selected, spec, group_column, value)
            if summary is not None:
                subsets.append(summary)
    return subsets, spec


def materialize(selected: dict[str, Any], destination: Path) -> dict[str, Any]:
    path = Path(selected["path"])
    frame, _ = read_csv(path)
    if selected["filter_column"] is not None:
        frame = frame[
            frame[selected["filter_column"]].astype(str).eq(selected["filter_value"])
        ].copy()
    spec = selected["schema"]
    entry_dt = pd.to_datetime(frame[spec["entry_column"]], errors="coerce")
    exit_dt = pd.to_datetime(frame[spec["exit_column"]], errors="coerce")
    valid = entry_dt.notna() & exit_dt.notna() & exit_dt.ge(entry_dt)
    frame = frame.loc[valid].copy()
    entry_dt = entry_dt.loc[valid]
    exit_dt = exit_dt.loc[valid]

    if spec["pnl_column"]:
        pnl = pd.to_numeric(frame[spec["pnl_column"]], errors="coerce")
        pnl_derivation = spec["pnl_column"]
    else:
        entry_price = pd.to_numeric(frame[spec["entry_price_column"]], errors="coerce")
        exit_price = pd.to_numeric(frame[spec["exit_price_column"]], errors="coerce")
        direction = direction_num(frame[spec["direction_column"]])
        pnl = direction * (exit_price - entry_price)
        pnl_derivation = "direction*(exit_price-entry_price)"

    if spec["r_column"]:
        pnl_r = pd.to_numeric(frame[spec["r_column"]], errors="coerce")
    else:
        pnl_r = pd.Series(np.nan, index=frame.index)

    if spec["source_column"]:
        source_seed = frame[spec["source_column"]]
    elif spec["candidate_id_column"]:
        source_seed = frame[spec["candidate_id_column"]]
    else:
        source_seed = pd.Series("", index=frame.index)
    source = source_seed.map(normalize_source_value)

    if spec["candidate_id_column"]:
        candidate_id = frame[spec["candidate_id_column"]].astype(str)
    else:
        candidate_id = pd.Series("", index=frame.index)
    generated = (
        "EXISTING|"
        + source.astype(str)
        + "|"
        + entry_dt.astype(str)
        + "|"
        + pd.Series(range(len(frame)), index=frame.index).astype(str)
    )
    candidate_id = candidate_id.where(
        candidate_id.str.len().gt(0) & candidate_id.ne("nan"), generated
    )

    if spec["priority_column"]:
        priority = pd.to_numeric(frame[spec["priority_column"]], errors="coerce")
        priority = priority.where(priority.notna(), source.map(source_priority))
    else:
        priority = source.map(source_priority)

    normalized = pd.DataFrame(
        {
            "candidate_id": candidate_id,
            "source": source,
            "priority": priority.astype(int),
            "entry_dt": entry_dt,
            "exit_dt": exit_dt,
            "pnl_usd": pnl,
            "pnl_r": pnl_r,
        }
    ).dropna(subset=["entry_dt", "exit_dt", "pnl_usd"])
    normalized = normalized.sort_values(
        ["entry_dt", "exit_dt", "candidate_id"], kind="mergesort"
    ).reset_index(drop=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(destination, index=False, encoding="utf-8-sig")
    return {
        "destination": str(destination),
        "rows": int(len(normalized)),
        "pnl_derivation": pnl_derivation,
        "source_counts": {
            str(key): int(value)
            for key, value in normalized.source.value_counts().sort_index().items()
        },
        "sha256": sha256_file(destination),
    }


def choose_exact(matches: list[dict[str, Any]], profile: str) -> tuple[dict[str, Any] | None, str]:
    candidates = [item for item in matches if profile in item["profile_matches"]]
    if len(candidates) == 1:
        return candidates[0], "single exact year-count match"
    if not candidates:
        return None, "no exact year-count match"
    ranked = sorted(
        candidates,
        key=lambda item: (
            0 if "stage286" in Path(item["path"]).name.lower() else 1,
            0 if item["filter_value"] and "safe" in item["filter_value"].lower() else 1,
            len(str(item["path"])),
            str(item["path"]).lower(),
        ),
    )
    first_key = (
        "stage286" in Path(ranked[0]["path"]).name.lower(),
        bool(ranked[0]["filter_value"] and "safe" in ranked[0]["filter_value"].lower()),
    )
    second_key = (
        "stage286" in Path(ranked[1]["path"]).name.lower(),
        bool(ranked[1]["filter_value"] and "safe" in ranked[1]["filter_value"].lower()),
    )
    if first_key != second_key:
        return ranked[0], "unique preferred exact match"
    return None, f"{len(candidates)} exact matches remain ambiguous"


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else candle_dir / "stage310b_component_trade_locator.json"
    )
    copy_to = (
        Path(args.copy_to).expanduser().resolve()
        if args.copy_to
        else candle_dir / "stage310_existing_portfolio_trades_input.csv"
    )

    roots = search_roots(candle_dir)
    paths = discover_paths(roots)
    all_subsets: list[dict[str, Any]] = []
    schemas: list[dict[str, Any]] = []
    for path in paths:
        subsets, spec = inspect_file(path)
        schemas.append(spec)
        all_subsets.extend(subsets)

    exact_matches = [item for item in all_subsets if item["profile_matches"]]
    selected_safe, safe_reason = choose_exact(exact_matches, "STAGE284_286_SAFE")
    selected_core, core_reason = choose_exact(exact_matches, "STAGE284_CORE")

    materialized = None
    if selected_safe is not None:
        materialized = materialize(selected_safe, copy_to)
        status = "GOLD_V3_310B_STAGE284_286_SAFE_LEDGER_READY"
        decision = "RUN_STAGE310_WITH_EXACT_SAFE_LEDGER"
        exit_code = 0
    elif selected_core is not None:
        core_destination = copy_to.with_name("stage310b_stage284_core_trades_input.csv")
        materialized = materialize(selected_core, core_destination)
        status = "GOLD_V3_310B_STAGE284_CORE_FOUND_STAGE286_SAFE_MISSING"
        decision = "RECONSTRUCT_STAGE286_SAFE_FROM_COMPONENTS_BEFORE_STAGE310"
        exit_code = 3
    else:
        status = "GOLD_V3_310B_COMPONENT_LEDGERS_NOT_RECOVERED"
        decision = "REGENERATE_BASE_STAGE280_STAGE281_STAGE286_TRADE_LEDGERS"
        exit_code = 2

    by_profile = {
        profile: [item for item in exact_matches if profile in item["profile_matches"]]
        for profile in PROFILES
    }
    report = {
        "status": status,
        "mode": "AUDIT_ONLY_STRUCTURAL_COMPONENT_LEDGER_LOCATOR",
        "decision": decision,
        "expected_profiles": {
            name: {str(year): count for year, count in counts.items()}
            for name, counts in PROFILES.items()
        },
        "searched_roots": [str(root) for root in roots],
        "absolute_exclusions": list(BANNED_PATH_TOKENS),
        "scanned_file_count": len(paths),
        "compatible_file_count": sum(bool(spec.get("compatible")) for spec in schemas),
        "examined_subset_count": len(all_subsets),
        "exact_match_count": len(exact_matches),
        "safe_selection_reason": safe_reason,
        "core_selection_reason": core_reason,
        "selected_safe": selected_safe,
        "selected_core": selected_core,
        "materialized": materialized,
        "matches_by_profile": by_profile,
        "exact_matches": exact_matches[:300],
        "compatible_schemas": [spec for spec in schemas if spec.get("compatible")][:300],
        "important": "A ledger is selected only when its exact 2024/2025/2026 trade counts match the frozen Stage284/286 contract. Similar filenames or generic GOLD/BTC ledgers are not accepted.",
        "promotion": {
            "performed": False,
            "stage292_candidate_pool_changed": False,
            "shadow_enabled": False,
        },
        "safety_flags": {
            "final_signal_changed": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
