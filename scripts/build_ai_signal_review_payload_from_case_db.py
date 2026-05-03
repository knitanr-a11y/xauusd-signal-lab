from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_ai_signal_review_payload import (  # noqa: E402
    CURRENT_SIGNAL_COLUMNS,
    FUTURE_LABEL_COLUMNS,
    HISTORICAL_CASE_COLUMNS,
    build_prompt_text,
    prepare_cases,
    row_to_dict,
    select_similar_cases,
    to_jsonable,
)

DEFAULT_CASE_DB = PROJECT_ROOT / "data" / "results" / "ai_cases" / "xm_kiwami_gold_abc_v3_all_ai_cases_enriched.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "case_db_payloads"

# Historical labels are allowed only inside similar_*_cases.
HISTORICAL_LABEL_COLUMNS = [
    "case_type",
    "case_reason",
    "result",
    "r",
    "exit_reason",
    "bars_held",
]

# Columns that identify where the row came from. These are useful for auditing self-case leakage.
ROW_ID_COLUMNS = [
    "source_row",
    "ai_case_db_row",
    "source_trade_row",
]


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def finite_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def row_label_summary(row: pd.Series) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col in HISTORICAL_LABEL_COLUMNS:
        if col in row.index:
            out[col] = to_jsonable(row[col])
    return out


def row_identity_summary(row: pd.Series) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col in ROW_ID_COLUMNS:
        if col in row.index:
            out[col] = to_jsonable(row[col])
    return out


def historical_case_to_dict(row: pd.Series) -> dict[str, Any]:
    """Build one historical case for the payload.

    Labels are intentionally included here because this row is historical evidence.
    The same labels must never appear in current_signal_snapshot.
    """
    case = row_to_dict(row, HISTORICAL_CASE_COLUMNS)

    # Keep explicit row identifiers even when older/newer case DBs differ in naming.
    for key, value in row_identity_summary(row).items():
        case[key] = value

    if "similarity_score" in row.index:
        case["similarity_score"] = finite_float(row["similarity_score"])

    return case


def assert_current_signal_has_no_future_labels(current_signal: dict[str, Any]) -> None:
    leaked = sorted([col for col in FUTURE_LABEL_COLUMNS if col in current_signal])
    if leaked:
        raise RuntimeError(f"current_signal_snapshot leaked future/label columns: {leaked}")


def assert_no_self_case_leakage(
    *,
    payload: dict[str, Any],
    current_index: int,
    current_row: pd.Series,
) -> None:
    current_source_row = int(current_row.get("source_row", current_index))
    current_ai_case_db_row = current_row.get("ai_case_db_row")
    current_source_trade_row = current_row.get("source_trade_row")

    leaks: list[str] = []
    for bucket_name in ["similar_winning_cases", "similar_losing_cases"]:
        for case in payload.get(bucket_name, []):
            if case.get("source_row") == current_source_row:
                leaks.append(f"{bucket_name}: source_row={current_source_row}")
            if current_ai_case_db_row is not None and not pd.isna(current_ai_case_db_row):
                if case.get("ai_case_db_row") == to_jsonable(current_ai_case_db_row):
                    leaks.append(f"{bucket_name}: ai_case_db_row={to_jsonable(current_ai_case_db_row)}")
            if current_source_trade_row is not None and not pd.isna(current_source_trade_row):
                if case.get("source_trade_row") == to_jsonable(current_source_trade_row):
                    leaks.append(f"{bucket_name}: source_trade_row={to_jsonable(current_source_trade_row)}")

    if leaks:
        raise RuntimeError("current row leaked into historical comparison cases: " + ", ".join(leaks))


