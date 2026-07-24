from __future__ import annotations
import argparse,json,os,subprocess,sys,time
from datetime import UTC,datetime
from pathlib import Path
THIS=Path(__file__).resolve();ONE_SHOT=THIS.parent/'run_m9y_shadow_once.py';STOP='STOP_M9Y_SHADOW_LOOP';LOCK='m9y_shadow_loop.lock'
def utc():return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
def atom(path,v):path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)
def main()->int:
 local=Path(os.environ.get('LOCALAPPDATA',''))/'xauusd_signal_lab'/'mochipoyo_alert_research';rt=local/'m9y_runtime';log=local/'logs'/'m9y';stop=rt/STOP;lock=rt/LOCK;runtime=rt/'m9y_runtime_manifest.json';status=log/'latest_m9y_shadow_loop_status.json';logfile=log/'m9y_shadow_forever.log'
 if not runtime.is_file():print('[M9Y LOOP BLOCKED] runtime missing',file=sys.stderr);return 2
 try: fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
 except FileExistsError:print('[M9Y LOOP BLOCKED] loop lock exists',file=sys.stderr);return 2
 stop.unlink(missing_ok=True);cycles=ok=failed=0;started=utc()
 try:
  while True:
   if stop.exists():break
   cycles+=1;cp=subprocess.run([sys.executable,str(ONE_SHOT)],capture_output=True,text=True,encoding='utf-8',errors='replace')
   log.mkdir(parents=True,exist_ok=True)
   with logfile.open('a',encoding='utf-8') as f:f.write(f'\n===== cycle {cycles} {utc()} rc={cp.returncode} =====\n'+cp.stdout+'\n'+cp.stderr)
   if cp.stdout:print(cp.stdout.rstrip())
   if cp.stderr:print(cp.stderr.rstrip(),file=sys.stderr)
   if cp.returncode==0:ok+=1
   else:failed+=1
   payload={'status':'RUNNING' if cp.returncode==0 else 'BLOCKED','stage':'M9Y_GOLD_PAYOFF_FRESH_PROSPECTIVE_SHADOW','audit_only':True,'started_at_utc':started,'updated_at_utc':utc(),'cycles':cycles,'successful_cycles':ok,'failed_cycles':failed,'last_exit_code':cp.returncode,'m9v_reset':False,'discord_send':False,'mt5_order':False};atom(status,payload)
   if cp.returncode==2:return 2
   deadline=time.monotonic()+60
   while time.monotonic()<deadline and not stop.exists():time.sleep(min(1,max(0,deadline-time.monotonic())))
  atom(status,{'status':'STOPPED','stage':'M9Y_GOLD_PAYOFF_FRESH_PROSPECTIVE_SHADOW','updated_at_utc':utc(),'cycles':cycles,'successful_cycles':ok,'failed_cycles':failed,'m9v_reset':False});return 0
 finally:lock.unlink(missing_ok=True)
if __name__=='__main__':raise SystemExit(main())
