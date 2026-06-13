#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GO_ATOMIC_VECTOR_PORTFOLIO_AND_SHORT_GAP_DIAGNOSIS_AUDIT_ONLY'
READY='GOLD_V3_107GO_ATOMIC_VECTOR_PORTFOLIO_AND_SHORT_GAP_DIAGNOSIS_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GO_ATOMIC_VECTOR_PORTFOLIO_AND_SHORT_GAP_DIAGNOSIS_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'

def files_dir(arg):
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(env).expanduser().resolve() if env else Path.cwd()

def save(df,p):
    p.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(p,index=False,encoding='utf-8-sig')

def pf(vals):
    a=np.array(vals,float); gp=a[a>0].sum(); gl=-a[a<0].sum()
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)

def metric(df):
    if df is None or df.empty:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    if 'entry_month' not in x:
        x['entry_month']=pd.to_datetime(x.entry_dt,errors='coerce').dt.to_period('M').astype(str)
    mon=x.groupby('entry_month').result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))

def pfcap(v):
    try:
        x=float(v); return 10.0 if math.isinf(x) else min(max(x,0.0),10.0)
    except Exception:
        return 0.0

def score(m):
    return pfcap(m.get('profit_factor',0))*1000 + float(m.get('win_rate',0))*900 + min(float(m.get('trades',0)),300)*0.30 + float(m.get('sum_result_usd',0))*0.04 - float(m.get('negative_month_count',0))*350

def overlap(a,b):
    return len(a&b)/max(1,min(len(a),len(b))) if a and b else 0.0

def build_key_df(df):
    x=df.copy()
    for c in ['side','family','condition','profile_id']:
        x[c]=x[c].astype(str)
    x['cooldown_bars']=pd.to_numeric(x['cooldown_bars'],errors='coerce').fillna(0).astype(int)
    x['candidate_key']=x.apply(lambda r:f"{r.side}||{r.family}||{r.condition}||{r.profile_id}||CD{int(r.cooldown_bars)}",axis=1)
    return x

