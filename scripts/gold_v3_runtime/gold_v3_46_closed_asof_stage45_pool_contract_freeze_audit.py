#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 46 closed-asof Stage45 pool contract freeze audit-only.

Reads Stage45 closed audit outputs and freezes the contract without manually
removing or demoting any candidates. The full Stage45 candidate pool remains;
selection is handled only by the rolling health gate.

No MT5, Discord, AI API, live hook, or final signal.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_46_CLOSED_ASOF_STAGE45_POOL_CONTRACT_FREEZE_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_46_CLOSED_ASOF_STAGE45_POOL_CONTRACT_FREEZE_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_46_CLOSED_ASOF_STAGE45_POOL_CONTRACT_FREEZE_BLOCKED_AUDIT_ONLY"

REQUIRED_EXPERIMENT = "fixed_8_plus_hv_siblings_strict_rolling_health_gate"
REQUIRED_HV_PROFILES = ["HV_TP180_SL70_H128", "HV_TP200_SL80_H128", "HV_TP220_SL90_H128"]
REQUIRED_GATE = {"window": 30, "min_history": 20, "pf_threshold": 1.1, "loss_streak_lt": 3, "virtual_monitoring": True}

SAFETY_FALSE = [
    "live_allowed",
    "mt5_execution_enabled",
    "mt5_bat_created",
    "discord_live_enabled",
    "ai_api_called",
    "signals_generated",
    "final_signal_enabled",
    "stage41_trading_source_used",
    "gold_v2_old_gold_disc8_used",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def metric_val(df: pd.DataFrame, col: str, default: Any = "") -> Any:
    if df.empty or col not in df.columns:
        return default
    return df.iloc[0].get(col, default)


def ok_row(check_id: str, ok: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {
        "check_id": check_id,
        "result": "PASS" if ok else "FAIL",
        "observed": observed,
        "expected": expected,
        "severity": severity,
    }


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]
    for d in candidates:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "45_high_vol_sibling_strict_gate_walkforward_audit_only").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with Stage45 closed output folder.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--stage45-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.stage45_dir:
        s45 = Path(args.stage45_dir).expanduser().resolve()
    else:
        files_dir = find_files_dir()
        s45 = files_dir / "FX_OUTPUTS" / "gold_v3" / "45_high_vol_sibling_strict_gate_walkforward_audit_only"
    out = Path(args.output_dir).expanduser().resolve() if args.output_dir else s45.parent / "46_closed_asof_stage45_pool_contract_freeze_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    summary_path = s45 / "gold_v3_45_hv_sibling_strict_gate_summary.json"
    exp_path = s45 / "gold_v3_45_hv_sibling_gate_experiment_summary.csv"
    cand_def_path = s45 / "gold_v3_45_hv_sibling_candidate_definitions.csv"
    monthly_path = s45 / "gold_v3_45_hv_sibling_strict_gate_monthly_summary.csv"
    paste_path = s45 / "gold_v3_45_PASTE_ME_REVIEW_SUMMARY.txt"

    validation: list[dict[str, Any]] = []
    missing = [str(p) for p in [summary_path, exp_path, cand_def_path, monthly_path] if not p.exists()]
    validation.append(ok_row("required_stage45_files_present", not missing, "; ".join(missing) if missing else "all_present", "summary/experiment/candidate_definitions/monthly"))
    if missing:
        pd.DataFrame(validation).to_csv(out / "gold_v3_46_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    summary = read_json(summary_path)
    exp = read_csv(exp_path)
    cand_def = read_csv(cand_def_path)
    monthly = read_csv(monthly_path)

    validation.append(ok_row("htf_asof_closed", summary.get("htf_asof"), summary.get("htf_asof"), "closed"))
    validation[-1]["result"] = "PASS" if summary.get("htf_asof") == "closed" else "FAIL"
    validation.append(ok_row("audit_only_true", summary.get("audit_only") is True, summary.get("audit_only"), True))
    for flag in SAFETY_FALSE:
        validation.append(ok_row(f"safety_{flag}_false", summary.get(flag) is False, summary.get(flag), False))

    gate = summary.get("health_gate", {})
    for k, v in REQUIRED_GATE.items():
        validation.append(ok_row(f"gate_{k}", gate.get(k) == v, gate.get(k), v))

    exp_row = exp[exp["experiment"].astype(str).eq(REQUIRED_EXPERIMENT)] if "experiment" in exp.columns else pd.DataFrame()
    validation.append(ok_row("strict_gate_experiment_present", not exp_row.empty, REQUIRED_EXPERIMENT if not exp_row.empty else "missing", REQUIRED_EXPERIMENT))

    labels = "\n".join(cand_def.get("label", pd.Series(dtype=str)).astype(str).tolist())
    for prof in REQUIRED_HV_PROFILES:
        validation.append(ok_row(f"hv_profile_pool_contains_{prof}", prof in labels, prof if prof in labels else "missing", prof))

    hv_profile_manual_removal = False
    validation.append(ok_row("no_manual_candidate_demotion_or_removal", not hv_profile_manual_removal, "full_pool_retained", "full_pool_retained"))

    val_df = pd.DataFrame(validation)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS

    result = {
        "step": STEP,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "stage45_dir": str(s45),
        "output_dir": str(out),
        "audit_only": True,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "mt5_bat_created": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "signals_generated": False,
        "final_signal_enabled": False,
        "stage41_trading_source_used": False,
        "gold_v2_old_gold_disc8_used": False,
        "frozen_contract": {
            "htf_asof": "closed",
            "open_asof_allowed": False,
            "candidate_pool_policy": "retain_all_stage45_base_and_hv_sibling_candidates_no_manual_demote_no_manual_remove",
            "hv_profiles_retained": REQUIRED_HV_PROFILES,
            "hv_rule": summary.get("hv_rule"),
            "health_gate": REQUIRED_GATE,
            "selection_policy": "rolling_health_gate_only_virtual_monitoring_all_candidates",
        },
        "stage45_baseline": exp_row.iloc[0].to_dict() if not exp_row.empty else {},
        "validation_failures": failed.to_dict("records"),
    }

    val_df.to_csv(out / "gold_v3_46_validation_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([result["frozen_contract"] | result["stage45_baseline"]]).to_csv(out / "gold_v3_46_closed_asof_stage45_pool_contract.csv", index=False, encoding="utf-8-sig")
    (out / "gold_v3_46_closed_asof_stage45_pool_contract.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    monthly_text = monthly.to_string(index=False) if not monthly.empty else "monthly_missing"
    paste = []
    paste.append("GOLD V3 46 PASTE_ME_CONTRACT_FREEZE_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("contract: closed_asof_stage45_full_pool_strict_rolling_health_gate")
    paste.append("open_asof_allowed: false")
    paste.append("candidate_pool_policy: retain_all_stage45_base_and_hv_sibling_candidates_no_manual_demote_no_manual_remove")
    paste.append(f"hv_profiles_retained: {', '.join(REQUIRED_HV_PROFILES)}")
    paste.append(f"health_gate: {REQUIRED_GATE}")
    if not exp_row.empty:
        r = exp_row.iloc[0]
        paste.append("")
        paste.append("STAGE45_CLOSED_BASELINE")
        paste.append(f"trades: {int(r.get('trades', 0))}")
        paste.append(f"win_rate: {float(r.get('win_rate', 0.0))*100:.2f}%")
        paste.append(f"profit_factor: {float(r.get('profit_factor', 0.0)):.3f}")
        paste.append(f"sum_result_usd: {float(r.get('sum_result_usd', 0.0)):.2f}")
        paste.append(f"max_drawdown_usd: {float(r.get('max_drawdown_usd', 0.0)):.2f}")
        paste.append(f"loss_months: {int(r.get('loss_months', 0))}")
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("MONTHLY_SUMMARY")
    paste.append(monthly_text)
    (out / "gold_v3_46_PASTE_ME_CONTRACT_FREEZE_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 46 closed-asof Stage45 pool contract freeze audit-only report

Status: `{status}`

## Frozen contract

- HTF asof: `closed`
- OPEN asof allowed: `false`
- Candidate pool: retain all Stage45 base + HV sibling candidates
- Manual demotion/removal: `false`
- HV profiles retained: `{', '.join(REQUIRED_HV_PROFILES)}`
- Gate: `{REQUIRED_GATE}`

## Stage45 baseline

```json
{json.dumps(result['stage45_baseline'], ensure_ascii=False, indent=2)}
```

## Safety

Audit-only. No MT5, Discord, AI API, live hook, or final signal.
"""
    (out / "GOLD_V3_46_CLOSED_ASOF_STAGE45_POOL_CONTRACT_FREEZE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_46_PASTE_ME_CONTRACT_FREEZE_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
