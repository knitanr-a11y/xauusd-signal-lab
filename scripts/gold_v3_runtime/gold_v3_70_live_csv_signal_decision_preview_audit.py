#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 70 live CSV signal decision preview audit-only.

Produces deterministic SIGNAL/NO_SIGNAL preview from Stage69 latest closed
condition candidates and Stage67 candidate health state.

No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "GOLD_V3_70_LIVE_CSV_SIGNAL_DECISION_PREVIEW_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_70_LIVE_CSV_SIGNAL_DECISION_PREVIEW_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_70_LIVE_CSV_SIGNAL_DECISION_PREVIEW_BLOCKED_AUDIT_ONLY"
STAGE69_READY = "GOLD_V3_69_LIVE_CSV_CONDITION_DETECTOR_READY_AUDIT_ONLY"
STAGE68_READY = "GOLD_V3_68_RANK_DEDUP_SELECTION_REPRO_READY_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
KEY_COLS = ["candidate_label","base_candidate_label","source_profile_id","profile_id","hv_profile","tp_usd","sl_usd","horizon_m15","horizon_m5_bars"]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    if path.exists() and path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def norm_cell(v: Any) -> str:
    if pd.isna(v):
        return ""
    if isinstance(v, (np.integer, int)):
        return str(int(v))
    if isinstance(v, (np.floating, float)):
        f = float(v)
        if math.isfinite(f) and f.is_integer():
            return str(int(f))
        return (f"{f:.10f}").rstrip("0").rstrip(".")
    s = str(v).strip()
    if s.lower() in {"nan", "none", "nat"}:
        return ""
    return s


def normalize_key_part(s: Any) -> str:
    x = norm_cell(s)
    if not x:
        return ""
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", x):
        try:
            f = float(x)
            if math.isfinite(f) and f.is_integer():
                return str(int(f))
            return (f"{f:.10f}").rstrip("0").rstrip(".")
        except Exception:
            return x
    return x


def build_candidate_key(df: pd.DataFrame) -> pd.Series:
    key = pd.Series([""] * len(df), index=df.index, dtype="object")
    for i, c in enumerate(KEY_COLS):
        part = df[c].map(normalize_key_part)
        key = part if i == 0 else key + "|" + part
    return key.astype(str)


def as_bool_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "y"])