def qgate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--max-candidates-per-side',type=int,default=8); ap.add_argument('--max-overlap',type=float,default=0.35)
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); src=mt5/'FX_OUTPUTS'/'gold_v3'/'107gnc'; out=mt5/'FX_OUTPUTS'/'gold_v3'/'107goc'; out.mkdir(parents=True,exist_ok=True)
    req={'candidate_summary':src/'gold_v3_107gn_candidate_summary.csv','top_ledger':src/'gold_v3_107gn_top_candidate_trade_ledger.csv'}
    blockers=[]; vals=[]; findings=[]; outputs=[]
    for k,p in req.items():
        if not p.exists(): blockers.append(dict(blocker_id='missing_'+k,artifact=str(p),reason='required Stage107GN output missing'))
    if not blockers:
        cand=build_key_df(pd.read_csv(req['candidate_summary'],encoding='utf-8-sig'))
        led=pd.read_csv(req['top_ledger'],encoding='utf-8-sig')
        led['entry_dt']=pd.to_datetime(led.entry_dt,errors='coerce'); led=led[led.entry_dt.notna()].copy(); led['entry_month']=led.entry_dt.dt.to_period('M').astype(str)
        led['result_usd']=pd.to_numeric(led.result_usd,errors='coerce'); led=led[led.result_usd.notna()].copy()
        if 'candidate_key' not in led.columns:
            led=build_key_df(led)
        metrics=[]; sets={}
        for key,g in led.groupby('candidate_key'):
            m=metric(g); first=g.iloc[0]
            m.update(candidate_key=key,side=str(first.side),family=str(first.family),condition=str(first.condition),profile_id=str(first.profile_id),cooldown_bars=int(first.cooldown_bars))
            m['ledger_score']=score(m); sets[key]=set(g.entry_dt.astype(str)); metrics.append(m)
        met=pd.DataFrame(metrics).sort_values(['side','ledger_score'],ascending=[True,False])
        save(met,out/'gold_v3_107go_candidate_ledger_metrics.csv'); outputs.append('gold_v3_107go_candidate_ledger_metrics.csv')
        selections=[]; portfolio_parts=[]
        for side in ['LONG','SHORT']:
            s=met[met.side==side].copy()
            if side=='LONG':
                s=s[(s.trades>=10)&(s.profit_factor>=1.8)&(s.win_rate>=0.55)].copy()
            else:
                s=s[(s.trades>=20)&(s.profit_factor>=1.35)&(s.win_rate>=0.40)].copy()
            s=s.sort_values('ledger_score',ascending=False)
            chosen=[]; chosen_sets=[]
            for _,r in s.iterrows():
                st=sets.get(r.candidate_key,set())
                ov=max([overlap(st,z) for z in chosen_sets],default=0.0)
                if ov<=a.max_overlap:
                    rr=r.to_dict(); rr['selected_rank']=len(chosen)+1; rr['max_overlap_with_selected']=ov; selections.append(rr); chosen.append(r.candidate_key); chosen_sets.append(st)
                    portfolio_parts.append(led[led.candidate_key==r.candidate_key].assign(selected_rank=len(chosen),portfolio_side=side,ledger_score=float(r.ledger_score)))
                if len(chosen)>=a.max_candidates_per_side: break
        sel=pd.DataFrame(selections)
        save(sel,out/'gold_v3_107go_diversified_selection.csv'); outputs.append('gold_v3_107go_diversified_selection.csv')
        if portfolio_parts:
            port=pd.concat(portfolio_parts,ignore_index=True).sort_values(['portfolio_side','entry_dt','ledger_score'],ascending=[True,True,False])
            port=port.drop_duplicates(['portfolio_side','entry_dt'],keep='first')
        else:
            port=pd.DataFrame()
        save(port,out/'gold_v3_107go_portfolio_ledger.csv'); outputs.append('gold_v3_107go_portfolio_ledger.csv')
        side_rows=[]
        for side,g in port.groupby('portfolio_side') if not port.empty else []:
            m=metric(g); m.update(side=side,candidate_count=int(sel[sel.side==side].candidate_key.nunique()) if not sel.empty else 0); side_rows.append(m)
        side_df=pd.DataFrame(side_rows)
        save(side_df,out/'gold_v3_107go_side_portfolio_summary.csv'); outputs.append('gold_v3_107go_side_portfolio_summary.csv')
        # Combined conflict diagnostic only.
        conf=[]
        if not port.empty and 'LONG' in set(port.portfolio_side) and 'SHORT' in set(port.portfolio_side):
            raw=port.sort_values(['entry_dt','ledger_score'],ascending=[True,False])
            conflict_rows=int(raw.duplicated('entry_dt',keep=False).sum())
            resolved=raw.drop_duplicates('entry_dt',keep='first')
            rm=metric(resolved); rm.update(conflict_rows_before_resolution=conflict_rows,combined_trades_after_resolution=len(resolved)); conf.append(rm)
        else:
            conf.append(dict(conflict_rows_before_resolution=0,combined_trades_after_resolution=len(port)))
        conf_df=pd.DataFrame(conf)
        save(conf_df,out/'gold_v3_107go_combined_conflict_summary.csv'); outputs.append('gold_v3_107go_combined_conflict_summary.csv')
        # side gap decision
        gap=[]
        for side in ['LONG','SHORT']:
            r=side_df[side_df.side==side] if len(side_df) and 'side' in side_df.columns else pd.DataFrame()
            if r.empty:
                gap.append(dict(side=side,portfolio_available=False,decision='NO_PORTFOLIO_AVAILABLE_REDESIGN_REQUIRED'))
                continue
            row=r.iloc[0]
            if side=='LONG': ok=bool(row.trades>=100 and row.profit_factor>=2.0 and row.win_rate>=0.55 and row.negative_month_count<=2)
            else: ok=bool(row.trades>=100 and row.profit_factor>=1.8 and row.win_rate>=0.50 and row.negative_month_count<=2)
            decision='PORTFOLIO_PROMISING_RUN_ANCHORED_TEST' if ok else ('QUALITY_OK_BUT_TOO_FEW_TRADES' if row.profit_factor>=2.0 and row.win_rate>=0.55 else 'REDESIGN_REQUIRED')
            gap.append(dict(side=side,portfolio_available=True,trades=int(row.trades),win_rate=float(row.win_rate),profit_factor=float(row.profit_factor),sum_result_usd=float(row.sum_result_usd),negative_month_count=int(row.negative_month_count),candidate_count=int(row.candidate_count),passes_practical_gate=ok,decision=decision))
        gap_df=pd.DataFrame(gap)
        save(gap_df,out/'gold_v3_107go_side_gap_decision.csv'); outputs.append('gold_v3_107go_side_gap_decision.csv')
        long_ok=bool(gap_df[(gap_df.side=='LONG')&(gap_df.get('passes_practical_gate',False)==True)].shape[0]) if len(gap_df) else False
        short_ok=bool(gap_df[(gap_df.side=='SHORT')&(gap_df.get('passes_practical_gate',False)==True)].shape[0]) if len(gap_df) else False
        gates=pd.DataFrame([qgate('long_atomic_portfolio_practical',1 if long_ok else 0,'>=',1),qgate('short_atomic_portfolio_practical',1 if short_ok else 0,'>=',1),qgate('portfolio_ledger_positive',len(port),'>=',1)])
        save(gates,out/'gold_v3_107go_quality_gate_matrix.csv'); outputs.append('gold_v3_107go_quality_gate_matrix.csv')
        actions=[]
        if long_ok or short_ok:
            actions.append(dict(priority=1,action='run_anchored_train_test_on_atomic_portfolio',reason=f'long_ok={long_ok}, short_ok={short_ok}'))
        if not long_ok:
            actions.append(dict(priority=2,action='redesign_long_density_or_union_logic',reason='LONG atomic seeds remain too sparse or fail practical portfolio gate.'))
        if not short_ok:
            actions.append(dict(priority=3,action='redesign_short_feature_family',reason='SHORT atomic seeds remain weak; likely need different features/regime/TP design.'))
        save(pd.DataFrame(actions),out/'gold_v3_107go_recommended_next_actions.csv'); outputs.append('gold_v3_107go_recommended_next_actions.csv')
        findings.append('side_portfolio_summary='+json.dumps(side_df.to_dict(orient='records'),ensure_ascii=False,default=str))
        findings.append('side_gap_decision='+json.dumps(gap_df.to_dict(orient='records'),ensure_ascii=False,default=str))
        findings.append('quality_gates='+json.dumps(gates.result.value_counts().to_dict(),ensure_ascii=False,default=str))
        vals.append(dict(check_id='candidate_metrics_positive',result='PASS' if len(met)>0 else 'FAIL',observed=len(met),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='candidate_pool_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),input_dir=str(src),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='light_seconds_to_minutes_stop_if_over_1h')
    if not blockers:
        summary.update(candidate_metric_rows=int(len(met)),selection_rows=int(len(sel)),portfolio_rows=int(len(port)),long_portfolio_ok=long_ok,short_portfolio_ok=short_ok)
    save(pd.DataFrame(blockers),out/'gold_v3_107go_blocker_matrix.csv'); save(val,out/'gold_v3_107go_validation_matrix.csv')
    outputs += ['gold_v3_107go_blocker_matrix.csv','gold_v3_107go_validation_matrix.csv','gold_v3_107go_summary.json','GOLD_V3_107GO_ATOMIC_VECTOR_PORTFOLIO_AND_SHORT_GAP_DIAGNOSIS_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107go_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GO_ATOMIC_VECTOR_PORTFOLIO_AND_SHORT_GAP_DIAGNOSIS_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GO report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107GO PASTE_ME_ATOMIC_VECTOR_PORTFOLIO_AND_SHORT_GAP_DIAGNOSIS',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GN candidate summary and top ledger only; no M5 re-evaluation; no runtime change','runtime_estimate: light; seconds_to_minutes; stop_if_over_1h',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
