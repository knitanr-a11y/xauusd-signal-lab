#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C96_PROFIT_CLASS_MISMATCH_DIAGNOSTIC_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c96_profit_class_mismatch_diagnostic_audit_only"
INPUTS = [
    "25c95_summary.json",
    "25c95_transform_rows.csv",
    "25c95_transform_summary.csv",
    "25c95_decision_matrix.csv",
    "25c95_blocker_matrix.csv",
    "25c94_summary.json",
    "25c94_profit_binding_rows.csv",
]
EXPECTED_25C95_STATUS = "PROFIT_TRANSFORM_BINDING_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_TRANSFORM_ROWS = 42750
EXPECTED_TRANSFORM_SUMMARY_ROWS = 342
EXPECTED_25C94_BINDING_ROWS = 5250
EXPECTED_TOP_ROWS = 125
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}


def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def files_root() -> Path:
    r = repo_root(); return r.parents[1] if len(r.parents) >= 2 else r.parent
def fx_outputs() -> Path: return files_root() / "FX_OUTPUTS"
def out_dir() -> Path:
    p = fx_outputs() / OUT_NAME; p.mkdir(parents=True, exist_ok=True); return p


def find_file(name: str) -> Path | None:
    for c in [repo_root() / name, fx_outputs() / name]:
        if c.exists(): return c
    for base in [fx_outputs(), repo_root()]:
        if base.exists():
            found = sorted(base.rglob(name))
            if found: return found[0]
    return None


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""): h.update(b)
    return h.hexdigest()


def clean(x: Any) -> Any:
    if isinstance(x, dict): return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, list): return [clean(v) for v in x]
    if isinstance(x, float):
        if math.isnan(x): return None
        if math.isinf(x): return "inf" if x > 0 else "-inf"
    try:
        if pd.isna(x): return None
    except Exception: pass
    return x.isoformat() if hasattr(x, "isoformat") else x


def write_json(p: Path, obj: dict[str, Any]) -> None:
    p.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def read_json(p: Path | None) -> dict[str, Any]:
    if not p or not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}


def read_csv(p: Path | None) -> pd.DataFrame:
    return pd.read_csv(p) if p and p.exists() else pd.DataFrame()


def inventory(paths: dict[str, Path | None]) -> pd.DataFrame:
    rows = []
    for n, p in paths.items():
        r = {"filename": n, "exists": bool(p and p.exists()), "path": str(p) if p else ""}
        if p and p.exists():
            r["bytes"] = p.stat().st_size; r["sha256"] = sha256_file(p)
            if p.suffix.lower() == ".csv":
                r["row_count"] = len(pd.read_csv(p)); r["columns"] = ";".join(pd.read_csv(p, nrows=0).columns)
        rows.append(r)
    return pd.DataFrame(rows)


def class_profit(v: Any) -> str:
    try:
        f = float(v)
    except Exception:
        return "NA"
    if math.isnan(f): return "NA"
    return f"{round(f, 6):.6f}"


def ratio_value(top: Any, selected: Any) -> float | None:
    try:
        t, s = float(top), float(selected)
        if math.isnan(t) or math.isnan(s) or abs(s) <= 1e-12: return None
        return t / s
    except Exception:
        return None


