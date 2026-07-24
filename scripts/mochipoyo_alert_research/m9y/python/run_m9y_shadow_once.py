from __future__ import annotations
import json,math,os,shutil,sys,zipfile
from datetime import UTC,datetime
from pathlib import Path
from typing import Any
import m9y_core as core

THIS=Path(__file__).resolve(); REPO_ROOT=THIS.parents[4] if len(THIS.parents)>4 else THIS.parents[2]
DEFAULT_CONTRACT=REPO_ROOT/'config'/'mochipoyo_alert_research'/'m9y_gold_payoff_fresh_prospective_shadow_contract_20260724.json'

def write_csv(path:Path,rows:list[dict[str,Any]])->None: core.m9p.write_csv(path,rows)
def dump_json(path:Path,v:Any)->None: core.m9p.dump_json(path,v)

def resolve_environment()->tuple[Path,float,Path,Path,Path,Path]:
    local_root=Path(os.environ.get('LOCALAPPDATA',''))/'xauusd_signal_lab'/'mochipoyo_alert_research'
    metadata_path=local_root/'outputs'/'M8B'/'LATEST'/'06_symbol_metadata.json'
    if not metadata_path.is_file(): raise core.M9YContractError(f'M8B symbol metadata missing: {metadata_path}')
    metadata=json.loads(metadata_path.read_text(encoding='utf-8'))
    mt5_root=Path(str(metadata.get('mt5_files_root',''))); point=float(metadata.get('symbols',{}).get('XAUUSD',{}).get('point','nan'))
    if not mt5_root.is_dir() or not math.isfinite(point): raise core.M9YContractError(f'MT5 root or point unavailable: {mt5_root} point={point}')
    return mt5_root,point,local_root/'m9y_runtime'/'m9y_runtime_manifest.json',local_root/'outputs'/'M9Y',local_root/'m9v_runtime'/'m9v_runtime_manifest.json',local_root/'outputs'/'M9V'/'LATEST'

def grouped(rows:list[dict[str,Any]],mode:str)->list[dict[str,Any]]:
    groups={}
    for row in rows:
        if row.get('weighted_return_bps') is None: continue
        dt=core.parse_time(str(row['actual_entry_time']))
        label=str(dt.year) if mode=='year' else (f'{dt.year}Q{(dt.month-1)//3+1}' if mode=='quarter' else f'{dt.year}-{dt.month:02d}')
        groups.setdefault(label,[]).append(row)
    return [{mode:k,**core._metrics(v)} for k,v in sorted(groups.items())]

