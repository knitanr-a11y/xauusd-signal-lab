#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,ast,csv,json,shutil,sys
from datetime import datetime
from pathlib import Path
import pandas as pd
SCRIPT_DIR=Path(__file__).resolve().parent
REPO_ROOT=SCRIPT_DIR.parents[1]
for p in [SCRIPT_DIR,REPO_ROOT,REPO_ROOT/'scripts']:
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from build_gold_disc8_ai_tag_numeric_tagger_from_review import clean,resolve,windows_long_path
SCHEMA='gold_disc8_demo_runtime_integration_preflight_v1_audit_only'
DEF_CONFIG=Path('data/runtime_logs/gold_disc8_demo_runtime_gate_candidate_config/latest/gold_disc8_demo_runtime_gate_candidate_config.audit_only.json')
DEF_POLICY=Path('data/runtime_logs/gold_disc8_demo_runtime_gate_candidate_config/latest/gold_disc8_demo_runtime_gate_candidate_config_strategy_policy.csv')
DEF_SAFE=Path('scripts/gold_disc8/run_gold_disc8_live_decision_audit_forever_safe.py')
DEF_ALIGNED=Path('scripts/gold_disc8/run_gold_disc8_live_decision_audit_forever_aligned.py')
DEF_BAT=Path('scripts/gold_disc8/run_gold_disc8_live_decision_audit_forever_aligned.bat')
DEF_OUT=Path('data/runtime_logs/gold_disc8_demo_runtime_integration_preflight')
REQ_ALIGNED=['CANDIDATE_COLUMNS','DEFAULT_GATE_RULES_JSON','DEFAULT_MANIFEST_JSON','DEFAULT_MQL5_FILES_DIR','DEFAULT_OUT_DIR','LEDGER_COLUMNS','LOOP_SUMMARY_COLUMNS','NEAR_MISS_COLUMNS','STALE_ROW_COLUMNS','STRATEGY_DIAGNOSTIC_COLUMNS','finalize_strategy_diag','load_pre_send_tags','parse_manifest','read_json','scan_candidates','ts_text','weekly_dir','windows_long_path','write_csv','write_json']
REQ_CAND_COLS=['decision_key','decision','dispatch_ready','strategy_id','direction','entry_time','gate_status','gate_block_hits','gate_watch_hits','requires_pre_send_tagger','tagger_status','reason']
def now(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def rid(): return datetime.now().strftime('%Y%m%d_%H%M%S')
def mkdirp(p): Path(windows_long_path(Path(p))).mkdir(parents=True,exist_ok=True)
def wjson(p,o): mkdirp(Path(p).parent); open(windows_long_path(Path(p)),'w',encoding='utf-8').write(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True,default=str))
def wcsv(p,rows,cols):
    mkdirp(Path(p).parent)
    with open(windows_long_path(Path(p)),'w',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore'); wr.writeheader()
        for r in rows: wr.writerow({c:r.get(c,'') for c in cols})
def rjson(p):
    with open(windows_long_path(resolve(Path(p))),encoding='utf-8-sig') as f: return json.load(f)
def rcsv(p): return pd.read_csv(windows_long_path(resolve(Path(p))),encoding='utf-8-sig',sep=None,engine='python')
def read_text(p): return open(windows_long_path(resolve(Path(p))),encoding='utf-8-sig').read()
def audit(label,path,required,note):
    p=resolve(Path(path)); return {'label':label,'path':str(p),'exists':p.exists(),'required':required,'status':'OK' if p.exists() else ('MISSING_REQUIRED' if required else 'MISSING_OPTIONAL'),'note':note}
def parse_source(label,path):
    p=resolve(Path(path)); r={'label':label,'path':str(p),'parse_ok':False,'line_count':0,'defined_names':'','missing_required_names':'','status':'UNKNOWN','note':''}
    try:
        txt=read_text(p); r['line_count']=txt.count('\n')+1
        tree=ast.parse(txt,filename=str(p)); r['parse_ok']=True
        names=set()
        for n in tree.body:
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)): names.add(n.name)
            elif isinstance(n,ast.Assign):
                for t in n.targets:
                    if isinstance(t,ast.Name): names.add(t.id)
        r['defined_names']=' | '.join(sorted(names))
        if label=='aligned_py':
            miss=[x for x in REQ_ALIGNED if x not in names]
            r['missing_required_names']=' | '.join(miss); r['status']='OK' if not miss else 'MISSING_REQUIRED_NAMES'
        elif label=='safe_py':
            miss=[x for x in ['force_dispatch_sealed','dedup_ledger_rows','run_iteration','main'] if x not in names]
            r['missing_required_names']=' | '.join(miss); r['status']='OK' if not miss else 'MISSING_REQUIRED_NAMES'
        else: r['status']='OK'
    except SyntaxError as e:
        r['status']='SYNTAX_ERROR'; r['note']=f'{e.msg} line={e.lineno} offset={e.offset}'
    except Exception as e:
        r['status']='READ_OR_PARSE_ERROR'; r['note']=type(e).__name__+': '+str(e)
    return r
