#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from typing import Any
import pandas as pd

READY = "GOLD_V3_99_RECENT_CLOSED_CANDLE_SIGNAL_REPLAY_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_99_RECENT_CLOSED_CANDLE_SIGNAL_REPLAY_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
CSV_NAMES = ["goldsharp_m15.csv", "goldsharp_h1.csv", "goldsharp_h4.csv", "goldsharp_d1.csv", "goldsharp_m5.csv"]
REQUIRED_DEP_DIRS = [
    "68_rank_dedup_selection_repro_audit_only",
    "51_full_candidate_virtual_opportunity_ledger_builder_audit_only",
    "50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only",
]


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.resolve()
        if (d / "goldsharp_m15.csv").exists() or (d / "FX_OUTPUTS" / "gold_v3").exists():
            return d
    raise SystemExit("Files dir not found")


def read_csv_any(path: Path) -> tuple[pd.DataFrame, str]:
    first = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()[0]
    sep = ";" if first.count(";") >= first.count(",") else ","
    return pd.read_csv(path, sep=sep, encoding="utf-8-sig"), sep


def write_csv(df: pd.DataFrame, path: Path, sep: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep=sep, index=False, encoding="utf-8-sig")


def safe_name(ts: Any) -> str:
    return str(pd.to_datetime(ts)).replace("-", "").replace(":", "").replace(" ", "_")


def run_stage80(repo: Path, cdir: Path) -> tuple[int, str, float]:
    s80 = repo / "scripts" / "gold_v3_runtime" / "gold_v3_80_immutable_runtime_monitor_audit.py"
    cmd = [sys.executable, str(s80), "--candle-dir", str(cdir), "--once", "--run-immediately", "--enable-signal-gated-ledger-sidecar", "--disable-auto-support-bundle"]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=str(repo), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return int(p.returncode), p.stdout[-4000:], time.perf_counter() - t0


def rj(p: Path) -> dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception as e:
        return {"_error": repr(e)}


def vrow(cid, passed, obs, exp, sev="BLOCKER"):
    return {"check_id": cid, "result": "PASS" if passed else "FAIL", "observed": obs, "expected": exp, "severity": sev}


