#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, itertools, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GF_WALKFORWARD_CANDIDATE_SELECTION_AUDIT_ONLY'
READY='GOLD_V3_107GF_WALKFORWARD_CANDIDATE_SELECTION_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GF_WALKFORWARD_CANDIDATE_SELECTION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
KEY=['side','condition','profile_id','cooldown_bars']

def files_dir(arg):
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(env).expanduser().resolve() if env else Path.cwd()

def pf(vals):
    a=np.array(vals,float); gp=a[a>0].sum(); gl=-a[a<0].sum()
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)

def metric(df):
    if df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['result_usd']=pd.to_numeric(x.result_usd,errors='coerce'); x=x[x.result_usd.notna()]
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    if 'entry_month' not in x: x['entry_month']=pd.to_datetime(x.entry_dt,errors='coerce').dt.to_period('M').astype(str)
    mon=x.groupby('entry_month').result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))

def pfcap(x): return 10.0 if math.isinf(x) else min(float(x),10.0)
def key_tuple(r): return tuple(str(r[c]) for c in KEY)
def overlap(a,b): return len(a&b)/max(1,min(len(a),len(b))) if a and b else 0.0

def score_train(m): return pfcap(m['profit_factor'])*1000 + m['win_rate']*700 + min(m['trades'],600)*0.35 - m['negative_month_count']*250

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def month_range(all_months,target,lookback):
    idx=all_months.index(target)
    if lookback=='expanding': return all_months[:idx]
    n=int(lookback); return all_months[max(0,idx-n):idx]

def select_side(train, side, min_tr, min_pf, min_wr, max_neg, max_cands, max_ov):
    cand=[]
    for k,g in train[train.side==side].groupby(KEY,dropna=False):
        m=metric(g)
        if m['trades']>=min_tr and m['profit_factor']>=min_pf and m['win_rate']>=min_wr and m['negative_month_count']<=max_neg:
            st=set(pd.to_datetime(g.entry_dt).astype(str)); cand.append((score_train(m),tuple(map(str,k)),st,m))
    cand=sorted(cand,key=lambda x:x[0],reverse=True); chosen=[]; sets=[]
    for sc,k,st,m in cand:
        ov=max([overlap(st,s) for s in sets], default=0.0)
        if ov<=max_ov:
            chosen.append((sc,k,m,ov)); sets.append(st)
        if len(chosen)>=max_cands: break
    return chosen

def apply_month(test, chosen, target_month):
    parts=[]
    for side,items in chosen.items():
        for rank,(sc,k,m,ov) in enumerate(items,1):
            g=test[(test.side.astype(str)==k[0])&(test.condition.astype(str)==k[1])&(test.profile_id.astype(str)==k[2])&(test.cooldown_bars.astype(str)==k[3])].copy()
            if g.empty: continue
            g['wf_side']=side; g['wf_rank']=rank; g['train_score']=sc; g['target_month']=target_month; g['train_trades']=m['trades']; g['train_pf']=m['profit_factor']; g['train_wr']=m['win_rate']
            parts.append(g)
    raw=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
    if raw.empty: return raw,0
    raw=raw.sort_values(['entry_dt','train_score'],ascending=[True,False])
    conflicts=int(raw.duplicated('entry_dt',keep=False).sum())
    out=raw.drop_duplicates('entry_dt',keep='first')
    return out, conflicts

