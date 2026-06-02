#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, csv, json, shutil, sys
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

SCHEMA_VERSION='gold_disc8_top3_candidate_rule_replay_568_v1_audit_only'
DEFAULT_TRADE_AUDIT=Path('data/runtime_logs/gold_disc8_ai_tag_vs_numeric_gate_replay_568/latest/gold_disc8_ai_tag_vs_numeric_gate_replay_568_trade_audit.csv')
DEFAULT_FEATURE=Path('data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/trade_feature_snapshot.csv')
DEFAULT_PROBE=Path('data/runtime_logs/gold_disc8_ai_block_numeric_miss_analysis_568/latest/gold_disc8_ai_block_numeric_miss_feature_probe.csv')
DEFAULT_OUT_ROOT=Path('data/runtime_logs/gold_disc8_top3_candidate_rule_replay_568')
DEFAULT_STRATEGIES='DISC_08_BUY_TP200_SL100_RR2,DISC_01_BUY_TP200_SL100_RR2,DISC_09_BUY_TP80_SL50_RR1p6'
EXPECTED_ROWS=568
FILE_AUDIT_COLS='label path exists rows columns required status note'.split()
RULE_COLS='rule_id source_rank strategy_id tag_group tag_name feature op threshold probe_hit_rows missed_tag_capture_rate ai_allow_false_hit_rate precision_to_missed_tag hit_total_r source_note'.split()
HIT_COLS='rule_id trade_id strategy_id direction entry_time entry_month ai_decision original_numeric_gate_decision confusion_class profit_r_num win_loss_flat tag_group tag_name feature op threshold value'.split()
TRADE_COLS='trade_id strategy_id direction entry_time entry_month ai_decision original_numeric_gate_decision original_confusion_class candidate_replay_decision candidate_hit_count candidate_rule_ids candidate_tags profit_r_num win_loss_flat dispatch_ready'.split()
SUMMARY_COLS='group key bucket trade_count win_count loss_count flat_count win_rate profit_factor avg_r total_r ai_block_count ai_allow_count candidate_block_count candidate_allow_count false_block_count captured_ai_block_count'.split()
RULE_SUMMARY_COLS='rule_id strategy_id tag_group tag_name feature op threshold hit_count win_count loss_count flat_count win_rate profit_factor avg_r total_r ai_block_hit_count ai_allow_hit_count ai_allow_false_hit_rate ai_block_capture_count precision_vs_ai_block note'.split()

