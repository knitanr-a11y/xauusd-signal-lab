from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd


def live_dir() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "scripts/gold_ml_v1/live_research_challenger"
    )


def import_live(name: str):
    path = str(live_dir())
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module(name)


live_execution = import_live("live_execution")
live_settings = import_live("live_settings")
live_win_rate = import_live("live_win_rate")
live_mt5 = import_live("live_mt5")

process_execution_cycle = live_execution.process_execution_cycle
LIVE_CONFIRM_TOKEN = live_settings.LIVE_CONFIRM_TOKEN
load_runtime_settings = live_settings.load_runtime_settings
load_historical_win_rates = live_win_rate.load_historical_win_rates
MetaTrader5Client = live_mt5.MetaTrader5Client
OrderResult = live_mt5.OrderResult

COMPS = ("A_CORE", "B_STATE", "P18", "W024A")


def write_history(path: Path) -> None:
    path.mkdir(parents=True)
    for year in (2024, 2025, 2026):
        pd.DataFrame(
            {
                "comp": ["A_CORE", "A_CORE", "B_STATE", "P18", "W024A"],
                "r": [1.0, -1.0, 1.0, 0.2, -1.0],
            }
        ).to_csv(path / f"research_challenger_local_{year}.csv", index=False)


def registry_row(
    decision: str = "2026-06-29 10:00:00", state: str = "OPEN"
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "candidate_key": f"GML1-WATCH-022-C|{decision}",
                "candidate_id": "GML1-WATCH-022-C",
                "comp": "A_CORE",
                "decision_time": decision,
                "direction": "LONG",
                "horizon_hours": 6,
                "position_state": state,
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


def base_env(live: Path, history: Path, *, dry_run: bool = True) -> None:
    lines = [
        "DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/test/test",
        "GML1_DISCORD_ENABLED=true",
        "GML1_MT5_ORDER_ENABLED=true",
        f"GML1_MT5_DRY_RUN={'true' if dry_run else 'false'}",
        "GML1_MT5_SYMBOL=XAUUSD",
        "GML1_MT5_VOLUME=0.01",
        f"GML1_HISTORICAL_RESULTS_DIR={history}",
    ]
    if not dry_run:
        lines.append(f"GML1_MT5_LIVE_CONFIRM={LIVE_CONFIRM_TOKEN}")
    (live / ".env").write_text("\n".join(lines), encoding="utf-8")


def test_settings_fail_closed_without_volume_or_symbol(tmp_path: Path) -> None:
    live = tmp_path / "live"
    live.mkdir()
    (live / ".env").write_text(
        "DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/x/y\n"
        "GML1_MT5_ORDER_ENABLED=true\n"
        "GML1_MT5_DRY_RUN=false\n",
        encoding="utf-8",
    )
    settings = load_runtime_settings(live, tmp_path)
    assert settings.discord_enabled is True
    assert settings.real_orders_armed is False
    assert any("GML1_MT5_SYMBOL" in item for item in settings.config_errors)
    assert any("positive MT5 volume" in item for item in settings.config_errors)


def test_historical_win_rate_is_candidate_specific(tmp_path: Path) -> None:
    history = tmp_path / "history"
    write_history(history)
    result = load_historical_win_rates(history, COMPS)
    assert result["A_CORE"].trades == 6
    assert result["A_CORE"].wins == 3
    assert result["A_CORE"].win_rate == 0.5
    assert result["P18"].win_rate == 1.0


def test_initialization_does_not_backfill_then_dry_run_notifies(
    tmp_path: Path,
) -> None:
    live = tmp_path / "live"
    output = tmp_path / "output"
    history = tmp_path / "history"
    live.mkdir()
    output.mkdir()
    write_history(history)
    base_env(live, history, dry_run=True)
    messages: list[str] = []

    first = process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=pd.DataFrame(columns=registry_row().columns),
        latest_m1_close=pd.Timestamp("2026-06-29 10:01:00"),
        now_text="2026-06-29 10:01:00",
        repo_root=tmp_path,
        webhook_sender=lambda _url, **kwargs: messages.append(kwargs["content"]),
    )
    assert first["status"] == "EXECUTION_INITIALIZED_NO_BACKFILL"

    second = process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=registry_row(),
        latest_m1_close=pd.Timestamp("2026-06-29 10:01:00"),
        now_text="2026-06-29 10:01:05",
        repo_root=tmp_path,
        webhook_sender=lambda _url, **kwargs: messages.append(kwargs["content"]),
    )
    assert second["new_execution_statuses"] == {"DRY_RUN": 1}
    assert len(messages) == 1
    assert "過去自動売買WR" in messages[0]
    assert "実運用WR" in messages[0]
    assert "50.00%" in messages[0]

    third = process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=registry_row(),
        latest_m1_close=pd.Timestamp("2026-06-29 10:02:00"),
        now_text="2026-06-29 10:02:00",
        repo_root=tmp_path,
        webhook_sender=lambda _url, **kwargs: messages.append(kwargs["content"]),
    )
    assert third["new_execution_rows"] == 0
    assert len(messages) == 1


