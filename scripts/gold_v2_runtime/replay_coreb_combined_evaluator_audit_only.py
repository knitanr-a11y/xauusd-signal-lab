#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, operator
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEF = ROOT / "configs/gold_v2/frozen_coreB_combined_evaluator_definition_20260604.json"
READY = "FROZEN_COREB_COMBINED_EVALUATOR_DEFINITION_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED"
SNAP_REL = Path("FX_OUTPUTS/gold_v2_coreb_combined_required_feature_snapshot_audit_only/gold_v2_coreb_combined_required_feature_snapshot.csv")
SUMMARY_REL = Path("FX_OUTPUTS/gold_v2_coreb_combined_required_feature_snapshot_audit_only/gold_v2_coreb_combined_required_feature_snapshot_summary.json")
OPS = {">": operator.gt, "<": operator.lt, ">=": operator.ge, "<=": operator.le, "==": operator.eq}


def files_dir() -> Path:
    return ROOT.parents[1] if len(ROOT.parents) >= 2 else ROOT.parent


def out_dir() -> Path:
    p = files_dir() / "FX_OUTPUTS" / "gold_v2_coreb_combined_evaluator_replay_audit_only"
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def rule_mask(df: pd.DataFrame, rule: dict) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for key in ["base_condition_objects", "added_filter_condition_objects"]:
        for c in rule.get(key, []) or []:
            f = c.get("field")
            op = c.get("operator")
            val = c.get("value")
            if f not in df.columns or op not in OPS:
                return pd.Series(False, index=df.index)
            s = pd.to_numeric(df[f], errors="coerce")
            mask &= OPS[op](s, float(val)).fillna(False)
    return mask


