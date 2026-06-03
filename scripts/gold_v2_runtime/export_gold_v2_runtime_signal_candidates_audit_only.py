#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GOLD V2 runtime signal candidate exporter (audit-only).

This script converts the already-audited CoreA + CoreB RR125 + MEDIUM ledger into
runtime-shaped JSONL/CSV records.

It intentionally does NOT:
  - call AI APIs
  - send Discord notifications
  - send MT5/live orders
  - connect to any live hooks

Default flow:
  1) Run 04 preflight.
  2) Run 03 CoreA/CoreB/MEDIUM audit.
  3) Run this exporter.

The exporter reads:
  Files/FX_OUTPUTS/gold_v2_coreA_coreB_medium_audit_only/coreA_coreB_medium_ledger.csv

and writes:
  Files/FX_OUTPUTS/gold_v2_runtime_signal_candidates_audit_only/
    gold_v2_runtime_signal_candidates.csv
    gold_v2_runtime_signal_candidates.jsonl
    gold_v2_runtime_signal_candidates_latest.json
    gold_v2_runtime_signal_candidates_summary.csv
    gold_v2_runtime_signal_candidates_summary.json
    GOLD_V2_RUNTIME_SIGNAL_CANDIDATES_AUDIT_ONLY_REPORT.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd


DEFAULT_CONFIG = "configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json"
DEFAULT_VIEW = "CoreA+CoreB+MEDIUM_extra0p5"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export GOLD V2 runtime-shaped signal candidates from audit ledger")
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--ledger", default=None, help="Path to coreA_coreB_medium_ledger.csv. Defaults to Files/FX_OUTPUTS output.")
    parser.add_argument("--view", default=DEFAULT_VIEW)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--include-datasets", default="2025,2026", help="Comma-separated dataset labels to export")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    if len(root.parents) >= 2:
        return root.parents[1]
    return root.parent


def resolve_path(path_text: str, *, base: Optional[Path] = None) -> Path:
    p = Path(path_text)
    if p.is_absolute():
        return p
    return ((base or repo_root()) / p).resolve()


def default_ledger_path() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_coreA_coreB_medium_audit_only" / "coreA_coreB_medium_ledger.csv"


def default_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_runtime_signal_candidates_audit_only"


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return None
        v = float(value)
        if math.isnan(v):
            return None
        if math.isinf(v):
            return v
        return v
    except Exception:
        return None


def source_to_priority(source: str) -> str:
    source = str(source)
    if source == "CORE_A_ONLY":
        return "HIGH_A"
    if source == "CORE_B_ONLY":
        return "HIGH_B"
    if source == "CORE_A_CORE_B_CONFLUENCE":
        return "HIGH_CONFLUENCE"
    if source.startswith("MEDIUM_"):
        return "MEDIUM"
    return "UNKNOWN"


def source_to_component(source: str) -> str:
    source = str(source)
    if source == "CORE_A_ONLY":
        return "CoreA_fold4_ABC_CAP5"
    if source == "CORE_B_ONLY":
        return "RR125_BUY_CONFLUENCE"
    if source == "CORE_A_CORE_B_CONFLUENCE":
        return "CoreA_PLUS_RR125_BUY_CONFLUENCE"
    if source.startswith("MEDIUM_"):
        return source.replace("MEDIUM_", "")
    return source


def source_to_lot_multiplier(source: str, cfg: Dict[str, Any]) -> float:
    source = str(source)
    if source == "CORE_A_ONLY":
        return float(cfg.get("coreA", {}).get("lot_multiplier", 1.0))
    if source == "CORE_B_ONLY":
        return float(cfg.get("coreB", {}).get("lot_multiplier", 1.0))
    if source == "CORE_A_CORE_B_CONFLUENCE":
        extra = float(cfg.get("confluence", {}).get("initial_extra_coreB_exposure", 0.5))
        return float(cfg.get("coreA", {}).get("lot_multiplier", 1.0)) + extra
    if source.startswith("MEDIUM_"):
        return float(cfg.get("medium", {}).get("default_lot_multiplier", 0.5))
    return 0.0


def source_to_execution_mode(source: str) -> str:
    source = str(source)
    if source.startswith("MEDIUM_"):
        return "AUDIT_OR_NOTIFICATION_ONLY_UNTIL_DEMO_APPROVED"
    return "AUDIT_ONLY_UNTIL_DEMO_APPROVED"


