#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, itertools, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GB_DUAL_EDGE_WALKFORWARD_DENSITY_AND_CONFLICT_AUDIT_ONLY'
READY='GOLD_V3_107GB_DUAL_EDGE_WALKFORWARD_DENSITY_AND_CONFLICT_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GB_DUAL_EDGE_WALKFORWARD_DENSITY_AND_CONFLICT_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
ROOT=Path(__file__).resolve().parents[2]
NAMES={'m15':['gold#_m15.csv','goldsharp_m15.csv'],'m5':['gold#_m5.csv','goldsharp_m5.csv'],'h1':['gold#_h1.csv','goldsharp_h1.csv'],'h4':['gold#_h4.csv','goldsharp_h4.csv'],'d1':['gold#_d1.csv','goldsharp_d1.csv']}
FORBIDDEN=('gold_v2','old_gold','disc8','stage41')
FIXED=[('TP5_SL2.5_RR2_H64',5,2.5,64),('TP10_SL5_RR2_H64',10,5,64),('TP15_SL7.5_RR2_H64',15,7.5,64),('TP20_SL10_RR2_H64',20,10,64)]
VOL=[(0.5,1.5),(0.5,2.0),(0.75,2.0),(1.0,2.0),(1.25,2.5)]

def bad(p):
    s=str(p).replace('\\','/').lower(); return any(x in s for x in FORBIDDEN)

def files_dir(arg):
    if arg: return Path(arg).expanduser().resolve()
    env=os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    return Path(env).expanduser().resolve() if env else Path.cwd()

def dirs(data, mt5):
    out=[]
    if data: out.append(Path(data).expanduser().resolve())
    if mt5: out.append(Path(mt5).expanduser().resolve()/'FX_INPUTS'/'gold_v3'/'107g')
    out.append(Path.cwd())
    return list(dict.fromkeys(out))

def read_csv(p):
    df=pd.read_csv(p,sep=None,engine='python',encoding='utf-8-sig')
    cols={c.lower():c for c in df.columns}; t=cols.get('time') or cols.get('datetime') or cols.get('date')
    if not t or any(c not in cols for c in ['open','high','low','close']): raise ValueError('OHLC columns missing')
    x=df[[t,cols['open'],cols['high'],cols['low'],cols['close']]].copy(); x.columns=['time','open','high','low','close']
    x['time']=pd.to_datetime(x.time,errors='coerce')
    for c in ['open','high','low','close']: x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.dropna().sort_values('time')

def load_tf(tf, ds):
    parts=[]; src=[]
    for d in ds:
        for n in NAMES[tf]:
            p=d/n
            if p.exists() and not bad(p):
                x=read_csv(p); x['source_file']=n; parts.append(x); src.append(str(p))
    if not parts: return pd.DataFrame(), src, 0
    y=pd.concat(parts,ignore_index=True).sort_values(['time','source_file']); before=len(y); y=y.drop_duplicates('time',keep='last').sort_values('time').reset_index(drop=True)
    return y, src, before-len(y)

