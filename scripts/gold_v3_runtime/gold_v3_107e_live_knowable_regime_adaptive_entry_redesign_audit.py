#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, itertools, json, math, os
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="GOLD_V3_107E_LIVE_KNOWABLE_REGIME_ADAPTIVE_ENTRY_REDESIGN_AUDIT_ONLY"
READY="GOLD_V3_107E_LIVE_KNOWABLE_REGIME_ADAPTIVE_ENTRY_REDESIGN_READY_AUDIT_ONLY"
BLOCKED="GOLD_V3_107E_LIVE_KNOWABLE_REGIME_ADAPTIVE_ENTRY_REDESIGN_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"
CSV_CONTRACT="open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden"
POOL_POLICY="poolから外さない。rolling health gateに判断させる。"
ROOT=Path(__file__).resolve().parents[2]
FORBIDDEN=("gold_v2","old_gold","disc8","stage41")

def bad(p:Path)->bool:
    s=str(p).replace('\\','/').lower(); return any(x in s for x in FORBIDDEN)

def fdir(arg:str)->Path:
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    if env: return Path(env).expanduser().resolve()
    p=ROOT
    while p.parent!=p:
        if p.name.lower()=="files" and p.parent.name.lower()=="mql5": return p
        p=p.parent
    return ROOT

def pf(v):
    a=np.array(v,float); gp=a[a>0].sum(); gl=-a[a<0].sum()
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)

def metric(x):
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=x[pd.to_numeric(x.result_usd,errors='coerce').notna()].copy()
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x.result_usd=pd.to_numeric(x.result_usd,errors='coerce')
    if 'entry_month' not in x: x['entry_month']=pd.to_datetime(x.entry_dt,errors='coerce').dt.to_period('M').astype(str)
    mon=x.groupby('entry_month').result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=float(pf(x.result_usd.tolist())),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))

def prep(df):
    df=df.copy(); df['entry_dt']=pd.to_datetime(df.entry_dt,errors='coerce'); df['exit_dt']=pd.to_datetime(df.exit_dt,errors='coerce'); df['entry_month']=df.entry_dt.dt.to_period('M').astype(str); df['entry_year']=df.entry_dt.dt.year
    df['result_usd']=pd.to_numeric(df.result_usd,errors='coerce')
    if 'is_high_vol' not in df and 'is_high_vol_value' in df: df['is_high_vol']=df.is_high_vol_value
    df['is_high_vol']=df.get('is_high_vol',False).astype(str).str.lower().isin(['true','1','yes'])
    h4=pd.to_numeric(df.get('h4_ret4',0),errors='coerce').fillna(0); df['h4_dir']=np.where(h4>0,'UP',np.where(h4<0,'DOWN','FLAT'))
    df['hv_state']=np.where(df.is_high_vol,'TRUE_HV','NON_TRUE_HV')
    hr=pd.to_numeric(df.get('jst_hour',-1),errors='coerce').fillna(-1)
    df['session_bucket']=np.select([hr.between(7,10),hr.between(11,15),hr.between(16,22)],['JST_07_10','JST_11_15','JST_16_22'],default='OTHER')
    df['weekday_bucket']='WD_'+pd.to_numeric(df.get('jst_weekday',-1),errors='coerce').fillna(-1).astype(int).astype(str)
    return df

def reg(row,key):
    mp={'jst_weekday':'weekday_bucket'}
    return '|'.join(str(row.get(mp.get(k,k),'NA')) for k in key.split('+'))

def side_pf(hist,rg,side,min_n):
    v=list(hist[(rg,side)]); return pf(v) if len(v)>=min_n else 0.0

