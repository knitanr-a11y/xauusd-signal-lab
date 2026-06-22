from pathlib import Path
import json
import pandas as pd

OUT = Path('/mnt/data/stage276_sequence_state_transition')


def test_prefix_feature_parity_all_64():
    df = pd.read_csv(OUT / 'stage276_prefix_feature_parity.csv')
    assert len(df) == 64
    assert (df['status'] == 'PASS').all()
    assert df['nan_pattern_exact'].all()
    assert float(df['max_abs_diff'].max()) == 0.0


def test_model_and_candidate_replay_parity():
    model = pd.read_csv(OUT / 'stage276_model_score_stream_parity.csv')
    candidate = pd.read_csv(OUT / 'stage276_batch_stream_candidate_parity.csv')
    assert len(model) == 4
    assert model['pass'].all()
    assert float(model['chunk64_max_abs_diff'].max()) == 0.0
    assert float(model['one_row_max_abs_diff'].max()) <= 1e-12
    assert len(candidate) == 16
    assert candidate['pass'].all()
    assert candidate['index_exact'].all()
    assert candidate['direction_exact'].all()


def test_fixed_stage276_grid_and_no_posthoc_promotion():
    ranking = pd.read_csv(OUT / 'stage276_all_cell_ranking.csv')
    selected = pd.read_csv(OUT / 'stage276_selected_cells_2024.csv')
    assert len(ranking) == 112
    assert int(ranking['discovery_pass'].sum()) == 0
    assert len(selected) == 0
    assert set(ranking['source']) == {'SEQUENCE_MODEL', 'EVENT_RULE'}


def test_feature_contract_and_safety_flags():
    contract = json.loads((OUT / 'stage276_feature_contract.json').read_text())
    forbidden = {
        'quality_y', 'positive_y', 'label_end_idx', 'future_return',
        'mfe', 'mae', 'exit_type', 'gross_r', 'gross_usd'
    }
    assert forbidden.isdisjoint(contract['feature_cols'])
    assert contract['feature_count'] == 48
    summary = json.loads((OUT / 'stage276_final_summary.json').read_text())
    assert summary['status'] == 'GOLD_V3_276_NO_DISCOVERY_LEAD_AUDIT_ONLY'
    assert summary['live_ready'] is False
    assert summary['final_signal'] is False
    assert summary['mt5_order'] is False
    assert summary['discord_notify'] is False
    assert summary['discovery_leads_2024'] == 0
    assert summary['prefix_feature_parity_pass'] is True
    assert summary['model_score_parity_pass'] is True
    assert summary['candidate_replay_parity_pass'] is True
