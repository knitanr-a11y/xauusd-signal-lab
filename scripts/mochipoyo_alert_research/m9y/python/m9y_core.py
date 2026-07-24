from __future__ import annotations

import bisect
import csv
import hashlib
import io
import json
import math
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
M9V_DIR = THIS.parents[2] / "m9v" / "python"
M9P_DIR = THIS.parents[2] / "m9p" / "python"
for directory in (M9V_DIR, M9P_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
import m9v_core as m9v
import m9v_core_v2 as m9v2
import run_gold_dynamic_core_reproduction_audit as m9p

STAGE = "M9Y_GOLD_PAYOFF_FRESH_PROSPECTIVE_SHADOW"
RUNTIME_CONTRACT_VERSION = "M9Y_RUNTIME_V1_APPEND_SAFE_PREFIX"
TIME_FORMAT = m9p.TIME_FORMAT
ARMS = {
    "Y0_W1_NATIVE_EXIT": {"risk_n6": False, "runner_share": 0.0},
    "Y1_W1_N6_NATIVE_EXIT": {"risk_n6": True, "runner_share": 0.0},
    "Y2_W1_N6_RUNNER50": {"risk_n6": True, "runner_share": 0.50},
    "Y3_W1_N6_RUNNER75": {"risk_n6": True, "runner_share": 0.75},
}
RECLAIM_OFFSET_ATR = 0.10
RECLAIM_WAIT_MINUTES = 10
M9V_STAGE = "M9V_GOLD_MULTI_TIMEFRAME_FRESH_PROSPECTIVE_SHADOW"
M9V_RUNTIME_VERSION = "M9V_RUNTIME_V2_APPEND_SAFE_PREFIX"

class M9YContractError(RuntimeError):
    pass

def parse_time(text: str) -> datetime:
    return datetime.strptime(text, TIME_FORMAT)
def fmt_time(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)
def load_json(path: Path) -> dict[str, Any]:
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: raise M9YContractError(f"cannot read JSON: {path}") from exc
    if not isinstance(value,dict): raise M9YContractError(f"JSON is not object: {path}")
    return value
def sha256_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def file_sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def tail_snapshot(path: Path)->dict[str,Any]:
    try:return m9v.tail_snapshot(path)
    except Exception as exc:raise M9YContractError(str(exc)) from exc
def prefix_fingerprint_rows(path:Path,row_count:int)->dict[str,Any]:
    try:return m9v2.prefix_fingerprint_rows(path,row_count)
    except Exception as exc:raise M9YContractError(str(exc)) from exc

def validate_contract(contract:dict[str,Any])->None:
    if contract.get('project')!='MOCHIPOYO_ALERT_RESEARCH' or contract.get('stage')!=STAGE:raise M9YContractError('unexpected M9Y contract')
    if contract.get('status')!='DESIGN_FROZEN_NOT_STARTED':raise M9YContractError('M9Y contract not frozen')
    data=contract.get('data',{})
    if data.get('ticker')!='XAUUSD' or data.get('time_basis')!='MT5_SERVER_TIME' or data.get('historical_backfill') is not False:raise M9YContractError('unsafe M9Y data contract')
    if set(data.get('live_file_map',{}))!={'M1','M5','M15','H1','H4'}:raise M9YContractError('unexpected M9Y file map')
    if set(contract.get('arms',{}))!=set(ARMS):raise M9YContractError('M9Y arms mismatch')
    dep=contract.get('base_candidate',{}).get('m9v_dependency',{})
    if dep.get('required_stage')!=M9V_STAGE or dep.get('required_runtime_contract_version')!=M9V_RUNTIME_VERSION or dep.get('read_only') is not True or dep.get('m9v_start_reused') is not False:raise M9YContractError('unsafe M9V dependency contract')
    safety=contract.get('safety',{})
    if safety.get('audit_only') is not True:raise M9YContractError('audit_only must be true')
    for key in ('discord_send','mt5_order','live_ready','final_signal','entry_gate_enabled','m7c_formula_changed','m8c_reset','m9v_reset','automatic_live_promotion'):
        if safety.get(key) is not False:raise M9YContractError(f'unsafe M9Y flag: {key}')

def validate_runtime_manifest(runtime:dict[str,Any],contract:dict[str,Any],contract_sha:str,m9v_runtime_path:Path)->dict[str,Any]:
    validate_contract(contract)
    if runtime.get('stage')!=STAGE or runtime.get('runtime_status')!='FROZEN_FRESH_START' or runtime.get('runtime_contract_version')!=RUNTIME_CONTRACT_VERSION:raise M9YContractError('unexpected M9Y runtime')
    if runtime.get('contract_sha256')!=contract_sha or runtime.get('historical_backfill_allowed') is not False or runtime.get('reset_allowed') is not False:raise M9YContractError('M9Y runtime integrity failed')
    if not isinstance(runtime.get('frozen_row_prefixes'),dict):raise M9YContractError('missing M9Y frozen prefixes')
    if not m9v_runtime_path.is_file():raise M9YContractError(f'M9V runtime missing: {m9v_runtime_path}')
    current_m9v=load_json(m9v_runtime_path)
    if current_m9v.get('stage')!=M9V_STAGE or current_m9v.get('runtime_contract_version')!=M9V_RUNTIME_VERSION:raise M9YContractError('M9V upstream runtime mismatch')
    if current_m9v.get('reset_allowed') is not False or current_m9v.get('historical_backfill_allowed') is not False:raise M9YContractError('unsafe M9V upstream runtime')
    if runtime.get('m9v_runtime_manifest_sha256')!=file_sha256(m9v_runtime_path):raise M9YContractError('M9V runtime manifest changed after M9Y freeze')
    if runtime.get('m9v_prospective_start_server_time')!=current_m9v.get('prospective_start_server_time'):raise M9YContractError('M9V start changed after M9Y freeze')
    return current_m9v

def wilder_atr14(bars:list[m9p.Bar])->list[float|None]:
    tr=[]
    for i,b in enumerate(bars):
        if i==0:v=b.high-b.low
        else:
            p=bars[i-1].close;v=max(b.high-b.low,abs(b.high-p),abs(b.low-p))
        tr.append(v)
    out:[float|None]=[None]*len(bars)
    if len(bars)>=14:
        out[13]=sum(tr[:14])/14.0
        for i in range(14,len(bars)):
            prev=out[i-1];assert prev is not None;out[i]=((13*prev)+tr[i])/14.0
    return out

def _metrics(rows:list[dict[str,Any]])->dict[str,Any]:
    resolved=[r for r in rows if r.get('weighted_return_bps') is not None]
    if not resolved:return {'accepted_count':len(rows),'resolved_count':0,'open_count':len(rows),'win_rate':None,'profit_factor_bps':None,'net_bps':0.0,'average_win_bps':None,'average_loss_bps':None,'payoff_ratio':None,'max_drawdown_bps':0.0,'max_losing_streak':0,'tail_le_minus_100_fraction':None}
    ordered=sorted(resolved,key=lambda r:parse_time(str(r['actual_entry_time'])));vals=[float(r['weighted_return_bps']) for r in ordered];wins=[v for v in vals if v>0];losses=[v for v in vals if v<0]
    eq=peak=dd=0.0;streak=maxst=0
    for v in vals:
        eq+=v;peak=max(peak,eq);dd=max(dd,peak-eq)
        if v<0:streak+=1;maxst=max(maxst,streak)
        else:streak=0
    avgw=sum(wins)/len(wins) if wins else None;avgl=sum(losses)/len(losses) if losses else None;grossloss=abs(sum(losses))
    return {'accepted_count':len(rows),'resolved_count':len(resolved),'open_count':len(rows)-len(resolved),'win_rate':sum(v>0 for v in vals)/len(vals),'profit_factor_bps':None if grossloss==0 else sum(wins)/grossloss,'net_bps':sum(vals),'average_win_bps':avgw,'average_loss_bps':avgl,'payoff_ratio':None if avgw is None or avgl in (None,0) else avgw/abs(avgl),'max_drawdown_bps':dd,'max_losing_streak':maxst,'tail_le_minus_100_fraction':sum(v<=-100 for v in vals)/len(vals)}

def _stable_m9v_feed(latest_dir:Path)->tuple[dict[str,Any],list[dict[str,str]]]:
    summary_path=latest_dir/'01_summary.json';ledger_path=latest_dir/'02_branch_candidate_ledger.csv'
    for attempt in range(5):
        try:
            s1=summary_path.read_bytes(); l=ledger_path.read_bytes(); s2=summary_path.read_bytes()
            if s1!=s2:raise OSError('M9V LATEST changed during read')
            summary=json.loads(s1.decode('utf-8'))
            reader=csv.DictReader(io.StringIO(l.decode('utf-8-sig')));rows=list(reader)
            return summary,rows
        except Exception:
            if attempt==4:raise M9YContractError('cannot obtain stable M9V LATEST feed snapshot')
            time.sleep(0.25)
    raise M9YContractError('unreachable M9V feed error')

def _runner_times(m15:list[m9p.Bar])->list[datetime]:
    rci=m9p.rci_series([b.close for b in m15],9);out=[]
    for ci in range(50,len(m15)):
        s=ci-1;c,p,p2=rci[s],rci[s-1],rci[s-2]
        if c is not None and p is not None and p2 is not None and c<p and p>=p2:out.append(m15[ci].time)
    return out

def _n6(entry:datetime,h4:list[m9p.Bar],rci:list[float|None],close:list[datetime])->tuple[bool,float|None]:
    i=bisect.bisect_right(close,entry)-1
    if i<107:return False,None
    vals=rci[i-99:i+1]
    if not all(v is not None for v in vals):return False,None
    cur=float(rci[i]);pct=sum(float(v)<=cur for v in vals if v is not None)/100.0
    return pct>0.25 and pct<=0.50,pct

def audit(*,data_root:Path,contract:dict[str,Any],runtime:dict[str,Any],point:float,m9v_runtime_path:Path,m9v_latest_dir:Path)->dict[str,Any]:
    contract_sha=sha256_bytes(json.dumps(contract,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
    m9v_runtime=validate_runtime_manifest(runtime,contract,contract_sha,m9v_runtime_path);start=parse_time(str(runtime['prospective_start_server_time']))
    paths={}
    for tf,fn in contract['data']['live_file_map'].items():
        p=data_root/str(fn)
        if not p.is_file():raise M9YContractError(f'missing live GOLD CSV: {p}')
        frozen=runtime['frozen_row_prefixes'].get(tf)
        if not isinstance(frozen,dict):raise M9YContractError(f'missing frozen prefix: {tf}')
        if prefix_fingerprint_rows(p,int(frozen.get('row_count',0)))!=frozen:raise M9YContractError(f'frozen pre-start rows changed after M9Y start: {tf}')
        paths[tf]=p
    feed_summary,feed_rows=_stable_m9v_feed(m9v_latest_dir)
    if feed_summary.get('stage')!=M9V_STAGE or feed_summary.get('status')!='PASS_FRESH_PROSPECTIVE_AUDIT_ONLY':raise M9YContractError('M9V upstream summary not PASS')
    if feed_summary.get('prospective_start_server_time')!=m9v_runtime.get('prospective_start_server_time'):raise M9YContractError('M9V feed/runtime start mismatch')
    if feed_summary.get('guardrails',{}).get('historical_backfill') is not False or feed_summary.get('guardrails',{}).get('m8c_reset') is not False:raise M9YContractError('unsafe M9V feed guardrails')
    base=[r for r in feed_rows if r.get('branch')=='S2_M15' and r.get('proxy_primary_time') and parse_time(r['proxy_primary_time'])>start]
    base.sort(key=lambda r:parse_time(r['turn_entry_time']))
    m1=m9p.load_bars(paths['M1']);m5=m9p.load_bars(paths['M5']);m15=m9p.load_bars(paths['M15']);h1=m9p.load_bars(paths['H1']);h4=m9p.load_bars(paths['H4'])
    m1_idx={b.time:i for i,b in enumerate(m1)};m5_close=[b.time+timedelta(minutes=5) for b in m5];atr5=wilder_atr14(m5);h4_close=[b.time+timedelta(hours=4) for b in h4];h4_rci=m9p.rci_series([b.close for b in h4],9);h1_close=[b.time+timedelta(hours=1) for b in h1];h1mac=[f-s for f,s in zip(m9p.ema([b.close for b in h1],6),m9p.ema([b.close for b in h1],13))];rtimes=_runner_times(m15)
    candidates=[];pending=[];skipped=[]
    for r in base:
        cid=r.get('candidate_id') or f"S2_{r['proxy_primary_time']}_{r['turn_entry_time']}";pt=parse_time(r['proxy_primary_time']);ft=parse_time(r['turn_entry_time']);pi=m1_idx.get(pt);fi=m1_idx.get(ft)
        if pi is None or fi is None:pending.append({'upstream_candidate_id':cid,'reason':'M1_EXACT_COVERAGE_PENDING',**r});continue
        i5=bisect.bisect_right(m5_close,ft)-1
        if i5<0 or atr5[i5] is None or float(atr5[i5])<=0:skipped.append({'upstream_candidate_id':cid,'reason':'ATR_UNAVAILABLE',**r});continue
        level=m1[pi].open-RECLAIM_OFFSET_ATR*float(atr5[i5]);native_text=(r.get('native_exit_time') or '').strip();native_t=parse_time(native_text) if native_text else None;native_i=m1_idx.get(native_t) if native_t else None
        ai=fi if m1[fi].open>=level else None
        if ai is None:
            max_ai=fi+RECLAIM_WAIT_MINUTES;scan_end=min(len(m1)-2,max_ai-1)
            if native_i is not None:scan_end=min(scan_end,native_i-2)
            for ci in range(fi,scan_end+1):
                if m1[ci].close>=level:
                    ni=ci+1
                    if ni<=max_ai and (native_i is None or ni<native_i):ai=ni
                    break
        if ai is None:
            timeout=len(m1)-1>=fi+RECLAIM_WAIT_MINUTES;native_done=native_i is not None and native_i<=min(len(m1)-1,fi+RECLAIM_WAIT_MINUTES)
            (skipped if timeout or native_done else pending).append({'upstream_candidate_id':cid,'reason':'RECLAIM_TIMEOUT_OR_NATIVE_EXIT' if timeout or native_done else 'RECLAIM_PENDING','reclaim_level':level,**r});continue
        at=m1[ai].time;entry=m1[ai].open+m1[ai].spread*point;n6,pct=_n6(at,h4,h4_rci,h4_close);native_ret=None
        if native_i is not None:native_ret=(m1[native_i].open-entry)/abs(entry)*10000.0
        h1up=None;runner_t=None;runner_ret=None
        if native_t is not None and native_ret is not None:
            ih1=bisect.bisect_right(h1_close,native_t)-1;h1up=ih1>0 and h1mac[ih1]>h1mac[ih1-1]
            if h1up:
                pos=bisect.bisect_left(rtimes,native_t)
                if pos<len(rtimes):
                    ri=m1_idx.get(rtimes[pos])
                    if ri is not None:runner_t=rtimes[pos];runner_ret=(m1[ri].open-entry)/abs(entry)*10000.0
        candidates.append({'candidate_id':f'M9Y_C{len(candidates)+1:06d}','upstream_m9v_candidate_id':cid,'proxy_primary_time':r['proxy_primary_time'],'first_turn_time':r['turn_entry_time'],'actual_entry_time':fmt_time(at),'native_exit_time':native_text or None,'runner_exit_time':fmt_time(runner_t) if runner_t else None,'entry_delay_minutes':ai-fi,'primary_bid':m1[pi].open,'reclaim_level':level,'entry_exec':entry,'N6_at_actual_entry':n6,'N6_percentile_at_actual_entry':pct,'native_return_bps':native_ret,'H1_MACD_rising_at_native_exit':h1up,'runner_return_bps':runner_ret,'status':'ENTRY_OPEN' if native_ret is None else ('RUNNER_PENDING' if h1up and runner_ret is None else 'EXIT_CONTEXT_RESOLVED')})
    arms={};overlaps=[]
    for name,spec in ARMS.items():
        accepted=[];active_until=None;active_open=False;active_id=None
        for r in candidates:
            entry=parse_time(r['actual_entry_time'])
            if active_open or (active_until is not None and entry<active_until):overlaps.append({'arm':name,'active_trade_id':active_id,'skipped_candidate_id':r['candidate_id'],'skipped_actual_entry_time':r['actual_entry_time'],'reason':'ONE_POSITION_ACTIVE'});continue
            risk=0.5 if spec['risk_n6'] and r['N6_at_actual_entry'] else 1.0;share=float(spec['runner_share']);nr=r['native_return_bps'];rr=r['runner_return_bps'];h1up=r['H1_MACD_rising_at_native_exit'] is True;ret=None;exit_t=None
            if nr is not None:
                if share>0 and h1up:
                    if rr is not None and r['runner_exit_time']:
                        ret=((1-share)*float(nr)+share*float(rr))*risk;exit_t=parse_time(r['runner_exit_time'])
                else:ret=float(nr)*risk;exit_t=parse_time(r['native_exit_time'])
            ar={**r,'arm':name,'arm_trade_id':f'{name}_T{len(accepted)+1:06d}','risk_weight':risk,'runner_share':share,'weighted_return_bps':ret,'effective_exit_time':fmt_time(exit_t) if exit_t else None};accepted.append(ar);active_id=ar['arm_trade_id']
            if exit_t is None:active_open=True;active_until=None
            else:active_open=False;active_until=exit_t
        arms[name]=accepted
    return {'start_server_time':fmt_time(start),'m9v_upstream_start_server_time':m9v_runtime.get('prospective_start_server_time'),'latest_server_open':{tf:fmt_time(bs[-1].time) for tf,bs in {'M1':m1,'M5':m5,'M15':m15,'H1':h1,'H4':h4}.items()},'upstream_s2_post_start_count':len(base),'w1_candidate_count':len(candidates),'pending':pending,'skipped':skipped,'candidates':candidates,'arms':arms,'arm_metrics':{k:_metrics(v) for k,v in arms.items()},'overlaps':overlaps}
