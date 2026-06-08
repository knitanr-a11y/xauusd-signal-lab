#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C101_PREFIX_COLLISION_RAW_FIELD_SCAN_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c101_prefix_collision_raw_field_scan_audit_only"
INPUTS = ["25c100_summary.json", "25c100_prefix_feature_rows.csv", "25c100_prefix_signature_collision_groups.csv", "25c100_prefix_signature_collision_rows.csv", "25c100_prefix_field_match_summary.csv", "rr125_raw_signal_ledger.csv"]
EXPECTED_25C100_STATUS = "ENTRY_TIME_PREFIX_SIGNATURE_AMBIGUOUS_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_FEATURE_ROWS = 250
EXPECTED_COLLISION_GROUPS = 6
EXPECTED_COLLISION_ROWS = 14
EXPECTED_RAW_ROWS = 6834
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
PREFIX_SIG = ["selector", "top_candidate_id", "prefix_component_count", "prefix_component_unique_origins", "prefix_candidate_ids", "prefix_origin_ids", "prefix_candidate_id_eq_top_candidate_id_class", "prefix_max_profit_raw_row_class", "prefix_min_profit_raw_row_class", "prefix_first_component_sort_raw_row_class", "prefix_last_component_sort_raw_row_class", "prefix_profit_mean_class", "prefix_profit_median_class", "entry_offset_from_component_min_min_class"]
FORBIDDEN_TOKENS = ["profit", "pnl", "outcome", "result", "win", "loss", "exit", "close", "tp", "sl", "mae", "mfe", "hit", "duration", "holding"]
STRUCTURAL = {"dataset", "direction", "candidate_id", "origin_id", "strategy_id", "policy", "filter", "component", "cluster", "entry_time"}


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


def md(df: pd.DataFrame, n: int = 40) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows(): lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def col_class(c: str) -> str:
    lc = c.lower()
    if any(tok in lc for tok in FORBIDDEN_TOKENS): return "forbidden_future_or_outcome"
    if lc in STRUCTURAL or any(tok in lc for tok in ["strategy", "policy", "filter", "component", "cluster"]): return "structural_or_id"
    return "candidate_ex_ante_review"


def prep_raw(raw: pd.DataFrame) -> pd.DataFrame:
    r = raw.copy()
    if "policy" in r.columns: r = r[r["policy"].astype(str).eq("RR125_from_RR1_rules")].copy()
    r["entry_time"] = pd.to_datetime(r["entry_time"], errors="coerce")
    r["exit_time"] = pd.to_datetime(r.get("exit_time"), errors="coerce") if "exit_time" in r.columns else pd.NaT
    if "candidate_id" not in r.columns: r["candidate_id"] = r.get("origin_id", "")
    if "origin_id" not in r.columns: r["origin_id"] = r["candidate_id"]
    r["dataset"] = r["dataset"].astype(str); r["direction"] = r["direction"].astype(str)
    r = r.sort_values(["dataset", "direction", "entry_time", "exit_time", "candidate_id", "origin_id"], kind="mergesort").reset_index(drop=True)
    comp_ids, last_key, last_entry, comp_no = [], None, None, -1
    for _, row in r.iterrows():
        key = (row["dataset"], row["direction"])
        if key != last_key: comp_no = 0
        elif pd.notna(last_entry) and pd.notna(row["entry_time"]) and (row["entry_time"] - last_entry).total_seconds() / 60.0 > 15: comp_no += 1
        comp_ids.append(f"{row['dataset']}|{row['direction']}|entry_gap15|{comp_no}")
        last_key, last_entry = key, row["entry_time"]
    r["selected_component_id"] = comp_ids
    return r


def valset(s: pd.Series) -> str:
    vals = []
    for v in s.dropna().tolist():
        sv = str(v)
        if sv and sv.lower() != "nan": vals.append(sv)
    return ";".join(sorted(set(vals)))


