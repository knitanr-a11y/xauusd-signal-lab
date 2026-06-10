#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract compact paste-ready review files from GOLD V3 Stage45 audit outputs.

This helper is audit-only. It reads existing Stage45 output CSV/JSON files and
creates small files that can be pasted into chat when upload limits are reached.
It does not call MT5, Discord, AI API, live hook, or final signal code.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def fmt_pct(x: Any) -> str:
    try:
        return f"{float(x) * 100:.2f}%"
    except Exception:
        return ""


def fmt_num(x: Any, nd: int = 2) -> str:
    try:
        return f"{float(x):,.{nd}f}"
    except Exception:
        return ""


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True)
    p.add_argument("--mode-label", default="closed_valid")
    args = p.parse_args()

    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    summary = read_json(out / "gold_v3_45_hv_sibling_strict_gate_summary.json")
    exp = read_csv(out / "gold_v3_45_hv_sibling_gate_experiment_summary.csv")
    monthly = read_csv(out / "gold_v3_45_hv_sibling_strict_gate_monthly_summary.csv")
    cand = read_csv(out / "gold_v3_45_hv_sibling_strict_gate_candidate_summary.csv")

    chosen = pd.DataFrame()
    if not exp.empty and "experiment" in exp.columns:
        chosen = exp[exp["experiment"].astype(str).eq("fixed_8_plus_hv_siblings_strict_rolling_health_gate")].copy()
        if chosen.empty:
            chosen = exp.tail(1).copy()

    lines: list[str] = []
    lines.append("GOLD V3 45 PASTE_ME_REVIEW_SUMMARY")
    lines.append(f"mode_label: {args.mode_label}")
    lines.append(f"status: {summary.get('status', '')}")
    lines.append(f"htf_asof: {summary.get('htf_asof', '')}")
    lines.append(f"start_jst: {summary.get('start_jst', '')}")
    lines.append(f"end_jst: {summary.get('end_jst', '')}")
    lines.append(f"complete_horizon_only: {summary.get('complete_horizon_only', '')}")
    lines.append(f"hv_rule: {summary.get('hv_rule', '')}")
    lines.append(f"health_gate: {summary.get('health_gate', {})}")
    lines.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    lines.append("")

    if not chosen.empty:
        r = chosen.iloc[0]
        lines.append("MAIN_RESULT_FIXED8_PLUS_HV_STRICT_GATE")
        lines.append(f"trades: {int(r.get('trades', 0))}")
        lines.append(f"win_rate: {fmt_pct(r.get('win_rate'))}")
        lines.append(f"profit_factor: {fmt_num(r.get('profit_factor'), 3)}")
        lines.append(f"sum_result_usd: {fmt_num(r.get('sum_result_usd'), 2)}")
        lines.append(f"avg_result_usd: {fmt_num(r.get('avg_result_usd'), 2)}")
        lines.append(f"max_drawdown_usd: {fmt_num(r.get('max_drawdown_usd'), 2)}")
        lines.append(f"loss_months: {int(r.get('loss_months', 0))}")
        lines.append("")

    if not exp.empty:
        cols = [c for c in ["experiment", "trades", "win_rate", "profit_factor", "sum_result_usd", "max_drawdown_usd", "loss_months"] if c in exp.columns]
        small = exp[cols].copy()
        if "win_rate" in small.columns:
            small["win_rate_pct"] = small["win_rate"].map(fmt_pct)
        lines.append("EXPERIMENT_SUMMARY")
        lines.append(small.to_string(index=False))
        lines.append("")
        small.to_csv(out / "gold_v3_45_PASTE_ME_experiment_summary.csv", index=False, encoding="utf-8-sig")

    if not monthly.empty:
        cols = [c for c in ["entry_month", "trades", "win_rate", "profit_factor", "sum_result_usd", "max_drawdown_usd"] if c in monthly.columns]
        msmall = monthly[cols].copy()
        if "win_rate" in msmall.columns:
            msmall["win_rate_pct"] = msmall["win_rate"].map(fmt_pct)
        lines.append("MONTHLY_SUMMARY")
        lines.append(msmall.to_string(index=False))
        lines.append("")
        msmall.to_csv(out / "gold_v3_45_PASTE_ME_monthly_summary.csv", index=False, encoding="utf-8-sig")

    if not cand.empty:
        cols = [c for c in ["candidate_label", "hv_sibling", "trades", "win_rate", "profit_factor", "sum_result_usd", "max_drawdown_usd"] if c in cand.columns]
        csmall = cand[cols].copy()
        if "trades" in csmall.columns:
            csmall = csmall.sort_values(["sum_result_usd", "trades"], ascending=[False, False]).head(12)
        if "win_rate" in csmall.columns:
            csmall["win_rate_pct"] = csmall["win_rate"].map(fmt_pct)
        lines.append("TOP_CANDIDATE_SUMMARY_BY_SUM_RESULT_USD")
        lines.append(csmall.to_string(index=False))
        lines.append("")
        csmall.to_csv(out / "gold_v3_45_PASTE_ME_top_candidate_summary.csv", index=False, encoding="utf-8-sig")

    paste = "\n".join(lines).rstrip() + "\n"
    (out / "gold_v3_45_PASTE_ME_REVIEW_SUMMARY.txt").write_text(paste, encoding="utf-8")

    print("[PASTE_ME_CREATED]")
    print(out / "gold_v3_45_PASTE_ME_REVIEW_SUMMARY.txt")
    print(out / "gold_v3_45_PASTE_ME_experiment_summary.csv")
    print(out / "gold_v3_45_PASTE_ME_monthly_summary.csv")
    print(out / "gold_v3_45_PASTE_ME_top_candidate_summary.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