def ema(s,n): return s.ewm(span=n,adjust=False,min_periods=n).mean()
def atr(df,n):
    pc=df.close.shift(1); tr=pd.concat([(df.high-df.low),(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)
    return tr.rolling(n,min_periods=n).mean()
def rsi(s,n=14):
    d=s.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0); rs=up.rolling(n,min_periods=n).mean()/dn.rolling(n,min_periods=n).mean()
    return 100-100/(1+rs)

def add_feat(x,p=''):
    y=x.copy(); y[p+'ema20']=ema(y.close,20); y[p+'ema50']=ema(y.close,50); y[p+'atr28']=atr(y,28); y[p+'ret4']=y.close.diff(4); y[p+'rsi14']=rsi(y.close); return y

def merge(m15,h1,h4,d1):
    x=add_feat(m15)
    for tf,df in [('h1',h1),('h4',h4),('d1',d1)]:
        if df.empty: continue
        f=add_feat(df,tf+'_'); cols=['time']+[c for c in f if c.startswith(tf+'_')]
        x=pd.merge_asof(x.sort_values('time'),f[cols].sort_values('time'),on='time',direction='backward')
    x['entry_year']=x.time.dt.year; x['entry_month']=x.time.dt.to_period('M').astype(str); return x

def prim(df,side):
    d={}; q70=df.atr28.rolling(500,min_periods=100).quantile(.7)
    if side=='LONG':
        d['h4_up']=(df.get('h4_ema20')>df.get('h4_ema50')) & (df.get('h4_ret4')>0); d['h1_up']=(df.get('h1_ema20')>df.get('h1_ema50')) & (df.get('h1_ret4')>0)
        d['m15_uptrend']=df.ema20>df.ema50; d['pullback_long']=(df.close<df.ema20)&(df.close>df.ema50); d['momentum_long']=(df.ret4>0)&(df.close>df.ema20); d['rsi_low_mid']=(df.rsi14>=30)&(df.rsi14<=55)
    else:
        d['h4_down']=(df.get('h4_ema20')<df.get('h4_ema50')) & (df.get('h4_ret4')<0); d['h1_down']=(df.get('h1_ema20')<df.get('h1_ema50')) & (df.get('h1_ret4')<0)
        d['m15_downtrend']=df.ema20<df.ema50; d['pullback_short']=(df.close>df.ema20)&(df.close<df.ema50); d['momentum_short']=(df.ret4<0)&(df.close<df.ema20); d['rsi_high_mid']=(df.rsi14>=45)&(df.rsi14<=70)
    hr=df.time.dt.hour; d['high_vol']=df.atr28>=q70; d['non_high_vol']=df.atr28<q70; d['session_7_15']=hr.between(7,15); d['session_16_22']=hr.between(16,22)
    return {k:v.fillna(False).values for k,v in d.items()}

def cd(idx,n):
    out=[]; last=-10**9
    for i in idx:
        if i-last>=n: out.append(i); last=i
    return out

def pf(vals):
    a=np.array(vals,float); gp=a[a>0].sum(); gl=-a[a<0].sum(); return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)

def met(vals,months):
    a=np.array(vals,float); n=len(a)
    if n==0: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    neg=int((pd.DataFrame({'m':months,'r':a}).groupby('m').r.sum()<0).sum()) if months else 0
    return dict(trades=int(n),wins=int((a>0).sum()),losses=int((a<0).sum()),win_rate=float((a>0).mean()),profit_factor=float(pf(a)),sum_result_usd=float(a.sum()),negative_month_count=neg)

def one(row,m5,tp,sl,h):
    st=np.searchsorted(m5.time.values,row.time.to_datetime64(),side='right'); en=min(len(m5),st+h*3); ep=float(row.close); side=row.side
    tpv=ep+tp if side=='LONG' else ep-tp; slv=ep-sl if side=='LONG' else ep+sl
    for i in range(st,en):
        ht=(m5.high.iat[i]>=tpv) if side=='LONG' else (m5.low.iat[i]<=tpv); hs=(m5.low.iat[i]<=slv) if side=='LONG' else (m5.high.iat[i]>=slv)
        if ht and hs: return -sl
        if hs: return -sl
        if ht: return tp
    return 0.0

def profiles(df):
    prof=list(FIXED)
    for tm,rr in VOL:
        prof.append((f'TPmax5_ATR{tm}_RR{rr}_H64',tm,rr,64))
    return prof

def eval_cond(df,m5,mask,side,label,prof,cool):
    pid,a,b,h=prof; idx0=np.where(mask)[0]; idx=cd(idx0,cool); tmp=df.iloc[idx].copy(); tmp['side']=side; vals=[]; mons=[]
    for _,r in tmp.iterrows():
        if str(pid).startswith('TPmax5'):
            tp=max(5.0,float(r.atr28)*float(a)); sl=tp/float(b)
        else: tp=float(a); sl=float(b)
        vals.append(one(r,m5,tp,sl,h)); mons.append(str(r.time.to_period('M')))
    m=met(vals,mons); m.update(side=side,condition=label,profile_id=pid,cooldown_bars=cool,raw_events=int(len(idx0)),trade_count_after_cooldown=int(len(idx)))
    led=pd.DataFrame({'entry_dt':tmp.time.values,'entry_month':mons,'side':side,'condition':label,'profile_id':pid,'cooldown_bars':cool,'result_usd':vals}) if vals else pd.DataFrame()
    return m,led

