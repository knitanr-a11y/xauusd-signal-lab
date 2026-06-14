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

STEP = "GOLD_V3_107R_RESOLVED_EXIT_DT_REHYDRATION_AUDIT_ONLY"
READY = "GOLD_V3_107R_RESOLVED_EXIT_DT_REHYDRATION_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_107R_RESOLVED_EXIT_DT_REHYDRATION_BLOCKED_AUDIT_ONLY"

JOIN_KEYS = [
    ["global_candidate_key"],
    ["entry_dt", "global_candidate_key"],
    ["entry_dt", "side", "candidate_key", "profile_id"],
    ["entry_dt", "side", "family", "condition", "profile_id"],
    ["entry_dt", "side", "result_usd"],
]
EXIT_ALIASES = ["exit_time", "close_dt", "closed_dt", "resolved_dt", "tp_dt", "sl_dt", "outcome_dt"]


def log(s: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}", flush=True)


def prog(i: int, n: int, s: str) -> None:
    p = 100.0 * i / max(1, n)
    log(f"progress {p:5.1f}% complete / {100.0-p:5.1f}% remaining | step {i}/{n} | {s}")


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


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


def build_key(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    x = norm_frame(df, cols)
    return x[cols].astype(str).agg("||".join, axis=1)


def scan_headers(root: Path, out_dir: Path) -> pd.DataFrame:
    rows = []
    paths = sorted(root.rglob("*.csv"))
    for i, p in enumerate(paths, 1):
        if out_dir in p.parents:
            continue
        try:
            hdr = pd.read_csv(p, nrows=0, encoding="utf-8-sig")
            cols = list(hdr.columns)
            exact = "exit_dt" in cols
            aliases = [c for c in cols if c in EXIT_ALIASES]
            rows.append(dict(path=str(p), file=p.name, parent=str(p.parent), column_count=len(cols), has_exit_dt=exact, exit_aliases="|".join(aliases), has_entry_dt="entry_dt" in cols, has_result_usd="result_usd" in cols, has_global_candidate_key="global_candidate_key" in cols, has_candidate_key="candidate_key" in cols, columns_preview="|".join(cols[:40])))
        except Exception as e:
            rows.append(dict(path=str(p), file=p.name, parent=str(p.parent), scan_error=str(e), has_exit_dt=False))
        if i % 50 == 0:
            prog(i, max(1, len(paths)), "header scan")
    return pd.DataFrame(rows)


def read_candidate_subset(path: Path, usecols: list[str]) -> pd.DataFrame:
    cols = list(dict.fromkeys(usecols))
    try:
        return pd.read_csv(path, usecols=lambda c: c in cols, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def attempt_join(best: pd.DataFrame, source_path: Path, source_cols: list[str]) -> tuple[list[dict], pd.DataFrame]:
    attempts = []
    best_n = len(best)
    best_joined = pd.DataFrame()
    for keys in JOIN_KEYS:
        if not all(k in best.columns and k in source_cols for k in keys):
            continue
        usecols = keys + ["exit_dt"]
        src = read_candidate_subset(source_path, usecols)
        if "exit_dt" not in src.columns:
            continue
        if not all(k in src.columns for k in keys):
            continue
        b = best.copy()
        s = src[keys + ["exit_dt"]].copy()
        b["__join_key"] = build_key(b, keys)
        s["__join_key"] = build_key(s, keys)
        dup_src = int(s["__join_key"].duplicated().sum())
        s = s.drop_duplicates("__join_key", keep="first")
        merged = b.merge(s[["__join_key", "exit_dt"]], on="__join_key", how="left", suffixes=("", "_src"))
        non_null = int(merged["exit_dt"].notna().sum())
        coverage = non_null / max(1, best_n)
        exit_dt = pd.to_datetime(merged["exit_dt"], errors="coerce")
        entry_dt = pd.to_datetime(merged["entry_dt"], errors="coerce") if "entry_dt" in merged.columns else pd.Series(pd.NaT, index=merged.index)
        exit_ge_entry_count = int((exit_dt.notna() & entry_dt.notna() & (exit_dt >= entry_dt)).sum())
        strict_pass = bool(non_null == best_n and exit_ge_entry_count == best_n and dup_src == 0)
        attempts.append(dict(source_path=str(source_path), join_keys=" + ".join(keys), selected_rows=best_n, non_null_exit_dt=non_null, coverage=coverage, source_duplicate_keys=dup_src, exit_ge_entry_count=exit_ge_entry_count, strict_join_pass=strict_pass))
        if strict_pass and best_joined.empty:
            merged = merged.drop(columns=["__join_key"])
            merged["exit_dt"] = exit_dt.dt.strftime("%Y-%m-%d %H:%M:%S")
            best_joined = merged.copy()
    return attempts, best_joined


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    src = root / "107qc"
    out = root / "107rc"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")
    prog(0, 5, "start")

    blocks, outputs, vals, findings = [], [], [], []
    ledger_path = src / "gold_v3_107q_best_family_trade_ledger.csv"
    summary_path = src / "gold_v3_107q_summary.json"
    if not ledger_path.exists():
        blocks.append(dict(blocker_id="missing_107q_best_family_trade_ledger", path=str(ledger_path)))
    if not summary_path.exists():
        blocks.append(dict(blocker_id="missing_107q_summary", path=str(summary_path)))

    best = pd.DataFrame()
    source_catalog = pd.DataFrame()
    attempts_df = pd.DataFrame()
    resolved = pd.DataFrame()

    if not blocks:
        best = pd.read_csv(ledger_path, encoding="utf-8-sig", low_memory=False)
        if "entry_dt" not in best.columns:
            blocks.append(dict(blocker_id="best_family_ledger_missing_entry_dt"))
        prog(1, 5, f"loaded best_family_ledger rows={len(best)}")

    if not blocks:
        source_catalog = scan_headers(root, out)
        save(source_catalog, out / "gold_v3_107r_exit_dt_source_catalog.csv")
        outputs.append("gold_v3_107r_exit_dt_source_catalog.csv")
        exact = source_catalog[source_catalog.get("has_exit_dt", False) == True].copy()
        if exact.empty:
            blocks.append(dict(blocker_id="exit_dt_source_not_found", reason="No CSV under FX_OUTPUTS/gold_v3 has an exact exit_dt column."))
        prog(2, 5, f"source catalog complete exact_exit_dt_sources={0 if exact.empty else len(exact)}")

    if not blocks:
        rows = []
        for i, r in exact.iterrows():
            p = Path(str(r["path"]))
            try:
                hdr = pd.read_csv(p, nrows=0, encoding="utf-8-sig")
                attempts, joined = attempt_join(best, p, list(hdr.columns))
                rows.extend(attempts)
                if not joined.empty and resolved.empty:
                    resolved = joined.copy()
                    findings.append(f"resolved_exit_dt_source={p}")
            except Exception as e:
                rows.append(dict(source_path=str(p), join_error=str(e), strict_join_pass=False))
            prog(2 + min(1, (i + 1) / max(1, len(exact))), 5, f"join attempts {i+1}/{len(exact)}")
        attempts_df = pd.DataFrame(rows)
        save(attempts_df, out / "gold_v3_107r_join_attempts.csv")
        outputs.append("gold_v3_107r_join_attempts.csv")
        if resolved.empty:
            blocks.append(dict(blocker_id="partial_or_ambiguous_exit_dt_join", reason="No exact exit_dt source joined 100% with non-null exit_dt and exit_dt >= entry_dt."))
        else:
            save(resolved, out / "gold_v3_107r_resolved_best_family_ledger.csv")
            outputs.append("gold_v3_107r_resolved_best_family_ledger.csv")
        prog(4, 5, "join attempts complete")

    pre_rows = []
    if not best.empty:
        pre_rows.append(dict(check_id="best_family_ledger_rows", result="PASS" if len(best) > 0 else "BLOCKED", observed=len(best), expected=">0", severity="BLOCKER"))
    if not source_catalog.empty:
        pre_rows.append(dict(check_id="exact_exit_dt_source_found", result="PASS" if bool(source_catalog.get("has_exit_dt", pd.Series(dtype=bool)).any()) else "BLOCKED", observed=int(source_catalog.get("has_exit_dt", pd.Series(dtype=bool)).sum()) if "has_exit_dt" in source_catalog else 0, expected=">0", severity="BLOCKER"))
    if not resolved.empty:
        pre_rows.append(dict(check_id="resolved_exit_dt_full_coverage", result="PASS", observed=f"{resolved['exit_dt'].notna().sum()}/{len(resolved)}", expected=f"{len(resolved)}/{len(resolved)}", severity="BLOCKER"))
        exit_dt = pd.to_datetime(resolved["exit_dt"], errors="coerce")
        entry_dt = pd.to_datetime(resolved["entry_dt"], errors="coerce")
        pre_rows.append(dict(check_id="exit_dt_ge_entry_dt", result="PASS" if bool(((exit_dt >= entry_dt) & exit_dt.notna() & entry_dt.notna()).all()) else "BLOCKED", observed=int(((exit_dt >= entry_dt) & exit_dt.notna() & entry_dt.notna()).sum()), expected=len(resolved), severity="BLOCKER"))
    pre = pd.DataFrame(pre_rows)
    save(pre, out / "gold_v3_107r_exit_dt_precondition_matrix.csv")
    outputs.append("gold_v3_107r_exit_dt_precondition_matrix.csv")

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
    if not resolved.empty:
        vals.append(dict(check_id="resolved_best_family_ledger_positive", result="PASS", observed=len(resolved), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failed = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0

    if validation_failed:
        status = BLOCKED
        decision = "RESOLVED_EXIT_DT_REHYDRATION_BLOCKED_INPUT_INCOMPLETE"
    elif resolved.empty:
        status = BLOCKED
        if any(b.get("blocker_id") == "exit_dt_source_not_found" for b in blocks):
            decision = "RESOLVED_EXIT_DT_REHYDRATION_BLOCKED_EXIT_DT_SOURCE_NOT_FOUND"
        else:
            decision = "RESOLVED_EXIT_DT_REHYDRATION_BLOCKED_PARTIAL_OR_AMBIGUOUS_JOIN"
    else:
        status = READY
        decision = "RESOLVED_EXIT_DT_REHYDRATION_READY_FOR_107S_HEALTH_GATE_REPLAY"

    summary = dict(
        step=STEP,
        status=status,
        decision=decision,
        created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        output_dir=str(out),
        audit_only=True,
        live_ready=False,
        source_csv_mutated=False,
        contract_mutated=False,
        open_asof_allowed=False,
        progress_logging_enabled=True,
        blocker_count=len(blocks),
        validation_failure_count=validation_failed,
        elapsed_seconds=round(time.time() - t0, 2),
        best_family_rows=int(len(best)) if not best.empty else 0,
        source_catalog_rows=int(len(source_catalog)) if not source_catalog.empty else 0,
        exact_exit_dt_source_count=int(source_catalog["has_exit_dt"].sum()) if not source_catalog.empty and "has_exit_dt" in source_catalog else 0,
        join_attempt_rows=int(len(attempts_df)) if not attempts_df.empty else 0,
        resolved_rows=int(len(resolved)) if not resolved.empty else 0,
        resolved_exit_dt_non_null=int(resolved["exit_dt"].notna().sum()) if not resolved.empty and "exit_dt" in resolved.columns else 0,
    )

    save(pd.DataFrame(blocks), out / "gold_v3_107r_blocker_matrix.csv")
    save(val, out / "gold_v3_107r_validation_matrix.csv")
    outputs += ["gold_v3_107r_blocker_matrix.csv", "gold_v3_107r_validation_matrix.csv", "gold_v3_107r_summary.json", "GOLD_V3_107R_RESOLVED_EXIT_DT_REHYDRATION_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_107r_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_107R_RESOLVED_EXIT_DT_REHYDRATION_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107R report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    lines = [
        "GOLD V3 107R PASTE_ME_RESOLVED_EXIT_DT_REHYDRATION",
        f"status: {status}",
        f"ready: {str(status == READY).lower()}",
        "live_ready: false",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "open_asof_allowed: false",
        "safety: audit_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false",
        "blocker_count: " + str(len(blocks)),
        "",
        "KEY_METRICS",
    ] + [f"{k}: {v}" for k, v in summary.items()] + [
        "",
        "FINDINGS",
    ] + (findings or ["NO_FINDINGS"]) + [
        "",
        "BLOCKERS",
        pd.DataFrame(blocks).to_string(index=False) if blocks else "NO_BLOCKERS",
        "",
        "EXIT_DT_PRECONDITION",
        pre.to_string(index=False) if not pre.empty else "NO_PRECONDITION_ROWS",
        "",
        "VALIDATION",
        val.to_string(index=False),
        "",
        "OUTPUTS",
    ] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(5, 5, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
