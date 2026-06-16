#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_166_PRIORITY_REPAIR_PACKET_AUDIT_ONLY'
CUR='density_safe||100||Q0.6'
CUTOFF='2026-06-05 15:15:00'

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
def metric(df,rc):
    if df.empty: return dict(events=0,sum=0.0,pf=0.0,wr=0.0,neg=0,months=0,neg_months=0,june_events=0,june_sum=0.0,min_entry_dt='',max_entry_dt='')
    r=pd.to_numeric(df[rc],errors='coerce').fillna(0); m=df.groupby('month')[rc].sum()
    return dict(events=int(len(df)),sum=float(r.sum()),pf=pf(r),wr=float((r>0).mean()),neg=int((r<0).sum()),months=int(len(m)),neg_months=int((m<0).sum()),june_events=int((df.month=='2026-06').sum()),june_sum=float(m.get('2026-06',0.0)),min_entry_dt=str(df.entry_dt.min()),max_entry_dt=str(df.entry_dt.max()))
def pref(d,p): return {p+k:v for k,v in d.items()}
def col(df,names):
    for n in names:
        if n in df.columns: return n
    return ''
def score_cols(df): return [c for c in ['feature_score','score','ledger_score','score_threshold'] if c in df.columns]
def one_entry(df,rc):
    if df.empty: return df.copy()
    x=df.copy(); sc=score_cols(x)
    for c in sc: x[c]=pd.to_numeric(x[c],errors='coerce')
    if sc: return x.sort_values(['entry_dt']+sc,ascending=[True]+[False]*len(sc),kind='mergesort').groupby('entry_dt',as_index=False).head(1)
    return x.sort_values(['entry_dt'],kind='mergesort').groupby('entry_dt',as_index=False).head(1)
def add_candidate(rows,events,x,rc,priority,label,desc,mask):
    raw=x[mask].copy(); oe=one_entry(raw,rc); oe=oe.copy(); oe.insert(0,'priority',priority); oe.insert(1,'candidate',label); oe.insert(2,'candidate_desc',desc)
    rec={'priority':priority,'candidate':label,'candidate_desc':desc,'raw_rows':int(len(raw)),'raw_unique_entry_dt':int(raw.entry_dt.nunique())}
    cut=pd.Timestamp(CUTOFF)
    rec.update(pref(metric(oe,rc),'one_full_')); rec.update(pref(metric(oe[oe.entry_dt>=cut],rc),'one_after_')); rec.update(pref(metric(oe[oe.entry_dt<cut],rc),'one_before_'))
    rec['adoption_note']='one entry per entry_dt; no stacking; priority packet candidate'
    rows.append(rec); events.append(oe)
