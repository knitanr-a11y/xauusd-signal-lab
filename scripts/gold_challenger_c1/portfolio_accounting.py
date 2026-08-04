from __future__ import annotations
import numpy as np
import pandas as pd
from .contracts import FIXED_SPREAD

def summarize_pnl(values)->dict:
    p=np.asarray(values,float);p=p[np.isfinite(p)];gp=p[p>0].sum();gl=-p[p<0].sum();eq=np.cumsum(p);peak=np.maximum.accumulate(np.r_[0.0,eq])[:-1] if len(p) else np.array([]);dd=float(np.max(peak-eq)) if len(p) else np.nan
    return {'trades':int(len(p)),'wins':int((p>0).sum()),'losses':int((p<0).sum()),'win_rate':float((p>0).mean()) if len(p) else np.nan,'gross_profit':float(gp),'gross_loss':float(gl),'pf':float(gp/gl) if gl>0 else (float('inf') if gp>0 else np.nan),'net':float(p.sum()),'ev':float(p.mean()) if len(p) else np.nan,'max_dd':dd}

def _preempt_pnl(row,preempt_idx,m1):
    e=float(m1.open.iloc[int(row.entry_idx)]);x=float(m1.open.iloc[int(preempt_idx)])
    return x-(e+FIXED_SPREAD) if row.chosen_side=='LONG' else e-(x+FIXED_SPREAD)

def simulate_v19_priority(challenger:pd.DataFrame,v19:pd.DataFrame,m1:pd.DataFrame,preempt:bool=True):
    c=challenger.sort_values(['entry_idx','candidate_id']).reset_index(drop=True);v=v19.sort_values(['entry_idx','origin_id']).reset_index(drop=True)
    events=[]
    for i,r in v.iterrows(): events.append((int(r.entry_idx),0,'V19',i))
    for i,r in c.iterrows(): events.append((int(r.entry_idx),1,'CHALLENGER',i))
    events.sort()
    active=None;accepted_c=[];supp=[];accepted_v=[]
    for idx,prio,system,pos in events:
        # release a naturally closed position before a later timestamp; same-index remains busy.
        if active is not None and idx>int(active['exit_idx']): active=None
        if system=='V19':
            r=v.iloc[pos]
            if active is not None and active['system']=='CHALLENGER':
                if preempt:
                    cr=active['row'].copy();cr['resolved_exit_idx']=idx;cr['resolved_exit_dt']=pd.Timestamp(m1.time.iloc[idx]);cr['resolved_pnl']=_preempt_pnl(cr,idx,m1);cr['exit_reason']='V19_PREEMPT';accepted_c.append(cr);active=None
                else:
                    supp.append({'system':'V19','origin_id':int(r.origin_id),'entry_idx':idx,'reason':'CHALLENGER_OPEN_NO_PREEMPT_COUNTERFACTUAL'});continue
            if active is not None:
                # Frozen V19 input should already be non-overlapping; fail closed otherwise.
                raise RuntimeError('V19_INTERNAL_OVERLAP')
            vr=r.copy();vr['resolved_exit_idx']=int(r.natural_exit_idx);vr['resolved_exit_dt']=r.natural_exit_dt;vr['resolved_pnl']=float(r.natural_pnl);vr['exit_reason']='V19_NATURAL';accepted_v.append(vr);active={'system':'V19','exit_idx':int(r.natural_exit_idx),'row':r}
        else:
            r=c.iloc[pos]
            if active is not None:
                supp.append({'system':'CHALLENGER','candidate_id':int(r.candidate_id),'entry_idx':idx,'reason':active['system']+'_OPEN'});continue
            active={'system':'CHALLENGER','exit_idx':int(r.natural_exit_idx),'row':r}
    if active is not None and active['system']=='CHALLENGER':
        cr=active['row'].copy();cr['resolved_exit_idx']=int(cr.natural_exit_idx);cr['resolved_exit_dt']=cr.natural_exit_dt;cr['resolved_pnl']=float(cr.natural_pnl);cr['exit_reason']='NATURAL';accepted_c.append(cr)
    # Candidate positions that ended naturally before later events were not appended at release; reconstruct accepted IDs and natural exits.
    accepted_ids={int(r.candidate_id) for r in accepted_c}
    suppressed_ids={int(r['candidate_id']) for r in supp if r['system']=='CHALLENGER'}
    for r in c.itertuples(index=False):
        cid=int(r.candidate_id)
        if cid not in accepted_ids and cid not in suppressed_ids:
            z=pd.Series(r._asdict());z['resolved_exit_idx']=int(r.natural_exit_idx);z['resolved_exit_dt']=r.natural_exit_dt;z['resolved_pnl']=float(r.natural_pnl);z['exit_reason']='NATURAL';accepted_c.append(z);accepted_ids.add(cid)
    cc=pd.DataFrame(accepted_c).sort_values('entry_idx').reset_index(drop=True) if accepted_c else pd.DataFrame()
    vv=pd.DataFrame(accepted_v).sort_values('entry_idx').reset_index(drop=True) if accepted_v else pd.DataFrame()
    if len(cc):cc['system']='CHALLENGER'
    if len(vv):vv['system']='V19'
    comb=pd.concat([vv,cc],ignore_index=True,sort=False).sort_values(['resolved_exit_idx','entry_idx']).reset_index(drop=True)
    return cc,vv,comb,pd.DataFrame(supp)

def monthly_correlation(v19,challenger):
    def m(df):
        if df.empty:return pd.Series(dtype=float)
        return df.assign(month=pd.to_datetime(df.resolved_exit_dt).dt.to_period('M').astype(str)).groupby('month').resolved_pnl.sum()
    a=m(v19);b=m(challenger);z=pd.concat([a.rename('v19'),b.rename('challenger')],axis=1).fillna(0)
    return float(z.corr().iloc[0,1]) if len(z)>1 and z.v19.std()>0 and z.challenger.std()>0 else np.nan,z.reset_index()
