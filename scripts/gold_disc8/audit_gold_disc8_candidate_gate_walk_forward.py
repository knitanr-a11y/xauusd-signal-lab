#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,json,shutil,sys
from datetime import datetime
from pathlib import Path
from typing import Any
import pandas as pd
SCRIPT_DIR=Path(__file__).resolve().parent
REPO_ROOT=SCRIPT_DIR.parents[1]
for p in [SCRIPT_DIR,REPO_ROOT,REPO_ROOT/'scripts']:
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from build_gold_disc8_ai_tag_numeric_tagger_from_review import clean,fm,metrics,resolve,safe_float,windows_long_path
SCHEMA='gold_disc8_candidate_gate_walk_forward_v1_audit_only'
DEF_REPLAY=Path('data/runtime_logs/gold_disc8_top3_candidate_rule_replay_568/latest')
DEF_GROUPS=Path('data/runtime_logs/gold_disc8_top3_candidate_rule_consolidation/latest/gold_disc8_top3_candidate_rule_consolidated_groups.csv')
DEF_OUT=Path('data/runtime_logs/gold_disc8_candidate_gate_walk_forward')
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
def month_of(r):
    m=clean(r.get('entry_month'))
    if m: return m[:7]
    t=clean(r.get('entry_time'))
    return t[:7]
def is_block(r): return clean(r.get('ai_decision'))=='AI_BLOCK'
def is_allow(r): return clean(r.get('ai_decision'))=='AI_ALLOW'
def stat(rows):
    vals=[rv(r) for r in rows]; m=metrics(vals); n=len(rows); ab=sum(is_block(r) for r in rows); aa=sum(is_allow(r) for r in rows)
    return {'count':n,'win_count':sum(v>0 for v in vals),'loss_count':sum(v<0 for v in vals),'win_rate':fm(m['win_rate']),'profit_factor':fm(m['profit_factor']),'avg_r':fm(m['avg_r']),'total_r':fm(m['total_r']),'ai_block_count':ab,'ai_allow_count':aa,'precision_vs_ai_block':fm(None if n==0 else ab/n),'ai_allow_false_hit_rate':fm(None if n==0 else aa/n)}
def priority(cls): return {'BLOCK_CANDIDATE':1,'WATCH_CANDIDATE':2}.get(cls,9)
def audit(label,path,required,note):
    p=resolve(Path(path)); return {'label':label,'path':str(p),'exists':p.exists(),'required':required,'status':'OK' if p.exists() else ('MISSING_REQUIRED' if required else 'MISSING_OPTIONAL'),'note':note}
def merge_hits(groups,hits):
    g=groups.copy(); h=hits.copy(); g['thr_key']=pd.to_numeric(g['threshold'],errors='coerce').round(6); h['thr_key']=pd.to_numeric(h['threshold'],errors='coerce').round(6)
    return h.merge(g[['group_id','strategy_id','feature','op','thr_key','tags']],on=['strategy_id','feature','op','thr_key'],how='left')
def group_train_stats(groups,merged,trade_rows,train_months):
    trade_by_id={clean(r['trade_id']):r for r in trade_rows if month_of(r) in train_months}
    hit_by_gid={}
    for _,h in merged.dropna(subset=['group_id']).iterrows():
        tid=clean(h.get('trade_id')); gid=clean(h.get('group_id'))
        if tid in trade_by_id: hit_by_gid.setdefault(gid,{})[tid]=trade_by_id[tid]
    out={}
    for _,g in groups.iterrows():
        gid=clean(g.get('group_id')); rows=list(hit_by_gid.get(gid,{}).values()); s=stat(rows)
        out[gid]={**s,'group_id':gid,'strategy_id':clean(g.get('strategy_id')),'feature':clean(g.get('feature')),'op':clean(g.get('op')),'threshold':g.get('threshold'),'tags':clean(g.get('tags'))}
    return out
def classify(s,args):
    if s['count']>=args.min_train_hits and float(s['total_r'] or 0)<0 and float(s['precision_vs_ai_block'] or 0)>=args.block_min_precision and float(s['ai_allow_false_hit_rate'] or 0)<=args.block_max_false_rate:
        return 'BLOCK_CANDIDATE'
    if s['count']>=args.min_train_hits and float(s['total_r'] or 0)<0 and float(s['precision_vs_ai_block'] or 0)>=args.watch_min_precision and float(s['ai_allow_false_hit_rate'] or 0)<=args.watch_max_false_rate:
        return 'WATCH_CANDIDATE'
    return 'REJECT_CANDIDATE'
