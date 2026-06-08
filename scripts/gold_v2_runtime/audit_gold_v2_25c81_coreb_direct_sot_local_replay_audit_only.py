#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25C81: CoreB direct SOT local replay audit-only.

Corrected local replay:
- RR bucket accepts both RR125 and RR1.25 textual forms.
- Final SOT joins normalize CoreB numeric keys so 5 and 5.0 match.
- A002 is deliberately not used for CoreB WR/PF or performance.

No Discord, MT5, AI API, live hook, live evaluator enablement, or final signal.
"""
from __future__ import annotations

import hashlib
import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

STEP = "25C81_COREB_DIRECT_SOT_LOCAL_REPLAY_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_25c81_coreb_direct_sot_local_replay_audit_only"
EXTERNAL_ACTIONS = {
    "discord_send_allowed": False,
    "mt5_order_allowed": False,
    "ai_api_allowed": False,
    "live_hook_allowed": False,
}

INPUTS = {
    "selected_top_ledgers": "gold_v2_13c_coreb_rr125_selected_top_ledgers.csv",
    "coreb_final_sot_rows": "gold_v2_13c_coreb_final_sot_rows.csv",
    "final_portfolio_sot": "gold_v2_final_portfolio_2025_2026_sot_ledger.csv",
    "rr125_top_ledgers": "rr125_top_ledgers.csv",
    "rr125_raw_signal_ledger": "rr125_raw_signal_ledger.csv",
    "local_sync_summary": "25c80_local_sync_summary.json",
}

COREB_KEY_COLUMNS = ["dataset", "entry_time", "coreb_cluster_id", "coreb_profit_r"]
TOP_KEY_COLUMNS = ["dataset", "entry_time", "cluster_id", "top_candidate_id", "profit", "filter", "policy"]
RR125_ACCEPTED = {"RR125", "RR1.25", "1.25", "1.250000", "125"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_root() / "FX_OUTPUTS"


def out_dir() -> Path:
    out = fx_outputs() / OUT_DIR_NAME
    out.mkdir(parents=True, exist_ok=True)
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_file(filename: str) -> Path | None:
    base = fx_outputs()
    direct = base / filename
    if direct.exists():
        return direct
    if base.exists():
        matches = sorted(base.rglob(filename))
        if matches:
            return matches[0]
    return None


def read_csv(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def clean_json(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): clean_json(v) for k, v in x.items()}
    if isinstance(x, list):
        return [clean_json(v) for v in x]
    if isinstance(x, float):
        if math.isnan(x):
            return None
        if math.isinf(x):
            return "inf" if x > 0 else "-inf"
        return x
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    return x


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(clean_json(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def metric(values: Iterable[float]) -> dict[str, Any]:
    s = pd.Series(list(values), dtype="float64").dropna()
    if s.empty:
        return {
            "count": 0,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "win_rate": math.nan,
            "pf": math.nan,
            "gross_win": 0.0,
            "gross_loss": 0.0,
            "total_r": 0.0,
            "avg_r": math.nan,
            "worst_r": math.nan,
            "best_r": math.nan,
        }
    wins = int((s > 0).sum())
    losses = int((s < 0).sum())
    breakeven = int((s == 0).sum())
    gross_win = float(s[s > 0].sum())
    gross_loss = float(-s[s < 0].sum())
    pf = math.inf if gross_loss == 0 and gross_win > 0 else (gross_win / gross_loss if gross_loss > 0 else math.nan)
    return {
        "count": int(len(s)),
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "win_rate": float(wins / len(s)),
        "pf": float(pf) if not math.isnan(pf) else math.nan,
        "gross_win": gross_win,
        "gross_loss": gross_loss,
        "total_r": float(s.sum()),
        "avg_r": float(s.mean()),
        "worst_r": float(s.min()),
        "best_r": float(s.max()),
    }


def input_inventory(paths: dict[str, Path | None]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label, p in paths.items():
        row: dict[str, Any] = {
            "input_label": label,
            "filename": INPUTS[label],
            "exists": bool(p and p.exists()),
            "path": str(p) if p else "",
        }
        if p and p.exists():
            row["bytes"] = p.stat().st_size
            row["sha256"] = sha256_file(p)
            if p.suffix.lower() == ".csv":
                try:
                    df0 = pd.read_csv(p, nrows=0)
                    row["row_count"] = int(len(pd.read_csv(p)))
                    row["columns"] = ";".join(df0.columns)
                except Exception as exc:
                    row["read_error"] = repr(exc)
        rows.append(row)
    return pd.DataFrame(rows)


def normalize_timestamp(s: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(s, errors="coerce")
    out = parsed.dt.strftime("%Y-%m-%d %H:%M:%S")
    return out.fillna(s.astype(str).str.strip())


def normalize_int_like(s: pd.Series) -> pd.Series:
    n = pd.to_numeric(s, errors="coerce")
    out = n.round(0).astype("Int64").astype(str)
    return out.where(n.notna(), s.astype(str).str.strip())


def normalize_float_like(s: pd.Series, ndigits: int = 6) -> pd.Series:
    n = pd.to_numeric(s, errors="coerce")
    out = n.round(ndigits).map(lambda v: f"{v:.{ndigits}f}" if pd.notna(v) else "")
    return out.where(n.notna(), s.astype(str).str.strip())


def normalize_top_key_frame(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if "dataset" in d.columns:
        d["dataset"] = normalize_int_like(d["dataset"])
    if "entry_time" in d.columns:
        d["entry_time"] = normalize_timestamp(d["entry_time"])
    for c in ["cluster_id", "top_candidate_id"]:
        if c in d.columns:
            d[c] = normalize_int_like(d[c])
    if "profit" in d.columns:
        d["profit"] = normalize_float_like(d["profit"], 6)
    for c in ["filter", "policy"]:
        if c in d.columns:
            d[c] = d[c].astype(str).str.strip()
    return d


def normalize_coreb_key_frame(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if "dataset" in d.columns:
        d["dataset"] = normalize_int_like(d["dataset"])
    if "entry_time" in d.columns:
        d["entry_time"] = normalize_timestamp(d["entry_time"])
    if "coreb_cluster_id" in d.columns:
        d["coreb_cluster_id"] = normalize_int_like(d["coreb_cluster_id"])
    if "coreb_profit_r" in d.columns:
        d["coreb_profit_r"] = normalize_float_like(d["coreb_profit_r"], 6)
    return d


def key_set(df: pd.DataFrame, cols: list[str]) -> set[tuple[str, ...]]:
    if df.empty or any(c not in df.columns for c in cols):
        return set()
    return set(map(tuple, df[cols].astype(str).to_numpy()))


def build_coreb_metrics(selected: pd.DataFrame) -> pd.DataFrame:
    if selected.empty or "profit" not in selected.columns:
        return pd.DataFrame([{"scope": "CoreB_13C_selected_top_ledgers", "status": "MISSING_OR_UNREADABLE"}])
    rows: list[dict[str, Any]] = []
    for dataset, g in selected.groupby("dataset", dropna=False):
        m = metric(pd.to_numeric(g["profit"], errors="coerce"))
        m.update(scope="CoreB_13C_selected_top_ledgers", dataset=str(dataset), profit_column="profit")
        rows.append(m)
    m = metric(pd.to_numeric(selected["profit"], errors="coerce"))
    m.update(scope="CoreB_13C_selected_top_ledgers", dataset="total", profit_column="profit")
    rows.append(m)
    return pd.DataFrame(rows)


def rr125_mask(series: pd.Series) -> pd.Series:
    normalized = series.astype(str).str.strip().str.upper().str.replace("_", "", regex=False)
    accepted = {v.upper().replace("_", "") for v in RR125_ACCEPTED}
    return normalized.isin(accepted)


def top_filter_parity(selected: pd.DataFrame, top: pd.DataFrame) -> pd.DataFrame:
    if selected.empty or top.empty:
        return pd.DataFrame([{"check_id": "C81-T000", "check": "input_present", "status": "FAIL", "detail": "selected or top missing"}])

    target = top[(top["policy"].astype(str).eq("RR125_from_RR1_rules")) & (top["filter"].astype(str).eq("same_count>=15"))].copy()
    key_cols = [c for c in TOP_KEY_COLUMNS if c in selected.columns and c in target.columns]
    selected_set = key_set(normalize_top_key_frame(selected), key_cols)
    target_set = key_set(normalize_top_key_frame(target), key_cols)
    diff = selected_set.symmetric_difference(target_set)

    same_count_num = pd.to_numeric(selected.get("same_count"), errors="coerce") if "same_count" in selected.columns else pd.Series(dtype="float64")
    rr_ok = rr125_mask(selected["rr_bucket"]) if "rr_bucket" in selected.columns else pd.Series([False] * len(selected))

    return pd.DataFrame([
        {"check_id": "C81-T001", "check": "selected_rows", "observed": int(len(selected)), "expected": 125, "status": "PASS" if len(selected) == 125 else "FAIL"},
        {"check_id": "C81-T002", "check": "top_filter_rows", "observed": int(len(target)), "expected": 125, "status": "PASS" if len(target) == 125 else "FAIL"},
        {"check_id": "C81-T003", "check": "selected_equals_top_filter_set_diff", "observed": int(len(diff)), "expected": 0, "status": "PASS" if not diff and key_cols else "FAIL", "key_cols": ";".join(key_cols)},
        {"check_id": "C81-T004", "check": "all_buy", "observed": int(selected.get("top_direction", pd.Series(dtype=str)).astype(str).str.upper().eq("BUY").sum()), "expected": 125, "status": "PASS" if "top_direction" in selected.columns and selected["top_direction"].astype(str).str.upper().eq("BUY").all() else "FAIL"},
        {"check_id": "C81-T005", "check": "all_rr125_or_rr1_25", "observed": int(rr_ok.sum()), "expected": 125, "status": "PASS" if len(rr_ok) == len(selected) and bool(rr_ok.all()) else "FAIL", "accepted_values": ";".join(sorted(RR125_ACCEPTED))},
        {"check_id": "C81-T006", "check": "same_count_min15", "observed": int((same_count_num >= 15).sum()) if not same_count_num.empty else 0, "expected": 125, "status": "PASS" if not same_count_num.empty and (same_count_num >= 15).all() else "FAIL"},
    ])


def final_sot_join_parity(selected: pd.DataFrame, coreb_final: pd.DataFrame, final_portfolio: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if selected.empty:
        return pd.DataFrame([{"check_id": "C81-F000", "check": "selected_present", "status": "FAIL"}])

    selected_key = selected.rename(columns={"cluster_id": "coreb_cluster_id", "profit": "coreb_profit_r"}).copy()
    selected_set = key_set(normalize_coreb_key_frame(selected_key), COREB_KEY_COLUMNS)

    final_set = key_set(normalize_coreb_key_frame(coreb_final), COREB_KEY_COLUMNS)
    inter_final = selected_set.intersection(final_set)
    rows.append({
        "check_id": "C81-F001",
        "check": "selected_rows_in_13c_final_sot_by_normalized_coreb_key",
        "observed": int(len(inter_final)),
        "expected": 125,
        "status": "PASS" if len(inter_final) == 125 else "FAIL",
        "key_cols": ";".join(COREB_KEY_COLUMNS),
    })
    rows.append({
        "check_id": "C81-F002",
        "check": "13c_final_sot_coreb_key_rows_in_selected",
        "observed": int(len(final_set.intersection(selected_set))),
        "expected": 125,
        "status": "PASS" if len(final_set.intersection(selected_set)) == 125 else "FAIL",
        "key_cols": ";".join(COREB_KEY_COLUMNS),
    })

    if not final_portfolio.empty and all(c in final_portfolio.columns for c in COREB_KEY_COLUMNS):
        fp_coreb = final_portfolio[final_portfolio["coreb_cluster_id"].notna() & final_portfolio["coreb_profit_r"].notna()].copy()
        fp_set = key_set(normalize_coreb_key_frame(fp_coreb), COREB_KEY_COLUMNS)
        rows.append({
            "check_id": "C81-F003",
            "check": "selected_rows_in_final_portfolio_coreb_rows_by_normalized_coreb_key",
            "observed": int(len(selected_set.intersection(fp_set))),
            "expected": 125,
            "status": "PASS" if len(selected_set.intersection(fp_set)) == 125 else "FAIL",
            "key_cols": ";".join(COREB_KEY_COLUMNS),
        })
        rows.append({
            "check_id": "C81-F004",
            "check": "final_portfolio_coreb_rows_in_selected_by_normalized_coreb_key",
            "observed": int(len(fp_set.intersection(selected_set))),
            "expected": 125,
            "status": "PASS" if len(fp_set.intersection(selected_set)) == 125 else "FAIL",
            "key_cols": ";".join(COREB_KEY_COLUMNS),
        })
    else:
        rows.append({"check_id": "C81-F003", "check": "final_portfolio_coreb_key_present", "status": "FAIL"})

    component_counts = coreb_final.get("component", pd.Series(dtype=str)).astype(str).value_counts().to_dict() if not coreb_final.empty and "component" in coreb_final.columns else {}
    rows.append({
        "check_id": "C81-F005",
        "check": "13c_final_sot_component_coreb_only",
        "observed": int(component_counts.get("CORE_B_ONLY", 0)),
        "expected": 117,
        "status": "PASS" if int(component_counts.get("CORE_B_ONLY", 0)) == 117 else "REVIEW",
    })
    rows.append({
        "check_id": "C81-F006",
        "check": "13c_final_sot_component_corea_coreb_confluence",
        "observed": int(component_counts.get("CORE_A_CORE_B_CONFLUENCE", 0)),
        "expected": 8,
        "status": "PASS" if int(component_counts.get("CORE_A_CORE_B_CONFLUENCE", 0)) == 8 else "REVIEW",
    })
    return pd.DataFrame(rows)


def readiness_matrix(all_pass: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["CoreB_direct_sot_metrics", "READY" if all_pass else "REVIEW", "CoreB 125 selected top-ledger metrics recomputed locally."],
        ["CoreB_topledger_filter_parity", "PASS" if all_pass else "REVIEW", "Selected 125 rows equal rr125_top_ledgers RR125_from_RR1_rules / same_count>=15 if checks pass."],
        ["CoreB_final_sot_join", "PASS" if all_pass else "REVIEW", "CoreB-specific normalized key: dataset+entry_time+coreb_cluster_id+coreb_profit_r."],
        ["A002_in_coreb_main_path", "DEMOTED", "A002 is not used for CoreB WR/PF."],
        ["CoreB_live_evaluator", "BLOCKED", "Cluster representative logic still missing."],
        ["live_final_signal", "OFF", "No external/final actions."],
    ], columns=["gate", "status", "detail"])


def guardrail_matrix() -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, "PASS"],
        ["a002_used_for_coreb_metrics", False, "PASS"],
        ["discord_send_allowed", False, "PASS"],
        ["mt5_order_allowed", False, "PASS"],
        ["ai_api_allowed", False, "PASS"],
        ["live_hook_allowed", False, "PASS"],
        ["live_evaluator_allowed", False, "PASS"],
        ["final_signal_allowed", False, "PASS"],
    ], columns=["guardrail", "value", "status"])


def markdown_table(df: pd.DataFrame, max_rows: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    d = df.head(max_rows).fillna("").copy()
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def build_report(summary: dict[str, Any], inv: pd.DataFrame, metrics_df: pd.DataFrame, top_df: pd.DataFrame, final_df: pd.DataFrame, ready_df: pd.DataFrame, guard_df: pd.DataFrame) -> str:
    return "\n".join([
        "# GOLD V2 25C81 CoreB direct SOT local replay audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Status: `{summary['status']}`",
        "",
        "## Official state",
        "",
        f"- previous_local_official_status: `{summary['previous_local_official_status']}`",
        f"- a002_used_for_coreb_metrics: `{summary['a002_used_for_coreb_metrics']}`",
        "",
        "## Input inventory",
        markdown_table(inv[["input_label", "filename", "exists", "path"]]),
        "",
        "## CoreB direct metrics",
        markdown_table(metrics_df),
        "",
        "## Top-ledger filter parity",
        markdown_table(top_df),
        "",
        "## Final SOT join parity",
        markdown_table(final_df),
        "",
        "## Readiness",
        markdown_table(ready_df),
        "",
        "## Guardrails",
        markdown_table(guard_df),
        "",
        "## Important",
        "",
        "This corrected replay accepts RR1.25 as the local rr_bucket label for RR125 and normalizes CoreB numeric join keys so integer and float representations match. CoreB live evaluator remains blocked because same_count/cluster representative logic is not recovered.",
    ])


def status_all_pass(df: pd.DataFrame) -> bool:
    if df.empty or "status" not in df.columns:
        return False
    return bool((df["status"].astype(str) == "PASS").all())


def main() -> int:
    out = out_dir()
    created = datetime.now(timezone.utc).isoformat()
    paths = {label: find_file(filename) for label, filename in INPUTS.items()}
    inv = input_inventory(paths)

    selected = read_csv(paths["selected_top_ledgers"])
    coreb_final = read_csv(paths["coreb_final_sot_rows"])
    final_portfolio = read_csv(paths["final_portfolio_sot"])
    top = read_csv(paths["rr125_top_ledgers"])
    sync = read_json(paths["local_sync_summary"])

    metrics_df = build_coreb_metrics(selected)
    top_parity = top_filter_parity(selected, top)
    final_parity = final_sot_join_parity(selected, coreb_final, final_portfolio)

    required_inputs_present = bool(inv["exists"].all()) if not inv.empty else False
    sync_ready = bool(sync.get("coreb_direct_sot_inputs_ready") is True and sync.get("local_official_status") == "25C79_A002_ID_JOIN_BLOCKED")
    top_pass = status_all_pass(top_parity)
    final_pass = status_all_pass(final_parity)
    metric_total = metrics_df[metrics_df.get("dataset", pd.Series(dtype=str)).astype(str).eq("total")] if not metrics_df.empty and "dataset" in metrics_df.columns else pd.DataFrame()
    metrics_pass = bool(len(metric_total) and int(metric_total.iloc[0].get("count", -1)) == 125)

    all_pass = bool(required_inputs_present and sync_ready and top_pass and final_pass and metrics_pass)
    status = "COREB_DIRECT_SOT_LOCAL_REPLAY_PASSED_AUDIT_ONLY_LIVE_BLOCKED" if all_pass else "COREB_DIRECT_SOT_LOCAL_REPLAY_REVIEW_REQUIRED_AUDIT_ONLY"

    ready_df = readiness_matrix(all_pass)
    guard_df = guardrail_matrix()

    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "previous_local_official_status": sync.get("local_official_status"),
        "sync_ready": sync_ready,
        "required_inputs_present": required_inputs_present,
        "top_filter_parity_pass": top_pass,
        "final_sot_join_parity_pass": final_pass,
        "metrics_total_125": metrics_pass,
        "coreb_direct_sot_local_official_ready": all_pass,
        "a002_used_for_coreb_metrics": False,
        "a002_role": "DEMOTED_AUXILIARY_ONLY",
        "coreb_live_evaluator_allowed": False,
        "final_signal_allowed": False,
        "external_actions": EXTERNAL_ACTIONS,
        "next_recommended_step": "25C82_LOCAL_COREB_REPORT_PACKAGE_OR_CLUSTER_LOGIC_RECOVERY_AUDIT_ONLY" if all_pass else "REVIEW_25C81_LOCAL_REPLAY_FAILURES",
    }

    inv.to_csv(out / "25c81_input_inventory.csv", index=False, encoding="utf-8-sig")
    metrics_df.to_csv(out / "25c81_coreb_direct_metrics.csv", index=False, encoding="utf-8-sig")
    top_parity.to_csv(out / "25c81_top_filter_parity.csv", index=False, encoding="utf-8-sig")
    final_parity.to_csv(out / "25c81_final_sot_join_parity.csv", index=False, encoding="utf-8-sig")
    ready_df.to_csv(out / "25c81_readiness_matrix.csv", index=False, encoding="utf-8-sig")
    guard_df.to_csv(out / "25c81_guardrail_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c81_summary.json", summary)
    (out / "GOLD_V2_25C81_COREB_DIRECT_SOT_LOCAL_REPLAY_AUDIT_ONLY_REPORT.md").write_text(build_report(summary, inv, metrics_df, top_parity, final_parity, ready_df, guard_df), encoding="utf-8")

    zip_path = fx_outputs() / "gold_v2_25c81_coreb_direct_sot_local_replay_audit_only.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            z.write(p, arcname=p.name)

    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