def add_key_columns(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    if x.empty:
        return x
    if "base_candidate_label" not in x.columns:
        x["base_candidate_label"] = x["candidate_label"].astype(str).str.replace(r"^HV_(.*?)__HV_TP.*$", r"\1", regex=True)
    if "hv_profile" not in x.columns:
        x["hv_profile"] = x["profile_id"].where(x.get("hv_sibling", False).astype(bool), "")
    if "horizon_m5_bars" not in x.columns:
        x["horizon_m5_bars"] = pd.to_numeric(x["horizon_m15"], errors="coerce").fillna(0).astype(int) * 3
    x["candidate_key"] = build_candidate_key(x)
    return x


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files", root.parent.parent]
    for d in candidates:
        d = d.expanduser().resolve()
        if (d/"FX_OUTPUTS"/"gold_v3"/"69_live_csv_condition_detector_audit_only").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with Stage69 outputs")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage69-dir", default="")
    p.add_argument("--stage68-dir", default="")
    p.add_argument("--stage67-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    s69 = Path(a.stage69_dir).expanduser().resolve() if a.stage69_dir else base_out / "69_live_csv_condition_detector_audit_only"
    s68 = Path(a.stage68_dir).expanduser().resolve() if a.stage68_dir else base_out / "68_rank_dedup_selection_repro_audit_only"
    s67 = Path(a.stage67_dir).expanduser().resolve() if a.stage67_dir else base_out / "67_health_gate_rehydration_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out / "70_live_csv_signal_decision_preview_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p69 = s69 / "gold_v3_69_live_csv_condition_detector_summary.json"
    p69_latest = s69 / "gold_v3_69_latest_closed_condition_candidates.csv"
    p68 = s68 / "gold_v3_68_rank_dedup_selection_repro_summary.json"
    p67_state = s67 / "gold_v3_67_health_gate_rehydrated_candidate_state.csv"

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for name, path in [("stage69_summary", p69), ("stage69_latest_candidates", p69_latest), ("stage68_summary", p68), ("stage67_candidate_state", p67_state)]:
        val.append(ok(f"{name}_present", path.exists(), str(path), "exists"))
        if not path.exists():
            blockers.append(blocker(f"{name}_missing", str(path), "REQUIRED_INPUT_MISSING"))

    j69 = read_json(p69) if p69.exists() else {}
    j68 = read_json(p68) if p68.exists() else {}
    val.append(ok("stage69_status_ready", j69.get("status") == STAGE69_READY, j69.get("status"), STAGE69_READY))
    val.append(ok("stage69_detector_ready", j69.get("live_csv_condition_detector_ready") is True, j69.get("live_csv_condition_detector_ready"), True))
    val.append(ok("stage68_status_ready", j68.get("status") == STAGE68_READY, j68.get("status"), STAGE68_READY))
    val.append(ok("stage68_rank_dedup_ready", j68.get("rank_dedup_selection_repro_ready") is True, j68.get("rank_dedup_selection_repro_ready"), True))
    for src, j in [("stage69", j69), ("stage68", j68)]:
        for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "ai_api_called", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
            val.append(ok(f"{src}_{key}_false", j.get(key) is False, j.get(key), False))

    decision = pd.DataFrame()
    screen = pd.DataFrame()
    latest_time = str(j69.get("latest_closed_m15_time", ""))
    latest_rows = 0
    eligible_rows = 0
    missing_health = 0
    decision_value = ""
    no_signal_reason = ""
    selected_candidate = ""

    if not blockers:
        latest = read_csv(p69_latest)
        state = read_csv(p67_state)
        latest_rows = int(len(latest))
        state = add_key_columns(state) if not state.empty else state
        latest = add_key_columns(latest) if not latest.empty else latest
        if not latest.empty:
            missing_key_cols = [c for c in KEY_COLS if c not in latest.columns]
            val.append(ok("latest_candidates_have_key_columns", not missing_key_cols, "|".join(missing_key_cols), "none"))
            if missing_key_cols:
                blockers.append(blocker("latest_candidate_key_missing", str(p69_latest), "MISSING_KEY_COLUMNS", missing_key_cols))
            else:
                hs = state[["candidate_key", "health_gate_pass", "health_gate_reason", "rolling_pf_before", "loss_streak_before", "observed_event_count"]].drop_duplicates("candidate_key", keep="last")
                screen = latest.merge(hs, on="candidate_key", how="left")
                missing_health = int(screen["health_gate_pass"].isna().sum())
                screen["health_gate_pass_bool"] = as_bool_series(screen["health_gate_pass"])
                screen = screen.sort_values(["priority", "candidate_label", "candidate_key", "condition_id"], kind="mergesort").reset_index(drop=True)
                eligible = screen[screen["health_gate_pass_bool"]].copy()
                eligible_rows = int(len(eligible))
                if missing_health:
                    blockers.append(blocker("latest_candidate_health_missing", str(p67_state), "STAGE67_HEALTH_STATE_MISSING_FOR_LATEST_CANDIDATE", {"missing": missing_health, "latest_rows": latest_rows}))
                if len(eligible) > 0:
                    r = eligible.iloc[0].to_dict()
                    decision_value = "SIGNAL"
                    selected_candidate = str(r.get("candidate_label", ""))
                    no_signal_reason = ""
                    decision = pd.DataFrame([{**r, "latest_closed_m15_time": latest_time, "decision": decision_value, "no_signal_reason": no_signal_reason, "audit_only": True, "live_ready": False}])
                else:
                    decision_value = "NO_SIGNAL"
                    no_signal_reason = "HEALTH_GATE_BLOCKED"
                    decision = pd.DataFrame([{"latest_closed_m15_time": latest_time, "decision": decision_value, "no_signal_reason": no_signal_reason, "latest_condition_candidate_rows": latest_rows, "eligible_candidate_rows": 0, "audit_only": True, "live_ready": False}])
        else:
            val.append(ok("latest_candidates_empty_allowed", True, 0, "NO_SIGNAL_ALLOWED"))
            decision_value = "NO_SIGNAL"
            no_signal_reason = "CONDITION_NOT_MET"
            screen = pd.DataFrame()
            decision = pd.DataFrame([{"latest_closed_m15_time": latest_time, "decision": decision_value, "no_signal_reason": no_signal_reason, "latest_condition_candidate_rows": 0, "eligible_candidate_rows": 0, "audit_only": True, "live_ready": False}])
        val.append(ok("latest_closed_time_present", latest_time != "", latest_time, "nonempty"))
        val.append(ok("decision_row_produced", len(decision) == 1, len(decision), 1))
        val.append(ok("latest_candidates_health_join", missing_health == 0, missing_health, 0))

    screen.to_csv(out / "gold_v3_70_latest_closed_candidate_screen.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "gold_v3_70_latest_closed_signal_decision.csv", index=False, encoding="utf-8-sig")

    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
    val.append(ok("no_ohlc_re_adjudication", True, "not_used", "not_used"))
    val.append(ok("live_flags_all_false", True, "all_false", "all_false"))

    pd.DataFrame(blockers).to_csv(out / "gold_v3_70_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty and not blockers else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_70_validation_matrix.csv", index=False, encoding="utf-8-sig")

    summary = {
        "step": STEP,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "candle_dir": str(cdir),
        "output_dir": str(out),
        "audit_only": True,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "mt5_bat_created": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "signals_generated": False,
        "final_signal_enabled": False,
        "contract_mutated": False,
        "manual_candidate_demotion_or_removal": False,
        "open_asof_allowed": False,
        "csv_contract": CSV_CONTRACT,
        "csv_open_bar_exclusion_required": False,
        "live_ready": False,
        "signal_decision_preview_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "candidate_key_source": "+".join(KEY_COLS),
        "latest_closed_m15_time": latest_time,
        "latest_condition_candidate_rows": latest_rows,
        "eligible_candidate_rows": eligible_rows,
        "decision": decision_value,
        "no_signal_reason": no_signal_reason,
        "selected_candidate_label": selected_candidate,
        "missing_health_state_rows": missing_health,
        "validation_failure_count": int(len(failed)),
        "blocker_count": int(len(blockers)),
    }
    (out / "gold_v3_70_live_csv_signal_decision_preview_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 70 PASTE_ME_LIVE_CSV_SIGNAL_DECISION_PREVIEW_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("signal_decision_preview_ready: " + str(status == READY_STATUS).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("csv_contract: " + CSV_CONTRACT)
    paste.append("csv_open_bar_exclusion_required: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append("pool_policy: " + POOL_POLICY)
    paste.append("candidate_key_source: " + "+".join(KEY_COLS))
    paste.append(f"latest_closed_m15_time: {latest_time}")
    paste.append(f"latest_condition_candidate_rows: {latest_rows}")
    paste.append(f"eligible_candidate_rows: {eligible_rows}")
    paste.append(f"decision: {decision_value}")
    paste.append(f"no_signal_reason: {no_signal_reason}")
    paste.append(f"selected_candidate_label: {selected_candidate}")
    paste.append(f"missing_health_state_rows: {missing_health}")
    paste.append(f"blocker_count: {len(blockers)}")
    paste.append("")
    paste.append("BLOCKERS")
    paste.append(pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS")
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_70_latest_closed_candidate_screen.csv")
    paste.append("gold_v3_70_latest_closed_signal_decision.csv")
    paste.append("gold_v3_70_blocker_matrix.csv")
    paste.append("gold_v3_70_validation_matrix.csv")
    paste.append("gold_v3_70_live_csv_signal_decision_preview_summary.json")
    (out / "gold_v3_70_PASTE_ME_LIVE_CSV_SIGNAL_DECISION_PREVIEW_SUMMARY.txt").write_text("\n".join(paste)+"\n", encoding="utf-8")

    report = f"""# GOLD V3 70 live CSV signal decision preview audit-only report

Status: `{status}`

## Summary

- latest_closed_m15_time: `{latest_time}`
- latest_condition_candidate_rows: `{latest_rows}`
- eligible_candidate_rows: `{eligible_rows}`
- decision: `{decision_value}`
- no_signal_reason: `{no_signal_reason}`
- blocker_count: `{len(blockers)}`

## Safety

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out / "GOLD_V3_70_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_70_PASTE_ME_LIVE_CSV_SIGNAL_DECISION_PREVIEW_SUMMARY.txt")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
