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
SCHEMA='gold_disc8_wf_guard_impact_vs_total_v1_audit_only'
DEF_BASE=Path('data/runtime_logs/gold_disc8_ai_tag_vs_numeric_gate_replay_568/latest/gold_disc8_ai_tag_vs_numeric_gate_replay_568_trade_audit.csv')
DEF_WF=Path('data/runtime_logs/gold_disc8_candidate_gate_walk_forward/latest/gold_disc8_candidate_gate_walk_forward_test_assignments.csv')
DEF_OUT=Path('data/runtime_logs/gold_disc8_wf_guard_impact_vs_total')
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
def val(r): return float(sf(r.get('profit_r_num'),0.0) or 0.0)
def mon(r):
    m=clean(r.get('entry_month'))
    return m[:7] if m else clean(r.get('entry_time'))[:7]
def st(rows):
    vs=[val(r) for r in rows]; m=metrics(vs)
    return {'count':len(rows),'win_count':sum(v>0 for v in vs),'loss_count':sum(v<0 for v in vs),'win_rate':fm(m['win_rate']),'profit_factor':fm(m['profit_factor']),'avg_r':fm(m['avg_r']),'total_r':fm(m['total_r']),'ai_block_count':sum(clean(r.get('ai_decision'))=='AI_BLOCK' for r in rows),'ai_allow_count':sum(clean(r.get('ai_decision'))=='AI_ALLOW' for r in rows)}
def pref(p,s): return {p+'_'+k:v for k,v in s.items()}
def cmp(scope,key,scenario,before,guard):
    gids={clean(r['trade_id']) for r in guard}; after=[r for r in before if clean(r['trade_id']) not in gids]
    bs,gs,as_=st(before),st(guard),st(after); bt=float(bs['total_r'] or 0); gt=float(gs['total_r'] or 0); at=float(as_['total_r'] or 0)
    out={'scope':scope,'key':key,'scenario':scenario,'delta_total_r':fm(at-bt),'guard_total_r_share_of_before':fm(None if bt==0 else gt/bt)}
    out.update(pref('before',bs)); out.update(pref('guard',gs)); out.update(pref('after',as_)); return out
def parse():
    p=argparse.ArgumentParser(description='Compare walk-forward guard hits against total performance. Audit-only.')
    p.add_argument('--base-trade-audit-csv',type=Path,default=DEF_BASE)
    p.add_argument('--walk-forward-assignments-csv',type=Path,default=DEF_WF)
    p.add_argument('--out-root',type=Path,default=DEF_OUT)
    p.add_argument('--run-id',default='')
    p.add_argument('--no-latest-copy',action='store_false',dest='latest',default=True)
    return p.parse_args()
def main():
    a=parse(); run_id=a.run_id or rid(); root=resolve(a.out_root); run=root/'runs'/run_id; latest=root/'latest'; mkdirp(run)
    paths={'monthly':run/'gold_disc8_wf_guard_impact_vs_total_monthly_summary.csv','strategy_monthly':run/'gold_disc8_wf_guard_impact_vs_total_strategy_monthly_summary.csv','overall':run/'gold_disc8_wf_guard_impact_vs_total_overall_summary.csv','summary':run/'gold_disc8_wf_guard_impact_vs_total_summary.json'}
    if not resolve(a.base_trade_audit_csv).exists() or not resolve(a.walk_forward_assignments_csv).exists():
        s={'schema_version':SCHEMA,'cycle_ok':False,'reason':'STOP_MISSING_INPUT','base':str(resolve(a.base_trade_audit_csv)),'wf':str(resolve(a.walk_forward_assignments_csv)),'outputs':{k:str(v) for k,v in paths.items()}}; wjson(paths['summary'],s); print(json.dumps(s,ensure_ascii=False,indent=2)); return 2
    base=rcsv(a.base_trade_audit_csv).to_dict('records'); wf=rcsv(a.walk_forward_assignments_csv).to_dict('records')
    byid={clean(r['trade_id']):r for r in base}; test_months=sorted({mon(r) for r in wf if mon(r)})
    scenario_ids={
        'WF_ALL_GUARD':{clean(r['trade_id']) for r in wf if clean(r.get('selected_classification'))=='BLOCK_CANDIDATE'},
        'WF_DISC08_ONLY':{clean(r['trade_id']) for r in wf if clean(r.get('selected_classification'))=='BLOCK_CANDIDATE' and clean(r.get('strategy_id'))=='DISC_08_BUY_TP200_SL100_RR2'},
        'WF_DISC01_REFERENCE':{clean(r['trade_id']) for r in wf if clean(r.get('selected_classification'))=='BLOCK_CANDIDATE' and clean(r.get('strategy_id'))=='DISC_01_BUY_TP200_SL100_RR2'},
    }
    scenarios=list(scenario_ids.keys()); months=sorted({mon(r) for r in base if mon(r)})
    overall=[]; monthly=[]; sm=[]
    oos=[r for r in base if mon(r) in test_months]
    for sc in scenarios:
        guards=[byid[t] for t in scenario_ids[sc] if t in byid]
        overall.append(cmp('ALL','ALL_MONTHS',sc,base,guards))
        overall.append(cmp('OOS','OOS_MONTHS',sc,oos,[r for r in guards if mon(r) in test_months]))
        for m in months:
            b=[r for r in base if mon(r)==m]; g=[r for r in guards if mon(r)==m]
            monthly.append(cmp('MONTH',m,sc,b,g))
            for sid in sorted({clean(r.get('strategy_id')) for r in b}):
                bb=[r for r in b if clean(r.get('strategy_id'))==sid]; gg=[r for r in g if clean(r.get('strategy_id'))==sid]
                sm.append(cmp('MONTH_STRATEGY',m+'|'+sid,sc,bb,gg))
    cols=list(overall[0].keys()); wcsv(paths['overall'],overall,cols); wcsv(paths['monthly'],monthly,cols); wcsv(paths['strategy_monthly'],sm,cols)
    s={'schema_version':SCHEMA,'cycle_ok':True,'reason':'OK_AUDIT_ONLY_WF_GUARD_IMPACT_VS_TOTAL','run_id':run_id,'created_at':now(),'months':months,'oos_months':test_months,'scenario_highlights':{r['scenario']+'_'+r['scope']:r for r in overall},'notes':{'WF_ALL_GUARD':'adaptive walk-forward guard hits, includes DISC_01 reference risk','WF_DISC08_ONLY':'DISC_08 only, closer to final hard-guard idea','WF_DISC01_REFERENCE':'reference only; final policy should keep DISC_01 as watch, not hard guard'},'no_ai_api_call':True,'no_discord_send':True,'no_mt5_order_send':True,'sot_mutated':False,'runtime_gate_rules_mutated':False,'live_decision_ledger_mutated':False,'dispatch_ready_enabled':False,'outputs':{k:str(v) for k,v in paths.items()}}
    wjson(paths['summary'],s)
    if a.latest:
        if latest.exists(): shutil.rmtree(windows_long_path(latest))
        mkdirp(latest)
        for p in paths.values(): shutil.copy2(windows_long_path(p),windows_long_path(latest/p.name))
    print(json.dumps(s,ensure_ascii=False,indent=2,sort_keys=True,default=str)); return 0
if __name__=='__main__': raise SystemExit(main())
