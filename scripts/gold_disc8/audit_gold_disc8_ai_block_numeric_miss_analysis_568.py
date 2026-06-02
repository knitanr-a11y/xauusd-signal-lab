#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, csv, json, math, shutil, sys
from datetime import datetime
from pathlib import Path
from typing import Any
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
for p in [SCRIPT_DIR, REPO_ROOT, REPO_ROOT / 'scripts']:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from build_gold_disc8_ai_tag_numeric_tagger_from_review import clean, fm, metrics, resolve, safe_float, windows_long_path  # noqa:E402

SCHEMA_VERSION='gold_disc8_ai_block_numeric_miss_analysis_568_v1_audit_only'
DEFAULT_TRADE_AUDIT=Path('data/runtime_logs/gold_disc8_ai_tag_vs_numeric_gate_replay_568/latest/gold_disc8_ai_tag_vs_numeric_gate_replay_568_trade_audit.csv')
DEFAULT_FEATURE=Path('data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/trade_feature_snapshot.csv')
DEFAULT_OUT_ROOT=Path('data/runtime_logs/gold_disc8_ai_block_numeric_miss_analysis_568')
EXPECTED_TRADE_ROWS=568
SUMMARY_COLS='group key bucket trade_count win_count loss_count flat_count win_rate profit_factor avg_r total_r'.split()
TAG_COLS='tag_group tag_name trade_count win_count loss_count flat_count win_rate profit_factor avg_r total_r strategy_count month_count'.split()
STAG_COLS='strategy_id tag_group tag_name trade_count win_count loss_count flat_count win_rate profit_factor avg_r total_r'.split()
PROBE_COLS='strategy_id tag_group tag_name positive_missed_rows feature op threshold probe_hit_rows missed_tag_capture_count missed_tag_capture_rate ai_allow_false_hit_count ai_allow_false_hit_rate precision_to_missed_tag hit_win_count hit_loss_count hit_profit_factor hit_total_r score note'.split()
FILE_AUDIT_COLS='label path exists rows columns required status note'.split()
TEXT_COL_HINTS={'trade_id','strategy_id','direction','entry_time','entry_month','ai_decision','numeric_gate_decision','confusion_class','ai_tags','numeric_tag_hits','win_loss_flat','schema_version','run_id'}
LEAK_TOKENS=['mfe','mae','post_entry','after_entry','profit','outcome','result','exit','truth','label','dispatch','win','loss','tp_price','sl_price']


