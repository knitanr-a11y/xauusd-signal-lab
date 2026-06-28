from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pandas as pd


def live_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts/gold_ml_v1/live_research_challenger"


def import_live(name: str):
    path = str(live_dir())
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module(name)


policy = import_live("live_execution_live_wr")
settings_module = import_live("live_settings")


def registry_row() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "candidate_key": "GML1-WATCH-022-C|2026-06-29 10:00:00",
                "candidate_id": "GML1-WATCH-022-C",
                "comp": "A_CORE",
                "decision_time": "2026-06-29 10:00:00",
                "direction": "LONG",
                "horizon_hours": 6,
                "position_state": "OPEN",
                "first_seen_at": "2026-06-29 10:01:00",
                "atr": 10.0,
                "target_r": 1.0,
                "entry_price": 100.0,
                "stop_price": 90.0,
                "target_price": 110.0,
                "current_price": 100.5,
            }
        ]
    )


def test_configured_service_stays_on_even_when_old_toggle_keys_are_false(
    tmp_path: Path,
) -> None:
    live = tmp_path / "live"
    output = tmp_path / "output"
    live.mkdir()
    output.mkdir()
    (live / ".env").write_text(
        "\n".join(
            [
                "DISCORD_WEBHOOK_URL=https://example.invalid/webhook",
                "GML1_DISCORD_ENABLED=false",
                "GML1_MT5_ORDER_ENABLED=false",
                "GML1_MT5_DRY_RUN=true",
                "GML1_MT5_SYMBOL=XAUUSD",
                "GML1_MT5_VOLUME=0.01",
            ]
        ),
        encoding="utf-8",
    )
    messages: list[str] = []
    sender = lambda _url, **kwargs: messages.append(kwargs["content"])

    first = policy.process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=pd.DataFrame(columns=registry_row().columns),
        latest_m1_close=pd.Timestamp("2026-06-29 10:01:00"),
        now_text="2026-06-29 10:01:00",
        repo_root=tmp_path,
        webhook_sender=sender,
    )
    assert first["service_mode"] == "ALWAYS_ON_FAIL_CLOSED"

    second = policy.process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=registry_row(),
        latest_m1_close=pd.Timestamp("2026-06-29 10:01:00"),
        now_text="2026-06-29 10:01:05",
        repo_root=tmp_path,
        webhook_sender=sender,
    )
    assert second["new_execution_statuses"] == {"DRY_RUN": 1}
    assert second["controls"]["discord"] is True
    assert second["controls"]["mt5_order_requested"] is True
    assert len(messages) == 1


def test_missing_env_does_not_break_forced_position_recovery(tmp_path: Path) -> None:
    live = tmp_path / "live"
    live.mkdir()
    settings = settings_module.load_runtime_settings(live, tmp_path)
    adjusted = policy._always_on_settings(settings)
    assert adjusted.discord_enabled is False
    assert adjusted.mt5_enabled is False
    assert adjusted.require_historical_win_rate is False
