from pathlib import Path
import importlib.util
import sys
import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "btc_ai_v1" / "run_ohlc_rolling_adaptive_recalibration_forensic.py"
spec = importlib.util.spec_from_file_location("rolling", SCRIPT)
rolling = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rolling
assert spec.loader is not None
spec.loader.exec_module(rolling)


def synthetic_meta():
    times = pd.date_range("2023-09-01", "2024-03-31 23:45", freq="15min")
    n = len(times)
    maturity = (times + pd.Timedelta(hours=4)).view("int64")
    late = (times >= pd.Timestamp("2023-12-31 21:00")) & (times < pd.Timestamp("2024-01-01"))
    maturity[late] = pd.Timestamp("2024-01-01 03:00").value
    meta = pd.DataFrame({
        "decision_time": times,
        "maturity_ns": maturity,
        "label_long": (np.arange(n) % 3 == 0).astype("int8"),
        "label_short": (np.arange(n) % 4 == 0).astype("int8"),
        "d1_trend": np.where(np.arange(n) % 3 == 0, 1, np.where(np.arange(n) % 3 == 1, 0, -1)),
    })
    meta["month"] = rolling.stable_month_start(meta.decision_time)
    meta["d1_regime"] = rolling.d1_regime(meta.d1_trend)
    return meta, late


def test_resolved_only_monthly_training_cutoff():
    meta, late = synthetic_meta()
    cfg = rolling.FormalConfig(min_training_rows=1, min_positive_labels=1, n_estimators=2)
    cutoff = pd.Timestamp("2024-01-01")
    masks = rolling.build_masks(meta, cutoff, "ROLLING_3M", "LONG", cfg)
    train = masks["train"]
    assert not np.any(train & late)
    assert (meta.loc[train, "decision_time"] < masks["refit_time"]).all()
    assert (meta.loc[train, "maturity_ns"] <= pd.Timestamp(masks["refit_time"]).value).all()
    assert rolling.audit_masks(meta, masks, cutoff) == {
        "train_future_or_current_decision_count": 0,
        "train_unresolved_at_refit_count": 0,
        "calibration_outside_previous_month_count": 0,
        "train_validation_overlap_count": 0,
        "calibration_validation_overlap_count": 0,
        "validation_outside_target_month_count": 0,
        "selection_rows_2026_or_later_count": 0,
    }


def test_calibration_is_immediately_previous_month_only():
    meta, _ = synthetic_meta()
    cfg = rolling.FormalConfig(min_training_rows=1, min_positive_labels=1, n_estimators=2)
    cutoff = pd.Timestamp("2024-03-01")
    masks = rolling.build_masks(meta, cutoff, "EXPANDING", "SHORT", cfg)
    cal_times = meta.loc[masks["calibration"], "decision_time"]
    assert cal_times.min() == pd.Timestamp("2024-02-01")
    assert cal_times.max() < cutoff
    assert (cal_times >= pd.Timestamp("2024-02-01")).all()


def test_formal_months_exclude_2026():
    assert len(rolling.FORMAL_MONTHS) == 24
    assert rolling.FORMAL_MONTHS[0] == pd.Timestamp("2024-01-01")
    assert rolling.FORMAL_MONTHS[-1] == pd.Timestamp("2025-12-01")
    assert all(month < pd.Timestamp("2026-01-01") for month in rolling.FORMAL_MONTHS)


def test_psi_zero_for_identical_distribution():
    x = np.linspace(-2, 2, 1000)
    assert abs(rolling.psi(x, x, bins=10)) < 1e-12


def test_schedule_start_is_past_only():
    cutoff = pd.Timestamp("2025-07-01")
    cfg = rolling.FormalConfig()
    assert rolling.schedule_start(cutoff, "EXPANDING", cfg) == pd.Timestamp("2023-01-01")
    assert rolling.schedule_start(cutoff, "ROLLING_3M", cfg) == pd.Timestamp("2025-04-01")
    assert rolling.schedule_start(cutoff, "ROLLING_6M", cfg) == pd.Timestamp("2025-01-01")
    assert rolling.schedule_start(cutoff, "ROLLING_12M", cfg) == pd.Timestamp("2024-07-01")
