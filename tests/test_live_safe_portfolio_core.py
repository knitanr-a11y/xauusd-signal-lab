from datetime import datetime, timedelta
from pathlib import Path

from gold_v3.live_safe_portfolio.config import load_config
from gold_v3.live_safe_portfolio.engine import SafePortfolioEngine
from gold_v3.live_safe_portfolio.models import Candidate, DecisionStatus, Direction, Source
from gold_v3.live_safe_portfolio.state import SQLiteStateStore
from gold_v3.live_safe_portfolio.strict_short import strict_short_passes

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "gold_v3_live_safe_portfolio.audit_only.json"


def make_candidate(ident, source, entry, direction=Direction.LONG, hold=120):
    entry_dt = datetime.fromisoformat(entry)
    signal_dt = entry_dt - timedelta(minutes=5)
    return Candidate(ident, source, direction, signal_dt, entry_dt, hold, True,
                     signal_dt, signal_dt, "MT5_SERVER_NAIVE")


def make_engine(tmp_path):
    cfg = load_config(CONFIG)
    store = SQLiteStateStore(tmp_path / "state.sqlite", cfg.time_basis)
    return cfg, store, SafePortfolioEngine(cfg, store)


def test_flags_off():
    cfg = load_config(CONFIG)
    assert cfg.flags.audit_only
    assert not cfg.flags.live_ready
    assert not cfg.flags.final_signal
    assert not cfg.flags.mt5_order
    assert not cfg.flags.discord_notify
    assert not cfg.flags.partial_close


def test_rollover_and_priority(tmp_path):
    _, _, engine = make_engine(tmp_path)
    base = make_candidate("base", Source.BASE, "2026-06-01 23:30:00")
    assert engine.process_candidate(base).reason == "BASE_ROLLOVER_00_01_SHADOW_ONLY"
    added = make_candidate("added", Source.STAGE280, "2026-06-01 23:30:00")
    assert engine.process_candidate(added).status == DecisionStatus.ACCEPTED_SHADOW


def test_strict_thresholds_fixed():
    cfg = load_config(CONFIG)
    row = {"source_candidate": "SHORT_EXHAUST_Q90_EMA20_E225_CD120",
           "base_short_exhaust_q90": True, "score": 2.9,
           "sp_m15_ret4_atr": 0.3, "nq_m15_ret4_atr": 0.4}
    assert strict_short_passes(row, cfg.strict_short)[0]
    row["score"] = 3.1
    assert not strict_short_passes(row, cfg.strict_short)[0]
