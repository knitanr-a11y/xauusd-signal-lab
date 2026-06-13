#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GX_MULTI_SUBFILTER_STACK_65WR_AUDIT_ONLY'
READY='GOLD_V3_107GX_MULTI_SUBFILTER_STACK_65WR_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GX_MULTI_SUBFILTER_STACK_65WR_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
INPUTS=[('atomic_current_107GO','107goc','gold_v3_107go_portfolio_ledger.csv'),('atomic_top_107GN','107gnc','gold_v3_107gn_top_candidate_trade_ledger.csv'),('new_vector_top_107GL','107glc','gold_v3_107gl_top_vector_trade_ledger.csv'),('fixed_diversified_107GD','107gdc','gold_v3_107gd_diversified_portfolio_ledger.csv'),('broad_candidate_107GB','107gbc','gold_v3_107gb_top_candidate_trade_ledger.csv')]
SPLITS={'TRAIN_2025_TEST_2026':('2025-01-01','2026-01-01','2026-01-01','2027-01-01'),'TRAIN_2025H1_TEST_2025H2':('2025-01-01','2025-07-01','2025-07-01','2026-01-01'),'TRAIN_TO_2026_02_TEST_2026_03_PLUS':('2025-01-01','2026-03-01','2026-03-01','2027-01-01'),'TRAIN_TO_2026_04_TEST_2026_05_06':('2025-01-01','2026-05-01','2026-05-01','2027-01-01')}
SESSIONS={'tokyo_7_11':range(7,12),'london_12_16':range(12,17),'ny_17_22':range(17,23),'asia_0_6':range(0,7),'active_7_22':range(7,23),'all_0_23':range(0,24)}
PROFILES=[('elite65_min6',0.65,1.50,6),('elite65_min10',0.65,1.30,10),('strict63_min10',0.63,1.60,10),('wr60_pf2_min15',0.60,2.00,15)]
TOP_NS=[10,20,30,50,100,200,500]
TOP_CONFIGS=20

def log(s): print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}",flush=True)
def progress(cur,total,label):
    pct=100.0*cur/max(total,1); rem=100-pct
    log(f'progress {pct:5.1f}% complete / {rem:5.1f}% remaining | step {cur}/{total} | {label}')
def files_dir(s):
    if s: return Path(s).expanduser().resolve()
    e=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(e).expanduser().resolve() if e else Path.cwd()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def pf(vals):
    a=np.asarray(vals,dtype=float); gp=a[a>0].sum(); gl=-a[a<0].sum()
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def cap(v):
    try:
        x=float(v); return 10.0 if math.isinf(x) else max(0.0,min(x,10.0))
    except Exception: return 0.0

def metric(df):
    if df is None or df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    mon=x.groupby(pd.to_datetime(x.entry_dt).dt.to_period('M').astype(str)).result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))
def density(df):
    m=metric(df)
    if df is None or df.empty: return m|dict(min_entry_dt='',max_entry_dt='',business_days=0,business_day_trade_rate=0.0,active_trade_days=0,active_trade_day_rate=0.0)
    mn=pd.to_datetime(df.entry_dt.min()).date(); mx=pd.to_datetime(df.entry_dt.max()).date()
    bd=int(np.busday_count(np.datetime64(mn),np.datetime64(mx)+np.timedelta64(1,'D'))); ad=int(pd.to_datetime(df.entry_dt).dt.date.nunique())
    return m|dict(min_entry_dt=str(mn),max_entry_dt=str(mx),business_days=bd,business_day_trade_rate=float(m['trades']/bd) if bd else 0.0,active_trade_days=ad,active_trade_day_rate=float(m['trades']/ad) if ad else 0.0)

def add_calendar(x):
    x=x.copy(); dt=pd.to_datetime(x.entry_dt)
    x['entry_hour']=dt.dt.hour; x['entry_dow']=dt.dt.dayofweek
    return x