def make_signal_id(row: pd.Series, policy_id: str) -> str:
    raw = "|".join([
        policy_id,
        str(row.get("dataset", "")),
        str(row.get("entry_time", "")),
        str(row.get("direction", "")),
        str(row.get("source", "")),
        str(row.get("core_cluster_id", "")),
        str(row.get("coreb_cluster_id", "")),
        str(row.get("medium_cluster_id", "")),
    ])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def to_records(df: pd.DataFrame, cfg: Dict[str, Any], view: str) -> List[Dict[str, Any]]:
    policy_id = str(cfg.get("policy_id", "GOLD_V2_COREA_COREB_MEDIUM_POLICY"))
    safety = cfg.get("safety", {})
    records: List[Dict[str, Any]] = []
    for _, row in df.sort_values(["dataset", "entry_time", "source"]).iterrows():
        source = str(row.get("source", ""))
        priority = source_to_priority(source)
        component = source_to_component(source)
        rec: Dict[str, Any] = {
            "signal_id": make_signal_id(row, policy_id),
            "policy_id": policy_id,
            "view": view,
            "dataset": str(row.get("dataset", "")),
            "entry_time": str(row.get("entry_time", "")),
            "entry_month": str(row.get("entry_month", "")),
            "direction": str(row.get("direction", "")),
            "priority": priority,
            "component": component,
            "source": source,
            "lot_multiplier_candidate": source_to_lot_multiplier(source, cfg),
            "execution_mode": source_to_execution_mode(source),
            "audit_only": bool(safety.get("audit_only", True)),
            "ai_api_enabled": bool(safety.get("ai_api_enabled", False)),
            "discord_enabled": bool(safety.get("discord_enabled", False)),
            "mt5_order_enabled": bool(safety.get("mt5_order_enabled", False)),
            "live_hook_enabled": bool(safety.get("live_hook_enabled", False)),
            "profit_r_audit": safe_float(row.get("profit_r")),
            "core_profit_r_audit": safe_float(row.get("core_profit_r")),
            "coreb_profit_r_audit": safe_float(row.get("coreb_profit_r")),
            "medium_profit_r_audit": safe_float(row.get("medium_profit_r")),
            "core_cluster_id": None if pd.isna(row.get("core_cluster_id", np.nan)) else row.get("core_cluster_id"),
            "coreb_cluster_id": None if pd.isna(row.get("coreb_cluster_id", np.nan)) else row.get("coreb_cluster_id"),
            "medium_cluster_id": None if pd.isna(row.get("medium_cluster_id", np.nan)) else row.get("medium_cluster_id"),
            "extra_coreb_exposure": safe_float(row.get("extra_coreb_exposure")),
            "notes": "candidate output only; no order or notification side effects",
        }
        records.append(rec)
    return records


def metrics(values: Iterable[float]) -> Dict[str, Any]:
    vals = pd.Series(list(values)).dropna().astype(float).to_numpy()
    if len(vals) == 0:
        return {"count": 0, "win_rate": None, "pf": None, "total_r": 0.0, "worst": None, "maxdd": 0.0}
    gross_win = float(vals[vals > 0].sum())
    gross_loss = float(-vals[vals < 0].sum())
    if gross_loss == 0 and gross_win > 0:
        pf: Any = "inf"
    elif gross_loss > 0:
        pf = gross_win / gross_loss
    else:
        pf = None
    eq = np.cumsum(vals)
    peak = np.maximum.accumulate(np.r_[0.0, eq[:-1]])
    dd = np.maximum(peak - eq, 0.0)
    return {
        "count": int(len(vals)),
        "win_rate": float((vals > 0).mean()),
        "pf": pf,
        "total_r": float(vals.sum()),
        "worst": float(vals.min()),
        "maxdd": float(dd.max()) if len(dd) else 0.0,
    }


