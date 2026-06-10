#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, shutil, subprocess, sys, time
from pathlib import Path
from typing import Any
import pandas as pd

READY = "GOLD_V3_99_RECENT_CLOSED_CANDLE_SIGNAL_REPLAY_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_99_RECENT_CLOSED_CANDLE_SIGNAL_REPLAY_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"

CSV_NAMES = ["goldsharp_m15.csv", "goldsharp_h1.csv", "goldsharp_h4.csv", "goldsharp_d1.csv", "goldsharp_m5.csv"]


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.resolve()
        if (d / "goldsharp_m15.csv").exists() or (d / "FX_OUTPUTS" / "gold_v3").exists():
            return d
    raise SystemExit("Files dir not found")


def read_csv_any(path: Path) -> tuple[pd.DataFrame, str]:
    sample = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()[0]
    sep = ";" if sample.count(";") >= sample.count(",") else ","
    return pd.read_csv(path, sep=sep, encoding="utf-8-sig"), sep


def write_csv(df: pd.DataFrame, path: Path, sep: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep=sep, index=False, encoding="utf-8-sig")


def latest_time(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(df["time"], errors="raise")


def safe_name(ts: Any) -> str:
    return str(pd.to_datetime(ts)).replace("-", "").replace(":", "").replace(" ", "_")


def run_stage80(repo: Path, cdir: Path) -> tuple[int, str, float]:
    s80 = repo / "scripts" / "gold_v3_runtime" / "gold_v3_80_immutable_runtime_monitor_audit.py"
    cmd = [sys.executable, str(s80), "--candle-dir", str(cdir), "--once", "--run-immediately", "--enable-signal-gated-ledger-sidecar", "--disable-auto-support-bundle"]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=str(repo), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return int(p.returncode), p.stdout[-3000:], time.perf_counter() - t0


def rj(p: Path) -> dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception as e:
        return {"_error": repr(e)}


def row(cid, ok, obs, exp, sev="BLOCKER"):
    return {"check_id": cid, "result": "PASS" if ok else "FAIL", "observed": obs, "expected": exp, "severity": sev}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candle-dir", default="")
    ap.add_argument("--bars", type=int, default=32)
    ap.add_argument("--output-dir", default="")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]
    src = Path(args.candle_dir).resolve() if args.candle_dir else find_files_dir()
    base = src / "FX_OUTPUTS" / "gold_v3"
    out = Path(args.output_dir).resolve() if args.output_dir else base / "99c"
    replay_root = out / "replay_inputs"
    out.mkdir(parents=True, exist_ok=True)
    replay_root.mkdir(parents=True, exist_ok=True)

    checks = []
    blockers = []
    p_m15 = src / "goldsharp_m15.csv"
    checks.append(row("source_m15_present", p_m15.exists(), str(p_m15), "exists"))
    if not p_m15.exists():
        blockers.append({"blocker_id": "source_m15_missing", "reason": "REQUIRED_INPUT_MISSING", "detail": str(p_m15), "severity": "BLOCKER"})
        bars = []
    else:
        m15, sep15 = read_csv_any(p_m15)
        m15["__time"] = latest_time(m15)
        bars = list(m15.tail(max(1, int(args.bars)))["__time"])
        checks.append(row("replay_bar_count_positive", len(bars) > 0, len(bars), ">0"))

    results = []
    for i, ts in enumerate(bars, start=1):
        rdir = replay_root / f"{i:03d}_{safe_name(ts)}"
        if rdir.exists():
            shutil.rmtree(rdir)
        rdir.mkdir(parents=True, exist_ok=True)
        for name in CSV_NAMES:
            sp = src / name
            if not sp.exists():
                continue
            df, sep = read_csv_any(sp)
            if "time" in df.columns:
                t = pd.to_datetime(df["time"], errors="coerce")
                df = df[t <= ts].copy()
            write_csv(df, rdir / name, sep)
        rc, tail, sec = run_stage80(repo, rdir)
        summ = rj(rdir / "FX_OUTPUTS" / "gold_v3" / "80_immutable_runtime_monitor_audit_only" / "gold_v3_80_immutable_runtime_monitor_summary.json")
        decision = str(summ.get("sidecar_decision", ""))
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
            "tail": tail.replace("\r", " ").replace("\n", " ")[-500:],
        })

    res_df = pd.DataFrame(results)
    if len(res_df):
        checks += [
            row("all_stage80_returncode_zero", bool((res_df["returncode"] == 0).all()), int((res_df["returncode"] != 0).sum()), 0),
            row("all_decisions_detectable", bool(res_df["decision"].isin(["NO_SIGNAL", "SIGNAL"]).all()), sorted(res_df[~res_df["decision"].isin(["NO_SIGNAL", "SIGNAL"])] ["decision"].unique().tolist()), "NO_SIGNAL or SIGNAL"),
            row("no_signal_rows_skip_sidecar", bool(res_df[res_df["decision"] == "NO_SIGNAL"]["stage85_returncode"].eq("SKIPPED_NO_SIGNAL").all()), "checked", "SKIPPED_NO_SIGNAL"),
        ]
    for c in checks:
        if c["result"] != "PASS":
            blockers.append({"blocker_id": c["check_id"], "reason": "VALIDATION_FAILED", "detail": c, "severity": "BLOCKER"})
    status = READY if not blockers else BLOCKED
    signal_df = res_df[res_df["decision"] == "SIGNAL"].copy() if len(res_df) else pd.DataFrame()

    res_df.drop(columns=["tail"], errors="ignore").to_csv(out / "replay_results.csv", index=False, encoding="utf-8-sig")
    signal_df.drop(columns=["tail"], errors="ignore").to_csv(out / "signal_rows.csv", index=False, encoding="utf-8-sig")
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
        f"blocker_count: {len(blockers)}",
        "", "SIGNAL_ROWS", signal_df.drop(columns=["tail"], errors="ignore").to_string(index=False) if len(signal_df) else "NO_SIGNAL_ROWS_FOUND_IN_REPLAY_WINDOW",
        "", "REPLAY_RESULTS_HEAD", res_df.drop(columns=["tail"], errors="ignore").head(10).to_string(index=False) if len(res_df) else "NO_ROWS",
        "", "REPLAY_RESULTS_TAIL", res_df.drop(columns=["tail"], errors="ignore").tail(10).to_string(index=False) if len(res_df) else "NO_ROWS",
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(checks).to_string(index=False),
        "", "OUTPUTS", "paste_me.txt", "summary.json", "replay_results.csv", "signal_rows.csv", "validation.csv", "blockers.csv", "report.md",
    ]
    (out / "paste_me.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    (out / "report.md").write_text(f"# GOLD V3 99 recent closed candle signal replay\n\nStatus: `{status}`\n\nReplayed bars: `{len(res_df)}`\nSignal count: `{len(signal_df)}`\nBlockers: `{len(blockers)}`\n", encoding="utf-8")
    print(f"[{status}] {out / 'paste_me.txt'}")
    return 0 if status == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
