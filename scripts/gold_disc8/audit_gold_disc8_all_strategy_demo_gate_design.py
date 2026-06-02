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
SCHEMA='gold_disc8_all_strategy_demo_gate_design_v1_audit_only'
DEF_REPLAY=Path('data/runtime_logs/gold_disc8_ai_tag_vs_numeric_gate_replay_568/latest')
DEF_UNIQUE=Path('data/runtime_logs/gold_disc8_top3_candidate_rule_unique_impact/latest')
DEF_OUT=Path('data/runtime_logs/gold_disc8_all_strategy_demo_gate_design')
STRATEGIES=['DISC_01_BUY_TP200_SL100_RR2','DISC_02_BUY_TP80_SL50_RR1p6','DISC_04_BUY_TP150_SL100_RR1p5','DISC_05_BUY_TP80_SL50_RR1p6','DISC_06_SELL_TP80_SL50_RR1p6','DISC_08_BUY_TP200_SL100_RR2','DISC_09_BUY_TP80_SL50_RR1p6','DISC_11_SELL_TP80_SL50_RR1p6']
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
def rownum(r,c,d=0.0): return float(sf(r.get(c),d) or 0.0)
def audit(label,path,required,note):
    p=resolve(Path(path)); r={'label':label,'path':str(p),'exists':p.exists(),'rows':'','columns':'','required':required,'status':'OK' if p.exists() else ('MISSING_REQUIRED' if required else 'MISSING_OPTIONAL'),'note':note}
    if p.exists() and p.suffix.lower()=='.csv':
        try:
            df=pd.read_csv(windows_long_path(p),encoding='utf-8-sig',sep=None,engine='python'); r['rows']=len(df); r['columns']=' | '.join(map(str,df.columns))
        except Exception as e: r['status']='READ_ERROR'; r['note']=note+'; '+type(e).__name__+': '+str(e)
    return r
def bucket_map(df,sid):
    sub=df[(df['group'].astype(str).map(clean)=='strategy')&(df['key'].astype(str).map(clean)==sid)]
    return {clean(r['bucket']):r for _,r in sub.iterrows()}
def nzrow(mp,b): return mp.get(b,{})
def perf(r,prefix):
    return {prefix+'_count':int(rownum(r,'trade_count',0)),prefix+'_win_rate':fm(sf(r.get('win_rate'))),prefix+'_pf':fm(sf(r.get('profit_factor'))),prefix+'_total_r':fm(sf(r.get('total_r'),0.0))}
def choose_action(sid,d):
    nb=d['new_block_count']; nw=d['new_watch_count']; nbt=d['new_block_total_r']; nwt=d['new_watch_total_r']; eb=d['existing_numeric_block_count']; ebt=d['existing_numeric_block_total_r']; ef=d['existing_numeric_false_block_count']; eprec=d['existing_numeric_precision_vs_ai_block']; miss=d['ai_block_numeric_miss_total_r']
    if nb>0 and nbt<0 and d['new_block_precision_vs_ai_block']>=0.80 and d['new_block_false_rate']<=0.20:
        return 'DEMO_BLOCK_GATE_CANDIDATE','DISC_08 style additional numeric BLOCK candidate exists; use only after explicit runtime config generation'
    if nw>0 and nwt<0:
        return 'DEMO_WATCH_ONLY','candidate catches weak trades but false-hit risk is too high for automatic block'
    if eb>0 and ebt<=-3 and ef==0:
        return 'KEEP_EXISTING_NUMERIC_BLOCK_GATE','existing numeric gate blocks bad trades with no AI_ALLOW false block in 568 audit'
    if eb>0 and ebt<0:
        return 'KEEP_EXISTING_NUMERIC_GATE_WATCH','existing numeric gate is mildly negative but weak; keep/watch rather than expand'
    if sid.endswith('SELL_TP80_SL50_RR1p6') and eb==0 and miss<0:
        return 'NEEDS_SELL_SIDE_AUDIT','SELL strategy has AI_BLOCK misses but no current numeric candidate in this path'
    if miss>=0:
        return 'NO_ADDITIONAL_GATE','missed AI_BLOCK side is not harmful in this audit; avoid adding gate'
    return 'AI_REVIEW_REQUIRED','AI_BLOCK miss remains negative and no safe numeric candidate is available'
def parse():
    p=argparse.ArgumentParser(description='All 8 DISC8 demo gate design audit. Audit-only.')
    p.add_argument('--replay-root',type=Path,default=DEF_REPLAY); p.add_argument('--unique-root',type=Path,default=DEF_UNIQUE); p.add_argument('--out-root',type=Path,default=DEF_OUT); p.add_argument('--run-id',default=''); p.add_argument('--expected-trade-rows',type=int,default=EXPECTED); p.add_argument('--no-latest-copy',action='store_false',dest='latest',default=True); return p.parse_args()
