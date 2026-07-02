from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "run_btc_youtube_candidates_gold_style_audit_wrapper.py"
spec = importlib.util.spec_from_file_location("run_btc_youtube_candidates_gold_style_audit_wrapper", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_summary_has_gold_style_safety_fields_and_hides_webhook(tmp_path: Path, monkeypatch) -> None:
    webhook = "https://discord.com/api/webhooks/123456789/secret-token-value"
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", webhook)
    log_base = tmp_path / "logs"
    state_dir = tmp_path / "state"
    once_summary = tmp_path / "once_summary.json"
    once_summary.write_text(json.dumps({
        "dry_run": {"latest_closed": {"m5": "2026-07-03 00:00:00"}},
        "rows": {"trade_notifications": 1, "monitor_notifications": 2, "order_payloads": 2},
    }), encoding="utf-8")
    latest_state = {
        "last_cycle": {
            "cycle_index": 1,
            "cycle_start_utc": "2026-07-03 00:00:10",
            "cycle_end_utc": "2026-07-03 00:00:20",
            "cycle_ok": True,
            "classification": "OPERATIONAL_PASS",
            "once_summary_json": str(once_summary),
            "btc6_discord_status": "NO_ROWS",
        },
        "btc6_metrics": {"open_trades": 1, "closed_trades": 3, "total_r": 2.5},
    }
    summary = module.build_summary(
        latest_state, state_dir=state_dir, log_base=log_base,
        discord_env_name="DISCORD_WEBHOOK_URL", child_running=True,
    )
    encoded = json.dumps(summary)
    assert summary["status"] == "BTC_YOUTUBE_OPERATIONAL_READY_DEMO_ONLY"
    assert summary["real_money_enabled"] is False
    assert summary["final_signal"] is False
    assert summary["discord"]["webhook_configured"] is True
    assert summary["discord"]["webhook_value_logged"] is False
    assert webhook not in encoded
    assert summary["latest_closed"]["m5"] == "2026-07-03 00:00:00"
    assert summary["cycle_rows"]["order_payloads"] == 2


def test_cycle_key_is_unique_across_restarts() -> None:
    first = {"cycle_index": 1, "cycle_start_utc": "2026-07-03 00:00:10"}
    second = {"cycle_index": 1, "cycle_start_utc": "2026-07-03 01:00:10"}
    assert module.cycle_key(first) != module.cycle_key(second)


def test_write_artifacts_creates_summary_paste_me_and_ledger(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "configured")
    log_base = tmp_path / "logs"
    state_dir = tmp_path / "state"
    stable = log_base / "youtube_candidates_operational"
    stable.mkdir(parents=True)
    (stable / "latest_operational_state.json").write_text(json.dumps({
        "last_cycle": {
            "cycle_index": 4,
            "cycle_start_utc": "2026-07-03 02:00:10",
            "cycle_end_utc": "2026-07-03 02:00:20",
            "cycle_ok": False,
            "classification": "OPERATIONAL_FAILED",
        },
        "btc6_metrics": {},
    }), encoding="utf-8")
    module.write_audit_artifacts(
        state_dir=state_dir, log_base=log_base,
        discord_env_name="DISCORD_WEBHOOK_URL", child_running=True,
    )
    audit = stable / module.AUDIT_DIR_NAME
    assert (audit / module.SUMMARY_NAME).exists()
    assert (audit / module.PASTE_ME_NAME).exists()
    assert (audit / module.LEDGER_NAME).exists()
    text = (audit / module.PASTE_ME_NAME).read_text(encoding="utf-8")
    assert "status: BTC_YOUTUBE_OPERATIONAL_ATTENTION_REQUIRED_DEMO_ONLY" in text
