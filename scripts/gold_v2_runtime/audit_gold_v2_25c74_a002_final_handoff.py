#!/usr/bin/env python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

STEP = "25C74_A002_FINAL_HANDOFF"
IN_DIR = "gold_v2_25c73_a002_source_context_review"
OUT_DIR = "gold_v2_25c74_a002_final_handoff"


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
    inp = base / IN_DIR
    out = base / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    with open(inp / "02_25c73_summary.json", encoding="utf-8-sig") as f:
        s73 = json.load(f)
    checks73 = read_csv(inp / "03_25c73_checks.csv")
    metrics = read_csv(inp / "04_25c73_context_metrics.csv")
    findings = read_csv(inp / "09_25c73_findings.csv")
    stop_rows = int((checks73.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum())

    final_status = pd.DataFrame([
        {"item": "A002 fixed scope", "status": "REVIEWED", "detail": "772 events"},
        {"item": "row mapping", "status": "REVIEWED", "detail": "duplicates collapsed only after identical value check"},
        {"item": "numeric rr summary", "status": "RECORDED", "detail": "rr_sum=965; rr_mean=1.25"},
        {"item": "source context", "status": "RECORDED", "detail": "source and matched rows are uniform rr/direction"},
        {"item": "result interpretation", "status": "LIMITED", "detail": "rr is source-context value, not standalone live readiness"},
        {"item": "other use", "status": "BLOCKED", "detail": "requires separate human decision"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "HUMAN_DECISION_A002_CONTEXT_ACCEPTANCE_OR_RESULT_SOURCE_REQUEST", "allowed_now": True},
        {"rank": 2, "next_step": "COREB_FULL_OR_LIVE_USE", "allowed_now": False},
    ])
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": "A002_FINAL_HANDOFF_READY" if stop_rows == 0 else "A002_FINAL_HANDOFF_STOP",
        "input_25c73_status": s73.get("status"),
        "source_rows": s73.get("source_rows"),
        "matched_source_rows": s73.get("matched_source_rows"),
        "matched_unique_entry_times": s73.get("matched_unique_entry_times"),
        "matched_rr_unique": s73.get("matched_rr_unique"),
        "matched_direction_unique": s73.get("matched_direction_unique"),
        "a002_events": 772,
        "rr_sum_recorded": 965.0,
        "rr_mean_recorded": 1.25,
        "context_review_complete": s73.get("context_review_complete"),
        "result_interpretation_limited": True,
        "ready_for_other_use": False,
        "next_recommended_step": "HUMAN_DECISION_A002_CONTEXT_ACCEPTANCE_OR_RESULT_SOURCE_REQUEST",
        "total_stop_rows": stop_rows,
    }
    write_csv(out / "03_25c74_final_status_matrix.csv", final_status)
    write_csv(out / "04_25c74_context_metrics_carry_forward.csv", metrics)
    write_csv(out / "05_25c74_findings_carry_forward.csv", findings)
    write_csv(out / "06_25c74_next_step_plan.csv", next_plan)
    with open(out / "02_25c74_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    report = "# GOLD V2 25C74 A002 final handoff\n\n" + json.dumps(summary, ensure_ascii=False, indent=2)
    (out / "01_25c74_GOLD_V2_A002_FINAL_HANDOFF.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if stop_rows == 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())
