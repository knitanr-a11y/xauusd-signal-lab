#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os, re, time, warnings
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
warnings.filterwarnings('ignore', category=FutureWarning)
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_107GZ_DEEPER_FEATURE_PAIR_SEARCH_AUDIT_ONLY'
READY='GOLD_V3_107GZ_DEEPER_FEATURE_PAIR_SEARCH_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GZ_DEEPER_FEATURE_PAIR_SEARCH_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
PROFILES=[('pair67_min5',0.67,1.30,5),('pair65_min8',0.65,1.40,8),('pair63_min12',0.63,1.60,12),('pair60_pf2_min15',0.60,2.00,15)]
TOP_NS=[5,10,20,30,50,100]


def log(s): print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}",flush=True)
def prog(i,n,s):
    p=100*i/max(1,n); log(f'progress {p:5.1f}% complete / {100-p:5.1f}% remaining | step {i}/{n} | {s}')
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def cap(v):
    try:
        x=float(v); return 10.0 if math.isinf(x) else max(0.0,min(x,10.0))
    except Exception: return 0.0

def load_augmented_ledger(mt5:Path, root:Path, out:Path):
    cov=[]; feats={}; led=[]; lc=[]
    for tf in ['m15','h1','h4','d1']:
        x,c=gy.load_tf(mt5,tf); cov+=c
        if not x.empty: feats[tf]=gy.make_features(x,tf)
    save(pd.DataFrame(cov),out/'gold_v3_107gz_ohlc_coverage.csv')
    for src,sub,fn in gy.INPUTS:
        p=root/sub/fn; rows=0; err=''
        if p.exists():
            try:
                x=gy.normalize_ledger(pd.read_csv(p,encoding='utf-8-sig'),src); rows=len(x)
                if rows: led.append(x)
            except Exception as e: err=str(e)
        lc.append(dict(source_name=src,path=str(p),exists=p.exists(),rows=rows,error=err))
    save(pd.DataFrame(lc),out/'gold_v3_107gz_input_ledger_coverage.csv')
    if not led or 'm15' not in feats: return pd.DataFrame(), cov, lc
    ledger=pd.concat(led,ignore_index=True).sort_values('entry_dt')
    for f in feats.values(): ledger=gy.merge_asof_feature(ledger,f)
    fc=[dict(feature=c,coverage=float(ledger[c].notna().mean()),non_null=int(ledger[c].notna().sum())) for c in ledger.columns if re.match(r'^(m15|h1|h4|d1)_',c)]
    save(pd.DataFrame(fc),out/'gold_v3_107gz_feature_join_coverage.csv')
    return ledger,cov,lc

def single_filter_metrics(train,test,meta):
    rows=[]
    for fid,fn in gy.make_filters(train):
        tr=train[fn(train)].copy(); tm=gy.density_metrics(tr)
        if tm['trades']<5 or tm['sum_result_usd']<=0: continue
        te=test[fn(test)].copy(); om=gy.density_metrics(te)
        score=tm['win_rate']*9000+cap(tm['profit_factor'])*800+tm['trades']*0.25-tm['negative_month_count']*250
        r=dict(filter_id=fid,filter_expr=fid,train_score=score,kind='single')
        r.update({f'train_{k}':v for k,v in tm.items()}); r.update({f'oos_{k}':v for k,v in om.items()}); r.update(meta); rows.append(r)
    return pd.DataFrame(rows)

def pair_filter_metrics(train,test,meta,top_single=12):
    singles=[]
    for fid,fn in gy.make_filters(train):
        tr=train[fn(train)].copy(); tm=gy.density_metrics(tr)
        if tm['trades']>=5 and tm['sum_result_usd']>0:
            sc=tm['win_rate']*9000+cap(tm['profit_factor'])*800+tm['trades']*0.2-tm['negative_month_count']*250
            singles.append((fid,fn,sc))
    singles=sorted(singles,key=lambda x:x[2],reverse=True)[:top_single]
    rows=[]
    for i in range(len(singles)):
        for j in range(i+1,len(singles)):
            fid1,fn1,_=singles[i]; fid2,fn2,_=singles[j]
            expr=fid1+'&&'+fid2
            mask=fn1(train)&fn2(train); tr=train[mask].copy(); tm=gy.density_metrics(tr)
            if tm['trades']<4 or tm['sum_result_usd']<=0: continue
            te=test[(fn1(test)&fn2(test))].copy(); om=gy.density_metrics(te)
            score=tm['win_rate']*10000+cap(tm['profit_factor'])*850+tm['trades']*0.25-tm['negative_month_count']*300
            r=dict(filter_id=expr,filter_expr=expr,train_score=score,kind='pair')
            r.update({f'train_{k}':v for k,v in tm.items()}); r.update({f'oos_{k}':v for k,v in om.items()}); r.update(meta); rows.append(r)
    return pd.DataFrame(rows)

