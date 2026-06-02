#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, os, re, time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

SYSTEM_PROMPT = """You are a live-like XAUUSD signal risk tagger. Use only the provided signal-time snapshot.
Do not infer from future outcome. Return strict JSON only.
CAP_3 is the normal safe maximum when acceptable. CAP_2 means moderate crowding/risk. CAP_1 means high risk.
REPRESENTATIVE_ONLY means only one best signal should remain. BLOCK means avoid the trade."""
COLUMNS = ["snapshot_id","api_status","api_error","elapsed_sec","model","decision","stack_permission","risk_score","confidence","quality_tags","risk_tags","block_tags","reason_code","reason_short","raw_json"]
DONE={"OK","DRY_RUN"}

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument('--input', required=True); p.add_argument('--schema', required=True); p.add_argument('--output', required=True)
    p.add_argument('--env-file', default=''); p.add_argument('--model', default='gpt-4.1-mini'); p.add_argument('--timeout-sec', type=float, default=12.0)
    p.add_argument('--sleep-sec', type=float, default=0.2); p.add_argument('--resume', action='store_true'); p.add_argument('--max-rows', type=int, default=0); p.add_argument('--dry-run', action='store_true'); p.add_argument('--log-file', default='')
    return p.parse_args()

def log(msg, path=None):
    s=f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"; print(s, flush=True)
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path,'a',encoding='utf-8') as f: f.write(s+'\n')

def load_env(path, log_path):
    if not path or not Path(path).exists(): return
    pat=re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")
    loaded=[]
    for raw in Path(path).read_text(encoding='utf-8-sig').splitlines():
        line=raw.strip()
        if not line or line.startswith('#'): continue
        m=pat.match(line)
        if not m: continue
        k,v=m.group(1),m.group(2)
        if k not in {'OPENAI_API_KEY','OPENAI_MODEL'}: continue
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")): v=v[1:-1]
        if not os.environ.get(k): os.environ[k]=v; loaded.append(k)
    if loaded: log('Loaded env keys: '+', '.join(loaded), log_path)

def extract_text(resp: Any) -> str:
    if getattr(resp,'output_text',None): return str(resp.output_text)
    out=getattr(resp,'output',None)
    if out:
        parts=[]
        for item in out:
            for c in getattr(item,'content',[]) or []:
                t=getattr(c,'text',None)
                if t: parts.append(str(t))
        if parts: return ''.join(parts)
    try:
        return json.dumps(resp.model_dump(), ensure_ascii=False)
    except Exception:
        raise RuntimeError('Could not extract output text from OpenAI response')

