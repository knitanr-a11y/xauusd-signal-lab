#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,time,glob
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_155_CANDIDATE_DECISION_PACKET_AUDIT_ONLY'

def load(p): return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def readj(p):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def prog(out,d,t,label,t0):
    msg=f'[PROGRESS] config {d}/{t} ({(d/t*100 if t else 100):.1f}%) {label} elapsed={time.time()-t0:.1f}s'
    print(msg,flush=True); (out/'progress.txt').write_text(msg+'\n',encoding='utf-8')
    (out/'progress.json').write_text(json.dumps({'done':d,'total':t,'label':label,'elapsed_seconds':round(time.time()-t0,1)},ensure_ascii=False,indent=2),encoding='utf-8')
def fnum(x,default=0.0):
    try:
        if pd.isna(x): return default
        return float(x)
    except Exception: return default
def inum(x,default=0):
    try:
        if pd.isna(x): return default
        return int(float(x))
    except Exception: return default
def first_existing(paths):
    for p in paths:
        if p.exists(): return p
    return None
def add_candidate(rows, label, category, source_stage, rule, events, chal, champ, pf, total, neg, june_events, june_sum, risk, status='REVIEW'):
    rows.append({
        'candidate_label':label,
        'category':category,
        'source_stage':source_stage,
        'rule_or_order':rule,
        'events':inum(events),
        'challenger_events':inum(chal),
        'champion_events':inum(champ),
        'worst_sum':fnum(total),
        'worst_pf':fnum(pf),
        'negative_months':inum(neg),
        'june_events':inum(june_events),
        'june_worst_sum':fnum(june_sum),
        'risk_note':risk,
        'status':status,
    })
