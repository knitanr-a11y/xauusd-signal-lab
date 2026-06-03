#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GOLD V2 CoreA/CoreB RR1.25 overlap audit-only evaluator.

This script does NOT call AI APIs, Discord, MT5 order APIs, or any live hooks.
It only reads prebuilt audit ledgers and evaluates the agreed policy:

    CoreA = fold4_rules + ABC + CAP5
    CoreB = RR125_from_RR1_rules + same_count>=15 + CAP3

Overlap policy:

    CoreA standalone: lot 1.0
    CoreB standalone: lot 1.0
    CoreA BUY + CoreB BUY same entry time: confluence.
      Evaluate extra CoreB exposure of 0.0, 0.5, and 1.0.
      Profit = CoreA profit + extra_coreb_exposure * CoreB profit.

CoreB is BUY-only in the current RR1.25 probe, so opposite-direction conflicts
are tracked but should normally be zero or rare.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


CORE_A_VIEW = "CORE_A"
CORE_B_VIEW = "CORE_B_RR125"
CONFLUENCE_VIEW = "CONFLUENCE_COREA_COREB_EXACT_BUY"


@dataclass
class InputAudit:
    name: str
    path: str
    rows: int
    status: str
    message: str


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate GOLD V2 CoreA/CoreB RR125 overlap audit-only policy")
    parser.add_argument(
        "--core-input-dir",
        default=None,
        help="Directory with abc_stack_cap_2025_fold4_cluster_ledger.csv and abc_stack_cap_2026_cluster_ledger.csv",
    )
    parser.add_argument(
        "--rr125-input-dir",
        default=None,
        help="Directory with rr125_top_ledgers.csv from gold_v2_rr125_second_core_probe_outputs",
    )
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--coreb-policy", default="RR125_from_RR1_rules")
    parser.add_argument("--coreb-filter", default="same_count>=15")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    if len(root.parents) >= 2:
        return root.parents[1]
    return root.parent


def default_core_input_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_ABC_stack_cap_2025_2026_validation_outputs"


def default_rr125_input_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_rr125_second_core_probe_outputs"


def default_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_coreA_coreB_rr125_overlap_audit_only"


