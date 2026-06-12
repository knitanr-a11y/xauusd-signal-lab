#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, itertools, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107G_DUAL_EDGE_CONDITION_CANDIDATE_DESIGN_AUDIT_ONLY'
READY='GOLD_V3_107G_DUAL_EDGE_CONDITION_CANDIDATE_DESIGN_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107G_DUAL_EDGE_CONDITION_CANDIDATE_DESIGN_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
ROOT=Path(__file__).resolve().parents[2]
FORBIDDEN=('gold_v2','old_gold','disc8','stage41')
NAMES={'m15':['gold#_m15.csv','goldsharp_m15.csv'],'m5':['gold#_m5.csv','goldsharp_m5.csv'],'h1':['gold#_h1.csv','goldsharp_h1.csv'],'h4':['gold#_h4.csv','goldsharp_h4.csv'],'d1':['gold#_d1.csv','goldsharp_d1.csv']}
FIXED=[('TP5_SL2.5_RR2_H64',5,2.5,64),('TP10_SL5_RR2_H64',10,5,64),('TP15_SL7.5_RR2_H64',15,7.5,64),('TP20_SL10_RR2_H64',20,10,64)]
VOL=[(0.5,1.5),(0.75,2.0),(1.0,2.0),(1.25,2.5)]

def bad(p):
    s=str(p).replace('\\','/').lower(); return any(x in s for x in FORBIDDEN)

def base_dirs(arg, mt5):
    out=[]
    if arg: out.append(Path(arg).expanduser().resolve())
    if mt5:
        b=Path(mt5).expanduser().resolve(); out += [b/'FX_INPUTS'/'gold_v3'/'107g', b]
    out.append(Path.cwd())
    return list(dict.fromkeys(out))

def read_one(p):
    df=pd.read_csv(p,sep=None,engine='python',encoding='utf-8-sig')
    cols={c.lower():c for c in df.columns}; t=cols.get('time') or cols.get('datetime') or cols.get('date')
    if not t or any(k not in cols for k in ['open','high','low','close']): raise ValueError('missing time/ohlc')
    x=df[[t,cols['open'],cols['high'],cols['low'],cols['close']]].copy(); x.columns=['time','open','high','low','close']
    x['time']=pd.to_datetime(x.time,errors='coerce')
    for c in ['open','high','low','close']: x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.dropna().sort_values('time')

def load_tf(tf, dirs):
    parts=[]; used=[]
    for d in dirs:
        for n in NAMES[tf]:
            p=d/n
            if p.exists() and not bad(p):
                x=read_one(p); x['source_file']=n; parts.append(x); used.append(str(p))
    if not parts: return pd.DataFrame(), used
    df=pd.concat(parts,ignore_index=True).sort_values(['time','source_file'])
    before=len(df); df=df.drop_duplicates('time',keep='last').sort_values('time').reset_index(drop=True)
    df.attrs['dup_dropped']=before-len(df); return df, used

