from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "btc_ai_v1"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from stage55_shadow_features import load_csv


ROWS = [
    "2026.08.04 00:00:00,100.0,110.0,90.0,105.0,1,2,0",
    "2026.08.04 04:00:00,105.0,115.0,95.0,110.0,1,2,0",
]


def test_stage55_reads_live_comma_csv(tmp_path: Path) -> None:
    path = tmp_path / "btcusdsharp_h4.csv"
    path.write_text(
        "time,open,high,low,close,tick_volume,spread,real_volume\n"
        + "\n".join(ROWS)
        + "\n",
        encoding="utf-8",
    )
    frame = load_csv(path, "H4")
    assert list(frame.loc[:, ["open", "high", "low", "close"]].iloc[0]) == [100.0, 110.0, 90.0, 105.0]
    assert frame["close_time"].iloc[0] == pd.Timestamp("2026-08-04 04:00:00")


def test_stage55_still_reads_research_semicolon_csv(tmp_path: Path) -> None:
    path = tmp_path / "BTCUSD#_H4.csv"
    path.write_text(
        "time;open;high;low;close;tick_volume;spread;real_volume\n"
        + "\n".join(row.replace(",", ";") for row in ROWS)
        + "\n",
        encoding="utf-8",
    )
    frame = load_csv(path, "H4")
    assert len(frame) == 2
    assert frame["time"].iloc[-1] == pd.Timestamp("2026-08-04 04:00:00")
