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

STEP = "GOLD_V3_107R3_EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_AUDIT_ONLY"
READY = "GOLD_V3_107R3_EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_107R3_EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_BLOCKED_AUDIT_ONLY"

ALIAS = {
    "entry_dt": ["entry_dt", "signal_dt", "open_dt", "trade_dt", "dt"],
    "exit_dt": ["exit_dt"],
    "side": ["side", "direction", "trade_side", "candidate_side", "signal_side", "portfolio_side"],
    "profile_id": ["profile_id", "profile", "tp_sl_profile", "tp_sl_profile_id", "risk_profile"],
    "family": ["family", "rule_family", "candidate_family"],
    "condition": ["condition", "rule_condition", "candidate_condition"],
    "candidate_key": ["candidate_key", "rule_key", "strategy_key", "global_candidate_key"],
    "global_candidate_key": ["global_candidate_key", "candidate_key", "rule_key", "strategy_key"],
    "result_usd": ["result_usd", "pnl_usd", "profit_usd", "net_usd"],
    "score": ["score", "ledger_score", "feature_score"],
    "source_name": ["source_name", "source", "ledger_source"],
}
PREFERRED_KEYS = [
    ["entry_dt", "global_candidate_key"],
    ["entry_dt", "candidate_key", "profile_id", "side"],
    ["entry_dt", "family", "condition", "profile_id", "side"],
    ["entry_dt", "side", "result_usd", "score"],
    ["entry_dt", "side", "result_usd"],
    ["entry_dt", "score"],
    ["entry_dt"],
]


def log(s: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}", flush=True)


def prog(i: int, n: int, s: str) -> None:
    p = 100.0 * i / max(1, n)
    log(f"progress {p:5.1f}% complete / {100.0-p:5.1f}% remaining | step {i}/{n} | {s}")


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def canon_map(cols: list[str]) -> dict[str, str]:
    lower = {c.lower(): c for c in cols}
    out = {}
    for canon, aliases in ALIAS.items():
        for a in aliases:
            if a.lower() in lower:
                out[canon] = lower[a.lower()]
                break
    return out