def main()->int:
    try:
        contract_path=Path(os.environ.get('M9Y_CONTRACT',str(DEFAULT_CONTRACT)))
        data_override=os.environ.get('M9Y_GOLD_DATA_ROOT'); point_override=os.environ.get('M9Y_POINT'); runtime_override=os.environ.get('M9Y_RUNTIME_MANIFEST'); output_override=os.environ.get('M9Y_OUTPUT_ROOT')
        if data_override and point_override and runtime_override:
            data_root=Path(data_override);point=float(point_override);runtime_path=Path(runtime_override);output_root=Path(output_override or '/tmp/m9y_output');m9v_runtime_path=Path(os.environ['M9Y_M9V_RUNTIME_MANIFEST']);m9v_latest_dir=Path(os.environ['M9Y_M9V_LATEST_DIR'])
        else:
            data_root,point,runtime_path,output_root,m9v_runtime_path,m9v_latest_dir=resolve_environment()
            if data_override:data_root=Path(data_override)
            if point_override is not None:point=float(point_override)
            if runtime_override:runtime_path=Path(runtime_override)
            if output_override:output_root=Path(output_override)
        contract=core.load_json(contract_path);core.validate_contract(contract)
        if not runtime_path.is_file(): raise core.M9YContractError(f'M9Y runtime missing; initialize once first: {runtime_path}')
        runtime=core.load_json(runtime_path)
        result=core.audit(data_root=data_root,contract=contract,runtime=runtime,point=point,m9v_runtime_path=m9v_runtime_path,m9v_latest_dir=m9v_latest_dir)
        arm_metrics=result['arm_metrics']; review=contract['review_gates']; y0=len(result['arms']['Y0_W1_NATIVE_EXIT']); n6=sum(bool(r['N6_at_actual_entry']) for r in result['candidates'])
        summary={'project':'MOCHIPOYO_ALERT_RESEARCH','stage':core.STAGE,'status':'PASS_FRESH_PROSPECTIVE_AUDIT_ONLY','built_at_utc':datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
                 'prospective_start_server_time':result['start_server_time'],'latest_server_open':result['latest_server_open'],'upstream_s2_post_start_count':result['upstream_s2_post_start_count'],'w1_candidate_count':result['w1_candidate_count'],
                 'pending_count':len(result['pending']),'skipped_reclaim_count':len(result['skipped']),'overlap_skip_count':len(result['overlaps']),'arm_metrics':arm_metrics,
                 'review_readiness':{'operational_checkpoint':y0>=int(review['operational_checkpoint_Y0_accepted']),'interim_checkpoint':y0>=int(review['interim_checkpoint_Y0_accepted']),
                                     'minimum_N6_flagged_entries':n6>=int(review['minimum_N6_flagged_entries_for_risk_review']),'formal_checkpoint':y0>=int(review['formal_checkpoint_Y0_accepted']),'automatic_live_promotion':False},
                 'guardrails':{'audit_only':True,'historical_backfill':False,'pre_start_primary_candidate_eligibility':False,'one_position_per_arm':True,'m9v_modified_or_reset':False,'discord_send':False,'mt5_order':False,'live_ready':False,'final_signal':False}}
        stamp=datetime.now(UTC).strftime('%Y%m%d_%H%M%S');archive=output_root/'archive'/stamp;archive.mkdir(parents=True,exist_ok=False)
        (archive/'00_READ_ME_FIRST.txt').write_text('M9Y is a NEW fresh GOLD payoff audit-only shadow. It is separate from M9V. Y0=W1 native exit, Y1=+N6 sizing, Y2=+50% selective runner, Y3=+75% selective runner. One-position accounting is enforced per arm. No backfill/live promotion.\n',encoding='utf-8')
        dump_json(archive/'01_summary.json',summary);write_csv(archive/'02_w1_candidate_ledger.csv',result['candidates']);write_csv(archive/'03_pending_reclaim.csv',result['pending']);write_csv(archive/'04_skipped_reclaim.csv',result['skipped'])
        for i,name in enumerate(('Y0_W1_NATIVE_EXIT','Y1_W1_N6_NATIVE_EXIT','Y2_W1_N6_RUNNER50','Y3_W1_N6_RUNNER75'),start=5): write_csv(archive/f'{i:02d}_{name}_ledger.csv',result['arms'][name])
        write_csv(archive/'09_overlap_skip_metadata.csv',result['overlaps']);dump_json(archive/'10_upstream_reference.json',{'m9v_upstream_start_server_time':result['m9v_upstream_start_server_time'],'m9v_runtime_manifest':str(m9v_runtime_path),'m9v_latest_dir':str(m9v_latest_dir)});dump_json(archive/'11_runtime_manifest_copy.json',runtime)
        dump_json(archive/'12_data_quality.json',{'data_root':str(data_root),'point':point,'closed_rows_contract':True,'nearest_m1_fallback':False,'prefix_integrity_verified':True,'latest_server_open':result['latest_server_open']})
        periods=[]
        for name,rows in result['arms'].items():
            for mode in ('month','quarter','year'):
                for row in grouped(rows,mode):periods.append({'arm':name,'period_mode':mode,**row})
        write_csv(archive/'13_arm_period_metrics.csv',periods)
        (archive/'14_audit.log').write_text('\n'.join(['status=PASS_FRESH_PROSPECTIVE_AUDIT_ONLY',f"start={result['start_server_time']}",f"upstream_s2={result['upstream_s2_post_start_count']}",f"w1={result['w1_candidate_count']}",*(f'{k}={len(v)}' for k,v in result['arms'].items()),f"overlap_skips={len(result['overlaps'])}",'historical_backfill=false','m9v_modified_or_reset=false','discord_send=false','mt5_order=false','']),encoding='utf-8')
        names=[p.name for p in archive.iterdir() if p.is_file()]
        with zipfile.ZipFile(archive/'99_UPLOAD_PACKAGE.zip','w',zipfile.ZIP_DEFLATED) as z:
            for name in sorted(names): z.write(archive/name,name)
        latest=output_root/'LATEST';shutil.rmtree(latest,ignore_errors=True);shutil.copytree(archive,latest)
        print(f"[M9Y PASS] W1={result['w1_candidate_count']} Y0={len(result['arms']['Y0_W1_NATIVE_EXIT'])} Y1={len(result['arms']['Y1_W1_N6_NATIVE_EXIT'])} Y2={len(result['arms']['Y2_W1_N6_RUNNER50'])} Y3={len(result['arms']['Y3_W1_N6_RUNNER75'])}")
        print('[M9Y OUTPUT]',latest);return 0
    except Exception as exc:
        print(f'[M9Y BLOCKED] {type(exc).__name__}: {exc}',file=sys.stderr);print('[SAFE] M8C/M7C/collector/M9V are not modified by M9Y.',file=sys.stderr);return 2
if __name__=='__main__': raise SystemExit(main())