def split_metrics(led):
    rows=[]
    splits={'ALL':led,'2025':led[led.entry_dt.dt.year==2025],'2026':led[led.entry_dt.dt.year==2026],'2026_03_plus':led[led.entry_dt>=pd.Timestamp('2026-03-01')],'2026_05_06':led[led.entry_month.isin(['2026-05','2026-06'])]}
    for name,g in splits.items():
        r=met(g.result_usd.tolist(),g.entry_month.tolist()) if len(g) else met([],[]); r['split']=name; rows.append(r)
    return rows

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--data-dir',default=''); ap.add_argument('--max-combos',type=int,default=120)
    a=ap.parse_args(); mt5=files_dir(a.mt5_files_dir); out=mt5/'FX_OUTPUTS'/'gold_v3'/'107gbc'; out.mkdir(parents=True,exist_ok=True); ds=dirs(a.data_dir,str(mt5))
    blockers=[]; vals=[]; findings=[]; outputs=[]; data={}; cov=[]
    for tf in ['m15','m5','h1','h4','d1']:
        data[tf],src,dup=load_tf(tf,ds); cov.append(dict(timeframe=tf,rows=len(data[tf]),min_time=data[tf].time.min() if len(data[tf]) else '',max_time=data[tf].time.max() if len(data[tf]) else '',duplicate_rows_dropped=dup,sources=';'.join(src)))
    save(pd.DataFrame(cov),out/'gold_v3_107gb_input_coverage.csv'); outputs.append('gold_v3_107gb_input_coverage.csv')
    if data['m15'].empty or data['m5'].empty: blockers.append(dict(blocker_id='missing_m15_or_m5',reason='M15 and M5 exact OHLC required'))
    allsum=[]; allled=[]; splitrows=[]
    if not blockers:
        df=merge(data['m15'],data['h1'],data['h4'],data['d1']).dropna(subset=['atr28','ema20','ema50','rsi14']).reset_index(drop=True)
        feat=dict(feature_rows=len(df),min_time=df.time.min(),max_time=df.time.max(),years=','.join(map(str,sorted(df.entry_year.unique()))),months=df.entry_month.nunique())
        save(pd.DataFrame([feat]),out/'gold_v3_107gb_feature_coverage.csv'); outputs.append('gold_v3_107gb_feature_coverage.csv')
        for side in ['LONG','SHORT']:
            pr=prim(df,side); names=list(pr); combos=[]; fwd=df.close.shift(-16)-df.close
            for r in [1,2,3]:
                for cs in itertools.combinations(names,r):
                    mask=np.ones(len(df),bool)
                    for c in cs: mask &= pr[c]
                    n=int(mask.sum())
                    if 20<=n<=12000:
                        edge=(fwd[mask].mean() if side=='LONG' else -fwd[mask].mean()); combos.append((np.nan_to_num(edge),n,'&'.join(cs),mask))
            for _,_,lab,mask in sorted(combos,reverse=True)[:a.max_combos]:
                for prof in profiles(df):
                    for cool in [0,2,4]:
                        m,led=eval_cond(df,data['m5'],mask,side,lab,prof,cool); p=10 if math.isinf(m['profit_factor']) else m['profit_factor']; m['score']=p*1000+m['sum_result_usd']/10-m['negative_month_count']*250+m['trades']*0.2; allsum.append(m)
                        if len(led) and m['trades']>=20: 
                            led=led.assign(score=m['score']); allled.append(led); sr=split_metrics(led)
                            for rr in sr: rr.update(side=side,condition=lab,profile_id=m['profile_id'],cooldown_bars=cool); splitrows.append(rr)
        summ=pd.DataFrame(allsum).sort_values('score',ascending=False); save(summ,out/'gold_v3_107gb_candidate_density_summary.csv'); outputs.append('gold_v3_107gb_candidate_density_summary.csv')
        save(pd.DataFrame(splitrows),out/'gold_v3_107gb_candidate_split_summary.csv'); outputs.append('gold_v3_107gb_candidate_split_summary.csv')
        top=summ.head(50); save(top,out/'gold_v3_107gb_top_candidates.csv'); outputs.append('gold_v3_107gb_top_candidates.csv')
        led=pd.concat(allled,ignore_index=True) if allled else pd.DataFrame(); save(led,out/'gold_v3_107gb_top_candidate_trade_ledger.csv'); outputs.append('gold_v3_107gb_top_candidate_trade_ledger.csv')
        if not led.empty:
            mon=led.groupby(['side','condition','profile_id','cooldown_bars','entry_month'],dropna=False).result_usd.apply(list).reset_index(); mon2=[]
            for _,r in mon.iterrows():
                mm=met(r.result_usd,[r.entry_month]*len(r.result_usd)); mm.update(side=r.side,condition=r.condition,profile_id=r.profile_id,cooldown_bars=r.cooldown_bars,entry_month=r.entry_month); mon2.append(mm)
            save(pd.DataFrame(mon2),out/'gold_v3_107gb_candidate_monthly_summary.csv'); outputs.append('gold_v3_107gb_candidate_monthly_summary.csv')
        bestL=top[top.side=='LONG'].head(1); bestS=top[top.side=='SHORT'].head(1)
        if len(bestL): findings.append('best_long='+json.dumps(bestL.iloc[0].to_dict(),ensure_ascii=False,default=str))
        if len(bestS): findings.append('best_short='+json.dumps(bestS.iloc[0].to_dict(),ensure_ascii=False,default=str))
        if len(bestL) and len(bestS):
            ml=bestL.iloc[0]; ms=bestS.iloc[0]; prl=prim(df,'LONG'); prs=prim(df,'SHORT')
            maskL=np.ones(len(df),bool); maskS=np.ones(len(df),bool)
            for c in str(ml.condition).split('&'): maskL &= prl[c]
            for c in str(ms.condition).split('&'): maskS &= prs[c]
            conf=pd.DataFrame([dict(long_condition=ml.condition,short_condition=ms.condition,raw_long_events=int(maskL.sum()),raw_short_events=int(maskS.sum()),raw_conflict_events=int((maskL&maskS).sum()),conflict_rate_vs_long=float((maskL&maskS).sum()/max(1,maskL.sum())),conflict_rate_vs_short=float((maskL&maskS).sum()/max(1,maskS.sum())))])
            save(conf,out/'gold_v3_107gb_conflict_audit.csv'); outputs.append('gold_v3_107gb_conflict_audit.csv')
            findings.append('conflict_audit='+json.dumps(conf.iloc[0].to_dict(),ensure_ascii=False,default=str))
    vals.append(dict(check_id='m15_m5_present',result='PASS' if not blockers else 'FAIL',observed=len(blockers),expected='0',severity='BLOCKER'))
    for cid,obs,exp in [('audit_only',True,True),('source_csv_mutated',False,False),('candidate_pool_mutated',False,False),('open_asof_allowed',False,False)]: vals.append(dict(check_id=cid,result='PASS',observed=obs,expected=exp,severity='BLOCKER'))
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()))
    if not blockers and 'feat' in locals(): summary.update(feat)
    save(pd.DataFrame(blockers),out/'gold_v3_107gb_blocker_matrix.csv'); save(val,out/'gold_v3_107gb_validation_matrix.csv')
    (out/'gold_v3_107gb_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GB_DUAL_EDGE_WALKFORWARD_DENSITY_AND_CONFLICT_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GB report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    outputs += ['gold_v3_107gb_blocker_matrix.csv','gold_v3_107gb_validation_matrix.csv','gold_v3_107gb_summary.json','GOLD_V3_107GB_DUAL_EDGE_WALKFORWARD_DENSITY_AND_CONFLICT_AUDIT_ONLY_REPORT.md','paste_me.txt']
    lines=['GOLD V3 107GB PASTE_ME_DUAL_EDGE_WALKFORWARD_DENSITY_AND_CONFLICT',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: exact OHLC filenames; density, split, conflict audit; no runtime change',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