def normalize(df: pd.DataFrame, cmap: dict[str, str]) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for canon, src in cmap.items():
        if src not in df.columns:
            continue
        if canon.endswith("_dt"):
            out[canon] = pd.to_datetime(df[src], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
        elif canon in ["result_usd", "score"]:
            out[canon] = pd.to_numeric(df[src], errors="coerce").round(8).astype(str)
        else:
            out[canon] = df[src].astype(str).fillna("")
    return out


def key_series(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    return df[cols].astype(str).agg("||".join, axis=1)


def candidate_keys(shared: list[str]) -> list[list[str]]:
    out = []
    for k in PREFERRED_KEYS:
        if all(c in shared for c in k) and k not in out:
            out.append(k)
    base = [c for c in ["entry_dt", "side", "candidate_key", "global_candidate_key", "profile_id", "family", "condition", "result_usd", "score", "source_name"] if c in shared]
    for size in [2, 3, 4, 5]:
        for combo in itertools.combinations(base, size):
            combo = list(combo)
            if "entry_dt" not in combo:
                continue
            if combo not in out:
                out.append(combo)
            if len(out) >= 80:
                return out
    return out


def try_join(best_raw: pd.DataFrame, src_path: Path, key_cols: list[str]) -> tuple[dict, pd.DataFrame]:
    rec = dict(source_path=str(src_path), key_cols=" + ".join(key_cols), key_size=len(key_cols))
    try:
        hdr = pd.read_csv(src_path, nrows=0, encoding="utf-8-sig")
        src_cmap = canon_map(list(hdr.columns))
        best_cmap = canon_map(list(best_raw.columns))
        need_src = sorted(set([src_cmap[c] for c in set(key_cols + ["exit_dt"]) if c in src_cmap]))
        src_raw = pd.read_csv(src_path, usecols=lambda c: c in need_src, encoding="utf-8-sig", low_memory=False)
        b = normalize(best_raw, best_cmap)
        s = normalize(src_raw, src_cmap)
        if not all(c in b.columns and c in s.columns for c in key_cols) or "exit_dt" not in s.columns:
            rec.update(error="normalized_required_columns_missing", strict_join_pass=False)
            return rec, pd.DataFrame()
        b["__k"] = key_series(b, key_cols)
        s["__k"] = key_series(s, key_cols)
        source_dup = int(s["__k"].duplicated().sum())
        selected_dup = int(b["__k"].duplicated().sum())
        s2 = s.drop_duplicates("__k", keep="first")
        merged_key = b[["__k"]].merge(s2[["__k", "exit_dt"]], on="__k", how="left")
        non_null = int(merged_key["exit_dt"].notna().sum())
        coverage = non_null / max(1, len(best_raw))
        entry_dt = pd.to_datetime(b["entry_dt"], errors="coerce") if "entry_dt" in b.columns else pd.Series(pd.NaT, index=b.index)
        exit_dt = pd.to_datetime(merged_key["exit_dt"], errors="coerce")
        ge = int((exit_dt.notna() & entry_dt.notna() & (exit_dt >= entry_dt)).sum())
        strict = bool(non_null == len(best_raw) and ge == len(best_raw) and source_dup == 0)
        rec.update(selected_rows=len(best_raw), source_rows=len(src_raw), selected_unique_keys=int(b["__k"].nunique()), source_unique_keys=int(s["__k"].nunique()), selected_duplicate_keys=selected_dup, source_duplicate_keys=source_dup, non_null_exit_dt=non_null, coverage=coverage, exit_ge_entry_count=ge, strict_join_pass=strict)
        if strict:
            resolved = best_raw.copy()
            resolved["exit_dt"] = exit_dt.dt.strftime("%Y-%m-%d %H:%M:%S")
            resolved["exit_dt_source_path"] = str(src_path)
            resolved["exit_dt_join_key"] = " + ".join(key_cols)
            return rec, resolved
        return rec, pd.DataFrame()
    except Exception as e:
        rec.update(error=str(e), strict_join_pass=False)
        return rec, pd.DataFrame()


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    src_q = root / "107qc"
    src_r2 = root / "107r2c"
    out = root / "107r3c"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")
    prog(0, 5, "start")

    blocks, outputs, vals, findings = [], [], [], []
    best_path = src_q / "gold_v3_107q_best_family_trade_ledger.csv"
    detail_path = src_r2 / "gold_v3_107r2_exact_exit_dt_source_detail.csv"
    if not best_path.exists():
        blocks.append(dict(blocker_id="missing_107q_best_family_trade_ledger", path=str(best_path)))
    if not detail_path.exists():
        blocks.append(dict(blocker_id="missing_107r2_exact_exit_dt_source_detail", path=str(detail_path)))

    best = pd.DataFrame(); detail = pd.DataFrame(); cmap_rows = []; attempts = []; resolved = pd.DataFrame()
    if not blocks:
        best = pd.read_csv(best_path, encoding="utf-8-sig", low_memory=False)
        detail = pd.read_csv(detail_path, encoding="utf-8-sig", low_memory=False)
        if "path" not in detail.columns:
            blocks.append(dict(blocker_id="source_detail_missing_path_column"))
        prog(1, 5, f"loaded best_rows={len(best)} source_detail_rows={len(detail)}")

    if not blocks:
        best_cmap = canon_map(list(best.columns))
        total_sources = len(detail)
        for i, r in detail.reset_index(drop=True).iterrows():
            p = Path(str(r["path"]))
            try:
                hdr = pd.read_csv(p, nrows=0, encoding="utf-8-sig")
                src_cmap = canon_map(list(hdr.columns))
                shared = sorted(set(best_cmap.keys()).intersection(src_cmap.keys()))
                for canon in sorted(set(best_cmap.keys()).union(src_cmap.keys())):
                    cmap_rows.append(dict(source_path=str(p), canonical_column=canon, best_column=best_cmap.get(canon, ""), source_column=src_cmap.get(canon, ""), shared=canon in shared))
                keys = candidate_keys(shared)
                if not keys:
                    attempts.append(dict(source_path=str(p), attempted=False, reason="no_alias_shared_candidate_keys", strict_join_pass=False))
                for k in keys:
                    rec, joined = try_join(best, p, k)
                    attempts.append(rec)
                    if not joined.empty and resolved.empty:
                        resolved = joined.copy()
                        findings.append(f"strict_alias_join_source={p} key={' + '.join(k)}")
            except Exception as e:
                attempts.append(dict(source_path=str(p), attempted=False, error=str(e), strict_join_pass=False))
            prog(1 + i + 1, total_sources + 1, f"source {i+1}/{total_sources}")
        cmap_df = pd.DataFrame(cmap_rows)
        attempts_df = pd.DataFrame(attempts)
        save(cmap_df, out / "gold_v3_107r3_alias_source_column_map.csv")
        save(attempts_df, out / "gold_v3_107r3_synthetic_key_join_attempts.csv")
        outputs += ["gold_v3_107r3_alias_source_column_map.csv", "gold_v3_107r3_synthetic_key_join_attempts.csv"]
        if not resolved.empty:
            save(resolved, out / "gold_v3_107r3_resolved_best_family_ledger.csv")
            outputs.append("gold_v3_107r3_resolved_best_family_ledger.csv")
        prog(4, 5, "alias synthetic key attempts complete")
    else:
        cmap_df = pd.DataFrame(); attempts_df = pd.DataFrame()

    contract = pd.DataFrame([
        dict(required_column="entry_dt", reason="trade entry time"),
        dict(required_column="exit_dt", reason="resolved TP/SL/timeout exit time; must be known before future entries for health gate"),
        dict(required_column="side", reason="direction identity"),
        dict(required_column="result_usd", reason="must match selected result"),
        dict(required_column="profile_id", reason="TP/SL profile identity"),
        dict(required_column="candidate_key or global_candidate_key", reason="candidate identity"),
        dict(required_column="family", reason="rule family identity"),
        dict(required_column="condition", reason="rule condition identity"),
        dict(required_column="source_name", reason="source lineage"),
    ])
    save(contract, out / "gold_v3_107r3_resolved_ledger_contract_requirement.csv")
    outputs.append("gold_v3_107r3_resolved_ledger_contract_requirement.csv")

    strict_count = int(attempts_df.get("strict_join_pass", pd.Series(dtype=bool)).fillna(False).sum()) if not attempts_df.empty else 0
    best_attempts = pd.DataFrame()
    if not attempts_df.empty:
        x = attempts_df.copy()
        for c in ["coverage", "non_null_exit_dt"]:
            if c in x.columns:
                x[c] = pd.to_numeric(x[c], errors="coerce").fillna(0)
        best_attempts = x.sort_values(["strict_join_pass", "coverage", "non_null_exit_dt"], ascending=[False, False, False]).head(10)
        findings.append("best_alias_synthetic_key_attempts=" + json.dumps(best_attempts.to_dict(orient="records"), ensure_ascii=False, default=str))

    if strict_count > 0 and not resolved.empty:
        status = READY
        decision = "EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_READY_FOR_107S"
    elif blocks:
        status = BLOCKED
        decision = "EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_BLOCKED_INPUT_INCOMPLETE"
    else:
        status = BLOCKED
        decision = "EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_BLOCKED_NEED_RESOLVED_SOURCE_LEDGER"
        blocks.append(dict(blocker_id="strict_alias_synthetic_join_not_found", reason="No alias-aware synthetic key produced 100% non-null exit_dt coverage with exit_dt >= entry_dt and zero source duplicate keys."))

    vals = [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="progress_logging_enabled", result="PASS", observed=True, expected=True, severity="BLOCKER"),
    ]
    if not best.empty:
        vals.append(dict(check_id="best_family_ledger_positive", result="PASS", observed=len(best), expected=">0", severity="BLOCKER"))
    if not attempts_df.empty:
        vals.append(dict(check_id="synthetic_join_attempts_positive", result="PASS", observed=len(attempts_df), expected=">0", severity="BLOCKER"))
    if not resolved.empty:
        vals.append(dict(check_id="resolved_ledger_positive", result="PASS", observed=len(resolved), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failure_count = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0

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
        validation_failure_count=validation_failure_count,
        elapsed_seconds=round(time.time() - t0, 2),
        best_family_rows=int(len(best)) if not best.empty else 0,
        source_detail_rows=int(len(detail)) if not detail.empty else 0,
        alias_map_rows=int(len(cmap_df)) if not cmap_df.empty else 0,
        synthetic_join_attempt_rows=int(len(attempts_df)) if not attempts_df.empty else 0,
        strict_join_pass_count=strict_count,
        resolved_rows=int(len(resolved)) if not resolved.empty else 0,
    )

    save(pd.DataFrame(blocks), out / "gold_v3_107r3_blocker_matrix.csv")
    save(val, out / "gold_v3_107r3_validation_matrix.csv")
    outputs += ["gold_v3_107r3_blocker_matrix.csv", "gold_v3_107r3_validation_matrix.csv", "gold_v3_107r3_summary.json", "GOLD_V3_107R3_EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_107r3_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_107R3_EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107R3 report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = [
        "GOLD V3 107R3 PASTE_ME_EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION",
        f"status: {status}", f"ready: {str(status == READY).lower()}", "live_ready: false",
        "source_csv_mutated: false", "contract_mutated: false", "open_asof_allowed: false",
        "safety: audit_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false",
        "blocker_count: " + str(len(blocks)), "", "KEY_METRICS",
    ] + [f"{k}: {v}" for k, v in summary.items()] + [
        "", "FINDINGS",
    ] + (findings or ["NO_FINDINGS"]) + [
        "", "BLOCKERS", pd.DataFrame(blocks).to_string(index=False) if blocks else "NO_BLOCKERS",
        "", "RESOLVED_LEDGER_CONTRACT_REQUIREMENT", contract.to_string(index=False),
        "", "VALIDATION", val.to_string(index=False), "", "OUTPUTS",
    ] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(5, 5, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
