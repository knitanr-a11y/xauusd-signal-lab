#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json
from pathlib import Path
from typing import Any
import pandas as pd

READY = "GOLD_V3_101_STAGE69_DETECTION_COVERAGE_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_101_STAGE69_DETECTION_COVERAGE_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "99c" / "replay_results.csv").exists():
            return d
    raise SystemExit("Files dir with Stage99 output not found")


def rj(p: Path) -> dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception as e:
        return {"_error": repr(e)}


def rcsv(p: Path) -> pd.DataFrame:
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(p, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame()


def vrow(cid: str, passed: bool, obs: Any, exp: Any, sev: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": cid, "result": "PASS" if passed else "FAIL", "observed": obs, "expected": exp, "severity": sev}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candle-dir", default="")
    ap.add_argument("--stage99-dir", default="")
    ap.add_argument("--output-dir", default="")
    args = ap.parse_args()

    src = Path(args.candle_dir).resolve() if args.candle_dir else find_files_dir()
    base = src / "FX_OUTPUTS" / "gold_v3"
    s99 = Path(args.stage99_dir).resolve() if args.stage99_dir else base / "99c"
    out = Path(args.output_dir).resolve() if args.output_dir else base / "101c"
    out.mkdir(parents=True, exist_ok=True)

    p99s = s99 / "summary.json"
    p99r = s99 / "replay_results.csv"
    j99 = rj(p99s)
    replay = rcsv(p99r)
    checks = [
        vrow("stage99_summary_present", p99s.exists(), str(p99s), "exists"),
        vrow("stage99_results_present", p99r.exists(), str(p99r), "exists"),
        vrow("stage99_ready", j99.get("recent_closed_candle_signal_replay_ready") is True, j99.get("recent_closed_candle_signal_replay_ready"), True),
        vrow("stage99_results_nonempty", not replay.empty, len(replay), ">0"),
    ]
    blockers = []
    rows = []
    cand_rows = []
    if replay.empty:
        blockers.append({"blocker_id": "stage99_results_empty", "reason": "REQUIRED_INPUT_MISSING", "detail": str(p99r), "severity": "BLOCKER"})
    else:
        for _, rr in replay.iterrows():
            idx = int(rr.get("idx", 0)) if str(rr.get("idx", "")).strip() else 0
            asof = str(rr.get("asof_m15", ""))
            rdir = Path(str(rr.get("replay_dir", "")))
            s69 = rdir / "FX_OUTPUTS" / "gold_v3" / "69_live_csv_condition_detector_audit_only"
            js = rj(s69 / "gold_v3_69_live_csv_condition_detector_summary.json")
            det = rcsv(s69 / "gold_v3_69_detected_candidate_conditions.csv")
            latest = rcsv(s69 / "gold_v3_69_latest_closed_condition_candidates.csv")
            det_rows = int(js.get("detected_condition_rows", len(det) if not det.empty else 0) or 0)
            latest_rows = int(js.get("latest_closed_condition_candidate_rows", len(latest) if not latest.empty else 0) or 0)
            stage51_rows = int(js.get("stage51_rows", 0) or 0)
            missing51 = int(js.get("stage51_missing_detection_count", 0) or 0)
            q70_joined = int(js.get("q70_joined_rows", 0) or 0)
            q70_missing = int(js.get("q70_missing_rows", 0) or 0)
            last_detected = ""
            hours_since = ""
            if not det.empty and "entry_dt" in det.columns:
                dt = pd.to_datetime(det["entry_dt"], errors="coerce").dropna()
                if len(dt):
                    mx = dt.max()
                    last_detected = str(mx)
                    try:
                        hours_since = round((pd.to_datetime(asof) - mx).total_seconds() / 3600.0, 4)
                    except Exception:
                        hours_since = ""
            rows.append({
                "idx": idx,
                "asof_m15": asof,
                "stage69_status": str(js.get("status", "")),
                "detected_condition_rows": det_rows,
                "latest_closed_condition_candidate_rows": latest_rows,
                "stage51_rows": stage51_rows,
                "stage51_missing_detection_count": missing51,
                "q70_joined_rows": q70_joined,
                "q70_missing_rows": q70_missing,
                "last_detected_condition_time": last_detected,
                "hours_since_last_detected_condition": hours_since,
                "replay_dir": str(rdir),
            })
            if not det.empty:
                for _, dr in det.iterrows():
                    cand_rows.append({"idx": idx, "asof_m15": asof, "candidate_label": str(dr.get("candidate_label", "")), "entry_dt": str(dr.get("entry_dt", "")), "condition_id": str(dr.get("condition_id", ""))})
    cov = pd.DataFrame(rows)
    cand = pd.DataFrame(cand_rows)
    if not cov.empty:
        checks.append(vrow("coverage_rows_match_replay_rows", len(cov) == len(replay), len(cov), len(replay)))
        checks.append(vrow("stage69_any_detected_conditions", int(cov["detected_condition_rows"].max()) > 0, int(cov["detected_condition_rows"].max()), ">0", "WARN"))
    else:
        checks.append(vrow("coverage_nonempty", False, 0, ">0"))
    for c in checks:
        if c["result"] != "PASS" and c.get("severity") == "BLOCKER":
            blockers.append({"blocker_id": c["check_id"], "reason": "VALIDATION_FAILED", "detail": c, "severity": "BLOCKER"})
    status = READY if not blockers else BLOCKED

    det_by_idx = cov["detected_condition_rows"].describe().reset_index() if not cov.empty else pd.DataFrame()
    candidate_counts = cand["candidate_label"].value_counts(dropna=False).reset_index() if not cand.empty else pd.DataFrame(columns=["candidate_label", "count"])
    if not candidate_counts.empty:
        candidate_counts.columns = ["candidate_label", "count"]
    cov.to_csv(out / "stage69_detection_coverage.csv", index=False, encoding="utf-8-sig")
    cand.to_csv(out / "stage69_detected_condition_rows_long.csv", index=False, encoding="utf-8-sig")
    candidate_counts.to_csv(out / "candidate_label_counts.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(checks).to_csv(out / "validation.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(blockers).to_csv(out / "blockers.csv", index=False, encoding="utf-8-sig")
    bars_with_any = int((cov["detected_condition_rows"] > 0).sum()) if not cov.empty else 0
    max_detected = int(cov["detected_condition_rows"].max()) if not cov.empty else 0
    max_latest = int(cov["latest_closed_condition_candidate_rows"].max()) if not cov.empty else 0
    min_hours = cov["hours_since_last_detected_condition"].replace("", pd.NA).dropna().min() if not cov.empty else ""
    summary = {
        "status": status,
        "stage69_detection_coverage_ready": status == READY,
        "audit_only": True,
        "live_ready": False,
        "mt5_execution_enabled": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "final_signal_enabled": False,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "manual_candidate_demotion_or_removal": False,
        "open_asof_allowed": False,
        "csv_contract": CSV_CONTRACT,
        "csv_open_bar_exclusion_required": False,
        "pool_policy": POOL_POLICY,
        "stage99_replayed_bars": int(len(replay)) if not replay.empty else 0,
        "coverage_rows": int(len(cov)),
        "bars_with_any_detected_conditions_before_asof": bars_with_any,
        "max_detected_condition_rows_before_asof": max_detected,
        "max_latest_closed_condition_candidate_rows": max_latest,
        "min_hours_since_last_detected_condition": "" if pd.isna(min_hours) else min_hours,
        "blocker_count": len(blockers),
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paste = [
        "GOLD V3 101 PASTE_ME_STAGE69_DETECTION_COVERAGE_SUMMARY",
        f"status: {status}",
        f"stage69_detection_coverage_ready: {str(status == READY).lower()}",
        "live_ready: false",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"stage99_replayed_bars: {summary['stage99_replayed_bars']}",
        f"coverage_rows: {summary['coverage_rows']}",
        f"bars_with_any_detected_conditions_before_asof: {bars_with_any}",
        f"max_detected_condition_rows_before_asof: {max_detected}",
        f"max_latest_closed_condition_candidate_rows: {max_latest}",
        f"min_hours_since_last_detected_condition: {summary['min_hours_since_last_detected_condition']}",
        f"blocker_count: {len(blockers)}",
        "", "CANDIDATE_LABEL_COUNTS", candidate_counts.head(50).to_string(index=False) if not candidate_counts.empty else "NO_CANDIDATE_ROWS",
        "", "COVERAGE_HEAD", cov.head(20).to_string(index=False) if not cov.empty else "NO_COVERAGE_ROWS",
        "", "COVERAGE_TAIL", cov.tail(20).to_string(index=False) if not cov.empty else "NO_COVERAGE_ROWS",
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(checks).to_string(index=False),
        "", "OUTPUTS", "paste_me.txt", "summary.json", "stage69_detection_coverage.csv", "stage69_detected_condition_rows_long.csv", "candidate_label_counts.csv", "validation.csv", "blockers.csv", "report.md",
    ]
    (out / "paste_me.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    (out / "report.md").write_text(f"# GOLD V3 101 Stage69 detection coverage\n\nStatus: `{status}`\n\n- replay rows: `{summary['stage99_replayed_bars']}`\n- bars with any detected conditions before/asof: `{bars_with_any}`\n- max detected rows before/asof: `{max_detected}`\n- max latest candidate rows: `{max_latest}`\n- blockers: `{len(blockers)}`\n", encoding="utf-8")
    print(f"[{status}] {out / 'paste_me.txt'}")
    return 0 if status == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
