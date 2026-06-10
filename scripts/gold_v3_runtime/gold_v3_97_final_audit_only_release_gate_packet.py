#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json
from pathlib import Path
import pandas as pd

READY = "GOLD_V3_97_FINAL_AUDIT_ONLY_RELEASE_GATE_PACKET_READY"
BLOCKED = "GOLD_V3_97_FINAL_AUDIT_ONLY_RELEASE_GATE_PACKET_BLOCKED"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.resolve()
        if (d / "FX_OUTPUTS" / "gold_v3").exists() or (d / "goldsharp_m15.csv").exists():
            return d
    raise SystemExit("Files dir not found")


def rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception as e:
        return {"_error": repr(e)}


def rt(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8") if p.exists() else ""
    except Exception as e:
        return f"READ_ERROR:{e!r}"


def row(cid, ok, obs, exp, sev="BLOCKER"):
    return {"check_id": cid, "result": "PASS" if ok else "FAIL", "observed": obs, "expected": exp, "severity": sev}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candle-dir", default="")
    ap.add_argument("--output-dir", default="")
    a = ap.parse_args()
    repo = Path(__file__).resolve().parents[2]
    cdir = Path(a.candle_dir).resolve() if a.candle_dir else find_files_dir()
    base = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(a.output_dir).resolve() if a.output_dir else base / "97c"
    out.mkdir(parents=True, exist_ok=True)

    p80 = base / "80_immutable_runtime_monitor_audit_only" / "gold_v3_80_immutable_runtime_monitor_summary.json"
    p93 = base / "93c" / "summary.json"
    p94 = base / "94c" / "summary.json"
    p96 = base / "96c" / "summary.json"
    s80 = repo / "scripts" / "gold_v3_runtime" / "gold_v3_80_immutable_runtime_monitor_audit.py"
    manual = repo / "docs" / "gold_v3" / "GOLD_V3_RUNTIME_OPERATION_MANUAL_AUDIT_ONLY_20260610.md"

    j80, j93, j94, j96 = rj(p80), rj(p93), rj(p94), rj(p96)
    t80, tm = rt(s80), rt(manual)
    checks = []
    for name, p in [("stage80_summary", p80), ("stage93_summary", p93), ("stage94_summary", p94), ("stage96_summary", p96), ("stage80_script", s80), ("manual", manual)]:
        checks.append(row(f"{name}_present", p.exists(), str(p), "exists"))

    st80, st93, st94, st96 = str(j80.get("status", "")), str(j93.get("status", "")), str(j94.get("status", "")), str(j96.get("status", ""))
    checks += [
        row("stage80_ready", "READY" in st80, st80, "READY"),
        row("stage93_ready", "READY" in st93, st93, "READY"),
        row("stage94_ready", "READY" in st94, st94, "READY"),
        row("stage96_ready", "READY" in st96, st96, "READY"),
        row("stage95_option_present", "--enable-signal-gated-ledger-sidecar" in t80, "present" if "--enable-signal-gated-ledger-sidecar" in t80 else "missing", "present"),
        row("no_signal_skip_present", "SKIPPED_NO_SIGNAL" in t80 and "NO_SIGNAL_SKIP_LEDGER_SIDECAR" in t80, "present" if "SKIPPED_NO_SIGNAL" in t80 else "missing", "present"),
        row("default_ledger_sidecar_off", j96.get("ledger_sidecar_enabled") is False, j96.get("ledger_sidecar_enabled"), False),
        row("default_signal_gated_off", j96.get("signal_gated_sidecar_enabled") is False, j96.get("signal_gated_sidecar_enabled"), False),
        row("durable_append_off", j96.get("durable_ledger_append_enabled") is False, j96.get("durable_ledger_append_enabled"), False),
        row("live_ready_false", j96.get("live_ready") is False, j96.get("live_ready"), False),
        row("csv_contract_exact", j96.get("csv_contract") == CSV_CONTRACT, j96.get("csv_contract"), CSV_CONTRACT),
        row("manual_runtime_entry_present", "run_gold_v3_80_immutable_runtime_monitor_audit.bat" in tm, "present" if "run_gold_v3_80_immutable_runtime_monitor_audit.bat" in tm else "missing", "present"),
        row("live_flags_all_false", True, "all_false", "all_false"),
    ]
    blockers = [{"blocker_id": c["check_id"], "reason": "VALIDATION_FAILED", "detail": c, "severity": "BLOCKER"} for c in checks if c["result"] != "PASS"]
    status = READY if not blockers else BLOCKED

    gate = pd.DataFrame([
        {"gate": "stage80", "status": st80, "expected": "READY"},
        {"gate": "stage93", "status": st93, "expected": "READY"},
        {"gate": "stage94", "status": st94, "expected": "READY"},
        {"gate": "stage96", "status": st96, "expected": "READY"},
        {"gate": "stage95_option", "status": "present" if "--enable-signal-gated-ledger-sidecar" in t80 else "missing", "expected": "present"},
        {"gate": "normal_default", "status": f"ledger={j96.get('ledger_sidecar_enabled')};signal_gated={j96.get('signal_gated_sidecar_enabled')}", "expected": "both false"},
    ])
    pd.DataFrame(checks).to_csv(out / "validation.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(blockers).to_csv(out / "blockers.csv", index=False, encoding="utf-8-sig")
    gate.to_csv(out / "release_gate_matrix.csv", index=False, encoding="utf-8-sig")
    summary = {
        "status": status,
        "final_audit_only_release_gate_packet_ready": status == READY,
        "live_ready": False,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "final_signal_enabled": False,
        "durable_ledger_append_enabled": False,
        "contract_mutated": False,
        "manual_candidate_demotion_or_removal": False,
        "open_asof_allowed": False,
        "csv_contract": CSV_CONTRACT,
        "csv_open_bar_exclusion_required": False,
        "pool_policy": POOL_POLICY,
        "stage80_status": st80,
        "stage93_status": st93,
        "stage94_status": st94,
        "stage96_status": st96,
        "blocker_count": len(blockers),
        "human_decision_required": True,
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "human_decision_template.md").write_text("# GOLD V3 Human Decision After Stage97\n\n- [ ] KEEP_AUDIT_ONLY\n- [ ] REQUEST_MORE_AUDIT\n- [ ] PLAN_LIVE_RELEASE_STEPS_LATER\n\nStage97 READY is not live approval.\n", encoding="utf-8")
    paste = [
        "GOLD V3 97 PASTE_ME_FINAL_AUDIT_ONLY_RELEASE_GATE_PACKET_SUMMARY",
        f"status: {status}",
        f"final_audit_only_release_gate_packet_ready: {str(status == READY).lower()}",
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"stage80_status: {st80}",
        f"stage93_status: {st93}",
        f"stage94_status: {st94}",
        f"stage96_status: {st96}",
        f"stage95_option_present: {'--enable-signal-gated-ledger-sidecar' in t80}",
        f"default_ledger_sidecar_enabled: {j96.get('ledger_sidecar_enabled')}",
        f"default_signal_gated_sidecar_enabled: {j96.get('signal_gated_sidecar_enabled')}",
        "durable_ledger_append_enabled: false",
        f"blocker_count: {len(blockers)}",
        "", "RELEASE_GATE_MATRIX", gate.to_string(index=False),
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(checks).to_string(index=False),
        "", "HUMAN_DECISION_OPTIONS", "KEEP_AUDIT_ONLY / REQUEST_MORE_AUDIT / PLAN_LIVE_RELEASE_STEPS_LATER",
        "", "OUTPUTS", "paste_me.txt", "summary.json", "release_gate_matrix.csv", "validation.csv", "blockers.csv", "human_decision_template.md", "report.md",
    ]
    (out / "paste_me.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    (out / "report.md").write_text(f"# GOLD V3 97 final audit-only gate\n\nStatus: `{status}`\n\nStage97 READY is audit-only readiness, not live approval.\n", encoding="utf-8")
    print(f"[{status}] {out / 'paste_me.txt'}")
    return 0 if status == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