def call_api(prompt, schema_obj, model, timeout):
    from openai import OpenAI
    client=OpenAI(timeout=timeout)
    kwargs=dict(
        model=model,
        input=[{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':prompt}],
        text={'format':{'type':'json_schema','name':schema_obj['name'],'schema':schema_obj['schema'],'strict':bool(schema_obj.get('strict',True))}},
        max_output_tokens=1200,
    )
    if str(model).startswith('gpt-5'):
        kwargs['reasoning']={'effort':'minimal'}
    r=client.responses.create(**kwargs)
    txt=extract_text(r)
    try:
        return json.loads(txt)
    except Exception:
        raise RuntimeError('Response was not JSON text: '+txt[:500])

def norm(res, sid, model, status, error, elapsed):
    r=dict(res); r.setdefault('snapshot_id',sid); r.setdefault('decision','REVIEW'); r.setdefault('stack_permission','CAP_3'); r.setdefault('risk_score',0); r.setdefault('confidence',0.0); r.setdefault('quality_tags',[]); r.setdefault('risk_tags',[]); r.setdefault('block_tags',[]); r.setdefault('reason_code','REVIEW_CAP2_CROWDING'); r.setdefault('reason_short','')
    return {'snapshot_id':str(r['snapshot_id']),'api_status':status,'api_error':error,'elapsed_sec':round(elapsed,4),'model':model,'decision':str(r['decision']),'stack_permission':str(r['stack_permission']),'risk_score':r['risk_score'],'confidence':r['confidence'],'quality_tags':json.dumps(r['quality_tags'],ensure_ascii=False),'risk_tags':json.dumps(r['risk_tags'],ensure_ascii=False),'block_tags':json.dumps(r['block_tags'],ensure_ascii=False),'reason_code':str(r['reason_code']),'reason_short':str(r['reason_short']),'raw_json':json.dumps(r,ensure_ascii=False)}

def fallback(sid):
    return {'snapshot_id':sid,'decision':'BLOCK','stack_permission':'BLOCK','risk_score':5,'confidence':0.0,'quality_tags':[],'risk_tags':[],'block_tags':['BLOCK_FAKE_CONFLUENCE'],'reason_code':'BLOCK_DUE_TO_FAKE_CONFLUENCE','reason_short':'API_ERROR_OR_TIMEOUT_BLOCK'}

def upsert(path, row):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    clean={k:row.get(k,'') for k in COLUMNS}
    if path.exists() and path.stat().st_size>0:
        try:
            df=pd.read_csv(path)
            for c in COLUMNS:
                if c not in df.columns: df[c]=''
            df=df[COLUMNS]
            df=df[df['snapshot_id'].astype(str)!=str(clean['snapshot_id'])]
            df=pd.concat([df,pd.DataFrame([clean])], ignore_index=True)
            df.to_csv(path,index=False,encoding='utf-8-sig'); return
        except Exception: pass
    with open(path,'a',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=COLUMNS)
        if f.tell()==0: w.writeheader()
        w.writerow(clean)

def done_ids(path):
    p=Path(path)
    if not p.exists(): return set()
    try:
        df=pd.read_csv(p)
        if 'snapshot_id' not in df.columns: return set()
        if 'api_status' in df.columns: df=df[df['api_status'].astype(str).isin(DONE)]
        return set(df['snapshot_id'].astype(str))
    except Exception: return set()

def main():
    a=parse_args(); log_path=a.log_file or str(Path(a.output).with_suffix('.run.log'))
    log('GOLD V2 AI tag Phase 2 runner started', log_path); log('MT5 disabled / Discord disabled', log_path)
    load_env(a.env_file, log_path)
    if not a.dry_run and not os.environ.get('OPENAI_API_KEY'):
        log('ERROR OPENAI_API_KEY not set', log_path); return 2
    model=a.model or os.environ.get('OPENAI_MODEL') or 'gpt-4.1-mini'
    df=pd.read_csv(a.input)
    if a.max_rows and a.max_rows>0: df=df.head(a.max_rows)
    schema=json.loads(Path(a.schema).read_text(encoding='utf-8'))
    done=done_ids(a.output) if a.resume else set(); total=len(df); ok=err=skip=0
    log(f'model={model} timeout={a.timeout_sec} total={total} output={a.output}', log_path)
    for pos,(_,row) in enumerate(df.iterrows(), start=1):
        sid=str(row['snapshot_id']); prompt=str(row['prompt_text'])
        if sid in done: skip+=1; log(f'[{pos}/{total}] SKIP snapshot_id={sid}', log_path); continue
        log(f'[{pos}/{total}] START snapshot_id={sid}', log_path); st=time.perf_counter()
        try:
            if a.dry_run:
                status='DRY_RUN'; res={'snapshot_id':sid,'decision':'REVIEW','stack_permission':'CAP_3','risk_score':0,'confidence':0.0,'quality_tags':[],'risk_tags':[],'block_tags':[],'reason_code':'REVIEW_CAP3_OK','reason_short':'DRY_RUN'}
            else:
                status='OK'; res=call_api(prompt,schema,model,a.timeout_sec)
            elapsed=time.perf_counter()-st; out=norm(res,sid,model,status,'',elapsed); upsert(a.output,out); ok+=1
            log(f"[{pos}/{total}] DONE snapshot_id={sid} status={status} elapsed={elapsed:.3f}s decision={out['decision']} stack={out['stack_permission']}", log_path)
        except Exception as exc:
            elapsed=time.perf_counter()-st; out=norm(fallback(sid),sid,model,'ERROR',repr(exc),elapsed); upsert(a.output,out); err+=1
            log(f'[{pos}/{total}] ERROR snapshot_id={sid} elapsed={elapsed:.3f}s error={exc!r}', log_path)
        if a.sleep_sec>0: time.sleep(a.sleep_sec)
    log(f'DONE total={total} ok={ok} errors={err} skipped={skip}', log_path)
    return 0 if err==0 else 1
if __name__=='__main__': raise SystemExit(main())
