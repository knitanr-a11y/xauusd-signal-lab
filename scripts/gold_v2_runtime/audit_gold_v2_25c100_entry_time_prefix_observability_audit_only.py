#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C100_ENTRY_TIME_PREFIX_OBSERVABILITY_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c100_entry_time_prefix_observability_audit_only"
INPUTS = ["25c99_summary.json", "25c99_row_observability_flags.csv", "25c99_ex_ante_entry_offset_signature_summary.csv", "25c98_temporal_feature_rows.csv", "25c94_selector_component_rows.csv", "25c94_profit_binding_rows.csv", "rr125_raw_signal_ledger.csv"]
EXPECTED_25C99_STATUS = "TEMPORAL_ENTRY_OFFSET_DISAMBIGUATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
EXPECTED_FEATURE_ROWS = 250
EXPECTED_COMPONENT_ROWS = 250
EXPECTED_BINDING_ROWS = 5250
EXPECTED_RAW_ROWS = 6834
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
PREFIX_SIG = ["selector", "top_candidate_id", "prefix_component_count", "prefix_component_unique_origins", "prefix_candidate_ids", "prefix_origin_ids", "prefix_candidate_id_eq_top_candidate_id_class", "prefix_max_profit_raw_row_class", "prefix_min_profit_raw_row_class", "prefix_first_component_sort_raw_row_class", "prefix_last_component_sort_raw_row_class", "prefix_profit_mean_class", "prefix_profit_median_class", "entry_offset_from_component_min_min_class"]


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


def cls(v: Any) -> str:
    try:
        f = float(v)
        if math.isnan(f): return "NA"
        return f"{round(f, 6):.6f}"
    except Exception: return "NA"


def md(df: pd.DataFrame, n: int = 40) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows(): lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def prep_raw(raw: pd.DataFrame) -> pd.DataFrame:
    r = raw.copy()
    if "policy" in r.columns: r = r[r["policy"].astype(str).eq("RR125_from_RR1_rules")].copy()
    r["entry_time"] = pd.to_datetime(r["entry_time"], errors="coerce")
    r["exit_time"] = pd.to_datetime(r.get("exit_time"), errors="coerce") if "exit_time" in r.columns else pd.NaT
    r["profit_r"] = pd.to_numeric(r["profit_r"], errors="coerce") if "profit_r" in r.columns else pd.to_numeric(r.get("profit"), errors="coerce")
    if "candidate_id" not in r.columns: r["candidate_id"] = r.get("origin_id", "")
    if "origin_id" not in r.columns: r["origin_id"] = r["candidate_id"]
    r["dataset"] = r["dataset"].astype(str)
    r["direction"] = r["direction"].astype(str)
    r = r.sort_values(["dataset", "direction", "entry_time", "exit_time", "candidate_id", "origin_id"], kind="mergesort").reset_index(drop=True)
    comp_ids, last_key, last_entry, comp_no = [], None, None, -1
    for _, row in r.iterrows():
        key = (row["dataset"], row["direction"])
        if key != last_key:
            comp_no = 0
        elif pd.notna(last_entry) and pd.notna(row["entry_time"]) and (row["entry_time"] - last_entry).total_seconds() / 60.0 > 15:
            comp_no += 1
        comp_ids.append(f"{row['dataset']}|{row['direction']}|entry_gap15|{comp_no}")
        last_key, last_entry = key, row["entry_time"]
    r["selected_component_id"] = comp_ids
    return r