def main() -> int:
    out = out_dir()
    created = datetime.now(timezone.utc).isoformat()
    snap = files_dir() / SNAP_REL
    snap_summary_path = files_dir() / SUMMARY_REL
    if not DEF.exists() or not snap.exists():
        summary = {"created_utc": created, "status": "COREB_COMBINED_REPLAY_INPUT_MISSING", "definition_exists": DEF.exists(), "snapshot_exists": snap.exists(), "final_signal_allowed": False, "step13_allowed": False}
        write_json(out / "gold_v2_coreb_combined_evaluator_replay_summary.json", summary)
        return 2
    definition = read_json(DEF)
    snap_summary = read_json(snap_summary_path) if snap_summary_path.exists() else {}
    if definition.get("status") != READY:
        summary = {"created_utc": created, "status": "COREB_COMBINED_DEFINITION_NOT_READY", "definition_status": definition.get("status"), "final_signal_allowed": False, "step13_allowed": False}
        write_json(out / "gold_v2_coreb_combined_evaluator_replay_summary.json", summary)
        return 2
    df = pd.read_csv(snap)
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    selected_rules = definition.get("selected_rules", []) or []
    same_rules = definition.get("same_count_source_rules", []) or []
    selected_count = np.zeros(len(df), dtype=np.int16)
    same_count = np.zeros(len(df), dtype=np.int16)
    selected_hit_ids = [[] for _ in range(len(df))]
    same_hit_ids = [[] for _ in range(len(df))]
    for r in selected_rules:
        m = rule_mask(df, r).to_numpy(dtype=bool)
        selected_count += m.astype(np.int16)
        rid = r.get("rule_id", "")
        idx = np.flatnonzero(m)
        for i in idx:
            selected_hit_ids[i].append(rid)
    for r in same_rules:
        m = rule_mask(df, r).to_numpy(dtype=bool)
        same_count += m.astype(np.int16)
        rid = r.get("rule_id", "")
        idx = np.flatnonzero(m)
        for i in idx:
            same_hit_ids[i].append(rid)
    complete = df.get("coreb_combined_required_fields_complete", pd.Series(True, index=df.index)).fillna(False).astype(bool).to_numpy()
    signal = (selected_count > 0) & (same_count >= int(definition.get("same_count_min", 15))) & complete
    rows = pd.DataFrame({
        "time": df["time"],
        "close": df.get("close", np.nan),
        "required_fields_complete": complete,
        "selected_rule_hit_count": selected_count,
        "same_count_source_hit_count": same_count,
        "coreb_combined_candidate_signal": signal,
        "selected_hit_rule_ids": ["|".join(x) for x in selected_hit_ids],
        "same_count_hit_rule_ids": ["|".join(x) for x in same_hit_ids],
    })
    rows["year_month"] = rows["time"].dt.to_period("M").astype(str)
    rows.to_csv(out / "gold_v2_coreb_combined_evaluator_replay_rows.csv", index=False, encoding="utf-8-sig")
    monthly = rows.groupby("year_month", dropna=False).agg(
        rows=("time", "size"),
        selected_hit_rows=("selected_rule_hit_count", lambda x: int((x > 0).sum())),
        same_count_pass_rows=("same_count_source_hit_count", lambda x: int((x >= int(definition.get("same_count_min", 15))).sum())),
        coreb_candidate_signal_rows=("coreb_combined_candidate_signal", "sum"),
        max_selected_rule_hit_count=("selected_rule_hit_count", "max"),
        max_same_count_source_hit_count=("same_count_source_hit_count", "max"),
    ).reset_index()
    monthly.to_csv(out / "gold_v2_coreb_combined_evaluator_replay_monthly.csv", index=False, encoding="utf-8-sig")
    examples = rows[rows["coreb_combined_candidate_signal"]].head(200).copy()
    examples.to_csv(out / "gold_v2_coreb_combined_evaluator_replay_signal_examples.csv", index=False, encoding="utf-8-sig")
    signal_count = int(signal.sum())
    status = "COREB_COMBINED_REPLAY_CANDIDATE_FORMULA_AUDIT_READY_FINAL_SIGNAL_BLOCKED"
    expected_warning = "candidate_formula_not_source_validated; do not compare as final backtest parity"
    summary = {
        "created_utc": created,
        "status": status,
        "audit_only": True,
        "definition_id": definition.get("definition_id"),
        "entry_logic": definition.get("entry_logic"),
        "formula_source_status": snap_summary.get("formula_source_status", "UNKNOWN"),
        "candidate_formula_warning": expected_warning,
        "row_count": int(len(rows)),
        "complete_row_count": int(complete.sum()),
        "selected_rule_count": int(len(selected_rules)),
        "same_count_source_rule_count": int(len(same_rules)),
        "same_count_min": int(definition.get("same_count_min", 15)),
        "selected_hit_rows": int((selected_count > 0).sum()),
        "same_count_pass_rows": int((same_count >= int(definition.get("same_count_min", 15))).sum()),
        "coreb_candidate_signal_rows": signal_count,
        "max_selected_rule_hit_count": int(selected_count.max()) if len(selected_count) else 0,
        "max_same_count_source_hit_count": int(same_count.max()) if len(same_count) else 0,
        "expected_user_backtest_coreb_2025_trades": 104,
        "expected_user_backtest_coreb_2026_trades": 21,
        "parity_status": "NOT_PROVEN_CANDIDATE_FORMULA_ONLY",
        "component_signal_allowed": False,
        "live_evaluator_connection_allowed": False,
        "final_signal_allowed": False,
        "step13_allowed": False,
        "notification_should_send": False,
        "output_dir": str(out),
    }
    write_json(out / "gold_v2_coreb_combined_evaluator_replay_summary.json", summary)
    report = ["# GOLD V2 CoreB combined evaluator replay audit-only report", ""] + [f"- {k}: `{v}`" for k, v in summary.items()]
    report += ["", "## Important", "This replay uses the 12O candidate formula feature snapshot. It is not proof of parity with exploration features and must not be connected to live/final signals."]
    (out / "GOLD_V2_COREB_COMBINED_EVALUATOR_REPLAY_AUDIT_ONLY_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
