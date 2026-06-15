#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_163_CURRENT_BEST_STACK_CAP_AUDIT_ONLY'
CUR='density_safe||100||Q0.6'

def load(p): return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def readj(p):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def pf(s):
    x=pd.to_numeric(pd.Series(s),errors='coerce').dropna().astype(float)
    if x.empty: return 0.0
    gp=float(x[x>0].sum()); gl=float(-x[x<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def col(df,names):
    for n in names:
        if n in df.columns: return n
    return ''
def metric(vals):
    x=pd.to_numeric(pd.Series(vals),errors='coerce').fillna(0)
    return dict(count=int(len(x)),sum=float(x.sum()),pf=pf(x),wr=float((x>0).mean()) if len(x) else 0.0,neg=int((x<0).sum()))
def score_cols(df): return [c for c in ['feature_score','score','ledger_score','score_threshold'] if c in df.columns]
def select_group(g,cap,selector,rc):
    x=g.copy()
    if selector=='SCORE_DESC':
        sc=score_cols(x)
        for c in sc: x[c]=pd.to_numeric(x[c],errors='coerce')
        x=x.sort_values(sc,ascending=[False]*len(sc),kind='mergesort') if sc else x
    elif selector=='RESULT_DEBUG_BEST':
        x=x.sort_values(rc,ascending=False,kind='mergesort')
    if cap!='ALL': x=x.head(int(cap))
    return x
def run_mode(c,cap,selector,side_mode,rc):
    row_vals=[]; stack_vals=[]; split_vals=[]; used=[]; skipped=0; mixed=0
    for dt,g in c.groupby('entry_dt',sort=True):
        if 'side' in g.columns and g.side.nunique(dropna=True)>1:
            mixed+=1
            if side_mode=='DROP_MIXED':
                skipped+=1; continue
            if side_mode=='MAJORITY_SIDE':
                major=g.side.astype(str).value_counts().idxmax(); g=g[g.side.astype(str)==major]
        s=select_group(g,cap,selector,rc)
        if s.empty: continue
        vals=pd.to_numeric(s[rc],errors='coerce').fillna(0)
        row_vals.extend(vals.tolist()); stack_vals.append(float(vals.sum())); split_vals.append(float(vals.mean()))
        used.append({'entry_dt':dt,'rows_selected':int(len(s)),'row_sum':float(vals.sum()),'row_mean':float(vals.mean()),'side_values':';'.join(s.side.astype(str).unique()[:5]) if 'side' in s.columns else ''})
    rm=metric(row_vals); sm=metric(stack_vals); fm=metric(split_vals)
    return {**{f'row_{k}':v for k,v in rm.items()},**{f'stack_{k}':v for k,v in sm.items()},**{f'split_total_lot_{k}':v for k,v in fm.items()},'entry_dt_used':len(stack_vals),'mixed_side_seen':mixed,'mixed_side_skipped':skipped},pd.DataFrame(used)
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'163'; out.mkdir(parents=True,exist_ok=True)
    s162=readj(root/'162'/'gold_v3_162_summary.json'); cur=str(s162.get('current_best_policy_key') or CUR)
    raw=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); blockers=[]
    pc=col(raw,['policy_key','k2_policy_key','rule_key','policy']); rc=col(raw,['result_usd','worst_result_usd','pnl_usd','profit_usd','rep_result_usd'])
    if raw.empty: blockers.append({'id':'missing_ledger'})
    if not pc: blockers.append({'id':'missing_policy_column'})
    if not rc: blockers.append({'id':'missing_result_column'})
    rows=[]; examples=[]; total=0
    if not blockers:
        x=raw.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str); x['policy_norm']=x[pc].astype(str); x[rc]=pd.to_numeric(x[rc],errors='coerce').fillna(0)
        c=x[x.policy_norm.eq(cur)].copy(); caps=[1,3,5,8,10,'ALL']; selectors=['FILE_ORDER','SCORE_DESC']; side_modes=['DROP_MIXED','MAJORITY_SIDE']
        total=len(caps)*len(selectors)*len(side_modes); done=0
        for cap in caps:
            for selector in selectors:
                for side_mode in side_modes:
                    done+=1; print(f'[PROGRESS] config {done}/{total} cap={cap} selector={selector} side={side_mode}',flush=True)
                    rec,ev=run_mode(c,cap,selector,side_mode,rc); rec.update({'cap':cap,'selector':selector,'side_mode':side_mode}); rows.append(rec)
                    if cap==10 and selector=='SCORE_DESC' and side_mode=='DROP_MIXED': examples.append(ev.head(200))
        rank=pd.DataFrame(rows)
        rank['risk_multiplier_max']=rank['cap'].map(lambda v: 999 if v=='ALL' else int(v))
        rank=rank.sort_values(['cap','selector','side_mode']).reset_index(drop=True)
        save(rank,out/'gold_v3_163_current_best_stack_cap_metrics.csv')
        if examples: save(pd.concat(examples,ignore_index=True),out/'gold_v3_163_cap10_score_desc_examples.csv')
    else:
        rank=pd.DataFrame()
    target=rank[(rank.cap.astype(str)=='10')&(rank.selector.eq('SCORE_DESC'))&(rank.side_mode.eq('DROP_MIXED'))].head(1) if not rank.empty else pd.DataFrame()
    status='READY' if not blockers else 'INPUT_MISSING'; decision='STACK_CAP_AUDIT_READY' if status=='READY' else 'STACK_CAP_AUDIT_INPUT_MISSING'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'current_best_policy_key':cur,'recommended_review_cap':10,'target_selector':'SCORE_DESC','target_side_mode':'DROP_MIXED','target_stack_pf':float(target.iloc[0].stack_pf) if not target.empty else 0.0,'target_stack_sum':float(target.iloc[0].stack_sum) if not target.empty else 0.0,'target_entry_dt_used':int(target.iloc[0].entry_dt_used) if not target.empty else 0,'target_split_total_lot_pf':float(target.iloc[0].split_total_lot_pf) if not target.empty else 0.0,'candidate_count':int(len(rank)) if not rank.empty else 0,'source_162_interpretation':s162.get('interpretation',''),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_163_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_163_decision.csv')
    lines=['GOLD V3 163 PASTE_ME_CURRENT_BEST_STACK_CAP_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','STACK_CAP_METRICS',rank.to_string(index=False) if not rank.empty else 'NO_METRICS','','INTERPRETATION','Compares old current best stacking caps. stack_* assumes each selected row is a separate order unit. split_total_lot_* assumes total risk is fixed and split across selected rows. Mixed-side entry times are either dropped or reduced to majority side. Audit-only; no final/live.','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
