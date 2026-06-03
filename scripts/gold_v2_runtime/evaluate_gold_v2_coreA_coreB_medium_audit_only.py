#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GOLD V2 CoreA + CoreB RR1.25 + MEDIUM audit-only evaluator.

This script is audit-only. It does not call AI APIs, Discord, MT5, or any live hooks.

Policy:
  HIGH_A: CoreA = fold4_rules + ABC + CAP5
  HIGH_B: CoreB = RR125_from_RR1_rules + same_count>=15 + CAP3
  HIGH_CONFLUENCE: CoreA BUY + CoreB BUY exact same entry/direction,
                    profit = CoreA + extra_coreb_exposure * CoreB.
  MEDIUM: RANGE96_REFINED, VOL_TRMEAN32_REFINED, TIER2_HVT.

Precedence:
  CoreA/CoreB > MEDIUM.
  If MEDIUM has the same entry_time as CoreA/CoreB, skip MEDIUM.
  If MEDIUM candidates share the same entry_time + direction, keep one by priority:
    RANGE96_REFINED > VOL_TRMEAN32_REFINED > TIER2_HVT.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

MEDIUM_COMPONENTS = ["RANGE96_REFINED", "VOL_TRMEAN32_REFINED", "TIER2_HVT"]
MEDIUM_PRIORITY = {name: i for i, name in enumerate(MEDIUM_COMPONENTS)}
DATASET_MAP = {"2025": "2025_fold4", "2026": "2026_WF"}


