#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math, re, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C102_NON_ID_DISCRIMINATOR_FULL_SET_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c102_non_id_discriminator_full_set_audit_only"
INPUTS = ["25c101_summary.json", "25c101_resolving_column_candidates.csv", "25c101_raw_column_discriminator_summary.csv", "25c101_collision_prefix_raw_value_rows.csv", "25c100_prefix_feature_rows.csv", "rr125_raw_signal_ledger.csv"]
EXPECTED_25C101_STATUS = "PREFIX_COLLISION_RAW_FIELD_DISCRIMINATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
EXPECTED_FEATURE_ROWS = 250
EXPECTED_RAW_ROWS = 6834
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
PREFIX_SIG = ["selector", "top_candidate_id", "prefix_component_count", "prefix_component_unique_origins", "prefix_candidate_ids", "prefix_origin_ids", "prefix_candidate_id_eq_top_candidate_id_class", "prefix_max_profit_raw_row_class", "prefix_min_profit_raw_row_class", "prefix_first_component_sort_raw_row_class", "prefix_last_component_sort_raw_row_class", "prefix_profit_mean_class", "prefix_profit_median_class", "entry_offset_from_component_min_min_class"]
HARD_REJECT = {"entry_time_value_set", "entry_month_value_set", "selected_component_id_value_set", "exit_time_value_set"}
REVIEW_REPS = {"added_filter_text_value_set", "added_filter_text_count", "added_filter_text_token_set", "train_score_value_set", "train_score_count", "train_score_min_class", "train_score_max_class", "train_score_mean_class", "entry_price_value_set", "entry_price_round_1", "entry_price_round_5", "entry_price_round_10"}


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


def valset(s: pd.Series) -> str:
    vals = []
    for v in s.dropna().tolist():
        sv = str(v)
        if sv and sv.lower() != "nan": vals.append(sv)
    return ";".join(sorted(set(vals)))


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


def token_set(text_set: str) -> str:
    toks = []
    for tok in re.split(r"[^A-Za-z0-9_\.<>==]+", str(text_set)):
        if tok: toks.append(tok)
    return ";".join(sorted(set(toks)))


