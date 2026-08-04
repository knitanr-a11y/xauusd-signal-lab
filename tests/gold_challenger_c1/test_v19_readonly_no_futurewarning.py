from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.gold_challenger_c1.v19_readonly import _rank_day_exact, _reconstruct_score_ledger


def _calibration_frame() -> pd.DataFrame:
    times = pd.date_range("2026-05-01 00:00:00", periods=240, freq="h")
    return pd.DataFrame(
        {
            "entry_time": times,
            "score_long": np.linspace(0.05, 0.95, len(times)),
            "score_short": np.linspace(0.95, 0.05, len(times)),
        }
    )


def test_rank_day_does_not_concat_empty_history() -> None:
    calibration = _calibration_frame()
    current = pd.DataFrame(
        {
            "entry_time": [pd.Timestamp("2026-05-15 12:00:00")],
            "score_long": [0.70],
            "score_short": [0.30],
        }
    )
    empty_history = pd.DataFrame(columns=["entry_time", "score_long", "score_short"])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", FutureWarning)
        ranked = _rank_day_exact(current, empty_history, calibration)
    assert not [item for item in caught if issubclass(item.category, FutureWarning)]
    assert ranked.loc[0, "chosen_side"] == "LONG"


def test_reconstruct_score_ledger_has_no_empty_concat_futurewarning(tmp_path: Path) -> None:
    boundary = pd.Timestamp("2026-05-01")
    history = pd.DataFrame(
        {
            "entry_time": [
                "2026-05-12 10:00:00",
                "2026-05-13 10:00:00",
            ],
            "origin_id": [1, 2],
            "score_long": [0.70, 0.20],
            "score_short": [0.30, 0.80],
            "model_boundary": ["2026-05-01", "2026-05-01"],
        }
    )
    history.to_csv(tmp_path / "score_history.csv.gz", index=False, compression="gzip")
    model_dir = tmp_path / "models" / "2026-05-01"
    model_dir.mkdir(parents=True)
    _calibration_frame().to_csv(model_dir / "calibration_scores.csv.gz", index=False, compression="gzip")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", FutureWarning)
        ledger, details = _reconstruct_score_ledger(
            tmp_path,
            boundary,
            pd.Timestamp("2026-05-13 10:00:00"),
        )

    assert not [item for item in caught if issubclass(item.category, FutureWarning)]
    assert len(ledger) == 2
    assert details["pending_score_rows"] == 0
    assert ledger["chosen_side"].tolist() == ["LONG", "SHORT"]
