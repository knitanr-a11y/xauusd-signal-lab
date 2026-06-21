from pathlib import Path
import json
import pandas as pd

OUT = Path('/mnt/data/stage275_outcome_first_live_map')


def test_prefix_feature_parity_all_256():
    df = pd.read_csv(OUT / 'stage275_prefix_feature_parity.csv')
    assert len(df) == 256
    assert (df['status'] == 'PASS').all()
    assert float(df['max_abs_diff'].max()) == 0.0


def test_model_and_candidate_stream_parity():
    score = pd.read_csv(OUT / 'stage275_model_score_stream_parity.csv')
    cand = pd.read_csv(OUT / 'stage275_batch_stream_candidate_parity.csv')
    assert len(score) == 3
    assert score['chunk64_pass'].all()
    assert score['one_row_sample_pass'].all()
    assert len(cand) == 81
    assert cand['pass'].all()
    assert float(cand['score_max_abs_diff'].max()) == 0.0


def test_fixed_grid_and_no_posthoc_selection():
    grid = pd.read_csv(OUT / 'stage275_discovery_grid_2024.csv')
    selected = pd.read_csv(OUT / 'stage275_selected_cells_2024.csv')
    assert len(grid) == 81
    assert int(grid['discovery_lead'].sum()) == 0
    assert len(selected) == 0


def test_feature_contract_excludes_future_labels():
    c = json.loads((OUT / 'stage275_feature_contract.json').read_text())
    forbidden = {'FF1_24H','POS24','CLEAN1_24H','ret8_atr','ret24_atr','ret48_atr','mfe24_atr','mae24_atr','path_class'}
    assert forbidden.isdisjoint(c['feature_cols'])
    summary = json.loads((OUT / 'stage275_final_summary_20260621.json').read_text())
    assert summary['live_ready'] is False
    assert summary['discovery_leads'] == 0
