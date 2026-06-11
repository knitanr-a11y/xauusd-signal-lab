#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json
from pathlib import Path
from typing import Any
import pandas as pd

READY = "GOLD_V3_100_NO_SIGNAL_REASON_BREAKDOWN_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_100_NO_SIGNAL_REASON_BREAKDOWN_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "99c" / "replay_results.csv").exists():
            return d
    raise SystemExit("Files dir with Stage99 output not found")


def rj(p: Path) -> dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception as e:
        return {"_error": repr(e)}


def rcsv(p: Path) -> pd.DataFrame:
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(p, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame()


def vrow(cid: str, passed: bool, obs: Any, exp: Any, sev: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": cid, "result": "PASS" if passed else "FAIL", "observed": obs, "expected": exp, "severity": sev}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candle-dir", default="")
    ap.add_argument("--stage99-dir", default="")
    ap.add_argument("--output-dir", default="")
    args = ap.parse_args()

    src = Path(args.candle_dir).resolve() if args.candle_dir else find_files_dir()
    base = src / "FX_OUTPUTS" / "gold_v3"
    s99 = Path(args.stage99_dir).resolve() if args.stage99_dir else base / "99c"
    out = Path(args.output_dir).resolve() if args.output_dir else base / "100c"
    out.mkdir(parents=True, exist_ok=True)

    checks = []
    blockers = []
    p99_summary = s99 / "summary.json"
    p99_results = s99 / "replay_results.csv"
    checks.append(vrow("stage99_summary_present", p99_summary.exists(), str(p99_summary), "exists"))
    checks.append(vrow("stage99_replay_results_present", p99_results.exists(), str(p99_results), "exists"))
    j99 = rj(p99_summary)
    checks.append(vrow("stage99_ready", j99.get("recent_closed_candle_signal_replay_ready") is True, j99.get("recent_closed_candle_signal_replay_ready"), True))
    results = rcsv(p99_results)
    checks.append(vrow("stage99_results_nonempty", not results.empty, len(results), ">0"))
    if results.empty:
        blockers.append({"blocker_id": "stage99_results_missing_or_empty", "reason": "REQUIRED_INPUT_MISSING", "detail": str(p99_results), "severity": "BLOCKER"})

    rows = []
    cand_rows = []
    screen_rows = []
    if not results.empty:
        for _, rr in results.iterrows():
            idx = int(rr.get("idx", 0)) if str(rr.get("idx", "")).strip() else 0
            asof = str(rr.get("asof_m15", ""))
            rdir = Path(str(rr.get("replay_dir", "")))
            rbase = rdir / "FX_OUTPUTS" / "gold_v3"
            p69s = rbase / "69_live_csv_condition_detector_audit_only" / "gold_v3_69_live_csv_condition_detector_summary.json"
            p69c = rbase / "69_live_csv_condition_detector_audit_only" / "gold_v3_69_latest_closed_condition_candidates.csv"
            p70s = rbase / "70_live_csv_signal_decision_preview_audit_only" / "gold_v3_70_live_csv_signal_decision_preview_summary.json"
            p70screen = rbase / "70_live_csv_signal_decision_preview_audit_only" / "gold_v3_70_latest_closed_candidate_screen.csv"
            p70decision = rbase / "70_live_csv_signal_decision_preview_audit_only" / "gold_v3_70_latest_closed_signal_decision.csv"
            j69 = rj(p69s)
            j70 = rj(p70s)
            c69 = rcsv(p69c)
            s70 = rcsv(p70screen)
            d70 = rcsv(p70decision)
            latest_condition_rows = int(j70.get("latest_condition_candidate_rows", len(c69) if not c69.empty else 0) or 0)
            eligible_rows = int(j70.get("eligible_candidate_rows", 0) or 0)
            decision = str(j70.get("decision", rr.get("decision", "")))
            no_signal_reason = str(j70.get("no_signal_reason", ""))
            selected = str(j70.get("selected_candidate_label", ""))
            missing_health = int(j70.get("missing_health_state_rows", 0) or 0)
            if latest_condition_rows == 0:
                reason_class = "CONDITION_NOT_MET"
            elif eligible_rows == 0 and missing_health == 0:
                reason_class = "HEALTH_GATE_BLOCKED_ALL"
            elif missing_health > 0:
                reason_class = "HEALTH_STATE_MISSING"
            elif decision == "SIGNAL":
                reason_class = "SIGNAL"
            else:
                reason_class = "OTHER_GUARD_OR_UNKNOWN"
            rows.append({
                "idx": idx,
                "asof_m15": asof,
                "stage80_decision": str(rr.get("decision", "")),
                "stage80_status": str(rr.get("stage80_status", "")),
                "stage80_returncode": rr.get("returncode", ""),
                "stage69_status": str(j69.get("status", "")),
                "stage70_status": str(j70.get("status", "")),
                "latest_condition_candidate_rows": latest_condition_rows,
                "eligible_candidate_rows": eligible_rows,
                "missing_health_state_rows": missing_health,
                "decision": decision,
                "no_signal_reason": no_signal_reason,
                "reason_class": reason_class,
                "selected_candidate_label": selected,
                "replay_dir": str(rdir),
            })
            if not c69.empty:
                for _, cr in c69.iterrows():
                    cand_rows.append({"idx": idx, "asof_m15": asof, "candidate_label": str(cr.get("candidate_label", "")), "condition_id": str(cr.get("condition_id", "")), "priority": cr.get("priority", "")})
            if not s70.empty:
                for _, sr in s70.iterrows():
                    screen_rows.append({
                        "idx": idx,
                        "asof_m15": asof,
                        "candidate_label": str(sr.get("candidate_label", "")),
                        "health_gate_pass": str(sr.get("health_gate_pass", "")),
                        "health_gate_reason": str(sr.get("health_gate_reason", "")),
                        "rolling_pf_before": sr.get("rolling_pf_before", ""),
                        "loss_streak_before": sr.get("loss_streak_before", ""),
                        "observed_event_count": sr.get("observed_event_count", ""),
                    })

    bd = pd.DataFrame(rows)
    cand = pd.DataFrame(cand_rows)
    screen = pd.DataFrame(screen_rows)
    if not bd.empty:
        checks.append(vrow("breakdown_rows_match_replay_rows", len(bd) == len(results), len(bd), len(results)))
    else:
        checks.append(vrow("breakdown_nonempty", False, 0, ">0"))
    for c in checks:
        if c["result"] != "PASS":
            blockers.append({"blocker_id": c["check_id"], "reason": "VALIDATION_FAILED", "detail": c, "severity": "BLOCKER"})
    status = READY if not blockers else BLOCKED

    reason_counts = bd["reason_class"].value_counts(dropna=False).reset_index() if not bd.empty else pd.DataFrame(columns=["reason_class", "count"])
    if not reason_counts.empty:
        reason_counts.columns = ["reason_class", "count"]
    candidate_counts = cand["candidate_label"].value_counts(dropna=False).reset_index() if not cand.empty else pd.DataFrame(columns=["candidate_label", "count"])
    if not candidate_counts.empty:
        candidate_counts.columns = ["candidate_label", "count"]
    health_counts = screen["health_gate_reason"].value_counts(dropna=False).reset_index() if not screen.empty else pd.DataFrame(columns=["health_gate_reason", "count"])
    if not health_counts.empty:
        health_counts.columns = ["health_gate_reason", "count"]

    bd.to_csv(out / "no_signal_breakdown.csv", index=False, encoding="utf-8-sig")
    reason_counts.to_csv(out / "reason_class_counts.csv", index=False, encoding="utf-8-sig")
    candidate_counts.to_csv(out / "candidate_label_counts.csv", index=False, encoding="utf-8-sig")
    health_counts.to_csv(out / "health_gate_reason_counts.csv", index=False, encoding="utf-8-sig")
    screen.to_csv(out / "candidate_screen_rows.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(checks).to_csv(out / "validation.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(blockers).to_csv(out / "blockers.csv", index=False, encoding="utf-8-sig")

    condition_total = int(bd["latest_condition_candidate_rows"].sum()) if not bd.empty else 0
    bars_with_candidates = int((bd["latest_condition_candidate_rows"] > 0).sum()) if not bd.empty else 0
    bars_with_eligible = int((bd["eligible_candidate_rows"] > 0).sum()) if not bd.empty else 0
    signal_rows = int((bd["decision"] == "SIGNAL").sum()) if not bd.empty else 0
    summary = {
        "status": status,
        "no_signal_reason_breakdown_ready": status == READY,
        "audit_only": True,
        "live_ready": False,
        "mt5_execution_enabled": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "final_signal_enabled": False,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "manual_candidate_demotion_or_removal": False,
        "open_asof_allowed": False,
        "csv_contract": CSV_CONTRACT,
        "csv_open_bar_exclusion_required": False,
        "pool_policy": POOL_POLICY,
        "stage99_replayed_bars": int(len(results)) if not results.empty else 0,
        "breakdown_rows": int(len(bd)),
        "bars_with_condition_candidates": bars_with_candidates,
        "total_condition_candidate_rows": condition_total,
        "bars_with_health_eligible_candidates": bars_with_eligible,
        "signal_rows": signal_rows,
        "blocker_count": len(blockers),
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paste = [
        "GOLD V3 100 PASTE_ME_NO_SIGNAL_REASON_BREAKDOWN_SUMMARY",
        f"status: {status}",
        f"no_signal_reason_breakdown_ready: {str(status == READY).lower()}",
        "live_ready: false",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"stage99_replayed_bars: {summary['stage99_replayed_bars']}",
        f"breakdown_rows: {summary['breakdown_rows']}",
        f"bars_with_condition_candidates: {bars_with_candidates}",
        f"total_condition_candidate_rows: {condition_total}",
        f"bars_with_health_eligible_candidates: {bars_with_eligible}",
        f"signal_rows: {signal_rows}",
        f"blocker_count: {len(blockers)}",
        "", "REASON_CLASS_COUNTS", reason_counts.to_string(index=False) if not reason_counts.empty else "NO_REASON_ROWS",
        "", "CANDIDATE_LABEL_COUNTS", candidate_counts.head(50).to_string(index=False) if not candidate_counts.empty else "NO_CANDIDATE_ROWS",
        "", "HEALTH_GATE_REASON_COUNTS", health_counts.head(50).to_string(index=False) if not health_counts.empty else "NO_HEALTH_GATE_ROWS",
        "", "BREAKDOWN_HEAD", bd.head(20).to_string(index=False) if not bd.empty else "NO_BREAKDOWN_ROWS",
        "", "BREAKDOWN_TAIL", bd.tail(20).to_string(index=False) if not bd.empty else "NO_BREAKDOWN_ROWS",
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(checks).to_string(index=False),
        "", "OUTPUTS", "paste_me.txt", "summary.json", "no_signal_breakdown.csv", "reason_class_counts.csv", "candidate_label_counts.csv", "health_gate_reason_counts.csv", "candidate_screen_rows.csv", "validation.csv", "blockers.csv", "report.md",
    ]
    (out / "paste_me.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    (out / "report.md").write_text(f"# GOLD V3 100 no signal reason breakdown\n\nStatus: `{status}`\n\n- replay rows: `{summary['stage99_replayed_bars']}`\n- bars_with_condition_candidates: `{bars_with_candidates}`\n- total_condition_candidate_rows: `{condition_total}`\n- bars_with_health_eligible_candidates: `{bars_with_eligible}`\n- signal_rows: `{signal_rows}`\n- blockers: `{len(blockers)}`\n", encoding="utf-8")
    print(f"[{status}] {out / 'paste_me.txt'}")
    return 0 if status == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