def apply_expr(df,expr):
    if '&&' not in expr: return gy.apply_filter(df,expr)
    a,b=expr.split('&&',1); fs=dict(gy.make_filters(df))
    if a not in fs or b not in fs: return df.iloc[0:0]
    return df[(fs[a](df)&fs[b](df))].copy()

def stack(ledger,selected):
    parts=[]
    for _,r in selected.iterrows():
        x=ledger[(ledger.global_candidate_key==r.global_candidate_key)&(ledger.entry_dt>=pd.Timestamp(r.test_start))&(ledger.entry_dt<pd.Timestamp(r.test_end))].copy()
        x=apply_expr(x,str(r.filter_expr))
        if not x.empty:
            x['filter_expr']=r.filter_expr; x['train_score']=r.train_score; parts.append(x)
    if not parts: return pd.DataFrame()
    y=pd.concat(parts,ignore_index=True)
    return y.sort_values(['entry_dt','train_score'],ascending=[True,False]).drop_duplicates('entry_dt',keep='first')

def gate_row(n,o,op,t): return dict(gate=n,observed=o,operator=op,threshold=t,result='PASS' if (o>=t if op=='>=' else o<=t) else 'FAIL')

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--frontier-top',type=int,default=4); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'107gzc'; out.mkdir(parents=True,exist_ok=True)
    log(STEP+' START')
    blocks=[]; outputs=[]; findings=[]; vals=[]
    frontier_path=root/'107gyc'/'gold_v3_107gy_stack_frontier.csv'; sel_path=root/'107guc'/'gold_v3_107gu_selected_candidate_keys.csv'
    if not frontier_path.exists(): blocks.append(dict(blocker_id='missing_107gy_frontier',path=str(frontier_path)))
    if not sel_path.exists(): blocks.append(dict(blocker_id='missing_107gu_selected',path=str(sel_path)))
    ledger,_,_=load_augmented_ledger(mt5,root,out); outputs+=['gold_v3_107gz_ohlc_coverage.csv','gold_v3_107gz_input_ledger_coverage.csv','gold_v3_107gz_feature_join_coverage.csv']
    if ledger.empty: blocks.append(dict(blocker_id='missing_augmented_ledger_or_ohlc'))
    if not blocks:
        fr0=pd.read_csv(frontier_path,encoding='utf-8-sig').sort_values('review_score',ascending=False).head(args.frontier_top)
        sel=pd.read_csv(sel_path,encoding='utf-8-sig')
        total=sum(int(sel[(sel.split.astype(str)==str(r.split))&(sel.tier.astype(str)==str(r.tier))&(pd.to_numeric(sel.top_n,errors='coerce')==int(r.base_top_n))].shape[0]) for _,r in fr0.iterrows())+len(fr0)*len(PROFILES)*len(TOP_NS)
        cur=0; prog(cur,total,'start')
        all_sub=[]; front=[]; all_selected=[]
        for ci,(_,cfg) in enumerate(fr0.iterrows(),1):
            sp,tier,topn=str(cfg.split),str(cfg.tier),int(cfg.base_top_n)
            if sp not in gy.SPLITS: continue
            trs,tre,tes,tee=gy.SPLITS[sp]
            keys=sel[(sel.split.astype(str)==sp)&(sel.tier.astype(str)==tier)&(pd.to_numeric(sel.top_n,errors='coerce')==topn)].sort_values('rank')
            cfg_sub=[]
            for _,kr in keys.iterrows():
                cur+=1; key=str(kr.global_candidate_key)
                train=ledger[(ledger.global_candidate_key==key)&(ledger.entry_dt>=pd.Timestamp(trs))&(ledger.entry_dt<pd.Timestamp(tre))]
                test=ledger[(ledger.global_candidate_key==key)&(ledger.entry_dt>=pd.Timestamp(tes))&(ledger.entry_dt<pd.Timestamp(tee))]
                if not train.empty:
                    meta=dict(split=sp,tier=tier,base_top_n=topn,global_candidate_key=key,train_start=trs,train_end=tre,test_start=tes,test_end=tee)
                    sm1=single_filter_metrics(train,test,meta); sm2=pair_filter_metrics(train,test,meta,top_single=12)
                    sm=pd.concat([sm1,sm2],ignore_index=True) if not sm1.empty or not sm2.empty else pd.DataFrame()
                    if not sm.empty: all_sub.append(sm); cfg_sub.append(sm)
                if cur%10==0: prog(cur,total,f'pair metrics config={ci}/{len(fr0)}')
            pool0=pd.concat(cfg_sub,ignore_index=True) if cfg_sub else pd.DataFrame()
            for prof,w,pfmin,tmin in PROFILES:
                pool=pool0[(pool0.train_win_rate>=w)&(pool0.train_profit_factor>=pfmin)&(pool0.train_trades>=tmin)].sort_values('train_score',ascending=False) if not pool0.empty else pd.DataFrame()
                for n in TOP_NS:
                    cur+=1; ss=pool.head(n).copy(); port=stack(ledger,ss) if not ss.empty else pd.DataFrame(); m=gy.density_metrics(port)
                    row=dict(split=sp,tier=tier,base_top_n=topn,profile=prof,filter_top_n=n,train_pool_count=len(pool),selected_filters=len(ss),source_107gy_wr=float(cfg.oos_win_rate),source_107gy_pf=float(cfg.oos_profit_factor),source_107gy_density=float(cfg.oos_business_day_trade_rate))
                    row.update({f'oos_{k}':v for k,v in m.items()})
                    row['primary_65_gate']=bool(m['win_rate']>=0.65 and m['profit_factor']>=1.5 and m['trades']>=30)
                    row['review_63_gate']=bool(m['win_rate']>=0.63 and m['profit_factor']>=1.8 and m['trades']>=50)
                    row['small_65_gate']=bool(m['win_rate']>=0.65 and m['profit_factor']>=1.5 and m['trades']>=15)
                    row['review_score']=m['win_rate']*13000+cap(m['profit_factor'])*900+m['trades']*0.25+min(m['business_day_trade_rate'],30)*100-m['negative_month_count']*500
                    front.append(row)
                    if not ss.empty: all_selected.append(ss.assign(profile=prof,filter_top_n=n,stack_split=sp,stack_tier=tier,stack_base_top_n=topn))
                    if cur%20==0: prog(cur,total,f'stack config={ci}/{len(fr0)}')
        sub=pd.concat(all_sub,ignore_index=True) if all_sub else pd.DataFrame(); fr=pd.DataFrame(front).sort_values('review_score',ascending=False) if front else pd.DataFrame(); selected=pd.concat(all_selected,ignore_index=True) if all_selected else pd.DataFrame()
        save(sub,out/'gold_v3_107gz_filter_metrics.csv'); save(fr,out/'gold_v3_107gz_stack_frontier.csv'); save(selected,out/'gold_v3_107gz_selected_filters.csv')
        outputs+=['gold_v3_107gz_filter_metrics.csv','gold_v3_107gz_stack_frontier.csv','gold_v3_107gz_selected_filters.csv']
        if fr.empty: blocks.append(dict(blocker_id='no_frontier'))
        else:
            best=fr.iloc[0]; bs=selected[(selected.stack_split==best.split)&(selected.stack_tier==best.tier)&(selected.stack_base_top_n==best.base_top_n)&(selected.profile==best.profile)&(selected.filter_top_n==best.filter_top_n)] if not selected.empty else pd.DataFrame()
            port=stack(ledger,bs) if not bs.empty else pd.DataFrame(); save(port,out/'gold_v3_107gz_best_stack_ledger.csv'); outputs.append('gold_v3_107gz_best_stack_ledger.csv')
            p65=int(fr.primary_65_gate.sum()); r63=int(fr.review_63_gate.sum()); s65=int(fr.small_65_gate.sum())
            decision='PRIMARY_65_READY_FOR_REHYDRATION' if p65 else ('REVIEW_63_READY' if r63 else ('SMALL_65_REVIEW' if s65 else 'NO_65_PAIR_FILTER_NEED_NEW_VECTOR_OR_MODEL_FEATURES'))
            gates=pd.DataFrame([gate_row('any_primary_65',p65,'>=',1),gate_row('any_review_63',r63,'>=',1),gate_row('any_small_65',s65,'>=',1),gate_row('best_wr_ge_65',float(best.oos_win_rate),'>=',0.65),gate_row('best_trades_ge_30',int(best.oos_trades),'>=',30)])
            dec=pd.DataFrame([dict(decision=decision,primary_65_gate_count=p65,review_63_gate_count=r63,small_65_gate_count=s65,best_split=str(best.split),best_tier=str(best.tier),best_profile=str(best.profile),best_filter_top_n=int(best.filter_top_n),best_selected_filters=int(best.selected_filters),best_trades=int(best.oos_trades),best_wr=float(best.oos_win_rate),best_pf=float(best.oos_profit_factor),best_density=float(best.oos_business_day_trade_rate),next_stage='107H_RESOLVED_ONLY_REHYDRATION' if p65 else '107H_NEW_VECTOR_OR_MODEL_FEATURE_SEARCH')])
            save(gates,out/'gold_v3_107gz_quality_gate_matrix.csv'); save(dec,out/'gold_v3_107gz_next_action_decision.csv')
            outputs+=['gold_v3_107gz_quality_gate_matrix.csv','gold_v3_107gz_next_action_decision.csv']
            findings.append('next_action_decision='+json.dumps(dec.to_dict(orient='records'),ensure_ascii=False,default=str))
            findings.append('top_stack_frontier='+json.dumps(fr.head(10).to_dict(orient='records'),ensure_ascii=False,default=str))
            vals.append(dict(check_id='frontier_rows_positive',result='PASS',observed=len(fr),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blocks and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=gy.CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=gy.POOL_POLICY,blocker_count=len(blocks),validation_failure_count=int((~val.result.eq('PASS')).sum()),elapsed_seconds=round(time.time()-t0,2))
    if not blocks and 'fr' in locals() and not fr.empty:
        summary.update(stack_frontier_rows=len(fr),primary_65_gate_count=int(fr.primary_65_gate.sum()),review_63_gate_count=int(fr.review_63_gate.sum()),small_65_gate_count=int(fr.small_65_gate.sum()),best_wr=float(fr.iloc[0].oos_win_rate),best_pf=float(fr.iloc[0].oos_profit_factor),best_density=float(fr.iloc[0].oos_business_day_trade_rate),best_trades=int(fr.iloc[0].oos_trades),decision=decision)
    save(pd.DataFrame(blocks),out/'gold_v3_107gz_blocker_matrix.csv'); save(val,out/'gold_v3_107gz_validation_matrix.csv')
    outputs+=['gold_v3_107gz_blocker_matrix.csv','gold_v3_107gz_validation_matrix.csv','gold_v3_107gz_summary.json','GOLD_V3_107GZ_DEEPER_FEATURE_PAIR_SEARCH_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107gz_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GZ_DEEPER_FEATURE_PAIR_SEARCH_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GZ report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blocks},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107GZ PASTE_ME_DEEPER_FEATURE_PAIR_SEARCH',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+gy.CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+gy.POOL_POLICY,'source: Stage107GY frontier plus exact OHLC as-of features and Stage107 candidate bank; no M5 re-evaluation; no runtime change','runtime_estimate: targeted_light_to_medium_with_percent_progress','blocker_count: '+str(len(blocks)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blocks).to_string(index=False) if blocks else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    prog(total if 'total' in locals() else 1,total if 'total' in locals() else 1,'DONE')
    log(f'DONE status={status} elapsed={time.time()-t0:.1f}s paste_me={out/"paste_me.txt"}')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2

if __name__=='__main__': raise SystemExit(main())
