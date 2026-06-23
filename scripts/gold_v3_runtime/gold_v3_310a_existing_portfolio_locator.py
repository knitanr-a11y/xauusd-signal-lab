#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

EXACT_NAMES = (
    "gold_v3_stage286_short_selected_portfolio_trades.csv",
    "gold_v3_stage286_selected_portfolio_trades.csv",
    "stage286_short_selected_portfolio_trades.csv",
    "gold_v3_stage284_balanced_portfolio_trades.csv",
    "gold_v3_stage284_selected_portfolio_trades.csv",
    "stage284_balanced_portfolio_trades.csv",
)
PATTERNS = (
    "*stage286*portfolio*trade*.csv",
    "*stage284*portfolio*trade*.csv",
    "*selected*portfolio*trade*.csv",
    "*safe*portfolio*trade*.csv",
    "*portfolio*trade*ledger*.csv",
    "*portfolio*trades*.csv",
)
BANNED_PATH_TOKENS = (
    "gold_v2",
    "old_gold",
    "旧gold",
    "disc8",
    "stage41",
)
ENTRY_COLUMNS = (
    "entry_dt",
    "entry_time",
    "entry_datetime",
    "planned_entry_dt",
    "entry",
)
EXIT_COLUMNS = (
    "exit_dt",
    "exit_time",
    "exit_datetime",
    "resolved_dt",
    "close_dt",
    "exit",
)
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
)
ENTRY_PRICE_COLUMNS = ("entry_price", "reference_price", "open_price")
EXIT_PRICE_COLUMNS = ("exit_price", "close_price")
DIRECTION_COLUMNS = ("direction_num", "side_num", "sign", "direction", "side")
SOURCE_COLUMNS = (
    "source",
    "candidate_source",
    "stage",
    "candidate_type",
    "candidate_contract",
)
PRIORITY_COLUMNS = ("priority", "candidate_priority")
CANDIDATE_ID_COLUMNS = ("candidate_id", "trade_id", "id", "candidate_key")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--copy-to", default="")
    parser.add_argument("--explicit", default="")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_header(path: Path) -> tuple[pd.DataFrame, str]:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(path, encoding=encoding, nrows=8), encoding
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"HEADER_READ_FAILED: {path}: {last_error}")


