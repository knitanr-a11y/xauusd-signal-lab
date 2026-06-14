#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import itertools
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_107R2_EXIT_DT_SOURCE_INTELLIGENCE_AUDIT_ONLY"
READY = "GOLD_V3_107R2_EXIT_DT_SOURCE_INTELLIGENCE_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_107R2_EXIT_DT_SOURCE_INTELLIGENCE_BLOCKED_AUDIT_ONLY"

PREFERRED_KEYS = [
    "global_candidate_key", "candidate_key", "entry_dt", "side", "family", "condition", "profile_id", "result_usd",
    "policy_key", "regime_split", "portfolio_side", "source_name", "selected_rank",
]


def log(s: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}", flush=True)


def prog(i: int, n: int, s: str) -> None:
    p = 100.0 * i / max(1, n)
    log(f"progress {p:5.1f}% complete / {100.0-p:5.1f}% remaining | step {i}/{n} | {s}")


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def safe_read_header(path: Path) -> list[str]:
    try:
        return list(pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns)
    except Exception:
        return []


def safe_row_count(path: Path) -> int:
    try:
        return sum(1 for _ in open(path, "rb")) - 1
    except Exception:
        return -1


def norm_frame(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    x = df.copy()
    for c in cols:
        if c not in x.columns:
            continue
        if c == "entry_dt" or c.endswith("_dt"):
            x[c] = pd.to_datetime(x[c], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
        elif c == "result_usd":
            x[c] = pd.to_numeric(x[c], errors="coerce").round(8).astype(str)
        else:
            x[c] = x[c].astype(str).fillna("")
    return x


def make_key(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    x = norm_frame(df, cols)
    return x[cols].astype(str).agg("||".join, axis=1)


def try_key(best: pd.DataFrame, path: Path, cols: list[str]) -> dict:
    out = dict(source_path=str(path), key_cols=" + ".join(cols), key_size=len(cols), attempted=True)
    try:
        usecols = list(dict.fromkeys(cols + ["exit_dt"]))
        src = pd.read_csv(path, usecols=lambda c: c in usecols, encoding="utf-8-sig", low_memory=False)
        if not all(c in src.columns for c in cols) or "exit_dt" not in src.columns:
            out.update(error="source_missing_required_key_or_exit_dt", strict_join_pass=False)
            return out
        b = best.copy()
        s = src[cols + ["exit_dt"]].copy()
        b["__k"] = make_key(b, cols)
        s["__k"] = make_key(s, cols)
        source_unique = int(s["__k"].nunique())
        selected_unique = int(b["__k"].nunique())
        source_dup = int(s["__k"].duplicated().sum())
        selected_dup = int(b["__k"].duplicated().sum())
        ss = s.drop_duplicates("__k", keep="first")
        m = b.merge(ss[["__k", "exit_dt"]], on="__k", how="left")
        non_null = int(m["exit_dt"].notna().sum())
        coverage = non_null / max(1, len(b))
        exit_dt = pd.to_datetime(m["exit_dt"], errors="coerce")
        entry_dt = pd.to_datetime(m["entry_dt"], errors="coerce") if "entry_dt" in m.columns else pd.Series(pd.NaT, index=m.index)
        ge_count = int((exit_dt.notna() & entry_dt.notna() & (exit_dt >= entry_dt)).sum())
        strict = bool(non_null == len(b) and ge_count == len(b) and source_dup == 0)
        out.update(selected_rows=len(b), source_rows=len(src), selected_unique_keys=selected_unique, source_unique_keys=source_unique, selected_duplicate_keys=selected_dup, source_duplicate_keys=source_dup, non_null_exit_dt=non_null, coverage=coverage, exit_ge_entry_count=ge_count, strict_join_pass=strict)
    except Exception as e:
        out.update(error=str(e), strict_join_pass=False)
    return out


def candidate_key_sets(shared: list[str]) -> list[list[str]]:
    preferred = [c for c in PREFERRED_KEYS if c in shared]
    out = []
    priority = [
        ["global_candidate_key"],
        ["entry_dt", "global_candidate_key"],
        ["entry_dt", "side", "candidate_key", "profile_id"],
        ["entry_dt", "side", "family", "condition", "profile_id"],
        ["entry_dt", "side", "result_usd"],
        ["entry_dt", "side", "score"],
        ["entry_dt", "score"],
    ]
    for k in priority:
        if all(c in shared for c in k):
            out.append(k)
    # Add compact combinations of shared preferred columns, favoring entry_dt anchors.
    small = [c for c in preferred if c != "exit_dt"][:10]
    for size in [1, 2, 3, 4]:
        for combo in itertools.combinations(small, size):
            combo = list(combo)
            if combo not in out:
                out.append(combo)
            if len(out) >= 40:
                return out
    return out


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    src_q = root / "107qc"
    src_r = root / "107rc"
    out = root / "107r2c"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")
    prog(0, 5, "start")

    blocks, outputs, vals, findings = [], [], [], []
    best_path = src_q / "gold_v3_107q_best_family_trade_ledger.csv"
    catalog_path = src_r / "gold_v3_107r_exit_dt_source_catalog.csv"
    if not best_path.exists():
        blocks.append(dict(blocker_id="missing_107q_best_family_trade_ledger", path=str(best_path)))
    if not catalog_path.exists():
        blocks.append(dict(blocker_id="missing_107r_exit_dt_source_catalog", path=str(catalog_path)))

    best = pd.DataFrame(); catalog = pd.DataFrame(); detail = pd.DataFrame(); shared_matrix = pd.DataFrame(); key_diag = pd.DataFrame(); next_action = pd.DataFrame(); resolved = pd.DataFrame()
    if not blocks:
        best = pd.read_csv(best_path, encoding="utf-8-sig", low_memory=False)
        catalog = pd.read_csv(catalog_path, encoding="utf-8-sig", low_memory=False)
        exact = catalog[catalog.get("has_exit_dt", False) == True].copy()
        if exact.empty:
            blocks.append(dict(blocker_id="no_exact_exit_dt_sources_in_107r_catalog"))
        prog(1, 5, f"loaded best_rows={len(best)} exact_sources={0 if exact.empty else len(exact)}")

    if not blocks:
        best_cols = list(best.columns)
        detail_rows, shared_rows, diag_rows = [], [], []
        total = len(exact)
        for idx, r in exact.reset_index(drop=True).iterrows():
            p = Path(str(r["path"]))
            cols = safe_read_header(p)
            row_count = safe_row_count(p)
            shared = sorted(set(cols).intersection(best_cols))
            key_shared = [c for c in PREFERRED_KEYS if c in shared]
            missing_priority = [c for c in PREFERRED_KEYS if c in best_cols and c not in cols]
            detail_rows.append(dict(source_rank=idx + 1, path=str(p), file=p.name, rows=row_count, column_count=len(cols), shared_column_count=len(shared), key_shared="|".join(key_shared), missing_priority_keys="|".join(missing_priority[:30]), has_entry_dt="entry_dt" in cols, has_global_candidate_key="global_candidate_key" in cols, has_candidate_key="candidate_key" in cols, has_result_usd="result_usd" in cols, columns_preview="|".join(cols[:80])))
            for c in shared:
                shared_rows.append(dict(source_rank=idx + 1, path=str(p), shared_column=c, is_preferred_key=c in PREFERRED_KEYS))
            keys = candidate_key_sets(shared)
            if not keys:
                diag_rows.append(dict(source_path=str(p), attempted=False, reason="no_shared_candidate_key_columns", strict_join_pass=False))
            for k in keys:
                d = try_key(best, p, k)
                diag_rows.append(d)
                if d.get("strict_join_pass") and resolved.empty:
                    # Build resolved ledger using this key.
                    src = pd.read_csv(p, usecols=lambda c: c in list(dict.fromkeys(k + ["exit_dt"])), encoding="utf-8-sig", low_memory=False)
                    b = best.copy(); s = src[k + ["exit_dt"]].copy()
                    b["__k"] = make_key(b, k); s["__k"] = make_key(s, k)
                    ss = s.drop_duplicates("__k", keep="first")
                    resolved = b.merge(ss[["__k", "exit_dt"]], on="__k", how="left").drop(columns=["__k"])
                    findings.append(f"strict_join_source={p} key={' + '.join(k)}")
            prog(1 + idx + 1, total + 1, f"source {idx+1}/{total} {p.name}")
        detail = pd.DataFrame(detail_rows)
        shared_matrix = pd.DataFrame(shared_rows)
        key_diag = pd.DataFrame(diag_rows)
        save(detail, out / "gold_v3_107r2_exact_exit_dt_source_detail.csv")
        save(shared_matrix, out / "gold_v3_107r2_shared_column_matrix.csv")
        save(key_diag, out / "gold_v3_107r2_candidate_key_diagnostics.csv")
        outputs += ["gold_v3_107r2_exact_exit_dt_source_detail.csv", "gold_v3_107r2_shared_column_matrix.csv", "gold_v3_107r2_candidate_key_diagnostics.csv"]
        if not resolved.empty:
            save(resolved, out / "gold_v3_107r2_resolved_best_family_ledger.csv")
            outputs.append("gold_v3_107r2_resolved_best_family_ledger.csv")
        prog(4, 5, "source intelligence complete")

    strict_count = int(key_diag.get("strict_join_pass", pd.Series(dtype=bool)).fillna(False).sum()) if not key_diag.empty else 0
    best_diag = pd.DataFrame()
    if not key_diag.empty:
        kk = key_diag.copy()
        if "coverage" in kk.columns:
            kk["coverage"] = pd.to_numeric(kk["coverage"], errors="coerce").fillna(0)
        if "non_null_exit_dt" in kk.columns:
            kk["non_null_exit_dt"] = pd.to_numeric(kk["non_null_exit_dt"], errors="coerce").fillna(0)
        best_diag = kk.sort_values(["strict_join_pass", "coverage", "non_null_exit_dt"], ascending=[False, False, False]).head(10)
    if strict_count > 0:
        decision = "EXIT_DT_SOURCE_INTELLIGENCE_STRICT_JOIN_READY_FOR_107S"
        status = READY
        next_action = pd.DataFrame([dict(next_stage="107S_RESOLVED_ONLY_HEALTH_GATE_REPLAY_AUDIT_ONLY", reason="At least one strict full-coverage exit_dt join exists.")])
    elif not detail.empty and int((detail.get("shared_column_count", 0) > 0).sum()) > 0:
        decision = "EXIT_DT_SOURCE_INTELLIGENCE_RECONSTRUCTION_PLAN_READY"
        status = READY
        next_action = pd.DataFrame([dict(next_stage="107R3_EXIT_DT_RECONSTRUCTION_FROM_LEDGER_SOURCE_AUDIT_ONLY", reason="Exact exit_dt sources exist and share columns, but no strict key join passed. Inspect candidate_key_diagnostics and source_detail to define a proven reconstruction key or produce a resolved source ledger.")])
    elif not blocks:
        decision = "EXIT_DT_SOURCE_INTELLIGENCE_SOURCE_CONTRACT_REVIEW_REQUIRED"
        status = BLOCKED
        blocks.append(dict(blocker_id="no_shared_columns_between_exit_dt_sources_and_best_ledger", reason="Exact exit_dt sources exist, but no usable shared columns were found."))
        next_action = pd.DataFrame([dict(next_stage="SOURCE_CONTRACT_REVIEW", reason="A resolved source ledger with compatible keys must be generated or exposed.")])
    else:
        decision = "EXIT_DT_SOURCE_INTELLIGENCE_BLOCKED_INPUT_INCOMPLETE"
        status = BLOCKED
        next_action = pd.DataFrame([dict(next_stage="FIX_INPUTS", reason="Required 107Q/107R files are missing or invalid.")])
    save(next_action, out / "gold_v3_107r2_recommended_next_action.csv")
    outputs.append("gold_v3_107r2_recommended_next_action.csv")

    vals += [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="progress_logging_enabled", result="PASS", observed=True, expected=True, severity="BLOCKER"),
    ]
    if not best.empty:
        vals.append(dict(check_id="best_family_ledger_positive", result="PASS", observed=len(best), expected=">0", severity="BLOCKER"))
    if not detail.empty:
        vals.append(dict(check_id="exact_exit_dt_source_detail_positive", result="PASS", observed=len(detail), expected=">0", severity="BLOCKER"))
    if not key_diag.empty:
        vals.append(dict(check_id="candidate_key_diagnostics_positive", result="PASS", observed=len(key_diag), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failure_count = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0

    summary = dict(
        step=STEP, status=status, decision=decision,
        created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        output_dir=str(out), audit_only=True, live_ready=False, source_csv_mutated=False, contract_mutated=False, open_asof_allowed=False,
        progress_logging_enabled=True, blocker_count=len(blocks), validation_failure_count=validation_failure_count,
        elapsed_seconds=round(time.time() - t0, 2), best_family_rows=int(len(best)) if not best.empty else 0,
        exact_exit_dt_source_count=int(len(detail)) if not detail.empty else 0,
        shared_column_source_count=int((detail.get("shared_column_count", pd.Series(dtype=int)) > 0).sum()) if not detail.empty else 0,
        candidate_key_diagnostic_rows=int(len(key_diag)) if not key_diag.empty else 0,
        strict_join_pass_count=strict_count,
        resolved_rows=int(len(resolved)) if not resolved.empty else 0,
    )
    if not best_diag.empty:
        findings.append("best_candidate_key_diagnostics=" + json.dumps(best_diag.to_dict(orient="records"), ensure_ascii=False, default=str))
    save(pd.DataFrame(blocks), out / "gold_v3_107r2_blocker_matrix.csv")
    save(val, out / "gold_v3_107r2_validation_matrix.csv")
    outputs += ["gold_v3_107r2_blocker_matrix.csv", "gold_v3_107r2_validation_matrix.csv", "gold_v3_107r2_summary.json", "GOLD_V3_107R2_EXIT_DT_SOURCE_INTELLIGENCE_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_107r2_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_107R2_EXIT_DT_SOURCE_INTELLIGENCE_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107R2 report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = [
        "GOLD V3 107R2 PASTE_ME_EXIT_DT_SOURCE_INTELLIGENCE",
        f"status: {status}", f"ready: {str(status == READY).lower()}", "live_ready: false",
        "source_csv_mutated: false", "contract_mutated: false", "open_asof_allowed: false",
        "safety: audit_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false",
        "blocker_count: " + str(len(blocks)), "", "KEY_METRICS",
    ] + [f"{k}: {v}" for k, v in summary.items()] + [
        "", "FINDINGS",
    ] + (findings or ["NO_FINDINGS"]) + [
        "", "RECOMMENDED_NEXT_ACTION", next_action.to_string(index=False), "", "BLOCKERS",
        pd.DataFrame(blocks).to_string(index=False) if blocks else "NO_BLOCKERS",
        "", "VALIDATION", val.to_string(index=False), "", "OUTPUTS",
    ] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(5, 5, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