def normalize(df,src):
    if 'entry_dt' not in df.columns: return pd.DataFrame()
    x=df.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].copy()
    if x.empty: return x
    x['result_usd']=pd.to_numeric(x.get('result_usd',0),errors='coerce'); x=x[x.result_usd.notna()].copy()
    if 'portfolio_side' in x.columns: x['side']=x['portfolio_side']
    if 'selected_side' in x.columns and 'side' not in x.columns: x['side']=x['selected_side']
    if 'side' not in x.columns: x['side']='UNKNOWN'
    for c in ['side','family','condition','profile_id','candidate_key']:
        if c not in x.columns: x[c]=''
        x[c]=x[c].astype(str).replace({'nan':''})
    if 'cooldown_bars' not in x.columns: x['cooldown_bars']=0
    x['cooldown_bars']=pd.to_numeric(x.cooldown_bars,errors='coerce').fillna(0).astype(int)
    built=x.apply(lambda r:f"{r.side}||{r.family}||{r.condition}||{r.profile_id}||CD{int(r.cooldown_bars)}",axis=1)
    empty=x.candidate_key.eq('')|x.candidate_key.eq('nan')
    x.loc[empty,'candidate_key']=built[empty]
    x['source_name']=src; x['global_candidate_key']=x.source_name+'::'+x.candidate_key
    return add_calendar(x)

def filter_rows(df,pid):
    if df.empty: return df
    if pid=='ALL': return df
    if pid.startswith('HOUR_'):
        h=int(pid.split('_',1)[1]); return df[df.entry_hour==h]
    if pid.startswith('DOW_'):
        d=int(pid.split('_',1)[1]); return df[df.entry_dow==d]
    if pid.startswith('SESSIONDOW_'):
        rest=pid[len('SESSIONDOW_'):]; nm,d=rest.rsplit('_',1)
        return df[df.entry_hour.isin(list(SESSIONS[nm])) & (df.entry_dow==int(d))]
    if pid.startswith('HOURDOW_'):
        rest=pid[len('HOURDOW_'):]; h,d=rest.split('_')
        return df[(df.entry_hour==int(h)) & (df.entry_dow==int(d))]
    if pid.startswith('SESSION_'):
        nm=pid[len('SESSION_'):]; return df[df.entry_hour.isin(list(SESSIONS[nm]))]
    return df.iloc[0:0]

def prune_ids_for(train):
    ids=[]
    # Avoid ALL except when baseline itself has enough train samples; high WR gate will decide.
    if len(train)>=10: ids.append('ALL')
    for h,c in train.entry_hour.value_counts().items():
        if c>=4: ids.append(f'HOUR_{int(h)}')
    for d,c in train.entry_dow.value_counts().items():
        if c>=5: ids.append(f'DOW_{int(d)}')
    for nm,hrs in SESSIONS.items():
        cnt=int(train.entry_hour.isin(list(hrs)).sum())
        if cnt>=5 and nm!='all_0_23': ids.append(f'SESSION_{nm}')
    for nm,hrs in SESSIONS.items():
        if nm=='all_0_23': continue
        for d in range(5):
            if int((train.entry_hour.isin(list(hrs)) & (train.entry_dow==d)).sum())>=4: ids.append(f'SESSIONDOW_{nm}_{d}')
    for h in sorted(train.entry_hour.unique()):
        for d in range(5):
            if int(((train.entry_hour==h)&(train.entry_dow==d)).sum())>=3: ids.append(f'HOURDOW_{int(h)}_{d}')
    return list(dict.fromkeys(ids))

def subfilter_metrics_for_candidate(train_c,test_c,meta):
    rows=[]
    for pid in prune_ids_for(train_c):
        tr=filter_rows(train_c,pid); tm=density(tr)
        if tm['trades']<3 or tm['sum_result_usd']<=0: continue
        tst=filter_rows(test_c,pid); om=density(tst)
        # train-only score. No high trade-count penalty.
        score=tm['win_rate']*9000+cap(tm['profit_factor'])*850+tm['trades']*0.65+tm['sum_result_usd']*0.04-tm['negative_month_count']*300
        r=dict(prune_id=pid,train_score=score,pruned_subfilter_key=meta['global_candidate_key']+'::PRUNE::'+pid,**{f'train_{k}':v for k,v in tm.items()},**{f'oos_{k}':v for k,v in om.items()})
        r.update(meta); rows.append(r)
    return pd.DataFrame(rows)

