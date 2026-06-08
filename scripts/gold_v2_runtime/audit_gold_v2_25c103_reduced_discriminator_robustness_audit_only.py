#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math, re, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C103_REDUCED_DISCRIMINATOR_ROBUSTNESS_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c103_reduced_discriminator_robustness_audit_only"
INPUTS = ["25c102_summary.json", "25c102_candidate_feature_rows.csv", "25c102_candidate_discriminator_summary.csv", "25c102_candidate_collision_groups.csv", "25c102_candidate_collision_rows.csv"]
EXPECTED_25C102_STATUS = "NON_ID_DISCRIMINATOR_FULL_SET_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
EXPECTED_FEATURE_ROWS = 250
EXPECTED_DISC_ROWS = 16
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
PREFIX_SIG = ["selector", "top_candidate_id", "prefix_component_count", "prefix_component_unique_origins", "prefix_candidate_ids", "prefix_origin_ids", "prefix_candidate_id_eq_top_candidate_id_class", "prefix_max_profit_raw_row_class", "prefix_min_profit_raw_row_class", "prefix_first_component_sort_raw_row_class", "prefix_last_component_sort_raw_row_class", "prefix_profit_mean_class", "prefix_profit_median_class", "entry_offset_from_component_min_min_class"]
RULE_REPS = ["filter_feature_name_set", "filter_operator_feature_set", "filter_family_set", "filter_family_count", "filter_condition_count"]
SCORE_REPS = ["train_score_mean_bin_0_1", "train_score_mean_bin_0_25", "train_score_mean_bin_0_5", "train_score_range_bin_0_25", "train_score_count"]
PRICE_REPS = ["entry_price_bin_25", "entry_price_bin_50", "entry_price_bin_100", "entry_price_bin_250"]
ALL_REPS = RULE_REPS + SCORE_REPS + PRICE_REPS


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
    except Exception:
        pass
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
            r["bytes"] = p.stat().st_size
            r["sha256"] = sha256_file(p)
            if p.suffix.lower() == ".csv":
                r["row_count"] = len(pd.read_csv(p))
                r["columns"] = ";".join(pd.read_csv(p, nrows=0).columns)
        rows.append(r)
    return pd.DataFrame(rows)


def md(df: pd.DataFrame, n: int = 40) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def cls(v: Any) -> str:
    try:
        f = float(v)
        if math.isnan(f): return "NA"
        return f"{round(f, 6):.6f}"
    except Exception:
        return "NA"


def bin_value(v: Any, step: float) -> str:
    try:
        f = float(v)
        if math.isnan(f): return "NA"
        return cls(math.floor(f / step) * step)
    except Exception:
        return "NA"


def feature_family(name: str) -> str:
    n = str(name)
    if n.startswith("m5_"): return "m5"
    if "compression" in n: return "compression"
    if "range" in n: return "range"
    if "dist_low" in n: return "dist_low"
    if "dist_high" in n: return "dist_high"
    if "abs_ret" in n: return "abs_ret"
    if "ret" in n: return "ret"
    if "wick" in n: return "wick"
    return n.split("_")[0] if "_" in n else n


def parse_filter_text(text: str) -> tuple[str, str, str, int]:
    features, op_features, families = [], [], []
    parts = []
    for block in str(text).split(";"):
        for cond in re.split(r"\bAND\b|\bOR\b", block):
            cond = cond.strip()
            if cond: parts.append(cond)
    for cond in parts:
        m = re.match(r"^\s*([A-Za-z0-9_\.]+)\s*(<=|>=|==|>|<)", cond)
        if m:
            feat, op = m.group(1), m.group(2)
            features.append(feat)
            op_features.append(f"{feat}{op}")
            families.append(feature_family(feat))
    return ";".join(sorted(set(features))), ";".join(sorted(set(op_features))), ";".join(sorted(set(families))), len(parts)


