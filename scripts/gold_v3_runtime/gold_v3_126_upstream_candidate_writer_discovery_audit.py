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

STEP = "GOLD_V3_126_UPSTREAM_CANDIDATE_WRITER_DISCOVERY_AUDIT_ONLY"
READY = STEP + "_READY"
BLOCKED = STEP + "_BLOCKED"

TARGETS = {
    "107GB": ("107gbc", "gold_v3_107gb_top_candidate_trade_ledger.csv"),
    "107GD": ("107gdc", "gold_v3_107gd_diversified_portfolio_ledger.csv"),
    "107GL": ("107glc", "gold_v3_107gl_top_vector_trade_ledger.csv"),
    "107GN": ("107gnc", "gold_v3_107gn_top_candidate_trade_ledger.csv"),
    "107GO": ("107goc", "gold_v3_107go_portfolio_ledger.csv"),
}


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


def coverage(path: Path, label: str) -> dict:
    row = {"label": label, "path": str(path), "exists": path.exists(), "rows": 0, "time_col": "", "min_dt": "", "max_dt": "", "error": ""}
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
        row["time_col"] = tcol
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


def score_text(text: str, subdir: str, filename: str) -> int:
    low = text.lower()
    score = 0
    if subdir.lower() in low:
        score += 5
    if filename in text:
        score += 20
    if "save(" in low and filename in text:
        score += 20
    if ".to_csv" in low and filename in text:
        score += 20
    if f'out = root / "{subdir}"' in text or f"out = root / '{subdir}'" in text or f'out=root/"{subdir}"' in text or f"out=root/'{subdir}'" in text:
        score += 30
    if f'src = root / "{subdir}"' in text or f"src = root / '{subdir}'" in text or f"missing_{subdir}" in low:
        score -= 25
    return score


def discover(runtime: Path) -> pd.DataFrame:
    rows = []
    for p in sorted(runtime.glob("gold_v3_*.py")):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        low = text.lower()
        for label, (subdir, filename) in TARGETS.items():
            if subdir.lower() not in low and filename.lower() not in low and label.lower() not in low:
                continue
            snippets = []
            for i, line in enumerate(text.splitlines(), 1):
                ll = line.lower()
                if subdir.lower() in ll or filename.lower() in ll or label.lower() in ll:
                    snippets.append(f"L{i}:{line.strip()[:200]}")
            rows.append({"target": label, "script": p.name, "path": str(p), "score": score_text(text, subdir, filename), "matches": " || ".join(snippets[:25])})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["target", "score", "script"], ascending=[True, False, True]).reset_index(drop=True)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]
    runtime = repo / "scripts" / "gold_v3_runtime"
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "126"
    out.mkdir(parents=True, exist_ok=True)

    cov_rows = []
    for label, (subdir, filename) in TARGETS.items():
        cov_rows.append(coverage(root / subdir / filename, label))
    cov_df = pd.DataFrame(cov_rows)
    save(cov_df, out / "gold_v3_126_current_candidate_coverage.csv")

    cand = discover(runtime)
    save(cand, out / "gold_v3_126_writer_candidates.csv")

    top_rows = []
    blockers = []
    for label in TARGETS:
        x = cand[cand.target == label].copy() if not cand.empty else pd.DataFrame()
        if x.empty or int(x.iloc[0].score) <= 0:
            blockers.append({"blocker_id": "writer_not_found", "target": label})
        else:
            top_rows.append(x.iloc[0].to_dict())
    top_df = pd.DataFrame(top_rows)
    save(top_df, out / "gold_v3_126_top_writer_candidates.csv")

    status = READY if top_rows else BLOCKED
    decision = "UPSTREAM_WRITER_CANDIDATES_FOUND" if top_rows else "UPSTREAM_WRITER_CANDIDATES_NOT_FOUND"
    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "target_writer_count": len(top_rows),
        "candidate_count": int(len(cand)) if not cand.empty else 0,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "review_only": True,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    write_json(out / "gold_v3_126_summary.json", summary | {"blockers": blockers})
    save(pd.DataFrame([summary]), out / "gold_v3_126_decision.csv")

    lines = ["GOLD V3 126 PASTE_ME_UPSTREAM_CANDIDATE_WRITER_DISCOVERY_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "CURRENT_CANDIDATE_COVERAGE", cov_df.to_string(index=False)]
    lines += ["", "TOP_WRITER_CANDIDATES", top_df.to_string(index=False) if not top_df.empty else "NO_TOP_WRITERS"]
    lines += ["", "ALL_WRITER_CANDIDATES", cand.head(50).to_string(index=False) if not cand.empty else "NO_CANDIDATES"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