def copy_required_deps(src_base: Path, dst_base: Path) -> list[dict[str, Any]]:
    copied = []
    dst_base.mkdir(parents=True, exist_ok=True)
    for d in REQUIRED_DEP_DIRS:
        sp = src_base / d
        dp = dst_base / d
        if sp.exists():
            if dp.exists():
                shutil.rmtree(dp)
            try:
                shutil.copytree(sp, dp)
                copied.append({"dir": d, "copied": True, "src": str(sp), "dst": str(dp), "error": ""})
            except Exception as e:
                copied.append({"dir": d, "copied": False, "src": str(sp), "dst": str(dp), "error": repr(e)})
        else:
            copied.append({"dir": d, "copied": False, "src": str(sp), "dst": str(dp), "error": "source_missing"})
    return copied


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candle-dir", default="")
    ap.add_argument("--bars", type=int, default=32)
    ap.add_argument("--output-dir", default="")
    ap.add_argument("--keep-temp", action="store_true")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]
    src = Path(args.candle_dir).resolve() if args.candle_dir else find_files_dir()
    src_base = src / "FX_OUTPUTS" / "gold_v3"
    out = Path(args.output_dir).resolve() if args.output_dir else src_base / "99c"
    out.mkdir(parents=True, exist_ok=True)

    temp_root = Path(tempfile.gettempdir()) / "g99_replay"
    if temp_root.exists() and not args.keep_temp:
        shutil.rmtree(temp_root, ignore_errors=True)
    temp_root.mkdir(parents=True, exist_ok=True)
    replay_root = temp_root

    checks = []
    blockers = []
    p_m15 = src / "goldsharp_m15.csv"
    checks.append(vrow("source_m15_present", p_m15.exists(), str(p_m15), "exists"))
    checks.append(vrow("replay_root_is_temp_short_path", str(replay_root).lower().find("g99_replay") >= 0, str(replay_root), "temp/g99_replay"))
    for d in REQUIRED_DEP_DIRS:
        checks.append(vrow(f"dep_{d}_present", (src_base / d).exists(), str(src_base / d), "exists"))
    if not p_m15.exists():
        blockers.append({"blocker_id": "source_m15_missing", "reason": "REQUIRED_INPUT_MISSING", "detail": str(p_m15), "severity": "BLOCKER"})
        bars = []
    else:
        m15, _sep15 = read_csv_any(p_m15)
        m15["__time"] = pd.to_datetime(m15["time"], errors="raise")
        bars = list(m15.tail(max(1, int(args.bars)))["__time"])
        checks.append(vrow("replay_bar_count_positive", len(bars) > 0, len(bars), ">0"))
    for d in REQUIRED_DEP_DIRS:
        if not (src_base / d).exists():
            blockers.append({"blocker_id": f"dep_{d}_missing", "reason": "REQUIRED_DEPENDENCY_MISSING", "detail": str(src_base / d), "severity": "BLOCKER"})

    results = []
    dep_rows = []
    if not blockers:
        for i, ts in enumerate(bars, start=1):
            rdir = replay_root / f"r{i:03d}"
            if rdir.exists():
                shutil.rmtree(rdir, ignore_errors=True)
            rdir.mkdir(parents=True, exist_ok=True)
            rbase = rdir / "FX_OUTPUTS" / "gold_v3"
            rbase.mkdir(parents=True, exist_ok=True)
            copied = copy_required_deps(src_base, rbase)
            dep_rows.extend([{**x, "idx": i, "asof_m15": str(ts)} for x in copied])
            dep_failed = [x for x in copied if not x.get("copied")]
            for name in CSV_NAMES:
                sp = src / name
                if not sp.exists():
                    continue
                df, sep = read_csv_any(sp)
                if "time" in df.columns:
                    t = pd.to_datetime(df["time"], errors="coerce")
                    df = df[t <= ts].copy()
                write_csv(df, rdir / name, sep)
            if dep_failed:
                rc, tail, sec = 1, "DEPENDENCY_COPY_FAILED: " + json.dumps(dep_failed, ensure_ascii=False), 0.0
                summ = {}
            else:
                rc, tail, sec = run_stage80(repo, rdir)
                summ = rj(rbase / "80_immutable_runtime_monitor_audit_only" / "gold_v3_80_immutable_runtime_monitor_summary.json")
            decision = str(summ.get("sidecar_decision", ""))
            if not decision:
                decision = str(summ.get("decision", ""))
            skip = str(summ.get("sidecar_skip_reason", ""))
            s85 = str(summ.get("last_stage85_returncode", ""))
            s86 = str(summ.get("last_stage86_returncode", ""))
            status80 = str(summ.get("status", ""))
            results.append({
                "idx": i,
                "asof_m15": str(ts),
                "returncode": rc,
                "seconds": round(sec, 6),
                "stage80_status": status80,
                "decision": decision,
                "skip_reason": skip,
                "stage85_returncode": s85,
                "stage86_returncode": s86,
                "latest_m15_time": summ.get("latest_m15_time", ""),
                "replay_dir": str(rdir),
                "tail": tail.replace("\r", " ").replace("\n", " ")[-1200:],
            })

    res_df = pd.DataFrame(results)
    dep_df = pd.DataFrame(dep_rows)
    if len(dep_df):
        checks.append(vrow("all_dependency_copies_ok", bool(dep_df["copied"].all()), int((~dep_df["copied"]).sum()), 0))
    if len(res_df):
        checks += [
            vrow("all_stage80_returncode_zero", bool((res_df["returncode"] == 0).all()), int((res_df["returncode"] != 0).sum()), 0),
            vrow("all_decisions_detectable", bool(res_df["decision"].isin(["NO_SIGNAL", "SIGNAL"]).all()), sorted(res_df[~res_df["decision"].isin(["NO_SIGNAL", "SIGNAL"])] ["decision"].unique().tolist()), "NO_SIGNAL or SIGNAL"),
            vrow("no_signal_rows_skip_sidecar", bool(res_df[res_df["decision"] == "NO_SIGNAL"]["stage85_returncode"].eq("SKIPPED_NO_SIGNAL").all()), "checked", "SKIPPED_NO_SIGNAL"),
        ]
    else:
        checks.append(vrow("replay_results_nonempty", False, 0, ">0"))
    for c in checks:
        if c["result"] != "PASS":
            blockers.append({"blocker_id": c["check_id"], "reason": "VALIDATION_FAILED", "detail": c, "severity": "BLOCKER"})
    status = READY if not blockers else BLOCKED
    signal_df = res_df[res_df["decision"] == "SIGNAL"].copy() if len(res_df) else pd.DataFrame()
    error_df = res_df[res_df["returncode"] != 0].copy() if len(res_df) else pd.DataFrame()

    res_df.drop(columns=["tail"], errors="ignore").to_csv(out / "replay_results.csv", index=False, encoding="utf-8-sig")
    res_df.to_csv(out / "replay_results_with_tail.csv", index=False, encoding="utf-8-sig")
    signal_df.drop(columns=["tail"], errors="ignore").to_csv(out / "signal_rows.csv", index=False, encoding="utf-8-sig")
    dep_df.to_csv(out / "dependency_copy_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(checks).to_csv(out / "validation.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(blockers).to_csv(out / "blockers.csv", index=False, encoding="utf-8-sig")
    summary = {
        "status": status,
        "recent_closed_candle_signal_replay_ready": status == READY,
        "audit_only": True,
        "live_ready": False,
        "mt5_execution_enabled": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "final_signal_enabled": False,
        "durable_ledger_append_enabled": False,
        "contract_mutated": False,
        "source_csv_mutated": False,
        "manual_candidate_demotion_or_removal": False,
        "open_asof_allowed": False,
        "csv_contract": CSV_CONTRACT,
        "csv_open_bar_exclusion_required": False,
        "pool_policy": POOL_POLICY,
        "requested_bars": int(args.bars),
        "replayed_bars": int(len(res_df)),
        "signal_count": int(len(signal_df)),
        "no_signal_count": int((res_df["decision"] == "NO_SIGNAL").sum()) if len(res_df) else 0,
        "unknown_count": int((~res_df["decision"].isin(["NO_SIGNAL", "SIGNAL"])).sum()) if len(res_df) else 0,
        "returncode_nonzero_count": int((res_df["returncode"] != 0).sum()) if len(res_df) else 0,
        "replay_root": str(replay_root),
        "blocker_count": len(blockers),
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paste = [
        "GOLD V3 99 PASTE_ME_RECENT_CLOSED_CANDLE_SIGNAL_REPLAY_SUMMARY",
        f"status: {status}",
        f"recent_closed_candle_signal_replay_ready: {str(status == READY).lower()}",
        "live_ready: false",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"requested_bars: {int(args.bars)}",
        f"replayed_bars: {len(res_df)}",
        f"signal_count: {len(signal_df)}",
        f"no_signal_count: {int((res_df['decision'] == 'NO_SIGNAL').sum()) if len(res_df) else 0}",
        f"unknown_count: {int((~res_df['decision'].isin(['NO_SIGNAL','SIGNAL'])).sum()) if len(res_df) else 0}",
        f"returncode_nonzero_count: {int((res_df['returncode'] != 0).sum()) if len(res_df) else 0}",
        f"replay_root: {replay_root}",
        f"blocker_count: {len(blockers)}",
        "", "SIGNAL_ROWS", signal_df.drop(columns=["tail"], errors="ignore").to_string(index=False) if len(signal_df) else "NO_SIGNAL_ROWS_FOUND_IN_REPLAY_WINDOW",
        "", "ERROR_ROWS", error_df[["idx", "asof_m15", "returncode", "decision", "tail"]].head(8).to_string(index=False) if len(error_df) else "NO_ERROR_ROWS",
        "", "REPLAY_RESULTS_HEAD", res_df.drop(columns=["tail"], errors="ignore").head(10).to_string(index=False) if len(res_df) else "NO_ROWS",
        "", "REPLAY_RESULTS_TAIL", res_df.drop(columns=["tail"], errors="ignore").tail(10).to_string(index=False) if len(res_df) else "NO_ROWS",
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(checks).to_string(index=False),
        "", "OUTPUTS", "paste_me.txt", "summary.json", "replay_results.csv", "replay_results_with_tail.csv", "signal_rows.csv", "dependency_copy_matrix.csv", "validation.csv", "blockers.csv", "report.md",
    ]
    (out / "paste_me.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    (out / "report.md").write_text(f"# GOLD V3 99 recent closed candle signal replay\n\nStatus: `{status}`\n\nReplayed bars: `{len(res_df)}`\nSignal count: `{len(signal_df)}`\nNonzero returncodes: `{summary['returncode_nonzero_count']}`\nReplay root: `{replay_root}`\nBlockers: `{len(blockers)}`\n", encoding="utf-8")
    print(f"[{status}] {out / 'paste_me.txt'}")
    return 0 if status == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