def prefix_features(features: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, f in features.iterrows():
        entry = pd.to_datetime(f["entry_time"], errors="coerce")
        comp = str(f["selected_component_id"])
        cr = raw[raw["selected_component_id"].astype(str).eq(comp)].copy()
        pr = cr[cr["entry_time"].le(entry)].copy()
        fr = cr[cr["entry_time"].gt(entry)].copy()
        prof = pr["profit_r"].dropna()
        row = f.to_dict()
        row["full_component_raw_rows"] = int(len(cr)); row["prefix_component_count"] = int(len(pr)); row["future_component_raw_rows"] = int(len(fr))
        row["prefix_component_unique_origins"] = int(pr["origin_id"].astype(str).nunique()) if not pr.empty else 0
        row["prefix_candidate_ids"] = ";".join(sorted(set(pr["candidate_id"].astype(str)))) if not pr.empty else ""
        row["prefix_origin_ids"] = ";".join(sorted(set(pr["origin_id"].astype(str)))) if not pr.empty else ""
        row["prefix_candidate_id_eq_top_candidate_id"] = float(pr[pr["candidate_id"].astype(str).eq(str(f["top_candidate_id"]))]["profit_r"].iloc[0]) if ((not pr.empty) and pr["candidate_id"].astype(str).eq(str(f["top_candidate_id"])).any()) else math.nan
        row["prefix_max_profit_raw_row"] = float(prof.max()) if len(prof) else math.nan
        row["prefix_min_profit_raw_row"] = float(prof.min()) if len(prof) else math.nan
        row["prefix_first_component_sort_raw_row"] = float(pr["profit_r"].iloc[0]) if len(pr) else math.nan
        row["prefix_last_component_sort_raw_row"] = float(pr["profit_r"].iloc[-1]) if len(pr) else math.nan
        row["prefix_profit_mean"] = float(prof.mean()) if len(prof) else math.nan
        row["prefix_profit_median"] = float(prof.median()) if len(prof) else math.nan
        row["prefix_profit_sum"] = float(prof.sum()) if len(prof) else math.nan
        for c in ["prefix_candidate_id_eq_top_candidate_id", "prefix_max_profit_raw_row", "prefix_min_profit_raw_row", "prefix_first_component_sort_raw_row", "prefix_last_component_sort_raw_row", "prefix_profit_mean", "prefix_profit_median", "prefix_profit_sum"]:
            row[c + "_class"] = cls(row[c])
        rows.append(row)
    return pd.DataFrame(rows)


def signature_summary(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    missing = [c for c in PREFIX_SIG if c not in rows.columns]
    if missing:
        return pd.DataFrame([{"signature_name": "prefix_only_plus_entry_offset", "groups": 0, "collision_groups": 0, "rows_in_collision_groups": 0, "max_top_profit_classes": 0, "missing_columns": ";".join(missing)}]), pd.DataFrame(), pd.DataFrame()
    g = rows.groupby(PREFIX_SIG, dropna=False).agg(rows=("top_row_index", "nunique"), top_profit_classes=("top_profit_class", "nunique"), top_profit_values=("top_profit_class", lambda s: ";".join(sorted(set(map(str, s)))))).reset_index()
    bad = g[g["top_profit_classes"] > 1].copy()
    s = pd.DataFrame([{"signature_name": "prefix_only_plus_entry_offset", "groups": int(len(g)), "collision_groups": int(len(bad)), "rows_in_collision_groups": int(bad["rows"].sum()) if not bad.empty else 0, "max_top_profit_classes": int(g["top_profit_classes"].max()) if not g.empty else 0, "missing_columns": ""}])
    if bad.empty: return s, pd.DataFrame(), pd.DataFrame()
    keys = bad[PREFIX_SIG].drop_duplicates(); cr = rows.merge(keys, on=PREFIX_SIG, how="inner")
    return s, bad, cr


def field_match(rows: pd.DataFrame) -> pd.DataFrame:
    pairs = [("component_count", "prefix_component_count"), ("component_unique_origins", "prefix_component_unique_origins"), ("candidate_ids", "prefix_candidate_ids"), ("origin_ids", "prefix_origin_ids"), ("candidate_id_eq_top_candidate_id_class", "prefix_candidate_id_eq_top_candidate_id_class"), ("max_profit_raw_row_class", "prefix_max_profit_raw_row_class"), ("min_profit_raw_row_class", "prefix_min_profit_raw_row_class"), ("first_component_sort_raw_row_class", "prefix_first_component_sort_raw_row_class"), ("last_component_sort_raw_row_class", "prefix_last_component_sort_raw_row_class"), ("profit_mean_class", "prefix_profit_mean_class"), ("profit_median_class", "prefix_profit_median_class")]
    out = []
    for full, pref in pairs:
        if full in rows.columns and pref in rows.columns:
            m = rows[full].astype(str).eq(rows[pref].astype(str))
            out.append({"full_field": full, "prefix_field": pref, "rows": int(len(rows)), "match_rows": int(m.sum()), "mismatch_rows": int((~m).sum()), "all_match": bool(m.all())})
    return pd.DataFrame(out)


def main() -> int:
    created = datetime.now(timezone.utc).isoformat(); out = out_dir(); paths = {n: find_file(n) for n in INPUTS}
    inv = inventory(paths); s99 = read_json(paths["25c99_summary.json"])
    feat = read_csv(paths["25c98_temporal_feature_rows.csv"])
    comp = read_csv(paths["25c94_selector_component_rows.csv"])
    binding = read_csv(paths["25c94_profit_binding_rows.csv"])
    raw0 = read_csv(paths["rr125_raw_signal_ledger.csv"])
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    upstream_ok = s99.get("status") == EXPECTED_25C99_STATUS
    feat_ok = len(feat) == EXPECTED_FEATURE_ROWS
    comp_ok = len(comp) == EXPECTED_COMPONENT_ROWS
    bind_ok = len(binding) == EXPECTED_BINDING_ROWS
    raw = prep_raw(raw0) if not raw0.empty else pd.DataFrame()
    raw_ok = len(raw) == EXPECTED_RAW_ROWS
    pref = prefix_features(feat, raw) if not feat.empty and not raw.empty else pd.DataFrame()
    fm = field_match(pref) if not pref.empty else pd.DataFrame()
    ss, cg, cr = signature_summary(pref) if not pref.empty else (pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    collisions = int(ss["collision_groups"].iloc[0]) if not ss.empty else 0
    strict_pref = pref[pref["top_row_index"].isin([31, 78])].copy() if not pref.empty else pd.DataFrame()
    all_full_prefix_match = bool(fm["all_match"].all()) if not fm.empty else False
    future_rows = int((pref["future_component_raw_rows"] > 0).sum()) if "future_component_raw_rows" in pref else 0
    if not (inputs_ok and upstream_ok and feat_ok and comp_ok and bind_ok and raw_ok):
        status = "ENTRY_TIME_PREFIX_OBSERVABILITY_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif collisions > 0:
        status = "ENTRY_TIME_PREFIX_SIGNATURE_AMBIGUOUS_AUDIT_ONLY_LIVE_BLOCKED"
    elif not all_full_prefix_match:
        status = "ENTRY_TIME_PREFIX_DISAMBIGUATOR_CANDIDATE_FUTURE_FIELD_REVIEW_REQUIRED_AUDIT_ONLY_LIVE_BLOCKED"
    else:
        status = "ENTRY_TIME_PREFIX_DISAMBIGUATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
    decision = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_25c99_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["25c98_temporal_feature_rows", len(feat), EXPECTED_FEATURE_ROWS, "PASS" if feat_ok else "FAIL"],
        ["25c94_selector_component_rows", len(comp), EXPECTED_COMPONENT_ROWS, "PASS" if comp_ok else "FAIL"],
        ["25c94_profit_binding_rows", len(binding), EXPECTED_BINDING_ROWS, "PASS" if bind_ok else "FAIL"],
        ["raw_rr125_rows", len(raw), EXPECTED_RAW_ROWS, "PASS" if raw_ok else "FAIL"],
        ["prefix_feature_rows", len(pref), EXPECTED_FEATURE_ROWS, "PASS" if len(pref) == EXPECTED_FEATURE_ROWS else "FAIL"],
        ["prefix_signature_collision_groups", collisions, 0, "PASS" if collisions == 0 else "BLOCKED"],
        ["all_full_strict_fields_equal_prefix", all_full_prefix_match, True, "PASS" if all_full_prefix_match else "REVIEW"],
        ["rows_with_future_component_rows", future_rows, 0, "INFO" if future_rows else "PASS"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
        ["source_recovery_approved", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([
        ["B100-001", "inputs/25c99-status/raw", "CLOSED" if inputs_ok and upstream_ok and raw_ok else "OPEN", "HARD", "25C99 and raw RR125 source artifacts must be present."],
        ["B100-002", "prefix_signature", "OPEN" if collisions > 0 else "REVIEW", "HARD", "Prefix-only signature collisions remain." if collisions > 0 else "Prefix-only signature is unique; human review required."],
        ["B100-003", "future_full_component_fields", "OPEN" if not all_full_prefix_match else "CLOSED", "HARD", "Full component strict fields differ from entry-time prefix fields."],
        ["B100-004", "representative_profit_binding", "OPEN", "HARD", "Profit representative source remains unresolved."],
        ["B100-005", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked."],
        ["B100-006", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 is auxiliary-only and not used."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "source_recovery_approved": False, "upstream_25c99_ok": upstream_ok, "inputs_present": inputs_ok, "25c98_temporal_feature_rows": int(len(feat)), "25c94_selector_component_rows": int(len(comp)), "25c94_profit_binding_rows": int(len(binding)), "raw_rr125_rows": int(len(raw)), "prefix_feature_rows": int(len(pref)), "prefix_signature_collision_groups": collisions, "all_full_strict_fields_equal_prefix": all_full_prefix_match, "rows_with_future_component_rows": future_rows, "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "external_actions": ACTIONS}
    inv.to_csv(out / "25c100_input_inventory.csv", index=False, encoding="utf-8-sig")
    pref.to_csv(out / "25c100_prefix_feature_rows.csv", index=False, encoding="utf-8-sig")
    fm.to_csv(out / "25c100_prefix_field_match_summary.csv", index=False, encoding="utf-8-sig")
    ss.to_csv(out / "25c100_prefix_signature_summary.csv", index=False, encoding="utf-8-sig")
    cg.to_csv(out / "25c100_prefix_signature_collision_groups.csv", index=False, encoding="utf-8-sig")
    cr.to_csv(out / "25c100_prefix_signature_collision_rows.csv", index=False, encoding="utf-8-sig")
    strict_pref.to_csv(out / "25c100_strict_collision_prefix_rows.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c100_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c100_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c100_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C100 entry-time prefix observability audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Decision matrix", md(decision), "", "## Prefix field match summary", md(fm), "", "## Prefix signature summary", md(ss), "", "## Strict collision prefix rows", md(strict_pref), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- prefix uniqueness not promoted", "- full-component future fields not promoted", "- A002 not used", "- source recovery not approved", "- live evaluator/final signal/external actions remain OFF", "- NO_SIGNAL must not notify Discord"])
    (out / "GOLD_V2_25C100_ENTRY_TIME_PREFIX_OBSERVABILITY_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs() / f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") or status.endswith("AUDIT_ONLY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
