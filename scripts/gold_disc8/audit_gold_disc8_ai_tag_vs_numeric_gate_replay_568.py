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

from build_gold_disc8_ai_tag_numeric_tagger_from_review import (  # noqa:E402
    DEFAULT_AI_REVIEW_LEDGER_JSONL, DEFAULT_BASE_TRADE_CSV, DEFAULT_GATE_RULES_JSON,
    DEFAULT_KEPT_LEDGER_CSV, DEFAULT_TRADE_FEATURE_SNAPSHOT_CSV, apply_rules, clean,
    expand_review_tags, fm, gate_target_tags, load_jsonl, merge_universe, metrics,
    read_csv_required, read_json, resolve, trade_r, windows_long_path,
)
from backtest_gold_disc8_live_decision_numeric_tagger_audit import (  # noqa:E402
    DEFAULT_NUMERIC_RULES_JSON, DEFAULT_TAG_RECALL_CSV, load_numeric_rules, load_promotable_tags,
)
from gold_disc8_feature_contract_bridge import filter_pre_entry_rules  # noqa:E402

SCHEMA_VERSION='gold_disc8_ai_tag_vs_numeric_gate_replay_568_v1_audit_only'
DEFAULT_OUT_ROOT=Path('data/runtime_logs/gold_disc8_ai_tag_vs_numeric_gate_replay_568')
EXPECTED_BASE_ROWS=568
TRADE_COLS='schema_version run_id trade_id strategy_id direction entry_time entry_month ai_decision numeric_gate_decision confusion_class profit_r_num win_loss_flat ai_tags numeric_tag_hits dispatch_ready'.split()
SUM_COLS='group key bucket trade_count win_count loss_count flat_count win_rate profit_factor avg_r total_r ai_block_count ai_allow_count numeric_block_count numeric_allow_count'.split()
HIT_COLS='trade_id strategy_id tag_group tag_name configured_action rule_id feature op threshold value'.split()
RECALL_COLS='strategy_id tag_group tag_name configured_action ai_tag_trade_count numeric_hit_trade_count true_positive_tag_count false_positive_numeric_count false_negative_ai_count precision_vs_ai_tag recall_vs_ai_tag ai_block_trade_count ai_block_recalled_by_numeric_count ai_block_recall_by_numeric ai_allow_false_numeric_hit_count ai_allow_false_numeric_hit_rate numeric_hit_total_r numeric_hit_profit_factor'.split()
FILE_AUDIT_COLS='label path exists rows columns required status note'.split()


