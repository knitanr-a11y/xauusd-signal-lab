#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 90 Stage80 ledger sidecar dry-run patch plan audit-only.

Plans where and how to add optional Stage85/86 sidecar execution after
Stage80->Stage76->Stage79. Does not modify Stage80.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_90_STAGE80_LEDGER_SIDECAR_DRY_RUN_PATCH_PLAN_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_90_STAGE80_LEDGER_SIDECAR_DRY_RUN_PATCH_PLAN_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_90_STAGE80_LEDGER_SIDECAR_DRY_RUN_PATCH_PLAN_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
CANDIDATE_KEY_ORDER = "candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars"


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception as e:
        return {"_read_error": repr(e)}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files", root.parent.parent]:
        d = d.expanduser().resolve()
        if (d/"goldsharp_m15.csv").exists() or (d/"FX_OUTPUTS"/"gold_v3").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def find_line(lines: list[str], needle: str) -> int:
    for i, line in enumerate(lines, start=1):
        if needle in line:
            return i
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    cdir = Path(args.candle_dir).expanduser().resolve() if args.candle_dir else find_files_dir()
    base = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(args.output_dir).expanduser().resolve() if args.output_dir else base / "90c"
    out.mkdir(parents=True, exist_ok=True)

    stage80 = repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_80_immutable_runtime_monitor_audit.py"
    s85 = repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_85_trade_review_ledger_entry_preview_audit.py"
    s86 = repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_86_trade_review_ledger_append_guard_audit.py"
    stage89_summary = base / "89c" / "summary.json"
    j89 = read_json(stage89_summary)

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for name, p in [("stage80_script", stage80), ("stage85_script", s85), ("stage86_script", s86), ("stage89_summary", stage89_summary)]:
        exists = p.exists()
        val.append(ok(f"{name}_present", exists, str(p), "exists"))
        if not exists:
            blockers.append(blocker(f"{name}_missing", str(p), "REQUIRED_ARTIFACT_MISSING"))

    lines = stage80.read_text(encoding="utf-8").splitlines() if stage80.exists() else []
    line_rc76 = find_line(lines, "rc76, tail76, sec76 = run_script")
    line_rc79 = find_line(lines, "rc79, tail79, sec79 = run_script")
    line_paste79 = find_line(lines, "last_stage79_paste_path = extract_stage79_paste_path")
    line_last_seen = find_line(lines, "last_seen = latest")
    line_event_done = find_line(lines, "PIPELINE_DONE")
    line_timing_fields = find_line(lines, "timing_fields =")
    line_build_summary = find_line(lines, "def build_summary")

    insertion_ok = bool(line_rc76 and line_rc79 and line_paste79 and line_last_seen and line_paste79 < line_last_seen)
    val.extend([
        ok("stage76_run_point_detected", bool(line_rc76), line_rc76, "line number"),
        ok("stage79_run_point_detected", bool(line_rc79), line_rc79, "line number"),
        ok("stage79_paste_extract_point_detected", bool(line_paste79), line_paste79, "line number"),
        ok("last_seen_commit_point_detected", bool(line_last_seen), line_last_seen, "line number"),
        ok("safe_insertion_order", insertion_ok, {"paste79_line": line_paste79, "last_seen_line": line_last_seen}, "paste79 before last_seen"),
        ok("stage89_ready", "READY" in str(j89.get("status", "")), str(j89.get("status", "")), "READY"),
    ])
    if not insertion_ok:
        blockers.append(blocker("safe_insertion_point_not_detected", str(stage80), "SAFE_INSERTION_POINT_NOT_DETECTED", {"line_paste79": line_paste79, "line_last_seen": line_last_seen}))
    if not ("READY" in str(j89.get("status", ""))):
        blockers.append(blocker("stage89_not_ready", str(stage89_summary), "STAGE89_NOT_READY", j89.get("status", "")))

    plan_rows = [
        {"order": 1, "patch_area": "argparse", "line_hint": "near parse_args", "proposed_change": "add --enable-ledger-sidecar-dry-run default false", "default_effect": "unchanged", "risk": "low"},
        {"order": 2, "patch_area": "script paths", "line_hint": "after s81 path definitions", "proposed_change": "define s85 and s86 script paths", "default_effect": "unchanged", "risk": "low"},
        {"order": 3, "patch_area": "state fields", "line_hint": "after last_stage79 fields", "proposed_change": "load last_stage85/86 rc/sec/paste state defaults", "default_effect": "summary fields only if enabled", "risk": "low"},
        {"order": 4, "patch_area": "timing log", "line_hint": "timing_fields already includes generic segment", "proposed_change": "write stage85_sidecar and stage86_sidecar timing rows when enabled", "default_effect": "none", "risk": "low"},
        {"order": 5, "patch_area": "pipeline", "line_hint": f"after line {line_paste79}, before line {line_last_seen}", "proposed_change": "if Stage79 OK and sidecar enabled: run Stage85 then Stage86", "default_effect": "disabled", "risk": "medium"},
        {"order": 6, "patch_area": "summary", "line_hint": f"build_summary line {line_build_summary}", "proposed_change": "include ledger_sidecar_enabled and last_stage85/86 fields", "default_effect": "visible false/default fields", "risk": "low"},
        {"order": 7, "patch_area": "paste summary", "line_hint": "write_outputs paste list", "proposed_change": "print sidecar enabled/rc/sec/paste fields", "default_effect": "visible false/default fields", "risk": "low"},
    ]
    insertion_rows = [
        {"marker": "stage76_run", "line": line_rc76, "meaning": "Stage76 --once execution point"},
        {"marker": "stage79_run", "line": line_rc79, "meaning": "Stage79 immutable snapshot execution point"},
        {"marker": "stage79_paste_extract", "line": line_paste79, "meaning": "Stage79 paste path becomes available"},
        {"marker": "last_seen_commit", "line": line_last_seen, "meaning": "Stage80 commits M15 as processed"},
        {"marker": "pipeline_done_event", "line": line_event_done, "meaning": "Stage80 writes done event"},
    ]
    patch_md = [
        "# GOLD V3 90 Stage80 ledger sidecar dry-run patch plan",
        "",
        "Stage90 does not modify Stage80. This is a plan only.",
        "",
        "## Safe insertion point",
        "",
        f"Insert optional sidecar execution after Stage79 paste path extraction line `{line_paste79}` and before last_seen commit line `{line_last_seen}`.",
        "",
        "Reason: Stage85 needs Stage76/Stage79 evidence, and Stage86 needs Stage85 output. If sidecar is blocking in the future patch, Stage80 should not mark the M15 as fully processed until sidecar checks pass.",
        "",
        "## Required defaults",
        "",
        "- `ledger_sidecar_enabled=false` by default.",
        "- No durable ledger append.",
        "- No Discord.",
        "- No MT5.",
        "- No AI API.",
        "- No final signal.",
        "- CSV contract remains closed-row only.",
        "",
        "## Proposed patch rows",
        "",
    ]
    for r in plan_rows:
        patch_md.append(f"- {r['order']}. **{r['patch_area']}** — {r['proposed_change']} (default: {r['default_effect']}, risk: {r['risk']})")

    stage80_modified = False
    sidecar_autorun_enabled = False
    durable_ledger_append_enabled = False
    live_flags_all_false = True
    val.extend([
        ok("stage90_does_not_modify_stage80", not stage80_modified, stage80_modified, False),
        ok("sidecar_autorun_disabled", not sidecar_autorun_enabled, sidecar_autorun_enabled, False),
        ok("durable_ledger_append_disabled", not durable_ledger_append_enabled, durable_ledger_append_enabled, False),
        ok("csv_open_bar_exclusion_required_false", True, False, False),
        ok("live_flags_all_false", live_flags_all_false, "all_false", "all_false"),
    ])
    failed = [v for v in val if v.get("result") != "PASS"]
    status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS

    write_csv(pd.DataFrame(plan_rows), out / "patch_plan.csv")
    write_csv(pd.DataFrame(insertion_rows), out / "insertion_point_matrix.csv")
    write_csv(pd.DataFrame(blockers), out / "blockers.csv")
    write_csv(pd.DataFrame(val), out / "validation.csv")
    write_text(out / "patch_plan.md", "\n".join(patch_md) + "\n")

    summary = {
        "step": STEP,
        "status": status,
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
        "stage80_ledger_sidecar_dry_run_patch_plan_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "candidate_key_order": CANDIDATE_KEY_ORDER,
        "stage80_modified_by_stage90": stage80_modified,
        "sidecar_autorun_enabled": sidecar_autorun_enabled,
        "durable_ledger_append_enabled": durable_ledger_append_enabled,
        "safe_insertion_line_after_stage79_paste": line_paste79,
        "safe_insertion_line_before_last_seen_commit": line_last_seen,
        "blocker_count": len(blockers),
        "validation_failure_count": len(failed),
        "next_stage_if_ready": "GOLD_V3_91_STAGE80_LEDGER_SIDECAR_DRY_RUN_PATCH_AUDIT_ONLY",
    }
    write_text(out / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2))

    paste = [
        "GOLD V3 90 PASTE_ME_STAGE80_LEDGER_SIDECAR_DRY_RUN_PATCH_PLAN_SUMMARY",
        f"status: {status}",
        "stage80_ledger_sidecar_dry_run_patch_plan_ready: " + str(status == READY_STATUS).lower(),
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"stage80_modified_by_stage90: {stage80_modified}",
        f"sidecar_autorun_enabled: {sidecar_autorun_enabled}",
        f"durable_ledger_append_enabled: {durable_ledger_append_enabled}",
        f"safe_insertion_after_stage79_paste_line: {line_paste79}",
        f"safe_insertion_before_last_seen_line: {line_last_seen}",
        f"blocker_count: {len(blockers)}",
        "", "PATCH_PLAN", pd.DataFrame(plan_rows).to_string(index=False),
        "", "INSERTION_POINTS", pd.DataFrame(insertion_rows).to_string(index=False),
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(val).to_string(index=False),
        "", "NEXT", "GOLD_V3_91_STAGE80_LEDGER_SIDECAR_DRY_RUN_PATCH_AUDIT_ONLY",
        "", "OUTPUTS", "paste_me.txt", "summary.json", "patch_plan.md", "patch_plan.csv", "insertion_point_matrix.csv", "blockers.csv", "validation.csv", "report.md",
    ]
    write_text(out / "paste_me.txt", "\n".join(paste) + "\n")
    report = f"""# GOLD V3 90 Stage80 ledger sidecar dry-run patch plan audit-only report

Status: `{status}`

- stage80_modified_by_stage90: `{stage80_modified}`
- sidecar_autorun_enabled: `{sidecar_autorun_enabled}`
- durable_ledger_append_enabled: `{durable_ledger_append_enabled}`
- safe insertion after Stage79 paste line: `{line_paste79}`
- safe insertion before last_seen line: `{line_last_seen}`
- blocker_count: `{len(blockers)}`

Stage90 is a plan only. It does not patch Stage80.
"""
    write_text(out / "report.md", report)
    print(f"[{status}] {out/'paste_me.txt'}")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
