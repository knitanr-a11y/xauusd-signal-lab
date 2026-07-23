from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_M7C_START = "2026-07-20T14:54:15Z"


def dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    runtime = root / "runtime" / "m8c"
    manifest = runtime / "m8c_forward_shadow_manifest.json"
    if manifest.is_file():
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        print(f"[M8C INIT EXISTING] prospective_start_utc={payload['prospective_start_utc']}")
        print("[M8C INIT PASS] existing manifest preserved; no reset performed")
        return 0

    m7c_dir = root / "logs" / "m7c"
    required = [
        m7c_dir / "latest_m7c_prospective_shadow.json",
        m7c_dir / "latest_m7c_proxy_signals.csv",
        m7c_dir / "latest_m7c_source_event_comparisons.csv",
        m7c_dir / "latest_m7c_extra_proxy_signals.csv",
    ]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        print(f"[M8C INIT BLOCKED] missing M7C inputs: {missing}")
        return 2

    report = json.loads(required[0].read_text(encoding="utf-8"))
    errors = []
    if report.get("prospective_start_utc") != EXPECTED_M7C_START:
        errors.append("M7C prospective_start_utc mismatch")
    if report.get("audit_only") is not True:
        errors.append("M7C audit_only must remain true")
    for key in ("discord_send", "mt5_order", "live_ready", "final_signal", "entry_gate_enabled"):
        if report.get(key) is not False:
            errors.append(f"M7C {key} must remain false")
    if errors:
        print(f"[M8C INIT BLOCKED] {errors}")
        return 2

    now = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M8C_EXTRA_LOSS_REDUCTION_GATE_FORWARD_SHADOW",
        "contract_version": "MOCHIPOYO_M8C_MINIMAL_PROXY_BRANCH_GATE_V2",
        "prospective_start_utc": now,
        "historical_backfill_allowed": False,
        "m8b_18_trade_sample_validation_reuse_allowed": False,
        "control_rule": "ACCEPT_ALL_PROXY_PRIMARY_CANDIDATES",
        "challenger_rule": "REJECT_IF_TICKER_BTCUSD_AND_TRANSITION_PRIMARY_LONG_ELSE_ACCEPT",
        "gate_inputs": ["ticker", "proxy_transition"],
        "future_source_match_used_as_gate_input": False,
        "source_anchor_separate": True,
        "source_anchor_suppressed_by_gate": False,
        "generator_state_changed_by_gate": False,
        "generator_state_policy": "Frozen M7C proxy signal stream is observed unchanged; gate is an execution-shadow overlay.",
        "audit_only": True,
        "discord_send": False,
        "mt5_order": False,
        "live_ready": False,
        "final_signal": False,
        "entry_gate_enabled_for_real_trading": False,
        "m7c_prospective_start_utc": EXPECTED_M7C_START,
        "m7c_runtime_manifest_reset": False,
    }
    dump(manifest, payload)
    print(f"[M8C INIT PASS] prospective_start_utc={now}")
    print(f"[M8C MANIFEST] {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
