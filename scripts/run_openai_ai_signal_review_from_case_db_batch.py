from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CASE_DB = PROJECT_ROOT / "data" / "results" / "ai_cases" / "xm_kiwami_gold_abc_v3_all_ai_cases_enriched.csv"
DEFAULT_PAYLOAD_DIR = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "case_db_payloads"
DEFAULT_LEDGER_CSV = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "ai_review_ledger.csv"
DEFAULT_SUMMARY_CSV = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "ai_review_case_db_batch_summary.csv"
DEFAULT_MODEL = "gpt-5-mini"


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def run_command(command: list[str], *, dry_run: bool) -> int:
    print("\n" + "-" * 120)
    print("COMMAND:")
    print(" ".join(command))
    print("-" * 120)
    if dry_run:
        return 0
    completed = subprocess.run(command, cwd=PROJECT_ROOT)
    return int(completed.returncode)


def parse_index_range(text: str, total_rows: int) -> list[int]:
    text = text.strip().lower()
    if text in {"all", "*"}:
        return list(range(total_rows))

    indices: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if end < start:
                raise ValueError(f"Invalid range: {part}")
            indices.extend(range(start, end + 1))
        else:
            indices.append(int(part))

    unique = sorted(set(indices))
    bad = [i for i in unique if i < 0 or i >= total_rows]
    if bad:
        raise IndexError(f"Index out of range: {bad}. total_rows={total_rows}")
    return unique


def build_payload(
    row_index: int,
    *,
    case_db: Path,
    win_limit: int,
    loss_limit: int,
    payload_dir: Path,
    dry_run: bool,
) -> int:
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "build_ai_signal_review_payload_from_case_db.py"),
        "--case-db",
        str(case_db),
        "--current-index",
        str(row_index),
        "--win-limit",
        str(win_limit),
        "--loss-limit",
        str(loss_limit),
        "--out-dir",
        str(payload_dir),
    ]
    return run_command(command, dry_run=dry_run)


def run_ai_review(
    row_index: int,
    *,
    payload_dir: Path,
    ledger_csv: Path,
    model: str,
    max_output_tokens: int,
    dry_run: bool,
) -> int:
    payload_json = payload_dir / f"ai_signal_review_payload_from_case_db_row_{row_index}.json"
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "run_openai_ai_signal_review.py"),
        "--payload-json",
        str(payload_json),
        "--model",
        model,
        "--max-output-tokens",
        str(max_output_tokens),
        "--ledger-csv",
        str(ledger_csv),
        "--save-ledger",
    ]
    return run_command(command, dry_run=dry_run)


def numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def summarize_ledger(ledger_csv: Path, out_csv: Path) -> None:
    if not ledger_csv.exists():
        print("Ledger not found, skip summary:", ledger_csv)
        return

    df = pd.read_csv(ledger_csv)
    if df.empty:
        print("Ledger is empty, skip summary:", ledger_csv)
        return

    if "actual_r" in df.columns:
        df["actual_r_num"] = numeric_series(df["actual_r"])
    else:
        df["actual_r_num"] = pd.NA

    rows: list[dict[str, object]] = []

    group_cols_sets = [
        ["final_risk_label"],
        ["winning_pattern_match", "losing_pattern_similarity", "final_risk_label"],
        ["signal_model", "side", "final_risk_label"],
    ]

    for group_cols in group_cols_sets:
        missing = [col for col in group_cols if col not in df.columns]
        if missing:
            continue

        for key, group in df.groupby(group_cols, dropna=False):
            if not isinstance(key, tuple):
                key = (key,)

            r = numeric_series(group.get("actual_r", pd.Series(dtype=object)))
            wins = r[r > 0]
            losses = r[r < 0]
            count_with_r = int(r.notna().sum())
            gross_win = float(wins.sum()) if len(wins) else 0.0
            gross_loss_abs = float(abs(losses.sum())) if len(losses) else 0.0
            pf = gross_win / gross_loss_abs if gross_loss_abs > 0 else None

            row: dict[str, object] = {
                "group_by": " x ".join(group_cols),
                "count": int(len(group)),
                "count_with_actual_r": count_with_r,
                "win_count": int((r > 0).sum()),
                "loss_count": int((r < 0).sum()),
                "win_rate": float((r > 0).sum() / count_with_r) if count_with_r else None,
                "total_r": float(r.sum()) if count_with_r else None,
                "avg_r": float(r.mean()) if count_with_r else None,
                "pf": pf,
            }
            for col, value in zip(group_cols, key):
                row[col] = value
            rows.append(row)

    if not rows:
        print("No summary rows generated.")
        return

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\nSaved case DB batch summary:", out_csv)
    print(pd.DataFrame(rows).to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch-build full case DB AI payloads, call OpenAI, save ledger rows, and summarize outcomes."
    )
    parser.add_argument("--case-db", type=Path, default=DEFAULT_CASE_DB)
    parser.add_argument("--indices", type=str, required=True, help="all, or comma/range format like 0,10,12-15")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--max-output-tokens", type=int, default=3000)
    parser.add_argument("--win-limit", type=int, default=8)
    parser.add_argument("--loss-limit", type=int, default=8)
    parser.add_argument("--payload-dir", type=Path, default=DEFAULT_PAYLOAD_DIR)
    parser.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)
    parser.add_argument("--summary-csv", type=Path, default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--sleep-seconds", type=float, default=1.0, help="Pause between API calls.")
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Print commands only. No payload/API/ledger writes.")
    args = parser.parse_args()

    case_db = resolve_path(args.case_db)
    payload_dir = resolve_path(args.payload_dir)
    ledger_csv = resolve_path(args.ledger_csv)
    summary_csv = resolve_path(args.summary_csv)

    if not case_db.exists():
        raise FileNotFoundError(case_db)

    cases = pd.read_csv(case_db)
    total_rows = len(cases)
    indices = parse_index_range(args.indices, total_rows=total_rows)

    print("Case DB:", case_db)
    print("Total rows:", total_rows)
    print("Target indices:", indices)
    print("Model:", args.model)
    print("Win/loss limits:", args.win_limit, args.loss_limit)
    print("Ledger CSV:", ledger_csv)
    print("Summary CSV:", summary_csv)
    print("Dry run:", args.dry_run)

    ok_count = 0
    fail_count = 0
    failures: list[tuple[int, str]] = []

    for n, row_index in enumerate(indices, start=1):
        print("\n" + "=" * 120)
        print(f"CASE DB BATCH {n}/{len(indices)} row={row_index}")
        print("=" * 120)

        rc = build_payload(
            row_index,
            case_db=case_db,
            win_limit=args.win_limit,
            loss_limit=args.loss_limit,
            payload_dir=payload_dir,
            dry_run=args.dry_run,
        )
        if rc != 0:
            fail_count += 1
            failures.append((row_index, f"payload rc={rc}"))
            if args.stop_on_error:
                break
            continue

        rc = run_ai_review(
            row_index,
            payload_dir=payload_dir,
            ledger_csv=ledger_csv,
            model=args.model,
            max_output_tokens=args.max_output_tokens,
            dry_run=args.dry_run,
        )
        if rc != 0:
            fail_count += 1
            failures.append((row_index, f"review rc={rc}"))
            if args.stop_on_error:
                break
            continue

        ok_count += 1
        if args.sleep_seconds > 0 and not args.dry_run:
            time.sleep(args.sleep_seconds)

    print("\n" + "=" * 120)
    print("CASE DB BATCH FINISHED")
    print("=" * 120)
    print("success:", ok_count)
    print("failed :", fail_count)
    if failures:
        print("Failures:")
        for row_index, reason in failures:
            print(f"  row={row_index}: {reason}")

    if not args.dry_run:
        summarize_ledger(ledger_csv, summary_csv)

    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
