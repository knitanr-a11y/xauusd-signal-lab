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


live_execution = import_live("live_execution")
manager = import_live("live_log_manager")
live_win_rate = import_live("live_win_rate")
COLUMNS = live_execution.LEDGER_COLUMNS


def row(**updates):
    value = {column: "" for column in COLUMNS}
    value.update(
        {
            "candidate_key": "key",
            "candidate_id": "candidate",
            "comp": "A_CORE",
            "direction": "LONG",
            "decision_time": "2026-05-10 10:00:00",
            "horizon_end_time": "2026-05-10 16:00:00",
            "execution_status": "ORDER_FILLED",
            "trade_state": "OPEN",
            "requested_at": "2026-05-10 10:00:05",
            "last_checked_at": "2026-05-10 10:01:00",
            "symbol": "XAUUSD",
            "volume": "0.01",
        }
    )
    value.update(updates)
    return value


def test_monthly_trade_archive_and_small_operational_ledger(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    closed = row(
        candidate_key="closed-key",
        trade_state="CLOSED",
        execution_status="CLOSED_BY_SL_TP_OR_MANUAL",
        live_result="WIN",
        closed_at="2026-05-10 12:00:00",
        net_profit="12.50",
        order_ticket="101",
        deal_ticket="201",
        position_ticket="301",
        exit_discord_sent_at="2026-05-10 12:00:05",
    )
    open_trade = row(
        candidate_key="open-key",
        candidate_id="GML1-PROV-018-APPROX",
        comp="P18",
        decision_time="2026-04-01 10:00:00",
        order_ticket="102",
        deal_ticket="202",
        position_ticket="302",
    )
    old_dry_run = row(
        candidate_key="dry-key",
        comp="W024A",
        decision_time="2026-04-01 10:00:00",
        execution_status="DRY_RUN",
        trade_state="NOT_SENT",
    )
    ledger = pd.DataFrame([closed, open_trade, old_dry_run], columns=COLUMNS)

    compacted, manifest = manager.maintain_logs_and_trades(
        output, ledger=ledger, now_text="2026-06-29 12:00:00"
    )

    assert set(compacted["candidate_key"]) == {"open-key"}
    assert manifest["archived_trades"] == 1
    assert manifest["purged_old_non_trade_rows"] == 1

    monthly = output / "trades/2026/live_trades_2026-05.csv"
    trade_index = output / "trades/trade_index.csv"
    summary = output / "trades/monthly_summary.csv"
    candidate_index = output / "state/candidate_key_index.csv"
    assert monthly.is_file()
    assert trade_index.is_file()
    assert summary.is_file()
    assert candidate_index.is_file()

    archived = pd.read_csv(monthly)
    assert archived["candidate_key"].tolist() == ["closed-key"]
    index = pd.read_csv(trade_index)
    assert index.loc[0, "net_profit"] == 12.5
    assert index.loc[0, "archive_file"] == "trades/2026/live_trades_2026-05.csv"
    monthly_summary = pd.read_csv(summary)
    assert monthly_summary.loc[0, "trades"] == 1
    assert monthly_summary.loc[0, "wins"] == 1
    assert monthly_summary.loc[0, "net_profit"] == 12.5
    keys = pd.read_csv(candidate_index)
    assert set(keys["candidate_key"]) == {"closed-key", "open-key", "dry-key"}

    combined = manager.combined_live_trade_frame(output, compacted)
    rates = live_win_rate.load_live_win_rates(combined, ("A_CORE", "P18"))
    assert rates["A_CORE"].trades == 1
    assert rates["A_CORE"].wins == 1
    assert rates["P18"].trades == 0


def test_short_logs_are_deleted_after_31_days_and_compressed_after_7(
    tmp_path: Path,
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    old = manager.append_notification_log(
        output,
        now_text="2026-05-01 10:00:00",
        status="SENT",
        content="old",
        username="GML1",
    )
    compressible = manager.append_notification_log(
        output,
        now_text="2026-06-15 10:00:00",
        status="SENT",
        content="compress",
        username="GML1",
    )
    recent = manager.append_notification_log(
        output,
        now_text="2026-06-28 10:00:00",
        status="SENT",
        content="recent",
        username="GML1",
    )

    stats = manager.prune_and_compress_short_logs(output, "2026-06-29 12:00:00")

    assert stats == {"deleted": 1, "compressed": 1}
    assert not old.exists()
    assert not compressible.exists()
    assert compressible.with_suffix(".jsonl.gz").is_file()
    assert recent.is_file()
