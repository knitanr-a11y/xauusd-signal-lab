#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25C80 local sync from 25C79 audit-only checkpoint.

This script does NOT advance the official local chain beyond 25C79.
It records that local official state remains 25C79 and checks whether the
files needed to replay/adopt the chat-side 25C80-25C89 evidence exist locally.

No Discord, MT5, AI API, live hook, live evaluator, or final signal action.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

STEP = "25C80_LOCAL_SYNC_FROM_25C79_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_25c80_local_sync_from_25c79_audit_only"
EXTERNAL_ACTIONS = {
    "discord_send_allowed": False,
    "mt5_order_allowed": False,
    "ai_api_allowed": False,
    "live_hook_allowed": False,
}

REQUIRED_FILES = [
    "gold_v2_13c_coreb_rr125_selected_top_ledgers.csv",
    "gold_v2_13c_coreb_final_sot_rows.csv",
    "gold_v2_final_portfolio_2025_2026_sot_ledger.csv",
    "rr125_top_ledgers.csv",
    "rr125_raw_signal_ledger.csv",
]

OPTIONAL_PRIOR_STATUS_FILES = [
    "02_25c79_summary.json",
    "gold_v2_25c79_a002_id_join_summary.json",
    "02_25c84_raw_rule_universe_replay_audit_summary.json",
    "02_25c89_coreb_direct_sot_parity_package_summary.json",
]


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


def safe_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def safe_read_csv(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


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
            "total_r": 0.0,
        }
    wins = int((s > 0).sum())
    losses = int((s < 0).sum())
    be = int((s == 0).sum())
    gross_win = float(s[s > 0].sum())
    gross_loss = float(-s[s < 0].sum())
    pf = math.inf if gross_loss == 0 and gross_win > 0 else (gross_win / gross_loss if gross_loss > 0 else math.nan)
    return {
        "count": int(len(s)),
        "wins": wins,
        "losses": losses,
        "breakeven": be,
        "win_rate": float(wins / len(s)),
        "pf": float(pf) if not math.isnan(pf) else math.nan,
        "total_r": float(s.sum()),
    }


def file_inventory() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name in REQUIRED_FILES + OPTIONAL_PRIOR_STATUS_FILES:
        p = find_file(name)
        row: dict[str, Any] = {
            "filename": name,
            "required": name in REQUIRED_FILES,
            "exists": bool(p),
            "path": str(p) if p else "",
        }
        if p:
            row["bytes"] = p.stat().st_size
            row["sha256"] = sha256_file(p)
            if p.suffix.lower() == ".csv":
                try:
                    head = pd.read_csv(p, nrows=0)
                    row["columns"] = ";".join(map(str, head.columns))
                except Exception as exc:
                    row["read_error"] = repr(exc)
        rows.append(row)
    return pd.DataFrame(rows)


def coreb_metric_check(selected_path: Path | None) -> pd.DataFrame:
    df = safe_read_csv(selected_path)
    if df.empty or "profit" not in df.columns:
        return pd.DataFrame([{"scope": "CoreB_13C_selected_top_ledgers", "status": "MISSING_OR_UNREADABLE"}])
    rows: list[dict[str, Any]] = []
    for dataset, group in df.groupby("dataset", dropna=False):
        m = metric(pd.to_numeric(group["profit"], errors="coerce"))
        m.update(scope="CoreB_13C_selected_top_ledgers", dataset=dataset, profit_column="profit")
        rows.append(m)
    m = metric(pd.to_numeric(df["profit"], errors="coerce"))
    m.update(scope="CoreB_13C_selected_top_ledgers", dataset="total", profit_column="profit")
    rows.append(m)
    return pd.DataFrame(rows)


def top_filter_check(top_path: Path | None, selected_path: Path | None) -> pd.DataFrame:
    top = safe_read_csv(top_path)
    selected = safe_read_csv(selected_path)
    if top.empty or selected.empty:
        return pd.DataFrame([{"check": "top_filter", "status": "MISSING_INPUT"}])
    target = top[(top.get("policy", "").astype(str) == "RR125_from_RR1_rules") & (top.get("filter", "").astype(str) == "same_count>=15")].copy()
    key_cols = [c for c in ["dataset", "entry_time", "cluster_id", "top_candidate_id", "profit", "filter", "policy"] if c in target.columns and c in selected.columns]
    if not key_cols:
        return pd.DataFrame([{"check": "top_filter", "status": "NO_COMMON_KEYS", "target_rows": len(target), "selected_rows": len(selected)}])
    a = set(map(tuple, target[key_cols].astype(str).to_numpy()))
    b = set(map(tuple, selected[key_cols].astype(str).to_numpy()))
    return pd.DataFrame([
        {"check": "top_filter_rows", "observed": int(len(target)), "expected": 125, "status": "PASS" if len(target) == 125 else "REVIEW"},
        {"check": "selected_rows", "observed": int(len(selected)), "expected": 125, "status": "PASS" if len(selected) == 125 else "REVIEW"},
        {"check": "selected_equals_top_filter_set_diff", "observed": int(len(a.symmetric_difference(b))), "expected": 0, "status": "PASS" if not a.symmetric_difference(b) else "REVIEW", "key_cols": ";".join(key_cols)},
    ])


