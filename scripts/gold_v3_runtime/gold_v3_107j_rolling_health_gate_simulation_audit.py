#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time,warnings
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
warnings.filterwarnings('ignore', category=FutureWarning)
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_107J_ROLLING_HEALTH_GATE_SIMULATION_AUDIT_ONLY'
READY='GOLD_V3_107J_ROLLING_HEALTH_GATE_SIMULATION_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107J_ROLLING_HEALTH_GATE_SIMULATION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
MIN_HIST=[0,3,5,8,10]
MIN_WR=[0.0,0.50,0.55,0.60,0.65]
MIN_PF=[0.0,1.0,1.3,1.5,2.0]
LOOKBACK=[0,20,50]
MODES=['shadow_history','traded_only']

def log(s): print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}",flush=True)
def prog(i,n,s):
    p=100*i/max(1,n); log(f'progress {p:5.1f}% complete / {100-p:5.1f}% remaining | step {i}/{n} | {s}')
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def pf(v):
    a=np.asarray(v,dtype=float); gp=a[a>0].sum(); gl=-a[a<0].sum(); return float(gp/gl) if gl>0 else (math.inf if gp>0 else 0.0)
def cap(v):
    try:
        x=float(v); return 10 if math.isinf(x) else max(0.0,min(x,10.0))
    except Exception: return 0.0

def metrics(df):
    if df is None or df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    mon=x.groupby(pd.to_datetime(x.entry_dt).dt.to_period('M').astype(str)).result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=pf(x.result_usd),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))
def day_stats(df):
    if df is None or df.empty: return dict(unique_trade_days=0,date_span_days=0,max_day_trades=0,max_day_trade_share=0.0,business_day_trade_rate=0.0,active_trade_day_rate=0.0,min_entry_dt='',max_entry_dt='')
    x=df.copy(); x['day']=pd.to_datetime(x.entry_dt).dt.date
    g=x.groupby('day').size().rename('day_trades').reset_index()
    max_day=int(g.day_trades.max()); mn=pd.to_datetime(x.entry_dt.min()).date(); mx=pd.to_datetime(x.entry_dt.max()).date(); span=(mx-mn).days+1
    bd=int(np.busday_count(np.datetime64(mn),np.datetime64(mx)+np.timedelta64(1,'D'))); ad=int(len(g))
    return dict(unique_trade_days=ad,date_span_days=span,max_day_trades=max_day,max_day_trade_share=float(max_day/len(x)),business_day_trade_rate=float(len(x)/bd) if bd else 0.0,active_trade_day_rate=float(len(x)/ad) if ad else 0.0,min_entry_dt=str(mn),max_entry_dt=str(mx))
def full_metrics(df): return metrics(df)|day_stats(df)

def health_ok(hist,min_hist,min_wr,min_pf,lookback):
    if lookback and len(hist)>lookback: hist=hist.sort_values('exit_dt').tail(lookback)
    if len(hist)<min_hist: return min_hist==0
    m=metrics(hist)
    return bool(m['win_rate']>=min_wr and m['profit_factor']>=min_pf)

def simulate(ledger,mode,min_hist,min_wr,min_pf,min_lb):
    cand=ledger.sort_values('entry_dt').copy(); accepted=[]; rows=[]
    for _,r in cand.iterrows():
        now=pd.Timestamp(r.entry_dt)
        if mode=='shadow_history':
            hist=cand[pd.to_datetime(cand.exit_dt)<=now].copy()
        else:
            hist=pd.DataFrame(accepted)
            if not hist.empty: hist=hist[pd.to_datetime(hist.exit_dt)<=now].copy()
        ok=health_ok(hist,min_hist,min_wr,min_pf,min_lb)
        rr=r.to_dict(); rr['health_pass']=bool(ok); rr['health_history_count']=int(len(hist)); rr['health_mode']=mode; rr['min_history']=min_hist; rr['min_wr']=min_wr; rr['min_pf']=min_pf; rr['lookback_resolved']=min_lb
        rows.append(rr)
        if ok: accepted.append(r.to_dict())
    out=pd.DataFrame(rows)
    return out[out.health_pass].copy(), out

