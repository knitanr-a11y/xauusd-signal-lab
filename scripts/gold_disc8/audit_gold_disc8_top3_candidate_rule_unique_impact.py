#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,json,shutil,sys
from datetime import datetime
from pathlib import Path
import pandas as pd
SCRIPT_DIR=Path(__file__).resolve().parent
REPO_ROOT=SCRIPT_DIR.parents[1]
for p in [SCRIPT_DIR,REPO_ROOT,REPO_ROOT/'scripts']:
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from build_gold_disc8_ai_tag_numeric_tagger_from_review import clean,fm,metrics,resolve,safe_float,windows_long_path
SCHEMA='gold_disc8_top3_candidate_rule_unique_impact_v1_audit_only'
DEF_CONS=Path('data/runtime_logs/gold_disc8_top3_candidate_rule_consolidation/latest')
DEF_REPLAY=Path('data/runtime_logs/gold_disc8_top3_candidate_rule_replay_568/latest')
DEF_OUT=Path('data/runtime_logs/gold_disc8_top3_candidate_rule_unique_impact')
EXPECTED=568

def now(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def rid(): return datetime.now().strftime('%Y%m%d_%H%M%S')
def mkdirp(p): Path(windows_long_path(Path(p))).mkdir(parents=True,exist_ok=True)
def wjson(p,o): mkdirp(Path(p).parent); open(windows_long_path(Path(p)),'w',encoding='utf-8').write(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True,default=str))
def wcsv(p,rows,cols):
    mkdirp(Path(p).parent)
    with open(windows_long_path(Path(p)),'w',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore'); wr.writeheader()
        for r in rows: wr.writerow({c:r.get(c,'') for c in cols})
def rcsv(p): return pd.read_csv(windows_long_path(resolve(Path(p))),encoding='utf-8-sig',sep=None,engine='python')
def sf(x,d=None):
    y=safe_float(x); return d if y is None else float(y)
def rv(r): return float(sf(r.get('profit_r_num'),0.0) or 0.0)
def wl(v): return 'WIN' if v>0 else ('LOSS' if v<0 else 'FLAT_OR_UNRESOLVED')
def pri(c): return {'BLOCK_CANDIDATE':1,'WATCH_CANDIDATE':2,'AI_REVIEW_CONTINUE':3,'REJECT_CANDIDATE':4}.get(clean(c),9)
def gsort(g): return (pri(g.get('classification')), float(g.get('total_r') or 0.0), -float(g.get('precision_vs_ai_block') or 0.0), -int(g.get('unique_hit_count') or 0))
def st(rows,scope,key,cls,action):
    vals=[float(r.get('profit_r_num') or 0.0) for r in rows]; m=metrics(vals); n=len(rows)
    ab=sum(clean(r.get('ai_decision'))=='AI_BLOCK' for r in rows); aa=sum(clean(r.get('ai_decision'))=='AI_ALLOW' for r in rows)
    return {'scope':scope,'key':key,'classification':cls,'demo_action':action,'unique_trade_count':n,'win_count':sum(v>0 for v in vals),'loss_count':sum(v<0 for v in vals),'flat_count':sum(v==0 for v in vals),'win_rate':fm(m['win_rate']),'profit_factor':fm(m['profit_factor']),'avg_r':fm(m['avg_r']),'total_r':fm(m['total_r']),'ai_block_count':ab,'ai_allow_count':aa,'precision_vs_ai_block':fm(None if n==0 else ab/n),'ai_allow_false_hit_rate':fm(None if n==0 else aa/n)}
def parse():
    p=argparse.ArgumentParser(description='Unique impact audit for DISC8 top3 consolidated candidate rules.')
    p.add_argument('--consolidation-root',type=Path,default=DEF_CONS); p.add_argument('--replay-root',type=Path,default=DEF_REPLAY); p.add_argument('--out-root',type=Path,default=DEF_OUT); p.add_argument('--run-id',default=''); p.add_argument('--expected-trade-rows',type=int,default=EXPECTED); p.add_argument('--no-latest-copy',action='store_false',dest='latest',default=True); return p.parse_args()
def main():
    a=parse(); run_id=a.run_id or rid(); cons=resolve(a.consolidation_root); replay=resolve(a.replay_root); root=resolve(a.out_root); run=root/'runs'/run_id; latest=root/'latest'; mkdirp(run)
    files={'groups':cons/'gold_disc8_top3_candidate_rule_consolidated_groups.csv','hits':replay/'gold_disc8_top3_candidate_rule_replay_rule_hit_detail.csv','trades':replay/'gold_disc8_top3_candidate_rule_replay_trade_audit.csv'}
    paths={'assignment':run/'gold_disc8_top3_candidate_rule_unique_trade_assignment.csv','class_summary':run/'gold_disc8_top3_candidate_rule_unique_classification_summary.csv','strategy_summary':run/'gold_disc8_top3_candidate_rule_unique_strategy_summary.csv','month_summary':run/'gold_disc8_top3_candidate_rule_unique_monthly_summary.csv','group_marginal':run/'gold_disc8_top3_candidate_rule_group_marginal_impact.csv','summary':run/'gold_disc8_top3_candidate_rule_unique_impact_summary.json'}
    missing=[k for k,p in files.items() if not resolve(p).exists()]
    if missing:
        s={'schema_version':SCHEMA,'cycle_ok':False,'reason':'STOP_MISSING_INPUT','missing':missing,'run_id':run_id,'created_at':now(),'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'dispatch_ready_forced_false':True,'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 2
    g=rcsv(files['groups']); h=rcsv(files['hits']); t=rcsv(files['trades'])
    problems=[]
    if len(t)!=a.expected_trade_rows: problems.append(f'trade rows expected {a.expected_trade_rows}, actual {len(t)}')
    for c in ['group_id','strategy_id','feature','op','threshold','classification','demo_action','total_r','precision_vs_ai_block','unique_hit_count']:
        if c not in g.columns: problems.append('groups missing '+c)
    for c in ['trade_id','strategy_id','feature','op','threshold']:
        if c not in h.columns: problems.append('hits missing '+c)
    for c in ['trade_id','strategy_id','entry_month','ai_decision','profit_r_num','dispatch_ready']:
        if c not in t.columns: problems.append('trades missing '+c)
    if 'dispatch_ready' in t.columns and t['dispatch_ready'].astype(str).str.lower().isin(['true','1','yes']).any(): problems.append('dispatch_ready true exists')
    if problems:
        s={'schema_version':SCHEMA,'cycle_ok':False,'reason':'STOP_INPUT_CONTRACT','problems':problems,'run_id':run_id,'created_at':now(),'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'dispatch_ready_forced_false':True,'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 3
    g=g.copy(); h=h.copy(); g['thr_key']=pd.to_numeric(g['threshold'],errors='coerce').round(6); h['thr_key']=pd.to_numeric(h['threshold'],errors='coerce').round(6)
    m=h.merge(g[['group_id','strategy_id','feature','op','thr_key','classification','demo_action','reason','tags','total_r','precision_vs_ai_block','unique_hit_count']],on=['strategy_id','feature','op','thr_key'],how='left')
    by_gid={clean(r['group_id']):r for _,r in g.iterrows()}
    hits_by_tid={}
    for _,r in m.dropna(subset=['group_id']).iterrows(): hits_by_tid.setdefault(clean(r['trade_id']),[]).append(r.to_dict())
    assign=[]
    for _,tr in t.iterrows():
        tid=clean(tr['trade_id']); hs=hits_by_tid.get(tid,[]); pr=rv(tr)
        if hs:
            best=sorted(hs,key=lambda x: gsort(by_gid.get(clean(x.get('group_id')),{})))[0]; bg=by_gid[clean(best['group_id'])]
            gids=sorted({clean(x.get('group_id')) for x in hs}); tags=sorted({clean(x.get('tags')) for x in hs if clean(x.get('tags'))})
            cls=clean(bg.get('classification')); act=clean(bg.get('demo_action')); gid=clean(bg.get('group_id')); reason=clean(bg.get('reason'))
        else:
            gids=[]; tags=[]; cls='NO_HIT'; act='ALLOW_BY_CANDIDATE_AUDIT'; gid=''; reason=''
        assign.append({'trade_id':tid,'strategy_id':clean(tr.get('strategy_id')),'direction':clean(tr.get('direction')),'entry_time':clean(tr.get('entry_time')),'entry_month':clean(tr.get('entry_month')),'ai_decision':clean(tr.get('ai_decision')),'original_confusion_class':clean(tr.get('original_confusion_class') or tr.get('confusion_class')),'profit_r_num':fm(pr),'win_loss_flat':wl(pr),'assigned_classification':cls,'assigned_demo_action':act,'assigned_group_id':gid,'assigned_reason':reason,'hit_group_ids':' | '.join(gids),'hit_group_count':len(gids),'hit_tags':' | '.join(tags),'dispatch_ready':False})
    cls_rows=[]
    for cls in ['BLOCK_CANDIDATE','WATCH_CANDIDATE','AI_REVIEW_CONTINUE','REJECT_CANDIDATE']:
        sub=[r for r in assign if r['assigned_classification']==cls]; cls_rows.append(st(sub,'classification',cls,cls,sub[0]['assigned_demo_action'] if sub else ''))
    strat_rows=[]
    for sid in sorted({r['strategy_id'] for r in assign if r['assigned_classification']!='NO_HIT'}):
        for cls in ['BLOCK_CANDIDATE','WATCH_CANDIDATE']:
            sub=[r for r in assign if r['strategy_id']==sid and r['assigned_classification']==cls]; strat_rows.append(st(sub,'strategy',sid,cls,sub[0]['assigned_demo_action'] if sub else ''))
    month_rows=[]
    for cls in ['BLOCK_CANDIDATE','WATCH_CANDIDATE']:
        for mo in sorted({r['entry_month'] for r in assign if r['assigned_classification']==cls}):
            sub=[r for r in assign if r['assigned_classification']==cls and r['entry_month']==mo]; q=st(sub,'month',mo,cls,sub[0]['assigned_demo_action'] if sub else ''); month_rows.append(q)
    marg=[]
    for _,gr in g.iterrows():
        gid=clean(gr['group_id']); sub=[r for r in assign if r['assigned_group_id']==gid]; vals=[float(r['profit_r_num'] or 0.0) for r in sub]; mm=metrics(vals); ab=sum(r['ai_decision']=='AI_BLOCK' for r in sub); aa=sum(r['ai_decision']=='AI_ALLOW' for r in sub); n=len(sub)
        marg.append({'group_id':gid,'strategy_id':clean(gr['strategy_id']),'feature':clean(gr['feature']),'op':clean(gr['op']),'threshold':gr['threshold'],'tags':clean(gr.get('tags')),'classification':clean(gr['classification']),'demo_action':clean(gr['demo_action']),'group_unique_hit_count':int(gr.get('unique_hit_count') or 0),'group_total_r':gr.get('total_r'),'marginal_unique_trade_count':n,'marginal_total_r':fm(mm['total_r']),'marginal_ai_block_count':ab,'marginal_ai_allow_count':aa,'marginal_precision_vs_ai_block':fm(None if n==0 else ab/n),'marginal_ai_allow_false_hit_rate':fm(None if n==0 else aa/n)})
    assign_cols='trade_id strategy_id direction entry_time entry_month ai_decision original_confusion_class profit_r_num win_loss_flat assigned_classification assigned_demo_action assigned_group_id assigned_reason hit_group_ids hit_group_count hit_tags dispatch_ready'.split()
    sum_cols='scope key classification demo_action unique_trade_count win_count loss_count flat_count win_rate profit_factor avg_r total_r ai_block_count ai_allow_count precision_vs_ai_block ai_allow_false_hit_rate'.split()
    marg_cols='group_id strategy_id feature op threshold tags classification demo_action group_unique_hit_count group_total_r marginal_unique_trade_count marginal_total_r marginal_ai_block_count marginal_ai_allow_count marginal_precision_vs_ai_block marginal_ai_allow_false_hit_rate'.split()
    wcsv(paths['assignment'],assign,assign_cols); wcsv(paths['class_summary'],cls_rows,sum_cols); wcsv(paths['strategy_summary'],strat_rows,sum_cols); wcsv(paths['month_summary'],month_rows,sum_cols); wcsv(paths['group_marginal'],marg,marg_cols)
    s={'schema_version':SCHEMA,'cycle_ok':True,'reason':'OK_AUDIT_ONLY_UNIQUE_IMPACT','run_id':run_id,'created_at':now(),'source_of_truth':'consolidated groups + replay hit detail + replay trade audit; one owner group per trade','no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_forced_false':True,'dispatch_ready_rows':0,'counts':{'trade_rows':len(t),'consolidated_groups':len(g),'rule_hit_rows':len(h),'candidate_hit_unique_trades':sum(r['assigned_classification']!='NO_HIT' for r in assign)},'unique_classification_summary':cls_rows,'warning':'Use unique_* outputs for demo impact. Prior consolidation classification_summary is per-group and can overcount overlapping trades.','outputs':{k:str(v) for k,v in paths.items()}}
    wjson(paths['summary'],s)
    if a.latest:
        if latest.exists(): shutil.rmtree(windows_long_path(latest))
        mkdirp(latest)
        for p in paths.values(): shutil.copy2(windows_long_path(p),windows_long_path(latest/p.name))
    print(json.dumps(s,ensure_ascii=False,indent=2,sort_keys=True,default=str)); return 0
if __name__=='__main__': raise SystemExit(main())
