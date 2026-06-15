#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time,re
from datetime import datetime,timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_159_HIGH_PF_ADDON_PACKET_AUDIT_ONLY'
CUR='density_safe||100||Q0.6'
CUTOFF='2026-06-05 15:15:00'

def load(p): return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def readj(p):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def prog(out,d,t,label,t0):
    msg=f'[PROGRESS] config {d}/{t} {label} elapsed={time.time()-t0:.1f}s'; print(msg,flush=True); (out/'progress.txt').write_text(msg+'\n',encoding='utf-8')
def pf(s):
    x=pd.to_numeric(pd.Series(s),errors='coerce').dropna().astype(float)
    if x.empty: return 0.0
    gp=float(x[x>0].sum()); gl=float(-x[x<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def col(df,names):
    for n in names:
        if n in df.columns: return n
    return ''
def prep(df,pc,rc):
    x=df.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str); x['hour']=x.entry_dt.dt.hour
    x['hour_bucket']=x.hour.map(lambda h:'00_05' if h<6 else ('06_11' if h<12 else ('12_17' if h<18 else '18_23')))
    x['policy_norm']=x[pc].astype(str); x[rc]=pd.to_numeric(x[rc],errors='coerce').fillna(0)
    return x
def score_cols(df): return [c for c in ['feature_score','score','ledger_score','score_threshold'] if c in df.columns]
def dedup(df):
    if df.empty: return df.copy()
    x=df.copy(); sc=score_cols(x)
    for c in sc: x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.sort_values(['entry_dt']+sc,ascending=[True]+[False]*len(sc),kind='mergesort').groupby('entry_dt',as_index=False).head(1)
def met(df,rc):
    if df.empty: return {'events':0,'sum':0.0,'pf':0.0,'wr':0.0,'neg_events':0,'months':0,'neg_months':0,'june_events':0,'june_sum':0.0}
    r=pd.to_numeric(df[rc],errors='coerce').fillna(0); m=df.groupby('month')[rc].sum()
    return {'events':int(len(df)),'sum':float(r.sum()),'pf':pf(r),'wr':float((r>0).mean()),'neg_events':int((r<0).sum()),'months':int(len(m)),'neg_months':int((m<0).sum()),'june_events':int((df.month=='2026-06').sum()),'june_sum':float(m.get('2026-06',0.0))}
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'159'; out.mkdir(parents=True,exist_ok=True)
    sj=readj(root/'156'/'gold_v3_156_summary.json'); cur=str(sj.get('current_best_policy_key') or CUR)
    raw=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); blockers=[]
    pc=col(raw,['policy_key','k2_policy_key','rule_key','policy']); rc=col(raw,['worst_result_usd','result_usd','pnl_usd','profit_usd','rep_result_usd'])
    if raw.empty: blockers.append({'id':'missing_ledger'})
    if not pc: blockers.append({'id':'missing_policy_column'})
    if not rc: blockers.append({'id':'missing_result_column'})
    rows=[]; total=9; prog(out,0,total,'START',t0)
    if not blockers:
        x=prep(raw,pc,rc); cut=pd.Timestamp(CUTOFF); after=x[x.entry_dt>=cut].copy(); before=x[x.entry_dt<cut].copy(); ca=set(after[after.policy_norm.eq(cur)].entry_dt)
        specs=[]
        base_after=~after.policy_norm.eq(cur); base_before=~before.policy_norm.eq(cur)
        specs.append(('ANY_H1_UP_TRUE','ANY_NON_CURRENT + h1_up=True','BROAD_HIGH_PF',after.h1_up.astype(str).eq('True') if 'h1_up' in after else False,before.h1_up.astype(str).eq('True') if 'h1_up' in before else False))
        specs.append(('ANY_LONG','ANY_NON_CURRENT + side=LONG','BROAD_HIGH_PF',after.side.astype(str).eq('LONG') if 'side' in after else False,before.side.astype(str).eq('LONG') if 'side' in before else False))
        specs.append(('ANY_18_23','ANY_NON_CURRENT + hour_bucket=18_23','BROAD_HIGH_PF',after.hour_bucket.eq('18_23'),before.hour_bucket.eq('18_23')))
        specs.append(('DENSITY_Q035','density_safe||100||Q0.35 policy only','POLICY_ONLY',after.policy_norm.eq('density_safe||100||Q0.35'),before.policy_norm.eq('density_safe||100||Q0.35')))
        specs.append(('PRACTICAL_30_Q035','practical_quality||30||Q0.35 policy only','POLICY_ONLY',after.policy_norm.eq('practical_quality||30||Q0.35'),before.policy_norm.eq('practical_quality||30||Q0.35')))
        specs.append(('PRACTICAL_30_Q04','practical_quality||30||Q0.4 policy only','POLICY_ONLY',after.policy_norm.eq('practical_quality||30||Q0.4'),before.policy_norm.eq('practical_quality||30||Q0.4')))
        specs.append(('D1_DIST_LE_164','d1_dist_atr <= -1.641755654337','JUNE_FEATURE',pd.to_numeric(after.get('d1_dist_atr'),errors='coerce')<=-1.641755654337 if 'd1_dist_atr' in after else False,pd.to_numeric(before.get('d1_dist_atr'),errors='coerce')<=-1.641755654337 if 'd1_dist_atr' in before else False))
        specs.append(('H1_RANGE_LE_0737','h1_range_atr <= 0.737217834712','HIGH_PF_FEATURE',pd.to_numeric(after.get('h1_range_atr'),errors='coerce')<=0.737217834712 if 'h1_range_atr' in after else False,pd.to_numeric(before.get('h1_range_atr'),errors='coerce')<=0.737217834712 if 'h1_range_atr' in before else False))
        specs.append(('M15_RSI_GE_6693','m15_rsi14 >= 66.932872868553','HIGH_PF_FEATURE',pd.to_numeric(after.get('m15_rsi14'),errors='coerce')>=66.932872868553 if 'm15_rsi14' in after else False,pd.to_numeric(before.get('m15_rsi14'),errors='coerce')>=66.932872868553 if 'm15_rsi14' in before else False))
        for i,(lab,desc,kind,ma,mb) in enumerate(specs,1):
            prog(out,i,total,lab,t0); ma=base_after & ma; mb=base_before & mb; aa=dedup(after[ma]); bb=dedup(before[mb]); am=met(aa,rc); bm=met(bb,rc); bavg=bm['events']/max(1,bm['months']); spec=am['events']/(bavg+1)
            bucket='HIGH_PF_BROAD' if am['events']>=20 and am['pf']>=2 and bm['months']>=8 else ('JUNE_FEATURE' if spec>=1.25 and am['events']>=3 else ('THIN_HIGH_PF' if am['pf']>=3 and am['events']>=3 else 'REVIEW'))
            rows.append({'candidate':lab,'description':desc,'kind':kind,'review_bucket':bucket,'current_same_time_after':int(aa.entry_dt.isin(ca).sum()) if not aa.empty else 0,**{f'after_{k}':v for k,v in am.items()},**{f'before_{k}':v for k,v in bm.items()},'before_monthly_avg_events':bavg,'temporal_specificity':spec})
        rank=pd.DataFrame(rows); rank['rank_score']=rank.after_sum+rank.after_pf*75+rank.after_wr*50-rank.after_neg_events*8+rank.temporal_specificity*25
        rank=rank.sort_values(['review_bucket','rank_score'],ascending=[True,False]).reset_index(drop=True); save(rank,out/'gold_v3_159_high_pf_addon_packet.csv')
    else:
        rank=pd.DataFrame(); prog(out,1,total,'BLOCKED',t0)
    top=rank.head(1) if not rank.empty else pd.DataFrame(); status='READY' if not blockers else 'INPUT_MISSING'; decision='HIGH_PF_ADDON_PACKET_READY' if status=='READY' else 'HIGH_PF_ADDON_PACKET_INPUT_MISSING'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'current_best_policy_key':cur,'current_best_preserved':True,'important_correction':'High-PF addon candidates are reviewed without using current-best absence as a gate.','candidate_count':int(len(rank)) if not rank.empty else 0,'top_candidate':str(top.iloc[0].candidate) if not top.empty else '','top_bucket':str(top.iloc[0].review_bucket) if not top.empty else '','top_after_events':int(top.iloc[0].after_events) if not top.empty else 0,'top_after_sum':float(top.iloc[0].after_sum) if not top.empty else 0.0,'top_after_pf':float(top.iloc[0].after_pf) if not top.empty else 0.0,'progress_total_configs':total,'progress_completed_configs':total if not blockers else 0,'progress_output':str(out/'progress.txt'),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_159_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_159_decision.csv')
    lines=['GOLD V3 159 PASTE_ME_HIGH_PF_ADDON_PACKET_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','HIGH_PF_ADDON_PACKET',rank.to_string(index=False) if not rank.empty else 'NO_PACKET','','INTERPRETATION','These are high-PF addon review candidates. They are not limited to current-best absence. Broad candidates can be strong but may not be June-only. Audit-only; no final/live.','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