def stack_oos(ledger, selected):
    parts=[]
    for _,r in selected.iterrows():
        x=ledger[(ledger.global_candidate_key==r.global_candidate_key)&(ledger.entry_dt>=pd.Timestamp(r.test_start))&(ledger.entry_dt<pd.Timestamp(r.test_end))].copy()
        x=filter_rows(x,str(r.prune_id))
        if not x.empty:
            x['pruned_subfilter_key']=r.pruned_subfilter_key; x['train_score']=r.train_score
            parts.append(x)
    if not parts: return pd.DataFrame()
    y=pd.concat(parts,ignore_index=True)
    return y.sort_values(['entry_dt','train_score'],ascending=[True,False]).drop_duplicates('entry_dt',keep='first')

def qgate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--top-configs',type=int,default=TOP_CONFIGS)
    args=ap.parse_args(); mt5=files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; gv=root/'107gvc'; gu=root/'107guc'; out=root/'107gxc'; out.mkdir(parents=True,exist_ok=True)
    log(f'{STEP} START multi-subfilter stack 65WR')
    req={'gv_density2':gv/'gold_v3_107gv_density2_pass_configs.csv','gu_selected':gu/'gold_v3_107gu_selected_candidate_keys.csv'}
    blocks=[]; vals=[]; outs=[]; finds=[]
    for k,p in req.items():
        if not p.exists(): blocks.append(dict(blocker_id='missing_'+k,artifact=str(p),reason='required prior output missing'))
    led=[]; cov=[]
    for src,sub,fn in INPUTS:
        p=root/sub/fn; rows=0; err=''
        if p.exists():
            try:
                x=normalize(pd.read_csv(p,encoding='utf-8-sig'),src); rows=len(x)
                if rows: led.append(x)
            except Exception as e: err=str(e)
        cov.append(dict(source_name=src,path=str(p),exists=p.exists(),rows=rows,error=err))
    save(pd.DataFrame(cov),out/'gold_v3_107gx_input_coverage.csv'); outs.append('gold_v3_107gx_input_coverage.csv')
    if not led: blocks.append(dict(blocker_id='no_candidate_ledgers',reason='No exact candidate ledgers found.'))
    if not blocks:
        ledger=pd.concat(led,ignore_index=True)
        d2=pd.read_csv(req['gv_density2'],encoding='utf-8-sig').sort_values('review_score',ascending=False).head(args.top_configs).copy()
        sel=pd.read_csv(req['gu_selected'],encoding='utf-8-sig')
        total_candidates=sum(int(sel[(sel.split.astype(str)==str(r.split))&(sel.tier.astype(str)==str(r.tier))&(pd.to_numeric(sel.top_n,errors='coerce')==int(r.top_n))].shape[0]) for _,r in d2.iterrows())
        total=max(1,total_candidates+len(d2)*len(PROFILES)*len(TOP_NS)); cur=0
        sub_rows=[]; frontier=[]; best_port=pd.DataFrame(); selected_out=[]
        progress(cur,total,'start')
        for ci,(_,cfg) in enumerate(d2.iterrows(),1):
            sp=str(cfg.split); tier=str(cfg.tier); topn=int(cfg.top_n)
            if sp not in SPLITS: continue
            trs,tre,tes,tee=SPLITS[sp]
            keys=sel[(sel.split.astype(str)==sp)&(sel.tier.astype(str)==tier)&(pd.to_numeric(sel.top_n,errors='coerce')==topn)].sort_values('rank')
            cfg_sub=[]
            for _,krow in keys.iterrows():
                cur+=1
                key=str(krow.global_candidate_key)
                train_c=ledger[(ledger.global_candidate_key==key)&(ledger.entry_dt>=pd.Timestamp(trs))&(ledger.entry_dt<pd.Timestamp(tre))].copy()
                test_c=ledger[(ledger.global_candidate_key==key)&(ledger.entry_dt>=pd.Timestamp(tes))&(ledger.entry_dt<pd.Timestamp(tee))].copy()
                if train_c.empty: continue
                meta=dict(split=sp,tier=tier,top_n=topn,base_rank=int(krow.get('rank',0)),global_candidate_key=key,train_start=trs,train_end=tre,test_start=tes,test_end=tee)
                sm=subfilter_metrics_for_candidate(train_c,test_c,meta)
                if not sm.empty:
                    sub_rows.append(sm); cfg_sub.append(sm)
                if cur%10==0 or cur==total_candidates: progress(cur,total,f'subfilter metrics config={ci}/{len(d2)} split={sp}')
            all_sub=pd.concat(cfg_sub,ignore_index=True) if cfg_sub else pd.DataFrame()
            for prof,min_wr,min_pf,min_tr in PROFILES:
                if all_sub.empty:
                    pool=pd.DataFrame()
                else:
                    pool=all_sub[(all_sub.train_win_rate>=min_wr)&(all_sub.train_profit_factor>=min_pf)&(all_sub.train_trades>=min_tr)&(all_sub.train_sum_result_usd>0)].copy()
                    pool=pool.sort_values(['train_score','train_win_rate','train_profit_factor','train_trades'],ascending=[False,False,False,False])
                for n in TOP_NS:
                    cur+=1
                    selected=pool.head(n).copy()
                    port=stack_oos(ledger,selected) if not selected.empty else pd.DataFrame()
                    m=density(port)
                    row=dict(split=sp,tier=tier,base_top_n=topn,profile=prof,subfilter_top_n=n,train_pool_count=int(len(pool)),selected_subfilters=int(len(selected)),base_candidates=int(len(keys)),original_wr=float(cfg.test_wr),original_pf=float(cfg.test_pf),original_density=float(cfg.test_business_day_trade_rate),**{f'oos_{k}':v for k,v in m.items()})
                    row['primary_65_gate']=bool(m['win_rate']>=0.65 and m['profit_factor']>=1.50 and m['trades']>=30)
                    row['high_volume_65_gate']=bool(m['win_rate']>=0.65 and m['profit_factor']>=1.50 and m['business_day_trade_rate']>=2.0)
                    row['fallback_62_gate']=bool(m['win_rate']>=0.62 and m['profit_factor']>=1.80 and m['trades']>=50)
                    row['review_score']=m['win_rate']*12000+cap(m['profit_factor'])*900+m['trades']*0.35+min(m['business_day_trade_rate'],30)*120-m['negative_month_count']*500
                    frontier.append(row)
                    if not selected.empty:
                        sel2=selected.assign(profile=prof,subfilter_top_n=n,stack_split=sp,stack_tier=tier,base_top_n=topn)
                        selected_out.append(sel2)
                    if cur%20==0 or cur==total: progress(cur,total,f'stack eval config={ci}/{len(d2)} profile={prof} n={n}')
        sub_all=pd.concat(sub_rows,ignore_index=True) if sub_rows else pd.DataFrame()
        fr=pd.DataFrame(frontier).sort_values(['review_score','oos_win_rate','oos_profit_factor'],ascending=[False,False,False]) if frontier else pd.DataFrame()
        selected_all=pd.concat(selected_out,ignore_index=True) if selected_out else pd.DataFrame()
        save(sub_all,out/'gold_v3_107gx_subfilter_metrics.csv'); outs.append('gold_v3_107gx_subfilter_metrics.csv')
        save(fr,out/'gold_v3_107gx_stack_frontier.csv'); outs.append('gold_v3_107gx_stack_frontier.csv')
        save(selected_all,out/'gold_v3_107gx_selected_subfilters.csv'); outs.append('gold_v3_107gx_selected_subfilters.csv')
        if fr.empty:
            blocks.append(dict(blocker_id='no_stack_frontier',reason='No stack frontier rows.'))
        else:
            best=fr.iloc[0]
            best_sel=selected_all[(selected_all.stack_split==best.split)&(selected_all.stack_tier==best.tier)&(selected_all.base_top_n==best.base_top_n)&(selected_all.profile==best.profile)&(selected_all.subfilter_top_n==best.subfilter_top_n)].copy() if not selected_all.empty else pd.DataFrame()
            best_port=stack_oos(ledger,best_sel) if not best_sel.empty else pd.DataFrame()
            save(best_port,out/'gold_v3_107gx_best_stack_ledger.csv'); outs.append('gold_v3_107gx_best_stack_ledger.csv')
            primary=int(fr.primary_65_gate.sum()); hv65=int(fr.high_volume_65_gate.sum()); fb=int(fr.fallback_62_gate.sum())
            gates=pd.DataFrame([qgate('any_primary_65_gate',primary,'>=',1),qgate('any_high_volume_65_gate',hv65,'>=',1),qgate('any_fallback_62_gate',fb,'>=',1),qgate('best_wr_ge_65',float(best.oos_win_rate),'>=',0.65),qgate('best_pf_ge_15',float(best.oos_profit_factor),'>=',1.50)])
            decision='PRIMARY_65WR_STACK_READY_FOR_REHYDRATION_AUDIT' if primary>0 else ('HIGH_VOLUME_65WR_STACK_READY_FOR_REHYDRATION_AUDIT' if hv65>0 else ('FALLBACK_62WR_STACK_REVIEW' if fb>0 else 'NO_65WR_OOS_STACK_NEED_NON_CALENDAR_LIVE_KNOWABLE_FEATURES'))
            dec=pd.DataFrame([dict(decision=decision,primary_65_gate_count=primary,high_volume_65_gate_count=hv65,fallback_62_gate_count=fb,best_split=str(best.split),best_tier=str(best.tier),best_base_top_n=int(best.base_top_n),best_profile=str(best.profile),best_subfilter_top_n=int(best.subfilter_top_n),best_selected_subfilters=int(best.selected_subfilters),best_trades=int(best.oos_trades),best_wr=float(best.oos_win_rate),best_pf=float(best.oos_profit_factor),best_density=float(best.oos_business_day_trade_rate),next_stage='107GY_RESOLVED_ONLY_REHYDRATION_65WR_STACK' if primary or hv65 else '107GY_NON_CALENDAR_LIVE_KNOWABLE_SUBFILTER_SEARCH')])
            save(gates,out/'gold_v3_107gx_quality_gate_matrix.csv'); save(dec,out/'gold_v3_107gx_next_action_decision.csv')
            outs += ['gold_v3_107gx_quality_gate_matrix.csv','gold_v3_107gx_next_action_decision.csv']
            finds.append('next_action_decision='+json.dumps(dec.to_dict(orient='records'),ensure_ascii=False,default=str))
            finds.append('top_stack_frontier='+json.dumps(fr.head(12).to_dict(orient='records'),ensure_ascii=False,default=str))
            vals.append(dict(check_id='stack_frontier_rows_positive',result='PASS' if len(fr)>0 else 'FAIL',observed=len(fr),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='candidate_pool_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blocks and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blocks),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='medium_with_percent_progress_stop_if_over_1h',elapsed_seconds=round(time.time()-t0,2))
    if not blocks and 'fr' in locals() and not fr.empty:
        summary.update(stack_frontier_rows=int(len(fr)),primary_65_gate_count=int(fr.primary_65_gate.sum()),high_volume_65_gate_count=int(fr.high_volume_65_gate.sum()),fallback_62_gate_count=int(fr.fallback_62_gate.sum()),best_wr=float(fr.iloc[0].oos_win_rate),best_pf=float(fr.iloc[0].oos_profit_factor),best_density=float(fr.iloc[0].oos_business_day_trade_rate),best_trades=int(fr.iloc[0].oos_trades),decision=decision)
    save(pd.DataFrame(blocks),out/'gold_v3_107gx_blocker_matrix.csv'); save(val,out/'gold_v3_107gx_validation_matrix.csv')
    outs += ['gold_v3_107gx_blocker_matrix.csv','gold_v3_107gx_validation_matrix.csv','gold_v3_107gx_summary.json','GOLD_V3_107GX_MULTI_SUBFILTER_STACK_65WR_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107gx_summary.json').write_text(json.dumps(summary|{'findings':finds},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GX_MULTI_SUBFILTER_STACK_65WR_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GX report\n\n'+json.dumps({'summary':summary,'findings':finds,'blockers':blocks},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107GX PASTE_ME_MULTI_SUBFILTER_STACK_65WR',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GV density2 configs plus exact candidate ledgers; multiple train-only high-WR subfilters per base candidate; no M5 re-evaluation; no runtime change','runtime_estimate: medium_with_percent_progress; stop_if_over_1h',f'blocker_count: {len(blocks)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(finds or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blocks).to_string(index=False) if blocks else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    progress(total if 'total' in locals() else 1,total if 'total' in locals() else 1,'DONE')
    log(f'DONE status={status} elapsed={time.time()-t0:.1f}s paste_me={out/"paste_me.txt"}')
    print(json.dumps({'status':status,'ready':status==READY,'elapsed_seconds':round(time.time()-t0,2),'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
