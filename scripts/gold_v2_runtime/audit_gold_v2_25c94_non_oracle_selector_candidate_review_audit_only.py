#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c94_non_oracle_selector_candidate_review_audit_only"
INPUTS = ["25c93_summary.json", "rr125_raw_signal_ledger.csv", "rr125_top_ledgers.csv", "gold_v2_13c_coreb_rr125_selected_top_ledgers.csv"]
EXPECTED_25C93_STATUS = "NON_ORACLE_COMPONENT_SELECTOR_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
EXPECTED_RAW_ROWS = 6834
EXPECTED_TOP_ROWS = 125
SELECTORS = ["latest_start", "closest_start"]
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_root() / "FX_OUTPUTS"


def out_dir() -> Path:
    path = fx_outputs() / OUT_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def find_file(name: str) -> Path | None:
    for candidate in [repo_root() / name, fx_outputs() / name]:
        if candidate.exists():
            return candidate
    for base in [fx_outputs(), repo_root()]:
        if base.exists():
            found = sorted(base.rglob(name))
            if found:
                return found[0]
    return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): safe_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [safe_json_value(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(safe_json_value(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def read_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_csv(path: Path | None) -> pd.DataFrame:
    return pd.read_csv(path) if path and path.exists() else pd.DataFrame()


def norm(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def inventory(paths: dict[str, Path | None]) -> pd.DataFrame:
    rows = []
    for name, path in paths.items():
        row = {"filename": name, "exists": bool(path and path.exists()), "path": str(path) if path else ""}
        if path and path.exists():
            row["bytes"] = path.stat().st_size
            row["sha256"] = sha256_file(path)
            if path.suffix.lower() == ".csv":
                row["row_count"] = len(pd.read_csv(path))
                row["columns"] = ";".join(pd.read_csv(path, nrows=0).columns)
        rows.append(row)
    return pd.DataFrame(rows)


def prep_raw(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "policy" not in df.columns:
        return pd.DataFrame()
    d = df[df["policy"].astype(str).eq("RR125_from_RR1_rules")].copy()
    d["entry_dt"] = pd.to_datetime(d["entry_time"], errors="coerce")
    d["exit_dt"] = pd.to_datetime(d["exit_time"], errors="coerce")
    d["profit_num"] = pd.to_numeric(d["profit_r"] if "profit_r" in d.columns else d.get("profit"), errors="coerce")
    for col in ["dataset", "direction", "origin_id", "candidate_id"]:
        d[col] = d[col].map(norm) if col in d.columns else ""
    return d.sort_values(["dataset", "direction", "entry_dt", "exit_dt", "candidate_id", "origin_id"]).reset_index(drop=True)


def prep_top(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "policy" not in df.columns or "filter" not in df.columns:
        return pd.DataFrame()
    d = df[df["policy"].astype(str).eq("RR125_from_RR1_rules") & df["filter"].astype(str).eq("same_count>=15")].copy()
    d["entry_dt"] = pd.to_datetime(d["entry_time"], errors="coerce")
    for col in ["same_count", "source_rule_count", "unique_origins", "profit"]:
        d[col + "_num"] = pd.to_numeric(d.get(col), errors="coerce")
    for col in ["dataset", "top_direction", "top_candidate_id", "cluster_id"]:
        d[col] = d[col].map(norm) if col in d.columns else ""
    return d.sort_values(["dataset", "entry_dt", "cluster_id"]).reset_index(drop=True)


def build_components(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames = []
    gap = pd.Timedelta(minutes=15)
    for _, group0 in raw.groupby(["dataset", "direction"], dropna=False):
        group = group0.sort_values(["entry_dt", "exit_dt", "candidate_id", "origin_id"]).copy()
        cid = -1
        prev = None
        ids = []
        for _, row in group.iterrows():
            ent = row["entry_dt"]
            if cid < 0 or prev is None or pd.isna(ent) or (ent - prev) > gap:
                cid += 1
            prev = ent
            ids.append(cid)
        group["recon_cluster_id"] = ids
        group["selected_component_id"] = group["dataset"].astype(str) + "|" + group["direction"].astype(str) + "|entry_gap15|" + group["recon_cluster_id"].astype(str)
        frames.append(group)
    raw2 = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if raw2.empty:
        return raw2, pd.DataFrame()
    ct = raw2.groupby(["dataset", "direction", "recon_cluster_id", "selected_component_id"], dropna=False).agg(
        component_count=("entry_time", "size"), component_unique_origins=("origin_id", "nunique"),
        component_min_entry=("entry_dt", "min"), component_max_entry=("entry_dt", "max"), component_max_exit=("exit_dt", "max"),
        component_profit_sum=("profit_num", "sum"), component_profit_mean=("profit_num", "mean"), component_profit_median=("profit_num", "median"),
        component_profit_min=("profit_num", "min"), component_profit_max=("profit_num", "max"),
        candidate_ids=("candidate_id", lambda s: ";".join(sorted({norm(v) for v in s if norm(v)}))),
        origin_ids=("origin_id", lambda s: ";".join(sorted({norm(v) for v in s if norm(v)}))),
    ).reset_index()
    return raw2, ct


def covering(ct: pd.DataFrame, tr: pd.Series) -> pd.DataFrame:
    c = ct[ct["dataset"].astype(str).eq(str(tr["dataset"])) & ct["direction"].astype(str).eq(str(tr["top_direction"]))].copy()
    c = c[(c["component_min_entry"] <= tr["entry_dt"]) & (c["component_max_exit"] >= tr["entry_dt"])] if not c.empty else c
    if not c.empty:
        c["dist_start"] = (c["component_min_entry"] - tr["entry_dt"]).abs().dt.total_seconds() / 60.0
        center = c["component_min_entry"] + (c["component_max_exit"] - c["component_min_entry"]) / 2
        c["dist_center"] = (center - tr["entry_dt"]).abs().dt.total_seconds() / 60.0
    return c


def pick(c: pd.DataFrame, selector: str) -> pd.Series | None:
    if c.empty:
        return None
    if selector == "latest_start":
        return c.sort_values(["component_min_entry", "component_count", "dist_center"], ascending=[False, True, True]).iloc[0]
    return c.sort_values(["dist_start", "component_count", "dist_center"], ascending=[True, True, True]).iloc[0]


def num_eq(a: Any, b: Any) -> bool:
    try:
        af, bf = float(a), float(b)
        return (not math.isnan(af)) and (not math.isnan(bf)) and abs(af - bf) <= 1e-6
    except Exception:
        return False


def component_raw(raw2: pd.DataFrame, component_id: str) -> pd.DataFrame:
    return raw2[raw2["selected_component_id"].astype(str).eq(str(component_id))].copy()


def representative_values(rows: pd.DataFrame, top_candidate_id: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    tid = norm(top_candidate_id)
    subsets = {
        "candidate_id_eq_top_candidate_id": rows[rows["candidate_id"].eq(tid)],
        "origin_id_eq_top_candidate_id": rows[rows["origin_id"].eq(tid)],
        "candidate_or_origin_eq_top_candidate_id": rows[rows["candidate_id"].eq(tid) | rows["origin_id"].eq(tid)],
        "candidate_id_contains_top_candidate_id": rows[rows["candidate_id"].astype(str).str.contains(tid, regex=False, na=False)],
        "origin_id_contains_top_candidate_id": rows[rows["origin_id"].astype(str).str.contains(tid, regex=False, na=False)],
        "candidate_or_origin_contains_top_candidate_id": rows[rows["candidate_id"].astype(str).str.contains(tid, regex=False, na=False) | rows["origin_id"].astype(str).str.contains(tid, regex=False, na=False)],
    }
    for method, subset in subsets.items():
        out[method] = None if subset.empty else subset.sort_values(["entry_dt", "exit_dt", "candidate_id", "origin_id"]).iloc[0]["profit_num"]
    if rows.empty:
        return out
    ordered = rows.sort_values(["entry_dt", "exit_dt", "candidate_id", "origin_id"])
    out.update({
        "earliest_entry_raw_row": ordered.iloc[0]["profit_num"],
        "latest_entry_raw_row": ordered.iloc[-1]["profit_num"],
        "earliest_exit_raw_row": rows.sort_values(["exit_dt", "entry_dt"]).iloc[0]["profit_num"],
        "latest_exit_raw_row": rows.sort_values(["exit_dt", "entry_dt"]).iloc[-1]["profit_num"],
        "max_profit_raw_row": rows.sort_values(["profit_num", "entry_dt"], ascending=[False, True]).iloc[0]["profit_num"],
        "min_profit_raw_row": rows.sort_values(["profit_num", "entry_dt"], ascending=[True, True]).iloc[0]["profit_num"],
        "first_component_sort_raw_row": ordered.iloc[0]["profit_num"],
        "last_component_sort_raw_row": ordered.iloc[-1]["profit_num"],
        "profit_sum": rows["profit_num"].sum(),
        "profit_mean": rows["profit_num"].mean(),
        "profit_median": rows["profit_num"].median(),
        "profit_min": rows["profit_num"].min(),
        "profit_max": rows["profit_num"].max(),
        "profit_first": ordered.iloc[0]["profit_num"],
        "profit_last": ordered.iloc[-1]["profit_num"],
    })
    return out


def md(df: pd.DataFrame, n: int = 40) -> str:
    if df.empty:
        return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    created = datetime.now(timezone.utc).isoformat()
    out = out_dir()
    paths = {name: find_file(name) for name in INPUTS}
    inv = inventory(paths)
    s93 = read_json(paths["25c93_summary.json"])
    raw = prep_raw(read_csv(paths["rr125_raw_signal_ledger.csv"]))
    top = prep_top(read_csv(paths["rr125_top_ledgers.csv"]))
    direct = read_csv(paths["gold_v2_13c_coreb_rr125_selected_top_ledgers.csv"])
    raw2, ct = build_components(raw)

    component_rows, pair_rows, profit_rows, presence_rows = [], [], [], []
    selected: dict[tuple[int, str], str] = {}
    for idx, tr in top.iterrows():
        cands = covering(ct, tr)
        for selector in SELECTORS:
            chosen = pick(cands, selector)
            base = {"top_row_index": int(idx), "selector": selector, "dataset": tr["dataset"], "entry_time": tr["entry_time"], "cluster_id": tr["cluster_id"], "top_direction": tr["top_direction"], "top_candidate_id": tr["top_candidate_id"], "top_profit": tr["profit_num"], "covering_components": len(cands), "selected": chosen is not None}
            if chosen is None:
                base.update({"selected_component_id": "", "same_count_match": False, "source_rule_count_match": False, "unique_origins_match": False})
                component_rows.append(base)
                continue
            cid = str(chosen["selected_component_id"])
            selected[(int(idx), selector)] = cid
            tid = norm(tr["top_candidate_id"])
            cand_ids = str(chosen["candidate_ids"])
            orig_ids = str(chosen["origin_ids"])
            rows = component_raw(raw2, cid)
            base.update({"selected_component_id": cid, "component_min_entry": chosen["component_min_entry"], "component_max_entry": chosen["component_max_entry"], "component_max_exit": chosen["component_max_exit"], "component_count": int(chosen["component_count"]), "component_unique_origins": int(chosen["component_unique_origins"]), "candidate_ids": cand_ids, "origin_ids": orig_ids, "contains_top_candidate_candidate": tid in cand_ids.split(";"), "contains_top_candidate_origin": tid in orig_ids.split(";"), "contains_top_candidate_any": tid in cand_ids.split(";") or tid in orig_ids.split(";"), "same_count_match": int(chosen["component_count"]) == int(tr["same_count_num"]), "source_rule_count_match": int(chosen["component_count"]) == int(tr["source_rule_count_num"]), "unique_origins_match": int(chosen["component_unique_origins"]) == int(tr["unique_origins_num"])})
            component_rows.append(base)
            exact_profit_rows = rows[rows["profit_num"].apply(lambda v: num_eq(v, tr["profit_num"]))]
            presence_rows.append({"top_row_index": int(idx), "selector": selector, "entry_time": tr["entry_time"], "cluster_id": tr["cluster_id"], "top_candidate_id": tid, "top_profit": tr["profit_num"], "selected_component_id": cid, "component_raw_rows": len(rows), "top_profit_present_in_component_raw_rows": len(exact_profit_rows) > 0, "top_profit_present_count": len(exact_profit_rows), "deployable_by_itself": False})
            reps = representative_values(rows, tid)
            for method, value in reps.items():
                binding_type = "aggregation" if method.startswith("profit_") else "raw_row"
                profit_rows.append({"top_row_index": int(idx), "selector": selector, "binding_type": binding_type, "binding_method": method, "entry_time": tr["entry_time"], "cluster_id": tr["cluster_id"], "top_candidate_id": tid, "top_profit": tr["profit_num"], "selected_component_id": cid, "binding_found": value is not None, "selected_profit": value, "profit_match": num_eq(value, tr["profit_num"])})
        pair_rows.append({"top_row_index": int(idx), "dataset": tr["dataset"], "entry_time": tr["entry_time"], "cluster_id": tr["cluster_id"], "top_candidate_id": tr["top_candidate_id"], "latest_start_component_id": selected.get((int(idx), "latest_start"), ""), "closest_start_component_id": selected.get((int(idx), "closest_start"), ""), "same_component": bool(selected.get((int(idx), "latest_start"), "")) and selected.get((int(idx), "latest_start"), "") == selected.get((int(idx), "closest_start"), "")})

    comp_df = pd.DataFrame(component_rows)
    pair_df = pd.DataFrame(pair_rows)
    profit_df = pd.DataFrame(profit_rows)
    presence_df = pd.DataFrame(presence_rows)
    if profit_df.empty:
        psum = pd.DataFrame(columns=["selector", "binding_type", "binding_method", "rows", "binding_found_rows", "profit_match_rows", "full_profit_match"])
    else:
        psum = profit_df.groupby(["selector", "binding_type", "binding_method"], dropna=False).agg(rows=("top_row_index", "size"), binding_found_rows=("binding_found", "sum"), profit_match_rows=("profit_match", "sum")).reset_index()
        psum["binding_found_rows"] = psum["binding_found_rows"].astype(int)
        psum["profit_match_rows"] = psum["profit_match_rows"].astype(int)
        psum["full_profit_match"] = psum["profit_match_rows"].eq(len(top))
        psum = psum.sort_values(["profit_match_rows", "binding_found_rows"], ascending=[False, False])

    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    upstream_ok = s93.get("status") == EXPECTED_25C93_STATUS
    raw_ok = len(raw) == EXPECTED_RAW_ROWS
    top_ok = len(top) == EXPECTED_TOP_ROWS
    def count_ok(df: pd.DataFrame) -> bool:
        return len(df) == EXPECTED_TOP_ROWS and bool(df["selected"].all()) and int(df["same_count_match"].sum()) == EXPECTED_TOP_ROWS and int(df["source_rule_count_match"].sum()) == EXPECTED_TOP_ROWS and int(df["unique_origins_match"].sum()) == EXPECTED_TOP_ROWS
    latest_ok = count_ok(comp_df[comp_df["selector"].eq("latest_start")])
    closest_ok = count_ok(comp_df[comp_df["selector"].eq("closest_start")])
    pair_count = int(pair_df["same_component"].sum()) if not pair_df.empty else 0
    pair_ok = pair_count == EXPECTED_TOP_ROWS
    profit_ok = (not psum.empty) and bool(psum["full_profit_match"].any())
    presence_full = (not presence_df.empty) and bool((presence_df.groupby("selector")["top_profit_present_in_component_raw_rows"].sum() == EXPECTED_TOP_ROWS).any())

    if not (inputs_ok and upstream_ok and raw_ok and top_ok):
        status = "NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif not (latest_ok and closest_ok and pair_ok):
        status = "NON_ORACLE_SELECTOR_COUNT_REVIEW_FAILED_AUDIT_ONLY_LIVE_BLOCKED"
    elif not profit_ok:
        status = "NON_ORACLE_SELECTOR_COUNT_MATCHED_PROFIT_BINDING_BLOCKED_AUDIT_ONLY_LIVE_BLOCKED"
    else:
        status = "NON_ORACLE_SELECTOR_AND_PROFIT_BINDING_CANDIDATE_READY_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"

    decision = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_25c93_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["raw_rr125_rows", len(raw), EXPECTED_RAW_ROWS, "PASS" if raw_ok else "FAIL"],
        ["top125_rows", len(top), EXPECTED_TOP_ROWS, "PASS" if top_ok else "FAIL"],
        ["direct_historical_sot_rows", len(direct), EXPECTED_TOP_ROWS, "PASS" if len(direct) in [0, EXPECTED_TOP_ROWS] else "WARN"],
        ["latest_start_count_fields", latest_ok, True, "PASS" if latest_ok else "BLOCKED"],
        ["closest_start_count_fields", closest_ok, True, "PASS" if closest_ok else "BLOCKED"],
        ["latest_start_vs_closest_start_same_component", pair_count, EXPECTED_TOP_ROWS, "PASS" if pair_ok else "BLOCKED"],
        ["non_oracle_profit_binding_full_match", profit_ok, True, "PASS" if profit_ok else "BLOCKED"],
        ["top_profit_presence_full_diagnostic_only", presence_full, "diagnostic_only", "INFO"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
        ["source_recovery_approved", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([
        ["B94-001", "inputs/source-counts", "CLOSED" if inputs_ok and upstream_ok and raw_ok and top_ok else "OPEN", "HARD", "Inputs, 25C93 status, and source row counts must match."],
        ["B94-002", "selector_count_stability", "CLOSED" if latest_ok and closest_ok and pair_ok else "OPEN", "HARD", "Both selectors must match count fields and same component for all 125 rows."],
        ["B94-003", "representative_profit_binding", "CLOSED" if profit_ok else "OPEN", "HARD", "Profit/top_candidate_id binding must match without oracle logic."],
        ["B94-004", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked."],
        ["B94-005", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 is auxiliary-only and not used."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "source_recovery_approved": False, "component_family": "entry_gap", "gap_min": 15, "selectors_under_review": SELECTORS, "inputs_present": inputs_ok, "upstream_25c93_ok": upstream_ok, "raw_rr125_rows": int(len(raw)), "expected_raw_rr125_rows": EXPECTED_RAW_ROWS, "top125_rows": int(len(top)), "expected_top125_rows": EXPECTED_TOP_ROWS, "direct_historical_sot_rows": int(len(direct)), "latest_start_count_ok": latest_ok, "closest_start_count_ok": closest_ok, "latest_start_vs_closest_start_same_component": pair_count, "profit_binding_ok": profit_ok, "top_profit_presence_full_diagnostic_only": presence_full, "best_profit_binding_candidates": safe_json_value(psum[psum["full_profit_match"].eq(True)].head(20).to_dict("records") if not psum.empty else []), "coreb_historical_sot_report_allowed": True, "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "external_actions": ACTIONS}

    inv.to_csv(out / "25c94_input_inventory.csv", index=False, encoding="utf-8-sig")
    comp_df.to_csv(out / "25c94_selector_component_rows.csv", index=False, encoding="utf-8-sig")
    pair_df.to_csv(out / "25c94_selector_pair_stability.csv", index=False, encoding="utf-8-sig")
    psum.to_csv(out / "25c94_profit_binding_summary.csv", index=False, encoding="utf-8-sig")
    profit_df.to_csv(out / "25c94_profit_binding_rows.csv", index=False, encoding="utf-8-sig")
    presence_df.to_csv(out / "25c94_profit_presence_diagnostics.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c94_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c94_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c94_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C94 non-oracle selector candidate review audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Decision matrix", md(decision), "", "## Selector pair stability", md(pair_df), "", "## Profit binding summary", md(psum), "", "## Profit presence diagnostics", "Diagnostics only; stored top profit/raw presence is not source recovery approval by itself.", md(presence_df), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- no oracle matching promoted to live logic", "- A002 not used", "- source recovery not approved", "- live evaluator/final signal/external actions remain OFF", "- NO_SIGNAL must not notify Discord"])
    (out / "GOLD_V2_25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs() / f"{OUT_NAME}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") or status.endswith("AUDIT_ONLY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