def to_number(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def metrics(values: Iterable[float]) -> Dict[str, float]:
    vals = pd.Series(list(values)).dropna().astype(float).to_numpy()
    n = int(len(vals))
    if n == 0:
        return {
            "count": 0,
            "win_rate": math.nan,
            "pf": math.nan,
            "total_r": 0.0,
            "avg_r": math.nan,
            "worst": math.nan,
            "best": math.nan,
            "maxdd": 0.0,
            "max_loss_streak": 0,
            "gross_win": 0.0,
            "gross_loss": 0.0,
        }

    gross_win = float(vals[vals > 0].sum())
    gross_loss = float(-vals[vals < 0].sum())
    if gross_loss == 0 and gross_win > 0:
        pf = math.inf
    elif gross_loss > 0:
        pf = gross_win / gross_loss
    else:
        pf = math.nan

    eq = np.cumsum(vals)
    previous_peak = np.maximum.accumulate(np.r_[0.0, eq[:-1]])
    dd = np.maximum(previous_peak - eq, 0.0)

    streak = 0
    max_streak = 0
    for v in vals:
        if v < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    return {
        "count": n,
        "win_rate": float((vals > 0).mean()),
        "pf": float(pf) if not math.isnan(pf) else math.nan,
        "total_r": float(vals.sum()),
        "avg_r": float(vals.mean()),
        "worst": float(vals.min()),
        "best": float(vals.max()),
        "maxdd": float(dd.max()) if len(dd) else 0.0,
        "max_loss_streak": int(max_streak),
        "gross_win": gross_win,
        "gross_loss": gross_loss,
    }


def audit_file(name: str, path: Path, df: Optional[pd.DataFrame], required: Sequence[str]) -> InputAudit:
    if df is None:
        return InputAudit(name, str(path), 0, "ERROR", "file not found or unreadable")
    missing = [c for c in required if c not in df.columns]
    if missing:
        return InputAudit(name, str(path), int(len(df)), "ERROR", f"missing columns: {missing}")
    if len(df) == 0:
        return InputAudit(name, str(path), 0, "ERROR", "no rows")
    return InputAudit(name, str(path), int(len(df)), "OK", "")


def read_csv(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    return pd.read_csv(path)


def normalize_core(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    d = df.copy()
    if "signal_ABC" not in d.columns:
        if "signal_fixed_ABC" in d.columns:
            d["signal_ABC"] = d["signal_fixed_ABC"]
        elif "signal" in d.columns:
            d["signal_ABC"] = d["signal"]
        else:
            d["signal_ABC"] = "REJECT"
    d["signal_ABC"] = d["signal_ABC"].fillna("REJECT").astype(str)

    core = d[d["signal_ABC"].ne("REJECT")].copy()
    core["entry_time"] = pd.to_datetime(core["top_entry_time"], errors="coerce")
    core["entry_month"] = core.get("entry_month", core["entry_time"].dt.to_period("M").astype(str))
    for c in ["profit_cap3_from_members", "profit_cap5_from_members"]:
        core[c] = to_number(core[c])
    core["profit_r"] = np.where(
        core["signal_ABC"].eq("A"),
        core["profit_cap5_from_members"],
        core["profit_cap3_from_members"],
    )
    out = core[["entry_time", "entry_month", "top_direction", "signal_ABC", "profit_r", "cluster_id"]].copy()
    out = out.rename(columns={"top_direction": "direction", "cluster_id": "source_cluster_id"})
    out["dataset"] = dataset
    out["source"] = "CORE_A"
    return out.sort_values("entry_time").reset_index(drop=True)


def normalize_coreb(rr: pd.DataFrame, dataset: str, policy: str, filter_name: str) -> pd.DataFrame:
    d = rr.copy()
    d = d[(d["dataset"].astype(str).eq(dataset)) & d["policy"].astype(str).eq(policy) & d["filter"].astype(str).eq(filter_name)].copy()
    d["entry_time"] = pd.to_datetime(d["entry_time"], errors="coerce")
    d["entry_month"] = d.get("entry_month", d["entry_time"].dt.to_period("M").astype(str))
    d["profit_r"] = to_number(d["profit"])
    out = d[["entry_time", "entry_month", "top_direction", "profit_r", "cluster_id", "same_count", "unique_origins", "top_candidate_id"]].copy()
    out = out.rename(columns={"top_direction": "direction", "cluster_id": "source_cluster_id"})
    out["dataset"] = dataset
    out["source"] = "CORE_B_RR125"
    return out.sort_values("entry_time").reset_index(drop=True)


def build_overlap_portfolio(core: pd.DataFrame, coreb: pd.DataFrame, extra_coreb: float) -> pd.DataFrame:
    core = core.copy()
    coreb = coreb.copy()
    core["key"] = core["entry_time"].astype("int64").astype(str) + "|" + core["direction"].astype(str)
    coreb["key"] = coreb["entry_time"].astype("int64").astype(str) + "|" + coreb["direction"].astype(str)
    overlap_keys = set(core["key"]) & set(coreb["key"])
    coreb_by_key = coreb.drop_duplicates("key").set_index("key")

    rows: List[Dict[str, object]] = []

    for _, r in core.iterrows():
        key = r["key"]
        if key in overlap_keys:
            br = coreb_by_key.loc[key]
            source = f"CONFLUENCE_EXTRA_{extra_coreb}"
            profit = float(r["profit_r"]) + float(extra_coreb) * float(br["profit_r"])
            rr_profit = float(br["profit_r"])
            rr_source_cluster_id = br.get("source_cluster_id", np.nan)
        else:
            source = "CORE_A_ONLY"
            profit = float(r["profit_r"])
            rr_profit = np.nan
            rr_source_cluster_id = np.nan
        rows.append(
            {
                "dataset": r["dataset"],
                "entry_time": r["entry_time"],
                "entry_month": r["entry_month"],
                "direction": r["direction"],
                "source": source,
                "profit_r": profit,
                "core_profit_r": float(r["profit_r"]),
                "coreb_profit_r": rr_profit,
                "core_cluster_id": r.get("source_cluster_id", np.nan),
                "coreb_cluster_id": rr_source_cluster_id,
                "extra_coreb_exposure": extra_coreb,
            }
        )

    for _, r in coreb.iterrows():
        if r["key"] in overlap_keys:
            continue
        rows.append(
            {
                "dataset": r["dataset"],
                "entry_time": r["entry_time"],
                "entry_month": r["entry_month"],
                "direction": r["direction"],
                "source": "CORE_B_ONLY",
                "profit_r": float(r["profit_r"]),
                "core_profit_r": np.nan,
                "coreb_profit_r": float(r["profit_r"]),
                "core_cluster_id": np.nan,
                "coreb_cluster_id": r.get("source_cluster_id", np.nan),
                "extra_coreb_exposure": extra_coreb,
            }
        )

    return pd.DataFrame(rows).sort_values("entry_time").reset_index(drop=True)


def summarize_portfolio(portfolio: pd.DataFrame, view: str) -> Dict[str, object]:
    m = metrics(portfolio["profit_r"])
    m.update({"dataset": portfolio["dataset"].iloc[0] if len(portfolio) else "", "view": view})
    return m


def summarize_monthly(portfolio: pd.DataFrame, view: str) -> pd.DataFrame:
    rows = []
    for (dataset, month), g in portfolio.groupby(["dataset", "entry_month"]):
        m = metrics(g["profit_r"])
        m.update({"dataset": dataset, "month": month, "view": view})
        rows.append(m)
    return pd.DataFrame(rows)


def summarize_source(portfolio: pd.DataFrame, view: str) -> pd.DataFrame:
    rows = []
    for (dataset, source), g in portfolio.groupby(["dataset", "source"]):
        m = metrics(g["profit_r"])
        m.update({"dataset": dataset, "source": source, "view": view})
        rows.append(m)
    return pd.DataFrame(rows)


def simple_markdown_table(df: pd.DataFrame, cols: Sequence[str]) -> str:
    if df.empty:
        return "_No rows._"
    view = df[[c for c in cols if c in df.columns]].copy()
    if "win_rate" in view.columns:
        view["win_rate"] = to_number(view["win_rate"]) * 100.0
    for c in ["pf", "total_r", "avg_r", "worst", "best", "maxdd", "gross_win", "gross_loss"]:
        if c in view.columns:
            view[c] = to_number(view[c])
    headers = list(view.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in view.iterrows():
        cells = []
        for h in headers:
            v = row[h]
            if pd.isna(v):
                cells.append("")
            elif isinstance(v, (float, np.floating)):
                if math.isinf(float(v)):
                    cells.append("inf" if v > 0 else "-inf")
                else:
                    cells.append(f"{float(v):.2f}")
            else:
                cells.append(str(v).replace("|", "\\|"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_report(path: Path, summary: pd.DataFrame, monthly: pd.DataFrame, source: pd.DataFrame, audits: List[InputAudit], policy: Dict[str, object]) -> None:
    lines = []
    lines.append("# GOLD V2 CoreA/CoreB RR125 overlap audit-only report")
    lines.append("")
    lines.append(f"Created UTC: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## Policy")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(policy, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## Input audit")
    lines.append(simple_markdown_table(pd.DataFrame([asdict(a) for a in audits]), ["name", "path", "rows", "status", "message"]))
    lines.append("")
    lines.append("## Aggregate")
    lines.append(simple_markdown_table(summary, ["dataset", "view", "count", "win_rate", "pf", "total_r", "avg_r", "worst", "maxdd", "max_loss_streak"]))
    lines.append("")
    lines.append("## Source breakdown")
    lines.append(simple_markdown_table(source, ["dataset", "view", "source", "count", "win_rate", "pf", "total_r", "worst", "maxdd"]))
    lines.append("")
    lines.append("## Monthly")
    lines.append(simple_markdown_table(monthly, ["dataset", "month", "view", "count", "win_rate", "pf", "total_r", "worst", "maxdd", "max_loss_streak"]))
    lines.append("")
    lines.append("This is audit-only. It does not approve runtime, Discord, or MT5 order integration.")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    core_input_dir = Path(args.core_input_dir).expanduser().resolve() if args.core_input_dir else default_core_input_dir()
    rr125_input_dir = Path(args.rr125_input_dir).expanduser().resolve() if args.rr125_input_dir else default_rr125_input_dir()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    core25_path = core_input_dir / "abc_stack_cap_2025_fold4_cluster_ledger.csv"
    core26_path = core_input_dir / "abc_stack_cap_2026_cluster_ledger.csv"
    rr125_path = rr125_input_dir / "rr125_top_ledgers.csv"

    core25_raw = read_csv(core25_path)
    core26_raw = read_csv(core26_path)
    rr125_raw = read_csv(rr125_path)

    audits = [
        audit_file("core_2025_fold4", core25_path, core25_raw, ["top_entry_time", "signal_ABC", "profit_cap3_from_members", "profit_cap5_from_members"]),
        audit_file("core_2026", core26_path, core26_raw, ["top_entry_time", "profit_cap3_from_members", "profit_cap5_from_members"]),
        audit_file("rr125_top_ledgers", rr125_path, rr125_raw, ["dataset", "policy", "filter", "entry_time", "profit", "top_direction"]),
    ]

    for a in audits:
        print(f"[INPUT] {a.name}: status={a.status} rows={a.rows} path={a.path}")
        if a.message:
            print(f"        {a.message}")

    if args.strict and any(a.status != "OK" for a in audits):
        print("[ERROR] Strict mode: input audit failed", file=sys.stderr)
        return 2
    if any(a.status != "OK" for a in audits):
        print("[ERROR] Missing or invalid input", file=sys.stderr)
        return 2

    datasets = [
        ("2025", normalize_core(core25_raw, "2025")),
        ("2026", normalize_core(core26_raw, "2026")),
    ]

    summary_rows: List[Dict[str, object]] = []
    monthly_frames: List[pd.DataFrame] = []
    source_frames: List[pd.DataFrame] = []
    ledgers: List[pd.DataFrame] = []

    policy = {
        "CoreA": "fold4_rules + ABC + CAP5",
        "CoreB": f"{args.coreb_policy} + {args.coreb_filter} + CAP3",
        "overlap": "same entry_time and same direction; profit = CoreA + extra_coreb_exposure * CoreB",
        "extra_coreb_exposure_values": [0.0, 0.5, 1.0],
        "conflict": "CoreA SELL + CoreB BUY exact-time conflict is not added as confluence; CoreB is skipped on exact same opposite-time if present",
    }

    rr125_all = rr125_raw.copy()
    rr125_all["dataset"] = rr125_all["dataset"].astype(str)

    for dataset, core in datasets:
        coreb = normalize_coreb(rr125_all, dataset, args.coreb_policy, args.coreb_filter)
        summary_rows.append({**metrics(core["profit_r"]), "dataset": dataset, "view": CORE_A_VIEW})
        summary_rows.append({**metrics(coreb["profit_r"]), "dataset": dataset, "view": CORE_B_VIEW})

        confluence = core.merge(
            coreb[["entry_time", "direction", "profit_r"]].rename(columns={"profit_r": "coreb_profit_r"}),
            on=["entry_time", "direction"],
            how="inner",
        )
        summary_rows.append({**metrics(confluence["profit_r"] if len(confluence) else []), "dataset": dataset, "view": CONFLUENCE_VIEW, "overlap_count": int(len(confluence))})

        for extra in [0.0, 0.5, 1.0]:
            view = f"CORE_A_PLUS_CORE_B_DEDUP_EXTRA_{extra}"
            portfolio = build_overlap_portfolio(core, coreb, extra)
            portfolio["view"] = view
            ledgers.append(portfolio)
            summary_rows.append(summarize_portfolio(portfolio, view))
            monthly_frames.append(summarize_monthly(portfolio, view))
            source_frames.append(summarize_source(portfolio, view))

    summary = pd.DataFrame(summary_rows).sort_values(["dataset", "view"]).reset_index(drop=True)
    monthly = pd.concat(monthly_frames, ignore_index=True) if monthly_frames else pd.DataFrame()
    source = pd.concat(source_frames, ignore_index=True) if source_frames else pd.DataFrame()
    ledger = pd.concat(ledgers, ignore_index=True) if ledgers else pd.DataFrame()

    summary.to_csv(output_dir / "coreA_coreB_rr125_overlap_summary.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(output_dir / "coreA_coreB_rr125_overlap_monthly.csv", index=False, encoding="utf-8-sig")
    source.to_csv(output_dir / "coreA_coreB_rr125_overlap_source_breakdown.csv", index=False, encoding="utf-8-sig")
    ledger.to_csv(output_dir / "coreA_coreB_rr125_overlap_ledger.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([asdict(a) for a in audits]).to_csv(output_dir / "coreA_coreB_rr125_overlap_input_audit.csv", index=False, encoding="utf-8-sig")

    json_summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "AUDIT_ONLY",
        "core_input_dir": str(core_input_dir),
        "rr125_input_dir": str(rr125_input_dir),
        "output_dir": str(output_dir),
        "policy": policy,
        "input_audit": [asdict(a) for a in audits],
        "aggregate": summary.replace({np.nan: None, np.inf: "inf", -np.inf: "-inf"}).to_dict(orient="records"),
    }
    (output_dir / "coreA_coreB_rr125_overlap_summary.json").write_text(json.dumps(json_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(output_dir / "GOLD_V2_COREA_COREB_RR125_OVERLAP_AUDIT_ONLY_REPORT.md", summary, monthly, source, audits, policy)

    print(f"[DONE] output_dir={output_dir}")
    print(summary[["dataset", "view", "count", "win_rate", "pf", "total_r", "worst", "maxdd", "max_loss_streak"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