def build_features(rows: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    out = []
    for _, row in rows.iterrows():
        entry = pd.to_datetime(row["entry_time"], errors="coerce")
        comp = str(row["selected_component_id"])
        pr = raw[raw["selected_component_id"].astype(str).eq(comp) & raw["entry_time"].le(entry)].copy()
        d = row.to_dict()
        for col in ["added_filter_text", "train_score", "entry_price", "entry_month", "entry_time", "selected_component_id", "exit_time"]:
            if col in pr.columns:
                d[col + "_value_set"] = valset(pr[col])
        aft = d.get("added_filter_text_value_set", "")
        d["added_filter_text_count"] = 0 if not aft else len(aft.split(";"))
        d["added_filter_text_token_set"] = token_set(aft)
        ts = pd.to_numeric(pr["train_score"], errors="coerce").dropna() if "train_score" in pr.columns else pd.Series(dtype=float)
        d["train_score_count"] = int(len(ts))
        d["train_score_min_class"] = cls(ts.min()) if len(ts) else "NA"
        d["train_score_max_class"] = cls(ts.max()) if len(ts) else "NA"
        d["train_score_mean_class"] = cls(ts.mean()) if len(ts) else "NA"
        ep = pd.to_numeric(pr["entry_price"], errors="coerce").dropna() if "entry_price" in pr.columns else pd.Series(dtype=float)
        base_ep = float(ep.iloc[-1]) if len(ep) else math.nan
        d["entry_price_round_1"] = cls(round(base_ep / 1.0) * 1.0) if not math.isnan(base_ep) else "NA"
        d["entry_price_round_5"] = cls(round(base_ep / 5.0) * 5.0) if not math.isnan(base_ep) else "NA"
        d["entry_price_round_10"] = cls(round(base_ep / 10.0) * 10.0) if not math.isnan(base_ep) else "NA"
        out.append(d)
    return pd.DataFrame(out)


def count_collisions(df: pd.DataFrame, cols: list[str]) -> tuple[int, int, int, pd.DataFrame, pd.DataFrame]:
    g = df.groupby(cols, dropna=False).agg(rows=("top_row_index", "nunique"), top_profit_classes=("top_profit_class", "nunique"), top_profit_values=("top_profit_class", lambda s: ";".join(sorted(set(map(str, s)))))).reset_index()
    bad = g[g["top_profit_classes"] > 1].copy()
    if bad.empty: return 0, 0, int(g["top_profit_classes"].max()) if not g.empty else 0, bad, pd.DataFrame()
    keys = bad[cols].drop_duplicates(); cr = df.merge(keys, on=cols, how="inner")
    return int(len(bad)), int(bad["rows"].sum()), int(g["top_profit_classes"].max()), bad, cr


def rep_class(name: str) -> str:
    if name in HARD_REJECT: return "hard_reject_id_time_or_forbidden"
    if name in REVIEW_REPS: return "review_only_non_id_candidate"
    return "other_review"


def main() -> int:
    created = datetime.now(timezone.utc).isoformat(); out = out_dir(); paths = {n: find_file(n) for n in INPUTS}
    inv = inventory(paths); s101 = read_json(paths["25c101_summary.json"])
    pref0 = read_csv(paths["25c100_prefix_feature_rows.csv"])
    resolving0 = read_csv(paths["25c101_resolving_column_candidates.csv"])
    raw0 = read_csv(paths["rr125_raw_signal_ledger.csv"])
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    upstream_ok = s101.get("status") == EXPECTED_25C101_STATUS
    pref_ok = len(pref0) == EXPECTED_FEATURE_ROWS
    resolving_ok = len(resolving0) >= 7
    raw = prep_raw(raw0) if not raw0.empty else pd.DataFrame(); raw_ok = len(raw) == EXPECTED_RAW_ROWS
    feat = build_features(pref0, raw) if not pref0.empty and not raw.empty else pd.DataFrame()
    reps = ["added_filter_text_value_set", "added_filter_text_count", "added_filter_text_token_set", "train_score_value_set", "train_score_count", "train_score_min_class", "train_score_max_class", "train_score_mean_class", "entry_price_value_set", "entry_price_round_1", "entry_price_round_5", "entry_price_round_10", "entry_month_value_set", "entry_time_value_set", "selected_component_id_value_set", "exit_time_value_set"]
    rows, cgroups, crows = [], [], []
    for rep in reps:
        if rep not in feat.columns: continue
        cg, rr, mx, bad, cr = count_collisions(feat, PREFIX_SIG + [rep])
        rc = rep_class(rep); resolves = cg == 0
        rows.append({"representation": rep, "representation_class": rc, "collision_groups": cg, "rows_in_collision_groups": rr, "max_top_profit_classes": mx, "resolves_full_set": resolves, "human_review_required": resolves and rc != "hard_reject_id_time_or_forbidden"})
        if not bad.empty:
            bad.insert(0, "representation", rep); cgroups.append(bad)
            cr.insert(0, "representation", rep); crows.append(cr)
    summary_df = pd.DataFrame(rows).sort_values(["resolves_full_set", "representation_class", "representation"], ascending=[False, True, True]) if rows else pd.DataFrame()
    cgdf = pd.concat(cgroups, ignore_index=True) if cgroups else pd.DataFrame(); crdf = pd.concat(crows, ignore_index=True) if crows else pd.DataFrame()
    resolves = summary_df[summary_df["resolves_full_set"].astype(bool)] if not summary_df.empty else pd.DataFrame()
    review_resolves = resolves[resolves["representation_class"].eq("review_only_non_id_candidate")] if not resolves.empty else pd.DataFrame()
    hard_resolves = resolves[resolves["representation_class"].eq("hard_reject_id_time_or_forbidden")] if not resolves.empty else pd.DataFrame()
    if not (inputs_ok and upstream_ok and pref_ok and raw_ok and resolving_ok):
        status = "NON_ID_DISCRIMINATOR_FULL_SET_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif len(resolves) == 0:
        status = "NON_ID_DISCRIMINATOR_FULL_SET_UNRESOLVED_AUDIT_ONLY_LIVE_BLOCKED"
    elif len(review_resolves) == 0 and len(hard_resolves) > 0:
        status = "NON_ID_DISCRIMINATOR_FULL_SET_ONLY_ID_OR_FORBIDDEN_AUDIT_ONLY_LIVE_BLOCKED"
    else:
        status = "NON_ID_DISCRIMINATOR_FULL_SET_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
    decision = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_25c101_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["prefix_feature_rows", len(pref0), EXPECTED_FEATURE_ROWS, "PASS" if pref_ok else "FAIL"],
        ["raw_rr125_rows", len(raw), EXPECTED_RAW_ROWS, "PASS" if raw_ok else "FAIL"],
        ["25c101_resolving_columns", len(resolving0), ">=7", "PASS" if resolving_ok else "FAIL"],
        ["representations_tested", len(summary_df), ">0", "PASS" if len(summary_df) else "FAIL"],
        ["full_set_resolving_representations", len(resolves), 0, "REVIEW" if len(resolves) else "BLOCKED"],
        ["review_only_non_id_resolving_representations", len(review_resolves), 0, "REVIEW" if len(review_resolves) else "BLOCKED"],
        ["hard_reject_resolving_representations", len(hard_resolves), 0, "INFO" if len(hard_resolves) else "PASS"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
        ["source_recovery_approved", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([
        ["B102-001", "inputs/25c101/raw", "CLOSED" if inputs_ok and upstream_ok and raw_ok else "OPEN", "HARD", "25C101 and raw RR125 artifacts must be present."],
        ["B102-002", "non_id_discriminator_full_set", "REVIEW" if len(review_resolves) else "OPEN", "HARD", "Review-only non-ID representation resolves full-set collisions." if len(review_resolves) else "No review-only non-ID representation resolves full-set collisions."],
        ["B102-003", "hard_reject_id_time_forbidden", "OPEN" if len(hard_resolves) else "CLOSED", "HARD", "ID/time/forbidden representations must not be promoted."],
        ["B102-004", "representative_profit_binding", "OPEN", "HARD", "Profit representative source remains unresolved."],
        ["B102-005", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked."],
        ["B102-006", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 is auxiliary-only and not used."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summ = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "source_recovery_approved": False, "upstream_25c101_ok": upstream_ok, "inputs_present": inputs_ok, "prefix_feature_rows": int(len(pref0)), "raw_rr125_rows": int(len(raw)), "representations_tested": int(len(summary_df)), "full_set_resolving_representations": int(len(resolves)), "review_only_non_id_resolving_representations": int(len(review_resolves)), "hard_reject_resolving_representations": int(len(hard_resolves)), "review_resolving_candidates": clean(review_resolves.to_dict("records")), "hard_reject_resolving_candidates": clean(hard_resolves.to_dict("records")), "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "external_actions": ACTIONS}
    inv.to_csv(out / "25c102_input_inventory.csv", index=False, encoding="utf-8-sig")
    feat.to_csv(out / "25c102_candidate_feature_rows.csv", index=False, encoding="utf-8-sig")
    summary_df.to_csv(out / "25c102_candidate_discriminator_summary.csv", index=False, encoding="utf-8-sig")
    cgdf.to_csv(out / "25c102_candidate_collision_groups.csv", index=False, encoding="utf-8-sig")
    crdf.to_csv(out / "25c102_candidate_collision_rows.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c102_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c102_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c102_summary.json", summ)
    report = "\n".join(["# GOLD V2 25C102 non-ID discriminator full-set audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Decision matrix", md(decision), "", "## Candidate discriminator summary", md(summary_df), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- non-ID uniqueness not promoted", "- ID/time/forbidden representations not promoted", "- A002 not used", "- source recovery not approved", "- live evaluator/final signal/external actions remain OFF", "- NO_SIGNAL must not notify Discord"])
    (out / "GOLD_V2_25C102_NON_ID_DISCRIMINATOR_FULL_SET_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs() / f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") or status.endswith("AUDIT_ONLY") else 2

if __name__ == "__main__":
    raise SystemExit(main())