def test_stale_candidate_is_not_ordered(tmp_path: Path) -> None:
    live = tmp_path / "live"
    output = tmp_path / "output"
    history = tmp_path / "history"
    live.mkdir()
    output.mkdir()
    write_history(history)
    base_env(live, history, dry_run=True)
    process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=pd.DataFrame(columns=registry_row().columns),
        latest_m1_close=pd.Timestamp("2026-06-29 10:01:00"),
        now_text="2026-06-29 10:01:00",
        repo_root=tmp_path,
        webhook_sender=lambda *_args, **_kwargs: None,
    )
    result = process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=registry_row("2026-06-29 09:00:00"),
        latest_m1_close=pd.Timestamp("2026-06-29 10:01:00"),
        now_text="2026-06-29 10:01:05",
        repo_root=tmp_path,
        webhook_sender=lambda *_args, **_kwargs: None,
    )
    assert result["new_execution_statuses"] == {"SKIPPED_STALE": 1}


class FakeClient:
    order_calls = 0
    positions: dict[int, SimpleNamespace] = {}

    def __init__(self, settings):
        self.settings = settings

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def magic(self, comp: str) -> int:
        return 982201

    def comment(self, candidate_key: str, comp: str) -> str:
        return MetaTrader5Client.comment(candidate_key, comp)

    def recover_existing(self, *, magic: int, comment: str):
        return None

    def gml1_positions(self):
        return list(self.positions.values())

    def open_market_order(self, record, volume):
        self.__class__.order_calls += 1
        ticket = 12345
        self.__class__.positions[ticket] = SimpleNamespace(
            ticket=ticket, magic=982201
        )
        return OrderResult(
            status="ORDER_FILLED",
            retcode=10009,
            message="done",
            magic=982201,
            comment=self.comment(record["candidate_key"], record["comp"]),
            symbol="XAUUSD",
            volume=volume,
            order_ticket=ticket,
            deal_ticket=54321,
            position_ticket=ticket,
            fill_price=100.0,
            stop_price=90.0,
            target_price=110.0,
        )

    def get_position(self, ticket: int):
        return self.positions.get(ticket)

    def close_position(self, ticket: int, *, comment: str, magic: int):
        self.positions.pop(ticket, None)
        return OrderResult(
            status="TIME_EXIT_FILLED",
            retcode=10009,
            message="closed",
            magic=magic,
            comment=comment,
            symbol="XAUUSD",
            volume=0.01,
            position_ticket=ticket,
            fill_price=101.0,
        )

    def closed_position_profit(self, position_ticket: int):
        if position_ticket in self.positions:
            return None
        return 1.25, pd.Timestamp("2026-06-29 16:01:00").to_pydatetime()