def now_text(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def run_id_text(): return datetime.now().strftime('%Y%m%d_%H%M%S')
def mkdirp(p:Path): Path(windows_long_path(p)).mkdir(parents=True, exist_ok=True)
def wjson(p:Path,o:dict[str,Any]): mkdirp(p.parent); open(windows_long_path(p),'w',encoding='utf-8').write(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True,default=str))
def wcsv(p:Path,rows:list[dict[str,Any]],cols:list[str]):
    mkdirp(p.parent)
    with open(windows_long_path(p),'w',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore'); wr.writeheader()
        for r in rows: wr.writerow({c:r.get(c,'') for c in cols})

def read_csv(path:Path,label:str)->pd.DataFrame:
    p=resolve(path)
    if not p.exists(): raise FileNotFoundError(f'{label} not found: {p}')
    return pd.read_csv(windows_long_path(p),encoding='utf-8-sig',sep=None,engine='python')

def audit_file(label:str,path:Path,required:bool,note:str)->dict[str,Any]:
    p=resolve(path); r={'label':label,'path':str(p),'exists':p.exists(),'rows':'','columns':'','required':required,'status':'OK' if p.exists() else ('MISSING_REQUIRED' if required else 'MISSING_OPTIONAL'),'note':note}
    if p.exists() and p.suffix.lower()=='.csv':
        try:
            df=pd.read_csv(windows_long_path(p),encoding='utf-8-sig',sep=None,engine='python'); r['rows']=len(df); r['columns']=' | '.join(map(str,df.columns))
        except Exception as e: r['status']='READ_ERROR'; r['note']=f'{note}; {type(e).__name__}: {e}'
    return r

def fnum(x:Any, default:float|None=None)->float|None:
    y=safe_float(x)
    return default if y is None else float(y)

def wl(x:float)->str: return 'WIN' if x>0 else ('LOSS' if x<0 else 'FLAT_OR_UNRESOLVED')
def rval(row:Any)->float:
    x=fnum(row.get('profit_r_num'),0.0)
    return 0.0 if x is None else float(x)

def op_match(v:float,op:str,thr:float)->bool:
    if op=='<=': return v<=thr
    if op=='>=': return v>=thr
    if op=='<': return v<thr
    if op=='>': return v>thr
    return False

def select_rules(probe:pd.DataFrame,args:argparse.Namespace)->list[dict[str,Any]]:
    strategies={clean(x) for x in args.strategies.split(',') if clean(x)}
    rows=[]
    need=['strategy_id','tag_group','tag_name','feature','op','threshold','probe_hit_rows','missed_tag_capture_rate','ai_allow_false_hit_rate','precision_to_missed_tag','hit_total_r']
    for c in need:
        if c not in probe.columns: raise RuntimeError(f'feature_probe missing column: {c}')
    for i,r in probe.iterrows():
        sid=clean(r.get('strategy_id')); group=clean(r.get('tag_group'))
        if sid not in strategies or group!=args.tag_group: continue
        hit=fnum(r.get('probe_hit_rows'),0) or 0
        cap=fnum(r.get('missed_tag_capture_rate'),0) or 0
        false=fnum(r.get('ai_allow_false_hit_rate'),999) or 999
        prec=fnum(r.get('precision_to_missed_tag'),0) or 0
        tr=fnum(r.get('hit_total_r'),0) or 0
        if hit < args.min_probe_hit_rows: continue
        if cap < args.min_missed_tag_capture_rate: continue
        if false > args.max_ai_allow_false_hit_rate: continue
        if prec < args.min_precision_to_missed_tag: continue
        if tr >= args.max_hit_total_r: continue
        feat=clean(r.get('feature')); op=clean(r.get('op')); thr=fnum(r.get('threshold'))
        if not feat or not op or thr is None: continue
        rid=f'{sid}:{group}:{clean(r.get("tag_name"))}:{feat}:{op}:{fm(thr)}'
        rows.append({'rule_id':rid,'source_rank':i+1,'strategy_id':sid,'tag_group':group,'tag_name':clean(r.get('tag_name')),'feature':feat,'op':op,'threshold':fm(thr),'probe_hit_rows':int(hit),'missed_tag_capture_rate':fm(cap),'ai_allow_false_hit_rate':fm(false),'precision_to_missed_tag':fm(prec),'hit_total_r':fm(tr),'source_note':'FROM_MISS_FEATURE_PROBE_AUDIT_ONLY'})
    # de-duplicate exact rules while preserving best source order
    out=[]; seen=set()
    for r in rows:
        k=(r['strategy_id'],r['tag_group'],r['tag_name'],r['feature'],r['op'],str(r['threshold']))
        if k in seen: continue
        seen.add(k); out.append(r)
    return out

def metric_row(rows:list[dict[str,Any]], group:str, key:str, bucket:str)->dict[str,Any]:
    vals=[float(r.get('profit_r_num') or 0.0) for r in rows]; m=metrics(vals); n=len(rows)
    return {'group':group,'key':key,'bucket':bucket,'trade_count':n,'win_count':sum(v>0 for v in vals),'loss_count':sum(v<0 for v in vals),'flat_count':sum(v==0 for v in vals),'win_rate':fm(m['win_rate']),'profit_factor':fm(m['profit_factor']),'avg_r':fm(m['avg_r']),'total_r':fm(m['total_r']),'ai_block_count':sum(r.get('ai_decision')=='AI_BLOCK' for r in rows),'ai_allow_count':sum(r.get('ai_decision')=='AI_ALLOW' for r in rows),'candidate_block_count':sum(r.get('candidate_replay_decision')=='BLOCK' for r in rows),'candidate_allow_count':sum(r.get('candidate_replay_decision')!='BLOCK' for r in rows),'false_block_count':sum(r.get('ai_decision')=='AI_ALLOW' and r.get('candidate_replay_decision')=='BLOCK' for r in rows),'captured_ai_block_count':sum(r.get('ai_decision')=='AI_BLOCK' and r.get('candidate_replay_decision')=='BLOCK' for r in rows)}

def summaries(rows:list[dict[str,Any]])->tuple[list[dict[str,Any]],list[dict[str,Any]],list[dict[str,Any]]]:
    def build(group,key,sub):
        out=[metric_row(sub,group,key,'ALL')]
        for b in ['BLOCK','ALLOW']:
            out.append(metric_row([r for r in sub if ('BLOCK' if r.get('candidate_replay_decision')=='BLOCK' else 'ALLOW')==b],group,key,b))
        return out
    overall=build('overall','ALL',rows)
    monthly=[]
    for m in sorted({clean(r.get('entry_month')) for r in rows}): monthly+=build('month',m,[r for r in rows if clean(r.get('entry_month'))==m])
    strategy=[]
    for s in sorted({clean(r.get('strategy_id')) for r in rows}): strategy+=build('strategy',s,[r for r in rows if clean(r.get('strategy_id'))==s])
    return overall,monthly,strategy

def replay(trade:pd.DataFrame, feature:pd.DataFrame, rules:list[dict[str,Any]])->tuple[list[dict[str,Any]],list[dict[str,Any]],list[dict[str,Any]]]:
    t=trade.copy(); t['trade_id']=t['trade_id'].map(clean)
    f=feature.copy(); f['trade_id']=f['trade_id'].map(clean); f=f.drop_duplicates('trade_id',keep='last')
    df=t.merge(f,on='trade_id',how='left',suffixes=('','_feat'))
    hit_rows=[]; hit_by_tid:dict[str,list[dict[str,Any]]]={}
    for rule in rules:
        feat=rule['feature']; op=rule['op']; thr=fnum(rule['threshold'])
        if thr is None or feat not in df.columns: continue
        for _,row in df[df['strategy_id'].astype(str).map(clean).eq(rule['strategy_id'])].iterrows():
            val=fnum(row.get(feat))
            if val is None or not op_match(val,op,thr): continue
            pr=rval(row); tid=clean(row.get('trade_id'))
            h={'rule_id':rule['rule_id'],'trade_id':tid,'strategy_id':clean(row.get('strategy_id')),'direction':clean(row.get('direction')),'entry_time':clean(row.get('entry_time')),'entry_month':clean(row.get('entry_month')),'ai_decision':clean(row.get('ai_decision')),'original_numeric_gate_decision':clean(row.get('numeric_gate_decision')),'confusion_class':clean(row.get('confusion_class')),'profit_r_num':fm(pr),'win_loss_flat':wl(pr),'tag_group':rule['tag_group'],'tag_name':rule['tag_name'],'feature':feat,'op':op,'threshold':rule['threshold'],'value':fm(val)}
            hit_rows.append(h); hit_by_tid.setdefault(tid,[]).append(h)
    combined=[]
    for _,row in t.iterrows():
        tid=clean(row.get('trade_id')); hs=hit_by_tid.get(tid,[]); pr=rval(row)
        combined.append({'trade_id':tid,'strategy_id':clean(row.get('strategy_id')),'direction':clean(row.get('direction')),'entry_time':clean(row.get('entry_time')),'entry_month':clean(row.get('entry_month')),'ai_decision':clean(row.get('ai_decision')),'original_numeric_gate_decision':clean(row.get('numeric_gate_decision')),'original_confusion_class':clean(row.get('confusion_class')),'candidate_replay_decision':'BLOCK' if hs else 'ALLOW','candidate_hit_count':len(hs),'candidate_rule_ids':' | '.join(sorted({h['rule_id'] for h in hs})),'candidate_tags':' | '.join(sorted({h['tag_group']+':'+h['tag_name'] for h in hs})),'profit_r_num':fm(pr),'win_loss_flat':wl(pr),'dispatch_ready':False})
    rule_summary=[]
    for rule in rules:
        sub=[h for h in hit_rows if h['rule_id']==rule['rule_id']]
        vals=[float(h['profit_r_num'] or 0.0) for h in sub]; m=metrics(vals); n=len(sub)
        ai_block=sum(h['ai_decision']=='AI_BLOCK' for h in sub); ai_allow=sum(h['ai_decision']=='AI_ALLOW' for h in sub)
        rule_summary.append({'rule_id':rule['rule_id'],'strategy_id':rule['strategy_id'],'tag_group':rule['tag_group'],'tag_name':rule['tag_name'],'feature':rule['feature'],'op':rule['op'],'threshold':rule['threshold'],'hit_count':n,'win_count':sum(v>0 for v in vals),'loss_count':sum(v<0 for v in vals),'flat_count':sum(v==0 for v in vals),'win_rate':fm(m['win_rate']),'profit_factor':fm(m['profit_factor']),'avg_r':fm(m['avg_r']),'total_r':fm(m['total_r']),'ai_block_hit_count':ai_block,'ai_allow_hit_count':ai_allow,'ai_allow_false_hit_rate':fm(None if n==0 else ai_allow/n),'ai_block_capture_count':ai_block,'precision_vs_ai_block':fm(None if n==0 else ai_block/n),'note':'AUDIT_ONLY_NOT_RUNTIME_RULE'})
    rule_summary=sorted(rule_summary,key=lambda r:(float(r['total_r'] or 0),-int(r['hit_count'] or 0)))
    return combined,hit_rows,rule_summary

def parse_args():
    p=argparse.ArgumentParser(description='Replay top-3 DISC8 candidate numeric miss rules over 568 SOT trades. Audit-only.')
    p.add_argument('--trade-audit-csv',type=Path,default=DEFAULT_TRADE_AUDIT)
    p.add_argument('--trade-feature-snapshot-csv',type=Path,default=DEFAULT_FEATURE)
    p.add_argument('--feature-probe-csv',type=Path,default=DEFAULT_PROBE)
    p.add_argument('--out-root',type=Path,default=DEFAULT_OUT_ROOT)
    p.add_argument('--run-id',default='')
    p.add_argument('--strategies',default=DEFAULT_STRATEGIES)
    p.add_argument('--tag-group',default='risk')
    p.add_argument('--expected-trade-rows',type=int,default=EXPECTED_ROWS)
    p.add_argument('--min-probe-hit-rows',type=int,default=5)
    p.add_argument('--min-missed-tag-capture-rate',type=float,default=0.40)
    p.add_argument('--max-ai-allow-false-hit-rate',type=float,default=0.15)
    p.add_argument('--min-precision-to-missed-tag',type=float,default=0.60)
    p.add_argument('--max-hit-total-r',type=float,default=-0.000001)
    p.add_argument('--no-latest-copy',action='store_false',dest='write_latest_copy',default=True)
    return p.parse_args()

def main()->int:
    a=parse_args(); run_id=a.run_id or run_id_text(); root=resolve(a.out_root); run=root/'runs'/run_id; latest=root/'latest'; mkdirp(run)
    paths={'input_audit':run/'gold_disc8_top3_candidate_rule_replay_input_audit.csv','candidate_rules':run/'gold_disc8_top3_candidate_rule_replay_candidate_rules.csv','trade_audit':run/'gold_disc8_top3_candidate_rule_replay_trade_audit.csv','rule_hit_detail':run/'gold_disc8_top3_candidate_rule_replay_rule_hit_detail.csv','rule_summary':run/'gold_disc8_top3_candidate_rule_replay_rule_summary.csv','overall':run/'gold_disc8_top3_candidate_rule_replay_overall_summary.csv','monthly':run/'gold_disc8_top3_candidate_rule_replay_monthly_summary.csv','strategy':run/'gold_disc8_top3_candidate_rule_replay_strategy_summary.csv','summary':run/'gold_disc8_top3_candidate_rule_replay_summary.json'}
    ia=[audit_file('trade_audit_csv',a.trade_audit_csv,True,'568 replay trade audit SOT'),audit_file('trade_feature_snapshot_csv',a.trade_feature_snapshot_csv,True,'pre-entry feature snapshot'),audit_file('feature_probe_csv',a.feature_probe_csv,True,'miss-analysis candidate feature probe')]
    wcsv(paths['input_audit'],ia,FILE_AUDIT_COLS)
    miss=[r for r in ia if r['required'] and not r['exists']]
    if miss:
        s={'schema_version':SCHEMA_VERSION,'cycle_ok':False,'reason':'STOP_MISSING_REQUIRED_INPUT_FILES','run_id':run_id,'created_at':now_text(),'missing_required_labels':[r['label'] for r in miss],'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_forced_false':True,'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 2
    trade=read_csv(a.trade_audit_csv,'trade audit'); feature=read_csv(a.trade_feature_snapshot_csv,'feature snapshot'); probe=read_csv(a.feature_probe_csv,'feature probe')
    problems=[]
    for c in ['trade_id','strategy_id','entry_time','entry_month','ai_decision','numeric_gate_decision','confusion_class','profit_r_num','dispatch_ready']:
        if c not in trade.columns: problems.append(f'trade_audit missing {c}')
    if 'trade_id' not in feature.columns: problems.append('feature_snapshot missing trade_id')
    if len(trade)!=a.expected_trade_rows: problems.append(f'trade_audit rows expected {a.expected_trade_rows}, actual {len(trade)}')
    if 'dispatch_ready' in trade.columns and trade['dispatch_ready'].astype(str).str.lower().isin(['true','1','yes']).any(): problems.append('dispatch_ready true row exists')
    if problems:
        s={'schema_version':SCHEMA_VERSION,'cycle_ok':False,'reason':'STOP_INPUT_CONTRACT_FAILED','run_id':run_id,'created_at':now_text(),'problems':problems,'counts':{'trade_audit_rows':len(trade),'feature_rows':len(feature),'probe_rows':len(probe)},'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_forced_false':True,'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 3
    rules=select_rules(probe,a); wcsv(paths['candidate_rules'],rules,RULE_COLS)
    if not rules:
        s={'schema_version':SCHEMA_VERSION,'cycle_ok':False,'reason':'STOP_NO_CANDIDATE_RULES_AFTER_FILTER','run_id':run_id,'created_at':now_text(),'filters':vars(a),'counts':{'trade_audit_rows':len(trade),'feature_rows':len(feature),'probe_rows':len(probe),'candidate_rules':0},'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_forced_false':True,'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 4
    combined,hits,rule_sum=replay(trade,feature,rules); overall,monthly,strategy=summaries(combined)
    wcsv(paths['trade_audit'],combined,TRADE_COLS); wcsv(paths['rule_hit_detail'],hits,HIT_COLS); wcsv(paths['rule_summary'],rule_sum,RULE_SUMMARY_COLS); wcsv(paths['overall'],overall,SUMMARY_COLS); wcsv(paths['monthly'],monthly,SUMMARY_COLS); wcsv(paths['strategy'],strategy,SUMMARY_COLS)
    vals=[float(r['profit_r_num'] or 0.0) for r in combined if r['candidate_replay_decision']=='BLOCK']; bm=metrics(vals)
    total_block=sum(r['candidate_replay_decision']=='BLOCK' for r in combined); captured=sum(r['candidate_replay_decision']=='BLOCK' and r['ai_decision']=='AI_BLOCK' for r in combined); false=sum(r['candidate_replay_decision']=='BLOCK' and r['ai_decision']=='AI_ALLOW' for r in combined)
    s={'schema_version':SCHEMA_VERSION,'cycle_ok':True,'reason':'OK_AUDIT_ONLY_TOP3_CANDIDATE_RULE_REPLAY_568','run_id':run_id,'created_at':now_text(),'source_of_truth':'trade_audit.csv + trade_feature_snapshot.csv + feature_probe.csv; no OHLC rediscovery; no AI review','target_strategies':[clean(x) for x in a.strategies.split(',') if clean(x)],'tag_group':a.tag_group,'filters':{'min_probe_hit_rows':a.min_probe_hit_rows,'min_missed_tag_capture_rate':a.min_missed_tag_capture_rate,'max_ai_allow_false_hit_rate':a.max_ai_allow_false_hit_rate,'min_precision_to_missed_tag':a.min_precision_to_missed_tag,'max_hit_total_r':a.max_hit_total_r},'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_forced_false':True,'dispatch_ready_rows':0,'counts':{'trade_audit_rows':len(trade),'feature_rows':len(feature),'probe_rows':len(probe),'candidate_rules':len(rules),'rule_hit_rows':len(hits),'candidate_block_rows':total_block,'captured_ai_block_rows':captured,'false_block_ai_allow_rows':false,'candidate_allow_rows':len(combined)-total_block},'candidate_block_performance':{'trade_count':bm['trade_count'],'win_count':bm['win_count'],'loss_count':bm['loss_count'],'win_rate':fm(bm['win_rate']),'profit_factor':fm(bm['profit_factor']),'avg_r':fm(bm['avg_r']),'total_r':fm(bm['total_r'])},'classification_metrics':{'precision_vs_ai_block':fm(None if total_block==0 else captured/total_block),'ai_allow_false_block_rate_all_568':fm(false/len(combined)),'captured_ai_block_rows':captured},'outputs':{k:str(v) for k,v in paths.items()},'do_not_execute':'Candidate rows are audit probes only. Do not promote to runtime gate or enable dispatch_ready/Discord/MT5/OpenAI from this output.'}
    wjson(paths['summary'],s)
    if a.write_latest_copy:
        if latest.exists(): shutil.rmtree(windows_long_path(latest))
        mkdirp(latest)
        for p in paths.values(): shutil.copy2(windows_long_path(p),windows_long_path(latest/p.name))
    print(json.dumps(s,ensure_ascii=False,indent=2,sort_keys=True,default=str)); return 0

if __name__=='__main__': raise SystemExit(main())