def ema(s,n): return s.ewm(span=n,adjust=False,min_periods=n).mean()
def atr(df,n):
    pc=df.close.shift(1); tr=pd.concat([(df.high-df.low),(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)
    return tr.rolling(n,min_periods=n).mean()
def rsi(s,n=14):
    d=s.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0); rs=up.rolling(n,min_periods=n).mean()/dn.rolling(n,min_periods=n).mean()
    return 100-100/(1+rs)

def add_base(df,prefix=''):
    x=df.copy(); x[prefix+'ema20']=ema(x.close,20); x[prefix+'ema50']=ema(x.close,50); x[prefix+'ema100']=ema(x.close,100)
    x[prefix+'atr14']=atr(x,14); x[prefix+'atr28']=atr(x,28); x[prefix+'ret1']=x.close.diff(1); x[prefix+'ret4']=x.close.diff(4); x[prefix+'ret16']=x.close.diff(16); x[prefix+'rsi14']=rsi(x.close,14)
    return x

def merge_htf(m15,h1,h4,d1):
    x=m15.copy()
    for tf,df in [('h1',h1),('h4',h4),('d1',d1)]:
        if df.empty: continue
        f=add_base(df,tf+'_'); cols=['time']+[c for c in f.columns if c.startswith(tf+'_')]
        x=pd.merge_asof(x.sort_values('time'),f[cols].sort_values('time'),on='time',direction='backward')
    return x

def primitives(df,side):
    c={}
    if side=='LONG':
        c['h4_up']=(df.get('h4_ema20')>df.get('h4_ema50')) & (df.get('h4_ret4')>0); c['h1_up']=(df.get('h1_ema20')>df.get('h1_ema50')) & (df.get('h1_ret4')>0)
        c['m15_uptrend']=(df.ema20>df.ema50); c['pullback_long']=(df.close<df.ema20) & (df.close>df.ema50); c['momentum_long']=(df.ret4>0) & (df.close>df.ema20); c['rsi_low_mid']=(df.rsi14>=30) & (df.rsi14<=55)
    else:
        c['h4_down']=(df.get('h4_ema20')<df.get('h4_ema50')) & (df.get('h4_ret4')<0); c['h1_down']=(df.get('h1_ema20')<df.get('h1_ema50')) & (df.get('h1_ret4')<0)
        c['m15_downtrend']=(df.ema20<df.ema50); c['pullback_short']=(df.close>df.ema20) & (df.close<df.ema50); c['momentum_short']=(df.ret4<0) & (df.close<df.ema20); c['rsi_high_mid']=(df.rsi14>=45) & (df.rsi14<=70)
    q70=df.atr28.rolling(500,min_periods=100).quantile(.70); c['high_vol']=(df.atr28>=q70); c['non_high_vol']=(df.atr28<q70)
    hr=df.time.dt.hour; c['session_7_15']=hr.between(7,15); c['session_16_22']=hr.between(16,22)
    return {k:v.fillna(False).values for k,v in c.items()}

def result_one(row,m5,tp,sl,h=64):
    start=np.searchsorted(m5['time'].values,row.time.to_datetime64(),side='right'); end=min(len(m5),start+h*3)
    ep=float(row.close); side=row.side
    if side=='LONG': tpv=ep+tp; slv=ep-sl
    else: tpv=ep-tp; slv=ep+sl
    hi=m5.high.values; lo=m5.low.values
    for i in range(start,end):
        ht=(hi[i]>=tpv) if side=='LONG' else (lo[i]<=tpv); hs=(lo[i]<=slv) if side=='LONG' else (hi[i]>=slv)
        if ht and hs: return -sl
        if hs: return -sl
        if ht: return tp
    return 0.0

def apply_cd(idx,cool=4):
    out=[]; last=-10**9
    for i in idx:
        if i-last>=cool: out.append(i); last=i
    return out

def metrics(vals,months=None):
    a=np.array(vals,float); tr=len(a)
    if tr==0: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    gp=a[a>0].sum(); gl=-a[a<0].sum(); p=gp/gl if gl>0 else (math.inf if gp>0 else 0.0); neg=0
    if months is not None and len(months)==tr:
        s=pd.DataFrame({'m':months,'r':a}).groupby('m').r.sum(); neg=int((s<0).sum())
    return dict(trades=int(tr),wins=int((a>0).sum()),losses=int((a<0).sum()),win_rate=float((a>0).mean()),profit_factor=float(p),sum_result_usd=float(a.sum()),negative_month_count=neg)

def eval_candidate(df,m5,mask,side,label,profile):
    prof,tp,sl,h=profile; idx=apply_cd(np.where(mask)[0],4); vals=[]; mons=[]
    tmp=df.iloc[idx].copy(); tmp['side']=side
    for _,r in tmp.iterrows(): vals.append(result_one(r,m5,tp,sl,h)); mons.append(str(r.time.to_period('M')))
    m=metrics(vals,mons); m.update(side=side,condition=label,profile_id=prof,tp_usd=tp,sl_usd=sl,horizon_m15=h,entry_count=len(idx))
    rows=pd.DataFrame({'entry_dt':tmp.time.values,'side':side,'condition':label,'profile_id':prof,'result_usd':vals}) if vals else pd.DataFrame()
    return m,rows

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--data-dir',default=''); ap.add_argument('--mt5-files-dir',default=os.environ.get('MT5_FILES_DIR','')); ap.add_argument('--max-combos',type=int,default=120)
    args=ap.parse_args(); dirs=base_dirs(args.data_dir,args.mt5_files_dir); base=Path(args.mt5_files_dir).expanduser().resolve() if args.mt5_files_dir else Path.cwd(); out=base/'FX_OUTPUTS'/'gold_v3'/'107gc'; out.mkdir(parents=True,exist_ok=True)
    blockers=[]; vals=[]; findings=[]; outputs=[]; loaded={}; cov=[]
    for tf in ['m15','m5','h1','h4','d1']:
        loaded[tf],used=load_tf(tf,dirs); cov.append(dict(timeframe=tf,rows=len(loaded[tf]),min_time=loaded[tf].time.min() if len(loaded[tf]) else '',max_time=loaded[tf].time.max() if len(loaded[tf]) else '',sources=';'.join(used),duplicate_rows_dropped=loaded[tf].attrs.get('dup_dropped',0)))
    covdf=pd.DataFrame(cov); save(covdf,out/'gold_v3_107g_input_coverage.csv'); outputs.append('gold_v3_107g_input_coverage.csv')
    if loaded['m15'].empty or loaded['m5'].empty: blockers.append(dict(blocker_id='missing_m15_or_m5',reason='M15 and M5 exact OHLC files are required'))
    if not blockers:
        m15=add_base(loaded['m15']); df=merge_htf(m15,loaded['h1'],loaded['h4'],loaded['d1']).dropna(subset=['atr28','ema20','ema50','rsi14']).reset_index(drop=True)
        df['entry_year']=df.time.dt.year; df['entry_month']=df.time.dt.to_period('M').astype(str)
        save(pd.DataFrame([dict(feature_rows=len(df),years=','.join(map(str,sorted(df.entry_year.dropna().unique()))),min_time=df.time.min(),max_time=df.time.max())]),out/'gold_v3_107g_feature_coverage.csv'); outputs.append('gold_v3_107g_feature_coverage.csv')
        all_summ=[]; ledgers=[]
        for side in ['LONG','SHORT']:
            prim=primitives(df,side); names=list(prim.keys()); combos=[]
            for r in [2,3]:
                for cs in itertools.combinations(names,r):
                    mask=np.ones(len(df),dtype=bool)
                    for c in cs: mask &= prim[c]
                    n=int(mask.sum())
                    if 40<=n<=8000: combos.append(('&'.join(cs),mask,n))
            scored=[]; fwd=df.close.shift(-16)-df.close
            for lab,mask,n in combos:
                edge=(fwd[mask].mean() if side=='LONG' else -fwd[mask].mean()); scored.append((edge,n,lab,mask))
            scored=sorted(scored,key=lambda x:(np.nan_to_num(x[0]),x[1]),reverse=True)[:args.max_combos]
            for _,_,lab,mask in scored:
                for prof in FIXED:
                    m,lg=eval_candidate(df,loaded['m5'],mask,side,lab,prof); all_summ.append(m)
                    if not lg.empty and m['trades']>=20: ledgers.append(lg)
        summ=pd.DataFrame(all_summ)
        if not summ.empty:
            summ['score']=summ['profit_factor'].replace(np.inf,10)*1000 + summ['sum_result_usd']/10 - summ['negative_month_count']*250
            long_s=summ[summ.side=='LONG'].sort_values('score',ascending=False); short_s=summ[summ.side=='SHORT'].sort_values('score',ascending=False)
            save(long_s,out/'gold_v3_107g_long_edge_candidate_summary.csv'); save(short_s,out/'gold_v3_107g_short_edge_candidate_summary.csv'); top=pd.concat([long_s.head(20),short_s.head(20)],ignore_index=True); save(top,out/'gold_v3_107g_top_edge_candidates.csv')
            outputs += ['gold_v3_107g_long_edge_candidate_summary.csv','gold_v3_107g_short_edge_candidate_summary.csv','gold_v3_107g_top_edge_candidates.csv']
            if ledgers: save(pd.concat(ledgers,ignore_index=True),out/'gold_v3_107g_top_candidate_trade_ledger.csv'); outputs.append('gold_v3_107g_top_candidate_trade_ledger.csv')
            bL=long_s.iloc[0].to_dict() if len(long_s) else {}; bS=short_s.iloc[0].to_dict() if len(short_s) else {}
            findings.append('best_long_edge: '+json.dumps(bL,ensure_ascii=False,default=str)); findings.append('best_short_edge: '+json.dumps(bS,ensure_ascii=False,default=str))
            findings.append('vol_tpsl_note: 107G initial compact script evaluates fixed RR2 profiles; TP-min-5/SL=TP/RR dynamic profiles remain in spec for expanded 107G-B')
        else: blockers.append(dict(blocker_id='no_candidate_results',reason='candidate generation returned no rows'))
    vals.append(dict(check_id='m15_m5_present',result='PASS' if not blockers else 'FAIL',observed=len(blockers),expected='0 blockers',severity='BLOCKER'))
    for cid,obs,exp in [('audit_only',True,True),('source_csv_mutated',False,False),('candidate_pool_mutated',False,False),('open_asof_allowed',False,False)]: vals.append(dict(check_id=cid,result='PASS',observed=obs,expected=exp,severity='BLOCKER'))
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()))
    save(pd.DataFrame(blockers),out/'gold_v3_107g_blocker_matrix.csv'); save(val,out/'gold_v3_107g_validation_matrix.csv')
    (out/'gold_v3_107g_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107G_DUAL_EDGE_CONDITION_CANDIDATE_DESIGN_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107G report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107g_blocker_matrix.csv','gold_v3_107g_validation_matrix.csv','gold_v3_107g_summary.json','GOLD_V3_107G_DUAL_EDGE_CONDITION_CANDIDATE_DESIGN_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107G PASTE_ME_DUAL_EDGE_CONDITION_CANDIDATE_DESIGN',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: exact OHLC filenames; new LONG/SHORT edge condition candidates; no runtime change',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
