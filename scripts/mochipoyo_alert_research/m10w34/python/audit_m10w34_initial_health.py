from __future__ import annotations
import json, os, shutil, sys, zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

THIS=Path(__file__).resolve()
MR=THIS.parents[2]
RECOVERY=MR/"recovery"/"python"
for directory in (MR/"common"/"python",THIS.parent,RECOVERY):
    if str(directory) not in sys.path:
        sys.path.insert(0,str(directory))

import bounded_csv_journal_integrity as journal_integrity
journal_integrity.install_verified_adapter_hooks()
import bounded_csv_source_adapter as adapter
import m10w34_runtime as runtime
import migrate_bounded_csv_source_adapter as migration

def utc_text(): return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
def utc_stamp(): return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")
def read_json(path: Path)->dict[str,Any]:
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value,dict) else {"_error":"JSON_NOT_OBJECT"}
    except Exception as exc:
        return {"_error":f"{type(exc).__name__}: {exc}"}
def info(path: Path)->dict[str,Any]:
    row={"path":str(path),"exists":path.is_file()}
    if path.is_file():
        row.update({"size_bytes":path.stat().st_size,"sha256":adapter.sha256_file(path)})
    return row
def tail(path: Path,lines:int=160)->str:
    if not path.is_file(): return ""
    return "".join(path.read_text(encoding="utf-8",errors="replace").splitlines(keepends=True)[-lines:])

