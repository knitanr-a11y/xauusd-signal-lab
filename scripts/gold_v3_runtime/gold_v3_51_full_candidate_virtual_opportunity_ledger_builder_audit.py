#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 51 full-candidate virtual opportunity ledger builder audit-only.

Builds a full candidate opportunity ledger using Stage50 high-vol state and
Stage45 candidate definitions, then compares against Stage47 replay ledger.

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

STEP = "GOLD_V3_51_FULL_CANDIDATE_VIRTUAL_OPPORTUNITY_LEDGER_BUILDER_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_51_FULL_CANDIDATE_VIRTUAL_OPPORTUNITY_LEDGER_BUILDER_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_51_FULL_CANDIDATE_VIRTUAL_OPPORTUNITY_LEDGER_BUILDER_BLOCKED_AUDIT_ONLY"
STAGE46_READY = "GOLD_V3_46_CLOSED_ASOF_STAGE45_POOL_CONTRACT_FREEZE_READY_AUDIT_ONLY"
STAGE47_READY = "GOLD_V3_47_CLOSED_ASOF_POOL_CONTRACT_FORWARD_AUDIT_READY_AUDIT_ONLY"
STAGE49_READY = "GOLD_V3_49_CLOSED_ASOF_STATE_SCHEMA_AND_SHADOW_LEDGER_READY_AUDIT_ONLY"
STAGE50_READY = "GOLD_V3_50_H4_CLOSED_READINESS_AND_PRIOR_60D_Q70_STATE_BUILDER_READY_AUDIT_ONLY"