def check_config(cfg,policy):
    rows=[]
    def add(k,ok,detail): rows.append({'check':k,'ok':bool(ok),'status':'OK' if ok else 'NG','detail':detail})
    add('config_audit_only',cfg.get('audit_only') is True,str(cfg.get('audit_only')))
    add('config_not_runtime',cfg.get('do_not_use_as_runtime_config') is True,str(cfg.get('do_not_use_as_runtime_config')))
    add('dispatch_disabled',cfg.get('dispatch_ready_enabled') is False,str(cfg.get('dispatch_ready_enabled')))
    safe=cfg.get('safety',{}) if isinstance(cfg.get('safety'),dict) else {}
    for k in ['no_ai_api_call','no_discord_send','no_mt5_order_send','sot_mutated','runtime_gate_rules_mutated','live_decision_ledger_mutated']:
        expected=False if k.endswith('mutated') else True
        add('safety_'+k,safe.get(k)==expected,str(safe.get(k)))
    add('strategy_policy_count_8',len(policy)==8,str(len(policy)))
    add('additional_block_candidates_present',len(cfg.get('embedded_candidates',{}).get('additional_block_candidates',[]))>=1,str(len(cfg.get('embedded_candidates',{}).get('additional_block_candidates',[]))))
    add('additional_watch_candidates_present',len(cfg.get('embedded_candidates',{}).get('additional_watch_candidates',[]))>=1,str(len(cfg.get('embedded_candidates',{}).get('additional_watch_candidates',[]))))
    return rows
def integration_rows(cfg,policy):
    rows=[]
    for _,r in policy.iterrows():
        sid=clean(r.get('strategy_id')); mode=clean(r.get('gate_mode'))
        if mode=='ADDITIONAL_NUMERIC_BLOCK_CANDIDATE': target='safe.py run_iteration after scan_candidates, before force_dispatch_sealed'; action='evaluate additional candidate rules and set decision BLOCK/WATCH in audit-only first'
        elif mode=='ADDITIONAL_NUMERIC_WATCH_ONLY': target='same hook, watch annotation only'; action='write WATCH_ONLY/gate_watch_hits but keep dispatch false during audit'
        elif mode in ['EXISTING_NUMERIC_BLOCK_GATE','EXISTING_NUMERIC_GATE_WATCH']: target='aligned scan_candidates existing gate path'; action='verify existing gate_status/gate_block_hits/gate_watch_hits already appears in candidate ledger'
        else: target='no automatic numeric gate hook'; action='keep pending tagger/manual or future side-specific audit'
        rows.append({'strategy_id':sid,'gate_mode':mode,'recommended_demo_action':clean(r.get('recommended_demo_action')),'proposed_integration_hook':target,'preflight_action':action,'dispatch_ready_enabled':False,'status':'AUDIT_ONLY_PRECONNECT'})
    return rows
def parse():
    p=argparse.ArgumentParser(description='Preflight audit before wiring DISC8 demo runtime gate candidate into live decision pipeline.')
    p.add_argument('--candidate-config-json',type=Path,default=DEF_CONFIG); p.add_argument('--strategy-policy-csv',type=Path,default=DEF_POLICY); p.add_argument('--safe-py',type=Path,default=DEF_SAFE); p.add_argument('--aligned-py',type=Path,default=DEF_ALIGNED); p.add_argument('--aligned-bat',type=Path,default=DEF_BAT); p.add_argument('--out-root',type=Path,default=DEF_OUT); p.add_argument('--run-id',default=''); p.add_argument('--no-latest-copy',action='store_false',dest='latest',default=True); return p.parse_args()
