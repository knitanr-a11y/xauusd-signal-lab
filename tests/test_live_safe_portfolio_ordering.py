from datetime import datetime, timedelta
from pathlib import Path

import pytest

from gold_v3.live_safe_portfolio.config import load_config
from gold_v3.live_safe_portfolio.engine import SafePortfolioEngine
from gold_v3.live_safe_portfolio.models import Candidate, Direction, Resolution, Source
from gold_v3.live_safe_portfolio.state import SQLiteStateStore

CONFIG = Path(__file__).resolve().parents[1] / "config" / "gold_v3_live_safe_portfolio.audit_only.json"


def c(ident, source, entry):
    entry_dt = datetime.fromisoformat(entry)
    signal_dt = entry_dt - timedelta(minutes=5)
    return Candidate(ident, source, Direction.LONG, signal_dt, entry_dt, 120,
                     True, signal_dt, signal_dt, "MT5_SERVER_NAIVE")


def test_year_state_and_ordering(tmp_path):
    cfg = load_config(CONFIG)
    store = SQLiteStateStore(tmp_path / "state.sqlite", cfg.time_basis)
    engine = SafePortfolioEngine(cfg, store)
    engine.process_candidate(c("add", Source.STAGE280, "2026-12-31 18:00:00"))
    exit_dt = datetime.fromisoformat("2026-12-31 20:00:00")
    store.add_resolution(Resolution("add", exit_dt, -8.0, "LOSS", True, exit_dt))
    decision = engine.process_candidate(c("base", Source.BASE, "2027-01-01 10:00:00"))
    assert decision.dd_before_entry == 8.0
    with pytest.raises(ValueError, match="out-of-order"):
        engine.process_candidate(c("old", Source.BASE, "2026-06-01 10:00:00"))
