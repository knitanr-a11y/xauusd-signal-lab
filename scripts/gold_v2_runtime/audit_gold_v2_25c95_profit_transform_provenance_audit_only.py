#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C95_PROFIT_TRANSFORM_PROVENANCE_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c95_profit_transform_provenance_audit_only"
INPUTS = [
    "25c94_summary.json",
    "25c94_decision_matrix.csv",
    "25c94_profit_binding_rows.csv",
    "25c94_profit_binding_summary.csv",
    "25c94_profit_presence_diagnostics.csv",
    "25c94_selector_pair_stability.csv",
]
EXPECTED_25C94_STATUS = "NON_ORACLE_SELECTOR_COUNT_MATCHED_PROFIT_BINDING_BLOCKED_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_BINDING_ROWS = 5250
EXPECTED_BINDING_SUMMARY_ROWS = 42
EXPECTED_PAIR_ROWS = 125
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
TRANSFORMS = {
    "direct": lambda x: x,
    "scale_3": lambda x: x * 3.0,
    "scale_2": lambda x: x * 2.0,
    "scale_4": lambda x: x * 4.0,
    "scale_1_5": lambda x: x * 1.5,
    "scale_0_75": lambda x: x * 0.75,
    "scale_1_over_3": lambda x: x / 3.0,
    "neg_direct": lambda x: -x,
    "neg_scale_3": lambda x: -x * 3.0,
}


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


def num_eq(a: Any, b: Any) -> bool:
    try:
        af, bf = float(a), float(b)
        return (not math.isnan(af)) and (not math.isnan(bf)) and abs(af - bf) <= 1e-6
    except Exception:
        return False


def md(df: pd.DataFrame, n: int = 40) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    created = datetime.now(timezone.utc).isoformat(); out = out_dir(); paths = {n: find_file(n) for n in INPUTS}
    inv = inventory(paths); s94 = read_json(paths["25c94_summary.json"])
    binding_rows = read_csv(paths["25c94_profit_binding_rows.csv"])
    binding_summary = read_csv(paths["25c94_profit_binding_summary.csv"])
    pair = read_csv(paths["25c94_selector_pair_stability.csv"])
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    upstream_ok = s94.get("status") == EXPECTED_25C94_STATUS
    binding_rows_ok = len(binding_rows) == EXPECTED_BINDING_ROWS
    binding_summary_ok = len(binding_summary) == EXPECTED_BINDING_SUMMARY_ROWS
    pair_rows_ok = len(pair) == EXPECTED_PAIR_ROWS

    transform_rows = []
    if not binding_rows.empty:
        for _, row in binding_rows.iterrows():
            if not bool(row.get("binding_found", False)) or pd.isna(row.get("selected_profit")):
                continue
            selected_profit = float(row["selected_profit"]); top_profit = float(row["top_profit"])
            for name, fn in TRANSFORMS.items():
                transformed = fn(selected_profit)
                transform_rows.append({
                    "top_row_index": int(row["top_row_index"]), "selector": row["selector"], "binding_type": row["binding_type"], "binding_method": row["binding_method"], "transform": name,
                    "entry_time": row["entry_time"], "cluster_id": row["cluster_id"], "top_candidate_id": row["top_candidate_id"], "top_profit": top_profit,
                    "selected_profit": selected_profit, "transformed_profit": transformed, "profit_match": num_eq(transformed, top_profit), "selected_component_id": row["selected_component_id"],
                })
    trows = pd.DataFrame(transform_rows)
    if trows.empty:
        tsum = pd.DataFrame(columns=["selector", "binding_type", "binding_method", "transform", "rows", "binding_found_rows", "profit_match_rows", "full_profit_match"])
    else:
        tsum = trows.groupby(["selector", "binding_type", "binding_method", "transform"], dropna=False).agg(rows=("top_row_index", "size"), binding_found_rows=("selected_profit", "size"), profit_match_rows=("profit_match", "sum")).reset_index()
        tsum["profit_match_rows"] = tsum["profit_match_rows"].astype(int)
        tsum["full_profit_match"] = tsum["profit_match_rows"].eq(EXPECTED_PAIR_ROWS)
        tsum = tsum.sort_values(["profit_match_rows", "binding_found_rows", "selector", "binding_method", "transform"], ascending=[False, False, True, True, True])
    best_rows = tsum.head(20).copy()
    full = (not tsum.empty) and bool(tsum["full_profit_match"].any())
    best_match = int(tsum["profit_match_rows"].max()) if not tsum.empty else 0

    if not (inputs_ok and upstream_ok and binding_rows_ok and binding_summary_ok and pair_rows_ok):
        status = "PROFIT_TRANSFORM_PROVENANCE_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif full:
        status = "PROFIT_TRANSFORM_BINDING_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
    else:
        status = "PROFIT_TRANSFORM_BINDING_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED"

    decision = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_25c94_blocked_status_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["profit_binding_rows", len(binding_rows), EXPECTED_BINDING_ROWS, "PASS" if binding_rows_ok else "FAIL"],
        ["profit_binding_summary_rows", len(binding_summary), EXPECTED_BINDING_SUMMARY_ROWS, "PASS" if binding_summary_ok else "FAIL"],
        ["selector_pair_rows", len(pair), EXPECTED_PAIR_ROWS, "PASS" if pair_rows_ok else "FAIL"],
        ["best_transform_profit_match_rows", best_match, EXPECTED_PAIR_ROWS, "PASS" if full else "BLOCKED"],
        ["full_profit_transform_match", full, True, "PASS" if full else "BLOCKED"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
        ["source_recovery_approved", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([
        ["B95-001", "inputs/25c94-status", "CLOSED" if inputs_ok and upstream_ok and binding_rows_ok and binding_summary_ok and pair_rows_ok else "OPEN", "HARD", "25C94 artifacts and expected blocked status must be present."],
        ["B95-002", "profit_transform_binding", "CLOSED" if full else "OPEN", "HARD", "At least one exact transform must match 125/125 rows."],
        ["B95-003", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked regardless of transform audit result."],
        ["B95-004", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 is auxiliary-only and not used."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "source_recovery_approved": False, "upstream_25c94_ok": upstream_ok, "inputs_present": inputs_ok, "profit_binding_rows": int(len(binding_rows)), "profit_binding_summary_rows": int(len(binding_summary)), "selector_pair_rows": int(len(pair)), "best_transform_profit_match_rows": best_match, "full_profit_transform_match": full, "best_transform_candidates": clean(best_rows.to_dict("records")), "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "external_actions": ACTIONS}

    inv.to_csv(out / "25c95_input_inventory.csv", index=False, encoding="utf-8-sig")
    trows.to_csv(out / "25c95_transform_rows.csv", index=False, encoding="utf-8-sig")
    tsum.to_csv(out / "25c95_transform_summary.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c95_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c95_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c95_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C95 profit transform provenance audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Decision matrix", md(decision), "", "## Best transform summary", md(tsum), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- partial transform matches are not promoted", "- A002 not used", "- source recovery not approved", "- live evaluator/final signal/external actions remain OFF", "- NO_SIGNAL must not notify Discord"])
    (out / "GOLD_V2_25C95_PROFIT_TRANSFORM_PROVENANCE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs() / f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") or status.endswith("AUDIT_ONLY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