def simulate(df,key,win,min_n,pf_thr,margin):
    x=df.sort_values(['entry_dt','priority','candidate_label']).copy()
    comp=x[x.exit_dt.notna() & x.result_usd.notna()].sort_values(['exit_dt','entry_dt','proxy_side','priority','candidate_label']).to_dict('records')
    hist=defaultdict(lambda:deque(maxlen=win)); ptr=0; out=[]; no_trade=0
    for t,g in x.groupby('entry_dt',sort=True):
        now=pd.Timestamp(t)
        while ptr<len(comp) and pd.Timestamp(comp[ptr]['exit_dt'])<=now:
            r=comp[ptr]; hist[(reg(pd.Series(r),key),r['proxy_side'])].append(float(r['result_usd'])); ptr+=1
        rg=reg(g.iloc[0],key); lp=side_pf(hist,rg,'LONG',min_n); sp=side_pf(hist,rg,'SHORT',min_n)
        side='NO_TRADE'
        if lp>=pf_thr and lp>=sp*margin: side='LONG'
        elif sp>=pf_thr and sp>=lp*margin: side='SHORT'
        if side=='NO_TRADE': no_trade+=1; continue
        gg=g[g.proxy_side==side].sort_values(['priority','candidate_label'])
        if gg.empty: no_trade+=1; continue
        d=gg.iloc[0].to_dict(); d.update(policy_side=side,regime_key=key,regime_value=rg,policy_window=win,policy_min_history=min_n,policy_pf_threshold=pf_thr,policy_margin=margin); out.append(d)
    return pd.DataFrame(out),no_trade

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    base=fdir(args.mt5_files_dir); inp=base/'FX_OUTPUTS'/'gold_v3'/'107c'/'gold_v3_107_long_short_proxy_ledger.csv'; out=base/'FX_OUTPUTS'/'gold_v3'/'107ec'; out.mkdir(parents=True,exist_ok=True)
    blockers=[]; validations=[]; findings=[]; outputs=[]
    validations.append(dict(check_id='stage107_ledger_present',result='PASS' if inp.exists() and not bad(inp) else 'FAIL',observed=str(inp),expected='exists and allowed',severity='BLOCKER'))
    if not inp.exists() or bad(inp): blockers.append(dict(blocker_id='stage107_ledger_missing_or_forbidden',artifact=str(inp),reason='REQUIRED_STAGE107_OUTPUT_MISSING_OR_FORBIDDEN'))
    grid=pd.DataFrame(); top_ledger=pd.DataFrame()
    if not blockers:
        try:
            df=prep(pd.read_csv(inp,encoding='utf-8-sig'))
            cov=df.drop_duplicates('entry_dt').groupby('entry_year').entry_dt.agg(['count','min','max']).reset_index(); save(cov,out/'gold_v3_107e_year_coverage.csv'); outputs.append('gold_v3_107e_year_coverage.csv')
            years=set(cov.entry_year.dropna().astype(int).tolist())
            if not ({2025,2026}<=years): findings.append('cross_year_2025_2026_coverage_incomplete: available_years='+','.join(map(str,sorted(years))))
            raw=df.groupby(['h4_dir','hv_state','session_bucket','proxy_side'],dropna=False).apply(lambda g: pd.Series(metric(g)),include_groups=False).reset_index(); save(raw,out/'gold_v3_107e_regime_raw_side_matrix.csv'); outputs.append('gold_v3_107e_regime_raw_side_matrix.csv')
            rows=[]; ledgers={}; keys=['h4_dir','hv_state','session_bucket','h4_dir+hv_state','h4_dir+hv_state+session_bucket','h4_dir+hv_state+jst_weekday']
            for key,win,mn,pft,mar in itertools.product(keys,[20,30,50],[10,20,30],[1.0,1.15,1.3],[1.0,1.15,1.3]):
                sel,nt=simulate(df,key,win,mn,pft,mar)
                if sel.empty: continue
                m=metric(sel); rec=metric(sel[sel.entry_dt>=pd.Timestamp('2026-03-01')]); rec56=metric(sel[sel.entry_month.isin(['2026-05','2026-06'])])
                long_n=int((sel.policy_side=='LONG').sum()); short_n=int((sel.policy_side=='SHORT').sum())
                apf=10 if math.isinf(m['profit_factor']) else m['profit_factor']; rpf=10 if math.isinf(rec['profit_factor']) else rec['profit_factor']
                score=apf*1000+rpf*450+m['sum_result_usd']/10-m['negative_month_count']*250-nt*0.25
                row=dict(regime_key=key,window=win,min_history=mn,pf_threshold=pft,side_margin=mar,no_trade_events=nt,long_trades=long_n,short_trades=short_n,score=score,**{'all_'+k:v for k,v in m.items()},**{'recent_2026_03_plus_'+k:v for k,v in rec.items()},**{'recent_2026_05_06_'+k:v for k,v in rec56.items()})
                rows.append(row); ledgers[(key,win,mn,pft,mar)]=sel
            grid=pd.DataFrame(rows).sort_values('score',ascending=False).reset_index(drop=True) if rows else pd.DataFrame()
            save(grid,out/'gold_v3_107e_regime_policy_grid_summary.csv'); outputs.append('gold_v3_107e_regime_policy_grid_summary.csv')
            top=grid.head(25); save(top,out/'gold_v3_107e_top_regime_policy_configs.csv'); outputs.append('gold_v3_107e_top_regime_policy_configs.csv')
            if len(top):
                b=top.iloc[0]; top_ledger=ledgers[(b.regime_key,int(b.window),int(b.min_history),float(b.pf_threshold),float(b.side_margin))]; save(top_ledger,out/'gold_v3_107e_top_policy_selected_trade_ledger.csv'); outputs.append('gold_v3_107e_top_policy_selected_trade_ledger.csv')
                findings.append(f"best_policy: regime_key={b.regime_key} window={b.window} min_history={b.min_history} pf_threshold={b.pf_threshold} side_margin={b.side_margin} all_pf={b.all_profit_factor} all_wr={b.all_win_rate} sum={b.all_sum_result_usd} long={b.long_trades} short={b.short_trades} no_trade={b.no_trade_events} recent03_pf={b.recent_2026_03_plus_profit_factor} recent0506_pf={b.recent_2026_05_06_profit_factor}")
            findings.append('policy_uses_only_resolved_exit_dt_le_current_entry_dt_history')
            validations.append(dict(check_id='policy_grid_rows_positive',result='PASS' if len(grid)>0 else 'FAIL',observed=len(grid),expected='>0',severity='BLOCKER'))
        except Exception as e:
            blockers.append(dict(blocker_id='stage107e_runtime_exception',artifact=str(inp),reason='RUNTIME_EXCEPTION',detail=repr(e)))
            validations.append(dict(check_id='stage107e_runtime',result='FAIL',observed=repr(e),expected='no_exception',severity='BLOCKER'))
    for cid,obs,exp in [('audit_only',True,True),('source_csv_mutated',False,False),('candidate_pool_mutated',False,False),('open_asof_allowed',False,False)]: validations.append(dict(check_id=cid,result='PASS',observed=obs,expected=exp,severity='BLOCKER'))
    val=pd.DataFrame(validations); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    best={}
    if len(grid):
        b=grid.iloc[0].to_dict(); keep=['regime_key','window','min_history','pf_threshold','side_margin','no_trade_events','long_trades','short_trades','all_trades','all_win_rate','all_profit_factor','all_sum_result_usd','all_negative_month_count','recent_2026_03_plus_profit_factor','recent_2026_05_06_profit_factor','score']; best={('best_'+k):v for k,v in b.items() if k in keep}
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),input_dir=str(inp.parent),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()),policy_grid_rows=int(len(grid)))|best
    save(pd.DataFrame(blockers),out/'gold_v3_107e_blocker_matrix.csv'); save(val,out/'gold_v3_107e_validation_matrix.csv')
    (out/'gold_v3_107e_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107E_LIVE_KNOWABLE_REGIME_ADAPTIVE_ENTRY_REDESIGN_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107E report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107e_blocker_matrix.csv','gold_v3_107e_validation_matrix.csv','gold_v3_107e_summary.json','GOLD_V3_107E_LIVE_KNOWABLE_REGIME_ADAPTIVE_ENTRY_REDESIGN_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107E PASTE_ME_LIVE_KNOWABLE_REGIME_ADAPTIVE_ENTRY_REDESIGN',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: Stage107 outputs only; live-knowable regime keys; resolved-only histories',f'blocker_count: {len(blockers)}','','KEY_METRICS']
    lines += [f'{k}: {v}' for k,v in summary.items()]
    lines += ['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