def summarize(records: List[Dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    rows: List[Dict[str, Any]] = []
    for keys, g in df.groupby(["dataset", "priority", "component"]):
        dataset, priority, component = keys
        m = metrics(g["profit_r_audit"])
        m.update({"dataset": dataset, "priority": priority, "component": component})
        rows.append(m)
    for dataset, g in df.groupby("dataset"):
        m = metrics(g["profit_r_audit"])
        m.update({"dataset": dataset, "priority": "ALL", "component": "ALL"})
        rows.append(m)
    return pd.DataFrame(rows).sort_values(["dataset", "priority", "component"]).reset_index(drop=True)


def simple_markdown_table(df: pd.DataFrame, cols: Sequence[str]) -> str:
    if df.empty:
        return "_No rows._"
    view = df[[c for c in cols if c in df.columns]].copy()
    if "win_rate" in view.columns:
        view["win_rate"] = pd.to_numeric(view["win_rate"], errors="coerce") * 100.0
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join(["---"] * len(view.columns)) + " |"]
    for _, row in view.iterrows():
        cells = []
        for col in view.columns:
            value = row[col]
            if pd.isna(value):
                cells.append("")
            elif isinstance(value, (float, np.floating)):
                cells.append(f"{float(value):.2f}")
            else:
                cells.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    config_path = resolve_path(args.config, base=repo_root())
    ledger_path = Path(args.ledger).expanduser().resolve() if args.ledger else default_ledger_path()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not config_path.exists():
        print(f"[ERROR] config not found: {config_path}", file=sys.stderr)
        return 2
    if not ledger_path.exists():
        print(f"[ERROR] ledger not found: {ledger_path}", file=sys.stderr)
        print("Run 03_RUN_COREA_COREB_MEDIUM_AUDIT_ONLY.bat first.", file=sys.stderr)
        return 2

    cfg = read_json(config_path)
    ledger = pd.read_csv(ledger_path)
    required = ["dataset", "view", "entry_time", "entry_month", "direction", "source", "profit_r"]
    missing = [c for c in required if c not in ledger.columns]
    if missing:
        print(f"[ERROR] missing ledger columns: {missing}", file=sys.stderr)
        return 2

    include_datasets = {x.strip() for x in str(args.include_datasets).split(",") if x.strip()}
    selected = ledger[(ledger["view"].astype(str).eq(args.view)) & (ledger["dataset"].astype(str).isin(include_datasets))].copy()
    if selected.empty:
        print(f"[ERROR] no rows for view={args.view} datasets={sorted(include_datasets)}", file=sys.stderr)
        return 2

    records = to_records(selected, cfg, args.view)
    out_csv = output_dir / "gold_v2_runtime_signal_candidates.csv"
    out_jsonl = output_dir / "gold_v2_runtime_signal_candidates.jsonl"
    out_latest = output_dir / "gold_v2_runtime_signal_candidates_latest.json"
    out_summary_csv = output_dir / "gold_v2_runtime_signal_candidates_summary.csv"
    out_summary_json = output_dir / "gold_v2_runtime_signal_candidates_summary.json"
    out_report = output_dir / "GOLD_V2_RUNTIME_SIGNAL_CANDIDATES_AUDIT_ONLY_REPORT.md"

    pd.DataFrame(records).to_csv(out_csv, index=False, encoding="utf-8-sig")
    with out_jsonl.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")

    latest_by_dataset = []
    rec_df = pd.DataFrame(records)
    rec_df["entry_time_dt"] = pd.to_datetime(rec_df["entry_time"], errors="coerce")
    for dataset, g in rec_df.sort_values("entry_time_dt").groupby("dataset"):
        latest_by_dataset.append(g.drop(columns=["entry_time_dt"]).iloc[-1].to_dict())
    latest_payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "AUDIT_ONLY_SIGNAL_CANDIDATES",
        "view": args.view,
        "source_ledger": str(ledger_path),
        "latest_by_dataset": latest_by_dataset,
    }
    out_latest.write_text(json.dumps(latest_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_df = summarize(records)
    summary_df.to_csv(out_summary_csv, index=False, encoding="utf-8-sig")
    summary_payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "AUDIT_ONLY_SIGNAL_CANDIDATES",
        "config_path": str(config_path),
        "ledger_path": str(ledger_path),
        "output_dir": str(output_dir),
        "view": args.view,
        "record_count": len(records),
        "summary": summary_df.replace({np.nan: None, np.inf: "inf", -np.inf: "-inf"}).to_dict(orient="records"),
        "safety": cfg.get("safety", {}),
    }
    out_summary_json.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# GOLD V2 runtime signal candidates audit-only report", "",
        f"Created UTC: {datetime.now(timezone.utc).isoformat()}", "",
        "## Safety", "",
        "```json", json.dumps(cfg.get("safety", {}), ensure_ascii=False, indent=2), "```", "",
        "## Input", "",
        f"- config: `{config_path}`",
        f"- ledger: `{ledger_path}`",
        f"- view: `{args.view}`",
        f"- records: `{len(records)}`", "",
        "## Summary", "",
        simple_markdown_table(summary_df, ["dataset", "priority", "component", "count", "win_rate", "pf", "total_r", "worst", "maxdd"]), "",
        "## Latest by dataset", "",
        simple_markdown_table(pd.DataFrame(latest_by_dataset), ["dataset", "entry_time", "direction", "priority", "component", "lot_multiplier_candidate", "profit_r_audit", "mt5_order_enabled", "discord_enabled"]), "",
        "This exporter is audit-only. It does not execute orders or send notifications.",
    ]
    out_report.write_text("\n".join(lines), encoding="utf-8")

    print(f"[DONE] output_dir={output_dir}")
    print(summary_df.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
