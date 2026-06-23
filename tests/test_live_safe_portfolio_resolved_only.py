from datetime import datetime, timedelta
from pathlib import Path

from gold_v3.live_safe_portfolio.config import load_config
from gold_v3.live_safe_portfolio.engine import SafePortfolioEngine
from gold_v3.live_safe_portfolio.models import Candidate, Direction, Resolution, Source
from gold_v3.live_safe_portfolio.state import SQLiteStateStore

CONFIG = Path(__file__).resolve().parents[1] / "config" / "gold_v3_live_safe_portfolio.audit_only.json"


def make_candidate(ident, source, entry, direction=Direction.LONG):
    entry_dt = datetime.fromisoformat(entry)
    signal_dt = entry_dt - timedelta(minutes=5)
    return Candidate(ident, source, direction, signal_dt, entry_dt, 120, True,
                     signal_dt, signal_dt, "MT5_SERVER_NAIVE")


def test_resolution_is_not_applied_before_exit(tmp_path):
    cfg = load_config(CONFIG)
    store = SQLiteStateStore(tmp_path / "state.sqlite", cfg.time_basis)
    engine = SafePortfolioEngine(cfg, store)
    engine.process_candidate(make_candidate("first", Source.STAGE280, "2026-06-01 10:00:00"))
    exit_dt = datetime.fromisoformat("2026-06-01 14:00:00")
    store.add_resolution(Resolution("first", exit_dt, -20.0, "LOSS", True, exit_dt))
    early = engine.process_candidate(make_candidate("early", Source.STAGE281, "2026-06-01 13:00:00"))
    assert early.dd_before_entry == 0.0
    assert early.reason == "ONE_POSITION_ACTIVE"
    late = engine.process_candidate(make_candidate("late", Source.SHORT_STRICT, "2026-06-02 15:00:00", Direction.SHORT))
    assert late.dd_before_entry == 20.0