def collision_raw_values(coll: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    out = []
    for _, row in coll.iterrows():
        entry = pd.to_datetime(row["entry_time"], errors="coerce")
        comp = str(row["selected_component_id"])
        pr = raw[raw["selected_component_id"].astype(str).eq(comp) & raw["entry_time"].le(entry)].copy()
        base = row.to_dict()
        for c in raw.columns:
            base[f"rawset__{c}"] = valset(pr[c]) if c in pr.columns else ""
        out.append(base)
    return pd.DataFrame(out)


def count_collisions(df: pd.DataFrame, cols: list[str]) -> tuple[int, int, int]:
    g = df.groupby(cols, dropna=False).agg(rows=("top_row_index", "nunique"), top_profit_classes=("top_profit_class", "nunique")).reset_index()
    bad = g[g["top_profit_classes"] > 1]
    return int(len(bad)), int(bad["rows"].sum()) if not bad.empty else 0, int(g["top_profit_classes"].max()) if not g.empty else 0


def main() -> int:
    created = datetime.now(timezone.utc).isoformat(); out = out_dir(); paths = {n: find_file(n) for n in INPUTS}
    inv = inventory(paths); s100 = read_json(paths["25c100_summary.json"])
    feat = read_csv(paths["25c100_prefix_feature_rows.csv"])
    cgroups = read_csv(paths["25c100_prefix_signature_collision_groups.csv"])
    coll = read_csv(paths["25c100_prefix_signature_collision_rows.csv"])
    raw0 = read_csv(paths["rr125_raw_signal_ledger.csv"])
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    upstream_ok = s100.get("status") == EXPECTED_25C100_STATUS
    feat_ok = len(feat) == EXPECTED_FEATURE_ROWS
    cg_ok = len(cgroups) == EXPECTED_COLLISION_GROUPS
    coll_ok = len(coll) == EXPECTED_COLLISION_ROWS
    raw = prep_raw(raw0) if not raw0.empty else pd.DataFrame(); raw_ok = len(raw) == EXPECTED_RAW_ROWS
    value_rows = collision_raw_values(coll, raw) if not coll.empty and not raw.empty else pd.DataFrame()
    base_collision_groups = int(s100.get("prefix_signature_collision_groups", 0) or 0)
    inv_cols = pd.DataFrame([{"raw_column": c, "column_class": col_class(c), "dtype": str(raw[c].dtype) if c in raw.columns else ""} for c in raw.columns])
    scan = []
    if not value_rows.empty:
        for c in raw.columns:
            vc = f"rawset__{c}"
            cols = PREFIX_SIG + [vc]
            missing = [x for x in cols if x not in value_rows.columns]
            if missing:
                cg2, rows2, mx = base_collision_groups, len(coll), 0
            else:
                cg2, rows2, mx = count_collisions(value_rows, cols)
            cls = col_class(c)
            scan.append({"raw_column": c, "column_class": cls, "base_collision_groups": base_collision_groups, "collision_groups_with_column": cg2, "rows_in_collision_groups_with_column": rows2, "max_top_profit_classes_with_column": mx, "resolves_collision": cg2 == 0, "human_review_required": cg2 == 0 and cls != "forbidden_future_or_outcome"})
    scan_df = pd.DataFrame(scan).sort_values(["resolves_collision", "column_class", "raw_column"], ascending=[False, True, True]) if scan else pd.DataFrame()
    resolving = scan_df[scan_df["resolves_collision"].astype(bool)].copy() if not scan_df.empty else pd.DataFrame()
    non_forbidden = resolving[~resolving["column_class"].eq("forbidden_future_or_outcome")].copy() if not resolving.empty else pd.DataFrame()
    if not (inputs_ok and upstream_ok and feat_ok and cg_ok and coll_ok and raw_ok):
        status = "PREFIX_COLLISION_RAW_FIELD_SCAN_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif resolving.empty:
        status = "PREFIX_COLLISION_RAW_FIELD_SCAN_NO_EX_ANTE_DISCRIMINATOR_AUDIT_ONLY_LIVE_BLOCKED"
    elif non_forbidden.empty:
        status = "PREFIX_COLLISION_RAW_FIELD_SCAN_ONLY_FORBIDDEN_DISCRIMINATORS_AUDIT_ONLY_LIVE_BLOCKED"
    else:
        status = "PREFIX_COLLISION_RAW_FIELD_DISCRIMINATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
    decision = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_25c100_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["prefix_feature_rows", len(feat), EXPECTED_FEATURE_ROWS, "PASS" if feat_ok else "FAIL"],
        ["prefix_collision_groups", len(cgroups), EXPECTED_COLLISION_GROUPS, "PASS" if cg_ok else "FAIL"],
        ["prefix_collision_rows", len(coll), EXPECTED_COLLISION_ROWS, "PASS" if coll_ok else "FAIL"],
        ["raw_rr125_rows", len(raw), EXPECTED_RAW_ROWS, "PASS" if raw_ok else "FAIL"],
        ["raw_columns_scanned", len(scan_df), ">0", "PASS" if len(scan_df) else "FAIL"],
        ["resolving_raw_columns", len(resolving), 0, "REVIEW" if len(resolving) else "BLOCKED"],
        ["non_forbidden_resolving_raw_columns", len(non_forbidden), 0, "REVIEW" if len(non_forbidden) else "BLOCKED"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
        ["source_recovery_approved", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([
        ["B101-001", "inputs/25c100/raw", "CLOSED" if inputs_ok and upstream_ok and raw_ok else "OPEN", "HARD", "25C100 and raw RR125 artifacts must be present."],
        ["B101-002", "raw_field_discriminator", "REVIEW" if len(non_forbidden) else "OPEN", "HARD", "Non-forbidden raw prefix columns resolve collisions; human review required." if len(non_forbidden) else "No non-forbidden raw prefix discriminator found."],
        ["B101-003", "forbidden_future_outcome_columns", "OPEN" if len(resolving) and len(non_forbidden) < len(resolving) else "CLOSED", "HARD", "Forbidden outcome/profit columns must not be promoted."],
        ["B101-004", "representative_profit_binding", "OPEN", "HARD", "Profit representative source remains unresolved."],
        ["B101-005", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked."],
        ["B101-006", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 is auxiliary-only and not used."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "source_recovery_approved": False, "upstream_25c100_ok": upstream_ok, "inputs_present": inputs_ok, "prefix_feature_rows": int(len(feat)), "prefix_collision_groups": int(len(cgroups)), "prefix_collision_rows": int(len(coll)), "raw_rr125_rows": int(len(raw)), "raw_columns_scanned": int(len(scan_df)), "resolving_raw_columns": int(len(resolving)), "non_forbidden_resolving_raw_columns": int(len(non_forbidden)), "resolving_column_candidates": clean(resolving.to_dict("records")[:50]), "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "external_actions": ACTIONS}
    inv.to_csv(out / "25c101_input_inventory.csv", index=False, encoding="utf-8-sig")
    inv_cols.to_csv(out / "25c101_raw_column_inventory.csv", index=False, encoding="utf-8-sig")
    value_rows.to_csv(out / "25c101_collision_prefix_raw_value_rows.csv", index=False, encoding="utf-8-sig")
    scan_df.to_csv(out / "25c101_raw_column_discriminator_summary.csv", index=False, encoding="utf-8-sig")
    resolving.to_csv(out / "25c101_resolving_column_candidates.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c101_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c101_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c101_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C101 prefix collision raw field scan audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Decision matrix", md(decision), "", "## Resolving column candidates", md(resolving), "", "## Raw column discriminator summary", md(scan_df), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- raw-column uniqueness not promoted", "- forbidden future/outcome/profit columns not promoted", "- A002 not used", "- source recovery not approved", "- live evaluator/final signal/external actions remain OFF", "- NO_SIGNAL must not notify Discord"])
    (out / "GOLD_V2_25C101_PREFIX_COLLISION_RAW_FIELD_SCAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs() / f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") or status.endswith("AUDIT_ONLY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
