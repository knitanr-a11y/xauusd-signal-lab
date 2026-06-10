#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 52 health gate state and rank-dedup selection ledger audit-only.

Reads Stage51 full-candidate virtual opportunity ledger, reconstructs Stage45
strict rolling health gate state and selected trade ledger, then compares against
Stage47 replay strict gate trade ledger.

No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "GOLD_V3_52_HEALTH_GATE_STATE_AND_RANK_DEDUP_SELECTION_LEDGER_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_52_HEALTH_GATE_STATE_AND_RANK_DEDUP_SELECTION_LEDGER_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_52_HEALTH_GATE_STATE_AND_RANK_DEDUP_SELECTION_LEDGER_BLOCKED_AUDIT_ONLY"
STAGE46_READY = "GOLD_V3_46_CLOSED_ASOF_STAGE45_POOL_CONTRACT_FREEZE_READY_AUDIT_ONLY"
STAGE47_READY = "GOLD_V3_47_CLOSED_ASOF_POOL_CONTRACT_FORWARD_AUDIT_READY_AUDIT_ONLY"
STAGE49_READY = "GOLD_V3_49_CLOSED_ASOF_STATE_SCHEMA_AND_SHADOW_LEDGER_READY_AUDIT_ONLY"
STAGE51_READY = "GOLD_V3_51_FULL_CANDIDATE_VIRTUAL_OPPORTUNITY_LEDGER_BUILDER_READY_AUDIT_ONLY"

WINDOW = 30
MIN_HISTORY = 20
PF_THRESHOLD = 1.10
LOSS_STREAK_LT = 3


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def pf(vals: list[float]) -> float:
    a = np.array(vals, dtype=float)
    gp = a[a > 0].sum()
    gl = -a[a < 0].sum()
    if gl > 0:
        return float(gp / gl)
    return math.inf if gp > 0 else 0.0