def add_reduced(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    parsed = d["added_filter_text_value_set"].apply(parse_filter_text) if "added_filter_text_value_set" in d.columns else pd.Series([("", "", "", 0)] * len(d))
    d["filter_feature_name_set"] = parsed.apply(lambda x: x[0])
    d["filter_operator_feature_set"] = parsed.apply(lambda x: x[1])
    d["filter_family_set"] = parsed.apply(lambda x: x[2])
    d["filter_condition_count"] = parsed.apply(lambda x: int(x[3]))
    d["filter_family_count"] = d["filter_family_set"].apply(lambda s: 0 if not str(s) else len(str(s).split(";")))
    # train_score_value_set is a semicolon separated list.
    def scores(s: Any) -> list[float]:
        vals = []
        for p in str(s).split(";"):
            try: vals.append(float(p))
            except Exception: pass
        return vals
    sc = d["train_score_value_set"].apply(scores) if "train_score_value_set" in d.columns else pd.Series([[]] * len(d))
    d["_score_mean"] = sc.apply(lambda xs: float(sum(xs) / len(xs)) if xs else math.nan)
    d["_score_range"] = sc.apply(lambda xs: float(max(xs) - min(xs)) if xs else math.nan)
    d["train_score_mean_bin_0_1"] = d["_score_mean"].apply(lambda v: bin_value(v, 0.1))
    d["train_score_mean_bin_0_25"] = d["_score_mean"].apply(lambda v: bin_value(v, 0.25))
    d["train_score_mean_bin_0_5"] = d["_score_mean"].apply(lambda v: bin_value(v, 0.5))
    d["train_score_range_bin_0_25"] = d["_score_range"].apply(lambda v: bin_value(v, 0.25))
    d["train_score_count"] = sc.apply(len)
    # Use last price from the value set as audit approximation matching 25C102 behavior.
    def last_price(s: Any) -> float:
        vals = []
        for p in str(s).split(";"):
            try: vals.append(float(p))
            except Exception: pass
        return vals[-1] if vals else math.nan
    ep = d["entry_price_value_set"].apply(last_price) if "entry_price_value_set" in d.columns else pd.Series([math.nan] * len(d))
    d["entry_price_bin_25"] = ep.apply(lambda v: bin_value(v, 25.0))
    d["entry_price_bin_50"] = ep.apply(lambda v: bin_value(v, 50.0))
    d["entry_price_bin_100"] = ep.apply(lambda v: bin_value(v, 100.0))
    d["entry_price_bin_250"] = ep.apply(lambda v: bin_value(v, 250.0))
    return d.drop(columns=[c for c in ["_score_mean", "_score_range"] if c in d.columns])


def rep_class(rep: str) -> str:
    if rep in RULE_REPS: return "rule_text_reduced"
    if rep in SCORE_REPS: return "train_score_reduced"
    if rep in PRICE_REPS: return "price_regime_review_only"
    return "unknown"


def count_collisions(df: pd.DataFrame, cols: list[str]) -> tuple[int, int, int, pd.DataFrame, pd.DataFrame]:
    g = df.groupby(cols, dropna=False).agg(rows=("top_row_index", "nunique"), top_profit_classes=("top_profit_class", "nunique"), top_profit_values=("top_profit_class", lambda s: ";".join(sorted(set(map(str, s)))))).reset_index()
    bad = g[g["top_profit_classes"] > 1].copy()
    if bad.empty:
        return 0, 0, int(g["top_profit_classes"].max()) if not g.empty else 0, bad, pd.DataFrame()
    keys = bad[cols].drop_duplicates()
    cr = df.merge(keys, on=cols, how="inner")
    return int(len(bad)), int(bad["rows"].sum()), int(g["top_profit_classes"].max()), bad, cr


def main() -> int:
    created = datetime.now(timezone.utc).isoformat()
    out = out_dir()
    paths = {n: find_file(n) for n in INPUTS}
    inv = inventory(paths)
    s102 = read_json(paths["25c102_summary.json"])
    base = read_csv(paths["25c102_candidate_feature_rows.csv"])
    disc = read_csv(paths["25c102_candidate_discriminator_summary.csv"])
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    upstream_ok = s102.get("status") == EXPECTED_25C102_STATUS
    base_ok = len(base) == EXPECTED_FEATURE_ROWS
    disc_ok = len(disc) == EXPECTED_DISC_ROWS
    feat = add_reduced(base) if not base.empty else pd.DataFrame()
    rows, cgroups, crows = [], [], []
    if not feat.empty:
        for rep in ALL_REPS:
            if rep not in feat.columns: continue
            cols = PREFIX_SIG + [rep]
            missing = [c for c in cols if c not in feat.columns]
            if missing:
                cg, rr, mx, bad, cr = 999, 999, 999, pd.DataFrame(), pd.DataFrame()
            else:
                cg, rr, mx, bad, cr = count_collisions(feat, cols)
            uv = int(feat[rep].nunique(dropna=False)) if rep in feat.columns else 0
            rows.append({"representation": rep, "representation_class": rep_class(rep), "collision_groups": cg, "rows_in_collision_groups": rr, "max_top_profit_classes": mx, "unique_values": uv, "unique_ratio": uv / len(feat) if len(feat) else None, "resolves_full_set": cg == 0, "human_review_required": cg == 0})
            if not bad.empty:
                bad.insert(0, "representation", rep)
                cgroups.append(bad)
                cr.insert(0, "representation", rep)
                crows.append(cr)
    summary_df = pd.DataFrame(rows).sort_values(["resolves_full_set", "representation_class", "unique_ratio", "representation"], ascending=[False, True, True, True]) if rows else pd.DataFrame()
    cgdf = pd.concat(cgroups, ignore_index=True) if cgroups else pd.DataFrame()
    crdf = pd.concat(crows, ignore_index=True) if crows else pd.DataFrame()
    resolving = summary_df[summary_df["resolves_full_set"].astype(bool)] if not summary_df.empty else pd.DataFrame()
    rule_resolving = resolving[resolving["representation_class"].eq("rule_text_reduced")] if not resolving.empty else pd.DataFrame()
    score_resolving = resolving[resolving["representation_class"].eq("train_score_reduced")] if not resolving.empty else pd.DataFrame()
    price_resolving = resolving[resolving["representation_class"].eq("price_regime_review_only")] if not resolving.empty else pd.DataFrame()
    if not (inputs_ok and upstream_ok and base_ok and disc_ok):
        status = "REDUCED_DISCRIMINATOR_ROBUSTNESS_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif len(rule_resolving):
        status = "RULE_TEXT_REDUCED_DISCRIMINATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
    elif len(score_resolving):
        status = "TRAIN_SCORE_BIN_DISCRIMINATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
    elif len(price_resolving):
        status = "PRICE_REGIME_ONLY_DISCRIMINATOR_AUDIT_ONLY_LIVE_BLOCKED"
    else:
        status = "REDUCED_DISCRIMINATOR_FORMS_UNRESOLVED_AUDIT_ONLY_LIVE_BLOCKED"
    decision = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_25c102_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["candidate_feature_rows", len(base), EXPECTED_FEATURE_ROWS, "PASS" if base_ok else "FAIL"],
        ["candidate_discriminator_summary_rows", len(disc), EXPECTED_DISC_ROWS, "PASS" if disc_ok else "FAIL"],
        ["reduced_representations_tested", len(summary_df), ">0", "PASS" if len(summary_df) else "FAIL"],
        ["reduced_resolving_representations", len(resolving), 0, "REVIEW" if len(resolving) else "BLOCKED"],
        ["rule_text_reduced_resolving", len(rule_resolving), 0, "REVIEW" if len(rule_resolving) else "BLOCKED"],
        ["train_score_reduced_resolving", len(score_resolving), 0, "REVIEW" if len(score_resolving) else "BLOCKED"],
        ["price_regime_resolving", len(price_resolving), 0, "INFO" if len(price_resolving) else "PASS"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
        ["source_recovery_approved", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([
        ["B103-001", "inputs/25c102", "CLOSED" if inputs_ok and upstream_ok and base_ok else "OPEN", "HARD", "25C102 candidate artifacts must be present."],
        ["B103-002", "rule_text_reduced_discriminator", "REVIEW" if len(rule_resolving) else "OPEN", "HARD", "Reduced rule-text representation resolves collisions; human review required." if len(rule_resolving) else "Reduced rule-text representations do not resolve full-set collisions."],
        ["B103-003", "score_or_price_overfit", "OPEN" if len(score_resolving) or len(price_resolving) else "CLOSED", "HARD", "Score/price representations are diagnostics only; do not promote."],
        ["B103-004", "representative_profit_binding", "OPEN", "HARD", "Profit representative source remains unresolved."],
        ["B103-005", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked."],
        ["B103-006", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 is auxiliary-only and not used."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summ = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "source_recovery_approved": False, "upstream_25c102_ok": upstream_ok, "inputs_present": inputs_ok, "candidate_feature_rows": int(len(base)), "candidate_discriminator_summary_rows": int(len(disc)), "reduced_representations_tested": int(len(summary_df)), "reduced_resolving_representations": int(len(resolving)), "rule_text_reduced_resolving": int(len(rule_resolving)), "train_score_reduced_resolving": int(len(score_resolving)), "price_regime_resolving": int(len(price_resolving)), "rule_resolving_candidates": clean(rule_resolving.to_dict("records")), "score_resolving_candidates": clean(score_resolving.to_dict("records")), "price_resolving_candidates": clean(price_resolving.to_dict("records")), "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "external_actions": ACTIONS}
    inv.to_csv(out / "25c103_input_inventory.csv", index=False, encoding="utf-8-sig")
    feat.to_csv(out / "25c103_reduced_feature_rows.csv", index=False, encoding="utf-8-sig")
    summary_df.to_csv(out / "25c103_reduced_discriminator_summary.csv", index=False, encoding="utf-8-sig")
    cgdf.to_csv(out / "25c103_reduced_collision_groups.csv", index=False, encoding="utf-8-sig")
    crdf.to_csv(out / "25c103_reduced_collision_rows.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c103_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c103_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c103_summary.json", summ)
    report = "\n".join(["# GOLD V2 25C103 reduced discriminator robustness audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Decision matrix", md(decision), "", "## Reduced discriminator summary", md(summary_df), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- reduced discriminator uniqueness not promoted", "- score/price regime diagnostics not promoted", "- A002 not used", "- source recovery not approved", "- live evaluator/final signal/external actions remain OFF", "- NO_SIGNAL must not notify Discord"])
    (out / "GOLD_V2_25C103_REDUCED_DISCRIMINATOR_ROBUSTNESS_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs() / f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") or status.endswith("AUDIT_ONLY") else 2

if __name__ == "__main__":
    raise SystemExit(main())