def prior_status_check() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name in OPTIONAL_PRIOR_STATUS_FILES:
        p = find_file(name)
        j = safe_json(p)
        rows.append({
            "filename": name,
            "exists": bool(p),
            "status": j.get("status"),
            "step": j.get("step"),
            "path": str(p) if p else "",
        })
    return pd.DataFrame(rows)


def make_report(summary: dict[str, Any], inv: pd.DataFrame, metrics_df: pd.DataFrame, top_check: pd.DataFrame, prior: pd.DataFrame) -> str:
    def md(df: pd.DataFrame, max_rows: int = 50) -> str:
        if df.empty:
            return "_No rows._"
        d = df.head(max_rows).fillna("").copy()
        lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
        for _, r in d.iterrows():
            lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
        return "\n".join(lines)

    return "\n".join([
        "# GOLD V2 25C80 local sync from 25C79 audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Status: `{summary['status']}`",
        "",
        "## Official state",
        "",
        "Local official chain remains at `25C79_A002_ID_JOIN_BLOCKED` until later chat-side evidence is replayed locally.",
        "",
        "## Required file inventory",
        md(inv[["filename", "required", "exists", "path"]]),
        "",
        "## CoreB direct SOT metric check",
        md(metrics_df),
        "",
        "## Top-ledger filter check",
        md(top_check),
        "",
        "## Prior status files found locally",
        md(prior),
        "",
        "## Decision",
        "",
        f"- local_official_status: `{summary['local_official_status']}`",
        f"- later_chat_evidence_adopted: `{summary['later_chat_evidence_adopted']}`",
        f"- coreb_direct_sot_inputs_ready: `{summary['coreb_direct_sot_inputs_ready']}`",
        f"- next_recommended_step: `{summary['next_recommended_step']}`",
        "",
        "## Safety",
        "",
        "- audit_only: true",
        "- Discord/MT5/AI/live_hook/final_signal: false",
    ])


def main() -> int:
    out = out_dir()
    created = datetime.now(timezone.utc).isoformat()
    inv = file_inventory()
    selected_path = find_file("gold_v2_13c_coreb_rr125_selected_top_ledgers.csv")
    top_path = find_file("rr125_top_ledgers.csv")
    metrics_df = coreb_metric_check(selected_path)
    top_check = top_filter_check(top_path, selected_path)
    prior = prior_status_check()

    required_ready = bool(inv[inv["required"]]["exists"].all()) if not inv.empty else False
    top_pass = bool((top_check.get("status", pd.Series(dtype=str)) == "PASS").all()) if not top_check.empty else False
    metric_pass = False
    if not metrics_df.empty and "count" in metrics_df.columns:
        total = metrics_df[metrics_df.get("dataset").astype(str) == "total"]
        metric_pass = bool(len(total) and int(total.iloc[0].get("count", -1)) == 125)

    status = "LOCAL_SYNC_CHECKPOINT_READY_COREB_INPUTS_PRESENT_AUDIT_ONLY" if required_ready and top_pass and metric_pass else "LOCAL_SYNC_CHECKPOINT_REVIEW_REQUIRED_AUDIT_ONLY"
    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "local_official_status": "25C79_A002_ID_JOIN_BLOCKED",
        "later_chat_evidence_adopted": False,
        "required_files_ready": bool(required_ready),
        "top_filter_check_pass": bool(top_pass),
        "coreb_metric_total_125": bool(metric_pass),
        "coreb_direct_sot_inputs_ready": bool(required_ready and top_pass and metric_pass),
        "external_actions": EXTERNAL_ACTIONS,
        "final_signal_allowed": False,
        "live_evaluator_allowed": False,
        "next_recommended_step": "25C81_LOCAL_REPLAY_OR_25C89_COREB_DIRECT_SOT_LOCAL_REPLAY_AUDIT_ONLY" if required_ready else "RESTORE_REQUIRED_INPUT_FILES_BEFORE_LOCAL_SYNC",
    }

    inv.to_csv(out / "25c80_local_sync_required_file_inventory.csv", index=False, encoding="utf-8-sig")
    metrics_df.to_csv(out / "25c80_coreb_direct_sot_metric_check.csv", index=False, encoding="utf-8-sig")
    top_check.to_csv(out / "25c80_top_ledger_filter_check.csv", index=False, encoding="utf-8-sig")
    prior.to_csv(out / "25c80_prior_status_files_check.csv", index=False, encoding="utf-8-sig")
    (out / "25c80_local_sync_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    (out / "GOLD_V2_25C80_LOCAL_SYNC_FROM_25C79_AUDIT_ONLY_REPORT.md").write_text(make_report(summary, inv, metrics_df, top_check, prior), encoding="utf-8")

    print(json.dumps({"status": status, "output_dir": str(out), "local_official_status": summary["local_official_status"]}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if required_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
