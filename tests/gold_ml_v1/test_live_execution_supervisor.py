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


supervisor = import_live("live_execution_supervisor")
live_mt5 = import_live("live_mt5")
live_settings = import_live("live_settings")

OrderResult = live_mt5.OrderResult
LIVE_CONFIRM_TOKEN = live_settings.LIVE_CONFIRM_TOKEN


def write_history(path: Path) -> None:
    path.mkdir(parents=True)
    for year in (2024, 2025, 2026):
        pd.DataFrame(
            {
                "comp": ["A_CORE", "B_STATE", "P18", "W024A"],
                "r": [1.0, 1.0, 1.0, 1.0],
            }
        ).to_csv(path / f"research_challenger_local_{year}.csv", index=False)


def write_real_env(live: Path, history: Path) -> None:
    (live / ".env").write_text(
        "\n".join(
            [
                "GML1_DISCORD_ENABLED=false",
                "GML1_MT5_ORDER_ENABLED=true",
                "GML1_MT5_DRY_RUN=false",
                f"GML1_MT5_LIVE_CONFIRM={LIVE_CONFIRM_TOKEN}",
                "GML1_MT5_SYMBOL=XAUUSD",
                "GML1_MT5_VOLUME=0.01",
                f"GML1_HISTORICAL_RESULTS_DIR={history}",
            ]
        ),
        encoding="utf-8",
    )


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


class RecoveringFakeClient:
    positions: dict[int, SimpleNamespace] = {}
    order_calls = 0
    return_ticket_on_fill = True

    def __init__(self, settings):
        self.settings = settings

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def magic(self, comp: str) -> int:
        return 982201

    def comment(self, candidate_key: str, comp: str) -> str:
        return live_mt5.MetaTrader5Client.comment(candidate_key, comp)

    def recover_existing(self, *, magic: int, comment: str):
        position = self.find_position(magic=magic, comment=comment)
        if position is None:
            return None
        return OrderResult(
            status="ORDER_RECOVERED_OPEN",
            retcode=None,
            message="recovered",
            magic=magic,
            comment=comment,
            symbol="XAUUSD",
            volume=0.01,
            position_ticket=position.ticket,
            fill_price=100.0,
            stop_price=90.0,
            target_price=110.0,
        )

    def find_position(self, *, magic: int, comment: str):
        for position in self.positions.values():
            if position.magic == magic and position.comment == comment:
                return position
        return None

    def gml1_positions(self):
        return list(self.positions.values())

    def open_market_order(self, record, volume):
        self.__class__.order_calls += 1
        ticket = 12345
        comment = self.comment(record["candidate_key"], record["comp"])
        self.__class__.positions[ticket] = SimpleNamespace(
            ticket=ticket,
            magic=982201,
            comment=comment,
        )
        return OrderResult(
            status="ORDER_FILLED",
            retcode=10009,
            message="done",
            magic=982201,
            comment=comment,
            symbol="XAUUSD",
            volume=volume,
            order_ticket=ticket,
            deal_ticket=54321,
            position_ticket=(ticket if self.return_ticket_on_fill else None),
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
        return 1.0, pd.Timestamp("2026-06-29 16:01:00").to_pydatetime()


def initialize_and_place(
    *,
    live: Path,
    output: Path,
    repo_root: Path,
) -> None:
    empty = pd.DataFrame(columns=registry_row().columns)
    supervisor.process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=empty,
        latest_m1_close=pd.Timestamp("2026-06-29 10:01:00"),
        now_text="2026-06-29 10:01:00",
        repo_root=repo_root,
        client_factory=RecoveringFakeClient,
        webhook_sender=lambda *_args, **_kwargs: None,
    )
    result = supervisor.process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=registry_row(),
        latest_m1_close=pd.Timestamp("2026-06-29 10:01:00"),
        now_text="2026-06-29 10:01:05",
        repo_root=repo_root,
        client_factory=RecoveringFakeClient,
        webhook_sender=lambda *_args, **_kwargs: None,
    )
    assert result["new_execution_statuses"] == {"ORDER_FILLED": 1}


def test_open_position_is_managed_after_env_is_removed(tmp_path: Path) -> None:
    RecoveringFakeClient.positions = {}
    RecoveringFakeClient.order_calls = 0
    RecoveringFakeClient.return_ticket_on_fill = True
    live = tmp_path / "live"
    output = tmp_path / "output"
    history = tmp_path / "history"
    live.mkdir()
    output.mkdir()
    write_history(history)
    write_real_env(live, history)
    initialize_and_place(live=live, output=output, repo_root=tmp_path)

    (live / ".env").unlink()
    result = supervisor.process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=registry_row(),
        latest_m1_close=pd.Timestamp("2026-06-29 16:01:00"),
        now_text="2026-06-29 16:01:00",
        repo_root=tmp_path,
        client_factory=RecoveringFakeClient,
        webhook_sender=lambda *_args, **_kwargs: None,
    )
    assert result["forced_open_position_management"] is True
    assert any("CLOSED" in event for event in result["reconciliation_events"])
    ledger = pd.read_csv(output / "live_execution_ledger.csv")
    assert ledger.loc[0, "trade_state"] == "CLOSED"
    assert ledger.loc[0, "live_result"] == "WIN"


def test_missing_position_ticket_is_recovered_before_management(
    tmp_path: Path,
) -> None:
    RecoveringFakeClient.positions = {}
    RecoveringFakeClient.order_calls = 0
    RecoveringFakeClient.return_ticket_on_fill = False
    live = tmp_path / "live"
    output = tmp_path / "output"
    history = tmp_path / "history"
    live.mkdir()
    output.mkdir()
    write_history(history)
    write_real_env(live, history)
    initialize_and_place(live=live, output=output, repo_root=tmp_path)

    before = pd.read_csv(output / "live_execution_ledger.csv")
    assert pd.isna(before.loc[0, "position_ticket"])
    result = supervisor.process_execution_cycle(
        live_dir=live,
        output_dir=output,
        registry=registry_row(),
        latest_m1_close=pd.Timestamp("2026-06-29 10:02:00"),
        now_text="2026-06-29 10:02:00",
        repo_root=tmp_path,
        client_factory=RecoveringFakeClient,
        webhook_sender=lambda *_args, **_kwargs: None,
    )
    assert result["status"] == "PASS"
    after = pd.read_csv(output / "live_execution_ledger.csv")
    assert int(after.loc[0, "position_ticket"]) == 12345
    assert after.loc[0, "execution_status"] == "ORDER_RECOVERED_OPEN"