def find_column(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    lookup = {str(column).strip().lower(): str(column) for column in columns}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in lookup:
            return lookup[key]
    return None


def count_csv_rows(path: Path) -> int:
    line_count = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            line_count += chunk.count(b"\n")
    return max(0, line_count - 1)


def path_is_allowed(path: Path) -> bool:
    lowered = str(path).replace("\\", "/").lower()
    return not any(token in lowered for token in BANNED_PATH_TOKENS)


def search_roots(candle_dir: Path) -> list[Path]:
    roots: list[Path] = []
    for candidate in (
        candle_dir,
        candle_dir.parent,
        candle_dir.parent.parent if len(candle_dir.parents) >= 2 else candle_dir,
        candle_dir.parents[2] if len(candle_dir.parents) >= 3 else candle_dir,
        Path(__file__).resolve().parents[2],
        Path(__file__).resolve().parents[2] / "docs" / "gold_v3",
    ):
        resolved = candidate.resolve()
        if resolved.exists() and resolved not in roots and path_is_allowed(resolved):
            roots.append(resolved)
    return roots


def candidate_paths(roots: list[Path], explicit: Path | None) -> list[Path]:
    if explicit is not None:
        return [explicit]
    found: set[Path] = set()
    for root in roots:
        for name in EXACT_NAMES:
            for path in root.rglob(name):
                if path.is_file() and path_is_allowed(path):
                    found.add(path.resolve())
        for pattern in PATTERNS:
            for path in root.rglob(pattern):
                if path.is_file() and path_is_allowed(path):
                    found.add(path.resolve())
    return sorted(found, key=lambda path: str(path).lower())


def inspect_candidate(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": str(path),
        "name": path.name,
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else None,
    }
    if not path.exists() or not path.is_file():
        record.update(
            {
                "compatible_trade_ledger": False,
                "classification": "MISSING",
                "reason": "file does not exist",
                "score": -1000,
            }
        )
        return record
    try:
        sample, encoding = read_header(path)
    except Exception as exc:
        record.update(
            {
                "compatible_trade_ledger": False,
                "classification": "UNREADABLE",
                "reason": str(exc),
                "score": -500,
            }
        )
        return record

    columns = [str(column) for column in sample.columns]
    entry = find_column(columns, ENTRY_COLUMNS)
    exit_column = find_column(columns, EXIT_COLUMNS)
    pnl = find_column(columns, PNL_COLUMNS)
    entry_price = find_column(columns, ENTRY_PRICE_COLUMNS)
    exit_price = find_column(columns, EXIT_PRICE_COLUMNS)
    direction = find_column(columns, DIRECTION_COLUMNS)
    source = find_column(columns, SOURCE_COLUMNS)
    priority = find_column(columns, PRIORITY_COLUMNS)
    candidate_id = find_column(columns, CANDIDATE_ID_COLUMNS)
    has_price_pnl = bool(entry_price and exit_price and direction)
    compatible = bool(entry and exit_column and (pnl or has_price_pnl))
    row_count = count_csv_rows(path)

    year_min = None
    year_max = None
    parsed_entry_rows = 0
    if entry is not None and row_count <= 2_000_000:
        try:
            values = pd.read_csv(
                path,
                encoding=encoding,
                usecols=[entry],
            )[entry]
            parsed = pd.to_datetime(values, errors="coerce").dropna()
            parsed_entry_rows = int(len(parsed))
            if len(parsed):
                year_min = int(parsed.dt.year.min())
                year_max = int(parsed.dt.year.max())
        except Exception:
            pass

    lower_name = path.name.lower()
    exact_name = lower_name in {name.lower() for name in EXACT_NAMES}
    score = 0
    score += 1000 if exact_name else 0
    score += 180 if "stage286" in lower_name else 0
    score += 140 if "stage284" in lower_name else 0
    score += 90 if "portfolio" in lower_name else 0
    score += 80 if "trade" in lower_name else 0
    score += 50 if any(token in lower_name for token in ("selected", "safe", "balanced")) else 0
    score += 40 if source else 0
    score += 25 if priority else 0
    score += 25 if candidate_id else 0
    score += 40 if row_count in (573, 542, 544, 575) else 0
    score += 35 if year_min is not None and year_min <= 2024 and year_max is not None and year_max >= 2026 else 0
    score -= 500 if not compatible else 0

    if compatible:
        classification = "TRADE_LEVEL_COMPATIBLE"
        reason = "entry, exit, and realized PnL contract are available"
    elif entry is None and exit_column is None:
        classification = "SUMMARY_ONLY"
        reason = "no per-trade entry/exit timestamps"
    else:
        classification = "INCOMPLETE_TRADE_LEDGER"
        reason = "entry/exit or realized PnL contract is incomplete"

    record.update(
        {
            "encoding": encoding,
            "columns": columns,
            "row_count": row_count,
            "entry_column": entry,
            "exit_column": exit_column,
            "pnl_column": pnl,
            "entry_price_column": entry_price,
            "exit_price_column": exit_price,
            "direction_column": direction,
            "source_column": source,
            "priority_column": priority,
            "candidate_id_column": candidate_id,
            "parsed_entry_rows": parsed_entry_rows,
            "year_min": year_min,
            "year_max": year_max,
            "exact_expected_name": exact_name,
            "compatible_trade_ledger": compatible,
            "classification": classification,
            "reason": reason,
            "score": score,
        }
    )
    return record


def choose_candidate(records: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    compatible = [record for record in records if record["compatible_trade_ledger"]]
    compatible.sort(key=lambda record: (-int(record["score"]), str(record["path"]).lower()))
    if not compatible:
        return None, "no compatible trade-level portfolio CSV was found"
    exact = [record for record in compatible if record["exact_expected_name"]]
    if len(exact) == 1:
        return exact[0], "single compatible exact-name match"
    if len(exact) > 1:
        exact.sort(key=lambda record: (-int(record["score"]), str(record["path"]).lower()))
        if exact[0]["score"] > exact[1]["score"]:
            return exact[0], "highest-scoring exact-name match"
        return None, "multiple equally plausible exact-name trade ledgers"
    if len(compatible) == 1:
        return compatible[0], "single compatible trade ledger"
    if compatible[0]["score"] >= 350 and compatible[0]["score"] - compatible[1]["score"] >= 50:
        return compatible[0], "unique high-confidence structural match"
    return None, "multiple compatible trade ledgers require an explicit path"


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else candle_dir / "stage310a_existing_portfolio_locator.json"
    )
    copy_to = (
        Path(args.copy_to).expanduser().resolve()
        if args.copy_to
        else candle_dir / "stage310_existing_portfolio_trades_input.csv"
    )
    explicit = Path(args.explicit).expanduser().resolve() if args.explicit else None

    roots = search_roots(candle_dir)
    paths = candidate_paths(roots, explicit)
    records = [inspect_candidate(path) for path in paths]
    records.sort(key=lambda record: (-int(record["score"]), str(record["path"]).lower()))
    selected, selection_reason = choose_candidate(records)

    if selected is not None:
        source_path = Path(selected["path"])
        copy_to.parent.mkdir(parents=True, exist_ok=True)
        if source_path.resolve() != copy_to.resolve():
            shutil.copy2(source_path, copy_to)
        status = "GOLD_V3_310A_EXISTING_PORTFOLIO_TRADE_LEDGER_READY"
        decision = "RUN_STAGE310_WITH_LOCATED_LEDGER"
        exit_code = 0
        copied_sha = sha256_file(copy_to)
    else:
        status = "GOLD_V3_310A_BLOCKED_EXISTING_PORTFOLIO_TRADE_LEDGER_NOT_FOUND"
        decision = "LOCATE_OR_REGENERATE_ORIGINAL_TRADE_LEVEL_LEDGER"
        exit_code = 2
        copied_sha = None

    report = {
        "status": status,
        "mode": "AUDIT_ONLY_EXISTING_PORTFOLIO_LOCATOR",
        "decision": decision,
        "searched_roots": [str(root) for root in roots],
        "absolute_exclusions": list(BANNED_PATH_TOKENS),
        "exact_names": list(EXACT_NAMES),
        "patterns": list(PATTERNS),
        "explicit_path": str(explicit) if explicit else None,
        "candidate_file_count": len(records),
        "compatible_file_count": sum(bool(record["compatible_trade_ledger"]) for record in records),
        "selection_reason": selection_reason,
        "selected": selected,
        "copied_input": {
            "path": str(copy_to) if selected is not None else None,
            "sha256": copied_sha,
        },
        "inspected_candidates": records[:200],
        "important": "Summary-only files are intentionally rejected because overlap replay requires per-trade entry_dt, exit_dt, and realized PnL.",
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
