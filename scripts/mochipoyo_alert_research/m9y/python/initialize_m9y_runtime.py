from __future__ import annotations
import argparse,json,sys,time
from datetime import UTC,datetime
from pathlib import Path
from typing import Any
import m9y_core as core
MAX_LAG_SECONDS={"M1":0,"M5":2*5*60,"M15":2*15*60,"H1":2*60*60,"H4":2*4*60*60}
def atomic_json(path:Path,value:Any)->None:
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8');tmp.replace(path)
def inspect(data_root:Path,contract:dict[str,Any])->dict[str,Any]:
 out={}
 for tf,fn in contract['data']['live_file_map'].items():
  p=data_root/str(fn)
  if not p.is_file():raise core.M9YContractError(f'missing live GOLD CSV: {p}')
  out[tf]=core.tail_snapshot(p)
 return out
def parse_args():
 p=argparse.ArgumentParser();p.add_argument('--contract',required=True,type=Path);p.add_argument('--data-root',required=True,type=Path);p.add_argument('--runtime-manifest',required=True,type=Path);p.add_argument('--receipt',required=True,type=Path);p.add_argument('--lock-file',required=True,type=Path);p.add_argument('--m9v-runtime-manifest',required=True,type=Path);p.add_argument('--stability-seconds',type=float,default=2.0);return p.parse_args()
def main()->int:
 a=parse_args()
 try:
  if a.lock_file.exists():raise core.M9YContractError('stop M9Y monitor before initialization')
  if a.runtime_manifest.exists():raise core.M9YContractError('M9Y runtime already exists; reset/re-freeze forbidden')
  if not a.m9v_runtime_manifest.is_file():raise core.M9YContractError(f'M9V runtime missing: {a.m9v_runtime_manifest}')
  contract=core.load_json(a.contract);core.validate_contract(contract);m9v=core.load_json(a.m9v_runtime_manifest)
  if m9v.get('stage')!=core.M9V_STAGE or m9v.get('runtime_contract_version')!=core.M9V_RUNTIME_VERSION or m9v.get('reset_allowed') is not False or m9v.get('historical_backfill_allowed') is not False:raise core.M9YContractError('M9V runtime unsuitable for read-only upstream')
  contract_sha=core.sha256_bytes(json.dumps(contract,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
  before=inspect(a.data_root,contract)
  if a.stability_seconds>0:time.sleep(a.stability_seconds)
  after=inspect(a.data_root,contract)
  if before!=after:raise core.M9YContractError('live CSV changed during M9Y start freeze')
  latest={tf:core.parse_time(info['last_server_open']) for tf,info in after.items()};start=latest['M1']
  for tf,t in latest.items():
   lag=(start-t).total_seconds()
   if lag<0:raise core.M9YContractError(f'{tf} ahead of M1 during M9Y freeze')
   if lag>MAX_LAG_SECONDS[tf]:raise core.M9YContractError(f'{tf} lag too large: {lag}s')
  m9v_start=core.parse_time(str(m9v.get('prospective_start_server_time')))
  if m9v_start>=start:raise core.M9YContractError('M9Y fresh start must be strictly after existing M9V start')
  prefixes={tf:core.prefix_fingerprint_rows(a.data_root/fn,int(after[tf]['row_count'])) for tf,fn in contract['data']['live_file_map'].items()}
  now=datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
  runtime={'project':'MOCHIPOYO_ALERT_RESEARCH','stage':core.STAGE,'runtime_status':'FROZEN_FRESH_START','runtime_contract_version':core.RUNTIME_CONTRACT_VERSION,'created_at_utc':now,'prospective_start_server_time':core.fmt_time(start),'contract_sha256':contract_sha,'contract_path':str(a.contract),'data_root':str(a.data_root),'frozen_row_prefixes':prefixes,'prefix_semantics':'IMMUTABLE_ROWS_PRESENT_AT_INITIALIZATION; LATER STRICTLY-ASCENDING APPENDS ALLOWED','m9v_runtime_manifest_path':str(a.m9v_runtime_manifest),'m9v_runtime_manifest_sha256':core.file_sha256(a.m9v_runtime_manifest),'m9v_prospective_start_server_time':m9v.get('prospective_start_server_time'),'m9v_upstream_read_only':True,'pre_start_primary_candidate_eligibility':False,'historical_backfill_allowed':False,'reset_allowed':False,'audit_only':True,'discord_send':False,'mt5_order':False,'live_ready':False,'final_signal':False,'entry_gate_enabled':False}
  atomic_json(a.runtime_manifest,runtime);receipt={'status':'PASS','stage':'M9Y_FRESH_START_INITIALIZATION_AUDIT_ONLY','created_at_utc':now,'prospective_start_server_time':core.fmt_time(start),'runtime_contract_version':core.RUNTIME_CONTRACT_VERSION,'m9v_prospective_start_server_time':m9v.get('prospective_start_server_time'),'m9v_runtime_manifest_sha256':runtime['m9v_runtime_manifest_sha256'],'runtime_manifest':str(a.runtime_manifest),'contract_sha256':contract_sha,'historical_backfill_allowed':False,'reset_allowed':False,'audit_only':True};atomic_json(a.receipt,receipt)
  print('[M9Y INIT PASS] fresh GOLD payoff prospective start frozen');print(json.dumps(receipt,ensure_ascii=False,indent=2));return 0
 except Exception as exc:
  print(f'[M9Y INIT FAIL_CLOSED] {type(exc).__name__}: {exc}',file=sys.stderr);print('[SAFE] M8C/M7C/collector/M9V unchanged.',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
