#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 61 frozen audit package human review audit-only.

Builds a human-review package for the Stage46-60 closed-asof audit chain.
No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_61_FROZEN_AUDIT_PACKAGE_HUMAN_REVIEW_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_61_FROZEN_AUDIT_PACKAGE_HUMAN_REVIEW_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_61_FROZEN_AUDIT_PACKAGE_HUMAN_REVIEW_BLOCKED_AUDIT_ONLY"
STAGE60_READY = "GOLD_V3_60_MUTABLE_SOURCE_PREFIX_HASH_VERIFICATION_READY_AUDIT_ONLY"

STAGE_THEMES = {
    46: "closed-asof Stage45 pool contract freeze",
    47: "closed-asof pool contract forward audit",
    48: "live-readiness gap audit",
    49: "state schema and shadow ledger contract",
    50: "H4 closed readiness and prior 60D Q70 state",
    51: "virtual opportunity ledger",
    52: "rolling health gate and rank-dedup selection ledger",
    53: "pending-to-closed shadow trade adjudication",
    54: "restart/replay checkpoint state",
    55: "strict checkpoint replay dry-run",
    56: "mutable source drift policy",
    57: "bounded replay window freeze decision",
    58: "bounded checkpoint replay dry-run",
    59: "mutable source prefix-hash baseline",
    60: "mutable source prefix-hash verification",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "60_mutable_source_prefix_hash_verification_audit_only").exists():
            return d
    raise FileNotFoundError("Stage60 output directory not found. Pass --candle-dir.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def find_stage_files(gold_v3_dir: Path, stage: int) -> list[Path]:
    pats = [
        f"**/gold_v3_{stage}_*summary.json",
        f"**/gold_v3_{stage}_*SUMMARY.json",
        f"**/gold_v3_{stage}_PASTE_ME*.txt",
        f"**/gold_v3_{stage}_*PASTE*.txt",
        f"**/GOLD_V3_{stage}_*REPORT*.md",
    ]
    files: list[Path] = []
    for pat in pats:
        files.extend([p for p in gold_v3_dir.glob(pat) if p.is_file()])
    uniq = {str(p.resolve()): p for p in files}
    return sorted(uniq.values(), key=lambda p: (p.stat().st_mtime, str(p)))


def extract_from_text(path: Path) -> dict[str, Any]:
    txt = path.read_text(encoding="utf-8", errors="replace")
    out: dict[str, Any] = {}
    for key in [
        "status", "live_ready", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed",
        "bounded_replay_ready", "prefix_hash_support_ready", "prefix_hash_verification_ready",
        "policy_ready", "stage55_strict_replay_ready", "live_allowed", "mt5_execution_enabled",
        "discord_live_enabled", "final_signal_enabled",
    ]:
        m = re.search(rf"^{re.escape(key)}\s*:\s*(.+)$", txt, flags=re.MULTILINE)
        if m:
            out[key] = m.group(1).strip()
    return out


def boolish(v: Any) -> Any:
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ["true", "1", "yes"]:
        return True
    if s in ["false", "0", "no"]:
        return False
    return v


def stage_snapshot(files: list[Path]) -> dict[str, Any]:
    if not files:
        return {}
    preferred = None
    for p in files:
        if p.suffix.lower() == ".json":
            preferred = p
    if preferred is None:
        preferred = files[-1]
    try:
        if preferred.suffix.lower() == ".json":
            data = read_json(preferred)
        else:
            data = extract_from_text(preferred)
    except Exception as e:
        data = {"parse_error": str(e)}
    data["source_file"] = str(preferred)
    data["source_file_count"] = len(files)
    return data


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    g = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else g / "61_frozen_audit_package_human_review_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    val: list[dict[str, Any]] = []
    val.append(ok("gold_v3_output_dir_present", g.exists(), str(g), "exists"))

    rows = []
    snapshots: dict[int, dict[str, Any]] = {}
    for stage, theme in STAGE_THEMES.items():
        files = find_stage_files(g, stage)
        snap = stage_snapshot(files)
        snapshots[stage] = snap
        status = snap.get("status", "")
        rows.append({
            "stage": stage,
            "theme": theme,
            "artifact_present": bool(files),
            "source_file_count": len(files),
            "selected_source_file": snap.get("source_file", ""),
            "status": status,
            "live_ready": boolish(snap.get("live_ready")),
            "live_allowed": boolish(snap.get("live_allowed")),
            "mt5_execution_enabled": boolish(snap.get("mt5_execution_enabled")),
            "discord_live_enabled": boolish(snap.get("discord_live_enabled")),
            "final_signal_enabled": boolish(snap.get("final_signal_enabled")),
            "contract_mutated": boolish(snap.get("contract_mutated")),
            "manual_candidate_demotion_or_removal": boolish(snap.get("manual_candidate_demotion_or_removal")),
            "open_asof_allowed": boolish(snap.get("open_asof_allowed")),
            "key_ready_flags": ", ".join([f"{k}={snap.get(k)}" for k in ["bounded_replay_ready", "prefix_hash_support_ready", "prefix_hash_verification_ready", "policy_ready"] if k in snap]),
        })
    inv = pd.DataFrame(rows)
    inv.to_csv(out / "gold_v3_61_stage_chain_inventory.csv", index=False, encoding="utf-8-sig")

    stage60 = snapshots.get(60, {})
    val.append(ok("stage60_artifact_present", bool(stage60), stage60.get("source_file", ""), "present"))
    val.append(ok("stage60_status_ready", stage60.get("status") == STAGE60_READY, stage60.get("status"), STAGE60_READY))
    val.append(ok("stage60_prefix_hash_verification_ready", boolish(stage60.get("prefix_hash_verification_ready")) is True, stage60.get("prefix_hash_verification_ready"), True))

    required_stage_missing = inv[~inv["artifact_present"]]
    val.append(ok("stage46_to_60_artifacts_present", required_stage_missing.empty, required_stage_missing["stage"].tolist(), []))

    # Safety evidence: if a stage reports a dangerous flag as true, block. Missing older flags are noted but do not imply approval.
    danger_checks = []
    for _, r in inv.iterrows():
        for key in ["live_ready", "live_allowed", "mt5_execution_enabled", "discord_live_enabled", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
            valv = r.get(key)
            if valv is True:
                danger_checks.append({"stage": int(r["stage"]), "flag": key, "value": valv})
    val.append(ok("no_stage_reports_live_or_mutation_enabled", len(danger_checks) == 0, danger_checks, []))

    safety = pd.DataFrame([
        {"safety_item": "audit_only", "value": True, "note": "Stage61 package only"},
        {"safety_item": "live_ready", "value": False, "note": "No live approval"},
        {"safety_item": "live_allowed", "value": False, "note": "No live approval"},
        {"safety_item": "mt5_execution_enabled", "value": False, "note": "No MT5 order BAT"},
        {"safety_item": "discord_live_enabled", "value": False, "note": "No Discord live notification"},
        {"safety_item": "ai_api_called", "value": False, "note": "No AI API call"},
        {"safety_item": "final_signal_enabled", "value": False, "note": "No final signal"},
        {"safety_item": "contract_mutated", "value": False, "note": "No candidate/pool mutation"},
        {"safety_item": "manual_candidate_demotion_or_removal", "value": False, "note": "No manual HV/base removal"},
        {"safety_item": "open_asof_allowed", "value": False, "note": "Closed-asof only"},
    ])
    safety.to_csv(out / "gold_v3_61_safety_summary.csv", index=False, encoding="utf-8-sig")

    decisions = pd.DataFrame([
        {"decision_id": "D1", "item": "Freeze audit package and stop", "status": "AVAILABLE", "requires_live_approval": False, "notes": "Keep audit-only frozen package."},
        {"decision_id": "D2", "item": "Continue live-readiness implementation planning audit-only", "status": "AVAILABLE", "requires_live_approval": False, "notes": "Planning/spec only; no MT5/Discord/final signal."},
        {"decision_id": "D3", "item": "Run additional robustness checks", "status": "AVAILABLE", "requires_live_approval": False, "notes": "More audit-only tests."},
        {"decision_id": "D4", "item": "Enable live/MT5/Discord/final signal", "status": "BLOCKED", "requires_live_approval": True, "notes": "Requires separate explicit approval and live-readiness implementation audit."},
    ])
    decisions.to_csv(out / "gold_v3_61_human_review_decision_matrix.csv", index=False, encoding="utf-8-sig")

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_61_validation_matrix.csv", index=False, encoding="utf-8-sig")

    summary = {
        "step": STEP,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
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
        "frozen_audit_package_ready": failed.empty,
        "stage_inventory_rows": int(len(inv)),
        "stage_artifact_missing_count": int((~inv["artifact_present"]).sum()),
        "stage60_status": stage60.get("status", ""),
        "stage60_prefix_hash_verification_ready": boolish(stage60.get("prefix_hash_verification_ready")),
        "human_review_required": True,
        "live_enablement_blocked": True,
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_61_frozen_audit_package_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 61 PASTE_ME_FROZEN_AUDIT_PACKAGE_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("frozen_audit_package_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append(f"stage_inventory_rows: {len(inv)}")
    paste.append(f"stage_artifact_missing_count: {int((~inv['artifact_present']).sum())}")
    paste.append(f"stage60_status: {stage60.get('status', '')}")
    paste.append(f"stage60_prefix_hash_verification_ready: {boolish(stage60.get('prefix_hash_verification_ready'))}")
    paste.append("stage55_strict_full_file_replay: intentionally_not_ready_after_mutable_source_append")
    paste.append("stage58_bounded_replay: ready_if_reported_by_stage58")
    paste.append("stage60_prefix_hash: ready_if_reported_by_stage60")
    paste.append("live_enablement: BLOCKED_REQUIRES_SEPARATE_EXPLICIT_APPROVAL_AND_LIVE_READINESS_AUDIT")
    paste.append("")
    paste.append("STAGE_CHAIN_INVENTORY")
    paste.append(inv[["stage", "theme", "artifact_present", "status", "live_ready", "contract_mutated", "open_asof_allowed", "key_ready_flags"]].to_string(index=False))
    paste.append("")
    paste.append("HUMAN_REVIEW_DECISION_MATRIX")
    paste.append(decisions.to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_61_stage_chain_inventory.csv")
    paste.append("gold_v3_61_safety_summary.csv")
    paste.append("gold_v3_61_human_review_decision_matrix.csv")
    paste.append("gold_v3_61_validation_matrix.csv")
    paste.append("gold_v3_61_frozen_audit_package_summary.json")
    (out / "gold_v3_61_PASTE_ME_FROZEN_AUDIT_PACKAGE_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = [
        "# GOLD V3 61 frozen audit package human review audit-only report",
        "",
        f"Status: `{status}`",
        "",
        "Audit-only. No MT5, Discord, AI API, live hook, or final signal.",
        "",
        "## Human review",
        "",
        "Live enablement remains blocked and requires separate explicit approval plus a live-readiness implementation audit.",
    ]
    (out / "GOLD_V3_61_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_61_PASTE_ME_FROZEN_AUDIT_PACKAGE_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
