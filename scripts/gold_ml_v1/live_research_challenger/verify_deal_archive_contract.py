from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

import live_deal_archive as archive
import live_deal_archive_strict  # noqa: F401
import live_execution


def _ledger(net: float) -> pd.DataFrame:
    row = {column: "" for column in live_execution.LEDGER_COLUMNS}
    row.update(
        {
            "candidate_key": "verify-key",
            "candidate_id": "verify-id",
            "comp": "A_CORE",
            "direction": "LONG",
            "decision_time": "2026-06-29 10:00:00",
            "execution_status": "CLOSED_BY_SL_TP_OR_MANUAL",
            "trade_state": "CLOSED",
            "live_result": "WIN",
            "position_ticket": "3001",
            "closed_at": "2026-06-29 12:00:00",
            "net_profit": str(net),
            "exit_discord_sent_at": "2026-06-29 12:00:05",
        }
    )
    return pd.DataFrame([row], columns=live_execution.LEDGER_COLUMNS)


def _capture() -> list[archive.DealCapture]:
    rows = (
        {
            "position_ticket": 3001,
            "deal_ticket": 4001,
            "order_ticket": 5001,
            "time": "",
            "time_msc": 1782702001000,
            "deal_type": 0,
            "entry": 0,
            "reason": 0,
            "magic": 982201,
            "symbol": "XAUUSD",
            "volume": 0.01,
            "price": 3300.0,
            "commission": -1.0,
            "swap": 0.0,
            "profit": 0.0,
            "fee": 0.0,
            "comment": "entry",
            "external_id": "",
        },
        {
            "position_ticket": 3001,
            "deal_ticket": 4002,
            "order_ticket": 5002,
            "time": "",
            "time_msc": 1782709200000,
            "deal_type": 1,
            "entry": 1,
            "reason": 4,
            "magic": 982201,
            "symbol": "XAUUSD",
            "volume": 0.01,
            "price": 3310.0,
            "commission": -0.5,
            "swap": 0.0,
            "profit": 10.0,
            "fee": 0.0,
            "comment": "exit",
            "external_id": "",
        },
    )
    return [archive.DealCapture(3001, rows)]


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary)
        result = archive.archive_captures(
            output, _ledger(8.5), _capture(), "2026-06-29 12:00:05"
        )
        assert result["completed_positions"] == 1
        assert result["time_basis"] == "UTC_FROM_MT5_TIME_MSC"
        deals = pd.read_csv(output / "trades/deals/2026/mt5_deals_2026-06.csv")
        positions = pd.read_csv(output / "trades/deal_position_index.csv")
        assert deals["deal_ticket"].tolist() == [4001, 4002]
        assert deals["row_hash"].str.len().eq(64).all()
        assert int(positions.loc[0, "exit_deal_count"]) == 1
        assert abs(float(positions.loc[0, "net_difference"])) < 1e-12

    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary)
        result = archive.archive_captures(
            output, _ledger(9.0), _capture(), "2026-06-29 12:00:05"
        )
        assert result["completed_positions"] == 0
        assert result["incomplete"]
        assert not (output / "trades/deal_position_index.csv").exists()
    print("deal archive contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