def main()->int:
    try:
        local=Path(os.environ["LOCALAPPDATA"])/"xauusd_signal_lab"/"mochipoyo_alert_research"
        paths=runtime.runtime_paths(local)
        snapshot=adapter.adapter_root(local)/"loop_snapshots"/"M10W34"
        latest=local/"outputs"/"M10W34"/"LATEST"/"01_summary.json"
        snap_receipt=snapshot/"00_snapshot_receipt.json"
        required=[paths["runtime"],paths["state"],paths["receipt"],paths["prestart"],paths["lock"],paths["loop_status"],latest,snap_receipt]
        missing=[str(p) for p in required if not p.is_file()]
        if missing: raise RuntimeError(f"M10W34 initial health evidence missing: {missing}")
        runtime_payload=read_json(paths["runtime"])
        state=read_json(paths["state"])
        start_receipt=read_json(paths["receipt"])
        prestart=read_json(paths["prestart"])
        loop_status=read_json(paths["loop_status"])
        latest_summary=read_json(latest)
        snapshot_receipt=read_json(snap_receipt)
        point=float(runtime_payload.get("point","nan"))
        contract=runtime.load_json(runtime.CONTRACT)
        processes=migration.running_processes("run_m10w34_private_snapshot.py")
        with adapter.update_lock(local,timeout_seconds=90.0):
            journals=journal_integrity.verify_journals(local)
            current=runtime.verify_runtime(local,snapshot,point,contract,runtime_payload)
            fingerprints=snapshot_receipt.get("journal_fingerprints",{})
            snapshot_files={}
            for tf,filename in adapter.FILE_MAP.items():
                path=snapshot/filename
                expected=fingerprints.get(tf,{}) if isinstance(fingerprints,dict) else {}
                actual_sha=adapter.sha256_file(path) if path.is_file() else None
                actual_size=path.stat().st_size if path.is_file() else None
                snapshot_files[tf]={**info(path),"receipt_sha256":expected.get("sha256"),"receipt_size_bytes":expected.get("size_bytes"),"sha256_match":actual_sha==expected.get("sha256"),"size_match":actual_size==expected.get("size_bytes"),"not_ahead_of_shared_journal":(runtime.parse_time(str(expected.get("last_server_open")))<=runtime.parse_time(str(journals[tf].get("last_server_open")))) if expected.get("last_server_open") and journals[tf].get("last_server_open") else False}
        start=runtime_payload.get("prospective_start_server_time")
        successful=int(loop_status.get("successful_cycles",0) or 0)
        terminal=int(loop_status.get("failed_terminal_cycles",0) or 0)
        checks={
            "exactly_one_process":len(processes)==1,
            "lock_present":paths["lock"].is_file(),
            "runtime_version":runtime_payload.get("runtime_contract_version")==runtime.RUNTIME_VERSION,
            "runtime_frozen":runtime_payload.get("runtime_status")=="FROZEN_FRESH_START",
            "state_start_match":state.get("prospective_start_server_time")==start,
            "start_receipt_match":start_receipt.get("prospective_start_server_time")==start and start_receipt.get("status")=="PASS",
            "prestart_engine_pass":str(prestart.get("status","")).startswith("PASS_PRESTART_CAUSAL_ENGINE_AUDIT"),
            "loop_running":loop_status.get("status")=="RUNNING",
            "successful_cycle":successful>=1,
            "no_terminal_failure":terminal==0,
            "latest_output_pass":latest_summary.get("status")=="PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
            "latest_output_start_match":latest_summary.get("prospective_start_server_time")==start,
            "snapshot_receipt_pass":snapshot_receipt.get("status")=="PASS_PRIVATE_LOOP_SNAPSHOT" and snapshot_receipt.get("snapshot_version")=="M10W34_PRIVATE_VERIFIED_SNAPSHOT_V1",
            "all_snapshot_files_match":all(r["sha256_match"] and r["size_match"] and r["not_ahead_of_shared_journal"] for r in snapshot_files.values()),
            "all_shared_journals_verified":len(journals)==6,
        }
        passed=all(checks.values())
        output=local/"outputs"/"M10W34_INITIAL_HEALTH"
        archive=output/"archive"/utc_stamp()
        archive.mkdir(parents=True,exist_ok=False)
        summary={"project":"MOCHIPOYO_ALERT_RESEARCH","stage":"M10W34_INITIAL_PRIVATE_SNAPSHOT_HEALTH_AUDIT_ONLY","status":"PASS_M10W34_INITIAL_HEALTHY_RUNNING_AUDIT_ONLY" if passed else "REVIEW_REQUIRED_M10W34_INITIAL_HEALTH","built_at_utc":utc_text(),"prospective_start_server_time":start,"processes":processes,"checks":checks,"loop_status":loop_status,"runtime":{**info(paths["runtime"]),"payload":runtime_payload},"state":{**info(paths["state"]),"payload":state},"start_receipt":{**info(paths["receipt"]),"payload":start_receipt},"prestart_audit":{**info(paths["prestart"]),"payload":prestart},"latest_output_summary":{**info(latest),"payload":latest_summary},"snapshot_receipt":{**info(snap_receipt),"payload":snapshot_receipt},"snapshot_files":snapshot_files,"current_snapshot":current,"shared_journals":journals,"mutations_performed":False,"process_started_or_stopped":False,"lock_removed":False,"runtime_or_start_modified":False,"journal_updated":False}
        (archive/"00_READ_ME_FIRST.txt").write_text("Read-only initial health audit for the M10W34 SNDX1 audit-only private-snapshot shadow.\n",encoding="utf-8")
        (archive/"01_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (archive/"02_runtime_manifest.json").write_text(json.dumps(runtime_payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (archive/"03_runtime_state.json").write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (archive/"04_prestart_causal_engine_audit.json").write_text(json.dumps(prestart,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (archive/"05_snapshot_receipt.json").write_text(json.dumps(snapshot_receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (archive/"06_loop_log_tail.txt").write_text(tail(paths["log"]),encoding="utf-8")
        (archive/"07_audit.log").write_text("\n".join([f"status={summary['status']}",f"prospective_start_server_time={start}",*(f"{k}={str(v).lower()}" for k,v in checks.items()),"mutations_performed=false","runtime_or_start_modified=false","journal_updated=false",""]),encoding="utf-8")
        with zipfile.ZipFile(archive/"99_UPLOAD_PACKAGE.zip","w",zipfile.ZIP_DEFLATED) as package:
            for path in sorted(p for p in archive.iterdir() if p.is_file()): package.write(path,path.name)
        latest_dir=output/"LATEST"
        shutil.rmtree(latest_dir,ignore_errors=True)
        shutil.copytree(archive,latest_dir)
        print(f"[M10W34 HEALTH] {summary['status']}")
        print(f"[OUTPUT] {latest_dir}")
        return 0 if passed else 3
    except Exception as exc:
        print(f"[M10W34 HEALTH BLOCKED] {type(exc).__name__}: {exc}",file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