def main():
    a=parse(); run_id=a.run_id or rid(); root=resolve(a.out_root); run=root/'runs'/run_id; latest=root/'latest'; mkdirp(run)
    files={'candidate_config_json':a.candidate_config_json,'strategy_policy_csv':a.strategy_policy_csv,'safe_py':a.safe_py,'aligned_py':a.aligned_py,'aligned_bat':a.aligned_bat}
    paths={'input_audit':run/'gold_disc8_demo_runtime_integration_preflight_input_audit.csv','source_health':run/'gold_disc8_demo_runtime_integration_preflight_source_health.csv','config_checks':run/'gold_disc8_demo_runtime_integration_preflight_config_checks.csv','integration_plan':run/'gold_disc8_demo_runtime_integration_preflight_plan.csv','summary':run/'gold_disc8_demo_runtime_integration_preflight_summary.json'}
    audits=[audit(k,v,True,'preflight input') for k,v in files.items()]; wcsv(paths['input_audit'],audits,'label path exists required status note'.split())
    missing=[r['label'] for r in audits if r['required'] and not r['exists']]
    if missing:
        s={'schema_version':SCHEMA,'cycle_ok':False,'reason':'STOP_MISSING_INPUT','missing':missing,'run_id':run_id,'created_at':now(),'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'dispatch_ready_enabled':False,'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 2
    cfg=rjson(a.candidate_config_json); pol=rcsv(a.strategy_policy_csv)
    source=[parse_source('safe_py',a.safe_py),parse_source('aligned_py',a.aligned_py)]
    bat_txt=read_text(a.aligned_bat); source.append({'label':'aligned_bat','path':str(resolve(a.aligned_bat)),'parse_ok':True,'line_count':bat_txt.count('\n')+1,'defined_names':'','missing_required_names':'','status':'OK' if 'run_gold_disc8_live_decision_audit_forever_safe.py' in bat_txt and 'dispatch_ready' in bat_txt else 'CHECK_BAT_TEXT','note':'checks safe wrapper reference and dispatch wording'})
    checks=check_config(cfg,pol); plan=integration_rows(cfg,pol)
    wcsv(paths['source_health'],source,'label path parse_ok line_count defined_names missing_required_names status note'.split())
    wcsv(paths['config_checks'],checks,'check ok status detail'.split())
    wcsv(paths['integration_plan'],plan,'strategy_id gate_mode recommended_demo_action proposed_integration_hook preflight_action dispatch_ready_enabled status'.split())
    bad_source=[r for r in source if r['status']!='OK']; bad_checks=[r for r in checks if not r['ok']]
    cycle_ok=not bad_source and not bad_checks
    reason='OK_AUDIT_ONLY_PREFLIGHT_READY_FOR_MANUAL_REVIEW' if cycle_ok else 'STOP_PREFLIGHT_FOUND_BLOCKERS'
    s={'schema_version':SCHEMA,'cycle_ok':cycle_ok,'reason':reason,'run_id':run_id,'created_at':now(),'counts':{'strategy_policy_rows':len(pol),'source_blockers':len(bad_source),'config_blockers':len(bad_checks)},'blockers':{'source_health':[r for r in bad_source],'config_checks':[r for r in bad_checks]},'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_enabled':False,'next_step':'If cycle_ok=true, manually review integration_plan before creating executable demo gate config. If false, fix blockers first.','outputs':{k:str(v) for k,v in paths.items()}}
    wjson(paths['summary'],s)
    if a.latest:
        if latest.exists(): shutil.rmtree(windows_long_path(latest))
        mkdirp(latest)
        for p in paths.values(): shutil.copy2(windows_long_path(p),windows_long_path(latest/p.name))
    print(json.dumps(s,ensure_ascii=False,indent=2,sort_keys=True,default=str)); return 0 if cycle_ok else 4
if __name__=='__main__': raise SystemExit(main())
