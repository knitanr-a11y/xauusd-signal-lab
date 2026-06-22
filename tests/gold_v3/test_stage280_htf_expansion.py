from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] / "docs" / "gold_v3"


def test_event_counts():
    data = pd.read_csv(ROOT / "gold_v3_stage280_event_counts.csv")
    assert data.n.sum() == 1561
    assert data[data.subtype == "REV"].n.sum() == 540


def test_calibrated_rev_lift():
    data = pd.read_csv(ROOT / "gold_v3_stage280_calibrated_model_metrics.csv")
    rev = data[data.subtype == "REV"].set_index("year")
    assert (rev.q95_lift > 2.0).all()


def test_cont_2026_not_promoted():
    data = pd.read_csv(ROOT / "gold_v3_stage280_calibrated_model_metrics.csv")
    row = data[(data.subtype == "CONT") & (data.year == 2026)].iloc[0]
    assert row.q95_rate == 0.0


def test_no_active_promotion_and_flags_off():
    contract = json.loads((ROOT / "gold_v3_stage280_final_contract.json").read_text())
    assert contract["selected_active_addition"] == "NONE"
    assert contract["flags"]["audit_only"] is True
    assert all(
        value is False
        for key, value in contract["flags"].items()
        if key != "audit_only"
    )


def test_shadow_candidate_three_year_positive():
    data = pd.read_csv(ROOT / "gold_v3_stage280_shadow_candidate_yearly.csv")
    candidate = data[data.variant == "REV_LONG_Q95_BRK6_E175_CAND"]
    assert set(candidate.year) == {2024, 2025, 2026}
    assert (candidate["sum"] > 0).all()
    assert (candidate.pf > 1).all()
