from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

import pandas as pd
import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "btc_ml_v1"
    / "BCR17_b5_shared_retrospective_value_gate"
    / "python"
    / "run_bcr17_b5_shared_value_gate.py"
)
spec = importlib.util.spec_from_file_location("bcr17", MODULE_PATH)
bcr17 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bcr17)


def test_fill_prices_long_and_short():
    long = bcr17._fill_prices("LONG", 100.0, 110.0, 2.0, 3.0)
    assert long["pnl_c0_usd_1lot"] == pytest.approx(8.0)
    assert long["pnl_c2_usd_1lot"] == pytest.approx(6.75)

    short = bcr17._fill_prices("SHORT", 100.0, 90.0, 2.0, 3.0)
    assert short["pnl_c0_usd_1lot"] == pytest.approx(7.0)
    assert short["pnl_c2_usd_1lot"] == pytest.approx(5.75)


def test_path_excursions_exclude_exit_bar_high_low():
    df = pd.DataFrame(
        {
            "time": pd.to_datetime(
                ["2026-01-01 00:00", "2026-01-01 00:15", "2026-01-01 00:30"]
            ),
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 106.0, 999.0],
            "low": [95.0, 96.0, 1.0],
            "close": [101.0, 102.0, 103.0],
            "spread_price": [2.0, 2.0, 2.0],
        }
    )
    out = bcr17._path_excursions(
        "LONG", df, 0, 2, 100.0, 2.0, 102.0, 2.0
    )
    assert out["mfe_c0_usd_1lot"] == pytest.approx(4.0)
    assert out["mae_c0_usd_1lot"] == pytest.approx(-7.0)


def test_exact_wilcoxon_and_holm():
    strong = bcr17.exact_wilcoxon_greater([1, 2, 3, 4])
    assert strong["p_one_sided_greater"] == pytest.approx(1 / 16)

    adjusted = bcr17.holm_adjust({"a": 0.01, "b": 0.04, "c": 0.20})
    assert adjusted["a"] == pytest.approx(0.03)
    assert adjusted["b"] == pytest.approx(0.08)
    assert adjusted["c"] == pytest.approx(0.20)


def test_classification_ladder():
    positive = {"net_usd_1lot": 10.0, "profit_factor": 1.2}
    negative = {"net_usd_1lot": -1.0, "profit_factor": 0.9}

    assert (
        bcr17._classification(positive, positive, 0.04)
        == "VALUE_SUPPORTED_RETROSPECTIVE"
    )
    assert (
        bcr17._classification(positive, positive, 0.50)
        == "VALUE_PROMISING_RETROSPECTIVE"
    )
    assert (
        bcr17._classification(positive, negative, 0.50)
        == "HOLD_COST_SENSITIVE"
    )
    assert (
        bcr17._classification(negative, negative, 0.50)
        == "REJECT_RETROSPECTIVE_VALUE"
    )


def _make_source_package(path: Path, machine: str) -> None:
    episodes = pd.DataFrame(
        [
            {
                "machine_id": machine,
                "direction": "LONG",
                "impulse_h1_open": "2026-01-01 00:00:00",
                "pullback_time": "2026-01-01 01:00:00",
                "reclaim_time": "2026-01-01 01:15:00",
                "entry_time": "2026-01-01 01:30:00",
                "exit_time": "2026-01-01 02:00:00",
                "holding_bars": 2,
                "endpoint_open": False,
                "exit_reason": "STRUCTURAL_SUCCESS",
            }
        ]
    )
    metrics = pd.DataFrame(
        [{"machine_id": machine, "closed_episodes": 1, "capability_pass": True}]
    )
    members = {
        "bcr16_episode_ledger.csv": episodes.to_csv(index=False),
        "bcr16_machine_metrics.csv": metrics.to_csv(index=False),
        "bcr16_summary.json": json.dumps(
            {
                "input_rows": bcr17.EXPECTED_INPUT_ROWS,
                "input": {"frozen_sha256": bcr17.EXPECTED_INPUT_SHA256},
                "all_eight_reported": True,
                "capability_pass_count": 8,
                "outcome_fields_opened": False,
                "value_evaluation_performed": False,
            }
        ),
        "bcr16_event_counts.csv": "x\n",
        "bcr16_gate_checks.csv": "x\n",
        "bcr16_monthly_entries.csv": "x\n",
        "bcr16_transition_ledger.csv": "x\n",
        "manifest.json": "{}",
    }
    with zipfile.ZipFile(path, "w") as zf:
        for name, text in members.items():
            zf.writestr(name, text)


def test_bcr16_package_sha_hard_gate(tmp_path):
    package = tmp_path / "source.zip"
    _make_source_package(package, bcr17.MACHINES[0])

    with pytest.raises(ValueError, match="SHA mismatch"):
        bcr17.load_bcr16_package(package)


def test_deterministic_zip(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "a.txt").write_text("a\n", encoding="utf-8")
    (out / "b.txt").write_text("b\n", encoding="utf-8")

    first = bcr17._deterministic_zip(out, [out / "b.txt", out / "a.txt"])
    sha_first = bcr17.sha256_file(first)
    first.unlink()

    second = bcr17._deterministic_zip(out, [out / "a.txt", out / "b.txt"])
    sha_second = bcr17.sha256_file(second)

    assert sha_first == sha_second
