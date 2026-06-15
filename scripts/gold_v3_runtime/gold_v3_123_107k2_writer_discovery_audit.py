#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_123_107K2_WRITER_DISCOVERY_AUDIT_ONLY"
READY = STEP + "_READY"
BLOCKED = STEP + "_BLOCKED"
TARGET = pd.Timestamp("2026-06-15")

OUTPUT_NAMES = [
    "gold_v3_107k2_regime_frontier.csv",
    "gold_v3_107k2_all_regime_ledgers.csv",
]


def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def detect_sep(path: Path) -> str:
    try:
        s = path.read_text(encoding="utf-8-sig", errors="ignore")[:4096]
        return ";" if s.count(";") > s.count(",") else ","
    except Exception:
        return ","


def coverage(path: Path) -> dict:
    row = {"path": str(path), "exists": path.exists(), "rows": 0, "time_col": "", "min_dt": "", "max_dt": "", "error": ""}
    if not path.exists():
        row["error"] = "missing"
        return row
    try:
        df = pd.read_csv(path, sep=detect_sep(path), encoding="utf-8-sig", low_memory=False)
        row["rows"] = int(len(df))
        tcol = ""
        for c in ["entry_dt", "exit_dt", "time", "datetime", "date", "timestamp", "dt"]:
            if c in df.columns:
                tcol = c
                break
        if not tcol:
            for c in df.columns:
                cl = str(c).lower()
                if "entry" in cl and "dt" in cl:
                    tcol = c
                    break
        row["time_col"] = str(tcol)
        if not tcol:
            row["error"] = "missing_time_column"
            return row
        t = pd.to_datetime(df[tcol], errors="coerce").dropna()
        if len(t):
            row["min_dt"] = str(t.min())
            row["max_dt"] = str(t.max())
        else:
            row["error"] = "all_time_parse_failed"
    except Exception as e:
        row["error"] = repr(e)
    return row


def score_script(text: str) -> int:
    low = text.lower()
    score = 0
    if "107k2c" in low:
        score += 5
    if any(n in text for n in OUTPUT_NAMES):
        score += 10
    if "save(" in low and any(n in text for n in OUTPUT_NAMES):
        score += 20
    if ".to_csv" in low and any(n in text for n in OUTPUT_NAMES):
        score += 20
    if 'out=root/"107k2c"' in low or "out=root/'107k2c'" in low or 'out = root / "107k2c"' in low or "out = root / '107k2c'" in low:
        score += 30
    if "missing_107k2" in low or 'src=root/"107k2c"' in low or "src=root/'107k2c'" in low or 'src = root / "107k2c"' in low or "src = root / '107k2c'" in low:
        score -= 25
    if "pd.read_csv" in low and "107k2c" in low and not ("save(" in low or ".to_csv" in low):
        score -= 20
    return score


def discover(runtime: Path) -> pd.DataFrame:
    rows = []
    for p in sorted(runtime.glob("gold_v3_*.py")):
        if p.name == Path(__file__).name:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        low = text.lower()
        if "107k2" not in low and not any(n.lower() in low for n in OUTPUT_NAMES):
            continue
        snippets = []
        for i, line in enumerate(text.splitlines(), 1):
            ll = line.lower()
            if "107k2" in ll or any(n.lower() in ll for n in OUTPUT_NAMES):
                snippets.append(f"L{i}:{line.strip()[:200]}")
        rows.append({"script": p.name, "path": str(p), "score": score_script(text), "matches": " || ".join(snippets[:30])})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["score", "script"], ascending=[False, True]).reset_index(drop=True)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]
    runtime = repo / "scripts" / "gold_v3_runtime"
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "123"
    out.mkdir(parents=True, exist_ok=True)

    cov = pd.DataFrame([
        {"name": "107k2_frontier", **coverage(root / "107k2c" / "gold_v3_107k2_regime_frontier.csv")},
        {"name": "107k2_all_regime_ledgers", **coverage(root / "107k2c" / "gold_v3_107k2_all_regime_ledgers.csv")},
        {"name": "107l_rehydrated_best_policy_ledger", **coverage(root / "107lc" / "gold_v3_107l_rehydrated_best_policy_ledger.csv")},
    ])
    save(cov, out / "gold_v3_123_107k2_current_coverage.csv")

    cand = discover(runtime)
    save(cand, out / "gold_v3_123_107k2_writer_candidates.csv")

    top_script = str(cand.iloc[0].script) if not cand.empty else ""
    top_score = int(cand.iloc[0].score) if not cand.empty else 0
    decision = "107K2_WRITER_CANDIDATE_FOUND" if top_score > 0 else "107K2_WRITER_NOT_FOUND_OR_LOW_CONFIDENCE"
    status = READY if top_score > 0 else BLOCKED
    blockers = [] if top_score > 0 else [{"blocker_id": "no_positive_107k2_writer_candidate", "action": "inspect gold_v3_123_107k2_writer_candidates.csv"}]

    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "top_script": top_script,
        "top_score": top_score,
        "candidate_count": int(len(cand)) if not cand.empty else 0,
        "target": str(TARGET),
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "review_only": True,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    write_json(out / "gold_v3_123_summary.json", summary | {"blockers": blockers})
    save(pd.DataFrame([summary]), out / "gold_v3_123_decision.csv")

    lines = ["GOLD V3 123 PASTE_ME_107K2_WRITER_DISCOVERY_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "CURRENT_COVERAGE", cov.to_string(index=False)]
    lines += ["", "WRITER_CANDIDATES", cand.head(20).to_string(index=False) if not cand.empty else "NO_CANDIDATES"]
    lines += ["", "NEXT_ACTION"]
    if top_score > 0:
        lines += [f"Run candidate writer: py -3 scripts\\gold_v3_runtime\\{top_script}", "Then rerun: scripts\\gold_v3_runtime\\bat\\run_gold_v3_122_regenerate_107l_then_june_01_15_audit.bat"]
    else:
        lines += ["No confident writer found. Paste this file."]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "top_script": top_script, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
