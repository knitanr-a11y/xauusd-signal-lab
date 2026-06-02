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
from build_gold_disc8_ai_tag_numeric_tagger_from_review import clean,resolve,windows_long_path
SCHEMA='gold_disc8_demo_runtime_gate_candidate_config_v1_audit_only'
DEF_DESIGN=Path('data/runtime_logs/gold_disc8_all_strategy_demo_gate_design/latest')
DEF_DETAIL=Path('data/runtime_logs/gold_disc8_top3_candidate_rule_consolidation/latest')
DEF_OUT=Path('data/runtime_logs/gold_disc8_demo_runtime_gate_candidate_config')
STRATEGIES=['DISC_01_BUY_TP200_SL100_RR2','DISC_02_BUY_TP80_SL50_RR1p6','DISC_04_BUY_TP150_SL100_RR1p5','DISC_05_BUY_TP80_SL50_RR1p6','DISC_06_SELL_TP80_SL50_RR1p6','DISC_08_BUY_TP200_SL100_RR2','DISC_09_BUY_TP80_SL50_RR1p6','DISC_11_SELL_TP80_SL50_RR1p6']
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
def rjson(p):
    with open(windows_long_path(resolve(Path(p))),encoding='utf-8') as f: return json.load(f)
def audit(label,path,required,note):
    p=resolve(Path(path)); return {'label':label,'path':str(p),'exists':p.exists(),'required':required,'status':'OK' if p.exists() else ('MISSING_REQUIRED' if required else 'MISSING_OPTIONAL'),'note':note}
def mode_for(action):
    return {'DEMO_BLOCK_GATE_CANDIDATE':'ADDITIONAL_NUMERIC_BLOCK_CANDIDATE','DEMO_WATCH_ONLY':'ADDITIONAL_NUMERIC_WATCH_ONLY','KEEP_EXISTING_NUMERIC_BLOCK_GATE':'EXISTING_NUMERIC_BLOCK_GATE','KEEP_EXISTING_NUMERIC_GATE_WATCH':'EXISTING_NUMERIC_GATE_WATCH','NEEDS_SELL_SIDE_AUDIT':'NO_DEMO_NUMERIC_GATE_NEEDS_SELL_AUDIT','AI_REVIEW_REQUIRED':'AI_REVIEW_REQUIRED','NO_ADDITIONAL_GATE':'NO_ADDITIONAL_GATE'}.get(action,'UNKNOWN')
def pick_rules(detail, sid, classification):
    src='block_candidates' if classification=='BLOCK_CANDIDATE' else 'watch_candidates'
    return [r for r in detail.get(src,[]) if clean(r.get('strategy_id'))==sid]
def parse():
    p=argparse.ArgumentParser(description='Build audit-only explicit demo runtime gate candidate config from all-strategy design.')
    p.add_argument('--design-root',type=Path,default=DEF_DESIGN); p.add_argument('--detail-root',type=Path,default=DEF_DETAIL); p.add_argument('--out-root',type=Path,default=DEF_OUT); p.add_argument('--run-id',default=''); p.add_argument('--no-latest-copy',action='store_false',dest='latest',default=True); return p.parse_args()
