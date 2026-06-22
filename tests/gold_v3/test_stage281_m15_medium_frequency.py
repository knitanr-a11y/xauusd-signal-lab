from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] / "docs" / "gold_v3"


def test_stage280_preserved():
    contract = json.loads((ROOT / "gold_v3_stage281_final_contract.json").read_text())
    assert contract["preserved_stage280"]["state"] == "UNCHANGED_SHADOW_RESEARCH_ONLY"


def test_medium_candidate_year_counts_and_positive():
    df = pd.read_csv(ROOT / "gold_v3_stage281_medium_frequency_yearly.csv")
    q = df[df.variant == "STAGE281_MEDIUM_CAND_COST060"].set_index("year")
    assert q.loc[2024, "n"] == 39
    assert q.loc[2025, "n"] == 30
    assert q.loc[2026, "n"] == 14
    assert (q["sum"] > 0).all()
    assert (q["pf"] > 1).all()


def test_cost100_stays_positive():
    df = pd.read_csv(ROOT / "gold_v3_stage281_medium_frequency_yearly.csv")
    q = df[df.variant == "STAGE281_MEDIUM_CAND_COST100"]
    assert (q["pf"] > 1).all()
    assert (q["sum"] > 0).all()


def test_causal_gate_contract():
    contract = json.loads((ROOT / "gold_v3_stage281_final_contract.json").read_text())
    gate = contract["medium_frequency_near_miss"]["causal_synergy_gate"]
    assert gate["resolved_only"] is True
    assert gate["last_resolved_base_trade_pnl"] == "< 0"
    assert gate["hours_since_last_resolved_base_exit"] == "<= 72"


def test_no_active_promotion_and_flags_off():
    contract = json.loads((ROOT / "gold_v3_stage281_final_contract.json").read_text())
    assert contract["selected_active_addition"] == "NONE"
    assert contract["flags"]["audit_only"] is True
    assert all(
        value is False
        for key, value in contract["flags"].items()
        if key != "audit_only"
    )
