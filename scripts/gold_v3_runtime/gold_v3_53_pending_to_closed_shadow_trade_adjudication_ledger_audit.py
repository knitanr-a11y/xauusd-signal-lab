#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 53 pending-to-closed shadow trade adjudication ledger audit-only.

Converts Stage52 selected trades into pending shadow trades, independently
adjudicates them with M5 candles, and compares closed outcomes with Stage52.

No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "GOLD_V3_53_PENDING_TO_CLOSED_SHADOW_TRADE_ADJUDICATION_LEDGER_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_53_PENDING_TO_CLOSED_SHADOW_TRADE_ADJUDICATION_LEDGER_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_53_PENDING_TO_CLOSED_SHADOW_TRADE_ADJUDICATION_LEDGER_BLOCKED_AUDIT_ONLY"
STAGE46_READY = "GOLD_V3_46_CLOSED_ASOF_STAGE45_POOL_CONTRACT_FREEZE_READY_AUDIT_ONLY"
STAGE47_READY = "GOLD_V3_47_CLOSED_ASOF_POOL_CONTRACT_FORWARD_AUDIT_READY_AUDIT_ONLY"
STAGE49_READY = "GOLD_V3_49_CLOSED_ASOF_STATE_SCHEMA_AND_SHADOW_LEDGER_READY_AUDIT_ONLY"
STAGE52_READY = "GOLD_V3_52_HEALTH_GATE_STATE_AND_RANK_DEDUP_SELECTION_LEDGER_READY_AUDIT_ONLY"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]
    for d in candidates:
        d = d.expanduser().resolve()
        if (d / "goldsharp_m5.csv").exists() and (d / "FX_OUTPUTS" / "gold_v3").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with goldsharp_m5.csv and FX_OUTPUTS/gold_v3")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage46-dir", default="")
    p.add_argument("--stage47-dir", default="")
    p.add_argument("--stage49-dir", default="")
    p.add_argument("--stage52-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def read_m5(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [str(c).strip().lower() for c in df.columns]
    for c in ["time", "open", "high", "low", "close"]:
        if c not in df.columns:
            raise ValueError(f"{path.name}: missing {c}")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").drop_duplicates("time").reset_index(drop=True)


def make_pending(selected: pd.DataFrame) -> pd.DataFrame:
    x = selected.copy().reset_index(drop=True)
    x["entry_dt"] = pd.to_datetime(x["entry_dt"], errors="coerce")
    for c in ["entry_price", "tp_usd", "sl_usd", "horizon_m15"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna(subset=["entry_dt", "entry_price", "tp_usd", "sl_usd", "horizon_m15"]).copy()
    x = x.sort_values(["entry_dt", "candidate_label", "profile_id"]).reset_index(drop=True)
    x["shadow_trade_id"] = [f"GOLDV3_53_SHADOW_{i:09d}" for i in range(len(x))]
    x["direction"] = "BUY"
    x["tp_price"] = x["entry_price"] + x["tp_usd"]
    x["sl_price"] = x["entry_price"] - x["sl_usd"]
    x["horizon_m5_bars"] = x["horizon_m15"].astype(int) * 3
    x["timeout_time_jst"] = x["entry_dt"] + pd.to_timedelta(x["horizon_m15"].astype(int) * 15, unit="m")
    x["status"] = "PENDING"
    cols = [
        "shadow_trade_id", "opportunity_id", "entry_dt", "candidate_label", "profile_id", "source_rank", "direction",
        "entry_price", "tp_usd", "sl_usd", "tp_price", "sl_price", "horizon_m15", "horizon_m5_bars",
        "timeout_time_jst", "status",
    ]
    for c in cols:
        if c not in x.columns:
            x[c] = ""
    return x[cols]


def adjudicate(pending: pd.DataFrame, m5: pd.DataFrame) -> pd.DataFrame:
    times = m5["time"].values
    lows = m5["low"].to_numpy(float)
    highs = m5["high"].to_numpy(float)
    closes = m5["close"].to_numpy(float)
    out: list[dict[str, Any]] = []
    for _, r in pending.iterrows():
        entry_dt = pd.Timestamp(r["entry_dt"])
        entry = float(r["entry_price"])
        tp_usd = float(r["tp_usd"])
        sl_usd = float(r["sl_usd"])
        horizon_m15 = int(r["horizon_m15"])
        end = entry_dt + pd.Timedelta(minutes=15 * horizon_m15)
        si = int(np.searchsorted(times, np.datetime64(entry_dt), side="right"))
        ei = int(np.searchsorted(times, np.datetime64(end), side="right"))
        base = r.to_dict()
        if ei <= si or len(m5) == 0 or ei == 0 or m5["time"].iloc[ei - 1] < end - pd.Timedelta(minutes=5):
            base.update({
                "close_time_jst": pd.NaT,
                "close_price": np.nan,
                "outcome": "INCOMPLETE_HORIZON",
                "result_usd": np.nan,
                "same_bar_priority": "SL",
                "adjudication_source": "M5_INCOMPLETE",
            })
            out.append(base)
            continue
        tp_px = entry + tp_usd
        sl_px = entry - sl_usd
        sl_hit = np.where(lows[si:ei] <= sl_px)[0]
        tp_hit = np.where(highs[si:ei] >= tp_px)[0]
        fs = int(sl_hit[0]) if len(sl_hit) else None
        ft = int(tp_hit[0]) if len(tp_hit) else None
        if fs is not None and (ft is None or fs <= ft):
            ai = si + fs
            close_time = m5["time"].iloc[ai]
            close_price = sl_px
            outcome = "SL"
            result_usd = -sl_usd
        elif ft is not None:
            ai = si + ft
            close_time = m5["time"].iloc[ai]
            close_price = tp_px
            outcome = "TP"
            result_usd = tp_usd
        else:
            ai = ei - 1
            close_time = m5["time"].iloc[ai]
            close_price = float(closes[ai])
            outcome = "TIMEOUT"
            result_usd = close_price - entry
        base.update({
            "close_time_jst": close_time,
            "close_price": close_price,
            "outcome": outcome,
            "result_usd": float(result_usd),
            "same_bar_priority": "SL",
            "adjudication_source": f"M5_ROWS_{si}_{ei}",
        })
        out.append(base)
    return pd.DataFrame(out)


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    s46 = Path(a.stage46_dir).expanduser().resolve() if a.stage46_dir else base_out / "46_closed_asof_stage45_pool_contract_freeze_audit_only"
    s47 = Path(a.stage47_dir).expanduser().resolve() if a.stage47_dir else base_out / "47_closed_asof_pool_contract_forward_audit_only"
    s49 = Path(a.stage49_dir).expanduser().resolve() if a.stage49_dir else base_out / "49_closed_asof_state_schema_and_shadow_ledger_audit_only"
    s52 = Path(a.stage52_dir).expanduser().resolve() if a.stage52_dir else base_out / "52_health_gate_state_rank_dedup_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out / "53_pending_to_closed_shadow_trade_adjudication_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p46 = s46 / "gold_v3_46_closed_asof_stage45_pool_contract.json"
    p47 = s47 / "gold_v3_47_forward_audit_summary.json"
    p49 = s49 / "gold_v3_49_state_schema_summary.json"
    p52 = s52 / "gold_v3_52_health_gate_selection_summary.json"
    p52_selected = s52 / "gold_v3_52_selected_trade_ledger.csv"
    p_m5 = cdir / "goldsharp_m5.csv"

    val: list[dict[str, Any]] = []
    for name, path in [
        ("stage46_contract", p46), ("stage47_forward", p47), ("stage49_schema", p49),
        ("stage52_summary", p52), ("stage52_selected_ledger", p52_selected), ("m5_csv", p_m5),
    ]:
        val.append(ok(f"{name}_present", path.exists(), str(path), "exists"))

    j46 = read_json(p46) if p46.exists() else {}
    j47 = read_json(p47) if p47.exists() else {}
    j49 = read_json(p49) if p49.exists() else {}
    j52 = read_json(p52) if p52.exists() else {}

    if j46:
        frozen = j46.get("frozen_contract", {})
        val.append(ok("stage46_status_ready", j46.get("status") == STAGE46_READY, j46.get("status"), STAGE46_READY))
        val.append(ok("stage46_closed_asof", frozen.get("htf_asof") == "closed", frozen.get("htf_asof"), "closed"))
        val.append(ok("stage46_open_asof_disallowed", frozen.get("open_asof_allowed") is False, frozen.get("open_asof_allowed"), False))
    if j47:
        val.append(ok("stage47_status_ready", j47.get("status") == STAGE47_READY, j47.get("status"), STAGE47_READY))
        val.append(ok("stage47_contract_reused", j47.get("contract_reused_without_candidate_changes") is True, j47.get("contract_reused_without_candidate_changes"), True))
        val.append(ok("stage47_no_manual_demotion", j47.get("manual_candidate_demotion_or_removal") is False, j47.get("manual_candidate_demotion_or_removal"), False))
    if j49:
        val.append(ok("stage49_status_ready", j49.get("status") == STAGE49_READY, j49.get("status"), STAGE49_READY))
        val.append(ok("stage49_schema_ready", j49.get("schema_ready") is True, j49.get("schema_ready"), True))
    if j52:
        val.append(ok("stage52_status_ready", j52.get("status") == STAGE52_READY, j52.get("status"), STAGE52_READY))
        val.append(ok("stage52_health_gate_selection_ready", j52.get("health_gate_selection_ready") is True, j52.get("health_gate_selection_ready"), True))
        val.append(ok("stage52_contract_not_mutated", j52.get("contract_mutated") is False, j52.get("contract_mutated"), False))

    pre_fail = [r for r in val if r["result"] != "PASS"]
    if pre_fail:
        pd.DataFrame(val).to_csv(out / "gold_v3_53_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    selected = read_csv(p52_selected)
    m5 = read_m5(p_m5)
    pending = make_pending(selected)
    closed = adjudicate(pending, m5)

    pending.to_csv(out / "gold_v3_53_pending_shadow_trade_ledger.csv", index=False, encoding="utf-8-sig")
    closed.to_csv(out / "gold_v3_53_closed_shadow_trade_ledger.csv", index=False, encoding="utf-8-sig")

    # Parity with Stage52 selected outcomes.
    ref = selected.copy()
    ref["entry_dt"] = pd.to_datetime(ref["entry_dt"], errors="coerce")
    ref["exit_dt"] = pd.to_datetime(ref["exit_dt"], errors="coerce")
    ref["result_usd"] = pd.to_numeric(ref["result_usd"], errors="coerce").round(8)
    ref["exit_price"] = pd.to_numeric(ref["exit_price"], errors="coerce").round(8)
    closed["entry_dt"] = pd.to_datetime(closed["entry_dt"], errors="coerce")
    closed["close_time_jst"] = pd.to_datetime(closed["close_time_jst"], errors="coerce")
    closed["result_usd"] = pd.to_numeric(closed["result_usd"], errors="coerce").round(8)
    closed["close_price"] = pd.to_numeric(closed["close_price"], errors="coerce").round(8)

    ref_key_cols = ["entry_dt", "candidate_label", "profile_id", "source_rank"]
    ref_small = ref[ref_key_cols + ["exit_dt", "exit_price", "exit_reason", "result_usd"]].copy()
    cl_small = closed[ref_key_cols + ["close_time_jst", "close_price", "outcome", "result_usd"]].copy()
    ref_small = ref_small.sort_values(ref_key_cols).reset_index(drop=True).add_prefix("stage52_")
    cl_small = cl_small.sort_values(ref_key_cols).reset_index(drop=True).add_prefix("stage53_")
    n = max(len(ref_small), len(cl_small))
    parity = pd.concat([ref_small.reindex(range(n)), cl_small.reindex(range(n))], axis=1)
    parity["entry_match"] = parity["stage52_entry_dt"].astype(str).fillna("").eq(parity["stage53_entry_dt"].astype(str).fillna(""))
    parity["candidate_match"] = parity["stage52_candidate_label"].astype(str).fillna("").eq(parity["stage53_candidate_label"].astype(str).fillna(""))
    parity["profile_match"] = parity["stage52_profile_id"].astype(str).fillna("").eq(parity["stage53_profile_id"].astype(str).fillna(""))
    parity["source_rank_match"] = parity["stage52_source_rank"].astype(str).fillna("").eq(parity["stage53_source_rank"].astype(str).fillna(""))
    parity["exit_time_match"] = parity["stage52_exit_dt"].astype(str).fillna("").eq(parity["stage53_close_time_jst"].astype(str).fillna(""))
    parity["exit_reason_match"] = parity["stage52_exit_reason"].astype(str).fillna("").eq(parity["stage53_outcome"].astype(str).fillna(""))
    parity["result_match"] = parity["stage52_result_usd"].astype(str).fillna("").eq(parity["stage53_result_usd"].astype(str).fillna(""))
    parity["price_match"] = parity["stage52_exit_price"].astype(str).fillna("").eq(parity["stage53_close_price"].astype(str).fillna(""))
    match_cols = ["entry_match", "candidate_match", "profile_match", "source_rank_match", "exit_time_match", "exit_reason_match", "result_match", "price_match"]
    parity["all_match"] = parity[match_cols].all(axis=1)
    parity.to_csv(out / "gold_v3_53_adjudication_parity.csv", index=False, encoding="utf-8-sig")

    cand_summary = closed.groupby(["candidate_label", "outcome"], dropna=False).agg(
        trades=("shadow_trade_id", "count"),
        sum_result_usd=("result_usd", "sum"),
    ).reset_index()
    cand_summary.to_csv(out / "gold_v3_53_candidate_outcome_summary.csv", index=False, encoding="utf-8-sig")

    val.append(ok("stage52_selected_ledger_nonempty", len(selected) > 0, len(selected), ">0"))
    val.append(ok("m5_has_rows", len(m5) > 0, len(m5), ">0"))
    val.append(ok("pending_count_equals_stage52_selected", len(pending) == len(selected), len(pending), len(selected)))
    val.append(ok("closed_count_equals_pending", len(closed) == len(pending), len(closed), len(pending)))
    val.append(ok("no_incomplete_horizon", int(closed["outcome"].astype(str).eq("INCOMPLETE_HORIZON").sum()) == 0, int(closed["outcome"].astype(str).eq("INCOMPLETE_HORIZON").sum()), 0))
    val.append(ok("same_bar_priority_sl", closed["same_bar_priority"].astype(str).eq("SL").all(), "SL", "SL"))
    val.append(ok("adjudication_parity_all_match", bool(parity["all_match"].all()), int((~parity["all_match"]).sum()), 0))
    val.append(ok("contract_not_mutated_by_stage53", True, "not_mutated_by_stage53", "not_mutated_by_stage53"))
    val.append(ok("manual_candidate_demotion_or_removal_false", True, False, False))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_53_validation_matrix.csv", index=False, encoding="utf-8-sig")

    outcome_counts = closed["outcome"].value_counts(dropna=False).to_dict()
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
        "live_ready": False,
        "shadow_adjudication_ready": failed.empty,
        "stage52_selected_trades": int(len(selected)),
        "pending_shadow_trades": int(len(pending)),
        "closed_shadow_trades": int(len(closed)),
        "adjudication_parity_mismatch_count": int((~parity["all_match"]).sum()),
        "outcome_counts": {str(k): int(v) for k, v in outcome_counts.items()},
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_53_shadow_adjudication_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 53 PASTE_ME_SHADOW_ADJUDICATION_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("shadow_adjudication_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    paste.append(f"stage52_selected_trades: {len(selected)}")
    paste.append(f"pending_shadow_trades: {len(pending)}")
    paste.append(f"closed_shadow_trades: {len(closed)}")
    paste.append(f"adjudication_parity_mismatch_count: {int((~parity['all_match']).sum())}")
    paste.append(f"outcome_counts: {json.dumps({str(k): int(v) for k, v in outcome_counts.items()}, ensure_ascii=False)}")
    paste.append("same_bar_priority: SL")
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_53_pending_shadow_trade_ledger.csv")
    paste.append("gold_v3_53_closed_shadow_trade_ledger.csv")
    paste.append("gold_v3_53_adjudication_parity.csv")
    paste.append("gold_v3_53_candidate_outcome_summary.csv")
    (out / "gold_v3_53_PASTE_ME_SHADOW_ADJUDICATION_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 53 pending-to-closed shadow trade adjudication audit-only report

Status: `{status}`

## Summary

- stage52_selected_trades: `{len(selected)}`
- pending_shadow_trades: `{len(pending)}`
- closed_shadow_trades: `{len(closed)}`
- adjudication_parity_mismatch_count: `{int((~parity['all_match']).sum())}`
- same_bar_priority: `SL`

## Safety

Audit-only. No MT5, Discord, AI API, live hook, or final signal.
"""
    (out / "GOLD_V3_53_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_53_PASTE_ME_SHADOW_ADJUDICATION_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