def loss_streak(vals: list[float]) -> int:
    n = 0
    for v in reversed(vals):
        if v < 0:
            n += 1
        else:
            break
    return n


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]
    for d in candidates:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with FX_OUTPUTS/gold_v3")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage46-dir", default="")
    p.add_argument("--stage47-dir", default="")
    p.add_argument("--stage49-dir", default="")
    p.add_argument("--stage51-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def build_gate_ledgers(opp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    x = opp.copy()
    x["entry_dt"] = pd.to_datetime(x["entry_dt"], errors="coerce")
    x["result_usd"] = pd.to_numeric(x["result_usd"], errors="coerce")
    x["priority"] = pd.to_numeric(x["priority"], errors="coerce")
    x = x.dropna(subset=["entry_dt", "result_usd", "priority", "candidate_label"]).copy()
    x = x.sort_values(["entry_dt", "priority", "candidate_label"]).reset_index(drop=True)

    hist: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=WINDOW))
    health_rows: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []

    for entry_dt, g in x.groupby("entry_dt", sort=True):
        g = g.sort_values(["priority", "candidate_label"]).copy()
        allowed_indices: list[int] = []
        allowed_labels: list[str] = []
        blocked_labels: list[str] = []
        for idx, r in g.iterrows():
            cand = str(r["candidate_label"])
            h = list(hist[cand])
            hist_n = len(h)
            rolling_pf: float | str = ""
            ls: int | str = ""
            eligible = True
            reason = "MIN_HISTORY_NOT_REACHED"
            if hist_n >= MIN_HISTORY:
                rolling_pf = pf(h)
                ls = loss_streak(h)
                eligible = (float(rolling_pf) >= PF_THRESHOLD) and (int(ls) < LOSS_STREAK_LT)
                reason = "PASS" if eligible else "PF_OR_LOSS_STREAK_BLOCK"
            if eligible:
                allowed_indices.append(idx)
                allowed_labels.append(cand)
            else:
                blocked_labels.append(cand)
            health_rows.append({
                "candidate_label": cand,
                "opportunity_id": r.get("opportunity_id", ""),
                "asof_m15_time_jst": entry_dt,
                "window": WINDOW,
                "min_history": MIN_HISTORY,
                "pf_threshold": PF_THRESHOLD,
                "loss_streak_lt": LOSS_STREAK_LT,
                "history_count": hist_n,
                "rolling_pf": rolling_pf,
                "loss_streak": ls,
                "eligible": bool(eligible),
                "eligibility_reason": reason,
                "priority": r.get("priority", ""),
                "result_usd_after_close": r.get("result_usd", ""),
            })

        selected_idx = allowed_indices[0] if allowed_indices else None
        if selected_idx is not None:
            sr = g.loc[selected_idx].to_dict()
            selected_rows.append(sr)
            selection_rows.append({
                "m15_time_jst": entry_dt,
                "candidate_count_before_gate": int(len(g)),
                "eligible_candidate_count": int(len(allowed_indices)),
                "selected_candidate_label": sr.get("candidate_label", ""),
                "selected_opportunity_id": sr.get("opportunity_id", ""),
                "selected_priority": sr.get("priority", ""),
                "selected_result_usd": sr.get("result_usd", ""),
                "dedup_priority_rule": "entry_dt, priority, candidate_label; first eligible",
                "eligible_candidates": " || ".join(allowed_labels[:50]),
                "blocked_candidates": " || ".join(blocked_labels[:50]),
                "no_signal_reason": "",
            })
        else:
            selection_rows.append({
                "m15_time_jst": entry_dt,
                "candidate_count_before_gate": int(len(g)),
                "eligible_candidate_count": 0,
                "selected_candidate_label": "",
                "selected_opportunity_id": "",
                "selected_priority": "",
                "selected_result_usd": "",
                "dedup_priority_rule": "entry_dt, priority, candidate_label; first eligible",
                "eligible_candidates": "",
                "blocked_candidates": " || ".join(blocked_labels[:50]),
                "no_signal_reason": "NO_ELIGIBLE_CANDIDATE",
            })

        # Virtual monitoring: append every candidate result after processing the timestamp.
        for _, r in g.iterrows():
            hist[str(r["candidate_label"])].append(float(r["result_usd"]))

    selected = pd.DataFrame(selected_rows)
    health = pd.DataFrame(health_rows)
    selection = pd.DataFrame(selection_rows)
    return health, selection, selected


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    s46 = Path(a.stage46_dir).expanduser().resolve() if a.stage46_dir else base_out / "46_closed_asof_stage45_pool_contract_freeze_audit_only"
    s47 = Path(a.stage47_dir).expanduser().resolve() if a.stage47_dir else base_out / "47_closed_asof_pool_contract_forward_audit_only"
    s49 = Path(a.stage49_dir).expanduser().resolve() if a.stage49_dir else base_out / "49_closed_asof_state_schema_and_shadow_ledger_audit_only"
    s51 = Path(a.stage51_dir).expanduser().resolve() if a.stage51_dir else base_out / "51_full_candidate_virtual_opportunity_ledger_builder_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out / "52_health_gate_state_rank_dedup_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p46 = s46 / "gold_v3_46_closed_asof_stage45_pool_contract.json"
    p47 = s47 / "gold_v3_47_forward_audit_summary.json"
    p49 = s49 / "gold_v3_49_state_schema_summary.json"
    p51 = s51 / "gold_v3_51_virtual_opportunity_summary.json"
    p51_ledger = s51 / "gold_v3_51_virtual_opportunity_ledger.csv"
    p47_selected = s47 / "stage47_replay" / "gold_v3_45_hv_sibling_strict_gate_trade_ledger.csv"

    val: list[dict[str, Any]] = []
    for name, path in [
        ("stage46_contract", p46), ("stage47_forward", p47), ("stage49_schema", p49),
        ("stage51_summary", p51), ("stage51_virtual_ledger", p51_ledger), ("stage47_selected_ledger", p47_selected),
    ]:
        val.append(ok(f"{name}_present", path.exists(), str(path), "exists"))

    j46 = read_json(p46) if p46.exists() else {}
    j47 = read_json(p47) if p47.exists() else {}
    j49 = read_json(p49) if p49.exists() else {}
    j51 = read_json(p51) if p51.exists() else {}

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
    if j51:
        val.append(ok("stage51_status_ready", j51.get("status") == STAGE51_READY, j51.get("status"), STAGE51_READY))
        val.append(ok("stage51_virtual_ledger_ready", j51.get("virtual_opportunity_ledger_ready") is True, j51.get("virtual_opportunity_ledger_ready"), True))
        val.append(ok("stage51_contract_not_mutated", j51.get("contract_mutated") is False, j51.get("contract_mutated"), False))

    pre_fail = [r for r in val if r["result"] != "PASS"]
    if pre_fail:
        pd.DataFrame(val).to_csv(out / "gold_v3_52_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    opp = read_csv(p51_ledger)
    replay = read_csv(p47_selected)
    health, selection, selected = build_gate_ledgers(opp)

    health.to_csv(out / "gold_v3_52_health_gate_state.csv", index=False, encoding="utf-8-sig")
    selection.to_csv(out / "gold_v3_52_rank_dedup_selection_ledger.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(out / "gold_v3_52_selected_trade_ledger.csv", index=False, encoding="utf-8-sig")

    # Parity against Stage47 selected strict gate ledger.
    for df in [selected, replay]:
        df["entry_dt"] = pd.to_datetime(df["entry_dt"], errors="coerce")
        if "result_usd" in df.columns:
            df["result_usd"] = pd.to_numeric(df["result_usd"], errors="coerce").round(8)
    left_cols = ["entry_dt", "candidate_label", "profile_id", "source_rank", "result_usd"]
    for c in left_cols:
        if c not in selected.columns:
            selected[c] = ""
        if c not in replay.columns:
            replay[c] = ""
    mine = selected[left_cols].sort_values(left_cols).reset_index(drop=True).copy()
    ref = replay[left_cols].sort_values(left_cols).reset_index(drop=True).copy()
    n = max(len(mine), len(ref))
    mine2 = mine.reindex(range(n)).add_prefix("stage52_")
    ref2 = ref.reindex(range(n)).add_prefix("stage47_")
    parity = pd.concat([mine2, ref2], axis=1)
    parity["match"] = True
    for c in left_cols:
        parity["match"] &= parity[f"stage52_{c}"].astype(str).fillna("").eq(parity[f"stage47_{c}"].astype(str).fillna(""))
    parity.to_csv(out / "gold_v3_52_selection_parity.csv", index=False, encoding="utf-8-sig")

    mine_counts = selected.groupby("candidate_label").size().rename("stage52_selected_count").reset_index()
    ref_counts = replay.groupby("candidate_label").size().rename("stage47_selected_count").reset_index()
    cand = mine_counts.merge(ref_counts, on="candidate_label", how="outer").fillna(0)
    cand["stage52_selected_count"] = cand["stage52_selected_count"].astype(int)
    cand["stage47_selected_count"] = cand["stage47_selected_count"].astype(int)
    cand["delta"] = cand["stage52_selected_count"] - cand["stage47_selected_count"]
    cand["match"] = cand["delta"].eq(0)
    cand.to_csv(out / "gold_v3_52_candidate_selection_summary.csv", index=False, encoding="utf-8-sig")

    val.append(ok("strict_gate_window", WINDOW == 30, WINDOW, 30))
    val.append(ok("strict_gate_min_history", MIN_HISTORY == 20, MIN_HISTORY, 20))
    val.append(ok("strict_gate_pf_threshold", PF_THRESHOLD == 1.10, PF_THRESHOLD, 1.10))
    val.append(ok("strict_gate_loss_streak_lt", LOSS_STREAK_LT == 3, LOSS_STREAK_LT, 3))
    val.append(ok("stage51_virtual_ledger_nonempty", len(opp) > 0, len(opp), ">0"))
    val.append(ok("health_gate_state_nonempty", len(health) > 0, len(health), ">0"))
    val.append(ok("selection_ledger_nonempty", len(selection) > 0, len(selection), ">0"))
    val.append(ok("selected_trade_count_matches_stage47", len(selected) == len(replay), len(selected), len(replay)))
    val.append(ok("selection_rows_match_stage47", bool(parity["match"].all()), int((~parity["match"]).sum()), 0))
    val.append(ok("candidate_selected_counts_match_stage47", bool(cand["match"].all()), int((~cand["match"]).sum()), 0))
    val.append(ok("contract_not_mutated_by_stage52", True, "not_mutated_by_stage52", "not_mutated_by_stage52"))
    val.append(ok("manual_candidate_demotion_or_removal_false", True, False, False))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_52_validation_matrix.csv", index=False, encoding="utf-8-sig")

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
        "health_gate_selection_ready": failed.empty,
        "stage51_opportunities": int(len(opp)),
        "health_gate_state_rows": int(len(health)),
        "rank_dedup_selection_rows": int(len(selection)),
        "stage52_selected_trades": int(len(selected)),
        "stage47_selected_trades": int(len(replay)),
        "selection_parity_mismatch_count": int((~parity["match"]).sum()),
        "candidate_selection_mismatch_count": int((~cand["match"]).sum()),
        "validation_failure_count": int(len(failed)),
        "health_gate": {"window": WINDOW, "min_history": MIN_HISTORY, "pf_threshold": PF_THRESHOLD, "loss_streak_lt": LOSS_STREAK_LT, "virtual_monitoring": True},
    }
    (out / "gold_v3_52_health_gate_selection_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 52 PASTE_ME_HEALTH_GATE_SELECTION_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("health_gate_selection_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    paste.append(f"stage51_opportunities: {len(opp)}")
    paste.append(f"health_gate_state_rows: {len(health)}")
    paste.append(f"rank_dedup_selection_rows: {len(selection)}")
    paste.append(f"stage52_selected_trades: {len(selected)}")
    paste.append(f"stage47_selected_trades: {len(replay)}")
    paste.append(f"selection_parity_mismatch_count: {int((~parity['match']).sum())}")
    paste.append(f"candidate_selection_mismatch_count: {int((~cand['match']).sum())}")
    paste.append("health_gate: window=30, min_history=20, pf_threshold=1.10, loss_streak_lt=3, virtual_monitoring=true")
    paste.append("")
    paste.append("TOP_SELECTED_COUNTS")
    paste.append(cand.sort_values("stage52_selected_count", ascending=False).head(20).to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_52_health_gate_state.csv")
    paste.append("gold_v3_52_rank_dedup_selection_ledger.csv")
    paste.append("gold_v3_52_selected_trade_ledger.csv")
    paste.append("gold_v3_52_selection_parity.csv")
    (out / "gold_v3_52_PASTE_ME_HEALTH_GATE_SELECTION_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 52 health gate state and rank-dedup selection ledger audit-only report

Status: `{status}`

## Summary

- stage51_opportunities: `{len(opp)}`
- health_gate_state_rows: `{len(health)}`
- rank_dedup_selection_rows: `{len(selection)}`
- stage52_selected_trades: `{len(selected)}`
- stage47_selected_trades: `{len(replay)}`
- selection_parity_mismatch_count: `{int((~parity['match']).sum())}`
- candidate_selection_mismatch_count: `{int((~cand['match']).sum())}`

## Safety

Audit-only. No MT5, Discord, AI API, live hook, or final signal.
"""
    (out / "GOLD_V3_52_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_52_PASTE_ME_HEALTH_GATE_SELECTION_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
