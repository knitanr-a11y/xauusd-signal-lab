from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] / "docs" / "gold_v3"


def test_2026_dollar_dd_but_lower_r_dd():
    df = pd.read_csv(ROOT / "gold_v3_stage282_risk_by_year.csv").set_index("year")
    assert df.loc[2026, "dollar_dd"] > df.loc[2025, "dollar_dd"]
    assert df.loc[2026, "r_dd"] < df.loc[2025, "r_dd"]
    assert df.loc[2026, "r_dd"] < df.loc[2024, "r_dd"]


def test_full_stop_risk_expanded():
    df = pd.read_csv(ROOT / "gold_v3_stage282_risk_by_year.csv").set_index("year")
    assert df.loc[2026, "median_full_sl_loss_usd"] > 3 * df.loc[2024, "median_full_sl_loss_usd"]


def test_risk_cap_reduces_2026_dd():
    df = pd.read_csv(ROOT / "gold_v3_stage282_risk_cap_yearly.csv")
    row = df[(df.full_sl_cap_usd == 7.5) & (df.year == 2026)].iloc[0]
    assert row.candidate_dd_cost060 <= 15.01
    assert row.integrated_dd <= 52.49


def test_no_guard_or_active_promotion():
    contract = json.loads((ROOT / "gold_v3_stage282_final_contract.json").read_text())
    assert contract["concentration_guards"]["decision"] == "NO_GUARD_PROMOTION"
    assert contract["selected_active_addition"] == "NONE"


def test_safety_flags_off():
    contract = json.loads((ROOT / "gold_v3_stage282_final_contract.json").read_text())
    assert contract["flags"]["audit_only"] is True
    assert all(v is False for k, v in contract["flags"].items() if k != "audit_only")
