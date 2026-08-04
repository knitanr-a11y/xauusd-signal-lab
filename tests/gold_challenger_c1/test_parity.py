import pandas as pd
from gold_challenger_c1.parity_audit import first_router_mismatch

def test_first_reference_mismatch_is_reported():
 ref=pd.DataFrame({'schedule':['SEMIANNUAL_EXPANDING'],'entry_time':[pd.Timestamp('2026-01-01')],'chosen_side':['LONG'],'chosen_rank':[.9],'rank_long':[.9],'rank_short':[.1]});rep=pd.DataFrame({'entry_time':[pd.Timestamp('2026-01-01')],'chosen_side':['SHORT'],'chosen_rank':[.8],'rank_long':[.2],'rank_short':[.8],'entry_idx':[1]});d={'H1':pd.DataFrame({'time':[pd.Timestamp('2025-12-31 23:00')]}),'H4':pd.DataFrame({'time':[pd.Timestamp('2025-12-31 20:00')]})};r=first_router_mismatch(ref,rep,[{'boundary':'2026-01-01','test_end':'2026-07-01'}],d);assert r['status']=='MISMATCH' and r['timestamp'].startswith('2026-01-01')