def now_text(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def run_id_text(): return datetime.now().strftime('%Y%m%d_%H%M%S')
def mkdirp(p:Path): Path(windows_long_path(p)).mkdir(parents=True, exist_ok=True)
def wjson(p:Path,o:dict[str,Any]): mkdirp(p.parent); open(windows_long_path(p),'w',encoding='utf-8').write(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True,default=str))
def wcsv(p:Path,rows:list[dict[str,Any]],cols:list[str]):
    mkdirp(p.parent)
    with open(windows_long_path(p),'w',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore'); wr.writeheader()
        for r in rows: wr.writerow({c:r.get(c,'') for c in cols})

def read_csv(path:Path,label:str,required:bool=True)->pd.DataFrame:
    p=resolve(path)
    if not p.exists():
        if required: raise FileNotFoundError(f'{label} not found: {p}')
        return pd.DataFrame()
    return pd.read_csv(windows_long_path(p),encoding='utf-8-sig',sep=None,engine='python')

def audit_file(label:str,path:Path,required:bool,note:str)->dict[str,Any]:
    p=resolve(path); r={'label':label,'path':str(p),'exists':p.exists(),'rows':'','columns':'','required':required,'status':'OK' if p.exists() else ('MISSING_REQUIRED' if required else 'MISSING_OPTIONAL'),'note':note}
    if p.exists() and p.suffix.lower()=='.csv':
        try:
            df=pd.read_csv(windows_long_path(p),encoding='utf-8-sig',sep=None,engine='python'); r['rows']=len(df); r['columns']=' | '.join(map(str,df.columns))
        except Exception as e: r['status']='READ_ERROR'; r['note']=f'{note}; {type(e).__name__}: {e}'
    return r

def split_tags(text:Any)->list[tuple[str,str]]:
    s=clean(text); out=[]
    if not s: return out
    for part in s.split('|'):
        tok=clean(part)
        if ':' not in tok: continue
        g,t=tok.split(':',1); g=clean(g); t=clean(t)
        if g and t: out.append((g,t))
    return sorted(set(out))

def rval(row:Any)->float:
    x=safe_float(row.get('profit_r_num'))
    return 0.0 if x is None else float(x)

def summarize(rows:list[dict[str,Any]], group:str, key:str, bucket_field:str='')->list[dict[str,Any]]:
    buckets=['ALL'] if not bucket_field else ['ALL']+sorted({clean(r.get(bucket_field)) for r in rows if clean(r.get(bucket_field))})
    out=[]
    for b in buckets:
        sub=rows if b=='ALL' else [r for r in rows if clean(r.get(bucket_field))==b]
        vals=[float(r.get('profit_r_num') or 0.0) for r in sub]; m=metrics(vals); n=len(sub)
        out.append({'group':group,'key':key,'bucket':b,'trade_count':n,'win_count':sum(v>0 for v in vals),'loss_count':sum(v<0 for v in vals),'flat_count':sum(v==0 for v in vals),'win_rate':fm(m['win_rate']),'profit_factor':fm(m['profit_factor']),'avg_r':fm(m['avg_r']),'total_r':fm(m['total_r'])})
    return out

def tag_rows_from_misses(misses:pd.DataFrame)->list[dict[str,Any]]:
    rows=[]
    for _,r in misses.iterrows():
        base={k:r.get(k,'') for k in ['trade_id','strategy_id','direction','entry_time','entry_month','profit_r_num','win_loss_flat','ai_tags']}
        for g,t in split_tags(r.get('ai_tags')):
            rows.append({**base,'tag_group':g,'tag_name':t})
    return rows

def tag_summary(tag_rows:list[dict[str,Any]])->tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    tag_out=[]; stag_out=[]
    for g,t in sorted({(r['tag_group'],r['tag_name']) for r in tag_rows}):
        sub=[r for r in tag_rows if r['tag_group']==g and r['tag_name']==t]
        vals=[float(r.get('profit_r_num') or 0) for r in sub]; m=metrics(vals)
        tag_out.append({'tag_group':g,'tag_name':t,'trade_count':len(sub),'win_count':sum(v>0 for v in vals),'loss_count':sum(v<0 for v in vals),'flat_count':sum(v==0 for v in vals),'win_rate':fm(m['win_rate']),'profit_factor':fm(m['profit_factor']),'avg_r':fm(m['avg_r']),'total_r':fm(m['total_r']),'strategy_count':len({r['strategy_id'] for r in sub}),'month_count':len({r['entry_month'] for r in sub})})
    for sid,g,t in sorted({(r['strategy_id'],r['tag_group'],r['tag_name']) for r in tag_rows}):
        sub=[r for r in tag_rows if r['strategy_id']==sid and r['tag_group']==g and r['tag_name']==t]
        vals=[float(r.get('profit_r_num') or 0) for r in sub]; m=metrics(vals)
        stag_out.append({'strategy_id':sid,'tag_group':g,'tag_name':t,'trade_count':len(sub),'win_count':sum(v>0 for v in vals),'loss_count':sum(v<0 for v in vals),'flat_count':sum(v==0 for v in vals),'win_rate':fm(m['win_rate']),'profit_factor':fm(m['profit_factor']),'avg_r':fm(m['avg_r']),'total_r':fm(m['total_r'])})
    tag_out=sorted(tag_out,key=lambda r:(float(r['total_r']),-int(r['trade_count'])))
    stag_out=sorted(stag_out,key=lambda r:(float(r['total_r']),-int(r['trade_count'])))
    return tag_out,stag_out

def numeric_feature_cols(df:pd.DataFrame,min_non_null:int)->list[str]:
    cols=[]
    for c in df.columns:
        lc=str(c).lower()
        if c in TEXT_COL_HINTS or lc.endswith('_time') or lc.endswith('_key') or any(tok in lc for tok in LEAK_TOKENS): continue
        s=pd.to_numeric(df[c],errors='coerce')
        if int(s.notna().sum())>=min_non_null: cols.append(c)
    return cols

def feature_probe(trade:pd.DataFrame, feature:pd.DataFrame, tag_rows:list[dict[str,Any]], min_tag_rows:int, min_feature_non_null:int, max_rows_per_tag:int)->list[dict[str,Any]]:
    if feature.empty or 'trade_id' not in feature.columns: return []
    f=feature.copy(); f['trade_id']=f['trade_id'].map(clean); f=f.drop_duplicates('trade_id',keep='last')
    t=trade.copy(); t['trade_id']=t['trade_id'].map(clean)
    merged=t.merge(f,on='trade_id',how='left',suffixes=('','_feat'))
    cols=numeric_feature_cols(merged,min_feature_non_null)
    by_tag={}
    for r in tag_rows:
        key=(clean(r['strategy_id']),clean(r['tag_group']),clean(r['tag_name']))
        by_tag.setdefault(key,set()).add(clean(r['trade_id']))
    out=[]
    for (sid,g,tag),pos_ids in sorted(by_tag.items()):
        if len(pos_ids)<min_tag_rows: continue
        sdf=merged[merged['strategy_id'].astype(str).map(clean)==sid].copy()
        if sdf.empty: continue
        sid_ids=sdf['trade_id'].astype(str).map(clean)
        ai_allow=sdf['ai_decision'].astype(str).map(clean).eq('AI_ALLOW')
        for feat in cols:
            vals=pd.to_numeric(sdf[feat],errors='coerce')
            pos_vals=vals[sid_ids.isin(pos_ids)].dropna()
            if len(pos_vals)<min_feature_non_null: continue
            thresholds=sorted(set(float(pos_vals.quantile(q)) for q in [0.25,0.5,0.75] if math.isfinite(float(pos_vals.quantile(q)))))
            local=[]
            for th in thresholds:
                for op in ['<=','>=']:
                    pred=(vals<=th) if op=='<=' else (vals>=th)
                    pred=pred.fillna(False)
                    hit=int(pred.sum()); cap=int((pred & sid_ids.isin(pos_ids)).sum())
                    if hit<=0 or cap<=0: continue
                    false=int((pred & ai_allow).sum())
                    cap_rate=cap/len(pos_ids); false_rate=false/max(int(ai_allow.sum()),1); precision=cap/hit
                    hit_rows=sdf[pred]; rv=[rval(row) for _,row in hit_rows.iterrows()]; m=metrics(rv)
                    score=(cap_rate*1.5)+precision-false_rate-(float(m['total_r'])/max(hit,1))*0.2
                    local.append({'strategy_id':sid,'tag_group':g,'tag_name':tag,'positive_missed_rows':len(pos_ids),'feature':feat,'op':op,'threshold':fm(float(th)),'probe_hit_rows':hit,'missed_tag_capture_count':cap,'missed_tag_capture_rate':fm(cap_rate),'ai_allow_false_hit_count':false,'ai_allow_false_hit_rate':fm(false_rate),'precision_to_missed_tag':fm(precision),'hit_win_count':m['win_count'],'hit_loss_count':m['loss_count'],'hit_profit_factor':fm(m['profit_factor']),'hit_total_r':fm(m['total_r']),'score':fm(score),'note':'AUDIT_PROBE_ONLY_NOT_RUNTIME_RULE'})
            out += sorted(local,key=lambda r:float(r['score']),reverse=True)[:max_rows_per_tag]
    return sorted(out,key=lambda r:(r['strategy_id'],r['tag_group'],r['tag_name'],-float(r['score'])))

def parse_args():
    p=argparse.ArgumentParser(description='Analyze AI_BLOCK_AND_NUMERIC_ALLOW misses from DISC8 568 replay. Audit-only.')
    p.add_argument('--trade-audit-csv',type=Path,default=DEFAULT_TRADE_AUDIT)
    p.add_argument('--trade-feature-snapshot-csv',type=Path,default=DEFAULT_FEATURE)
    p.add_argument('--out-root',type=Path,default=DEFAULT_OUT_ROOT)
    p.add_argument('--run-id',default='')
    p.add_argument('--expected-trade-rows',type=int,default=EXPECTED_TRADE_ROWS)
    p.add_argument('--min-tag-rows',type=int,default=5)
    p.add_argument('--min-feature-non-null',type=int,default=5)
    p.add_argument('--max-probe-rows-per-tag',type=int,default=10)
    p.add_argument('--no-latest-copy',action='store_false',dest='write_latest_copy',default=True)
    return p.parse_args()

def main()->int:
    a=parse_args(); run_id=a.run_id or run_id_text(); root=resolve(a.out_root); run=root/'runs'/run_id; latest=root/'latest'; mkdirp(run)
    input_audit=[audit_file('trade_audit_csv',a.trade_audit_csv,True,'replay 568 trade audit SOT'),audit_file('trade_feature_snapshot_csv',a.trade_feature_snapshot_csv,False,'optional pre-entry feature probe source')]
    paths={'input_audit':run/'gold_disc8_ai_block_numeric_miss_input_audit.csv','missed_trades':run/'gold_disc8_ai_block_numeric_miss_trades.csv','missed_by_month':run/'gold_disc8_ai_block_numeric_miss_by_month.csv','missed_by_strategy':run/'gold_disc8_ai_block_numeric_miss_by_strategy.csv','missed_by_tag':run/'gold_disc8_ai_block_numeric_miss_by_tag.csv','missed_by_strategy_tag':run/'gold_disc8_ai_block_numeric_miss_by_strategy_tag.csv','feature_probe':run/'gold_disc8_ai_block_numeric_miss_feature_probe.csv','summary':run/'gold_disc8_ai_block_numeric_miss_summary.json'}
    wcsv(paths['input_audit'],input_audit,FILE_AUDIT_COLS)
    if not resolve(a.trade_audit_csv).exists():
        s={'schema_version':SCHEMA_VERSION,'cycle_ok':False,'reason':'STOP_MISSING_TRADE_AUDIT_CSV','run_id':run_id,'created_at':now_text(),'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_forced_false':True,'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 2
    trade=read_csv(a.trade_audit_csv,'trade audit')
    problems=[]; req=['trade_id','strategy_id','entry_time','entry_month','ai_decision','confusion_class','profit_r_num','ai_tags','dispatch_ready']
    for c in req:
        if c not in trade.columns: problems.append(f'trade_audit missing {c}')
    if len(trade)!=a.expected_trade_rows: problems.append(f'trade_audit rows expected {a.expected_trade_rows}, actual {len(trade)}')
    if 'dispatch_ready' in trade.columns and trade['dispatch_ready'].astype(str).str.lower().isin(['true','1','yes']).any(): problems.append('dispatch_ready true row exists')
    if problems:
        s={'schema_version':SCHEMA_VERSION,'cycle_ok':False,'reason':'STOP_TRADE_AUDIT_CONTRACT_FAILED','run_id':run_id,'created_at':now_text(),'problems':problems,'counts':{'trade_audit_rows':len(trade)},'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_forced_false':True,'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 3
    miss=trade[trade['confusion_class'].astype(str).map(clean).eq('AI_BLOCK_AND_NUMERIC_ALLOW')].copy()
    miss['profit_r_num']=pd.to_numeric(miss['profit_r_num'],errors='coerce').fillna(0.0)
    mrows=miss.to_dict('records'); tags=tag_rows_from_misses(miss); tag_sum,stag_sum=tag_summary(tags)
    month=[]
    for mo in sorted(miss['entry_month'].astype(str).map(clean).unique()): month += summarize([r for r in mrows if clean(r.get('entry_month'))==mo],'month',mo)
    strat=[]
    for sid in sorted(miss['strategy_id'].astype(str).map(clean).unique()): strat += summarize([r for r in mrows if clean(r.get('strategy_id'))==sid],'strategy',sid)
    feature=read_csv(a.trade_feature_snapshot_csv,'feature snapshot',required=False)
    probe=feature_probe(trade,feature,tags,a.min_tag_rows,a.min_feature_non_null,a.max_probe_rows_per_tag)
    wcsv(paths['missed_trades'],mrows,list(trade.columns)); wcsv(paths['missed_by_month'],month,SUMMARY_COLS); wcsv(paths['missed_by_strategy'],strat,SUMMARY_COLS); wcsv(paths['missed_by_tag'],tag_sum,TAG_COLS); wcsv(paths['missed_by_strategy_tag'],stag_sum,STAG_COLS); wcsv(paths['feature_probe'],probe,PROBE_COLS)
    rv=[float(r.get('profit_r_num') or 0.0) for r in mrows]; met=metrics(rv)
    top_tags=tag_sum[:12]; top_stag=stag_sum[:12]
    s={'schema_version':SCHEMA_VERSION,'cycle_ok':True,'reason':'OK_AUDIT_ONLY_AI_BLOCK_NUMERIC_ALLOW_MISS_ANALYSIS','run_id':run_id,'created_at':now_text(),'source_of_truth':'replay trade_audit.csv; no OHLC rediscovery; feature_snapshot only for optional audit probe','no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_forced_false':True,'dispatch_ready_rows':0,'counts':{'trade_audit_rows':len(trade),'missed_ai_block_numeric_allow_rows':len(miss),'missed_tag_rows':len(tags),'missed_tag_summary_rows':len(tag_sum),'missed_strategy_tag_rows':len(stag_sum),'feature_probe_rows':len(probe),'feature_snapshot_rows':len(feature)},'missed_performance':{'trade_count':met['trade_count'],'win_count':met['win_count'],'loss_count':met['loss_count'],'win_rate':fm(met['win_rate']),'profit_factor':fm(met['profit_factor']),'avg_r':fm(met['avg_r']),'total_r':fm(met['total_r'])},'most_negative_tags':top_tags,'most_negative_strategy_tags':top_stag,'outputs':{k:str(v) for k,v in paths.items()},'do_not_execute':'Do not promote probes to runtime gate. Do not enable dispatch_ready/Discord/MT5/OpenAI from this audit.'}
    wjson(paths['summary'],s)
    if a.write_latest_copy:
        if latest.exists(): shutil.rmtree(windows_long_path(latest))
        mkdirp(latest)
        for p in paths.values(): shutil.copy2(windows_long_path(p),windows_long_path(latest/p.name))
    print(json.dumps(s,ensure_ascii=False,indent=2,sort_keys=True,default=str)); return 0

if __name__=='__main__': raise SystemExit(main())