def main():
    a=parse(); run_id=a.run_id or rid(); dr=resolve(a.design_root); tr=resolve(a.detail_root); root=resolve(a.out_root); run=root/'runs'/run_id; latest=root/'latest'; mkdirp(run)
    files={'design_json':dr/'gold_disc8_all_strategy_demo_gate_design.audit_only.json','strategy_plan':dr/'gold_disc8_all_strategy_demo_gate_design_strategy_plan.csv','detail_json':tr/'gold_disc8_demo_runtime_gate_candidate.audit_only.json'}
    paths={'input_audit':run/'gold_disc8_demo_runtime_gate_candidate_config_input_audit.csv','strategy_policy':run/'gold_disc8_demo_runtime_gate_candidate_config_strategy_policy.csv','config':run/'gold_disc8_demo_runtime_gate_candidate_config.audit_only.json','summary':run/'gold_disc8_demo_runtime_gate_candidate_config_summary.json'}
    audits=[audit(k,v,True,'candidate config input') for k,v in files.items()]; wcsv(paths['input_audit'],audits,'label path exists required status note'.split())
    missing=[r['label'] for r in audits if r['required'] and not r['exists']]
    if missing:
        s={'schema_version':SCHEMA,'cycle_ok':False,'reason':'STOP_MISSING_INPUT','missing':missing,'run_id':run_id,'created_at':now(),'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'dispatch_ready_enabled':False,'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 2
    design=rjson(files['design_json']); detail=rjson(files['detail_json']); plan=rcsv(files['strategy_plan'])
    problems=[]
    if not design.get('audit_only') or not design.get('do_not_use_as_runtime_config'): problems.append('design json is not audit-only')
    if not detail.get('audit_only') or not detail.get('do_not_use_as_runtime_config'): problems.append('detail json is not audit-only')
    have=set(plan['strategy_id'].astype(str).map(clean))
    for sid in STRATEGIES:
        if sid not in have: problems.append('missing strategy: '+sid)
    if problems:
        s={'schema_version':SCHEMA,'cycle_ok':False,'reason':'STOP_INPUT_CONTRACT','problems':problems,'run_id':run_id,'created_at':now(),'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'dispatch_ready_enabled':False,'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 3
    policies=[]; embedded={'additional_block_candidates':[],'additional_watch_candidates':[]}
    for _,r in plan.iterrows():
        sid=clean(r['strategy_id']); action=clean(r['recommended_demo_action']); mode=mode_for(action)
        br=pick_rules(detail,sid,'BLOCK_CANDIDATE') if action=='DEMO_BLOCK_GATE_CANDIDATE' else []
        wr=pick_rules(detail,sid,'WATCH_CANDIDATE') if action=='DEMO_WATCH_ONLY' else []
        embedded['additional_block_candidates']+=br; embedded['additional_watch_candidates']+=wr
        policies.append({'strategy_id':sid,'recommended_demo_action':action,'gate_mode':mode,'use_existing_numeric_rules':action in ['KEEP_EXISTING_NUMERIC_BLOCK_GATE','KEEP_EXISTING_NUMERIC_GATE_WATCH'],'additional_block_rule_count':len(br),'additional_watch_rule_count':len(wr),'dispatch_ready_enabled':False,'demo_runtime_status':'CANDIDATE_CONFIG_AUDIT_ONLY','reason':r.get('reason','')})
    cfg={'schema_version':SCHEMA,'audit_only':True,'do_not_use_as_runtime_config':True,'dispatch_ready_enabled':False,'created_at':now(),'source_inputs':{k:str(v) for k,v in files.items()},'safety':{'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False},'existing_numeric_rule_sources':{'numeric_rules_json':'data/runtime_logs/gold_disc8_ai_tag_numeric_tagger_from_review/gold_disc8_ai_tag_numeric_tagger_rules.json','tag_recall_csv':'data/runtime_logs/gold_disc8_ai_tag_numeric_tagger_from_review/gold_disc8_ai_tag_numeric_tagger_tag_recall_summary.csv'},'strategy_policy':policies,'embedded_candidates':embedded,'next_step':'manual approval then generate executable demo runtime gate config and wire into live decision pipeline'}
    wjson(paths['config'],cfg)
    wcsv(paths['strategy_policy'],policies,'strategy_id recommended_demo_action gate_mode use_existing_numeric_rules additional_block_rule_count additional_watch_rule_count dispatch_ready_enabled demo_runtime_status reason'.split())
    s={'schema_version':SCHEMA,'cycle_ok':True,'reason':'OK_AUDIT_ONLY_DEMO_RUNTIME_GATE_CANDIDATE_CONFIG','run_id':run_id,'created_at':now(),'counts':{'strategies':len(policies),'additional_block_candidates':len(embedded['additional_block_candidates']),'additional_watch_candidates':len(embedded['additional_watch_candidates'])},'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_enabled':False,'outputs':{k:str(v) for k,v in paths.items()}}
    wjson(paths['summary'],s)
    if a.latest:
        if latest.exists(): shutil.rmtree(windows_long_path(latest))
        mkdirp(latest)
        for p in paths.values(): shutil.copy2(windows_long_path(p),windows_long_path(latest/p.name))
    print(json.dumps(s,ensure_ascii=False,indent=2,sort_keys=True,default=str)); return 0
if __name__=='__main__': raise SystemExit(main())
