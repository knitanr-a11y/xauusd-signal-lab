from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pandas as pd


def live_script_dir() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "scripts/gold_ml_v1/live_research_challenger"
    )


def import_live(name: str):
    path = str(live_script_dir())
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module(name)


live_wr = import_live("live_execution_live_wr")
live_win_rate = import_live("live_win_rate")

process_execution_cycle = live_wr.process_execution_cycle
WinRateSummary = live_win_rate.WinRateSummary


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


def write_dry_run_env(live_dir: Path) -> None:
    (live_dir / ".env").write_text(
        "\n".join(
            [
                "DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/test/test",
                "GML1_DISCORD_ENABLED=true",
                "GML1_MT5_ORDER_ENABLED=true",
                "GML1_MT5_DRY_RUN=true",
                "GML1_MT5_SYMBOL=XAUUSD",
                "GML1_MT5_VOLUME=0.01",
                "GML1_REQUIRE_HISTORICAL_WIN_RATE=true",
                "GML1_HISTORICAL_RESULTS_DIR=C:\\definitely-missing-history",
            ]
        ),
        encoding="utf-8",
    )


def test_dry_run_ignores_missing_history_and_displays_only_live_wr(
    tmp_path: Path,
) -> None:
    live_dir = tmp_path / "live"
    output_dir = tmp_path / "output"
    live_dir.mkdir()
    output_dir.mkdir()
    write_dry_run_env(live_dir)
    messages: list[str] = []
    sender = lambda _url, **kwargs: messages.append(kwargs["content"])

    first = process_execution_cycle(
        live_dir=live_dir,
        output_dir=output_dir,
        registry=pd.DataFrame(columns=registry_row().columns),
        latest_m1_close=pd.Timestamp("2026-06-29 10:01:00"),
        now_text="2026-06-29 10:01:00",
        repo_root=tmp_path,
        webhook_sender=sender,
    )
    assert first["status"] == "EXECUTION_INITIALIZED_NO_BACKFILL"
    assert first["win_rate_scope"] == "LIVE_MT5_CLOSED_ORDERS_ONLY_BY_SLEEVE"
    assert "historical_win_rate" not in first

    second = process_execution_cycle(
        live_dir=live_dir,
        output_dir=output_dir,
        registry=registry_row(),
        latest_m1_close=pd.Timestamp("2026-06-29 10:01:00"),
        now_text="2026-06-29 10:01:05",
        repo_root=tmp_path,
        webhook_sender=sender,
    )
    assert second["new_execution_statuses"] == {"DRY_RUN": 1}
    assert second["controls"]["require_historical_win_rate"] is False
    assert "historical_win_rate" not in second
    assert len(messages) == 1
    assert "実運用WR（この軸）" in messages[0]
    assert "集計前（決済済み0件）" in messages[0]
    assert "過去" not in messages[0]
    assert "historical" not in messages[0].lower()


def test_live_only_message_uses_sleeve_realized_results() -> None:
    live = WinRateSummary(
        trades=5,
        wins=3,
        losses_or_flat=2,
        win_rate=0.6,
        source="live MT5 closed orders",
    )
    unused = WinRateSummary(
        trades=99,
        wins=99,
        losses_or_flat=0,
        win_rate=1.0,
        source="must not be displayed",
    )
    row = {
        "comp": "A_CORE",
        "candidate_id": "GML1-WATCH-022-C",
        "direction": "LONG",
        "decision_time": "2026-06-29 10:00:00",
        "execution_status": "ORDER_FILLED",
        "volume": 0.01,
        "fill_price": 3300.0,
        "stop_price": 3290.0,
        "target_price": 3310.0,
        "message": "done",
    }
    message = live_wr._entry_message(row, unused, live)
    assert "60.00%（3/5）" in message
    assert "99/99" not in message
    assert "過去" not in message


def test_exit_message_updates_live_wr_only() -> None:
    live = WinRateSummary(
        trades=1,
        wins=1,
        losses_or_flat=0,
        win_rate=1.0,
        source="live MT5 closed orders",
    )
    unused = WinRateSummary(
        trades=100,
        wins=0,
        losses_or_flat=100,
        win_rate=0.0,
        source="must not be displayed",
    )
    row = {
        "comp": "P18",
        "candidate_id": "GML1-PROV-018-APPROX",
        "decision_time": "2026-06-29 10:00:00",
        "closed_at": "2026-06-29 16:00:00",
        "live_result": "WIN",
        "net_profit": 12.5,
    }
    message = live_wr._exit_message(row, unused, live)
    assert "実運用WR（この軸・更新後）" in message
    assert "100.00%（1/1）" in message
    assert "0/100" not in message
    assert "過去" not in message
