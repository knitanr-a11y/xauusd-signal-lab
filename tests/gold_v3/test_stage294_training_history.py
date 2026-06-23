from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "scripts" / "gold_v3_runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from gold_v3_289_stage280_features import stage280_model_frame
from gold_v3_289_training_history_preflight import main as preflight_main


def test_stage280_engineering_keeps_values_without_fragmentation_warning():
    source = pd.DataFrame({
        "m1_ret5_atr": [0.5],
        "m1_ret15_atr": [0.3],
        "m1_ret30_atr": [-0.2],
        "m1_ret60_atr": [-0.6],
        "m1_ret120_atr": [-0.8],
        "m5_ret3_atr": [0.4],
        "m5_ret12_atr": [-0.2],
        "m15_ret1_atr": [0.1],
        "m15_ret4_atr": [-0.5],
        "m1_lower_wick_ratio": [0.7],
        "m1_upper_wick_ratio": [0.2],
        "m5_lower_wick_ratio": [0.6],
        "m5_upper_wick_ratio": [0.1],
        "m15_lower_wick_ratio": [0.4],
        "m15_upper_wick_ratio": [0.3],
        "h4_trend": [-1],
        "d1_trend": [1],
    })
    features = [
        "countermove_60", "turn_accel_5v30", "m5_turn_accel",
        "m15_turn_accel", "m1_reject_wick", "h4_align", "d1_align",
    ]
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = stage280_model_frame(source, features)
    assert not [item for item in captured if "fragmented" in str(item.message)]
    values = result.iloc[0].to_dict()
    assert values["countermove_60"] == pytest.approx(0.6)
    assert values["turn_accel_5v30"] == pytest.approx(0.64)
    assert values["m5_turn_accel"] == pytest.approx(0.6)
    assert values["m15_turn_accel"] == pytest.approx(0.3)
    assert values["m1_reject_wick"] == pytest.approx(0.5)
    assert values["h4_align"] == pytest.approx(-1.0)
    assert values["d1_align"] == pytest.approx(1.0)


def test_stage280_rev_long_features_keep_market_direction():
    source = pd.DataFrame({
        "m1_ret60_atr": [-0.6, 0.6],
        "m1_ret5_atr": [0.5, -0.5],
        "m1_ret30_atr": [-0.2, 0.2],
        "m1_pos60": [0.8, 0.2],
        "m1_lower_wick_ratio": [0.7, 0.2],
        "m1_upper_wick_ratio": [0.2, 0.7],
        "h4_trend": [-1, 1],
        "d1_trend": [-1, 1],
    })
    features = [
        "m1_ret60_atr", "m1_ret5_atr", "m1_pos60",
        "m1_lower_wick_ratio", "m1_upper_wick_ratio",
        "countermove_60", "turn_accel_5v30", "m1_reject_wick",
        "h4_align", "d1_align",
    ]
    result = stage280_model_frame(source, features)
    assert result.iloc[0]["m1_ret60_atr"] == pytest.approx(-0.6)
    assert result.iloc[1]["m1_ret60_atr"] == pytest.approx(0.6)
    assert result.iloc[0]["m1_pos60"] == pytest.approx(0.6)
    assert result.iloc[1]["m1_pos60"] == pytest.approx(-0.6)
    assert result.iloc[0]["h4_align"] == pytest.approx(-1.0)
    assert result.iloc[1]["h4_align"] == pytest.approx(1.0)
    assert result.iloc[0]["m1_reject_wick"] == pytest.approx(0.5)
    assert result.iloc[1]["m1_reject_wick"] == pytest.approx(-0.5)


def test_stage280_training_uses_future_valid_long_rev_contract():
    source = (RUNTIME / "gold_v3_289_train_live_models_audit.py").read_text(encoding="utf-8")
    assert 'ctx["future_valid"]' in source
    assert 'ctx.h4_trend.ne(0)&ctx.future_valid' in source
    assert 'z.event_dir.eq(1)&z.h4_trend.eq(-1)' in source
    assert 'stage280_model_frame(z,features)' in source


def test_preflight_blocks_missing_training_history(tmp_path, monkeypatch):
    report = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", [
        "preflight", "--candle-dir", str(tmp_path), "--report", str(report)
    ])
    assert preflight_main() == 2
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "BLOCKED_TRAINING_HISTORY_INCOMPLETE"
    assert any(item.startswith("MISSING_M1") for item in payload["blockers"])


def test_history_exporter_and_runner_contracts():
    exporter = (RUNTIME / "mt5" / "ExportGoldStage289TrainingHistory_v110.mq5").read_text(encoding="utf-8")
    assert '#property version "1.10"' in exporter
    assert 'ExportTimeframe(PERIOD_M1,"goldsharp_m1.csv")' in exporter
    assert 'ExportTimeframe(PERIOD_M5,"goldsharp_m5.csv")' in exporter
    assert 'ExportTimeframe(PERIOD_M15,"goldsharp_m15.csv")' in exporter

    installer = (RUNTIME / "bat" / "install_gold_v3_289_training_m1_exporter.bat").read_text(encoding="utf-8")
    assert "ExportGoldStage289TrainingHistory_v110.mq5" in installer

    one_shot = (RUNTIME / "bat" / "run_gold_v3_292_safe_portfolio_live.bat").read_text(encoding="utf-8")
    assert "for %%F in (h1 h4 d1)" in one_shot
    assert "for %%F in (m5 m15 h1 h4 d1)" not in one_shot

    continuous = (RUNTIME / "bat" / "run_gold_v3_292_safe_portfolio_live_continuous.bat").read_text(encoding="utf-8")
    assert "gold_v3_289_train_live_models_audit.py" not in continuous
    assert "Stage280/281 models are not ready" in continuous
