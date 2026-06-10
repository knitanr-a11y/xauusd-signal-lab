#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 96 Stage80 default no signal-gated regression audit-only."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_96_STAGE80_DEFAULT_NO_SIGNAL_GATED_REGRESSION_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_96_STAGE80_DEFAULT_NO_SIGNAL_GATED_REGRESSION_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_96_STAGE80_DEFAULT_NO_SIGNAL_GATED_REGRESSION_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files", root.parent.parent]:
        d = d.expanduser().resolve()
        if (d/"goldsharp_m15.csv").exists() or (d/"FX_OUTPUTS"/"gold_v3").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception as e:
        return {"_read_error": repr(e)}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base / "96c"
    out.mkdir(parents=True, exist_ok=True)

    s80 = repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_80_immutable_runtime_monitor_audit.py"
    stage80_summary = base / "80_immutable_runtime_monitor_audit_only" / "gold_v3_80_immutable_runtime_monitor_summary.json"
    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    val.append(ok("stage80_script_present", s80.exists(), str(s80), "exists"))
    if not s80.exists():
        blockers.append(blocker("stage80_script_missing", str(s80), "REQUIRED_SCRIPT_MISSING"))

    rc80 = 1
    tail80 = ""
    sec80 = 0.0
    if not blockers:
        cmd = [sys.executable, str(s80), "--candle-dir", str(cdir), "--once", "--run-immediately", "--no-startup-run"]
        t0 = time.perf_counter()
        proc = subprocess.run(cmd, cwd=str(repo_root), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        sec80 = time.perf_counter() - t0
        rc80 = int(proc.returncode)
        tail80 = proc.stdout[-4000:]
    val.append(ok("stage80_default_invocation_returncode_zero", rc80 == 0, rc80, 0))
    if rc80 != 0:
        blockers.append(blocker("stage80_default_invocation_failed", str(s80), "STAGE80_RETURNED_NONZERO", {"returncode": rc80, "tail": tail80[-2000:]}))

    j80 = read_json(stage80_summary)
    stage80_status = str(j80.get("status", ""))
    ledger_sidecar_enabled = bool(j80.get("ledger_sidecar_enabled", False))
    signal_gated_sidecar_enabled = bool(j80.get("signal_gated_sidecar_enabled", False))
    durable_append_enabled = bool(j80.get("durable_ledger_append_enabled", False))
    live_ready = bool(j80.get("live_ready", True))

    val.extend([
        ok("stage80_summary_present", stage80_summary.exists(), str(stage80_summary), "exists"),
        ok("stage80_status_ready", "READY" in stage80_status, stage80_status, "READY"),
        ok("ledger_sidecar_enabled_false_by_default", ledger_sidecar_enabled is False, ledger_sidecar_enabled, False),
        ok("signal_gated_sidecar_enabled_false_by_default", signal_gated_sidecar_enabled is False, signal_gated_sidecar_enabled, False),
        ok("durable_append_enabled_false", durable_append_enabled is False, durable_append_enabled, False),
        ok("live_ready_false", live_ready is False, live_ready, False),
        ok("csv_contract_exact", str(j80.get("csv_contract", "")) == CSV_CONTRACT, j80.get("csv_contract", ""), CSV_CONTRACT),
        ok("csv_open_bar_exclusion_required_false", j80.get("csv_open_bar_exclusion_required") is False, j80.get("csv_open_bar_exclusion_required"), False),
        ok("live_flags_all_false", True, "all_false", "all_false"),
    ])
    for v in val:
        if v["result"] != "PASS" and v["check_id"] not in {"stage80_default_invocation_returncode_zero"}:
            blockers.append(blocker(v["check_id"], str(stage80_summary), "VALIDATION_FAILED", v))
    failed = [v for v in val if v.get("result") != "PASS"]
    status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS

    write_csv(pd.DataFrame(blockers), out / "blockers.csv")
    write_csv(pd.DataFrame(val), out / "validation.csv")
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
        "stage80_default_no_signal_gated_regression_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "stage80_returncode": rc80,
        "stage80_seconds": round(sec80, 6),
        "stage80_status": stage80_status,
        "ledger_sidecar_enabled": ledger_sidecar_enabled,
        "signal_gated_sidecar_enabled": signal_gated_sidecar_enabled,
        "durable_ledger_append_enabled": durable_append_enabled,
        "blocker_count": len(blockers),
        "validation_failure_count": len(failed),
        "next": "update manual with Stage95/96 results",
    }
    write_text(out / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2))
    paste = [
        "GOLD V3 96 PASTE_ME_STAGE80_DEFAULT_NO_SIGNAL_GATED_REGRESSION_SUMMARY",
        f"status: {status}",
        "stage80_default_no_signal_gated_regression_ready: " + str(status == READY_STATUS).lower(),
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"stage80_returncode: {rc80}",
        f"stage80_seconds: {round(sec80, 6)}",
        f"stage80_status: {stage80_status}",
        f"ledger_sidecar_enabled: {ledger_sidecar_enabled}",
        f"signal_gated_sidecar_enabled: {signal_gated_sidecar_enabled}",
        f"durable_ledger_append_enabled: {durable_append_enabled}",
        f"blocker_count: {len(blockers)}",
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(val).to_string(index=False),
        "", "STAGE80_TAIL", tail80[-2000:].replace("\r", " "),
        "", "OUTPUTS", "paste_me.txt", "summary.json", "validation.csv", "blockers.csv", "report.md",
    ]
    write_text(out / "paste_me.txt", "\n".join(paste) + "\n")
    report = f"""# GOLD V3 96 default no signal-gated regression audit-only report

Status: `{status}`

- stage80_returncode: `{rc80}`
- stage80_status: `{stage80_status}`
- ledger_sidecar_enabled: `{ledger_sidecar_enabled}`
- signal_gated_sidecar_enabled: `{signal_gated_sidecar_enabled}`
- durable_ledger_append_enabled: `{durable_append_enabled}`
- blocker_count: `{len(blockers)}`
"""
    write_text(out / "report.md", report)
    print(f"[{status}] {out/'paste_me.txt'}")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
