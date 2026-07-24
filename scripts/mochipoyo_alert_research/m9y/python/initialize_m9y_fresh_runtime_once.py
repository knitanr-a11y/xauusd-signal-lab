from __future__ import annotations
import json,math,os,subprocess,sys
from pathlib import Path
THIS=Path(__file__).resolve();REPO_ROOT=THIS.parents[4];INITIALIZER=THIS.parent/'initialize_m9y_runtime.py';CONTRACT=REPO_ROOT/'config'/'mochipoyo_alert_research'/'m9y_gold_payoff_fresh_prospective_shadow_contract_20260724.json'
def main()->int:
 local=Path(os.environ.get('LOCALAPPDATA',''))/'xauusd_signal_lab'/'mochipoyo_alert_research';metadata_path=local/'outputs'/'M8B'/'LATEST'/'06_symbol_metadata.json'
 try:
  if not metadata_path.is_file():raise RuntimeError(f'M8B symbol metadata missing: {metadata_path}')
  md=json.loads(metadata_path.read_text(encoding='utf-8'));mt5=Path(str(md.get('mt5_files_root','')));point=float(md.get('symbols',{}).get('XAUUSD',{}).get('point','nan'))
  if not mt5.is_dir() or not math.isfinite(point):raise RuntimeError(f'MT5 root or XAUUSD point unavailable: {mt5} point={point}')
  rt=local/'m9y_runtime';m9v=local/'m9v_runtime'/'m9v_runtime_manifest.json';cmd=[sys.executable,str(INITIALIZER),'--contract',str(CONTRACT),'--data-root',str(mt5),'--runtime-manifest',str(rt/'m9y_runtime_manifest.json'),'--receipt',str(rt/'m9y_runtime_start_receipt.json'),'--lock-file',str(rt/'m9y_shadow_loop.lock'),'--m9v-runtime-manifest',str(m9v),'--stability-seconds','2']
  return int(subprocess.run(cmd,cwd=REPO_ROOT,check=False).returncode)
 except Exception as exc:
  print(f'[M9Y INIT FAIL_CLOSED] {type(exc).__name__}: {exc}',file=sys.stderr);print('[SAFE] M8C/M7C/collector/M9V unchanged.',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