def assign_test(merged,trade_rows,test_month,selected,train_stats):
    trade_by_id={clean(r['trade_id']):r for r in trade_rows if month_of(r)==test_month}
    hits_by_tid={}
    for _,h in merged.dropna(subset=['group_id']).iterrows():
        tid=clean(h.get('trade_id')); gid=clean(h.get('group_id'))
        if tid in trade_by_id and gid in selected: hits_by_tid.setdefault(tid,[]).append(gid)
    assigned=[]
    for tid,tr in trade_by_id.items():
        gids=hits_by_tid.get(tid,[])
        if not gids: continue
        def key(gid):
            s=train_stats[gid]; return (priority(selected[gid]), float(s['total_r'] or 0.0), -float(s['precision_vs_ai_block'] or 0.0), -int(s['count'] or 0))
        best=sorted(gids,key=key)[0]
        assigned.append({'trade_id':tid,'entry_month':test_month,'strategy_id':clean(tr.get('strategy_id')),'ai_decision':clean(tr.get('ai_decision')),'profit_r_num':fm(rv(tr)),'selected_classification':selected[best],'selected_group_id':best,'hit_group_ids':' | '.join(sorted(set(gids))),'hit_group_count':len(set(gids))})
    return assigned
def parse():
    p=argparse.ArgumentParser(description='Walk-forward audit for DISC8 candidate gate rules. Audit-only, no OHLC rediscovery.')
    p.add_argument('--replay-root',type=Path,default=DEF_REPLAY); p.add_argument('--consolidated-groups-csv',type=Path,default=DEF_GROUPS); p.add_argument('--out-root',type=Path,default=DEF_OUT); p.add_argument('--min-train-months',type=int,default=3); p.add_argument('--min-train-hits',type=int,default=5); p.add_argument('--block-min-precision',type=float,default=0.80); p.add_argument('--block-max-false-rate',type=float,default=0.20); p.add_argument('--watch-min-precision',type=float,default=0.60); p.add_argument('--watch-max-false-rate',type=float,default=0.40); p.add_argument('--run-id',default=''); p.add_argument('--no-latest-copy',action='store_false',dest='latest',default=True); return p.parse_args()
