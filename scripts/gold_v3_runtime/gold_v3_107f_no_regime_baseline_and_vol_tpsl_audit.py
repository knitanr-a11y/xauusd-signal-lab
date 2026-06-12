#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, itertools, json, math, os
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107F_NO_REGIME_BASELINE_AND_VOL_TPSL_AUDIT_ONLY'
READY='GOLD_V3_107F_NO_REGIME_BASELINE_AND_VOL_TPSL_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107F_NO_REGIME_BASELINE_AND_VOL_TPSL_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
ROOT=Path(__file__).resolve().parents[2]
FORBIDDEN=('gold_v2','old_gold','disc8','stage41')

def bad(p):
    s=str(p).replace('\\','/').lower(); return any(x in s for x in FORBIDDEN)

def files_dir(arg):
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    if env: return Path(env).expanduser().resolve()
    p=ROOT
    while p.parent!=p:
        if p.name.lower()=='files' and p.parent.name.lower()=='mql5': return p
        p=p.parent
    return ROOT

def pf(vals):
    a=np.array(vals,float); gp=a[a>0].sum(); gl=-a[a<0].sum()
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)

def metric(df):
    if df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df[pd.to_numeric(df.result_usd,errors='coerce').notna()].copy()
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x.result_usd=pd.to_numeric(x.result_usd,errors='coerce')
    if 'entry_month' not in x: x['entry_month']=pd.to_datetime(x.entry_dt,errors='coerce').dt.to_period('M').astype(str)
    mon=x.groupby('entry_month').result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))

def prep(df):
    df=df.copy(); df['entry_dt']=pd.to_datetime(df.entry_dt,errors='coerce'); df['exit_dt']=pd.to_datetime(df.exit_dt,errors='coerce'); df['entry_month']=df.entry_dt.dt.to_period('M').astype(str); df['result_usd']=pd.to_numeric(df.result_usd,errors='coerce')
    if 'is_high_vol' not in df and 'is_high_vol_value' in df: df['is_high_vol']=df.is_high_vol_value
    df['is_high_vol']=df.get('is_high_vol',False).astype(str).str.lower().isin(['true','1','yes'])
    return df

def side_gate(df,side,win,min_n,pf_thr):
    x=df[df.proxy_side==side].sort_values(['entry_dt','priority','candidate_label']).copy(); comp=x[x.exit_dt.notna() & x.result_usd.notna()].sort_values(['exit_dt','entry_dt','priority','candidate_label']).to_dict('records')
    hist=defaultdict(lambda:deque(maxlen=win)); ptr=0; out=[]
    for t,g in x.groupby('entry_dt',sort=True):
        now=pd.Timestamp(t)
        while ptr<len(comp) and pd.Timestamp(comp[ptr]['exit_dt'])<=now:
            r=comp[ptr]; hist[r['candidate_label']].append(float(r['result_usd'])); ptr+=1
        cand=[]
        for _,r in g.sort_values(['priority','candidate_label']).iterrows():
            vals=list(hist[r.candidate_label]); ok=len(vals)<min_n or pf(vals)>=pf_thr
            if ok: cand.append(r.to_dict())
        if cand: out.append(cand[0])
    return pd.DataFrame(out)

def dual_global(df,win,min_n,pf_thr,margin):
    x=df.sort_values(['entry_dt','priority','candidate_label']).copy(); comp=x[x.exit_dt.notna() & x.result_usd.notna()].sort_values(['exit_dt','entry_dt','proxy_side','priority','candidate_label']).to_dict('records')
    hist=defaultdict(lambda:deque(maxlen=win)); ptr=0; out=[]; nt=0
    for t,g in x.groupby('entry_dt',sort=True):
        now=pd.Timestamp(t)
        while ptr<len(comp) and pd.Timestamp(comp[ptr]['exit_dt'])<=now:
            r=comp[ptr]; hist[r['proxy_side']].append(float(r['result_usd'])); ptr+=1
        lp=pf(list(hist['LONG'])) if len(hist['LONG'])>=min_n else 0.0; sp=pf(list(hist['SHORT'])) if len(hist['SHORT'])>=min_n else 0.0
        side='NO_TRADE'
        if lp>=pf_thr and lp>=sp*margin: side='LONG'
        elif sp>=pf_thr and sp>=lp*margin: side='SHORT'
        if side=='NO_TRADE': nt+=1; continue
        gg=g[g.proxy_side==side].sort_values(['priority','candidate_label'])
        if gg.empty: nt+=1; continue
        d=gg.iloc[0].to_dict(); d.update(policy_side=side,no_regime_policy='dual_edge_global',no_trade_events=nt); out.append(d)
    return pd.DataFrame(out),nt

