#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 54 restart/replay checkpoint state audit-only.

Builds hash/count/time anchors for deterministic audit-only replay.
No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_54_RESTART_REPLAY_CHECKPOINT_STATE_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_54_RESTART_REPLAY_CHECKPOINT_STATE_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_54_RESTART_REPLAY_CHECKPOINT_STATE_BLOCKED_AUDIT_ONLY"
READY = {
    "49": "GOLD_V3_49_CLOSED_ASOF_STATE_SCHEMA_AND_SHADOW_LEDGER_READY_AUDIT_ONLY",
    "50": "GOLD_V3_50_H4_CLOSED_READINESS_AND_PRIOR_60D_Q70_STATE_BUILDER_READY_AUDIT_ONLY",
    "51": "GOLD_V3_51_FULL_CANDIDATE_VIRTUAL_OPPORTUNITY_LEDGER_BUILDER_READY_AUDIT_ONLY",
    "52": "GOLD_V3_52_HEALTH_GATE_STATE_AND_RANK_DEDUP_SELECTION_LEDGER_READY_AUDIT_ONLY",
    "53": "GOLD_V3_53_PENDING_TO_CLOSED_SHADOW_TRADE_ADJUDICATION_LEDGER_READY_AUDIT_ONLY",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3").exists():
            return d
    raise FileNotFoundError("FX_OUTPUTS/gold_v3 not found. Pass --candle-dir.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", errors="replace") as f:
        return max(0, sum(1 for _ in f) - 1)


def max_time(path: Path, col: str) -> str:
    if not path.exists():
        return ""
    try:
        df = pd.read_csv(path, encoding="utf-8-sig", usecols=[col])
    except Exception:
        return ""
    s = pd.to_datetime(df[col], errors="coerce").dropna()
    return str(s.max()) if len(s) else ""


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    g = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else g / "54_restart_replay_checkpoint_state_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    dirs = {
        "49": g / "49_closed_asof_state_schema_and_shadow_ledger_audit_only",
        "50": g / "50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only",
        "51": g / "51_full_candidate_virtual_opportunity_ledger_builder_audit_only",
        "52": g / "52_health_gate_state_rank_dedup_audit_only",
        "53": g / "53_pending_to_closed_shadow_trade_adjudication_audit_only",
    }
    summaries = {
        "49": dirs["49"] / "gold_v3_49_state_schema_summary.json",
        "50": dirs["50"] / "gold_v3_50_state_builder_summary.json",
        "51": dirs["51"] / "gold_v3_51_virtual_opportunity_summary.json",
        "52": dirs["52"] / "gold_v3_52_health_gate_selection_summary.json",
        "53": dirs["53"] / "gold_v3_53_shadow_adjudication_summary.json",
    }
    artifacts = {
        "m5_csv": cdir / "goldsharp_m5.csv",
        "m15_csv": cdir / "goldsharp_m15.csv",
        "h4_csv": cdir / "goldsharp_h4.csv",
        "stage49_manifest": dirs["49"] / "gold_v3_49_state_artifact_manifest.csv",
        "stage50_h4_state": dirs["50"] / "gold_v3_50_h4_closed_readiness_state.csv",
        "stage50_q70_state": dirs["50"] / "gold_v3_50_rolling_prior_60d_q70_state.csv",
        "stage51_virtual_ledger": dirs["51"] / "gold_v3_51_virtual_opportunity_ledger.csv",
        "stage52_health_gate_state": dirs["52"] / "gold_v3_52_health_gate_state.csv",
        "stage52_selection_ledger": dirs["52"] / "gold_v3_52_rank_dedup_selection_ledger.csv",
        "stage52_selected_trade_ledger": dirs["52"] / "gold_v3_52_selected_trade_ledger.csv",
        "stage53_pending_shadow_ledger": dirs["53"] / "gold_v3_53_pending_shadow_trade_ledger.csv",
        "stage53_closed_shadow_ledger": dirs["53"] / "gold_v3_53_closed_shadow_trade_ledger.csv",
    }

    val, js = [], {}
    for st, p in summaries.items():
        val.append(ok(f"stage{st}_summary_present", p.exists(), str(p), "exists"))
        if p.exists():
            js[st] = read_json(p)
            val.append(ok(f"stage{st}_status_ready", js[st].get("status") == READY[st], js[st].get("status"), READY[st]))
            for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
                val.append(ok(f"stage{st}_{key}_false", js[st].get(key) is False, js[st].get(key), False))

    hash_rows = []
    for name, p in artifacts.items():
        val.append(ok(f"artifact_{name}_present", p.exists(), str(p), "exists"))
        if p.exists():
            hash_rows.append({"artifact_id": name, "path": str(p), "sha256": sha256_file(p), "size_bytes": p.stat().st_size, "row_count_if_csv": csv_rows(p) if p.suffix.lower() == ".csv" else ""})
    hash_df = pd.DataFrame(hash_rows)
    hash_df.to_csv(out / "gold_v3_54_source_artifact_hashes.csv", index=False, encoding="utf-8-sig")

    s51_opp = js.get("51", {}).get("stage51_opportunities")
    s52_opp = js.get("52", {}).get("stage51_opportunities")
    s52_sel = js.get("52", {}).get("stage52_selected_trades")
    s53_sel = js.get("53", {}).get("stage52_selected_trades")
    s53_pending = js.get("53", {}).get("pending_shadow_trades")
    s53_closed = js.get("53", {}).get("closed_shadow_trades")
    val.append(ok("stage51_to_stage52_opportunity_count_match", s51_opp == s52_opp, s51_opp, s52_opp))
    val.append(ok("stage52_to_stage53_trade_count_match", s52_sel == s53_sel == s53_pending == s53_closed, [s52_sel, s53_sel, s53_pending, s53_closed], "all_equal"))
    val.append(ok("stage53_adjudication_parity_zero", js.get("53", {}).get("adjudication_parity_mismatch_count") == 0, js.get("53", {}).get("adjudication_parity_mismatch_count"), 0))

    restart_rows = [
        (1, "h4_closed_readiness_state", "stage50_h4_state", "latest_h4_close_time_jst"),
        (2, "rolling_prior_60d_q70_state", "stage50_q70_state", "m15_time_jst"),
        (3, "virtual_opportunity_ledger", "stage51_virtual_ledger", "m15_time_jst"),
        (4, "health_gate_state", "stage52_health_gate_state", "asof_m15_time_jst"),
        (5, "rank_dedup_selection_ledger", "stage52_selection_ledger", "m15_time_jst"),
        (6, "pending_shadow_trade_ledger", "stage53_pending_shadow_ledger", "entry_dt"),
        (7, "closed_shadow_trade_ledger", "stage53_closed_shadow_ledger", "close_time_jst"),
        (8, "replay_checkpoint_state", "", ""),
    ]
    restart = []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    for order, state, artifact_key, time_col in restart_rows:
        anchor = now if order == 8 else max_time(artifacts[artifact_key], time_col)
        restart.append({"step_order": order, "state": state, "artifact_key": artifact_key, "time_column": time_col, "restart_anchor": anchor})
    restart_df = pd.DataFrame(restart)
    restart_df.to_csv(out / "gold_v3_54_restart_plan.csv", index=False, encoding="utf-8-sig")
    val.append(ok("restart_plan_order_frozen", restart_df["step_order"].tolist() == list(range(1, 9)), restart_df["step_order"].tolist(), list(range(1, 9))))
    val.append(ok("restart_anchors_nonempty", restart_df["restart_anchor"].astype(str).ne("").all(), int(restart_df["restart_anchor"].astype(str).eq("").sum()), 0))
    val.append(ok("artifact_hashes_nonempty", len(hash_df) == len(artifacts) and hash_df["sha256"].astype(str).str.len().gt(0).all(), len(hash_df), len(artifacts)))

    checkpoint = {
        "checkpoint_id": "GOLD_V3_54_CHECKPOINT_000001",
        "created_at_utc": now,
        "audit_only": True,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "discord_live_enabled": False,
        "final_signal_enabled": False,
        "replay_order": " > ".join(restart_df["state"].tolist()),
        "last_virtual_opportunity_m15_time": restart[2]["restart_anchor"],
        "last_selection_m15_time": restart[4]["restart_anchor"],
        "last_pending_entry_time": restart[5]["restart_anchor"],
        "last_closed_exit_time": restart[6]["restart_anchor"],
        "source_file_hashes_json": json.dumps({r["artifact_id"]: r["sha256"] for r in hash_rows}, ensure_ascii=False, sort_keys=True),
    }
    pd.DataFrame([checkpoint]).to_csv(out / "gold_v3_54_replay_checkpoint_state.csv", index=False, encoding="utf-8-sig")

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_54_validation_matrix.csv", index=False, encoding="utf-8-sig")

    summary = {
        "step": STEP, "status": status, "created_at_utc": now, "candle_dir": str(cdir), "output_dir": str(out),
        "audit_only": True, "live_allowed": False, "mt5_execution_enabled": False, "mt5_bat_created": False,
        "discord_live_enabled": False, "ai_api_called": False, "signals_generated": False, "final_signal_enabled": False,
        "contract_mutated": False, "manual_candidate_demotion_or_removal": False, "open_asof_allowed": False, "live_ready": False,
        "checkpoint_ready": failed.empty, "hash_artifact_count": len(hash_df), "restart_plan_steps": len(restart_df),
        "validation_failure_count": int(len(failed)), "stage51_opportunities": s51_opp, "stage52_selected_trades": s52_sel,
        "stage53_closed_shadow_trades": s53_closed,
        "last_virtual_opportunity_m15_time": checkpoint["last_virtual_opportunity_m15_time"],
        "last_selection_m15_time": checkpoint["last_selection_m15_time"],
        "last_pending_entry_time": checkpoint["last_pending_entry_time"],
        "last_closed_exit_time": checkpoint["last_closed_exit_time"],
    }
    (out / "gold_v3_54_checkpoint_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 54 PASTE_ME_CHECKPOINT_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("checkpoint_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, final_signal=false")
    paste.append(f"hash_artifact_count: {len(hash_df)}")
    paste.append(f"restart_plan_steps: {len(restart_df)}")
    paste.append(f"stage51_opportunities: {s51_opp}")
    paste.append(f"stage52_selected_trades: {s52_sel}")
    paste.append(f"stage53_closed_shadow_trades: {s53_closed}")
    paste.append(f"last_virtual_opportunity_m15_time: {checkpoint['last_virtual_opportunity_m15_time']}")
    paste.append(f"last_selection_m15_time: {checkpoint['last_selection_m15_time']}")
    paste.append(f"last_pending_entry_time: {checkpoint['last_pending_entry_time']}")
    paste.append(f"last_closed_exit_time: {checkpoint['last_closed_exit_time']}")
    paste.append("")
    paste.append("RESTART_PLAN")
    paste.append(restart_df.to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_54_replay_checkpoint_state.csv")
    paste.append("gold_v3_54_source_artifact_hashes.csv")
    paste.append("gold_v3_54_restart_plan.csv")
    (out / "gold_v3_54_PASTE_ME_CHECKPOINT_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"# GOLD V3 54 restart/replay checkpoint state audit-only report\n\nStatus: `{status}`\n\nAudit-only. No MT5, Discord, AI API, live hook, or final signal.\n"
    (out / "GOLD_V3_54_REPORT.md").write_text(report, encoding="utf-8")
    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_54_PASTE_ME_CHECKPOINT_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