def main():
    a=parse(); run_id=a.run_id or rid(); rr=resolve(a.replay_root); root=resolve(a.out_root); run=root/'runs'/run_id; latest=root/'latest'; mkdirp(run)
    files={'trade_audit':rr/'gold_disc8_top3_candidate_rule_replay_trade_audit.csv','rule_hit_detail':rr/'gold_disc8_top3_candidate_rule_replay_rule_hit_detail.csv','consolidated_groups':a.consolidated_groups_csv}
    paths={'input_audit':run/'gold_disc8_candidate_gate_walk_forward_input_audit.csv','fold_summary':run/'gold_disc8_candidate_gate_walk_forward_fold_summary.csv','selected_groups':run/'gold_disc8_candidate_gate_walk_forward_selected_groups.csv','test_assignments':run/'gold_disc8_candidate_gate_walk_forward_test_assignments.csv','summary':run/'gold_disc8_candidate_gate_walk_forward_summary.json'}
    audits=[audit(k,v,True,'walk-forward input') for k,v in files.items()]; wcsv(paths['input_audit'],audits,'label path exists required status note'.split())
    missing=[r['label'] for r in audits if r['required'] and not r['exists']]
    if missing:
        s={'schema_version':SCHEMA,'cycle_ok':False,'reason':'STOP_MISSING_INPUT','missing':missing,'run_id':run_id,'created_at':now(),'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'dispatch_ready_enabled':False,'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 2
    trades=rcsv(files['trade_audit']); hits=rcsv(files['rule_hit_detail']); groups=rcsv(files['consolidated_groups'])
    problems=[]
    for c in ['trade_id','strategy_id','entry_time','profit_r_num','ai_decision']:
        if c not in trades.columns: problems.append('trade_audit missing '+c)
    for c in ['trade_id','strategy_id','feature','op','threshold']:
        if c not in hits.columns: problems.append('rule_hit_detail missing '+c)
    for c in ['group_id','strategy_id','feature','op','threshold','tags']:
        if c not in groups.columns: problems.append('consolidated_groups missing '+c)
    if problems:
        s={'schema_version':SCHEMA,'cycle_ok':False,'reason':'STOP_INPUT_CONTRACT','problems':problems,'run_id':run_id,'created_at':now(),'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 3
    rows=trades.to_dict('records'); months=sorted({month_of(r) for r in rows if month_of(r)})
    if len(months)<=a.min_train_months:
        s={'schema_version':SCHEMA,'cycle_ok':False,'reason':'STOP_NOT_ENOUGH_MONTHS','months':months,'min_train_months':a.min_train_months,'run_id':run_id,'created_at':now(),'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 4
    merged=merge_hits(groups,hits)
    fold_rows=[]; sel_rows=[]; ass_rows=[]
    for i in range(a.min_train_months,len(months)):
        train_months=months[:i]; test_month=months[i]
        gs=group_train_stats(groups,merged,rows,set(train_months))
        selected={}
        for gid,s in gs.items():
            cls=classify(s,a)
            sel_rows.append({'fold_id':i-a.min_train_months+1,'train_months':' | '.join(train_months),'test_month':test_month,'group_id':gid,'strategy_id':s['strategy_id'],'feature':s['feature'],'op':s['op'],'threshold':s['threshold'],'tags':s['tags'],'train_classification':cls,'train_count':s['count'],'train_total_r':s['total_r'],'train_precision_vs_ai_block':s['precision_vs_ai_block'],'train_false_rate':s['ai_allow_false_hit_rate']})
            if cls in ['BLOCK_CANDIDATE','WATCH_CANDIDATE']: selected[gid]=cls
        ar=assign_test(merged,rows,test_month,selected,gs); ass_rows+= [{'fold_id':i-a.min_train_months+1,**r} for r in ar]
        for cls in ['BLOCK_CANDIDATE','WATCH_CANDIDATE']:
            sub=[r for r in ar if r['selected_classification']==cls]; st=stat(sub)
            fold_rows.append({'fold_id':i-a.min_train_months+1,'train_months':' | '.join(train_months),'test_month':test_month,'classification':cls,'selected_group_count':sum(1 for v in selected.values() if v==cls),'test_unique_trade_count':st['count'],'test_win_count':st['win_count'],'test_loss_count':st['loss_count'],'test_win_rate':st['win_rate'],'test_profit_factor':st['profit_factor'],'test_avg_r':st['avg_r'],'test_total_r':st['total_r'],'test_ai_block_count':st['ai_block_count'],'test_ai_allow_count':st['ai_allow_count'],'test_precision_vs_ai_block':st['precision_vs_ai_block'],'test_false_rate':st['ai_allow_false_hit_rate']})
    wcsv(paths['fold_summary'],fold_rows,'fold_id train_months test_month classification selected_group_count test_unique_trade_count test_win_count test_loss_count test_win_rate test_profit_factor test_avg_r test_total_r test_ai_block_count test_ai_allow_count test_precision_vs_ai_block test_false_rate'.split())
    wcsv(paths['selected_groups'],sel_rows,'fold_id train_months test_month group_id strategy_id feature op threshold tags train_classification train_count train_total_r train_precision_vs_ai_block train_false_rate'.split())
    wcsv(paths['test_assignments'],ass_rows,'fold_id trade_id entry_month strategy_id ai_decision profit_r_num selected_classification selected_group_id hit_group_ids hit_group_count'.split())
    block=[r for r in ass_rows if r['selected_classification']=='BLOCK_CANDIDATE']; watch=[r for r in ass_rows if r['selected_classification']=='WATCH_CANDIDATE']
    s={'schema_version':SCHEMA,'cycle_ok':True,'reason':'OK_AUDIT_ONLY_WALK_FORWARD_CANDIDATE_GATE','run_id':run_id,'created_at':now(),'method':'candidate pool fixed from prior audit; each fold selects groups using only earlier months, then tests one future month. This is stronger than same-sample replay but not a perfect no-leak candidate-generation walk-forward.','months':months,'min_train_months':a.min_train_months,'fold_count':len(months)-a.min_train_months,'block_oos_summary':stat(block),'watch_oos_summary':stat(watch),'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_enabled':False,'outputs':{k:str(v) for k,v in paths.items()}}
    wjson(paths['summary'],s)
    if a.latest:
        if latest.exists(): shutil.rmtree(windows_long_path(latest))
        mkdirp(latest)
        for p in paths.values(): shutil.copy2(windows_long_path(p),windows_long_path(latest/p.name))
    print(json.dumps(s,ensure_ascii=False,indent=2,sort_keys=True,default=str)); return 0
if __name__=='__main__': raise SystemExit(main())
