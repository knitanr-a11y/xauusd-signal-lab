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
formatter = import_live("live_notification_formatter")
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


def empty_live() -> WinRateSummary:
    return WinRateSummary(
        trades=0,
        wins=0,
        losses_or_flat=0,
        win_rate=None,
        source="live MT5 closed orders",
        available=False,
        reason="no closed orders",
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
    assert "実運用成績" in messages[0]
    assert "集計前（決済済み0件）" in messages[0]
    assert "テスト実行（注文なし）" in messages[0]
    assert "LONG" not in messages[0]
    assert "DRY_RUN" not in messages[0]
    assert "GML1-WATCH" not in messages[0]
    assert "過去" not in messages[0]
    assert "historical" not in messages[0].lower()

    third = process_execution_cycle(
        live_dir=live_dir,
        output_dir=output_dir,
        registry=registry_row(),
        latest_m1_close=pd.Timestamp("2026-06-29 10:02:00"),
        now_text="2026-06-29 10:02:00",
        repo_root=tmp_path,
        webhook_sender=sender,
    )
    assert third["new_execution_rows"] == 0
    assert len(messages) == 1


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
        "horizon_end_time": "2026-06-29 16:00:00",
        "execution_status": "ORDER_FILLED",
        "symbol": "GOLD#",
        "volume": 0.01,
        "fill_price": 3300.0,
        "stop_price": 3290.0,
        "target_price": 3310.0,
        "message": "done",
    }
    message = live_wr._entry_message(row, unused, live)
    assert "3勝2敗 / 勝率 60.00%" in message
    assert "99勝" not in message
    assert "買い注文が約定しました" in message
    assert "4時間足環境＋15分足コア" in message
    assert "LONG" not in message
    assert "ORDER_FILLED" not in message
    assert "GML1-WATCH-022-C" not in message
    assert "done" not in message
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
        "direction": "LONG",
        "decision_time": "2026-06-29 10:00:00",
        "closed_at": "2026-06-29 16:00:00",
        "execution_status": "CLOSED_BY_SL_TP_OR_MANUAL",
        "live_result": "WIN",
        "net_profit": 12.5,
    }
    message = live_wr._exit_message(row, unused, live)
    assert "1勝0敗 / 勝率 100.00%" in message
    assert "0勝100敗" not in message
    assert "SL・TP・手動決済のいずれか" in message
    assert "GML1-PROV-018-APPROX" not in message
    assert "過去" not in message


def test_japanese_direction_status_and_close_reason_mappings() -> None:
    assert formatter.DIRECTION_NAMES == {"LONG": "買い", "SHORT": "売り"}
    for raw, japanese in formatter.EXECUTION_STATUS_NAMES.items():
        message = formatter.format_entry_message(
            {
                "comp": "A_CORE",
                "direction": "SHORT",
                "decision_time": "2026-07-02 10:00:00",
                "execution_status": raw,
            },
            empty_live(),
        )
        assert japanese in message
        assert raw not in message

    expected = {
        "SL": "損切り",
        "TP": "利益確定",
        "TIME": "保有期限による決済",
        "MANUAL": "手動決済",
    }
    for raw, japanese in expected.items():
        message = formatter.format_exit_message(
            {
                "comp": "A_CORE",
                "direction": "SHORT",
                "execution_status": "CLOSED_BY_SL_TP_OR_MANUAL",
                "close_reason": raw,
                "closed_at": "2026-07-02 11:00:00",
                "live_result": "LOSS",
                "net_profit": -1.0,
            },
            empty_live(),
        )
        assert f"決済：{japanese}" in message
        assert raw not in message

    time_message = formatter.format_exit_message(
        {
            "comp": "A_CORE",
            "direction": "LONG",
            "execution_status": "TIME_EXIT_FILLED",
            "closed_at": "2026-07-02 11:00:00",
            "live_result": "WIN",
            "net_profit": 1.0,
        },
        empty_live(),
    )
    assert "決済：保有期限による決済" in time_message


def test_old_ledger_is_extended_additively_without_reset(tmp_path: Path) -> None:
    path = tmp_path / "live_execution_ledger.csv"
    old = pd.DataFrame(
        [
            {
                **{column: "" for column in live_wr._BASE_LEDGER_COLUMNS},
                "candidate_key": "old-key",
                "candidate_id": "old-candidate",
                "comp": "P18",
                "direction": "LONG",
                "decision_time": "2026-07-01 10:00:00",
                "execution_status": "ORDER_FILLED",
                "trade_state": "OPEN",
                "entry_discord_sent_at": "2026-07-01 10:00:05",
                "exit_discord_sent_at": "",
                "custom_existing_column": "preserve-me",
            }
        ]
    )
    old.to_csv(path, index=False)

    columns = live_wr._ledger_columns(path)
    migrated = live_wr._load_ledger_additive(path, columns)
    assert migrated.loc[0, "candidate_key"] == "old-key"
    assert migrated.loc[0, "entry_discord_sent_at"] == "2026-07-01 10:00:05"
    assert migrated.loc[0, "custom_existing_column"] == "preserve-me"
    for column in live_wr._OPTIONAL_LEDGER_COLUMNS:
        assert column in migrated.columns


def test_optional_signal_fields_are_copied_without_changing_trade_contract() -> None:
    record = registry_row().iloc[0].to_dict()
    record.update(
        {
            "source_timeframe": "M15",
            "higher_timeframe": "H4",
            "features_json": {"bb_break": True},
            "signal_reason": "M15ボリンジャーバンド上抜け",
        }
    )
    row = live_wr._base_row_with_optional(record, "2026-06-29 10:01:05")
    assert row["direction"] == record["direction"]
    assert row["stop_price"] == ""
    assert row["target_price"] == ""
    assert row["horizon_end_time"] == "2026-06-29 16:00:00"
    assert row["source_timeframe"] == "M15"
    assert row["higher_timeframe"] == "H4"
    assert row["atr"] == 10.0
    assert row["target_r"] == 1.0
    assert row["horizon_hours"] == 6
    assert '"bb_break":true' in row["features_json"]


def test_missing_optional_fields_and_discord_limit() -> None:
    row = {
        "comp": "UNKNOWN",
        "direction": "LONG",
        "decision_time": "2026-07-02 10:00:00",
        "execution_status": "SIGNAL_ONLY",
        "signal_reason": "x" * 5000,
    }
    message = formatter.format_entry_message(row, empty_live())
    assert "GOLD自動売買戦略" in message
    assert len(message) <= formatter.DISCORD_CONTENT_LIMIT
    assert "表示上限のため一部を省略しました" in message