def md(df: pd.DataFrame, n: int = 40) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    created = datetime.now(timezone.utc).isoformat(); out = out_dir(); paths = {n: find_file(n) for n in INPUTS}
    inv = inventory(paths)
    s95 = read_json(paths["25c95_summary.json"])
    rows = read_csv(paths["25c95_transform_rows.csv"])
    tsum = read_csv(paths["25c95_transform_summary.csv"])
    b94 = read_csv(paths["25c94_profit_binding_rows.csv"])

    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    upstream_ok = s95.get("status") == EXPECTED_25C95_STATUS
    rows_ok = len(rows) == EXPECTED_TRANSFORM_ROWS
    tsum_ok = len(tsum) == EXPECTED_TRANSFORM_SUMMARY_ROWS
    b94_ok = len(b94) == EXPECTED_25C94_BINDING_ROWS

    work = rows.copy()
    if not work.empty:
        work["top_profit_class"] = work["top_profit"].apply(class_profit)
        work["selected_profit_class"] = work["selected_profit"].apply(class_profit)
        work["ratio"] = work.apply(lambda r: ratio_value(r.get("top_profit"), r.get("selected_profit")), axis=1)
        work["ratio_class"] = work["ratio"].apply(lambda x: "NA" if x is None or pd.isna(x) else f"{round(float(x), 6):.6f}")

    if work.empty:
        top_dist = pd.DataFrame(); best_by_top = pd.DataFrame(); focus = pd.DataFrame(); ratios = pd.DataFrame(); mismatch = pd.DataFrame()
    else:
        top_dist = work.drop_duplicates(["top_row_index", "top_profit_class"]).groupby("top_profit_class", dropna=False).agg(top_rows=("top_row_index", "nunique")).reset_index().sort_values("top_rows", ascending=False)
        best_by_top = work.groupby(["top_profit_class", "selector", "binding_type", "binding_method", "transform"], dropna=False).agg(rows=("top_row_index", "size"), match_rows=("profit_match", "sum")).reset_index()
        best_by_top["match_rows"] = best_by_top["match_rows"].astype(int)
        best_by_top = best_by_top.sort_values(["top_profit_class", "match_rows", "rows"], ascending=[True, False, False]).groupby("top_profit_class", as_index=False).head(5)
        focus = work[(work["transform"].eq("scale_3")) & (work["binding_method"].isin(["max_profit_raw_row", "profit_max", "candidate_id_eq_top_candidate_id"]))].copy()
        focus = focus.groupby(["selector", "binding_type", "binding_method", "transform", "top_profit_class", "selected_profit_class", "ratio_class"], dropna=False).agg(rows=("top_row_index", "size"), match_rows=("profit_match", "sum")).reset_index()
        focus["match_rows"] = focus["match_rows"].astype(int)
        focus = focus.sort_values(["match_rows", "rows"], ascending=[False, False])
        ratios = work[(work["selector"].eq("latest_start")) & (work["binding_method"].eq("max_profit_raw_row")) & (work["transform"].eq("scale_3"))].copy()
        ratios = ratios.groupby(["top_profit_class", "selected_profit_class", "ratio_class", "profit_match"], dropna=False).agg(rows=("top_row_index", "size")).reset_index().sort_values("rows", ascending=False)
        mismatch = work[(work["selector"].eq("latest_start")) & (work["binding_method"].eq("max_profit_raw_row")) & (work["transform"].eq("scale_3")) & (~work["profit_match"].astype(bool))].copy()
        keep = ["top_row_index", "entry_time", "cluster_id", "top_candidate_id", "top_profit", "selected_profit", "transformed_profit", "profit_match", "selected_component_id", "top_profit_class", "selected_profit_class", "ratio_class"]
        mismatch = mismatch[keep].sort_values(["top_profit_class", "entry_time"])

    best_match = int(tsum["profit_match_rows"].max()) if not tsum.empty and "profit_match_rows" in tsum.columns else 0
    unexpected_full = bool((tsum.get("full_profit_match", pd.Series(dtype=bool)).astype(str).str.lower() == "true").any()) if not tsum.empty else False

    if not (inputs_ok and upstream_ok and rows_ok and tsum_ok and b94_ok):
        status = "PROFIT_CLASS_MISMATCH_DIAGNOSTIC_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif unexpected_full:
        status = "PROFIT_CLASS_DIAGNOSTIC_UNEXPECTED_FULL_MATCH_REVIEW_REQUIRED_AUDIT_ONLY_LIVE_BLOCKED"
    else:
        status = "PROFIT_CLASS_MISMATCH_DIAGNOSTIC_READY_AUDIT_ONLY_LIVE_BLOCKED"

    decision = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_25c95_not_matched_status_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["transform_rows", len(rows), EXPECTED_TRANSFORM_ROWS, "PASS" if rows_ok else "FAIL"],
        ["transform_summary_rows", len(tsum), EXPECTED_TRANSFORM_SUMMARY_ROWS, "PASS" if tsum_ok else "FAIL"],
        ["25c94_profit_binding_rows", len(b94), EXPECTED_25C94_BINDING_ROWS, "PASS" if b94_ok else "FAIL"],
        ["best_transform_profit_match_rows", best_match, EXPECTED_TOP_ROWS, "BLOCKED"],
        ["unexpected_full_match", unexpected_full, False, "PASS" if not unexpected_full else "REVIEW"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
        ["source_recovery_approved", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([
        ["B96-001", "inputs/25c95-status", "CLOSED" if inputs_ok and upstream_ok and rows_ok and tsum_ok and b94_ok else "OPEN", "HARD", "25C95 artifacts and expected not-matched status must be present."],
        ["B96-002", "profit_class_diagnostic", "CLOSED" if status.endswith("LIVE_BLOCKED") else "OPEN", "INFO", "Diagnostic artifacts produced; not source recovery."],
        ["B96-003", "representative_profit_binding", "OPEN", "HARD", "25C95 did not find 125/125 transform binding."],
        ["B96-004", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked."],
        ["B96-005", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 is auxiliary-only and not used."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])

    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "source_recovery_approved": False, "upstream_25c95_ok": upstream_ok, "inputs_present": inputs_ok, "transform_rows": int(len(rows)), "transform_summary_rows": int(len(tsum)), "25c94_profit_binding_rows": int(len(b94)), "best_transform_profit_match_rows": best_match, "unexpected_full_match": unexpected_full, "top_profit_classes": int(len(top_dist)), "best_candidate_mismatch_rows": int(len(mismatch)), "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "external_actions": ACTIONS}

    inv.to_csv(out / "25c96_input_inventory.csv", index=False, encoding="utf-8-sig")
    top_dist.to_csv(out / "25c96_top_profit_class_distribution.csv", index=False, encoding="utf-8-sig")
    best_by_top.to_csv(out / "25c96_best_by_top_profit_class.csv", index=False, encoding="utf-8-sig")
    focus.to_csv(out / "25c96_focus_class_breakdown.csv", index=False, encoding="utf-8-sig")
    ratios.to_csv(out / "25c96_ratio_distribution.csv", index=False, encoding="utf-8-sig")
    mismatch.to_csv(out / "25c96_best_candidate_mismatch_rows.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c96_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c96_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c96_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C96 profit class mismatch diagnostic audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Decision matrix", md(decision), "", "## Top profit class distribution", md(top_dist), "", "## Best by top profit class", md(best_by_top), "", "## Focus class breakdown", md(focus), "", "## Ratio distribution for latest_start/max_profit_raw_row/scale_3", md(ratios), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- diagnostic only; no partial match promotion", "- A002 not used", "- source recovery not approved", "- live evaluator/final signal/external actions remain OFF", "- NO_SIGNAL must not notify Discord"])
    (out / "GOLD_V2_25C96_PROFIT_CLASS_MISMATCH_DIAGNOSTIC_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs() / f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") or status.endswith("AUDIT_ONLY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
