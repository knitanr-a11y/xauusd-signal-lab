#!/usr/bin/env python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

STEP = "25C72_A002_REVIEW"
IN_DIR = "gold_v2_25c71_a002_fixed_scope_outcome_disambiguation_audit_only"
OUT_DIR = "gold_v2_25c72_a002_review"


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
    with open(inp / "02_25c71_outcome_disambiguation_summary.json", encoding="utf-8-sig") as f:
        s71 = json.load(f)
    rows = read_csv(inp / "07_25c71_collapsed_outcome_rows.csv")
    rr = pd.to_numeric(rows["rr"], errors="coerce")
    checks = pd.DataFrame([
        {"check": "input_step", "observed": s71.get("step"), "expected": "25C71_A002_FIXED_SCOPE_OUTCOME_DISAMBIGUATION_AUDIT_ONLY", "status": "PASS" if s71.get("step") == "25C71_A002_FIXED_SCOPE_OUTCOME_DISAMBIGUATION_AUDIT_ONLY" else "STOP"},
        {"check": "rows", "observed": len(rows), "expected": 772, "status": "PASS" if len(rows) == 772 else "STOP"},
        {"check": "rr_sum", "observed": float(rr.sum()), "expected": 965.0, "status": "PASS" if abs(float(rr.sum()) - 965.0) < 1e-9 else "STOP"},
        {"check": "rr_mean", "observed": float(rr.mean()), "expected": 1.25, "status": "PASS" if abs(float(rr.mean()) - 1.25) < 1e-9 else "STOP"},
        {"check": "positive", "observed": int((rr > 0).sum()), "expected": 772, "status": "PASS" if int((rr > 0).sum()) == 772 else "STOP"},
        {"check": "one_rr_value", "observed": int(rr.nunique()), "expected": 1, "status": "PASS" if int(rr.nunique()) == 1 else "STOP"},
        {"check": "one_direction", "observed": int(rows["direction"].nunique()), "expected": 1, "status": "PASS" if int(rows["direction"].nunique()) == 1 else "STOP"},
    ])
    risk = pd.DataFrame([
        {"item": "uniform_rr", "observed": "772 rows have rr=1.25", "status": "REVIEW_REQUIRED"},
        {"item": "uniform_direction", "observed": "772 rows have the same direction", "status": "REVIEW_REQUIRED"},
        {"item": "scope", "observed": "A002 fixed subset only", "status": "REVIEW_REQUIRED"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "25C73_A002_SOURCE_CONTEXT_REVIEW", "allowed_now": True},
        {"rank": 2, "next_step": "other_use", "allowed_now": False},
    ])
    stop_rows = int((checks["status"] == "STOP").sum())
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": "A002_REVIEW_READY" if stop_rows == 0 else "A002_REVIEW_STOP",
        "events": int(len(rows)),
        "rr_sum": float(rr.sum()),
        "rr_mean": float(rr.mean()),
        "win_rate_rr_gt_0": float((rr > 0).mean()),
        "uniform_rr": True,
        "uniform_direction": True,
        "context_review_required": True,
        "ready_for_other_use": False,
        "next_recommended_step": "25C73_A002_SOURCE_CONTEXT_REVIEW",
        "total_stop_rows": stop_rows,
    }
    write_csv(out / "03_25c72_checks.csv", checks)
    write_csv(out / "04_25c72_interpretation_risk.csv", risk)
    write_csv(out / "05_25c72_next_step_plan.csv", next_plan)
    with open(out / "02_25c72_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    report = "# GOLD V2 25C72 A002 review\n\n" + json.dumps(summary, ensure_ascii=False, indent=2)
    (out / "01_25c72_GOLD_V2_A002_REVIEW.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if stop_rows == 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())
