#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 69 live CSV condition detector audit-only.

Detects GOLD V3 candidate conditions from live closed CSV rows using audited
Stage45 condition functions and audited Stage50 q70 high-vol state. This stage
performs condition detection only; it does not adjudicate future outcome.

No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "GOLD_V3_69_LIVE_CSV_CONDITION_DETECTOR_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_69_LIVE_CSV_CONDITION_DETECTOR_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_69_LIVE_CSV_CONDITION_DETECTOR_BLOCKED_AUDIT_ONLY"
STAGE68_READY = "GOLD_V3_68_RANK_DEDUP_SELECTION_REPRO_READY_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
KEY_COLS = [
    "candidate_label",
    "base_candidate_label",
    "source_profile_id",
    "profile_id",
    "hv_profile",
    "tp_usd",
    "sl_usd",
    "horizon_m15",
    "horizon_m5_bars",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
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
        except Exception:  # pragma: no cover
            return x
    return x


def build_candidate_key(df: pd.DataFrame) -> pd.Series:
    key = pd.Series([""] * len(df), index=df.index, dtype="object")
    for i, c in enumerate(KEY_COLS):
        part = df[c].map(normalize_key_part)
        key = part if i == 0 else key + "|" + part
    return key.astype(str)


def add_key_columns(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    if "base_candidate_label" not in x.columns:
        x["base_candidate_label"] = x["candidate_label"].astype(str).str.replace(r"^HV_(.*?)__HV_TP.*$", r"\1", regex=True)
    if "hv_profile" not in x.columns:
        x["hv_profile"] = x["profile_id"].where(x.get("hv_sibling", False).astype(bool), "")
    if "horizon_m5_bars" not in x.columns:
        x["horizon_m5_bars"] = pd.to_numeric(x["horizon_m15"], errors="coerce").fillna(0).astype(int) * 3
    x["candidate_key"] = build_candidate_key(x)
    return x


def load_stage45(path: Path):
    spec = importlib.util.spec_from_file_location("gold_v3_stage45", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd(), Path.cwd() / "Files", root, root / "Files", root.parent, root.parent / "Files", root.parent.parent]
    for d in candidates:
        d = d.expanduser().resolve()
        if (d / "goldsharp_m15.csv").exists() and (d / "goldsharp_h4.csv").exists() and (d / "goldsharp_m5.csv").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with goldsharp_m5/m15/h4.csv")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage68-dir", default="")
    p.add_argument("--stage51-dir", default="")
    p.add_argument("--stage50-dir", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--start-jst", default="2026-01-01")
    p.add_argument("--end-jst", default="")
    return p.parse_args()


def period(df: pd.DataFrame, start_jst: str, end_jst: str) -> pd.DataFrame:
    if df.empty:
        return df
    x = df.copy()
    t = pd.to_datetime(x["entry_dt"], errors="coerce")
    if start_jst:
        start = pd.Timestamp(start_jst)
        x = x[t >= start]
        t = pd.to_datetime(x["entry_dt"], errors="coerce")
    if end_jst:
        end = pd.Timestamp(end_jst)
        x = x[t <= end]
    return x.reset_index(drop=True)


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    s68 = Path(a.stage68_dir).expanduser().resolve() if a.stage68_dir else base_out / "68_rank_dedup_selection_repro_audit_only"
    s51 = Path(a.stage51_dir).expanduser().resolve() if a.stage51_dir else base_out / "51_full_candidate_virtual_opportunity_ledger_builder_audit_only"
    s50 = Path(a.stage50_dir).expanduser().resolve() if a.stage50_dir else base_out / "50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out / "69_live_csv_condition_detector_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p_m15 = cdir / "goldsharp_m15.csv"
    p_h4 = cdir / "goldsharp_h4.csv"
    p_m5 = cdir / "goldsharp_m5.csv"
    p68 = s68 / "gold_v3_68_rank_dedup_selection_repro_summary.json"
    p51 = s51 / "gold_v3_51_virtual_opportunity_ledger.csv"
    p50q = s50 / "gold_v3_50_rolling_prior_60d_q70_state.csv"
    p45 = Path(__file__).resolve().with_name("gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.py")

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for name, path in [
        ("goldsharp_m15", p_m15),
        ("goldsharp_h4", p_h4),
        ("goldsharp_m5", p_m5),
        ("stage68_summary", p68),
        ("stage51_ledger", p51),
        ("stage50_q70_state", p50q),
        ("stage45_runner", p45),
    ]:
        val.append(ok(f"{name}_present", path.exists(), str(path), "exists"))
        if not path.exists():
            blockers.append(blocker(f"{name}_missing", str(path), "REQUIRED_INPUT_MISSING"))

    j68 = read_json(p68) if p68.exists() else {}
    val.append(ok("stage68_status_ready", j68.get("status") == STAGE68_READY, j68.get("status"), STAGE68_READY))
    val.append(ok("stage68_rank_dedup_ready", j68.get("rank_dedup_selection_repro_ready") is True, j68.get("rank_dedup_selection_repro_ready"), True))
    for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "ai_api_called", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
        val.append(ok(f"stage68_{key}_false", j68.get(key) is False, j68.get(key), False))

    detected = pd.DataFrame()
    latest = pd.DataFrame()
    parity = pd.DataFrame()
    extra = pd.DataFrame()
    cand_summary = pd.DataFrame()
    latest_m15_time = ""
    detected_rows = 0
    stage51_rows = 0
    stage51_missing_count = 0
    extra_condition_rows = 0
    latest_candidate_count = 0
    candidate_count = 0
    q70_joined_rows = 0
    q70_missing_rows = 0

    if not blockers:
        try:
            st45 = load_stage45(p45)
            m15, _m5 = st45.prepare(cdir, "closed", 60, 0.70)
            q = read_csv(p50q)
            q["m15_time_jst"] = pd.to_datetime(q["m15_time_jst"], errors="coerce")
            q = q.dropna(subset=["m15_time_jst"]).drop_duplicates("m15_time_jst")
            m15 = m15.drop(columns=["m15_atr28_q", "is_high_vol"], errors="ignore")
            m15 = m15.merge(q[["m15_time_jst", "atr28_q70", "high_vol_pass"]], left_on="time", right_on="m15_time_jst", how="left")
            q70_joined_rows = int(m15["atr28_q70"].notna().sum())
            q70_missing_rows = int(m15["atr28_q70"].isna().sum())
            m15["m15_atr28_q"] = pd.to_numeric(m15["atr28_q70"], errors="coerce")
            m15["is_high_vol"] = m15["high_vol_pass"].fillna(False).astype(bool)
            latest_m15_time = str(pd.to_datetime(m15["time"], errors="coerce").max())
            cands = st45.base_candidates()
            all_cands = cands + st45.add_hv_siblings(cands)
            raw = st45.opportunities(m15, all_cands)
            if raw.empty:
                detected = pd.DataFrame()
            else:
                raw = period(raw, a.start_jst, a.end_jst)
                detected = add_key_columns(raw)
                detected["m15_time_jst"] = detected["entry_dt"]
                detected = detected.sort_values(["entry_dt", "priority", "candidate_label", "source_rank"]).reset_index(drop=True)
                detected["condition_id"] = [f"GOLDV3_69_COND_{i:09d}" for i in range(len(detected))]
            detected_rows = int(len(detected))
            candidate_count = int(detected["candidate_key"].nunique()) if not detected.empty else 0
            detected.to_csv(out / "gold_v3_69_detected_candidate_conditions.csv", index=False, encoding="utf-8-sig")
            if not detected.empty:
                lt = pd.to_datetime(latest_m15_time)
                latest = detected[pd.to_datetime(detected["entry_dt"], errors="coerce").eq(lt)].copy()
            latest_candidate_count = int(len(latest))
            latest.to_csv(out / "gold_v3_69_latest_closed_condition_candidates.csv", index=False, encoding="utf-8-sig")

            s51df = read_csv(p51)
            s51df = add_key_columns(s51df)
            stage51_rows = int(len(s51df))
            det_key = detected[["entry_dt", "candidate_key", "condition_id"]].copy() if not detected.empty else pd.DataFrame(columns=["entry_dt", "candidate_key", "condition_id"])
            det_key["entry_dt"] = pd.to_datetime(det_key["entry_dt"], errors="coerce")
            s51_key = s51df[["opportunity_id", "entry_dt", "candidate_key"]].copy()
            s51_key["entry_dt"] = pd.to_datetime(s51_key["entry_dt"], errors="coerce")
            parity = s51_key.merge(det_key, on=["entry_dt", "candidate_key"], how="left")
            parity["detected"] = parity["condition_id"].notna()
            stage51_missing_count = int((~parity["detected"]).sum())
            parity.to_csv(out / "gold_v3_69_stage51_detection_parity.csv", index=False, encoding="utf-8-sig")

            if not detected.empty:
                s51_pairs = s51_key[["entry_dt", "candidate_key"]].drop_duplicates().copy()
                det_all = detected.copy()
                det_all["entry_dt"] = pd.to_datetime(det_all["entry_dt"], errors="coerce")
                extra = det_all.merge(s51_pairs.assign(_in_stage51=True), on=["entry_dt", "candidate_key"], how="left")
                extra = extra[extra["_in_stage51"].isna()].drop(columns=["_in_stage51"], errors="ignore")
            extra_condition_rows = int(len(extra))
            extra.to_csv(out / "gold_v3_69_detector_extra_conditions.csv", index=False, encoding="utf-8-sig")
            cand_summary = detected.groupby(["candidate_key", "candidate_label"], dropna=False).size().rename("detected_count").reset_index() if not detected.empty else pd.DataFrame(columns=["candidate_key", "candidate_label", "detected_count"])
            cand_summary.to_csv(out / "gold_v3_69_candidate_condition_summary.csv", index=False, encoding="utf-8-sig")

            val.append(ok("stage45_import_ok", True, str(p45), "importable"))
            val.append(ok("q70_joined_rows_positive", q70_joined_rows > 0, q70_joined_rows, ">0"))
            val.append(ok("detected_conditions_nonempty", detected_rows > 0, detected_rows, ">0"))
            val.append(ok("stage51_rows_positive", stage51_rows > 0, stage51_rows, ">0"))
            val.append(ok("stage51_all_rows_detected", stage51_missing_count == 0, stage51_missing_count, 0))
            val.append(ok("latest_closed_m15_evaluated", latest_m15_time != "", latest_m15_time, "nonempty latest closed time"))
            val.append(ok("candidate_count_at_least_stage68", candidate_count >= int(j68.get("candidate_count", 0)), candidate_count, f">={int(j68.get('candidate_count', 0))}"))
            if stage51_missing_count != 0:
                blockers.append(blocker("stage51_detection_parity_failed", str(p51), "STAGE51_ROWS_NOT_DETECTED_FROM_LIVE_CSV_CONDITIONS", {"missing": stage51_missing_count, "stage51_rows": stage51_rows, "detected_rows": detected_rows}))
        except Exception as e:
            val.append(ok("stage45_detection_runtime", False, repr(e), "no_exception"))
            blockers.append(blocker("stage45_detection_runtime_error", str(p45), "DETECTOR_RUNTIME_EXCEPTION", repr(e)))
    else:
        for fname in [
            "gold_v3_69_detected_candidate_conditions.csv",
            "gold_v3_69_latest_closed_condition_candidates.csv",
            "gold_v3_69_stage51_detection_parity.csv",
            "gold_v3_69_detector_extra_conditions.csv",
            "gold_v3_69_candidate_condition_summary.csv",
        ]:
            (out / fname).write_text("", encoding="utf-8")

    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
    val.append(ok("no_ohlc_re_adjudication", True, "not_used", "not_used"))
    val.append(ok("stage45_evaluate_not_called", True, "not_called", "not_called"))
    val.append(ok("live_flags_all_false", True, "all_false", "all_false"))

    pd.DataFrame(blockers).to_csv(out / "gold_v3_69_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty and not blockers else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_69_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "live_csv_condition_detector_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "candidate_key_source": "+".join(KEY_COLS),
        "latest_closed_m15_time": latest_m15_time,
        "detected_condition_rows": detected_rows,
        "latest_closed_condition_candidate_rows": latest_candidate_count,
        "stage51_rows": stage51_rows,
        "stage51_missing_detection_count": stage51_missing_count,
        "detector_extra_condition_rows": extra_condition_rows,
        "candidate_count": candidate_count,
        "q70_joined_rows": q70_joined_rows,
        "q70_missing_rows": q70_missing_rows,
        "validation_failure_count": int(len(failed)),
        "blocker_count": int(len(blockers)),
    }
    (out / "gold_v3_69_live_csv_condition_detector_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste: list[str] = []
    paste.append("GOLD V3 69 PASTE_ME_LIVE_CSV_CONDITION_DETECTOR_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("live_csv_condition_detector_ready: " + str(status == READY_STATUS).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("csv_contract: " + CSV_CONTRACT)
    paste.append("csv_open_bar_exclusion_required: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append("pool_policy: " + POOL_POLICY)
    paste.append("candidate_key_source: " + "+".join(KEY_COLS))
    paste.append(f"latest_closed_m15_time: {latest_m15_time}")
    paste.append(f"detected_condition_rows: {detected_rows}")
    paste.append(f"latest_closed_condition_candidate_rows: {latest_candidate_count}")
    paste.append(f"stage51_rows: {stage51_rows}")
    paste.append(f"stage51_missing_detection_count: {stage51_missing_count}")
    paste.append(f"detector_extra_condition_rows: {extra_condition_rows}")
    paste.append(f"candidate_count: {candidate_count}")
    paste.append(f"q70_joined_rows: {q70_joined_rows}")
    paste.append(f"q70_missing_rows: {q70_missing_rows}")
    paste.append(f"blocker_count: {len(blockers)}")
    paste.append("")
    paste.append("BLOCKERS")
    paste.append(pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS")
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_69_detected_candidate_conditions.csv")
    paste.append("gold_v3_69_latest_closed_condition_candidates.csv")
    paste.append("gold_v3_69_stage51_detection_parity.csv")
    paste.append("gold_v3_69_detector_extra_conditions.csv")
    paste.append("gold_v3_69_candidate_condition_summary.csv")
    paste.append("gold_v3_69_blocker_matrix.csv")
    paste.append("gold_v3_69_validation_matrix.csv")
    paste.append("gold_v3_69_live_csv_condition_detector_summary.json")
    (out / "gold_v3_69_PASTE_ME_LIVE_CSV_CONDITION_DETECTOR_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 69 live CSV condition detector audit-only report

Status: `{status}`

## Summary

- latest_closed_m15_time: `{latest_m15_time}`
- detected_condition_rows: `{detected_rows}`
- latest_closed_condition_candidate_rows: `{latest_candidate_count}`
- stage51_rows: `{stage51_rows}`
- stage51_missing_detection_count: `{stage51_missing_count}`
- detector_extra_condition_rows: `{extra_condition_rows}`
- blocker_count: `{len(blockers)}`

## Contract

- candidate_key_source: `{'+'.join(KEY_COLS)}`
- csv_open_bar_exclusion_required: `false`
- pool_policy: `{POOL_POLICY}`
- Stage45 `evaluate()` is not called.

## Safety

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out / "GOLD_V3_69_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_69_PASTE_ME_LIVE_CSV_CONDITION_DETECTOR_SUMMARY.txt")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
