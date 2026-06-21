import importlib.util
import numpy as np
import pandas as pd

spec=importlib.util.spec_from_file_location('s','/mnt/data/stage270_regime_decay.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)


def test_psi_identical_is_zero_and_shift_is_material():
    a=np.arange(1000,dtype=float)
    assert abs(s.psi_numeric(a,a)) < 1e-9
    assert s.psi_numeric(a,a+500) > 0.25


def test_jsd_categorical_detects_direction_mix_change():
    a=['LONG']*100
    b=['LONG']*50+['SHORT']*50
    assert s.jsd_categorical(a,b) > 0.1


def test_matched_window_is_fixed_to_jan13_jun19():
    df=pd.DataFrame({'decision_time':pd.to_datetime(['2025-01-12 23:00','2025-01-13 00:00','2025-06-19 23:00','2025-06-20 00:00']), 'year':[2025]*4})
    out=s.get_period(df,2025,'MATCHED_CALENDAR_WINDOW')
    assert len(out)==2
    assert out.decision_time.min()==pd.Timestamp('2025-01-13 00:00')
    assert out.decision_time.max()==pd.Timestamp('2025-06-19 23:00')


def test_recency_classifier_marks_direction_collapse_as_weakened():
    p25={'median_return_atr':1.0,'positive_rate':0.65}
    p60={'n':50,'n_long':20,'n_short':30,'mean_return_atr':0.5,'median_return_atr':0.4,'mean_long':-0.2,'mean_short':1.0,'positive_rate':0.60}
    p30={'n':20,'mean_return_atr':0.3,'median_return_atr':0.2}
    status,reasons=s.classify_recency(p25,p60,p30)
    assert status=='WEAKENED_BUT_POSITIVE'
    assert 'one direction' in reasons