def main():
    a=parse(); run_id=a.run_id or rid(); rr=resolve(a.replay_root); ur=resolve(a.unique_root); root=resolve(a.out_root); run=root/'runs'/run_id; latest=root/'latest'; mkdirp(run)
    files={'replay_strategy':rr/'gold_disc8_ai_tag_vs_numeric_gate_replay_568_strategy_summary.csv','replay_overall':rr/'gold_disc8_ai_tag_vs_numeric_gate_replay_568_overall_summary.csv','unique_strategy':ur/'gold_disc8_top3_candidate_rule_unique_strategy_summary.csv','unique_classification':ur/'gold_disc8_top3_candidate_rule_unique_classification_summary.csv'}
    paths={'input_audit':run/'gold_disc8_all_strategy_demo_gate_design_input_audit.csv','strategy_plan':run/'gold_disc8_all_strategy_demo_gate_design_strategy_plan.csv','action_summary':run/'gold_disc8_all_strategy_demo_gate_design_action_summary.csv','audit_json':run/'gold_disc8_all_strategy_demo_gate_design.audit_only.json','summary':run/'gold_disc8_all_strategy_demo_gate_design_summary.json'}
    audits=[audit(k,v,True,'all strategy demo gate design input') for k,v in files.items()]; wcsv(paths['input_audit'],audits,'label path exists rows columns required status note'.split())
    missing=[r['label'] for r in audits if r['required'] and not r['exists']]
    if missing:
        s={'schema_version':SCHEMA,'cycle_ok':False,'reason':'STOP_MISSING_INPUT','missing':missing,'run_id':run_id,'created_at':now(),'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'dispatch_ready_forced_false':True,'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 2
    rs=rcsv(files['replay_strategy']); ro=rcsv(files['replay_overall']); us=rcsv(files['unique_strategy']); uc=rcsv(files['unique_classification'])
    problems=[]
    if int(ro[ro['bucket'].astype(str).map(clean)=='ALL']['trade_count'].iloc[0])!=a.expected_trade_rows: problems.append('overall trade_count not expected')
    for sid in STRATEGIES:
        if sid not in set(rs['key'].astype(str).map(clean)): problems.append('missing strategy in replay summary: '+sid)
    if problems:
        s={'schema_version':SCHEMA,'cycle_ok':False,'reason':'STOP_INPUT_CONTRACT','problems':problems,'run_id':run_id,'created_at':now(),'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'dispatch_ready_forced_false':True,'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 3
    rows=[]
    for sid in STRATEGIES:
        mp=bucket_map(rs,sid); allr=nzrow(mp,'ALL'); aa=nzrow(mp,'AI_ALLOW_AND_NUMERIC_ALLOW'); fab=nzrow(mp,'AI_ALLOW_AND_NUMERIC_BLOCK'); miss=nzrow(mp,'AI_BLOCK_AND_NUMERIC_ALLOW'); tb=nzrow(mp,'AI_BLOCK_AND_NUMERIC_BLOCK')
        eb=int(rownum(fab,'trade_count',0)+rownum(tb,'trade_count',0)); ebt=rownum(fab,'total_r',0)+rownum(tb,'total_r',0); eab=int(rownum(tb,'trade_count',0)); eaf=int(rownum(fab,'trade_count',0)); eprec=(eab/eb) if eb else None
        usub=us[us['key'].astype(str).map(clean)==sid]
        nb=nw=0; nbt=nwt=0.0; nbprec=nwprec=0.0; nbfr=nwfr=0.0
        for _,r in usub.iterrows():
            cls=clean(r['classification'])
            if cls=='BLOCK_CANDIDATE': nb=int(rownum(r,'unique_trade_count',0)); nbt=rownum(r,'total_r',0); nbprec=sf(r.get('precision_vs_ai_block'),0) or 0; nbfr=sf(r.get('ai_allow_false_hit_rate'),0) or 0
            if cls=='WATCH_CANDIDATE': nw=int(rownum(r,'unique_trade_count',0)); nwt=rownum(r,'total_r',0); nwprec=sf(r.get('precision_vs_ai_block'),0) or 0; nwfr=sf(r.get('ai_allow_false_hit_rate'),0) or 0
        d={'new_block_count':nb,'new_watch_count':nw,'new_block_total_r':nbt,'new_watch_total_r':nwt,'new_block_precision_vs_ai_block':nbprec,'new_watch_precision_vs_ai_block':nwprec,'new_block_false_rate':nbfr,'new_watch_false_rate':nwfr,'existing_numeric_block_count':eb,'existing_numeric_block_total_r':ebt,'existing_numeric_false_block_count':eaf,'existing_numeric_precision_vs_ai_block':eprec or 0,'ai_block_numeric_miss_total_r':rownum(miss,'total_r',0)}
        action,reason=choose_action(sid,d)
        out={'strategy_id':sid,'recommended_demo_action':action,'reason':reason,**perf(allr,'all'),**perf(aa,'ai_allow_numeric_allow'),**perf(miss,'ai_block_numeric_miss'),**perf(tb,'ai_block_existing_numeric_block'),'existing_numeric_block_count':eb,'existing_numeric_block_total_r':fm(ebt),'existing_numeric_ai_block_capture_count':eab,'existing_numeric_false_block_count':eaf,'existing_numeric_precision_vs_ai_block':fm(eprec),'new_block_count':nb,'new_block_total_r':fm(nbt),'new_block_precision_vs_ai_block':fm(nbprec),'new_block_false_rate':fm(nbfr),'new_watch_count':nw,'new_watch_total_r':fm(nwt),'new_watch_precision_vs_ai_block':fm(nwprec),'new_watch_false_rate':fm(nwfr),'demo_runtime_status':'AUDIT_ONLY_NOT_RUNTIME_CONFIG'}
        rows.append(out)
    cols='strategy_id recommended_demo_action reason all_count all_win_rate all_pf all_total_r ai_allow_numeric_allow_count ai_allow_numeric_allow_win_rate ai_allow_numeric_allow_pf ai_allow_numeric_allow_total_r ai_block_numeric_miss_count ai_block_numeric_miss_win_rate ai_block_numeric_miss_pf ai_block_numeric_miss_total_r ai_block_existing_numeric_block_count ai_block_existing_numeric_block_win_rate ai_block_existing_numeric_block_pf ai_block_existing_numeric_block_total_r existing_numeric_block_count existing_numeric_block_total_r existing_numeric_ai_block_capture_count existing_numeric_false_block_count existing_numeric_precision_vs_ai_block new_block_count new_block_total_r new_block_precision_vs_ai_block new_block_false_rate new_watch_count new_watch_total_r new_watch_precision_vs_ai_block new_watch_false_rate demo_runtime_status'.split()
    wcsv(paths['strategy_plan'],rows,cols)
    actions=[]
    for act in sorted({r['recommended_demo_action'] for r in rows}):
        sub=[r for r in rows if r['recommended_demo_action']==act]
        actions.append({'recommended_demo_action':act,'strategy_count':len(sub),'strategies':' | '.join(r['strategy_id'] for r in sub),'all_total_r':fm(sum(float(r['all_total_r'] or 0) for r in sub)),'existing_numeric_block_total_r':fm(sum(float(r['existing_numeric_block_total_r'] or 0) for r in sub)),'new_block_total_r':fm(sum(float(r['new_block_total_r'] or 0) for r in sub)),'new_watch_total_r':fm(sum(float(r['new_watch_total_r'] or 0) for r in sub))})
    wcsv(paths['action_summary'],actions,'recommended_demo_action strategy_count strategies all_total_r existing_numeric_block_total_r new_block_total_r new_watch_total_r'.split())
    gate={'schema_version':SCHEMA,'audit_only':True,'do_not_use_as_runtime_config':True,'dispatch_ready_enabled':False,'created_at':now(),'source_inputs':{k:str(v) for k,v in files.items()},'strategy_plan':rows,'safety':{'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False},'next_step':'manual review then generate explicit demo runtime candidate config'}
    wjson(paths['audit_json'],gate)
    s={'schema_version':SCHEMA,'cycle_ok':True,'reason':'OK_AUDIT_ONLY_ALL_STRATEGY_DEMO_GATE_DESIGN','run_id':run_id,'created_at':now(),'counts':{'strategies':len(rows),'trade_rows':int(ro[ro['bucket'].astype(str).map(clean)=='ALL']['trade_count'].iloc[0])},'action_summary':actions,'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_forced_false':True,'dispatch_ready_rows':0,'outputs':{k:str(v) for k,v in paths.items()}}
    wjson(paths['summary'],s)
    if a.latest:
        if latest.exists(): shutil.rmtree(windows_long_path(latest))
        mkdirp(latest)
        for p in paths.values(): shutil.copy2(windows_long_path(p),windows_long_path(latest/p.name))
    print(json.dumps(s,ensure_ascii=False,indent=2,sort_keys=True,default=str)); return 0
if __name__=='__main__': raise SystemExit(main())
