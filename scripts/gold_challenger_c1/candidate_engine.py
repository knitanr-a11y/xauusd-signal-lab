from __future__ import annotations
import numpy as np
import pandas as pd
from .contracts import ALLOWED_ENTRY_COLUMNS,FORBIDDEN_ENTRY_EXACT,TARGET_STATES,RANK_CEILING

def _forbidden(name:str)->bool:
    return name in FORBIDDEN_ENTRY_EXACT or name.startswith('future_') or name.startswith('next_')

def build_candidates(entry_input: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    extra=set(entry_input.columns)-set(ALLOWED_ENTRY_COLUMNS)
    if extra: raise ValueError(f'ENTRY_INPUT_NOT_WHITELISTED: {sorted(extra)}')
    if any(_forbidden(c) for c in entry_input.columns): raise ValueError('OUTCOME_COLUMN_IN_ENTRY_INPUT')
    missing=set(ALLOWED_ENTRY_COLUMNS)-set(entry_input.columns)
    if missing: raise ValueError(f'MISSING_ENTRY_COLUMNS: {sorted(missing)}')
    x=entry_input.sort_values(['decision_dt','origin_id']).reset_index(drop=True).copy()
    gap=x.decision_dt.diff().dt.total_seconds()/60
    eligible=x.chosen_rank.lt(RANK_CEILING)&x.wave_state.isin(TARGET_STATES)
    zone=np.where(eligible,'SUBP90_'+x.wave_state.astype(str),'OTHER')
    side_change=x.chosen_side.ne(x.chosen_side.shift());zone_change=pd.Series(zone).ne(pd.Series(zone).shift())
    boundary=gap.ne(15.0)|side_change|zone_change
    x['episode_id']=boundary.cumsum().astype(int)
    x['previous_decision_dt']=x.decision_dt.shift()
    x['eligible']=eligible
    x['causal_zone']=zone
    x['event_onset']=gap.eq(15.0)&(side_change|zone_change)&eligible
    candidates=x[x.event_onset].copy().reset_index(drop=True)
    candidates['candidate_id']=np.arange(len(candidates),dtype=int)
    return candidates,x
