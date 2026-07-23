from __future__ import annotations
import csv,json,math,os,shutil,statistics,zipfile
from datetime import datetime,timezone
from pathlib import Path

N=18; TF='%Y.%m.%d %H:%M:%S'; FILES={'XAUUSD':'goldsharp_m1.csv','BTCUSD':'btcusdsharp_m1.csv'}
TOUCH=(2.,5.,8.,10.,12.,15.); REBOUND=((5.,2.),(8.,2.),(10.,3.),(12.,3.),(15.,5.))

def rcsv(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def wcsv(p,rows):
    if not rows:
        p.write_text('',encoding='utf-8-sig')
        return
    fields=[]
    for row in rows:
        for key in row:
            if key not in fields:fields.append(key)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load_m1(p):
    r=rcsv(p); exp=['time','open','high','low','close','tick_volume','spread','real_volume']
    if not r or list(r[0])!=exp: raise RuntimeError(f'bad M1: {p}')
    return r
def bps(d,r):return d/r*10000.
def adv(t,s,b):return bps(s-float(b['low']),s) if t=='LONG' else bps(float(b['high'])-s,s)
def entry(t,b,pt):return float(b['open'])+(int(b['spread'])*pt if t=='LONG' else 0.)
def exitpx(t,b,pt):return float(b['open'])+(int(b['spread'])*pt if t=='SHORT' else 0.)
def ret(t,e,x):return bps(x-e,e) if t=='LONG' else bps(e-x,e)
def imp(t,o,n):return bps(o-n,o) if t=='LONG' else bps(n-o,o)
def win(tr,rows):
    a=datetime.strptime(tr['entry_server_open'],TF);z=datetime.strptime(tr['exit_server_open'],TF);out=[]
    for b in rows:
        t=datetime.strptime(b['time'],TF)
        if t<a:continue
        if t>z:break
        out.append((t,b))
    if not out or out[0][0]!=a or out[-1][0]!=z:raise RuntimeError('missing exact window '+tr['trade_id'])
    return out

def touch(tr,w,pt,q):
    s=float(tr['entry_bid_open']); zt,zb=w[-1]; a=datetime.strptime(tr['entry_server_open'],TF)
    for i in range(len(w)-1):
        tt,b=w[i]
        if adv(tr['direction'],s,b)<q:continue
        et,eb=w[i+1]
        if et>=zt:break
        e=entry(tr['direction'],eb,pt);x=exitpx(tr['direction'],zb,pt);v=ret(tr['direction'],e,x)
        return {'status':'ENTERED','trigger_time':tt.strftime(TF),'entry_time':et.strftime(TF),'entry_delay_minutes':int((et-a).total_seconds()/60),'entry_price':e,'return_bps':v,'entry_improvement_bps':imp(tr['direction'],float(tr['entry_exec_price']),e),'cf_outcome':'WIN' if v>0 else 'LOSS' if v<0 else 'FLAT'}
    return {'status':'SKIPPED'}

def rebound(tr,w,pt,q,r):
    s=float(tr['entry_bid_open']);zt,zb=w[-1];a=datetime.strptime(tr['entry_server_open'],TF);idx=None;ext=None;tt=None
    for i in range(len(w)-1):
        t,b=w[i]
        if adv(tr['direction'],s,b)>=q:
            idx=i;tt=t;ext=float(b['low'] if tr['direction']=='LONG' else b['high']);break
    if idx is None:return {'status':'SKIPPED'}
    for j in range(idx+1,len(w)-1):
        t,b=w[j];c=float(b['close'])
        if tr['direction']=='LONG':ext=min(ext,float(b['low'])); ok=bps(c-ext,ext)>=r
        else:ext=max(ext,float(b['high'])); ok=bps(ext-c,ext)>=r
        if not ok:continue
        et,eb=w[j+1]
        if et>=zt:break
        e=entry(tr['direction'],eb,pt);x=exitpx(tr['direction'],zb,pt);v=ret(tr['direction'],e,x)
        return {'status':'ENTERED','trigger_time':tt.strftime(TF),'rebound_confirm_time':t.strftime(TF),'entry_time':et.strftime(TF),'entry_delay_minutes':int((et-a).total_seconds()/60),'entry_price':e,'return_bps':v,'entry_improvement_bps':imp(tr['direction'],float(tr['entry_exec_price']),e),'cf_outcome':'WIN' if v>0 else 'LOSS' if v<0 else 'FLAT'}
    return {'status':'SKIPPED'}

def met(rows):
    e=[r for r in rows if r['status']=='ENTERED'];s=[r for r in rows if r['status']!='ENTERED'];v=[float(r['return_bps']) for r in e];w=[x for x in v if x>0];l=[x for x in v if x<0]
    return {'population':len(rows),'entered':len(e),'coverage':len(e)/len(rows) if rows else None,'win_rate':len(w)/len(e) if e else None,'pf':None if not l else sum(w)/abs(sum(l)),'net_bps':sum(v),'avg_bps':statistics.fmean(v) if v else None,'avg_entry_improvement_bps':statistics.fmean(float(r['entry_improvement_bps']) for r in e) if e else None,'avg_delay_min':statistics.fmean(float(r['entry_delay_minutes']) for r in e) if e else None,'missed_original_winners':sum(float(r['original_return_bps'])>0 for r in s),'missed_original_net_bps':sum(float(r['original_return_bps']) for r in s)}

def main():
    root=Path(os.environ.get('LOCALAPPDATA',''))/'xauusd_signal_lab'/'mochipoyo_alert_research';m8b=root/'outputs'/'M8B'/'LATEST';tp=m8b/'03_extra_entry_trades.csv';mp=m8b/'06_symbol_metadata.json'
    if not tp.is_file() or not mp.is_file():print('[M8BY BLOCKED] M8B LATEST missing');return 2
    tr=rcsv(tp);meta=json.loads(mp.read_text(encoding='utf-8'));fr=Path(meta.get('mt5_files_root',''))
    if len(tr)!=N or not fr.is_dir():print('[M8BY BLOCKED] frozen inputs invalid');return 2
    try:m1={k:load_m1(fr/v) for k,v in FILES.items()};wins={t['trade_id']:win(t,m1[t['ticker']]) for t in tr}
    except Exception as e:print('[M8BY BLOCKED]',e);return 2
    vars=[(f'TOUCH_{q:g}BPS','TOUCH',q,None) for q in TOUCH]+[(f'REBOUND_{q:g}_{r:g}BPS','REBOUND',q,r) for q,r in REBOUND];detail=[]
    for vid,mode,q,r in vars:
        for t in tr:
            pt=float(meta['symbols'][t['ticker']]['point']);x=touch(t,wins[t['trade_id']],pt,q) if mode=='TOUCH' else rebound(t,wins[t['trade_id']],pt,q,r)
            row={'variant':vid,'mode':mode,'pullback_bps':q,'rebound_bps':'' if r is None else r,'trade_id':t['trade_id'],'ticker':t['ticker'],'direction':t['direction'],'original_return_bps':float(t['spread_adjusted_return_bps']),'original_outcome':t['outcome'],'signal_bid_open':t['entry_bid_open']};row.update(x);detail.append(row)
    summary=[];xau=[];sj={}
    for vid,mode,q,r in vars:
        rr=[x for x in detail if x['variant']==vid];xm=[x for x in rr if x['ticker']=='XAUUSD'];bm=[x for x in rr if x['ticker']=='BTCUSD'];m=met(rr);xx=met(xm);bb=met(bm);base={'variant':vid,'mode':mode,'pullback_bps':q,'rebound_bps':'' if r is None else r};summary.append({**base,**m});xau.append({**base,**xx});sj[vid]={'all':m,'XAUUSD':xx,'BTCUSD':bb}
    out={'project':'MOCHIPOYO_ALERT_RESEARCH','stage':'M8BY_PULLBACK_ENTRY_OPPORTUNITY_AUDIT','status':'PASS_EXPLORATORY_ONLY','run_at_utc':datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),'audit_only':True,'variant_results':sj,'guardrails':{'same_18_is_validation':False,'best_grid_point_promotable':False,'new_forward_required':True,'reset_existing_m8c':False}}
    quality={'trigger_reference':'original signal M1 BID open','spread_counted_as_pullback':False,'trigger_bar_entry_used':False,'entry':'next observed M1 open','rebound_confirmation':'completed M1 close','exit_anchor':'original frozen M8B exit','commission':'NOT_MODELED','swap':'NOT_MODELED'}
    o=root/'outputs'/'M8BY';stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S');a=o/'archive'/stamp;a.mkdir(parents=True,exist_ok=False);dump(a/'01_summary.json',out);wcsv(a/'02_variant_summary.csv',summary);wcsv(a/'03_trade_variant_details.csv',detail);wcsv(a/'04_xau_variant_summary.csv',xau);dump(a/'05_data_quality.json',quality);(a/'00_READ_ME_FIRST.txt').write_text('M8BY pullback-entry opportunity audit. Same frozen 18 trades are hypothesis-generation only.\n',encoding='utf-8');(a/'06_audit.log').write_text(f'status=PASS_EXPLORATORY_ONLY\nvariants={len(vars)}\ntrades={len(tr)}\n',encoding='utf-8')
    names=['00_READ_ME_FIRST.txt','01_summary.json','02_variant_summary.csv','03_trade_variant_details.csv','04_xau_variant_summary.csv','05_data_quality.json','06_audit.log']
    with zipfile.ZipFile(a/'99_UPLOAD_PACKAGE.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in names:z.write(a/n,n)
    latest=o/'LATEST';shutil.rmtree(latest,ignore_errors=True);shutil.copytree(a,latest);print(f'[M8BY PASS] variants={len(vars)} trades={len(tr)}');print('[M8BY OUTPUT]',latest);return 0
if __name__=='__main__':raise SystemExit(main())
