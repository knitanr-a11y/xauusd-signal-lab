from __future__ import annotations
import argparse, json, sys, traceback
from datetime import datetime
from pathlib import Path
import pandas as pd
from cost_stress_contract import BRIDGE, RAW, backup_output, load_json, load_registries, scenarios_from, sha256_file, validate_config, verify_bridge, verify_raw
from cost_stress_engine import M1Engine, replay
from cost_stress_reports import candidate_summary, json_clean, lineage_summary, overall_gate, records, write_csvs, write_text_summary, year_summary

def run(args:argparse.Namespace)->int:
    output=args.output_dir.resolve(); backup=backup_output(output); config_path=args.config.resolve(); config=load_json(config_path); candidates,lineage_by_candidate=validate_config(config); scenarios=scenarios_from(config); raw_dir=args.raw_dir.resolve(); bridge_dir=args.bridge_dir.resolve()
    if not bridge_dir.exists(): raise FileNotFoundError(bridge_dir)
    raw_audit=verify_raw(raw_dir,config); bridge_audit=verify_bridge(bridge_dir,config,candidates); registry,registry_audit=load_registries(bridge_dir,config,candidates,lineage_by_candidate); engine=M1Engine(pd.read_csv(raw_dir/'gold_v3_2023_2026_m1.csv')); trades,checks=replay(registry,engine,config,lineage_by_candidate,scenarios)
    expected=len(registry)*len(scenarios)
    if len(trades)!=expected: raise RuntimeError(f'Trade/scenario rows {len(trades)} != {expected}')
    candidate=candidate_summary(trades,config); year=year_summary(trades,config); lineage=lineage_summary(candidate); gate=overall_gate(candidate,len(scenarios))
    if set(gate.candidate_id.astype(str))!=set(candidates): raise RuntimeError('Overall gate candidate set mismatch')
    write_csvs(output,trades,candidate,year,lineage,gate); config_hash=sha256_file(config_path)
    provenance={'run_status':'PASS','run_time_local':datetime.now().isoformat(timespec='seconds'),'config':str(config_path),'config_sha256':config_hash,'raw_dir':str(raw_dir),'bridge_dir':str(bridge_dir),'output_dir':str(output),'previous_output_backup':str(backup) if backup else None,'raw_audit':raw_audit,'bridge_audit':bridge_audit,'registry_audit':registry_audit,'baseline_parity_checks':checks,'scenario_count':len(scenarios),'trade_scenario_rows':len(trades),'audit_only':True}
    (output/'input_provenance.json').write_text(json.dumps(json_clean(provenance),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    passes=int((gate.candidate_overall_stress_gate=='PASS').sum()); fails=int((gate.candidate_overall_stress_gate=='FAIL').sum())
    summary={'status':'PASS','exit_code':0,'phase':config['phase'],'audit_only':True,'primary_population':RAW,'bridge_population':BRIDGE,'scenario_grid':[x.__dict__ for x in scenarios],'baseline_parity_checks':checks,'candidate_overall_gate':records(gate),'candidate_overall_gate_counts':{'PASS':passes,'FAIL':fails},'raw_candidate_scenario_results':records(candidate[candidate.population==RAW]),'bridge_candidate_scenario_results':records(candidate[candidate.population==BRIDGE]),'raw_lineage_results':records(lineage[lineage.population==RAW]),'bridge_lineage_results':records(lineage[lineage.population==BRIDGE]),'caveats':config['caveats'],'blockers':['Fresh prospective confirmation from goldsharp closed bars after 2026-06-23 18:15:00 MT5 server close is incomplete.','Registration, promotion and all live switches remain unauthorized and OFF.'],'automatic_next_action':None,'execution_switches':config['execution_switches']}
    (output/'cost_stress_summary.json').write_text(json.dumps(json_clean(summary),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8'); write_text_summary(output,config_path,config_hash,backup,scenarios,checks,registry,candidate,gate); (output/'COST_STRESS_RUN_ERROR.txt').write_text('status=PASS\nerror=NONE\n',encoding='utf-8')
    missing=sorted(set(config['required_outputs'])-{x.name for x in output.iterdir() if x.is_file()})
    if missing: raise RuntimeError(f'Required outputs missing: {missing}')
    print('='*72); print('GOLD_ML_V1 COST STRESS — RUN STATUS: PASS'); print(f'Baseline parity checks: {checks}'); print(f'Candidate stress gate: PASS={passes} FAIL={fails}'); print('No automatic promotion, registration, prospective step or live action was performed.'); print('='*72); return 0

def main()->int:
    parser=argparse.ArgumentParser(description='Audit-only cost stress for frozen GOLD_ML_V1 nine candidates'); parser.add_argument('--raw-dir',type=Path,required=True); parser.add_argument('--bridge-dir',type=Path,required=True); parser.add_argument('--config',type=Path,required=True); parser.add_argument('--output-dir',type=Path,default=Path('outputs/gold_ml_v1/cost_stress_raw_reconstructed')); args=parser.parse_args()
    try: return run(args)
    except Exception as exc:
        output=args.output_dir.resolve(); output.mkdir(parents=True,exist_ok=True); (output/'COST_STRESS_RUN_ERROR.txt').write_text(traceback.format_exc(),encoding='utf-8'); lines=['GOLD_ML_V1 COST STRESS','run_status=FAIL','exit_code=4',f"run_time_local={datetime.now().isoformat(timespec='seconds')}",f'error_type={type(exc).__name__}',f'error={exc}','automatic_next_action=NONE','live_ready=false']; (output/'LATEST_RUN_SUMMARY.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(f'[FAIL] {type(exc).__name__}: {exc}',file=sys.stderr); return 4
if __name__=='__main__': raise SystemExit(main())