def pick_row(df, col, value):
    if df.empty or col not in df.columns: return None
    z=df[df[col].astype(str)==str(value)]
    return z.iloc[0] if not z.empty else None
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'155'; out.mkdir(parents=True,exist_ok=True)
    prog(out,0,1,'START',t0)
    blockers=[]; rows=[]; notes=[]
    r154=load(root/'154'/'gold_v3_154_filter_order_ranking.csv')
    m154=load(root/'154'/'gold_v3_154_filter_order_monthly.csv')
    s154=readj(root/'154'/'gold_v3_154_summary.json')
    s153=readj(root/'153'/'gold_v3_153_summary.json')
    s148=readj(root/'148'/'gold_v3_148_summary.json')
    r148=load(root/'148'/'gold_v3_148_volume_review.csv')
    if r148.empty:
        cand=list((root/'148').glob('*volume*review*.csv'))+list((root/'148').glob('*ranking*.csv'))
        r148=load(cand[0]) if cand else pd.DataFrame()
    r147=pd.DataFrame()
    for p in list((root/'147').glob('*ranking*.csv'))+list((root/'147').glob('*hour*filter*.csv')):
        tmp=load(p)
        if 'rule_name' in tmp.columns and 'events' in tmp.columns:
            r147=tmp; break
    if r154.empty: blockers.append({'id':'missing_stage154_ranking','path':str(root/'154'/'gold_v3_154_filter_order_ranking.csv')})
    # Stage145 baseline from 154 ranking
    row=pick_row(r154,'rule_label','BASE_145_AFTER_SCORE_TRIM')
    if row is not None:
        add_candidate(rows,'BASE_145_AFTER_SCORE_TRIM','REFERENCE_BASE','154','NONE',row.events,row.challenger,row.champion,row.pf,row['sum'],row.neg_months,row.june_events,row.june_sum,'reference only; too many negative months','REFERENCE')
    # Count-oriented option from 147 if available: CHAMP_NOT_00_05
    row=pick_row(r147,'rule_name','CHAMP_NOT_00_05')
    if row is not None:
        add_candidate(rows,'A_COUNT_CHAMP_NOT_00_05','COUNT_ORIENTED','147','CHAMPION 00_05 removed only',row.events,row.get('challenger',None),row.get('champion',None),row.get('worst_pf',row.get('pf',0)),row.get('worst_sum',row.get('sum',0)),row.get('neg_months',row.get('negative_months',0)),row.get('june_events',0),row.get('june_worst',row.get('june_worst_sum',0)),'highest count option; residual negative months remain')
    else:
        notes.append('Stage147 CHAMP_NOT_00_05 row not found; count-oriented row may be absent.')
    # Hour-quality option from 154/148
    row=pick_row(r154,'rule_label','HOUR_FIRST')
    if row is not None:
        add_candidate(rows,'A2_HOUR_ONLY_QUALITY','COUNT_QUALITY_BRIDGE','154','CHAMP_NOT_00_05_AND_CHAL_NOT_06_11',row.events,row.challenger,row.champion,row.pf,row['sum'],row.neg_months,row.june_events,row.june_sum,'good frequency with June kept; negative months remain')
    # Balance option selected in 154
    row=pick_row(r154,'rule_label','HOUR_THEN_FEATURE_COMBO_NO_SCORE')
    if row is not None:
        add_candidate(rows,'B_BALANCED_HOUR_FEATURE','BALANCED','154','HOUR > FEATURE_COMBO; no score tail',row.events,row.challenger,row.champion,row.pf,row['sum'],row.neg_months,row.june_events,row.june_sum,'current best balance; two negative months remain')
    # PF option from 154/153
    row=pick_row(r154,'rule_label','HOUR_THEN_SCORE_THEN_FEATURE_COMBO')
    if row is not None:
        add_candidate(rows,'C_PF_HOUR_SCORE_FEATURE','PF_ORIENTED','154','HOUR > SCORE_TAIL > FEATURE_COMBO',row.events,row.challenger,row.champion,row.pf,row['sum'],row.neg_months,row.june_events,row.june_sum,'slightly higher PF, slightly fewer events; similar residual risk')
    # Rejected feature-first options prove ordering
    for lab in ['FEATURE_FIRST_COOLDOWN_ONLY','FEATURE_FIRST_COMBO']:
        row=pick_row(r154,'rule_label',lab)
        if row is not None:
            add_candidate(rows,lab,'ORDER_CHECK_REJECTED','154',row.order_sequence,row.events,row.challenger,row.champion,row.pf,row['sum'],row.neg_months,row.june_events,row.june_sum,'feature-first order underperformed; not a preferred path','REJECTED_ORDER')
    packet=pd.DataFrame(rows)
    if packet.empty: blockers.append({'id':'no_candidates_built'})
    if not packet.empty:
        # Decision labels: keep B as default when it exists and June >=4 and PF >2
        packet['score_for_human_review']=packet['worst_sum']+packet['worst_pf']*100-packet['negative_months']*250+packet['june_worst_sum']+packet['june_events']*5+packet['events']*0.1
        packet['suggested_use']='HOLD'
        packet.loc[packet['candidate_label'].eq('A_COUNT_CHAMP_NOT_00_05'),'suggested_use']='FREQUENCY_FALLBACK'
        packet.loc[packet['candidate_label'].eq('A2_HOUR_ONLY_QUALITY'),'suggested_use']='FREQUENCY_QUALITY_BRIDGE'
        packet.loc[packet['candidate_label'].eq('B_BALANCED_HOUR_FEATURE'),'suggested_use']='PRIMARY_HUMAN_REVIEW_CANDIDATE'
        packet.loc[packet['candidate_label'].eq('C_PF_HOUR_SCORE_FEATURE'),'suggested_use']='PF_PRIORITY_ALTERNATE'
        packet.loc[packet['status'].str.contains('REJECTED',na=False),'suggested_use']='DO_NOT_USE_AS_PRIMARY'
        packet=packet.sort_values(['suggested_use','score_for_human_review'],ascending=[True,False]).reset_index(drop=True)
    save(packet,out/'gold_v3_155_candidate_decision_packet.csv')
    # Add monthly rows for key B/C/A2 if available
    monthly_rows=[]
    if not m154.empty and 'rule_label' in m154.columns:
        for lab in ['HOUR_FIRST','HOUR_THEN_FEATURE_COMBO_NO_SCORE','HOUR_THEN_SCORE_THEN_FEATURE_COMBO']:
            z=m154[m154.rule_label.astype(str)==lab].copy()
            if not z.empty:
                z.insert(0,'candidate_label',{'HOUR_FIRST':'A2_HOUR_ONLY_QUALITY','HOUR_THEN_FEATURE_COMBO_NO_SCORE':'B_BALANCED_HOUR_FEATURE','HOUR_THEN_SCORE_THEN_FEATURE_COMBO':'C_PF_HOUR_SCORE_FEATURE'}[lab])
                monthly_rows.append(z)
    monthly=pd.concat(monthly_rows,ignore_index=True) if monthly_rows else pd.DataFrame()
    save(monthly,out/'gold_v3_155_candidate_monthly.csv')
    prog(out,1,1,'DONE',t0)
    primary=packet[packet.candidate_label.eq('B_BALANCED_HOUR_FEATURE')].head(1) if not packet.empty else pd.DataFrame()
    status='READY' if not blockers else 'INPUT_MISSING'
    decision='CANDIDATE_DECISION_PACKET_READY_PRIMARY_B_BALANCED' if not primary.empty and not blockers else ('CANDIDATE_DECISION_PACKET_READY_NO_PRIMARY' if not blockers else 'CANDIDATE_DECISION_PACKET_INPUT_MISSING')
    summary={
        'step':STEP,'status':status,'ready':not blockers,'decision':decision,
        'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
        'output_dir':str(out),'audit_only':True,'review_only':True,
        'primary_candidate':'B_BALANCED_HOUR_FEATURE' if not primary.empty else '',
        'primary_rule':'HOUR > FEATURE_COMBO; no score tail' if not primary.empty else '',
        'primary_events':int(primary.iloc[0].events) if not primary.empty else 0,
        'primary_challenger_events':int(primary.iloc[0].challenger_events) if not primary.empty else 0,
        'primary_worst_sum':float(primary.iloc[0].worst_sum) if not primary.empty else 0.0,
        'primary_worst_pf':float(primary.iloc[0].worst_pf) if not primary.empty else 0.0,
        'primary_negative_months':int(primary.iloc[0].negative_months) if not primary.empty else 0,
        'primary_june_events':int(primary.iloc[0].june_events) if not primary.empty else 0,
        'primary_june_worst_sum':float(primary.iloc[0].june_worst_sum) if not primary.empty else 0.0,
        'candidate_count':int(len(packet)) if not packet.empty else 0,
        'source_153_decision':s153.get('decision',''),'source_154_decision':s154.get('decision',''),
        'progress_total_configs':1,'progress_completed_configs':1 if not blockers else 0,'progress_output':str(out/'progress.txt'),
        'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,
        'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)
    }
    (out/'gold_v3_155_summary.json').write_text(json.dumps(summary|{'blockers':blockers,'notes':notes},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    save(pd.DataFrame([summary]),out/'gold_v3_155_decision.csv')
    lines=['GOLD V3 155 PASTE_ME_CANDIDATE_DECISION_PACKET_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]
    lines += ['','CANDIDATE_DECISION_PACKET',packet.to_string(index=False) if not packet.empty else 'NO_PACKET']
    lines += ['','CANDIDATE_MONTHLY',monthly.to_string(index=False) if not monthly.empty else 'NO_MONTHLY']
    lines += ['','HUMAN_DECISION_GUIDE',
        'A_COUNT / A2 = frequency-focused alternatives; keep June/event count but accept more negative months.',
        'B_BALANCED = current primary review candidate; keeps June 4 events and improves PF while not over-thinning as much as PF-only.',
        'C_PF = PF-priority alternate; slightly fewer events and similar residual monthly risk.',
        'Do not treat any candidate as final/live until a later final health gate and explicit approval.'
    ]
    lines += ['','NOTES', 'NO_NOTES' if not notes else '\n'.join(str(x) for x in notes)]
    lines += ['','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
