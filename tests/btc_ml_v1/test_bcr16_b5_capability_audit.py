from pathlib import Path
import importlib.util
import json
import sys

import pandas as pd

MODULE_PATH = Path(__file__).parents[2] / "scripts" / "btc_ml_v1" / "BCR16_b5_h1_impulse_m15_reclaim_capability_audit" / "python" / "run_bcr16_b5_capability_audit.py"
spec = importlib.util.spec_from_file_location("bcr16", MODULE_PATH)
bcr16 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bcr16
spec.loader.exec_module(bcr16)


def make_frame(hours=40):
    times = pd.date_range("2026-01-01 00:00:00", periods=hours * 4, freq="15min")
    rows = [{"time": t, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0} for t in times]
    return pd.DataFrame(rows)


def prepare_long_path():
    df = make_frame()
    base = 20 * 4
    df.loc[base + 0, ["open", "high", "low", "close"]] = [100.0, 101.5, 99.8, 101.2]
    df.loc[base + 1, ["open", "high", "low", "close"]] = [101.2, 102.5, 101.0, 102.2]
    df.loc[base + 2, ["open", "high", "low", "close"]] = [102.2, 103.6, 102.0, 103.4]
    df.loc[base + 3, ["open", "high", "low", "close"]] = [103.4, 104.4, 103.2, 104.2]
    df.loc[base + 4, ["open", "high", "low", "close"]] = [102.7, 102.8, 102.0, 102.5]
    df.loc[base + 5, ["open", "high", "low", "close"]] = [102.5, 104.1, 102.4, 104.0]
    df.loc[base + 8, ["open", "high", "low", "close"]] = [104.5, 106.2, 104.4, 106.0]
    return bcr16.add_m15_features(df)


def test_complete_h1_only():
    df = bcr16.add_m15_features(make_frame(20))
    full = bcr16.build_complete_h1(df)
    assert len(full) == 20
    broken = df.drop(index=7).reset_index(drop=True)
    incomplete = bcr16.build_complete_h1(broken)
    assert len(incomplete) == 19


def test_long_impulse_pullback_reclaim_and_success_exit():
    df = prepare_long_path()
    h1 = bcr16.build_complete_h1(df)
    out = bcr16.replay_machine(df, h1, bcr16.MachineSpec("T", 6, 0.75, 8))
    assert out["metrics"]["entries"] >= 1
    assert out["metrics"]["closed_episodes"] >= 1
    assert out["counts"]["h1_impulse"] >= 1
    assert out["counts"]["pullback"] >= 1
    assert out["counts"]["reclaim"] >= 1
    assert any(e["exit_reason"] == "STRUCTURAL_SUCCESS" for e in out["episodes"])


def test_fixed_expiry_closes_episode():
    df = prepare_long_path()
    base = 20 * 4
    for i in range(base + 7, len(df)):
        df.loc[i, ["open", "high", "low", "close"]] = [104.0, 104.5, 103.5, 104.0]
    df = bcr16.add_m15_features(df[["time", "open", "high", "low", "close"]])
    h1 = bcr16.build_complete_h1(df)
    out = bcr16.replay_machine(df, h1, bcr16.MachineSpec("T", 6, 0.75, 8))
    assert any(e["exit_reason"] == "THESIS_EXPIRY_32_BARS" for e in out["episodes"])
    assert max(e["holding_bars"] for e in out["episodes"] if not e["endpoint_open"]) == 32


def test_pending_gap_cancels_without_fallback():
    df = prepare_long_path().drop(index=20 * 4 + 5).reset_index(drop=True)
    h1 = bcr16.build_complete_h1(df)
    out = bcr16.replay_machine(df, h1, bcr16.MachineSpec("T", 6, 0.75, 16))
    assert out["counts"]["cancel_gap_in_sequence"] >= 1
    assert out["metrics"]["fallback_or_interpolation_used"] is False


def test_deterministic_package_and_no_value_columns(tmp_path, monkeypatch):
    df = prepare_long_path()[["time", "open", "high", "low", "close"]]
    csv_path = tmp_path / "m15.csv"
    df.to_csv(csv_path, index=False, lineterminator="\n")
    sha = bcr16.sha256_file(csv_path)
    monkeypatch.setattr(bcr16, "EXPECTED_INPUT_ROWS", len(df))
    monkeypatch.setattr(bcr16, "EXPECTED_INPUT_SHA256", sha)
    contract = {
        "stage": "BCR15_MATERIALLY_NEW_OUTCOME_BLIND_TRACK_B_MECHANISM_DESIGN",
        "frozen_input": {"BTC_M15_sha256": sha},
        "authorization": {"B5_outcome_access": False},
        "grammar": {"machines": [{"id": x[0], "R": x[1], "B": x[2], "W": x[3]} for x in bcr16.MACHINES]},
    }
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    result = bcr16.build_with_repeat(csv_path, contract_path, tmp_path / "out", False)
    assert result["deterministic_repeat_match"] is True
    for path in (tmp_path / "out").glob("*.csv"):
        cols = {c.lower() for c in pd.read_csv(path, nrows=0).columns}
        assert not cols.intersection(bcr16.FORBIDDEN_OUTPUT_COLUMNS)


def test_exact_prefix_rehydrate_only(tmp_path, monkeypatch):
    original = b"h\nr1\nr2\n"
    source = tmp_path / "live.csv"
    source.write_bytes(original + b"r3\n")
    monkeypatch.setattr(bcr16, "EXPECTED_INPUT_ROWS", 2)
    monkeypatch.setattr(bcr16, "EXPECTED_INPUT_SHA256", bcr16.sha256_bytes(original))
    resolved, meta = bcr16.resolve_frozen_input(source, tmp_path / "work", True)
    assert resolved.read_bytes() == original
    assert meta["prefix_rehydrated"] is True
