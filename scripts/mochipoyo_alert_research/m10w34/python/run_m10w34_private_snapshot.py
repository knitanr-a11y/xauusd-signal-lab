from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
MR = THIS.parents[2]
for directory in (MR / "common" / "python", THIS.parent):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import bounded_csv_journal_integrity as journal_integrity
journal_integrity.install_verified_adapter_hooks()
import bounded_csv_source_adapter as adapter
import m10w34_runtime as runtime

SNAPSHOT_VERSION = "M10W34_PRIVATE_VERIFIED_SNAPSHOT_V1"
LOOP_INTERVAL_SECONDS = 60

def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def local_root() -> Path:
    value = os.environ.get("LOCALAPPDATA","").strip()
    if not value:
        raise runtime.M10W34Error("LOCALAPPDATA unavailable")
    return Path(value)/"xauusd_signal_lab"/"mochipoyo_alert_research"

def snapshot_root(root: Path) -> Path:
    return adapter.adapter_root(root)/"loop_snapshots"/"M10W34"

def atomic_json(path: Path,payload: Any) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    os.replace(temp,path)

def append_log(path: Path,text: str) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as handle:
        handle.write(f"{utc_text()} {text}\n")

def materialize_snapshot(root: Path,timeout_seconds: float=90.0) -> Path:
    base=adapter.adapter_root(root)/"loop_snapshots"
    base.mkdir(parents=True,exist_ok=True)
    target=snapshot_root(root)
    temp=base/f".M10W34.tmp_{os.getpid()}_{time.time_ns()}"
    temp.mkdir(parents=True,exist_ok=False)
    try:
        with adapter.update_lock(root,timeout_seconds=timeout_seconds):
            verified=journal_integrity.verify_journals(root)
            shared=adapter.journal_root(root)
            for timeframe,filename in adapter.FILE_MAP.items():
                source=shared/filename
                destination=temp/filename
                shutil.copy2(source,destination)
                expected=verified[timeframe]
                if destination.stat().st_size!=int(expected["size_bytes"]):
                    raise adapter.AdapterIntegrityError(f"M10W34 private snapshot size mismatch: {timeframe}")
                if adapter.sha256_file(destination)!=str(expected["sha256"]):
                    raise adapter.AdapterIntegrityError(f"M10W34 private snapshot SHA256 mismatch: {timeframe}")
            receipt={
                "project":"MOCHIPOYO_ALERT_RESEARCH","status":"PASS_PRIVATE_LOOP_SNAPSHOT",
                "snapshot_version":SNAPSHOT_VERSION,"loop":"M10W34","created_at_utc":utc_text(),
                "source_manifest_sha256":adapter.sha256_file(adapter.manifest_path(root)),
                "journal_fingerprints":{tf:{k:details.get(k) for k in ("row_count","first_server_open","last_server_open","size_bytes","sha256")} for tf,details in verified.items()},
                "runtime_or_start_modified_by_snapshot":False,"historical_backfill_before_start":False,
            }
            (temp/"00_snapshot_receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
            if target.exists():
                shutil.rmtree(target)
            os.replace(temp,target)
        return target
    except Exception:
        shutil.rmtree(temp,ignore_errors=True)
        raise

def refresh(root: Path,source_root: Path,point: float) -> Path:
    adapter.ensure_updated(root,source_root,point,retry_window_seconds=90.0)
    return materialize_snapshot(root,timeout_seconds=90.0)

def transient(exc: BaseException) -> bool:
    if isinstance(exc,adapter.AdapterTransientError) or isinstance(exc,PermissionError):
        return True
    if isinstance(exc,OSError) and getattr(exc,"winerror",None) in {2,3,5,32,33}:
        return True
    text=f"{type(exc).__name__}: {exc}".lower()
    return any(token in text for token in ("permission denied","permissionerror","access is denied","アクセスが拒否","sharing violation","winerror 5","winerror 32","winerror 33"))

def run_single(mode: str) -> int:
    root=local_root()
    source_root,point=adapter.source_environment(root)
    snapshot=refresh(root,source_root,point)
    return runtime.initialize(snapshot,point) if mode=="initialize" else runtime.once(snapshot,point)

def forever(interval_seconds: int) -> int:
    root=local_root()
    source_root,point=adapter.source_environment(root)
    paths=runtime.runtime_paths(root)
    paths["directory"].mkdir(parents=True,exist_ok=True)
    paths["log"].parent.mkdir(parents=True,exist_ok=True)
    if not paths["runtime"].is_file():
        raise runtime.M10W34Error("runtime missing; run BAT01 exactly once first")
    if paths["lock"].exists():
        raise runtime.M10W34Error("loop lock already exists; do not delete manually")
    try:
        handle=os.open(paths["lock"],os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError as exc:
        raise runtime.M10W34Error("loop lock already exists") from exc
    os.write(handle,json.dumps({"pid":os.getpid(),"created_at_utc":utc_text(),"process_marker":"run_m10w34_private_snapshot.py","audit_only":True}).encode("utf-8"))
    os.close(handle)
    paths["stop"].unlink(missing_ok=True)
    prior={}
    if paths["loop_status"].is_file():
        try: prior=json.loads(paths["loop_status"].read_text(encoding="utf-8"))
        except Exception: prior={}
    cycles=int(prior.get("cycles",0) or 0)
    successful=int(prior.get("successful_cycles",0) or 0)
    waiting=int(prior.get("waiting_transient_cycles",0) or 0)
    terminal=int(prior.get("failed_terminal_cycles",0) or 0)
    append_log(paths["log"],"M10W34 LOOP START private verified snapshot audit-only")
    try:
        while True:
            if paths["stop"].is_file():
                atomic_json(paths["loop_status"],{"project":"MOCHIPOYO_ALERT_RESEARCH","stage":runtime.STAGE,"status":"STOPPED_BY_REQUEST","updated_at_utc":utc_text(),"cycles":cycles,"successful_cycles":successful,"waiting_transient_cycles":waiting,"failed_terminal_cycles":terminal,"runtime_or_start_modified":False})
                paths["stop"].unlink(missing_ok=True)
                return 0
            cycles+=1
            try:
                snapshot=refresh(root,source_root,point)
                rc=runtime.once(snapshot,point)
                if rc!=0:
                    raise runtime.M10W34Error(f"once returned exit code {rc}")
                successful+=1
                atomic_json(paths["loop_status"],{"project":"MOCHIPOYO_ALERT_RESEARCH","stage":runtime.STAGE,"status":"RUNNING","updated_at_utc":utc_text(),"pid":os.getpid(),"runner_version":SNAPSHOT_VERSION,"cycles":cycles,"successful_cycles":successful,"waiting_transient_cycles":waiting,"failed_terminal_cycles":terminal,"interval_seconds":interval_seconds,"snapshot_root":str(snapshot),"runtime_or_start_modified":False,"discord_send":False,"mt5_order":False})
                append_log(paths["log"],f"cycle={cycles} PASS successful={successful}")
            except Exception as exc:
                if transient(exc):
                    waiting+=1
                    atomic_json(paths["loop_status"],{"project":"MOCHIPOYO_ALERT_RESEARCH","stage":runtime.STAGE,"status":"WAITING_TRANSIENT_SOURCE","updated_at_utc":utc_text(),"pid":os.getpid(),"cycles":cycles,"successful_cycles":successful,"waiting_transient_cycles":waiting,"failed_terminal_cycles":terminal,"last_error":f"{type(exc).__name__}: {exc}","runtime_or_start_modified":False})
                    append_log(paths["log"],f"cycle={cycles} TRANSIENT {type(exc).__name__}: {exc}")
                else:
                    terminal+=1
                    atomic_json(paths["loop_status"],{"project":"MOCHIPOYO_ALERT_RESEARCH","stage":runtime.STAGE,"status":"BLOCKED_TERMINAL_FAIL_CLOSED","updated_at_utc":utc_text(),"pid":os.getpid(),"cycles":cycles,"successful_cycles":successful,"waiting_transient_cycles":waiting,"failed_terminal_cycles":terminal,"last_error":f"{type(exc).__name__}: {exc}","runtime_or_start_modified":False})
                    print(f"[M10W34 LOOP BLOCKED] {type(exc).__name__}: {exc}",file=sys.stderr)
                    return 2
            for _ in range(max(1,interval_seconds)):
                if paths["stop"].is_file(): break
                time.sleep(1)
    finally:
        paths["lock"].unlink(missing_ok=True)
        append_log(paths["log"],"M10W34 LOOP EXIT; own lock removed")

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=("initialize","once","forever"))
    parser.add_argument("--interval-seconds",type=int,default=LOOP_INTERVAL_SECONDS)
    args=parser.parse_args()
    try:
        if args.mode in ("initialize","once"):
            return run_single(args.mode)
        return forever(max(1,args.interval_seconds))
    except Exception as exc:
        print(f"[M10W34 OPERATOR BLOCKED] {type(exc).__name__}: {exc}",file=sys.stderr)
        print("[SAFE] Existing loops, runtimes, starts, journals, Discord and MT5 orders remain unchanged.",file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