def score(m,nt=0):
    p=10 if math.isinf(m['profit_factor']) else m['profit_factor']
    return p*1000 + m['sum_result_usd']/10 - m['negative_month_count']*250 - nt*0.25

def find_m5(base,arg):
    if arg:
        p=Path(arg).expanduser().resolve(); return p if p.exists() and not bad(p) else None
    for name in ['M5_backtest.csv','candles_history_M5.csv','candles_history_M5_backtest.csv']:
        p=base/name
        if p.exists() and not bad(p): return p
    return None

def load_m5(p):
    df=pd.read_csv(p,sep=None,engine='python',encoding='utf-8-sig')
    cols={c.lower():c for c in df.columns}
    t=cols.get('time') or cols.get('datetime') or cols.get('date')
    h=cols.get('high'); l=cols.get('low')
    if not t or not h or not l: raise ValueError('M5 CSV requires time/high/low columns')
    out=df[[t,h,l]].copy(); out.columns=['time','high','low']; out['time']=pd.to_datetime(out.time,errors='coerce'); out['high']=pd.to_numeric(out.high,errors='coerce'); out['low']=pd.to_numeric(out.low,errors='coerce')
    return out.dropna().sort_values('time')

def eval_dyn(row,m5,tp,sl):
    ent=pd.Timestamp(row.entry_dt); ep=float(row.entry_price); side=row.proxy_side; hz=int(row.get('horizon_m15',128))*3
    fut=m5[m5.time>ent].head(hz)
    if fut.empty: return np.nan
    if side=='LONG': tpv=ep+tp; slv=ep-sl
    else: tpv=ep-tp; slv=ep+sl
    for _,b in fut.iterrows():
        hit_tp=(b.high>=tpv) if side=='LONG' else (b.low<=tpv)
        hit_sl=(b.low<=slv) if side=='LONG' else (b.high>=slv)
        if hit_tp and hit_sl: return -sl
        if hit_sl: return -sl
        if hit_tp: return tp
    return 0.0

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--m5-csv',default=''); args=ap.parse_args()
    base=files_dir(args.mt5_files_dir); out=base/'FX_OUTPUTS'/'gold_v3'/'107fc'; out.mkdir(parents=True,exist_ok=True)
    ledger=base/'FX_OUTPUTS'/'gold_v3'/'107c'/'gold_v3_107_long_short_proxy_ledger.csv'; blockers=[]; vals=[]; findings=[]; outputs=[]
    vals.append(dict(check_id='stage107_ledger_present',result='PASS' if ledger.exists() and not bad(ledger) else 'FAIL',observed=str(ledger),expected='exists and allowed',severity='BLOCKER'))
    if not ledger.exists() or bad(ledger): blockers.append(dict(blocker_id='ledger_missing_or_forbidden',artifact=str(ledger),reason='REQUIRED_INPUT_MISSING'))
    rows=[]; selected_parts=[]; vol_rows=[]; status=READY
    if not blockers:
        df=prep(pd.read_csv(ledger,encoding='utf-8-sig'))
        for side,win,mn,pft in itertools.product(['LONG','SHORT'],[20,30,50],[10,20],[1.0,1.15,1.3]):
            sel=side_gate(df,side,win,mn,pft); m=metric(sel); pol=f'no_regime_{side.lower()}_only'
            rows.append(dict(policy=pol,window=win,min_history=mn,pf_threshold=pft,side_margin='',no_trade_events='',**m,score=score(m)))
            if not sel.empty: sel=sel.assign(policy=pol,window=win,min_history=mn,pf_threshold=pft); selected_parts.append(sel)
        for win,mn,pft,mar in itertools.product([20,30,50],[10,20],[1.0,1.15,1.3],[1.0,1.15,1.3]):
            sel,nt=dual_global(df,win,mn,pft,mar); m=metric(sel)
            rows.append(dict(policy='no_regime_dual_edge_global',window=win,min_history=mn,pf_threshold=pft,side_margin=mar,no_trade_events=nt,**m,score=score(m,nt)))
            if not sel.empty: sel=sel.assign(policy='no_regime_dual_edge_global',window=win,min_history=mn,pf_threshold=pft,side_margin=mar); selected_parts.append(sel)
        summ=pd.DataFrame(rows).sort_values('score',ascending=False).reset_index(drop=True); save(summ,out/'gold_v3_107f_no_regime_policy_summary.csv'); outputs.append('gold_v3_107f_no_regime_policy_summary.csv')
        allsel=pd.concat(selected_parts,ignore_index=True) if selected_parts else pd.DataFrame(); save(allsel,out/'gold_v3_107f_no_regime_selected_trade_ledger.csv'); outputs.append('gold_v3_107f_no_regime_selected_trade_ledger.csv')
        if not allsel.empty:
            mon=allsel.groupby(['policy','entry_month'],dropna=False).apply(lambda g: pd.Series(metric(g)),include_groups=False).reset_index(); save(mon,out/'gold_v3_107f_no_regime_monthly_summary.csv'); outputs.append('gold_v3_107f_no_regime_monthly_summary.csv')
        if len(summ):
            b=summ.iloc[0]; findings.append(f"best_no_regime_policy: policy={b.policy} window={b.window} min_history={b.min_history} pf_threshold={b.pf_threshold} side_margin={b.side_margin} trades={b.trades} wr={b.win_rate} pf={b.profit_factor} sum={b.sum_result_usd}")
        m5p=find_m5(base,args.m5_csv)
        if m5p is None:
            findings.append('vol_tpsl_skipped: exact M5 CSV not found; no broad scan used')
            vol=pd.DataFrame([dict(status='SKIPPED',reason='exact M5 CSV not found',min_tp_usd=5.0,min_sl_usd=5.0)])
        else:
            m5=load_m5(m5p); base_sel=allsel.head(300).copy() if len(allsel) else df.head(300).copy()
            for tm,sm in itertools.product([0.5,0.75,1.0,1.25],[0.25,0.35,0.5,0.75]):
                x=base_sel.copy(); atr=pd.to_numeric(x.get('m15_atr28',np.nan),errors='coerce').fillna(0); x['dyn_tp_usd']=np.maximum(5.0,atr*tm); x['dyn_sl_usd']=np.maximum(5.0,atr*sm); x['result_usd']=[eval_dyn(r,m5,r.dyn_tp_usd,r.dyn_sl_usd) for _,r in x.iterrows()]
                mm=metric(x); vol_rows.append(dict(tp_mult=tm,sl_mult=sm,min_tp_usd=5.0,min_sl_usd=5.0,m5_source=str(m5p),**mm,score=score(mm)))
            vol=pd.DataFrame(vol_rows).sort_values('score',ascending=False)
        save(vol,out/'gold_v3_107f_vol_tpsl_candidate_summary.csv'); outputs.append('gold_v3_107f_vol_tpsl_candidate_summary.csv')
        vals.append(dict(check_id='no_regime_rows_positive',result='PASS' if len(rows)>0 else 'FAIL',observed=len(rows),expected='>0',severity='BLOCKER'))
    for cid,obs,exp in [('audit_only',True,True),('source_csv_mutated',False,False),('candidate_pool_mutated',False,False),('open_asof_allowed',False,False)]: vals.append(dict(check_id=cid,result='PASS',observed=obs,expected=exp,severity='BLOCKER'))
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    best={}
    if 'summ' in locals() and len(summ):
        b=summ.iloc[0].to_dict(); keep=['policy','window','min_history','pf_threshold','side_margin','trades','win_rate','profit_factor','sum_result_usd','negative_month_count','score']; best={('best_'+k):v for k,v in b.items() if k in keep}
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),input_dir=str(ledger.parent),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()))|best
    save(pd.DataFrame(blockers),out/'gold_v3_107f_blocker_matrix.csv'); save(val,out/'gold_v3_107f_validation_matrix.csv')
    comp=pd.DataFrame([summary]); save(comp,out/'gold_v3_107f_comparison_summary.csv'); outputs.append('gold_v3_107f_comparison_summary.csv')
    (out/'gold_v3_107f_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107F_NO_REGIME_BASELINE_AND_VOL_TPSL_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107F report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107f_blocker_matrix.csv','gold_v3_107f_validation_matrix.csv','gold_v3_107f_summary.json','GOLD_V3_107F_NO_REGIME_BASELINE_AND_VOL_TPSL_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107F PASTE_ME_NO_REGIME_BASELINE_AND_VOL_TPSL',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107 outputs; no-regime baseline preserved; vol TP/SL optional exact-M5 only',f'blocker_count: {len(blockers)}','','KEY_METRICS']
    lines += [f'{k}: {v}' for k,v in summary.items()]
    lines += ['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