def build_payload_from_case_db(
    *,
    cases: pd.DataFrame,
    current_index: int,
    win_limit: int,
    loss_limit: int,
) -> dict[str, Any]:
    if current_index < 0 or current_index >= len(cases):
        raise IndexError(f"current-index out of range: {current_index}. rows={len(cases)}")

    current = cases.iloc[current_index]

    similar_wins = select_similar_cases(
        cases,
        current,
        "win_pattern",
        win_limit,
        current_index=current_index,
    )
    similar_losses = select_similar_cases(
        cases,
        current,
        "loss_pattern",
        loss_limit,
        current_index=current_index,
    )

    current_signal = row_to_dict(current, CURRENT_SIGNAL_COLUMNS)
    assert_current_signal_has_no_future_labels(current_signal)

    payload: dict[str, Any] = {
        "metadata": {
            "project": "xauusd-signal-lab",
            "broker_profile": "XM KIWAMI",
            "symbol": "GOLD# / goldsharp",
            "preset": "xm_kiwami_gold_abc_v3",
            "mode": "case_db_similarity_review_payload",
            "case_db_rows": int(len(cases)),
            "current_case_source_row": int(current.get("source_row", current_index)),
            "current_case_db_row": to_jsonable(current.get("ai_case_db_row")) if "ai_case_db_row" in current.index else None,
            "current_source_trade_row": to_jsonable(current.get("source_trade_row")) if "source_trade_row" in current.index else None,
            "warning": "This payload is for AI risk review only. It is not a final trade execution decision.",
        },
        "ai_task": build_prompt_text(),
        "current_signal_snapshot": current_signal,
        "similar_winning_cases": [historical_case_to_dict(row) for _, row in similar_wins.iterrows()],
        "similar_losing_cases": [historical_case_to_dict(row) for _, row in similar_losses.iterrows()],
        "current_row_label_audit_not_sent_as_features": row_label_summary(current),
        "retrieval_config": {
            "win_limit": int(win_limit),
            "loss_limit": int(loss_limit),
            "primary_filter": "same combined_signal_source and same side when enough cases exist",
            "fallback_filter": "same combined_signal_source OR same side when primary filter is too small",
            "current_row_excluded": True,
            "similarity_direction": "lower similarity_score is closer",
        },
        "guardrails": {
            "do_not_send_full_case_db_to_ai": True,
            "use_python_similarity_search_before_ai": True,
            "current_signal_snapshot_contains_pre_entry_features_only": True,
            "historical_cases_may_include_result_r_exit_reason_bars_held_as_labels": True,
            "exclude_current_row_from_historical_cases": True,
            "do_not_use_historical_labels_as_current_features": True,
            "respect_rule_based_signal_expectancy": True,
            "caution_does_not_mean_skip": True,
            "skip_candidate_requires_multiple_strong_reasons": True,
            "output_json_only": True,
        },
    }

    assert_no_self_case_leakage(payload=payload, current_index=current_index, current_row=current)
    return payload


def write_outputs(
    *,
    payload: dict[str, Any],
    out_dir: Path,
    current_index: int,
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / f"ai_signal_review_payload_from_case_db_row_{current_index}.json"
    out_prompt = out_dir / f"ai_signal_review_prompt_from_case_db_row_{current_index}.txt"

    out_json.write_text(json_dumps(payload), encoding="utf-8")
    out_prompt.write_text(
        payload["ai_task"]
        + "\n\nPAYLOAD_JSON:\n"
        + json_dumps(payload),
        encoding="utf-8",
    )
    return out_json, out_prompt


def print_summary(*, cases: pd.DataFrame, payload: dict[str, Any], current_index: int, out_json: Path, out_prompt: Path) -> None:
    current = payload["current_signal_snapshot"]
    audit = payload["current_row_label_audit_not_sent_as_features"]

    print("Case DB rows:", len(cases))
    print("Current index:", current_index)
    print("Current source/side/time:", current.get("combined_signal_source"), current.get("side"), current.get("jst_entry_time"))
    print("Current row label audit, not sent as current features:", audit)
    print("Similar winning cases:", len(payload["similar_winning_cases"]))
    print("Similar losing cases:", len(payload["similar_losing_cases"]))
    print("Current self-case leakage check: OK")
    print("Current future-label leakage check: OK")
    print("Saved JSON:", out_json)
    print("Saved prompt:", out_prompt)

    def preview(bucket_name: str) -> None:
        print(f"\n{bucket_name} preview:")
        rows = payload.get(bucket_name, [])
        if not rows:
            print("  none")
            return
        for case in rows[:10]:
            print(
                "  "
                f"score={case.get('similarity_score')} "
                f"row={case.get('source_row')} "
                f"case_db_row={case.get('ai_case_db_row')} "
                f"source={case.get('combined_signal_source')} "
                f"side={case.get('side')} "
                f"result={case.get('result')} "
                f"r={case.get('r')} "
                f"hour={case.get('jst_entry_hour')} "
                f"time={case.get('jst_entry_time')}"
            )

    preview("similar_winning_cases")
    preview("similar_losing_cases")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build one AI review payload by searching similar cases from the full local AI case DB."
    )
    parser.add_argument("--case-db", type=Path, default=DEFAULT_CASE_DB)
    parser.add_argument("--current-index", type=int, required=True, help="Row index in the case DB to treat as the current signal sample.")
    parser.add_argument("--win-limit", type=int, default=8, help="Number of similar historical winning cases to include.")
    parser.add_argument("--loss-limit", type=int, default=8, help="Number of similar historical losing cases to include.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    case_db = resolve_path(args.case_db)
    out_dir = resolve_path(args.out_dir)

    cases = prepare_cases(case_db)
    payload = build_payload_from_case_db(
        cases=cases,
        current_index=args.current_index,
        win_limit=args.win_limit,
        loss_limit=args.loss_limit,
    )
    out_json, out_prompt = write_outputs(payload=payload, out_dir=out_dir, current_index=args.current_index)
    print_summary(cases=cases, payload=payload, current_index=args.current_index, out_json=out_json, out_prompt=out_prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