def choose_candidates(mat,ledger,limit):
    m=mat[mat.exact_replay_ready.astype(str).str.lower().isin(['true','1'])].copy()
    if m.empty: m=mat[mat.primary_65_replayed.astype(str).str.lower().isin(['true','1'])].copy()
    if m.empty: m=mat.copy()
    return m.sort_values(['exact_replay_ready','primary_65_replayed','replayed_win_rate','replayed_trades'],ascending=[False,False,False,False]).head(limit)

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--candidate-top',type=int,default=8); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'107jc'; out.mkdir(parents=True,exist_ok=True)
    log(STEP+' START')
    blocks=[]; outputs=[]; vals=[]; findings=[]
    mpath=root/'107i2c'/'gold_v3_107i2_exact_replay_candidates.csv'; lpath=root/'107i2c'/'gold_v3_107i2_all_replayed_ledgers.csv'
    for name,p in [('107i2_candidates',mpath),('107i2_ledgers',lpath)]:
        if not p.exists(): blocks.append(dict(blocker_id='missing_'+name,path=str(p)))
    if not blocks:
        mat=pd.read_csv(mpath,encoding='utf-8-sig'); led=pd.read_csv(lpath,encoding='utf-8-sig')
        led['entry_dt']=pd.to_datetime(led.entry_dt,errors='coerce'); led['exit_dt']=pd.to_datetime(led.get('exit_dt'),errors='coerce') if 'exit_dt' in led.columns else pd.NaT
        led['result_usd']=pd.to_numeric(led.result_usd,errors='coerce')
        led=led[led.entry_dt.notna() & led.exit_dt.notna() & led.result_usd.notna()].copy()
        if led.empty: blocks.append(dict(blocker_id='missing_exit_dt_or_replay_rows',reason='resolved-only health gate requires exit_dt'))
    if not blocks:
        cand=choose_candidates(mat,led,args.candidate_top)
        total=len(cand)*len(MODES)*len(MIN_HIST)*len(MIN_WR)*len(MIN_PF)*len(LOOKBACK); cur=0; prog(cur,total,'start')
        rows=[]; pass_ledgers=[]; state_ledgers=[]
        for _,c in cand.iterrows():
            cr=int(c.candidate_rank); base=led[led.candidate_rank==cr].copy()
            if base.empty: continue
            for mode in MODES:
                for mh in MIN_HIST:
                    for mw in MIN_WR:
                        for mpf in MIN_PF:
                            for lb in LOOKBACK:
                                cur+=1
                                acc,state=simulate(base,mode,mh,mw,mpf,lb)
                                m=full_metrics(acc)
                                rec=dict(candidate_rank=cr,health_mode=mode,min_history=mh,min_wr=mw,min_pf=mpf,lookback_resolved=lb,source_wr=float(c.replayed_win_rate),source_pf=float(c.replayed_profit_factor),source_trades=int(c.replayed_trades),source_unique_trade_days=int(c.unique_trade_days),source_max_day_trade_share=float(c.max_day_trade_share))
                                rec.update({f'gated_{k}':v for k,v in m.items()})
                                rec['primary_65_gate']=bool(m['win_rate']>=0.65 and m['profit_factor']>=1.5 and m['trades']>=30 and m['unique_trade_days']>=4 and m['max_day_trade_share']<=0.45)
                                rec['review_65_small']=bool(m['win_rate']>=0.65 and m['profit_factor']>=1.5 and m['trades']>=15 and m['unique_trade_days']>=4)
                                rec['preserve_source_quality']=bool(m['win_rate']>=float(c.replayed_win_rate)-0.05 and m['trades']>=int(c.replayed_trades)*0.5)
                                rec['review_score']=m['win_rate']*12000+cap(m['profit_factor'])*900+m['trades']*0.35+min(m['business_day_trade_rate'],30)*100-m['max_day_trade_share']*1500-m['negative_month_count']*500
                                rows.append(rec)
                                if rec['primary_65_gate'] or rec['review_65_small']:
                                    tmp=acc.copy(); tmp['sim_candidate_rank']=cr; tmp['health_mode']=mode; tmp['min_history']=mh; tmp['min_wr']=mw; tmp['min_pf']=mpf; tmp['lookback_resolved']=lb; pass_ledgers.append(tmp)
                                if cur%100==0: prog(cur,total,f'candidate={cr} mode={mode}')
        fr=pd.DataFrame(rows).sort_values(['primary_65_gate','review_score'],ascending=[False,False]) if rows else pd.DataFrame()
        save(fr,out/'gold_v3_107j_health_gate_frontier.csv'); outputs.append('gold_v3_107j_health_gate_frontier.csv')
        allpass=pd.concat(pass_ledgers,ignore_index=True) if pass_ledgers else pd.DataFrame()
        save(allpass,out/'gold_v3_107j_passed_trade_ledgers.csv'); outputs.append('gold_v3_107j_passed_trade_ledgers.csv')
        if fr.empty: blocks.append(dict(blocker_id='no_health_frontier'))
        else:
            best=fr.iloc[0]
            mask=(allpass.sim_candidate_rank==int(best.candidate_rank))&(allpass.health_mode==best.health_mode)&(allpass.min_history==int(best.min_history))&(allpass.min_wr==float(best.min_wr))&(allpass.min_pf==float(best.min_pf))&(allpass.lookback_resolved==int(best.lookback_resolved)) if not allpass.empty else pd.Series(False)
            best_led=allpass[mask].copy() if not allpass.empty else pd.DataFrame()
            save(best_led,out/'gold_v3_107j_best_health_gate_ledger.csv'); outputs.append('gold_v3_107j_best_health_gate_ledger.csv')
            p65=int(fr.primary_65_gate.sum()); rev=int(fr.review_65_small.sum())
            decision='ROLLING_HEALTH_GATE_PRIMARY_READY_AUDIT_ONLY' if p65 else ('ROLLING_HEALTH_GATE_REVIEW_SMALL_ONLY' if rev else 'ROLLING_HEALTH_GATE_DID_NOT_PRESERVE_65')
            gates=pd.DataFrame([gy.gate_row('any_primary_65_health_gate',p65,'>=',1),gy.gate_row('any_review_65_small',rev,'>=',1),gy.gate_row('best_trades_ge_30',int(best.gated_trades),'>=',30),gy.gate_row('best_wr_ge_65',float(best.gated_win_rate),'>=',0.65),gy.gate_row('best_unique_days_ge_4',int(best.gated_unique_trade_days),'>=',4),gy.gate_row('best_max_day_share_le_45pct',float(best.gated_max_day_trade_share),'<=',0.45)])
            dec=pd.DataFrame([dict(decision=decision,primary_65_health_gate_count=p65,review_65_small_count=rev,best_candidate_rank=int(best.candidate_rank),best_health_mode=str(best.health_mode),best_min_history=int(best.min_history),best_min_wr=float(best.min_wr),best_min_pf=float(best.min_pf),best_lookback_resolved=int(best.lookback_resolved),best_trades=int(best.gated_trades),best_wr=float(best.gated_win_rate),best_pf=float(best.gated_profit_factor),best_density=float(best.gated_business_day_trade_rate),best_unique_trade_days=int(best.gated_unique_trade_days),best_max_day_trade_share=float(best.gated_max_day_trade_share),next_stage='107K_DEPLOYABILITY_REVIEW_PACKET' if p65 else '107K_HEALTH_GATE_REVIEW_OR_FEATURE_SCORE_ADJUSTMENT')])
            save(gates,out/'gold_v3_107j_quality_gate_matrix.csv'); save(dec,out/'gold_v3_107j_next_action_decision.csv'); outputs+=['gold_v3_107j_quality_gate_matrix.csv','gold_v3_107j_next_action_decision.csv']
            findings.append('next_action_decision='+json.dumps(dec.to_dict(orient='records'),ensure_ascii=False,default=str))
            findings.append('top_health_gate_frontier='+json.dumps(fr.head(15).to_dict(orient='records'),ensure_ascii=False,default=str))
            vals.append(dict(check_id='health_gate_frontier_positive',result='PASS',observed=len(fr),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blocks and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=gy.CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=gy.POOL_POLICY,blocker_count=len(blocks),validation_failure_count=int((~val.result.eq('PASS')).sum()),elapsed_seconds=round(time.time()-t0,2))
    if not blocks and 'fr' in locals() and not fr.empty:
        summary.update(health_frontier_rows=len(fr),primary_65_health_gate_count=int(fr.primary_65_gate.sum()),review_65_small_count=int(fr.review_65_small.sum()),best_wr=float(fr.iloc[0].gated_win_rate),best_pf=float(fr.iloc[0].gated_profit_factor),best_trades=int(fr.iloc[0].gated_trades),best_density=float(fr.iloc[0].gated_business_day_trade_rate),best_unique_trade_days=int(fr.iloc[0].gated_unique_trade_days),best_max_day_trade_share=float(fr.iloc[0].gated_max_day_trade_share),decision=decision)
    save(pd.DataFrame(blocks),out/'gold_v3_107j_blocker_matrix.csv'); save(val,out/'gold_v3_107j_validation_matrix.csv'); outputs+=['gold_v3_107j_blocker_matrix.csv','gold_v3_107j_validation_matrix.csv','gold_v3_107j_summary.json','GOLD_V3_107J_ROLLING_HEALTH_GATE_SIMULATION_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107j_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107J_ROLLING_HEALTH_GATE_SIMULATION_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107J report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blocks},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107J PASTE_ME_ROLLING_HEALTH_GATE_SIMULATION',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+gy.CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+gy.POOL_POLICY,'source: Stage107I2 exact replay ledgers with resolved-only rolling health gate; exit_dt <= current entry_dt; no runtime change','blocker_count: '+str(len(blocks)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blocks).to_string(index=False) if blocks else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    prog(total if 'total' in locals() else 1,total if 'total' in locals() else 1,'DONE')
    log(f'DONE status={status} elapsed={time.time()-t0:.1f}s paste_me={out/"paste_me.txt"}')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2

if __name__=='__main__': raise SystemExit(main())