@dataclass
class InputAudit:
    name: str
    path: str
    rows: int
    status: str
    message: str


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate GOLD V2 CoreA/CoreB/MEDIUM audit-only policy")
    parser.add_argument("--core-input-dir", default=None)
    parser.add_argument("--rr125-input-dir", default=None)
    parser.add_argument("--medium-input-dir", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--coreb-policy", default="RR125_from_RR1_rules")
    parser.add_argument("--coreb-filter", default="same_count>=15")
    parser.add_argument("--extra-coreb-exposure", type=float, default=0.5)
    parser.add_argument("--include-origin010-watch", action="store_true", help="Also include ORIGIN010_REFINED as WATCH/extra medium")
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


def default_medium_input_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_coreb_refined_probe_outputs"


def default_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_coreA_coreB_medium_audit_only"


def read_csv(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    return pd.read_csv(path)


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


def normalize_core(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    d = df.copy()
    if "signal_ABC" not in d.columns:
        if "signal_fixed_ABC" in d.columns:
            d["signal_ABC"] = d["signal_fixed_ABC"]
        elif "signal" in d.columns:
            d["signal_ABC"] = d["signal"]
        else:
            d["signal_ABC"] = "REJECT"
    core = d[d["signal_ABC"].fillna("REJECT").astype(str).ne("REJECT")].copy()
    core["entry_time"] = pd.to_datetime(core["top_entry_time"], errors="coerce")
    core["entry_month"] = core.get("entry_month", core["entry_time"].dt.to_period("M").astype(str))
    for c in ["profit_cap3_from_members", "profit_cap5_from_members"]:
        core[c] = to_number(core[c])
    core["profit_r"] = np.where(
        core["signal_ABC"].astype(str).eq("A"),
        core["profit_cap5_from_members"],
        core["profit_cap3_from_members"],
    )
    out = core[["entry_time", "entry_month", "top_direction", "signal_ABC", "profit_r", "cluster_id"]].copy()
    out = out.rename(columns={"top_direction": "direction", "cluster_id": "source_cluster_id"})
    out["dataset"] = dataset
    out["source"] = "CORE_A"
    return out.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)


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
    return out.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)


def normalize_medium(refined: pd.DataFrame, dataset: str, include_origin010: bool = False) -> pd.DataFrame:
    source_dataset = DATASET_MAP[dataset]
    components = list(MEDIUM_COMPONENTS)
    if include_origin010:
        components.append("ORIGIN010_REFINED")
    d = refined[(refined["dataset"].astype(str).eq(source_dataset)) & refined["component"].astype(str).isin(components)].copy()
    d["entry_time"] = pd.to_datetime(d["top_entry_time"], errors="coerce")
    d["entry_month"] = d.get("entry_month", d["entry_time"].dt.to_period("M").astype(str))
    profit = to_number(d.get("profit", pd.Series([np.nan] * len(d))))
    selected = to_number(d.get("selected_profit_r", pd.Series([np.nan] * len(d))))
    d["profit_r"] = profit.fillna(selected)
    d["priority"] = d["component"].map({**MEDIUM_PRIORITY, "ORIGIN010_REFINED": 99}).fillna(99)
    out = d[["entry_time", "entry_month", "top_direction", "profit_r", "cluster_id", "component", "priority"]].copy()
    out = out.rename(columns={"top_direction": "direction", "cluster_id": "source_cluster_id", "component": "refined_rule"})
    out["dataset"] = dataset
    out["source"] = "MEDIUM_" + out["refined_rule"].astype(str)
    return out.dropna(subset=["entry_time"]).sort_values(["entry_time", "direction", "priority"]).reset_index(drop=True)


def build_high_portfolio(core: pd.DataFrame, coreb: pd.DataFrame, extra_coreb: float) -> pd.DataFrame:
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
            rows.append({
                "dataset": r["dataset"], "entry_time": r["entry_time"], "entry_month": r["entry_month"],
                "direction": r["direction"], "source": "CORE_A_CORE_B_CONFLUENCE",
                "profit_r": float(r["profit_r"]) + float(extra_coreb) * float(br["profit_r"]),
                "core_profit_r": float(r["profit_r"]), "coreb_profit_r": float(br["profit_r"]),
                "medium_profit_r": np.nan, "core_cluster_id": r.get("source_cluster_id", np.nan),
                "coreb_cluster_id": br.get("source_cluster_id", np.nan), "medium_cluster_id": np.nan,
                "extra_coreb_exposure": extra_coreb,
            })
        else:
            rows.append({
                "dataset": r["dataset"], "entry_time": r["entry_time"], "entry_month": r["entry_month"],
                "direction": r["direction"], "source": "CORE_A_ONLY", "profit_r": float(r["profit_r"]),
                "core_profit_r": float(r["profit_r"]), "coreb_profit_r": np.nan, "medium_profit_r": np.nan,
                "core_cluster_id": r.get("source_cluster_id", np.nan), "coreb_cluster_id": np.nan,
                "medium_cluster_id": np.nan, "extra_coreb_exposure": extra_coreb,
            })
    for _, r in coreb.iterrows():
        if r["key"] in overlap_keys:
            continue
        rows.append({
            "dataset": r["dataset"], "entry_time": r["entry_time"], "entry_month": r["entry_month"],
            "direction": r["direction"], "source": "CORE_B_ONLY", "profit_r": float(r["profit_r"]),
            "core_profit_r": np.nan, "coreb_profit_r": float(r["profit_r"]), "medium_profit_r": np.nan,
            "core_cluster_id": np.nan, "coreb_cluster_id": r.get("source_cluster_id", np.nan),
            "medium_cluster_id": np.nan, "extra_coreb_exposure": extra_coreb,
        })
    return pd.DataFrame(rows).sort_values("entry_time").reset_index(drop=True)


def dedup_medium_against_high(medium: pd.DataFrame, high: pd.DataFrame) -> pd.DataFrame:
    if medium.empty:
        return medium.copy()
    high_times = set(pd.to_datetime(high["entry_time"])) if len(high) else set()
    m = medium[~medium["entry_time"].isin(high_times)].copy()
    if m.empty:
        return m
    m = m.sort_values(["entry_time", "direction", "priority"]).drop_duplicates(["entry_time", "direction"], keep="first")
    return m.reset_index(drop=True)


def add_medium_rows(high: pd.DataFrame, medium: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in medium.iterrows():
        rows.append({
            "dataset": r["dataset"], "entry_time": r["entry_time"], "entry_month": r["entry_month"],
            "direction": r["direction"], "source": r["source"], "profit_r": float(r["profit_r"]),
            "core_profit_r": np.nan, "coreb_profit_r": np.nan, "medium_profit_r": float(r["profit_r"]),
            "core_cluster_id": np.nan, "coreb_cluster_id": np.nan, "medium_cluster_id": r.get("source_cluster_id", np.nan),
            "extra_coreb_exposure": high["extra_coreb_exposure"].iloc[0] if len(high) and "extra_coreb_exposure" in high.columns else np.nan,
        })
    return pd.concat([high, pd.DataFrame(rows)], ignore_index=True).sort_values("entry_time").reset_index(drop=True)


def summarize(df: pd.DataFrame, dataset: str, view: str) -> Dict[str, object]:
    m = metrics(df["profit_r"] if len(df) else [])
    m.update({"dataset": dataset, "view": view})
    return m


def group_summary(df: pd.DataFrame, by: Sequence[str], view: str) -> pd.DataFrame:
    rows = []
    if df.empty:
        return pd.DataFrame()
    for keys, g in df.groupby(list(by)):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {col: val for col, val in zip(by, keys)}
        row.update(metrics(g["profit_r"]))
        row["view"] = view
        rows.append(row)
    return pd.DataFrame(rows)


def simple_markdown_table(df: pd.DataFrame, cols: Sequence[str]) -> str:
    if df.empty:
        return "_No rows._"
    view = df[[c for c in cols if c in df.columns]].copy()
    if "win_rate" in view.columns:
        view["win_rate"] = to_number(view["win_rate"]) * 100.0
    headers = list(view.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in view.iterrows():
        cells = []
        for h in headers:
            v = row[h]
            if pd.isna(v):
                cells.append("")
            elif isinstance(v, (float, np.floating)):
                cells.append("inf" if math.isinf(float(v)) and v > 0 else ("-inf" if math.isinf(float(v)) else f"{float(v):.2f}"))
            else:
                cells.append(str(v).replace("|", "\\|"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_report(path: Path, policy: Dict[str, object], audits: List[InputAudit], summary: pd.DataFrame, source: pd.DataFrame, monthly: pd.DataFrame) -> None:
    lines = [
        "# GOLD V2 CoreA + CoreB RR125 + MEDIUM audit-only report", "",
        f"Created UTC: {datetime.now(timezone.utc).isoformat()}", "",
        "## Policy", "```json", json.dumps(policy, ensure_ascii=False, indent=2), "```", "",
        "## Input audit", simple_markdown_table(pd.DataFrame([asdict(a) for a in audits]), ["name", "path", "rows", "status", "message"]), "",
        "## Aggregate", simple_markdown_table(summary, ["dataset", "view", "count", "win_rate", "pf", "total_r", "avg_r", "worst", "maxdd", "max_loss_streak"]), "",
        "## Source breakdown", simple_markdown_table(source, ["dataset", "view", "source", "count", "win_rate", "pf", "total_r", "worst", "maxdd"]), "",
        "## Monthly", simple_markdown_table(monthly, ["dataset", "entry_month", "view", "count", "win_rate", "pf", "total_r", "worst", "maxdd", "max_loss_streak"]), "",
        "Audit-only. No live order execution, AI API calls, Discord, or MT5 integration.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    core_input_dir = Path(args.core_input_dir).expanduser().resolve() if args.core_input_dir else default_core_input_dir()
    rr125_input_dir = Path(args.rr125_input_dir).expanduser().resolve() if args.rr125_input_dir else default_rr125_input_dir()
    medium_input_dir = Path(args.medium_input_dir).expanduser().resolve() if args.medium_input_dir else default_medium_input_dir()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    core25_path = core_input_dir / "abc_stack_cap_2025_fold4_cluster_ledger.csv"
    core26_path = core_input_dir / "abc_stack_cap_2026_cluster_ledger.csv"
    rr125_path = rr125_input_dir / "rr125_top_ledgers.csv"
    refined_path = medium_input_dir / "coreb_refined_rule_ledgers.csv"

    core25_raw = read_csv(core25_path)
    core26_raw = read_csv(core26_path)
    rr125_raw = read_csv(rr125_path)
    refined_raw = read_csv(refined_path)

    audits = [
        audit_file("core_2025_fold4", core25_path, core25_raw, ["top_entry_time", "signal_ABC", "profit_cap3_from_members", "profit_cap5_from_members"]),
        audit_file("core_2026", core26_path, core26_raw, ["top_entry_time", "profit_cap3_from_members", "profit_cap5_from_members"]),
        audit_file("rr125_top_ledgers", rr125_path, rr125_raw, ["dataset", "policy", "filter", "entry_time", "profit", "top_direction"]),
        audit_file("coreb_refined_rule_ledgers", refined_path, refined_raw, ["dataset", "component", "top_entry_time", "top_direction", "selected_profit_r"]),
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

    policy = {
        "CoreA": "fold4_rules + ABC entry gate + CAP5 sizing",
        "CoreB": f"{args.coreb_policy} + {args.coreb_filter} + CAP3",
        "CoreA_CoreB_overlap": f"same entry_time and direction; profit = CoreA + {args.extra_coreb_exposure} * CoreB",
        "MEDIUM": MEDIUM_COMPONENTS + (["ORIGIN010_REFINED"] if args.include_origin010_watch else []),
        "precedence": "CoreA/CoreB exact entry_time first; skip MEDIUM at same entry_time; dedupe MEDIUM by entry_time+direction using priority RANGE96 > VOL_TRMEAN32 > TIER2_HVT",
    }

    summaries, source_frames, monthly_frames, ledgers, medium_standalone = [], [], [], [], []
    for dataset, core_raw in [("2025", core25_raw), ("2026", core26_raw)]:
        core = normalize_core(core_raw, dataset)
        coreb = normalize_coreb(rr125_raw, dataset, args.coreb_policy, args.coreb_filter)
        medium = normalize_medium(refined_raw, dataset, args.include_origin010_watch)
        high = build_high_portfolio(core, coreb, args.extra_coreb_exposure)
        medium_dedup = dedup_medium_against_high(medium, high)
        combined = add_medium_rows(high, medium_dedup)
        medium_standalone.append(medium_dedup)
        view_high = "CoreA+CoreB_dedup_extra0p5" if abs(args.extra_coreb_exposure - 0.5) < 1e-12 else f"CoreA+CoreB_dedup_extra{args.extra_coreb_exposure}"
        view_all = "CoreA+CoreB+MEDIUM_extra0p5" if abs(args.extra_coreb_exposure - 0.5) < 1e-12 else f"CoreA+CoreB+MEDIUM_extra{args.extra_coreb_exposure}"
        summaries.append(summarize(high, dataset, view_high))
        summaries.append(summarize(combined, dataset, view_all))
        source_frames.append(group_summary(combined, ["dataset", "source"], view_all))
        monthly_frames.append(group_summary(combined, ["dataset", "entry_month"], view_all))
        high["view"] = view_high
        combined["view"] = view_all
        ledgers.extend([high, combined])

    summary = pd.DataFrame(summaries).sort_values(["view", "dataset"]).reset_index(drop=True)
    source = pd.concat(source_frames, ignore_index=True) if source_frames else pd.DataFrame()
    monthly = pd.concat(monthly_frames, ignore_index=True) if monthly_frames else pd.DataFrame()
    ledger = pd.concat(ledgers, ignore_index=True) if ledgers else pd.DataFrame()
    medium_standalone_df = pd.concat(medium_standalone, ignore_index=True) if medium_standalone else pd.DataFrame()
    medium_summary = group_summary(medium_standalone_df, ["dataset", "source"], "MEDIUM_DEDUP_STANDALONE") if len(medium_standalone_df) else pd.DataFrame()

    summary.to_csv(output_dir / "coreA_coreB_medium_summary.csv", index=False, encoding="utf-8-sig")
    source.to_csv(output_dir / "coreA_coreB_medium_source_breakdown.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(output_dir / "coreA_coreB_medium_monthly.csv", index=False, encoding="utf-8-sig")
    ledger.to_csv(output_dir / "coreA_coreB_medium_ledger.csv", index=False, encoding="utf-8-sig")
    medium_standalone_df.to_csv(output_dir / "medium_dedup_standalone_ledger.csv", index=False, encoding="utf-8-sig")
    medium_summary.to_csv(output_dir / "medium_dedup_standalone_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([asdict(a) for a in audits]).to_csv(output_dir / "coreA_coreB_medium_input_audit.csv", index=False, encoding="utf-8-sig")
    json_out = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "AUDIT_ONLY",
        "core_input_dir": str(core_input_dir),
        "rr125_input_dir": str(rr125_input_dir),
        "medium_input_dir": str(medium_input_dir),
        "output_dir": str(output_dir),
        "policy": policy,
        "input_audit": [asdict(a) for a in audits],
        "aggregate": summary.replace({np.nan: None, np.inf: "inf", -np.inf: "-inf"}).to_dict(orient="records"),
    }
    (output_dir / "coreA_coreB_medium_summary.json").write_text(json.dumps(json_out, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(output_dir / "GOLD_V2_COREA_COREB_MEDIUM_AUDIT_ONLY_REPORT.md", policy, audits, summary, source, monthly)
    print(f"[DONE] output_dir={output_dir}")
    print(summary[["dataset", "view", "count", "win_rate", "pf", "total_r", "worst", "maxdd", "max_loss_streak"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
