#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, csv, json, re, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = 'GOLD_V3_116_EXACT_LEDGER_BRIDGE'
READY = 'GOLD_V3_116_EXACT_LEDGER_BRIDGE_READY'
BLOCKED = 'GOLD_V3_116_EXACT_LEDGER_BRIDGE_BLOCKED'
M15_FILES = ['goldsharp_m15.csv', 'gold#_m15.csv']

def jst(): return datetime.now(timezone(timedelta(hours=9)))
def write_json(p: Path, o): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(o, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
def load_json(p: Path, d=None):
    if d is None: d={}
    if not p.exists(): return d
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return d
def append_jsonl(p: Path, o):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('a', encoding='utf-8') as f: f.write(json.dumps(o, ensure_ascii=False, default=str)+'\n')
def norm(x): return re.sub(r'[^a-z0-9]+','',str(x).lower())
def find_col(cols, names):
    m={norm(c):c for c in cols}
    for n in names:
        if n in m: return m[n]
    for k,v in m.items():
        if any(n in k for n in names): return v
    return None
def read_latest_ohlc(mt5: Path):
    errors=[]
    for fn in M15_FILES:
        p=mt5/fn
        if not p.exists():
            errors.append({'file':fn,'exists':False,'error':'missing'})
            continue
        try:
            sample=p.read_text(encoding='utf-8-sig', errors='ignore')[:4096]
            sep=';' if sample.count(';')>sample.count(',') else ','
            df=pd.read_csv(p, sep=sep, encoding='utf-8-sig')
            t=find_col(df.columns,['time','datetime','date','timestamp'])
            o=find_col(df.columns,['open']); h=find_col(df.columns,['high']); l=find_col(df.columns,['low']); c=find_col(df.columns,['close'])
            if not all([t,o,h,l,c]):
                errors.append({'file':fn,'exists':True,'error':'missing_ohlc_columns'})
                continue
            x=df[[t,o,h,l,c]].copy(); x.columns=['time','open','high','low','close']
            x['time']=pd.to_datetime(x['time'], errors='coerce')
            for col in ['open','high','low','close']: x[col]=pd.to_numeric(x[col], errors='coerce')
            x=x.dropna().sort_values('time').drop_duplicates('time', keep='last')
            if x.empty:
                errors.append({'file':fn,'exists':True,'error':'empty_after_parse'})
                continue
            r=x.iloc[-1]
            return {'path':str(p),'entry_dt':pd.Timestamp(r.time).strftime('%Y-%m-%d %H:%M:%S'),'open':float(r.open),'high':float(r.high),'low':float(r.low),'close':float(r.close),'rows':len(x)}, errors
        except Exception as e:
            errors.append({'file':fn,'exists':True,'error':str(e)})
    return None, errors
def parse_profile(profile: str, side: str, entry: float):
    s=str(profile)
    tp=None; sl=None
    m=re.search(r'TP([0-9]+(?:\.[0-9]+)?)_SL([0-9]+(?:\.[0-9]+)?)', s)
    if m:
        tp=float(m.group(1)); sl=float(m.group(2))
    m2=re.search(r'TPmax([0-9]+(?:\.[0-9]+)?)_ATR([0-9]+(?:\.[0-9]+)?)', s)
    if m2:
        tp=float(m2.group(1)); sl=float(m2.group(1))/1.5
    if tp is None or sl is None:
        return None, None
    if side=='LONG': return round(entry+tp,3), round(entry-sl,3)
    if side=='SHORT': return round(entry-tp,3), round(entry+sl,3)
    return None, None
def select_match(ledger: pd.DataFrame, entry_dt: str):
    x=ledger.copy()
    x['entry_dt_norm']=pd.to_datetime(x['entry_dt'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    m=x[x['entry_dt_norm']==entry_dt].copy()
    if m.empty: return None, 0
    m['result_usd_num']=pd.to_numeric(m.get('result_usd',0), errors='coerce')
    m=m.sort_values(['result_usd_num'], ascending=False)
    return m.iloc[0].to_dict(), len(m)
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'116c'; out.mkdir(parents=True, exist_ok=True)
    blockers=[]; freeze=load_json(root/'112c'/'gold_v3_112_selected_policy_freeze_manifest.json',{})
    ledger_path=root/'109c'/'gold_v3_109_selected_base_policy_ledger.csv'
    if not ledger_path.exists(): blockers.append({'blocker_id':'missing_selected_ledger','path':str(ledger_path)})
    latest, ohlc_errors=read_latest_ohlc(mt5)
    if latest is None: blockers.append({'blocker_id':'missing_latest_m15','details':ohlc_errors})
    signal=None; match_count=0; reason=''
    if not blockers:
        ledger=pd.read_csv(ledger_path, encoding='utf-8-sig', low_memory=False)
        row, match_count=select_match(ledger, latest['entry_dt'])
        if row is None:
            reason='latest_closed_candle_not_in_selected_ledger'
            signal={'signal_id':'NO_SIGNAL_EXACT_LEDGER_NO_MATCH|'+latest['entry_dt'],'entry_dt':latest['entry_dt'],'symbol':'XAUUSD','side':'NO_SIGNAL','entry_price':latest['close'],'tp':'','sl':'','reason':reason}
        else:
            side=str(row.get('side','')).upper()
            entry=float(latest['close'])
            tp,sl=parse_profile(str(row.get('profile_id','')), side, entry)
            reason='EXACT_LEDGER_MATCH'
            signal={'signal_id':'EXACT_LEDGER_MATCH|'+latest['entry_dt']+'|'+side+'|'+str(row.get('candidate_key','')),'entry_dt':latest['entry_dt'],'symbol':'XAUUSD','side':side,'entry_price':entry,'tp':tp if tp is not None else '', 'sl':sl if sl is not None else '', 'reason':reason, 'candidate_key':str(row.get('candidate_key','')), 'profile_id':str(row.get('profile_id','')), 'source':'109_selected_base_policy_ledger'}
        write_json(root/'115a'/'inbox'/'latest_signal.json', signal)
    status=READY if not blockers else BLOCKED
    now=jst(); event={'checked_at_jst':now.isoformat(),'status':status,'latest_m15':latest,'match_count':match_count,'signal':signal,'blockers':blockers,'freeze_selected_policy_key':freeze.get('selected_policy_key',''),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'approximate_reconstruction':False}
    append_jsonl(out/'journal'/now.strftime('%Y-%m')/f'gold_v3_116_bridge_{now.strftime("%Y-%m-%d")}.jsonl', event)
    write_json(out/'current'/'latest_bridge_status.json', event)
    summary={'step':STEP,'status':status,'ready':status==READY,'decision':'EXACT_LEDGER_BRIDGE_READY' if status==READY else 'EXACT_LEDGER_BRIDGE_BLOCKED','created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'latest_entry_dt':latest.get('entry_dt') if latest else '', 'match_count':match_count, 'emitted_side':signal.get('side') if signal else '', 'reason':signal.get('reason') if signal else '', 'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'approximate_reconstruction':False,'elapsed_seconds':round(time.time()-t0,2)}
    write_json(out/'gold_v3_116_summary.json', summary|{'blockers':blockers})
    lines=['GOLD V3 116 PASTE_ME_EXACT_LEDGER_BRIDGE',f'status: {status}',f'ready: {str(status==READY).lower()}',f'latest_entry_dt: {summary["latest_entry_dt"]}',f'match_count: {match_count}',f'emitted_side: {summary["emitted_side"]}',f'reason: {summary["reason"]}','source_csv_mutated: false','contract_mutated: false','open_asof_allowed: false','approximate_reconstruction: false','blocker_count: '+str(len(blockers)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
