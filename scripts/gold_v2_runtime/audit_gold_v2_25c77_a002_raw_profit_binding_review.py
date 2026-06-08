#!/usr/bin/env python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

STEP = "25C77_A002_RAW_PROFIT_BINDING_REVIEW"
LEDGER_DIR = "gold_v2_25c66_a002_fixed_scope_dry_run_execution_audit_only"
OUT_DIR = "gold_v2_25c77_a002_raw_profit_binding_review"
RAW_NAME = "rr125_raw_signal_ledger.csv"
TOP_NAME = "rr125_top_ledgers.csv"


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


def locate(base: Path, name: str) -> Path | None:
    hits = sorted(base.rglob(name))
    return hits[0] if hits else None


def nunique_str(s: pd.Series) -> int:
    return s.astype(str).nunique(dropna=False)


def main() -> int:
    base = root()
    out = base / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    ledger_path = base / LEDGER_DIR / "05_25c66_dry_run_event_ledger.csv"
    raw_path = locate(base, RAW_NAME)
    top_path = locate(base, TOP_NAME)
    checks = pd.DataFrame([
        {"check": "a002_ledger_exists", "observed": ledger_path.exists(), "expected": True, "status": "PASS" if ledger_path.exists() else "STOP"},
        {"check": "raw_exists", "observed": raw_path is not None, "expected": True, "status": "PASS" if raw_path else "STOP"},
        {"check": "top_exists", "observed": top_path is not None, "expected": True, "status": "PASS" if top_path else "WARN"},
    ])
    if checks["status"].eq("STOP").any():
        write_csv(out / "03_25c77_input_checks.csv", checks)
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": "A002_RAW_BINDING_STOP_MISSING_INPUT", "total_stop_rows": int(checks["status"].eq("STOP").sum())}
        (out / "01_25c77_A002_RAW_PROFIT_BINDING_REVIEW.md").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        with open(out / "02_25c77_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    ledger = read_csv(ledger_path)
    raw = read_csv(raw_path)  # type: ignore[arg-type]
    for df in (ledger, raw):
        for c in ["entry_time", "dataset", "policy"]:
            if c in df.columns:
                df[c] = df[c].astype(str)
    join_cols = [c for c in ["entry_time", "dataset", "policy"] if c in ledger.columns and c in raw.columns]
    joined = ledger[["a002_fixed_scope_event_id"] + join_cols].merge(raw, on=join_cols, how="left", indicator=True)
    grouped = joined.groupby("a002_fixed_scope_event_id", dropna=False)
    per_event = grouped.agg(
        raw_rows=("_merge", "size"),
        raw_match_rows=("_merge", lambda s: int((s == "both").sum())),
        unique_profit_r=("profit_r", nunique_str),
        unique_exit_time=("exit_time", nunique_str),
        unique_candidate_id=("candidate_id", nunique_str),
        unique_origin_id=("origin_id", nunique_str),
        unique_variant=("variant", nunique_str),
        unique_base_condition=("base_condition", nunique_str),
        unique_added_filter_text=("added_filter_text", nunique_str),
        unique_direction=("direction", nunique_str),
    ).reset_index()
    per_event["profit_only_unique"] = per_event["unique_profit_r"].eq(1)
    per_event["profit_exit_unique"] = per_event["unique_profit_r"].eq(1) & per_event["unique_exit_time"].eq(1)
    per_event["raw_profit_bind_status"] = per_event["profit_exit_unique"].map({True: "BINDABLE_BY_CURRENT_KEYS", False: "AMBIGUOUS_BY_CURRENT_KEYS"})
    dist = per_event.groupby("raw_rows", dropna=False).agg(events=("a002_fixed_scope_event_id", "size")).reset_index()
    ambiguity = pd.DataFrame([
        {"metric": "a002_events", "value": len(per_event)},
        {"metric": "joined_raw_rows", "value": len(joined)},
        {"metric": "events_with_raw_match", "value": int((per_event["raw_match_rows"] > 0).sum())},
        {"metric": "events_profit_only_unique", "value": int(per_event["profit_only_unique"].sum())},
        {"metric": "events_profit_exit_unique", "value": int(per_event["profit_exit_unique"].sum())},
        {"metric": "events_ambiguous", "value": int((~per_event["profit_exit_unique"]).sum())},
    ])
    safe = per_event[per_event["profit_exit_unique"]].copy()
    ambiguous = per_event[~per_event["profit_exit_unique"]].copy()
    top_review = pd.DataFrame()
    if top_path:
        top = read_csv(top_path)
        for c in ["entry_time", "dataset", "policy"]:
            if c in top.columns:
                top[c] = top[c].astype(str)
        top_join_cols = [c for c in ["entry_time", "dataset", "policy"] if c in ledger.columns and c in top.columns]
        tj = ledger[["a002_fixed_scope_event_id"] + top_join_cols].merge(top, on=top_join_cols, how="left", indicator=True)
        tg = tj.groupby("a002_fixed_scope_event_id", dropna=False).agg(top_rows=("_merge", "size"), top_match_rows=("_merge", lambda s: int((s == "both").sum())), unique_top_profit=("profit", nunique_str), unique_cluster=("cluster_id", nunique_str)).reset_index()
        top_review = pd.DataFrame([
            {"metric": "events_with_top_match", "value": int((tg["top_match_rows"] > 0).sum())},
            {"metric": "top_join_rows", "value": int(len(tj))},
            {"metric": "max_top_rows_per_event", "value": int(tg["top_match_rows"].max())},
        ])
    decision = pd.DataFrame([
        {"decision": "raw_profit_r_as_a002_result", "status": "BLOCKED", "reason": "profit_r/exit_time is not unique for all 772 events under audited keys"},
        {"decision": "safe_bindable_subset", "status": "PARTIAL_ONLY", "reason": "only events with unique profit_r and exit_time may be inspected as subset"},
        {"decision": "needed_key_columns", "status": "REQUIRED", "reason": "A002 ledger lacks candidate_id/origin_id/variant/base_condition/added_filter_text"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "REQUEST_A002_LEDGER_WITH_RAW_IDENTITY_COLUMNS", "allowed_now": True},
        {"rank": 2, "next_step": "USE_RAW_PROFIT_FOR_ALL_772", "allowed_now": False},
    ])
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": "A002_RAW_PROFIT_BINDING_BLOCKED_AMBIGUOUS_KEYS",
        "a002_events": int(len(per_event)),
        "raw_path": str(raw_path.relative_to(base)) if raw_path else "",
        "join_columns": join_cols,
        "joined_raw_rows": int(len(joined)),
        "events_with_raw_match": int((per_event["raw_match_rows"] > 0).sum()),
        "events_profit_only_unique": int(per_event["profit_only_unique"].sum()),
        "events_profit_exit_unique": int(per_event["profit_exit_unique"].sum()),
        "events_ambiguous": int((~per_event["profit_exit_unique"]).sum()),
        "raw_profit_binding_allowed": False,
        "next_recommended_step": "REQUEST_A002_LEDGER_WITH_RAW_IDENTITY_COLUMNS",
        "total_stop_rows": 0,
    }
    write_csv(out / "03_25c77_input_checks.csv", checks)
    write_csv(out / "04_25c77_raw_join_event_review.csv", per_event)
    write_csv(out / "05_25c77_raw_rows_per_event_distribution.csv", dist)
    write_csv(out / "06_25c77_ambiguity_summary.csv", ambiguity)
    write_csv(out / "07_25c77_bindable_subset_events.csv", safe)
    write_csv(out / "08_25c77_ambiguous_events.csv", ambiguous)
    write_csv(out / "09_25c77_top_ledger_review.csv", top_review)
    write_csv(out / "10_25c77_decision_matrix.csv", decision)
    write_csv(out / "11_25c77_next_step_plan.csv", next_plan)
    with open(out / "02_25c77_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    (out / "01_25c77_A002_RAW_PROFIT_BINDING_REVIEW.md").write_text("# GOLD V2 25C77 A002 raw profit binding review\n\n" + json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