def test_real_order_is_idempotent_and_time_exit_updates_live_wr(
    tmp_path: Path,
) -> None:
    FakeClient.order_calls = 0
    FakeClient.positions = {}
    live = tmp_path / "live"
    output = tmp_path / "output"
    history = tmp_path / "history"
    live.mkdir()
    output.mkdir()
    write_history(history)
    base_env(live, history, dry_run=False)
    messages: list[str] = []
    sender = lambda _url, **kwargs: messages.append(kwargs["content"])

    process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=pd.DataFrame(columns=registry_row().columns),
        latest_m1_close=pd.Timestamp("2026-06-29 10:01:00"),
        now_text="2026-06-29 10:01:00",
        repo_root=tmp_path,
        client_factory=FakeClient,
        webhook_sender=sender,
    )
    placed = process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=registry_row(),
        latest_m1_close=pd.Timestamp("2026-06-29 10:01:00"),
        now_text="2026-06-29 10:01:05",
        repo_root=tmp_path,
        client_factory=FakeClient,
        webhook_sender=sender,
    )
    assert placed["new_execution_statuses"] == {"ORDER_FILLED": 1}
    assert FakeClient.order_calls == 1

    repeated = process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=registry_row(),
        latest_m1_close=pd.Timestamp("2026-06-29 10:02:00"),
        now_text="2026-06-29 10:02:00",
        repo_root=tmp_path,
        client_factory=FakeClient,
        webhook_sender=sender,
    )
    assert repeated["new_execution_rows"] == 0
    assert FakeClient.order_calls == 1

    closed = process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=registry_row(),
        latest_m1_close=pd.Timestamp("2026-06-29 16:01:00"),
        now_text="2026-06-29 16:01:00",
        repo_root=tmp_path,
        client_factory=FakeClient,
        webhook_sender=sender,
    )
    assert "CLOSED" in " ".join(closed["reconciliation_events"])
    assert any("実運用WR（更新後）" in message for message in messages)
    ledger = pd.read_csv(output / "live_execution_ledger.csv")
    assert ledger.loc[0, "live_result"] == "WIN"
    assert len(MetaTrader5Client.comment("x", "A_CORE")) <= 31


def test_time_exit_filled_row_remains_active_until_position_is_confirmed_closed() -> None:
    ledger = pd.DataFrame(
        [
            {
                **{column: "" for column in live_execution.LEDGER_COLUMNS},
                "candidate_key": "k",
                "trade_state": "OPEN",
                "execution_status": "TIME_EXIT_FILLED",
            }
        ],
        columns=live_execution.LEDGER_COLUMNS,
    )
    assert len(live_execution._active_real_rows(ledger)) == 1


def test_existing_open_order_is_managed_even_after_new_orders_are_disabled(
    tmp_path: Path,
) -> None:
    FakeClient.order_calls = 0
    FakeClient.positions = {}
    live = tmp_path / "live"
    output = tmp_path / "output"
    history = tmp_path / "history"
    live.mkdir()
    output.mkdir()
    write_history(history)
    base_env(live, history, dry_run=False)
    sender = lambda *_args, **_kwargs: None

    process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=pd.DataFrame(columns=registry_row().columns),
        latest_m1_close=pd.Timestamp("2026-06-29 10:01:00"),
        now_text="2026-06-29 10:01:00",
        repo_root=tmp_path,
        client_factory=FakeClient,
        webhook_sender=sender,
    )
    process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=registry_row(),
        latest_m1_close=pd.Timestamp("2026-06-29 10:01:00"),
        now_text="2026-06-29 10:01:05",
        repo_root=tmp_path,
        client_factory=FakeClient,
        webhook_sender=sender,
    )
    env_path = live / ".env"
    env_path.write_text(
        env_path.read_text(encoding="utf-8")
        .replace("GML1_MT5_ORDER_ENABLED=true", "GML1_MT5_ORDER_ENABLED=false")
        .replace("GML1_MT5_SYMBOL=XAUUSD\n", ""),
        encoding="utf-8",
    )
    result = process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=registry_row(),
        latest_m1_close=pd.Timestamp("2026-06-29 16:01:00"),
        now_text="2026-06-29 16:01:00",
        repo_root=tmp_path,
        client_factory=FakeClient,
        webhook_sender=sender,
    )
    assert any("CLOSED" in event for event in result["reconciliation_events"])