def priority_union(event_frames,rc):
    if not event_frames: return pd.DataFrame()
    allx=pd.concat(event_frames,ignore_index=True)
    allx=allx.sort_values(['entry_dt','priority'],ascending=[True,True],kind='mergesort')
    return allx.groupby('entry_dt',as_index=False).head(1).copy()
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'166'; out.mkdir(parents=True,exist_ok=True)
    s165=readj(root/'165'/'gold_v3_165_summary.json')
    raw=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); blockers=[]; pc=col(raw,['policy_key','k2_policy_key','rule_key','policy']); rc=col(raw,['result_usd','worst_result_usd','pnl_usd','profit_usd','rep_result_usd'])
    if raw.empty: blockers.append({'id':'missing_ledger'})
    if not pc: blockers.append({'id':'missing_policy_column'})
    if not rc: blockers.append({'id':'missing_result_column'})
    rows=[]; events=[]
    if not blockers:
        x=raw.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str); x['policy_norm']=x[pc].astype(str); x[rc]=pd.to_numeric(x[rc],errors='coerce').fillna(0); x['hour']=x.entry_dt.dt.hour; x['hour_bucket']=x.hour.map(lambda h:'00_05' if h<6 else ('06_11' if h<12 else ('12_17' if h<18 else '18_23')))
        base=~x.policy_norm.eq(CUR)
        def num(c): return pd.to_numeric(x[c],errors='coerce') if c in x.columns else pd.Series(False,index=x.index)
        # revised priority: M15 RSI candidate is promoted above H1_RANGE/ANY_H1.
        add_candidate(rows,events,x,rc,1,'D1_DIST_LE_164_NO_PRUNE','D1_DIST_LE_164 no prune',base & (num('d1_dist_atr')<=-1.641755654337))
        add_candidate(rows,events,x,rc,2,'DENSITY_Q035_D1_LE_078','density_safe Q0.35 + d1_dist_atr <= -0.781481',x.policy_norm.eq('density_safe||100||Q0.35') & (num('d1_dist_atr')<=-0.781481))
        add_candidate(rows,events,x,rc,3,'M15_RSI_GE_6693_HIGH_Q09','M15_RSI_GE_6693 promoted: m15_rsi14 >= 73.861004',base & (num('m15_rsi14')>=66.932872868553) & (num('m15_rsi14')>=73.861004))
        # P4/P5 repaired: choose tighter options from Stage165 with fewer negative months / fewer events.
        add_candidate(rows,events,x,rc,4,'H1_RANGE_REPAIR_D1_LE_NEG017','H1_RANGE_LE_0737 + d1_dist_atr <= -0.170649',base & (num('h1_range_atr')<=0.737217834712) & (num('d1_dist_atr')<=-0.170649))
        add_candidate(rows,events,x,rc,5,'ANY_H1_UP_REPAIR_D1_H1_COMBO','ANY_H1_UP_TRUE + d1_dist_atr <= 1.247038 + h1_range_atr <= 0.744978',base & x.get('h1_up',pd.Series(False,index=x.index)).astype(str).eq('True') & (num('d1_dist_atr')<=1.247038) & (num('h1_range_atr')<=0.744978))
        packet=pd.DataFrame(rows).sort_values('priority').reset_index(drop=True); save(packet,out/'gold_v3_166_priority_candidate_packet.csv')
        union=priority_union(events,rc); save(union,out/'gold_v3_166_priority_union_events.csv')
        um=union.groupby('month')[rc].agg(['count','sum']).reset_index() if not union.empty else pd.DataFrame(); save(um,out/'gold_v3_166_priority_union_monthly.csv')
    else:
        packet=pd.DataFrame(); union=pd.DataFrame(); um=pd.DataFrame()
    cut=pd.Timestamp(CUTOFF)
    union_full=metric(union,rc) if not union.empty else metric(pd.DataFrame(),rc); union_after=metric(union[union.entry_dt>=cut],rc) if not union.empty else metric(pd.DataFrame(),rc); union_before=metric(union[union.entry_dt<cut],rc) if not union.empty else metric(pd.DataFrame(),rc)
    status='READY' if not blockers else 'INPUT_MISSING'; decision='PRIORITY_REPAIR_PACKET_READY' if status=='READY' else 'PRIORITY_REPAIR_PACKET_INPUT_MISSING'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'evaluation_contract':'later candidates only; one entry per entry_dt; priority-dedup union; no stacking','priority_change':'M15_RSI_GE_6693 promoted from old priority 5 to new priority 3; H1_RANGE and ANY_H1 kept but repaired/tightened','union_full_events':union_full['events'],'union_full_sum':union_full['sum'],'union_full_pf':union_full['pf'],'union_full_neg_months':union_full['neg_months'],'union_after_events':union_after['events'],'union_after_sum':union_after['sum'],'union_after_pf':union_after['pf'],'union_before_events':union_before['events'],'union_before_sum':union_before['sum'],'union_before_pf':union_before['pf'],'candidate_count':int(len(packet)) if not packet.empty else 0,'source_165_decision':s165.get('decision',''),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_166_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_166_decision.csv')
    lines=['GOLD V3 166 PASTE_ME_PRIORITY_REPAIR_PACKET_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','PRIORITY_CANDIDATE_PACKET',packet.to_string(index=False) if not packet.empty else 'NO_PACKET','','PRIORITY_UNION_MONTHLY',um.to_string(index=False) if not um.empty else 'NO_MONTHLY','','INTERPRETATION','Priority 3 and 4 from the previous packet are repaired/tightened, and previous priority 5 is promoted to priority 3. Union is priority-deduped by entry_dt and still one-entry-per-timestamp. Audit-only; no final/live.','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