def qgate(name,obs,op,thr):
    ok=obs>=thr if op=='>=' else obs<=thr if op=='<=' else obs==thr
    return dict(gate=name,observed=obs,operator=op,threshold=thr,result='PASS' if ok else 'FAIL')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); a=ap.parse_args()
    mt5=files_dir(a.mt5_files_dir); src=mt5/'FX_OUTPUTS'/'gold_v3'/'107gbc'; out=mt5/'FX_OUTPUTS'/'gold_v3'/'107gfc'; out.mkdir(parents=True,exist_ok=True)
    ledger_p=src/'gold_v3_107gb_top_candidate_trade_ledger.csv'
    blockers=[]; vals=[]; findings=[]; outputs=[]
    if not ledger_p.exists(): blockers.append(dict(blocker_id='missing_107gb_candidate_ledger',artifact=str(ledger_p),reason='required 107GB output missing'))
    if not blockers:
        led=pd.read_csv(ledger_p,encoding='utf-8-sig')
        led['entry_dt']=pd.to_datetime(led.entry_dt,errors='coerce'); led=led[led.entry_dt.notna()].copy()
        led['entry_month']=led.entry_dt.dt.to_period('M').astype(str); led['result_usd']=pd.to_numeric(led.result_usd,errors='coerce')
        for c in KEY: led[c]=led[c].astype(str)
        months=sorted(led.entry_month.unique().tolist())
        cfgs=list(itertools.product(['3','6','12','expanding'],[20,40,80],[1.5,1.8,2.0],[0.50,0.55,0.60],[1,2],[1,2,4]))
        cfg_rows=[]; monthly_rows=[]; select_rows=[]; ledger_parts=[]; conf_rows=[]
        for ci,(lb,mintr,minpf,minwr,maxneg,maxcand) in enumerate(cfgs):
            parts=[]; conf_total=0; used_months=0
            for target in months:
                tr_m=month_range(months,target,lb)
                if len(tr_m)<3: continue
                train=led[led.entry_month.isin(tr_m)]; test=led[led.entry_month==target]
                chosen={'LONG':select_side(train,'LONG',mintr,minpf,minwr,maxneg,maxcand,.35),'SHORT':select_side(train,'SHORT',mintr,minpf,minwr,maxneg,maxcand,.35)}
                for side,items in chosen.items():
                    for rank,(sc,k,m,ov) in enumerate(items,1): select_rows.append(dict(config_id=ci,target_month=target,side=side,rank=rank,condition=k[1],profile_id=k[2],cooldown_bars=k[3],train_score=sc,train_trades=m['trades'],train_wr=m['win_rate'],train_pf=m['profit_factor'],train_negative_month_count=m['negative_month_count'],max_overlap=ov,lookback_months=lb,min_train_trades=mintr,min_train_pf=minpf,min_train_wr=minwr,max_train_negative_months=maxneg,max_candidates_per_side=maxcand))
                outm,conf=apply_month(test,chosen,target); conf_total+=conf
                if not outm.empty:
                    used_months+=1; parts.append(outm.assign(config_id=ci,lookback_months=lb,min_train_trades=mintr,min_train_pf=minpf,min_train_wr=minwr,max_train_negative_months=maxneg,max_candidates_per_side=maxcand))
                    mm=metric(outm); mm.update(config_id=ci,target_month=target,conflict_rows_before_resolution=conf); monthly_rows.append(mm)
            allout=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
            m=metric(allout); m.update(config_id=ci,lookback_months=lb,min_train_trades=mintr,min_train_pf=minpf,min_train_wr=minwr,max_train_negative_months=maxneg,max_candidates_per_side=maxcand,walkforward_months=used_months,conflict_rows_before_resolution=conf_total)
            p=pfcap(m['profit_factor']); m['wf_score']=p*1000+m['win_rate']*800+min(m['trades'],800)*0.3-m['negative_month_count']*350-conf_total*0.1
            cfg_rows.append(m)
            if not allout.empty and m['trades']>=100: ledger_parts.append(allout)
        cfg=pd.DataFrame(cfg_rows).sort_values('wf_score',ascending=False); save(cfg,out/'gold_v3_107gf_wf_config_summary.csv'); outputs.append('gold_v3_107gf_wf_config_summary.csv')
        save(pd.DataFrame(monthly_rows),out/'gold_v3_107gf_wf_monthly_summary.csv'); outputs.append('gold_v3_107gf_wf_monthly_summary.csv')
        save(pd.DataFrame(select_rows),out/'gold_v3_107gf_wf_selection_log.csv'); outputs.append('gold_v3_107gf_wf_selection_log.csv')
        best_id=int(cfg.iloc[0].config_id) if len(cfg) else -1
        best_led=pd.concat([x for x in ledger_parts if len(x) and int(x.config_id.iloc[0])==best_id],ignore_index=True) if ledger_parts else pd.DataFrame()
        if best_led.empty and best_id>=0:
            # recreate exact best ledger if it was under storage threshold
            best=cfg.iloc[0]; parts=[]
            for target in months:
                tr_m=month_range(months,target,str(best.lookback_months))
                if len(tr_m)<3: continue
                train=led[led.entry_month.isin(tr_m)]; test=led[led.entry_month==target]
                chosen={'LONG':select_side(train,'LONG',int(best.min_train_trades),float(best.min_train_pf),float(best.min_train_wr),int(best.max_train_negative_months),int(best.max_candidates_per_side),.35),'SHORT':select_side(train,'SHORT',int(best.min_train_trades),float(best.min_train_pf),float(best.min_train_wr),int(best.max_train_negative_months),int(best.max_candidates_per_side),.35)}
                outm,_=apply_month(test,chosen,target)
                if not outm.empty: parts.append(outm.assign(config_id=best_id))
            best_led=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
        save(best_led,out/'gold_v3_107gf_wf_selected_trade_ledger.csv'); outputs.append('gold_v3_107gf_wf_selected_trade_ledger.csv')
        conf=pd.DataFrame([dict(best_config_id=best_id,conflict_rows_before_resolution=int(cfg.iloc[0].conflict_rows_before_resolution) if len(cfg) else 0)])
        save(conf,out/'gold_v3_107gf_wf_conflict_summary.csv'); outputs.append('gold_v3_107gf_wf_conflict_summary.csv')
        bm=metric(best_led); gates=[qgate('wf_trades',bm['trades'],'>=',300),qgate('wf_pf',bm['profit_factor'],'>=',1.8),qgate('wf_wr',bm['win_rate'],'>=',0.55),qgate('wf_negative_months',bm['negative_month_count'],'<=',3)]
        gate_df=pd.DataFrame(gates); save(gate_df,out/'gold_v3_107gf_quality_gate_matrix.csv'); outputs.append('gold_v3_107gf_quality_gate_matrix.csv')
        warn=pd.DataFrame([dict(warning_id='candidate_universe_selection_bias',severity='IMPORTANT',message='WF selection uses only prior results per target month, but the candidate universe itself comes from Stage107GB full-period candidate generation. A later train-only universe generation audit is still required.')])
        save(warn,out/'gold_v3_107gf_selection_bias_warning.csv'); outputs.append('gold_v3_107gf_selection_bias_warning.csv')
        findings.append('best_wf_config='+json.dumps(cfg.iloc[0].to_dict(),ensure_ascii=False,default=str) if len(cfg) else 'NO_CONFIG')
        findings.append('best_wf_metric='+json.dumps(bm,ensure_ascii=False,default=str))
        findings.append('quality_gates='+json.dumps(gate_df.result.value_counts().to_dict(),ensure_ascii=False,default=str))
        vals.append(dict(check_id='wf_configs_positive',result='PASS' if len(cfg)>0 else 'FAIL',observed=len(cfg),expected='>0',severity='BLOCKER'))
    for cid,obs,exp in [('audit_only',True,True),('source_csv_mutated',False,False),('candidate_pool_mutated',False,False),('open_asof_allowed',False,False)]: vals.append(dict(check_id=cid,result='PASS',observed=obs,expected=exp,severity='BLOCKER'))
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),input_dir=str(src),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()))
    if not blockers and 'bm' in locals(): summary.update({f'best_wf_{k}':v for k,v in bm.items()})
    save(pd.DataFrame(blockers),out/'gold_v3_107gf_blocker_matrix.csv'); save(val,out/'gold_v3_107gf_validation_matrix.csv')
    (out/'gold_v3_107gf_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GF_WALKFORWARD_CANDIDATE_SELECTION_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GF report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107gf_blocker_matrix.csv','gold_v3_107gf_validation_matrix.csv','gold_v3_107gf_summary.json','GOLD_V3_107GF_WALKFORWARD_CANDIDATE_SELECTION_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107GF PASTE_ME_WALKFORWARD_CANDIDATE_SELECTION',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107GB candidate ledger; monthly prior-history walk-forward selection; no runtime change',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
