import math
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(ROOT / "bootstrap" / "materialize_assets.py")], check=True)
sys.path.insert(0, str(ROOT / "scripts"))
import shadow_full95_all_q20_v1 as s


def test_context_features_last_trade():
    history = [{
        "net_pnl": -100.0, "entry_atr": 50.0, "exit_reason": "INITIAL_SL",
        "wall_clock_minutes": 60.0, "exit_time": "2026-01-01T03:00:00",
        "entry_event_id": "x"
    }]
    out = s.context_features(history, s.pd.Timestamp("2026-01-01T04:00:00"))
    assert out["prev_net_atr"] == -2.0
    assert out["prev_loss"] == 1.0
    assert out["prev_initial_sl"] == 1.0
    assert out["prior_loss_streak"] == 1.0
    assert math.isclose(out["minutes_since_prev_exit_log"], math.log1p(60.0))


def test_aligned_day_open_distance_is_positive_for_short():
    out = s.add_aligned_features({"day_open_distance_m15atr": 2.5, "h4_rsi14": .5, "h1_rsi14": .5, "m15_rsi14": .5}, "SHORT")
    assert out["signed_day_open_distance_m15atr"] == 2.5


def test_model_contract_loads():
    features, medians, threshold, booster = s.load_model()
    assert len(features) == 95
    assert len(medians) == 95
    assert booster.num_feature() == 95
    assert math.isfinite(threshold)
