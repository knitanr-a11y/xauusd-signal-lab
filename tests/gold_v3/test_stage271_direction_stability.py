import importlib.util
import pandas as pd
import numpy as np

spec=importlib.util.spec_from_file_location('s','/mnt/data/stage271_direction_stability.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)


def test_direction_aligned_features_are_symmetric():
    df=pd.DataFrame({
        'direction':[1.0,-1.0], 'd1_direction':[1.0,-1.0], 'h4_direction':[-1.0,1.0],
        'h1_rsi14':[60.0,40.0], 'h1_macd_hist_atr':[0.2,-0.2],
        'h1_ema_spread_signed_atr':[0.5,-0.5], 'h1_ema_slope3_atr':[0.1,-0.1],
        'd1_ema_slope3_atr':[0.3,-0.3], 'd1_macd_hist_atr':[0.05,-0.05],
        'h4_ema_slope3_atr':[-0.2,0.2], 'h4_macd_hist_atr':[-0.1,0.1],
        'return_atr':[1.0,1.0], 'decision_time':pd.to_datetime(['2025-01-01','2025-01-02'])
    })
    out=s.add_aligned_features(df)
    assert out.d1_dir_aligned.tolist()==[1.0,1.0]
    assert out.h4_dir_aligned.tolist()==[-1.0,-1.0]
    assert np.allclose(out.h1_rsi_center_aligned,[10.0,10.0])
    assert np.allclose(out.h1_macd_aligned,[0.2,0.2])


def test_path_class_r2_distinguishes_delayed_and_fade():
    delayed=pd.Series({'return_h8':-1.0,'return_h24':0.2,'return_h48':1.0})
    fade=pd.Series({'return_h8':1.0,'return_h24':0.2,'return_h48':-1.0})
    persistent=pd.Series({'return_h8':1.0,'return_h24':1.0,'return_h48':1.0})
    assert s.path_class(delayed,'R2')=='DELAYED'
    assert s.path_class(fade,'R2')=='FADE'
    assert s.path_class(persistent,'R2')=='PERSISTENT'


def test_model_features_exclude_forbidden_identity_fields():
    forbidden={'source_id','year','month','direction','return_atr','mfe_atr','mae_atr'}
    assert not forbidden.intersection(s.MODEL_FEATURES)


def test_cause_classifier_marks_small_recent_sample_insufficient():
    outcome=pd.DataFrame([{'regime':'R3','period':'LATEST60','direction':'LONG','n':6}])
    numdiag=pd.DataFrame(columns=['regime','period','direction','n','smd_win_minus_loss','feature'])
    model=pd.DataFrame(columns=['regime','direction','status','auc'])
    stable=pd.DataFrame(columns=['regime','direction','stable_entry_known_cause_feature'])
    out=s.cause_classification(outcome,numdiag,model,stable)
    row=out[(out.regime=='R3')&(out.direction=='LONG')].iloc[0]
    assert row.cause_classification=='INSUFFICIENT_SAMPLE'
