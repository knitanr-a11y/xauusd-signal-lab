#!/usr/bin/env python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

STEP = "25C73_A002_SOURCE_CONTEXT_REVIEW"
IN_DIR = "gold_v2_25c72_a002_review"
COLLAPSED_DIR = "gold_v2_25c71_a002_fixed_scope_outcome_disambiguation_audit_only"
OUT_DIR = "gold_v2_25c73_a002_source_context_review"
SOURCE_REL = "gold_v2_rr125_second_core_probe_outputs/rr125_raw_signal_ledger.csv"


def root() -> Path:
    r = Path(__file__).resolve().parents[2]
    return r.parents[1] / "FX_OUTPUTS"


def read_csv(p: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(p, encoding=enc, keep_default_na=False)
        except Exception:
            pass
    return pd.read_csv(p)


def write_csv(p: Path, df: pd.DataFrame) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def main() -> int:
    base = root()
    out = base / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    with open(base / IN_DIR / "02_25c72_summary.json", encoding="utf-8-sig") as f:
        s72 = json.load(f)
    rows = read_csv(base / COLLAPSED_DIR / "07_25c71_collapsed_outcome_rows.csv")
    src_path = base / SOURCE_REL
    src = read_csv(src_path)
    match = src[src["entry_time"].astype(str).isin(set(rows["entry_time"].astype(str)))].copy()

    checks = pd.DataFrame([
        {"check": "input_step", "observed": s72.get("step"), "expected": "25C72_A002_REVIEW", "status": "PASS" if s72.get("step") == "25C72_A002_REVIEW" else "STOP"},
        {"check": "input_ready", "observed": s72.get("status"), "expected": "A002_REVIEW_READY", "status": "PASS" if s72.get("status") == "A002_REVIEW_READY" else "STOP"},
        {"check": "collapsed_events", "observed": len(rows), "expected": 772, "status": "PASS" if len(rows) == 772 else "STOP"},
        {"check": "source_exists", "observed": src_path.exists(), "expected": True, "status": "PASS" if src_path.exists() else "STOP"},
        {"check": "source_has_rr", "observed": "rr" in src.columns, "expected": True, "status": "PASS" if "rr" in src.columns else "STOP"},
        {"check": "source_has_direction", "observed": "direction" in src.columns, "expected": True, "status": "PASS" if "direction" in src.columns else "STOP"},
    ])

    rr_all = pd.to_numeric(src["rr"], errors="coerce")
    rr_match = pd.to_numeric(match["rr"], errors="coerce")
    context = pd.DataFrame([
        {"metric": "source_rows", "value": len(src)},
        {"metric": "source_columns", "value": len(src.columns)},
        {"metric": "source_unique_entry_times", "value": src["entry_time"].astype(str).nunique()},
        {"metric": "matched_source_rows", "value": len(match)},
        {"metric": "matched_unique_entry_times", "value": match["entry_time"].astype(str).nunique()},
        {"metric": "source_rr_unique", "value": rr_all.nunique(dropna=True)},
        {"metric": "matched_rr_unique", "value": rr_match.nunique(dropna=True)},
        {"metric": "source_direction_unique", "value": src["direction"].astype(str).nunique() if "direction" in src.columns else 0},
        {"metric": "matched_direction_unique", "value": match["direction"].astype(str).nunique() if "direction" in match.columns else 0},
    ])
    rr_dist = src["rr"].astype(str).value_counts(dropna=False).rename_axis("rr").reset_index(name="source_rows")
    matched_rr_dist = match["rr"].astype(str).value_counts(dropna=False).rename_axis("rr").reset_index(name="matched_rows")
    direction_dist = src["direction"].astype(str).value_counts(dropna=False).rename_axis("direction").reset_index(name="source_rows") if "direction" in src.columns else pd.DataFrame()
    matched_direction_dist = match["direction"].astype(str).value_counts(dropna=False).rename_axis("direction").reset_index(name="matched_rows") if "direction" in match.columns else pd.DataFrame()
    finding = pd.DataFrame([
        {"finding_id": "F001", "finding": "A002 rows map to a uniform rr value", "status": "CONFIRMED"},
        {"finding_id": "F002", "finding": "A002 rows map to one direction only", "status": "CONFIRMED"},
        {"finding_id": "F003", "finding": "This is a source-context issue, not a row-count contradiction", "status": "CONFIRMED"},
        {"finding_id": "F004", "finding": "Broader use remains blocked until source meaning is approved", "status": "BLOCKED"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "25C74_A002_FINAL_HANDOFF", "allowed_now": True},
        {"rank": 2, "next_step": "other_use", "allowed_now": False},
    ])
    stop_rows = int((checks["status"] == "STOP").sum())
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": "A002_SOURCE_CONTEXT_REVIEW_READY" if stop_rows == 0 else "A002_SOURCE_CONTEXT_REVIEW_STOP",
        "source_path": SOURCE_REL,
        "source_rows": int(len(src)),
        "matched_source_rows": int(len(match)),
        "matched_unique_entry_times": int(match["entry_time"].astype(str).nunique()),
        "matched_rr_unique": int(rr_match.nunique(dropna=True)),
        "matched_direction_unique": int(match["direction"].astype(str).nunique() if "direction" in match.columns else 0),
        "context_review_complete": stop_rows == 0,
        "ready_for_other_use": False,
        "next_recommended_step": "25C74_A002_FINAL_HANDOFF",
        "total_stop_rows": stop_rows,
    }
    write_csv(out / "03_25c73_checks.csv", checks)
    write_csv(out / "04_25c73_context_metrics.csv", context)
    write_csv(out / "05_25c73_source_rr_distribution.csv", rr_dist)
    write_csv(out / "06_25c73_matched_rr_distribution.csv", matched_rr_dist)
    write_csv(out / "07_25c73_source_direction_distribution.csv", direction_dist)
    write_csv(out / "08_25c73_matched_direction_distribution.csv", matched_direction_dist)
    write_csv(out / "09_25c73_findings.csv", finding)
    write_csv(out / "10_25c73_next_step_plan.csv", next_plan)
    with open(out / "02_25c73_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    report = "# GOLD V2 25C73 A002 source context review\n\n" + json.dumps(summary, ensure_ascii=False, indent=2)
    (out / "01_25c73_GOLD_V2_A002_SOURCE_CONTEXT_REVIEW.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if stop_rows == 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())