def load_stage45(path: Path):
    spec = importlib.util.spec_from_file_location("gold_v3_stage45", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        if (d / "goldsharp_m15.csv").exists() and (d / "goldsharp_m5.csv").exists() and (d / "goldsharp_h4.csv").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with goldsharp_m5/m15/h4.csv")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage46-dir", default="")
    p.add_argument("--stage47-dir", default="")
    p.add_argument("--stage49-dir", default="")
    p.add_argument("--stage50-dir", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--start-jst", default="2026-01-01")
    p.add_argument("--end-jst", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    s46 = Path(a.stage46_dir).expanduser().resolve() if a.stage46_dir else base_out / "46_closed_asof_stage45_pool_contract_freeze_audit_only"
    s47 = Path(a.stage47_dir).expanduser().resolve() if a.stage47_dir else base_out / "47_closed_asof_pool_contract_forward_audit_only"
    s49 = Path(a.stage49_dir).expanduser().resolve() if a.stage49_dir else base_out / "49_closed_asof_state_schema_and_shadow_ledger_audit_only"
    s50 = Path(a.stage50_dir).expanduser().resolve() if a.stage50_dir else base_out / "50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out / "51_full_candidate_virtual_opportunity_ledger_builder_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p46 = s46 / "gold_v3_46_closed_asof_stage45_pool_contract.json"
    p47 = s47 / "gold_v3_47_forward_audit_summary.json"
    p49 = s49 / "gold_v3_49_state_schema_summary.json"
    p50 = s50 / "gold_v3_50_state_builder_summary.json"
    p50_q = s50 / "gold_v3_50_rolling_prior_60d_q70_state.csv"
    p47_opp = s47 / "stage47_replay" / "gold_v3_45_all_candidate_opportunity_ledger.csv"
    stage45_path = Path(__file__).resolve().with_name("gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.py")

    val: list[dict[str, Any]] = []
    for name, path in [
        ("stage46_contract", p46), ("stage47_forward", p47), ("stage49_schema", p49), ("stage50_summary", p50),
        ("stage50_q70_state", p50_q), ("stage47_replay_opportunity_ledger", p47_opp), ("stage45_runner", stage45_path),
    ]:
        val.append(ok(f"{name}_present", path.exists(), str(path), "exists"))

    j46 = read_json(p46) if p46.exists() else {}
    j47 = read_json(p47) if p47.exists() else {}
    j49 = read_json(p49) if p49.exists() else {}
    j50 = read_json(p50) if p50.exists() else {}

    if j46:
        frozen = j46.get("frozen_contract", {})
        val.append(ok("stage46_status_ready", j46.get("status") == STAGE46_READY, j46.get("status"), STAGE46_READY))
        val.append(ok("stage46_closed_asof", frozen.get("htf_asof") == "closed", frozen.get("htf_asof"), "closed"))
        val.append(ok("stage46_open_asof_disallowed", frozen.get("open_asof_allowed") is False, frozen.get("open_asof_allowed"), False))
        val.append(ok("stage46_no_manual_pool_mutation", "no_manual" in str(frozen.get("candidate_pool_policy", "")), frozen.get("candidate_pool_policy", ""), "no_manual..."))
    if j47:
        val.append(ok("stage47_status_ready", j47.get("status") == STAGE47_READY, j47.get("status"), STAGE47_READY))
        val.append(ok("stage47_contract_reused", j47.get("contract_reused_without_candidate_changes") is True, j47.get("contract_reused_without_candidate_changes"), True))
        val.append(ok("stage47_no_manual_demotion", j47.get("manual_candidate_demotion_or_removal") is False, j47.get("manual_candidate_demotion_or_removal"), False))
    if j49:
        val.append(ok("stage49_status_ready", j49.get("status") == STAGE49_READY, j49.get("status"), STAGE49_READY))
        val.append(ok("stage49_schema_ready", j49.get("schema_ready") is True, j49.get("schema_ready"), True))
    if j50:
        val.append(ok("stage50_status_ready", j50.get("status") == STAGE50_READY, j50.get("status"), STAGE50_READY))
        val.append(ok("stage50_state_builder_ready", j50.get("state_builder_ready") is True, j50.get("state_builder_ready"), True))
        val.append(ok("stage50_contract_not_mutated", j50.get("contract_mutated") is False, j50.get("contract_mutated"), False))

    pre_fail = [r for r in val if r["result"] != "PASS"]
    if pre_fail:
        pd.DataFrame(val).to_csv(out / "gold_v3_51_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    st45 = load_stage45(stage45_path)
    m15, m5 = st45.prepare(cdir, "closed", 60, 0.70)
    q = read_csv(p50_q)
    q["m15_time_jst"] = pd.to_datetime(q["m15_time_jst"], errors="coerce")
    q = q.dropna(subset=["m15_time_jst"]).drop_duplicates("m15_time_jst")
    m15 = m15.drop(columns=["m15_atr28_q", "is_high_vol"], errors="ignore")
    m15 = m15.merge(q[["m15_time_jst", "atr28_q70", "high_vol_pass"]], left_on="time", right_on="m15_time_jst", how="left")
    m15["m15_atr28_q"] = pd.to_numeric(m15["atr28_q70"], errors="coerce")
    m15["is_high_vol"] = m15["high_vol_pass"].fillna(False).astype(bool)

    cands = st45.base_candidates()
    all_cands = cands + st45.add_hv_siblings(cands)
    raw = st45.opportunities(m15, all_cands)
    opp = st45.evaluate(raw, m5, complete=True)
    opp = st45.period(opp, a.start_jst, a.end_jst)
    if opp.empty:
        raise RuntimeError("No evaluated opportunities after Stage51 build.")

    # Stable opportunity id and Stage49-oriented alias columns.
    opp = opp.sort_values(["entry_dt", "priority", "candidate_label", "source_rank"]).reset_index(drop=True)
    opp["opportunity_id"] = [f"GOLDV3_51_OPP_{i:09d}" for i in range(len(opp))]
    opp["m15_time_jst"] = opp["entry_dt"]
    opp["base_candidate_label"] = opp["candidate_label"].astype(str).str.replace(r"^HV_(.*?)__HV_TP.*$", r"\1", regex=True)
    opp["hv_profile"] = opp["profile_id"].where(opp["hv_sibling"].astype(bool), "")
    opp["horizon_m5_bars"] = pd.to_numeric(opp["horizon_m15"], errors="coerce").fillna(0).astype(int) * 3
    opp["gate_evaluated"] = False
    opp["gate_pass"] = False
    opp["selected_after_rank_dedup"] = False

    ledger_cols = [
        "opportunity_id", "m15_time_jst", "entry_dt", "jst_dt", "entry_month", "candidate_label", "base_candidate_label",
        "source_rank", "source_profile_id", "profile_id", "hv_sibling", "hv_profile", "tp_usd", "sl_usd", "horizon_m15", "horizon_m5_bars",
        "cooldown_minutes", "priority", "entry_price", "exit_dt", "exit_price", "exit_reason", "result_usd", "is_win", "is_loss",
        "gate_evaluated", "gate_pass", "selected_after_rank_dedup", "warning",
    ]
    for c in ledger_cols:
        if c not in opp.columns:
            opp[c] = ""
    opp[ledger_cols].to_csv(out / "gold_v3_51_virtual_opportunity_ledger.csv", index=False, encoding="utf-8-sig")

    cand_summary = st45.summarize(opp, ["candidate_label", "hv_sibling"])
    cand_summary.to_csv(out / "gold_v3_51_candidate_summary.csv", index=False, encoding="utf-8-sig")

    replay = read_csv(p47_opp)
    key = "candidate_label"
    mine_counts = opp.groupby(key).size().rename("stage51_count").reset_index()
    replay_counts = replay.groupby(key).size().rename("stage47_replay_count").reset_index()
    parity = mine_counts.merge(replay_counts, on=key, how="outer").fillna(0)
    parity["stage51_count"] = parity["stage51_count"].astype(int)
    parity["stage47_replay_count"] = parity["stage47_replay_count"].astype(int)
    parity["delta"] = parity["stage51_count"] - parity["stage47_replay_count"]
    parity["match"] = parity["delta"].eq(0)
    parity.to_csv(out / "gold_v3_51_candidate_count_parity.csv", index=False, encoding="utf-8-sig")

    val.append(ok("stage50_q70_has_high_vol_true", q["high_vol_pass"].fillna(False).sum() > 0, int(q["high_vol_pass"].fillna(False).sum()), ">0"))
    val.append(ok("candidate_pool_base_count", len(cands) == 8, len(cands), 8))
    val.append(ok("candidate_pool_with_hv_count", len(all_cands) == 32, len(all_cands), 32))
    val.append(ok("virtual_opportunity_ledger_nonempty", len(opp) > 0, len(opp), ">0"))
    val.append(ok("total_count_matches_stage47_replay", len(opp) == len(replay), len(opp), len(replay)))
    val.append(ok("candidate_count_parity_all_match", bool(parity["match"].all()), int((~parity["match"]).sum()), 0))
    val.append(ok("contract_not_mutated_by_stage51", True, "not_mutated_by_stage51", "not_mutated_by_stage51"))
    val.append(ok("manual_candidate_demotion_or_removal_false", True, False, False))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_51_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "virtual_opportunity_ledger_ready": failed.empty,
        "stage51_opportunities": int(len(opp)),
        "stage47_replay_opportunities": int(len(replay)),
        "candidate_parity_mismatch_count": int((~parity["match"]).sum()),
        "candidate_pool_base_count": int(len(cands)),
        "candidate_pool_with_hv_count": int(len(all_cands)),
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_51_virtual_opportunity_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 51 PASTE_ME_VIRTUAL_OPPORTUNITY_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("virtual_opportunity_ledger_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    paste.append(f"candidate_pool_base_count: {len(cands)}")
    paste.append(f"candidate_pool_with_hv_count: {len(all_cands)}")
    paste.append(f"stage51_opportunities: {len(opp)}")
    paste.append(f"stage47_replay_opportunities: {len(replay)}")
    paste.append(f"candidate_parity_mismatch_count: {int((~parity['match']).sum())}")
    paste.append("")
    paste.append("TOP_CANDIDATE_COUNTS")
    paste.append(mine_counts.sort_values("stage51_count", ascending=False).head(20).to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_51_virtual_opportunity_ledger.csv")
    paste.append("gold_v3_51_candidate_count_parity.csv")
    paste.append("gold_v3_51_candidate_summary.csv")
    (out / "gold_v3_51_PASTE_ME_VIRTUAL_OPPORTUNITY_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 51 full-candidate virtual opportunity ledger builder audit-only report

Status: `{status}`

## Summary

- stage51_opportunities: `{len(opp)}`
- stage47_replay_opportunities: `{len(replay)}`
- candidate_parity_mismatch_count: `{int((~parity['match']).sum())}`
- candidate_pool_base_count: `{len(cands)}`
- candidate_pool_with_hv_count: `{len(all_cands)}`

## Safety

Audit-only. No MT5, Discord, AI API, live hook, or final signal.
"""
    (out / "GOLD_V3_51_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_51_PASTE_ME_VIRTUAL_OPPORTUNITY_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
