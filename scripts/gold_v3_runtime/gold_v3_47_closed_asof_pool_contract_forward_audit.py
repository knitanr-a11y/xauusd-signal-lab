#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 47 closed-asof pool contract forward audit-only.

Validates Stage46 frozen contract, re-runs the Stage45 closed-asof full-pool
strict rolling health gate audit into a Stage47 replay folder, and writes a
compact PASTE_ME summary for chat review.

No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_47_CLOSED_ASOF_POOL_CONTRACT_FORWARD_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_47_CLOSED_ASOF_POOL_CONTRACT_FORWARD_AUDIT_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_47_CLOSED_ASOF_POOL_CONTRACT_FORWARD_AUDIT_BLOCKED_AUDIT_ONLY"
STAGE46_READY = "GOLD_V3_46_CLOSED_ASOF_STAGE45_POOL_CONTRACT_FREEZE_READY_AUDIT_ONLY"
REQUIRED_EXPERIMENT = "fixed_8_plus_hv_siblings_strict_rolling_health_gate"
REQUIRED_HV = ["HV_TP180_SL70_H128", "HV_TP200_SL80_H128", "HV_TP220_SL90_H128"]


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("gold_v3_45_runner", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def ok_row(check_id: str, ok: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if ok else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]
    for d in candidates:
        d = d.expanduser().resolve()
        if (d / "goldsharp_m5.csv").exists() and (d / "goldsharp_m15.csv").exists() and (d / "goldsharp_h4.csv").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with goldsharp_m5/m15/h4.csv")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage46-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def pct(x: Any) -> str:
    try:
        return f"{float(x) * 100:.2f}%"
    except Exception:
        return ""


def num(x: Any, nd: int = 2) -> str:
    try:
        return f"{float(x):,.{nd}f}"
    except Exception:
        return ""


def main() -> int:
    args = parse_args()
    cdir = Path(args.candle_dir).expanduser().resolve() if args.candle_dir else find_files_dir()
    stage46_dir = Path(args.stage46_dir).expanduser().resolve() if args.stage46_dir else cdir / "FX_OUTPUTS" / "gold_v3" / "46_closed_asof_stage45_pool_contract_freeze_audit_only"
    out = Path(args.output_dir).expanduser().resolve() if args.output_dir else cdir / "FX_OUTPUTS" / "gold_v3" / "47_closed_asof_pool_contract_forward_audit_only"
    replay_dir = out / "stage47_replay"
    out.mkdir(parents=True, exist_ok=True)
    replay_dir.mkdir(parents=True, exist_ok=True)

    val: list[dict[str, Any]] = []
    contract_path = stage46_dir / "gold_v3_46_closed_asof_stage45_pool_contract.json"
    val.append(ok_row("stage46_contract_present", contract_path.exists(), str(contract_path), "exists"))
    if not contract_path.exists():
        pd.DataFrame(val).to_csv(out / "gold_v3_47_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    contract = read_json(contract_path)
    frozen = contract.get("frozen_contract", {})
    val.append(ok_row("stage46_status_ready", contract.get("status") == STAGE46_READY, contract.get("status"), STAGE46_READY))
    val.append(ok_row("stage46_htf_asof_closed", frozen.get("htf_asof") == "closed", frozen.get("htf_asof"), "closed"))
    val.append(ok_row("stage46_open_asof_disallowed", frozen.get("open_asof_allowed") is False, frozen.get("open_asof_allowed"), False))
    pool_policy = str(frozen.get("candidate_pool_policy", ""))
    val.append(ok_row("stage46_pool_retained_no_manual_remove", "retain_all" in pool_policy and "no_manual" in pool_policy, pool_policy, "retain_all...no_manual..."))
    hv_profiles = list(frozen.get("hv_profiles_retained", []))
    for prof in REQUIRED_HV:
        val.append(ok_row(f"stage46_hv_retained_{prof}", prof in hv_profiles, prof if prof in hv_profiles else "missing", prof))

    # Re-run Stage45 closed-asof runner using frozen settings and current Files candles.
    runner_path = Path(__file__).resolve().with_name("gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.py")
    val.append(ok_row("stage45_runner_present", runner_path.exists(), str(runner_path), "exists"))
    failed_pre = [r for r in val if r["result"] != "PASS"]
    if failed_pre:
        pd.DataFrame(val).to_csv(out / "gold_v3_47_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    runner = load_module(runner_path)
    rc = runner.main([
        "--candle-dir", str(cdir),
        "--output-dir", str(replay_dir),
        "--start-jst", "2026-01-01",
        "--htf-asof", "closed",
        "--hv-rolling-days", "60",
        "--hv-quantile", "0.70",
        "--health-window", "30",
        "--health-min-history", "20",
        "--strict-pf-threshold", "1.10",
        "--strict-loss-streak-lt", "3",
        "--run-walkforward",
    ])
    val.append(ok_row("stage45_replay_return_code_zero", rc == 0, rc, 0))

    replay_summary_path = replay_dir / "gold_v3_45_hv_sibling_strict_gate_summary.json"
    replay_exp_path = replay_dir / "gold_v3_45_hv_sibling_gate_experiment_summary.csv"
    replay_monthly_path = replay_dir / "gold_v3_45_hv_sibling_strict_gate_monthly_summary.csv"
    val.append(ok_row("replay_summary_present", replay_summary_path.exists(), str(replay_summary_path), "exists"))
    val.append(ok_row("replay_experiment_present", replay_exp_path.exists(), str(replay_exp_path), "exists"))
    val.append(ok_row("replay_monthly_present", replay_monthly_path.exists(), str(replay_monthly_path), "exists"))

    replay_summary = read_json(replay_summary_path) if replay_summary_path.exists() else {}
    val.append(ok_row("replay_htf_asof_closed", replay_summary.get("htf_asof") == "closed", replay_summary.get("htf_asof"), "closed"))
    for flag in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "ai_api_called", "signals_generated", "final_signal_enabled"]:
        val.append(ok_row(f"replay_safety_{flag}_false", replay_summary.get(flag) is False, replay_summary.get(flag), False))

    exp = read_csv(replay_exp_path) if replay_exp_path.exists() else pd.DataFrame()
    row = exp[exp["experiment"].astype(str).eq(REQUIRED_EXPERIMENT)] if not exp.empty and "experiment" in exp.columns else pd.DataFrame()
    val.append(ok_row("replay_strict_gate_row_present", not row.empty, REQUIRED_EXPERIMENT if not row.empty else "missing", REQUIRED_EXPERIMENT))

    baseline = contract.get("stage45_baseline", {})
    current = row.iloc[0].to_dict() if not row.empty else {}
    delta_keys = ["trades", "win_rate", "profit_factor", "sum_result_usd", "max_drawdown_usd", "loss_months"]
    deltas = []
    for k in delta_keys:
        b = baseline.get(k, 0)
        c = current.get(k, 0)
        try:
            d = float(c) - float(b)
        except Exception:
            d = ""
        deltas.append({"metric": k, "stage46_baseline": b, "stage47_current": c, "delta": d})
    pd.DataFrame(deltas).to_csv(out / "gold_v3_47_metric_delta_vs_stage46_baseline.csv", index=False, encoding="utf-8-sig")

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_47_validation_matrix.csv", index=False, encoding="utf-8-sig")

    monthly = read_csv(replay_monthly_path) if replay_monthly_path.exists() else pd.DataFrame()
    result = {
        "step": STEP,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "candle_dir": str(cdir),
        "stage46_dir": str(stage46_dir),
        "output_dir": str(out),
        "replay_dir": str(replay_dir),
        "audit_only": True,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "mt5_bat_created": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "signals_generated": False,
        "final_signal_enabled": False,
        "contract_reused_without_candidate_changes": True,
        "manual_candidate_demotion_or_removal": False,
        "stage46_baseline": baseline,
        "stage47_current": current,
        "validation_failures": failed.to_dict("records"),
    }
    (out / "gold_v3_47_forward_audit_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 47 PASTE_ME_FORWARD_AUDIT_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("contract: closed_asof_stage45_full_pool_strict_rolling_health_gate")
    paste.append("contract_reused_without_candidate_changes: true")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    paste.append("")
    paste.append("STAGE47_CURRENT")
    if current:
        paste.append(f"trades: {int(current.get('trades', 0))}")
        paste.append(f"win_rate: {pct(current.get('win_rate'))}")
        paste.append(f"profit_factor: {num(current.get('profit_factor'), 3)}")
        paste.append(f"sum_result_usd: {num(current.get('sum_result_usd'), 2)}")
        paste.append(f"max_drawdown_usd: {num(current.get('max_drawdown_usd'), 2)}")
        paste.append(f"loss_months: {int(current.get('loss_months', 0))}")
    paste.append("")
    paste.append("DELTA_VS_STAGE46_BASELINE")
    paste.append(pd.DataFrame(deltas).to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("MONTHLY_SUMMARY")
    paste.append(monthly.to_string(index=False) if not monthly.empty else "monthly_missing")
    (out / "gold_v3_47_PASTE_ME_FORWARD_AUDIT_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 47 closed-asof pool contract forward audit-only report

Status: `{status}`

## Contract

- closed asof only
- full Stage45 base + HV sibling pool retained
- no manual candidate demotion/removal
- strict rolling health gate unchanged

## Current result

```json
{json.dumps(current, ensure_ascii=False, indent=2)}
```

## Safety

Audit-only. No MT5, Discord, AI API, live hook, or final signal.
"""
    (out / "GOLD_V3_47_CLOSED_ASOF_POOL_CONTRACT_FORWARD_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_47_PASTE_ME_FORWARD_AUDIT_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