def now_text(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def run_id_text(): return datetime.now().strftime('%Y%m%d_%H%M%S')
def mkdirp(p:Path): Path(windows_long_path(p)).mkdir(parents=True, exist_ok=True)
def wjson(p:Path,o:dict[str,Any]): mkdirp(p.parent); open(windows_long_path(p),'w',encoding='utf-8').write(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True,default=str))
def wcsv(p:Path,rows:list[dict[str,Any]],cols:list[str]):
    mkdirp(p.parent)
    with open(windows_long_path(p),'w',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore'); wr.writeheader()
        for r in rows: wr.writerow({c:r.get(c,'') for c in cols})

def audit_file(label:str,path:Path,required:bool,note:str)->dict[str,Any]:
    p=resolve(path); r={'label':label,'path':str(p),'exists':p.exists(),'rows':'','columns':'','required':required,'status':'OK' if p.exists() else ('MISSING_REQUIRED' if required else 'MISSING_OPTIONAL'),'note':note}
    if p.exists() and p.suffix.lower()=='.csv':
        try:
            df=pd.read_csv(windows_long_path(p),encoding='utf-8-sig',sep=None,engine='python'); r['rows']=len(df); r['columns']=' | '.join(map(str,df.columns))
        except Exception as e: r['status']='READ_ERROR'; r['note']=f'{note}; {type(e).__name__}: {e}'
    elif p.exists() and p.suffix.lower()=='.jsonl':
        with open(windows_long_path(p),'r',encoding='utf-8-sig') as f: r['rows']=sum(1 for line in f if line.strip())
    return r

def wl(x:float)->str:
    return 'WIN' if x>0 else ('LOSS' if x<0 else 'FLAT_OR_UNRESOLVED')

def cls(old:str)->str:
    return {'true_positive_blocked':'AI_BLOCK_AND_NUMERIC_BLOCK','false_negative_missed_block':'AI_BLOCK_AND_NUMERIC_ALLOW','false_positive_wrong_block':'AI_ALLOW_AND_NUMERIC_BLOCK','true_negative_kept':'AI_ALLOW_AND_NUMERIC_ALLOW'}.get(clean(old),clean(old))

def summarize(rows:list[dict[str,Any]], group:str, key:str, by:str)->list[dict[str,Any]]:
    buckets=['ALL']+sorted({clean(r.get(by)) for r in rows if clean(r.get(by))})
    out=[]
    for b in buckets:
        sub=rows if b=='ALL' else [r for r in rows if clean(r.get(by))==b]
        vals=[float(r.get('profit_r_num') or 0.0) for r in sub]; m=metrics(vals); n=len(sub)
        out.append({'group':group,'key':key,'bucket':b,'trade_count':n,'win_count':sum(v>0 for v in vals),'loss_count':sum(v<0 for v in vals),'flat_count':sum(v==0 for v in vals),'win_rate':fm(m['win_rate']),'profit_factor':fm(m['profit_factor']),'avg_r':fm(m['avg_r']),'total_r':fm(m['total_r']),'ai_block_count':sum(r.get('ai_decision')=='AI_BLOCK' for r in sub),'ai_allow_count':sum(r.get('ai_decision')=='AI_ALLOW' for r in sub),'numeric_block_count':sum(r.get('numeric_gate_decision')=='BLOCK' for r in sub),'numeric_allow_count':sum(r.get('numeric_gate_decision')!='BLOCK' for r in sub)})
    return out

def all_summaries(rows:list[dict[str,Any]])->tuple[list[dict[str,Any]],list[dict[str,Any]],list[dict[str,Any]]]:
    overall=summarize(rows,'overall','ALL','confusion_class')
    monthly=[]
    for m in sorted({clean(r.get('entry_month')) for r in rows}): monthly += summarize([r for r in rows if clean(r.get('entry_month'))==m],'month',m,'confusion_class')
    strategy=[]
    for s in sorted({clean(r.get('strategy_id')) for r in rows}): strategy += summarize([r for r in rows if clean(r.get('strategy_id'))==s],'strategy',s,'confusion_class')
    return overall,monthly,strategy

def tag_recall(universe:pd.DataFrame, tag_df:pd.DataFrame, hits:list[dict[str,Any]], targets:dict[tuple[str,str,str],str])->list[dict[str,Any]]:
    ai={(clean(r.trade_id),clean(r.strategy_id),clean(r.tag_group),clean(r.tag_name)) for r in tag_df.itertuples(index=False)} if not tag_df.empty else set()
    nh={(clean(h.get('trade_id')),clean(h.get('strategy_id')),clean(h.get('tag_group')),clean(h.get('tag_name'))) for h in hits}
    out=[]
    for (sid,g,t),act in sorted(targets.items()):
        sdf=universe[universe.strategy_id.astype(str).map(clean)==sid]
        ids={clean(x) for x in sdf.trade_id.tolist() if clean(x)}; a={i for i in ids if (i,sid,g,t) in ai}; n={i for i in ids if (i,sid,g,t) in nh}
        b={clean(r.trade_id) for r in sdf.itertuples(index=False) if clean(getattr(r,'truth_label',''))=='actual_blocked'}; k={clean(r.trade_id) for r in sdf.itertuples(index=False) if clean(getattr(r,'truth_label',''))=='actual_kept'}
        vals=[trade_r(row) for _,row in sdf[sdf.trade_id.astype(str).map(clean).isin(n)].iterrows()]; m=metrics(vals)
        out.append({'strategy_id':sid,'tag_group':g,'tag_name':t,'configured_action':act,'ai_tag_trade_count':len(a),'numeric_hit_trade_count':len(n),'true_positive_tag_count':len(a&n),'false_positive_numeric_count':len(n-a),'false_negative_ai_count':len(a-n),'precision_vs_ai_tag':fm(None if not n else len(a&n)/len(n)),'recall_vs_ai_tag':fm(None if not a else len(a&n)/len(a)),'ai_block_trade_count':len(b),'ai_block_recalled_by_numeric_count':len(b&n),'ai_block_recall_by_numeric':fm(None if not b else len(b&n)/len(b)),'ai_allow_false_numeric_hit_count':len(k&n),'ai_allow_false_numeric_hit_rate':fm(None if not k else len(k&n)/len(k)),'numeric_hit_total_r':fm(m['total_r']),'numeric_hit_profit_factor':fm(m['profit_factor'])})
    return out

def parse_args():
    p=argparse.ArgumentParser(description='Audit-only DISC8 AI tag SOT vs numeric gate replay on 568 reviewed trades.')
    p.add_argument('--ai-review-ledger-jsonl',type=Path,default=DEFAULT_AI_REVIEW_LEDGER_JSONL); p.add_argument('--trade-feature-snapshot-csv',type=Path,default=DEFAULT_TRADE_FEATURE_SNAPSHOT_CSV)
    p.add_argument('--base-trade-csv',type=Path,default=DEFAULT_BASE_TRADE_CSV); p.add_argument('--kept-ledger-csv',type=Path,default=DEFAULT_KEPT_LEDGER_CSV); p.add_argument('--gate-rules-json',type=Path,default=DEFAULT_GATE_RULES_JSON)
    p.add_argument('--numeric-rules-json',type=Path,default=DEFAULT_NUMERIC_RULES_JSON); p.add_argument('--tag-recall-csv',type=Path,default=DEFAULT_TAG_RECALL_CSV); p.add_argument('--out-root',type=Path,default=DEFAULT_OUT_ROOT)
    p.add_argument('--run-id',default=''); p.add_argument('--expected-base-rows',type=int,default=EXPECTED_BASE_ROWS); p.add_argument('--promotable-only',action='store_true',default=True); p.add_argument('--all-rules',action='store_false',dest='promotable_only'); p.add_argument('--no-latest-copy',action='store_false',dest='write_latest_copy',default=True)
    return p.parse_args()

def main()->int:
    a=parse_args(); run_id=a.run_id or run_id_text(); out=resolve(a.out_root); run=out/'runs'/run_id; latest=out/'latest'; mkdirp(run)
    inputs=[('ai_review_ledger_jsonl',a.ai_review_ledger_jsonl,True,'actual AI tag ledger'),('trade_feature_snapshot_csv',a.trade_feature_snapshot_csv,True,'pre-entry features'),('base_trade_csv',a.base_trade_csv,True,'568 universe'),('kept_ledger_csv',a.kept_ledger_csv,True,'frozen kept SOT'),('gate_rules_json',a.gate_rules_json,True,'AI tag gate targets'),('numeric_rules_json',a.numeric_rules_json,True,'numeric rules'),('tag_recall_csv',a.tag_recall_csv,False,'promotable tag summary')]
    fa=[audit_file(*x) for x in inputs]; file_audit=run/'gold_disc8_ai_tag_vs_numeric_gate_input_file_audit.csv'; wcsv(file_audit,fa,FILE_AUDIT_COLS)
    miss=[r for r in fa if r['required'] and not r['exists']]
    summary_path=run/'gold_disc8_ai_tag_vs_numeric_gate_replay_summary.json'
    if miss:
        s={'schema_version':SCHEMA_VERSION,'cycle_ok':False,'reason':'STOP_MISSING_REQUIRED_INPUT_FILES','run_id':run_id,'created_at':now_text(),'missing_required_labels':[r['label'] for r in miss],'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_forced_false':True,'input_audit_csv':str(file_audit)}; wjson(summary_path,s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 2
    base=read_csv_required(a.base_trade_csv,'base 568 trade CSV'); feat=read_csv_required(a.trade_feature_snapshot_csv,'trade_feature_snapshot CSV'); kept=read_csv_required(a.kept_ledger_csv,'kept SOT ledger CSV')
    reviews=load_jsonl(a.ai_review_ledger_jsonl); tags=expand_review_tags(reviews,base); targets=gate_target_tags(read_json(a.gate_rules_json)); raw=load_numeric_rules(a.numeric_rules_json); rules,excluded=filter_pre_entry_rules(raw); allowed=load_promotable_tags(a.tag_recall_csv,promotable_only=a.promotable_only)
    if allowed is not None: rules=[r for r in rules if (clean(r.get('strategy_id')),clean(r.get('tag_group')),clean(r.get('tag_name'))) in allowed]
    universe=merge_universe(base,feat,kept)
    problems=[]
    if len(base)!=a.expected_base_rows: problems.append(f'base_trade_rows expected {a.expected_base_rows}, actual {len(base)}')
    for name,df in [('base',base),('feature',feat),('kept',kept)]:
        if 'trade_id' not in df.columns: problems.append(f'{name} missing trade_id')
    if 'strategy_id' not in universe.columns: problems.append('merged universe missing strategy_id')
    if 'profit_r_num' not in universe.columns and 'profit_r' not in universe.columns: problems.append('merged universe missing profit_r_num/profit_r')
    if not targets: problems.append('gate target tags are zero')
    if not raw: problems.append('raw numeric rules are zero')
    if not rules: problems.append('numeric rules after filters are zero')
    if problems:
        s={'schema_version':SCHEMA_VERSION,'cycle_ok':False,'reason':'STOP_INPUT_OR_RULE_AUDIT_FAILED','run_id':run_id,'created_at':now_text(),'problems':problems,'counts':{'base_trade_rows':len(base),'feature_rows':len(feat),'kept_sot_rows':len(kept),'ai_review_rows':len(reviews),'expanded_ai_tag_rows':len(tags),'gate_target_tags':len(targets),'raw_numeric_rules_loaded':len(raw),'pre_entry_numeric_rules_kept_after_promotable_filter':len(rules),'future_rules_excluded':len(excluded)},'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_forced_false':True}; wjson(summary_path,s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 3
    trades,hits,_unused=apply_rules(universe,rules,tags)
    out_trades=[]
    for r in trades:
        pr=float(r.get('profit_r_num') or 0.0); c=cls(r.get('confusion_class')); nd='BLOCK' if r.get('proxy_binary')=='proxy_block' else 'ALLOW_NUMERIC_AUDIT_ONLY'; ai='AI_BLOCK' if r.get('truth_label')=='actual_blocked' else 'AI_ALLOW'
        et=clean(r.get('entry_time'))
        try: month=str(pd.to_datetime(et).to_period('M')) if et else ''
        except Exception: month=''
        out_trades.append({'schema_version':SCHEMA_VERSION,'run_id':run_id,'trade_id':r.get('trade_id'),'strategy_id':r.get('strategy_id'),'direction':r.get('direction'),'entry_time':et,'entry_month':month,'ai_decision':ai,'numeric_gate_decision':nd,'confusion_class':c,'profit_r_num':fm(pr),'win_loss_flat':wl(pr),'ai_tags':r.get('ai_tags'),'numeric_tag_hits':r.get('numeric_tag_hits'),'dispatch_ready':False})
    overall,monthly,strategy=all_summaries(out_trades); recall=tag_recall(universe,tags,hits,targets)
    paths={'trade_audit':run/'gold_disc8_ai_tag_vs_numeric_gate_replay_568_trade_audit.csv','numeric_hits':run/'gold_disc8_ai_tag_vs_numeric_gate_replay_568_numeric_rule_hits.csv','overall':run/'gold_disc8_ai_tag_vs_numeric_gate_replay_568_overall_summary.csv','monthly':run/'gold_disc8_ai_tag_vs_numeric_gate_replay_568_monthly_summary.csv','strategy':run/'gold_disc8_ai_tag_vs_numeric_gate_replay_568_strategy_summary.csv','tag_recall':run/'gold_disc8_ai_tag_vs_numeric_gate_replay_568_tag_recall_summary.csv','excluded_rules':run/'gold_disc8_ai_tag_vs_numeric_gate_replay_568_excluded_future_rules.csv','input_audit':file_audit,'summary':summary_path}
    wcsv(paths['trade_audit'],out_trades,TRADE_COLS); wcsv(paths['numeric_hits'],hits,HIT_COLS); wcsv(paths['overall'],overall,SUM_COLS); wcsv(paths['monthly'],monthly,SUM_COLS); wcsv(paths['strategy'],strategy,SUM_COLS); wcsv(paths['tag_recall'],recall,RECALL_COLS); wcsv(paths['excluded_rules'],excluded,'rule_id strategy_id tag_group tag_name configured_action feature op threshold excluded_reason'.split())
    counts={k:sum(r['confusion_class']==k for r in out_trades) for k in ['AI_BLOCK_AND_NUMERIC_BLOCK','AI_BLOCK_AND_NUMERIC_ALLOW','AI_ALLOW_AND_NUMERIC_BLOCK','AI_ALLOW_AND_NUMERIC_ALLOW']}; nb=sum(r['numeric_gate_decision']=='BLOCK' for r in out_trades); ab=sum(r['ai_decision']=='AI_BLOCK' for r in out_trades); aa=sum(r['ai_decision']=='AI_ALLOW' for r in out_trades); vals=[float(r['profit_r_num'] or 0) for r in out_trades]; m=metrics(vals)
    s={'schema_version':SCHEMA_VERSION,'cycle_ok':True,'reason':'OK_AUDIT_ONLY_AI_TAG_SOT_VS_EXISTING_NUMERIC_GATE_REPLAY_568','run_id':run_id,'created_at':now_text(),'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_forced_false':True,'dispatch_ready_rows':0,'promotable_only':bool(a.promotable_only),'ai_block_definition':'base 568 trade_id absent from frozen kept SOT','numeric_block_definition':'existing numeric rules configured_action=block after future/promotable filters','counts':{'base_trade_rows':len(base),'feature_rows':len(feat),'kept_sot_rows':len(kept),'ai_review_rows':len(reviews),'expanded_ai_tag_rows':len(tags),'gate_target_tags':len(targets),'raw_numeric_rules_loaded':len(raw),'pre_entry_numeric_rules_kept_after_promotable_filter':len(rules),'future_rules_excluded':len(excluded),'trade_rows':len(out_trades),'ai_block_rows':ab,'ai_allow_rows':aa,'numeric_block_rows':nb,'numeric_allow_rows':len(out_trades)-nb,'dispatch_ready_rows':0,**counts},'classification_metrics':{'numeric_recall_of_ai_block':fm(None if not ab else counts['AI_BLOCK_AND_NUMERIC_BLOCK']/ab),'numeric_block_precision_vs_ai_block':fm(None if not nb else counts['AI_BLOCK_AND_NUMERIC_BLOCK']/nb),'ai_allow_false_numeric_block_rate':fm(None if not aa else counts['AI_ALLOW_AND_NUMERIC_BLOCK']/aa)},'overall_performance':{'trade_count':m['trade_count'],'win_count':m['win_count'],'loss_count':m['loss_count'],'win_rate':fm(m['win_rate']),'profit_factor':fm(m['profit_factor']),'avg_r':fm(m['avg_r']),'total_r':fm(m['total_r'])},'inputs':{k:str(resolve(p)) for k,p,_,_ in inputs},'outputs':{k:str(v) for k,v in paths.items()}}
    wjson(summary_path,s)
    if a.write_latest_copy:
        if latest.exists(): shutil.rmtree(windows_long_path(latest))
        mkdirp(latest)
        for p in paths.values(): shutil.copy2(windows_long_path(p),windows_long_path(latest/p.name))
    print(json.dumps(s,ensure_ascii=False,indent=2,sort_keys=True,default=str)); return 0

if __name__=='__main__': raise SystemExit(main())
