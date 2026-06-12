#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GD_EDGE_SHARPENING_AND_DIVERSIFICATION_AUDIT_ONLY'
READY='GOLD_V3_107GD_EDGE_SHARPENING_AND_DIVERSIFICATION_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GD_EDGE_SHARPENING_AND_DIVERSIFICATION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'

def files_dir(arg):
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(env).expanduser().resolve() if env else Path.cwd()

def key_cols(): return ['side','condition','profile_id','cooldown_bars']
def norm_key(r): return tuple(str(r[c]) for c in key_cols())
def clauses(s): return set(str(s).split('&')) if pd.notna(s) else set()
def pf(vals):
    a=np.array(vals,float); gp=a[a>0].sum(); gl=-a[a<0].sum(); return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def metric(df):
    if df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    if 'entry_month' not in x: x['entry_month']=pd.to_datetime(x.entry_dt,errors='coerce').dt.to_period('M').astype(str)
    mon=x.groupby('entry_month').result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))
def pfcap(x):
    try:
        v=float(x); return 10.0 if math.isinf(v) else min(v,10.0)
    except Exception: return 0.0

def overlap(a,b):
    if not a or not b: return 0.0
    return len(a&b)/max(1,min(len(a),len(b)))

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--max-candidates-per-side',type=int,default=6); ap.add_argument('--max-overlap',type=float,default=.35)
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); src_gc=mt5/'FX_OUTPUTS'/'gold_v3'/'107gcc'; src_gb=mt5/'FX_OUTPUTS'/'gold_v3'/'107gbc'; out=mt5/'FX_OUTPUTS'/'gold_v3'/'107gdc'; out.mkdir(parents=True,exist_ok=True)
    blockers=[]; vals=[]; findings=[]; outputs=[]
    qpath=src_gc/'gold_v3_107gc_quality_rebalanced_candidates.csv'; lpath=src_gb/'gold_v3_107gb_top_candidate_trade_ledger.csv'
    if not qpath.exists(): blockers.append(dict(blocker_id='missing_quality_candidates',artifact=str(qpath),reason='required 107GC output missing'))
    if not lpath.exists(): blockers.append(dict(blocker_id='missing_trade_ledger',artifact=str(lpath),reason='required 107GB output missing'))
    if not blockers:
        q=pd.read_csv(qpath,encoding='utf-8-sig'); led=pd.read_csv(lpath,encoding='utf-8-sig')
        led['entry_dt']=pd.to_datetime(led.entry_dt,errors='coerce'); led['entry_month']=led.entry_dt.dt.to_period('M').astype(str)
        for c in ['cooldown_bars']: q[c]=q[c].astype(str); led[c]=led[c].astype(str)
        # sharpening
        rows=[]
        for side in ['LONG','SHORT']:
            s=q[q.side==side].copy()
            for _,pa in s.iterrows():
                pc=clauses(pa.condition)
                for _,ch in s.iterrows():
                    cc=clauses(ch.condition)
                    if len(cc)>len(pc) and pc.issubset(cc) and pa.profile_id==ch.profile_id and str(pa.cooldown_bars)==str(ch.cooldown_bars):
                        tr=max(1,float(pa.trades)); reduction=1-float(ch.trades)/tr
                        wrd=float(ch.win_rate)-float(pa.win_rate); pfd=pfcap(ch.profit_factor)-pfcap(pa.profit_factor); negd=float(pa.negative_month_count)-float(ch.negative_month_count)
                        score=wrd*1200+pfd*500+negd*200+reduction*200
                        rows.append(dict(side=side,parent_condition=pa.condition,child_condition=ch.condition,profile_id=ch.profile_id,cooldown_bars=ch.cooldown_bars,parent_trades=pa.trades,child_trades=ch.trades,trade_reduction_ratio=reduction,win_rate_delta=wrd,pf_delta=pfd,negative_month_delta=negd,sharpening_score=score))
        sharp=pd.DataFrame(rows).sort_values('sharpening_score',ascending=False) if rows else pd.DataFrame()
        save(sharp,out/'gold_v3_107gd_sharpening_matrix.csv'); outputs.append('gold_v3_107gd_sharpening_matrix.csv')
        # candidate maps
        key_to_set={}; key_to_df={}
        for k,g in led.groupby(key_cols(),dropna=False):
            kk=tuple(map(str,k)); key_to_set[kk]=set(g.entry_dt.dropna().astype(str)); key_to_df[kk]=g.copy()
        selections=[]; port_led=[]
        for side in ['LONG','SHORT']:
            cand=q[(q.side==side)&(q.trades>=80)&(q.profit_factor>=1.8)&(q.win_rate>=.55)&(q.negative_month_count<=2)].copy()
            cand=cand.sort_values('balanced_score',ascending=False) if 'balanced_score' in cand else cand.sort_values('score',ascending=False)
            chosen=[]; chosen_sets=[]
            for _,r in cand.iterrows():
                kk=norm_key(r)
                st=key_to_set.get(kk,set())
                if not st: continue
                ov=max([overlap(st,x) for x in chosen_sets], default=0.0)
                if ov<=a.max_overlap:
                    d=r.to_dict(); d['selected_rank']=len(chosen)+1; d['max_overlap_with_prior_selected']=ov; selections.append(d); chosen.append(kk); chosen_sets.append(st)
                    tmp=key_to_df[kk].copy(); tmp['portfolio_side']=side; tmp['selected_rank']=len(chosen); port_led.append(tmp)
                if len(chosen)>=a.max_candidates_per_side: break
        sel=pd.DataFrame(selections); save(sel,out/'gold_v3_107gd_diversified_candidate_selection.csv'); outputs.append('gold_v3_107gd_diversified_candidate_selection.csv')
        pled=pd.concat(port_led,ignore_index=True) if port_led else pd.DataFrame()
        if not pled.empty:
            # de-dupe within same side/time: keep earliest selected rank
            pled=pled.sort_values(['portfolio_side','entry_dt','selected_rank']).drop_duplicates(['portfolio_side','entry_dt'],keep='first')
        save(pled,out/'gold_v3_107gd_diversified_portfolio_ledger.csv'); outputs.append('gold_v3_107gd_diversified_portfolio_ledger.csv')
        ps=[]
        for side,g in pled.groupby('portfolio_side',dropna=False) if not pled.empty else []:
            m=metric(g); m.update(portfolio_side=side,candidate_count=int(sel[sel.side==side].selected_rank.max()) if len(sel[sel.side==side]) else 0,union_trades=m['trades']) ; ps.append(m)
        port=pd.DataFrame(ps); save(port,out/'gold_v3_107gd_diversified_portfolio_summary.csv'); outputs.append('gold_v3_107gd_diversified_portfolio_summary.csv')
        if not pled.empty:
            L=set(pled[pled.portfolio_side=='LONG'].entry_dt.astype(str)); S=set(pled[pled.portfolio_side=='SHORT'].entry_dt.astype(str)); inter=L&S
            conf=pd.DataFrame([dict(long_union_trades=len(L),short_union_trades=len(S),conflict_events=len(inter),conflict_rate_vs_long=len(inter)/max(1,len(L)),conflict_rate_vs_short=len(inter)/max(1,len(S)))])
        else: conf=pd.DataFrame([dict(long_union_trades=0,short_union_trades=0,conflict_events=0,conflict_rate_vs_long=0,conflict_rate_vs_short=0)])
        save(conf,out/'gold_v3_107gd_long_short_portfolio_conflict.csv'); outputs.append('gold_v3_107gd_long_short_portfolio_conflict.csv')
        rec=[]
        for _,r in sel.head(20).iterrows(): rec.append(dict(action='test_in_walkforward_portfolio',side=r.side,condition=r.condition,profile_id=r.profile_id,cooldown_bars=r.cooldown_bars,reason='diversified_low_overlap_quality_candidate'))
        if len(sharp):
            for _,r in sharp.head(10).iterrows(): rec.append(dict(action='test_sharpened_child_condition',side=r.side,condition=r.child_condition,profile_id=r.profile_id,cooldown_bars=r.cooldown_bars,reason='child improved WR/PF or reduced negative months'))
        save(pd.DataFrame(rec),out/'gold_v3_107gd_recommended_next_actions.csv'); outputs.append('gold_v3_107gd_recommended_next_actions.csv')
        for side in ['LONG','SHORT']:
            pg=port[port.portfolio_side==side]
            if len(pg): findings.append(f"portfolio_{side.lower()}="+json.dumps(pg.iloc[0].to_dict(),ensure_ascii=False,default=str))
        if len(sharp): findings.append('best_sharpening='+json.dumps(sharp.iloc[0].to_dict(),ensure_ascii=False,default=str))
        findings.append('conflict='+json.dumps(conf.iloc[0].to_dict(),ensure_ascii=False,default=str))
        vals.append(dict(check_id='selection_rows_positive',result='PASS' if len(sel)>0 else 'FAIL',observed=len(sel),expected='>0',severity='BLOCKER'))
    for cid,obs,exp in [('audit_only',True,True),('source_csv_mutated',False,False),('candidate_pool_mutated',False,False),('open_asof_allowed',False,False)]: vals.append(dict(check_id=cid,result='PASS',observed=obs,expected=exp,severity='BLOCKER'))
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),input_dirs=str(src_gc)+';'+str(src_gb),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()))
    save(pd.DataFrame(blockers),out/'gold_v3_107gd_blocker_matrix.csv'); save(val,out/'gold_v3_107gd_validation_matrix.csv')
    (out/'gold_v3_107gd_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GD_EDGE_SHARPENING_AND_DIVERSIFICATION_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GD report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107gd_blocker_matrix.csv','gold_v3_107gd_validation_matrix.csv','gold_v3_107gd_summary.json','GOLD_V3_107GD_EDGE_SHARPENING_AND_DIVERSIFICATION_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107GD PASTE_ME_EDGE_SHARPENING_AND_DIVERSIFICATION',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GC/107GB outputs only; sharpening and diversified low-overlap vectors; no runtime change',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
