from pathlib import Path
import importlib.util
import json
import sys

import pandas as pd

MODULE_PATH = Path(__file__).parents[2] / "scripts" / "btc_ml_v1" / "BCR13_b3_outcome_blind_density_audit" / "python" / "run_bcr13_b3_density_audit.py"
spec = importlib.util.spec_from_file_location("bcr13", MODULE_PATH)
bcr13 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bcr13
spec.loader.exec_module(bcr13)


def make_frame(n=90):
    times = pd.date_range("2026-01-01 00:00:00", periods=n, freq="15min")
    rows = []
    for t in times:
        rows.append({"time": t, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0})
    return pd.DataFrame(rows)


def test_long_breakout_retest_reaccel_entry_and_exit():
    df = make_frame()
    df.loc[40, ["open", "high", "low", "close"]] = [100.0, 102.4, 99.8, 102.0]
    df.loc[41, ["open", "high", "low", "close"]] = [102.0, 102.1, 101.2, 101.5]
    df.loc[42, ["open", "high", "low", "close"]] = [101.5, 103.2, 101.4, 103.0]
    df.loc[45, ["open", "high", "low", "close"]] = [101.0, 101.1, 99.7, 99.8]
    df = bcr13.add_causal_features(df)
    out = bcr13.replay_machine(df, bcr13.MachineSpec("T", 32, 0.25, 4))
    assert out["metrics"]["entries"] == 1
    assert out["metrics"]["closed_episodes"] == 1
    assert out["metrics"]["closed_long"] == 1
    assert out["counts"]["breakout"] >= 1
    assert out["counts"]["retest"] >= 1
    assert out["counts"]["reacceleration"] >= 1
    ep = out["episodes"][0]
    assert ep["entry_time"].startswith("2026-01-01 10:45:00")
    assert ep["exit_time"].startswith("2026-01-01 11:30:00")
    assert ep["holding_bars"] == 3


def test_current_bar_hlc_not_used_for_signal():
    df = make_frame(50)
    df.loc[41, ["open", "high", "low", "close"]] = [100.0, 150.0, 50.0, 149.0]
    df = bcr13.add_causal_features(df)
    out = bcr13.replay_machine(df, bcr13.MachineSpec("T", 32, 0.25, 4))
    boundary = "2026-01-01 10:15:00"
    assert not any(
        x["boundary_time"].startswith(boundary) and x["event"] == "BREAKOUT_ARMED"
        for x in out["transitions"]
    )


def test_pending_gap_cancels_without_fallback():
    df = make_frame(70)
    df.loc[40, ["open", "high", "low", "close"]] = [100.0, 102.4, 99.8, 102.0]
    df = df.drop(index=42).reset_index(drop=True)
    df = bcr13.add_causal_features(df)
    out = bcr13.replay_machine(df, bcr13.MachineSpec("T", 32, 0.25, 8))
    assert out["counts"]["cancel_gap_in_sequence"] >= 1
    assert out["metrics"]["fallback_or_interpolation_used"] is False


def test_simultaneous_conflict_is_fail_closed():
    df = bcr13.add_causal_features(make_frame(70))
    original = bcr13._breakout_flags
    bcr13._breakout_flags = lambda *args, **kwargs: (True, True, 2.0, 101.0, 99.0)
    try:
        out = bcr13.replay_machine(df, bcr13.MachineSpec("T", 32, 0.25, 4))
    finally:
        bcr13._breakout_flags = original
    assert out["counts"]["simultaneous_breakout_conflict"] > 0
    assert out["metrics"]["entries"] == 0


def test_build_is_deterministic_and_contains_no_value_columns(tmp_path, monkeypatch):
    df = make_frame(90)
    df.loc[40, ["open", "high", "low", "close"]] = [100.0, 102.4, 99.8, 102.0]
    df.loc[41, ["open", "high", "low", "close"]] = [102.0, 102.1, 101.2, 101.5]
    df.loc[42, ["open", "high", "low", "close"]] = [101.5, 103.2, 101.4, 103.0]
    df.loc[45, ["open", "high", "low", "close"]] = [101.0, 101.1, 99.7, 99.8]
    csv_path = tmp_path / "m15.csv"
    df.to_csv(csv_path, index=False, lineterminator="\n")
    sha = bcr13.sha256_file(csv_path)
    monkeypatch.setattr(bcr13, "EXPECTED_INPUT_ROWS", len(df))
    monkeypatch.setattr(bcr13, "EXPECTED_INPUT_SHA256", sha)

    contract = {
        "stage": "BCR12_MATERIALLY_NEW_OUTCOME_BLIND_TRACK_B_MECHANISM_DESIGN",
        "frozen_input": {"BTC_M15_sha256": sha},
        "authorization": {"B3_outcome_access": False},
        "grammar": {
            "machines": [
                {"id": m[0], "L": m[1], "D": m[2], "W": m[3]}
                for m in bcr13.MACHINES
            ]
        },
    }
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    result = bcr13.build_with_repeat(csv_path, contract_path, tmp_path / "out", False)
    assert result["deterministic_repeat_match"] is True
    assert (tmp_path / "out" / bcr13.PACKAGE_NAME).exists()
    for csv_file in (tmp_path / "out").glob("*.csv"):
        cols = {c.lower() for c in pd.read_csv(csv_file, nrows=0).columns}
        assert not cols.intersection(bcr13.FORBIDDEN_OUTPUT_COLUMNS)


def test_append_only_prefix_rehydrate_accepts_only_exact_hash(tmp_path, monkeypatch):
    original = b"header\nrow1\nrow2\n"
    source = tmp_path / "live.csv"
    source.write_bytes(original + b"row3\n")
    monkeypatch.setattr(bcr13, "EXPECTED_INPUT_ROWS", 2)
    monkeypatch.setattr(bcr13, "EXPECTED_INPUT_SHA256", bcr13.sha256_bytes(original))
    resolved, meta = bcr13.resolve_frozen_input(source, tmp_path / "work", True)
    assert resolved.read_bytes() == original
    assert meta["prefix_rehydrated"] is True
