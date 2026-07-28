from pathlib import Path
import json
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2] / "docs" / "gold_v3"
ROOT = REPO_ROOT if REPO_ROOT.exists() else Path("/mnt/data")


def test_external_coverage_and_parity():
    coverage = pd.read_csv(ROOT / "gold_v3_stage285_external_coverage_audit.csv")
    parity = pd.read_csv(ROOT / "gold_v3_stage285_gold_parity_audit.csv")
    assert len(coverage) == 25
    assert (coverage.gold_time_coverage > 0.99).all()
    assert parity.all_equal.all()


def test_cross_raw_all_years_positive_and_cost_stress():
    data = pd.read_csv(ROOT / "gold_v3_stage285_retained_candidate_yearly.csv")
    cross = data[data.candidate == "CROSS_LONG"]
    assert set(cross.year) == {2024, 2025, 2026}
    assert (cross.pf > 1).all()
    assert (cross.pf_cost100 > 1).all()
    assert (cross["sum"] > 0).all()


def test_short_no_discovery():
    contract = json.loads((ROOT / "gold_v3_stage285_final_contract.json").read_text())
    assert contract["four_tracks"]["short"]["decision"] == "NO_DISCOVERY"


def test_no_active_and_flags_off():
    contract = json.loads((ROOT / "gold_v3_stage285_final_contract.json").read_text())
    assert contract["selected_active_addition"] == "NONE"
    assert contract["flags"]["audit_only"] is True
    assert all(
        value is False
        for key, value in contract["flags"].items()
        if key != "audit_only"
    )


def test_2026_not_used_for_selection_contract():
    contract = json.loads((ROOT / "gold_v3_stage285_final_contract.json").read_text())
    assert contract["protocol"]["development_year"] == 2024
    assert contract["protocol"]["confirmation_year"] == 2025
    assert contract["protocol"]["display_only_year"] == 2026
