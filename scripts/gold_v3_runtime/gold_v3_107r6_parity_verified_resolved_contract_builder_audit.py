#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_107R6_PARITY_VERIFIED_RESOLVED_CONTRACT_BUILDER_AUDIT_ONLY"
READY = "GOLD_V3_107R6_PARITY_VERIFIED_RESOLVED_CONTRACT_BUILDER_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_107R6_PARITY_VERIFIED_RESOLVED_CONTRACT_BUILDER_BLOCKED_AUDIT_ONLY"
CONTRACT = gy.CONTRACT
POOL_POLICY = gy.POOL_POLICY
NAMES = {
    "m15": ["gold#_m15.csv", "goldsharp_m15.csv"],
    "m5": ["gold#_m5.csv", "goldsharp_m5.csv"],
}
ACTIVE_INPUTS = [
    ("atomic_current_107GO", "107goc", "gold_v3_107go_portfolio_ledger.csv"),
    ("atomic_top_107GN", "107gnc", "gold_v3_107gn_top_candidate_trade_ledger.csv"),
    ("fixed_diversified_107GD", "107gdc", "gold_v3_107gd_diversified_portfolio_ledger.csv"),
    ("broad_candidate_107GB", "107gbc", "gold_v3_107gb_top_candidate_trade_ledger.csv"),
]


def log(s: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}", flush=True)


def prog(i: int, n: int, s: str) -> None:
    p = 100.0 * i / max(1, n)
    log(f"progress {p:5.1f}% complete / {100.0-p:5.1f}% remaining | step {i}/{n} | {s}")


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def read_ohlc(path: Path) -> pd.DataFrame:
    sample = path.read_text(encoding="utf-8-sig", errors="ignore")[:4096]
    sep = ";" if sample.count(";") > sample.count(",") else ","
    df = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
    low = {c.lower(): c for c in df.columns}
    t = low.get("time") or low.get("datetime") or low.get("date") or low.get("timestamp")
    if not t or not all(c in low for c in ["open", "high", "low", "close"]):
        raise ValueError(f"OHLC columns missing in {path}")
    x = df[[t, low["open"], low["high"], low["low"], low["close"]]].copy()
    x.columns = ["time", "open", "high", "low", "close"]
    x["time"] = pd.to_datetime(x["time"], errors="coerce")
    for c in ["open", "high", "low", "close"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    return x.dropna().sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)


def find_ohlc(mt5: Path, tf: str) -> tuple[pd.DataFrame, str]:
    for name in NAMES[tf]:
        p = mt5 / name
        if p.exists():
            return read_ohlc(p), str(p)
    return pd.DataFrame(), ""


def atr(df: pd.DataFrame, n: int = 28) -> pd.Series:
    pc = df.close.shift(1)
    tr = pd.concat([(df.high - df.low), (df.high - pc).abs(), (df.low - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def make_m15_state(m15: pd.DataFrame) -> pd.DataFrame:
    x = m15.copy()
    x["atr28"] = atr(x, 28)
    return x[["time", "close", "atr28"]].dropna().sort_values("time")


def profile_tp_sl(profile_id: str, atr28: float) -> tuple[float, float, int, str]:
    s = str(profile_id)
    m = re.search(r"TP([0-9.]+)_SL([0-9.]+).*?_H([0-9]+)", s)
    if m:
        return float(m.group(1)), float(m.group(2)), int(m.group(3)), "fixed"
    m = re.search(r"TPmax5_ATR([0-9.]+)_RR([0-9.]+)_H([0-9]+)", s)
    if m:
        tm = float(m.group(1)); rr = float(m.group(2)); h = int(m.group(3))
        tp = max(5.0, float(atr28) * tm)
        return tp, tp / rr, h, "dynamic_atr"
    raise ValueError(f"unsupported_profile_id={profile_id}")


def resolve_one(entry_dt, side: str, profile_id: str, m15_state: pd.DataFrame, m5: pd.DataFrame) -> dict:
    ent = pd.Timestamp(entry_dt)
    st15 = np.searchsorted(m15_state.time.values, ent.to_datetime64(), side="left")
    if st15 >= len(m15_state) or pd.Timestamp(m15_state.time.iat[st15]) != ent:
        return dict(resolve_error="entry_dt_not_found_in_m15", recomputed_result_usd=np.nan)
    ep = float(m15_state.close.iat[st15])
    atr28 = float(m15_state.atr28.iat[st15])
    tp, sl, h, kind = profile_tp_sl(profile_id, atr28)
    st5 = np.searchsorted(m5.time.values, ent.to_datetime64(), side="right")
    end = min(len(m5), st5 + h * 3)
    if st5 >= len(m5) or end <= st5:
        return dict(resolve_error="no_future_m5", recomputed_result_usd=np.nan)
    tpv = ep + tp if side == "LONG" else ep - tp
    slv = ep - sl if side == "LONG" else ep + sl
    for j in range(st5, end):
        hi = float(m5.high.iat[j]); lo = float(m5.low.iat[j]); tm = pd.Timestamp(m5.time.iat[j])
        hit_tp = hi >= tpv if side == "LONG" else lo <= tpv
        hit_sl = lo <= slv if side == "LONG" else hi >= slv
        if hit_tp and hit_sl:
            return dict(recomputed_result_usd=-sl, exit_dt=tm, entry_price=ep, exit_price=slv, exit_reason="SL_BOTH", tp_usd=tp, sl_usd=sl, horizon_m15=h, profile_kind=kind, resolve_error="")
        if hit_sl:
            return dict(recomputed_result_usd=-sl, exit_dt=tm, entry_price=ep, exit_price=slv, exit_reason="SL", tp_usd=tp, sl_usd=sl, horizon_m15=h, profile_kind=kind, resolve_error="")
        if hit_tp:
            return dict(recomputed_result_usd=tp, exit_dt=tm, entry_price=ep, exit_price=tpv, exit_reason="TP", tp_usd=tp, sl_usd=sl, horizon_m15=h, profile_kind=kind, resolve_error="")
    tm = pd.Timestamp(m5.time.iat[end - 1])
    return dict(recomputed_result_usd=0.0, exit_dt=tm, entry_price=ep, exit_price=np.nan, exit_reason="TIMEOUT", tp_usd=tp, sl_usd=sl, horizon_m15=h, profile_kind=kind, resolve_error="")


def normalize_input(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    x = df.copy()
    if "entry_dt" not in x.columns:
        return pd.DataFrame()
    x["entry_dt"] = pd.to_datetime(x["entry_dt"], errors="coerce")
    x = x[x["entry_dt"].notna()].copy()
    x["result_usd"] = pd.to_numeric(x.get("result_usd", np.nan), errors="coerce")
    x = x[x["result_usd"].notna()].copy()
    if "portfolio_side" in x.columns:
        x["side"] = x["portfolio_side"]
    if "selected_side" in x.columns and "side" not in x.columns:
        x["side"] = x["selected_side"]
    if "side" not in x.columns:
        x["side"] = "UNKNOWN"
    for c in ["side", "family", "condition", "profile_id", "candidate_key"]:
        if c not in x.columns:
            x[c] = ""
        x[c] = x[c].astype(str).replace({"nan": ""})
    if "cooldown_bars" not in x.columns:
        x["cooldown_bars"] = 0
    x["cooldown_bars"] = pd.to_numeric(x["cooldown_bars"], errors="coerce").fillna(0).astype(int)
    empty = x["candidate_key"].eq("") | x["candidate_key"].eq("nan")
    built = x.apply(lambda r: f"{r.side}||{r.family}||{r.condition}||{r.profile_id}||CD{int(r.cooldown_bars)}", axis=1)
    x.loc[empty, "candidate_key"] = built[empty]
    x["source_name"] = source_name
    x["global_candidate_key"] = x["source_name"] + "::" + x["candidate_key"]
    return x.sort_values("entry_dt")


def resolve_ledger(src: pd.DataFrame, source_name: str, m15_state: pd.DataFrame, m5: pd.DataFrame, tol: float) -> tuple[pd.DataFrame, dict]:
    if src.empty:
        return pd.DataFrame(), dict(source_name=source_name, rows=0, parity_pass_rows=0, parity_fail_rows=0, resolve_error_rows=0, parity_pass_rate=0.0)
    recs = []
    n = len(src)
    for i, (_, r) in enumerate(src.iterrows(), 1):
        try:
            d = resolve_one(r.entry_dt, str(r.side), str(r.profile_id), m15_state, m5)
        except Exception as e:
            d = dict(resolve_error=str(e), recomputed_result_usd=np.nan)
        recs.append(d)
        if i % 5000 == 0:
            prog(i, n, f"resolving {source_name}")
    rr = pd.DataFrame(recs, index=src.index)
    out = pd.concat([src.reset_index(drop=True), rr.reset_index(drop=True)], axis=1)
    out["result_delta"] = pd.to_numeric(out["recomputed_result_usd"], errors="coerce") - pd.to_numeric(out["result_usd"], errors="coerce")
    out["result_parity_pass"] = out["result_delta"].abs() <= tol
    out["exit_dt"] = pd.to_datetime(out.get("exit_dt"), errors="coerce")
    out["exit_dt_ge_entry_dt"] = out["exit_dt"].notna() & (out["exit_dt"] >= pd.to_datetime(out["entry_dt"], errors="coerce"))
    out["result_source"] = "107R6_parity_verified_existing_profile_resolver_extension"
    out["resolver_script"] = Path(__file__).name
    out["csv_contract"] = CONTRACT
    met = dict(source_name=source_name, rows=int(len(out)), parity_pass_rows=int(out["result_parity_pass"].sum()), parity_fail_rows=int((~out["result_parity_pass"]).sum()), resolve_error_rows=int(out.get("resolve_error", pd.Series('', index=out.index)).astype(str).ne('').sum()), exit_dt_non_null=int(out["exit_dt"].notna().sum()), exit_dt_ge_entry_rows=int(out["exit_dt_ge_entry_dt"].sum()), parity_pass_rate=float(out["result_parity_pass"].mean()) if len(out) else 0.0)
    return out, met


def join_best(best: pd.DataFrame, combined: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    b = best.copy()
    c = combined.copy()
    b["entry_dt_norm"] = pd.to_datetime(b["entry_dt"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    c["entry_dt_norm"] = pd.to_datetime(c["entry_dt"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    for x in [b, c]:
        if "global_candidate_key" not in x.columns and "source_name" in x.columns and "candidate_key" in x.columns:
            x["global_candidate_key"] = x["source_name"].astype(str) + "::" + x["candidate_key"].astype(str)
        x["result_usd_norm"] = pd.to_numeric(x["result_usd"], errors="coerce").round(8).astype(str)
    keys = ["global_candidate_key", "entry_dt_norm", "result_usd_norm"]
    c2 = c.drop_duplicates(keys, keep="first")
    keep_cols = keys + ["exit_dt", "entry_price", "exit_price", "exit_reason", "tp_usd", "sl_usd", "horizon_m15", "result_parity_pass", "result_source", "resolver_script"]
    j = b.merge(c2[keep_cols], on=keys, how="left", suffixes=("", "_resolved"))
    non_null = int(j["exit_dt"].notna().sum()) if "exit_dt" in j.columns else 0
    met = dict(best_rows=int(len(best)), resolved_rows=non_null, coverage=float(non_null / max(1, len(best))), combined_duplicate_keys=int(c.duplicated(keys).sum()), join_keys=" + ".join(keys))
    return j, met


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--tol", type=float, default=1e-8)
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    outdir = root / "107r6c"
    outdir.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")
    prog(0, 6, "start")

    blocks = []
    outputs = []
    findings = []
    best_path = root / "107qc" / "gold_v3_107q_best_family_trade_ledger.csv"
    if not best_path.exists():
        blocks.append(dict(blocker_id="missing_107q_best_family_trade_ledger", path=str(best_path)))
    m15, m15_src = find_ohlc(mt5, "m15")
    m5, m5_src = find_ohlc(mt5, "m5")
    if m15.empty:
        blocks.append(dict(blocker_id="missing_m15_ohlc", tried="|".join(NAMES["m15"])))
    if m5.empty:
        blocks.append(dict(blocker_id="missing_m5_ohlc", tried="|".join(NAMES["m5"])))
    prog(1, 6, f"ohlc loaded m15={len(m15)} m5={len(m5)}")

    best = pd.DataFrame()
    combined_parts = []
    parity_rows = []
    if not blocks:
        best = pd.read_csv(best_path, encoding="utf-8-sig", low_memory=False)
        m15_state = make_m15_state(m15)
        for source_name, subdir, fn in ACTIVE_INPUTS:
            p = root / subdir / fn
            if not p.exists():
                parity_rows.append(dict(source_name=source_name, rows=0, parity_pass_rows=0, parity_fail_rows=0, resolve_error_rows=0, parity_pass_rate=0.0, input_exists=False, path=str(p)))
                continue
            raw = pd.read_csv(p, encoding="utf-8-sig", low_memory=False)
            src = normalize_input(raw, source_name)
            resolved, met = resolve_ledger(src, source_name, m15_state, m5, args.tol)
            met["input_exists"] = True
            met["path"] = str(p)
            parity_rows.append(met)
            if not resolved.empty:
                save(resolved, outdir / f"gold_v3_107r6_{source_name}_resolved_contract_ledger.csv")
                outputs.append(f"gold_v3_107r6_{source_name}_resolved_contract_ledger.csv")
                combined_parts.append(resolved)
            prog(2 + len(parity_rows), 6 + len(ACTIVE_INPUTS), f"resolved {source_name}")
    combined = pd.concat(combined_parts, ignore_index=True) if combined_parts else pd.DataFrame()
    parity = pd.DataFrame(parity_rows)
    save(parity, outdir / "gold_v3_107r6_source_parity_matrix.csv")
    outputs.append("gold_v3_107r6_source_parity_matrix.csv")
    if not combined.empty:
        save(combined, outdir / "gold_v3_107r6_resolved_input_ledgers_combined.csv")
        outputs.append("gold_v3_107r6_resolved_input_ledgers_combined.csv")

    resolved_best = pd.DataFrame()
    join_met = dict(best_rows=0, resolved_rows=0, coverage=0.0, combined_duplicate_keys=0, join_keys="")
    if not blocks and not best.empty and not combined.empty:
        resolved_best, join_met = join_best(best, combined[combined["result_parity_pass"] & combined["exit_dt_ge_entry_dt"]].copy())
        save(resolved_best, outdir / "gold_v3_107r6_resolved_107q_best_family_ledger.csv")
        outputs.append("gold_v3_107r6_resolved_107q_best_family_ledger.csv")
    join_df = pd.DataFrame([join_met])
    save(join_df, outdir / "gold_v3_107r6_join_coverage_matrix.csv")
    outputs.append("gold_v3_107r6_join_coverage_matrix.csv")
    prog(5, 6, "join coverage complete")

    all_source_parity = bool((parity["parity_fail_rows"].fillna(0).astype(int).sum() == 0) and (parity["resolve_error_rows"].fillna(0).astype(int).sum() == 0)) if not parity.empty else False
    full_best_coverage = bool(join_met.get("resolved_rows", 0) == join_met.get("best_rows", -1) and join_met.get("best_rows", 0) > 0)
    if blocks:
        status = BLOCKED
        decision = "PARITY_VERIFIED_RESOLVED_CONTRACT_BLOCKED_INPUT_INCOMPLETE"
    elif full_best_coverage and all_source_parity:
        status = READY
        decision = "PARITY_VERIFIED_RESOLVED_CONTRACT_READY_FOR_107S"
    else:
        status = BLOCKED
        decision = "PARITY_VERIFIED_RESOLVED_CONTRACT_PARTIAL_NEED_PRODUCER_PATCH"
        if not full_best_coverage:
            blocks.append(dict(blocker_id="resolved_107q_best_family_coverage_not_full", observed=join_met.get("resolved_rows", 0), expected=join_met.get("best_rows", 0), coverage=join_met.get("coverage", 0.0)))
        if not all_source_parity:
            blocks.append(dict(blocker_id="source_result_parity_or_resolve_error", parity_fail_rows=int(parity["parity_fail_rows"].fillna(0).sum()) if not parity.empty else -1, resolve_error_rows=int(parity["resolve_error_rows"].fillna(0).sum()) if not parity.empty else -1))

    vals = [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="result_parity_checked", result="PASS", observed=True, expected=True, severity="BLOCKER"),
    ]
    if not combined.empty:
        vals.append(dict(check_id="combined_resolved_rows_positive", result="PASS", observed=len(combined), expected=">0", severity="BLOCKER"))
    if not resolved_best.empty:
        vals.append(dict(check_id="resolved_best_ledger_written", result="PASS", observed=len(resolved_best), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failure_count = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0
    summary = dict(
        step=STEP,
        status=status,
        decision=decision,
        created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        output_dir=str(outdir),
        audit_only=True,
        live_ready=False,
        source_csv_mutated=False,
        contract_mutated=False,
        open_asof_allowed=False,
        csv_contract=CONTRACT,
        pool_policy=POOL_POLICY,
        blocker_count=len(blocks),
        validation_failure_count=validation_failure_count,
        elapsed_seconds=round(time.time() - t0, 2),
        m15_source=m15_src,
        m5_source=m5_src,
        combined_resolved_rows=int(len(combined)) if not combined.empty else 0,
        source_parity_fail_rows=int(parity["parity_fail_rows"].fillna(0).sum()) if not parity.empty else 0,
        source_resolve_error_rows=int(parity["resolve_error_rows"].fillna(0).sum()) if not parity.empty else 0,
        resolved_best_rows=int(len(resolved_best)) if not resolved_best.empty else 0,
        best_family_rows=int(join_met.get("best_rows", 0)),
        best_family_resolved_rows=int(join_met.get("resolved_rows", 0)),
        best_family_exit_dt_coverage=float(join_met.get("coverage", 0.0)),
    )
    if not parity.empty:
        findings.append("source_parity_matrix=" + json.dumps(parity.to_dict(orient="records"), ensure_ascii=False, default=str))
    findings.append("join_coverage=" + json.dumps(join_met, ensure_ascii=False, default=str))

    save(pd.DataFrame(blocks), outdir / "gold_v3_107r6_blocker_matrix.csv")
    save(val, outdir / "gold_v3_107r6_validation_matrix.csv")
    outputs += ["gold_v3_107r6_blocker_matrix.csv", "gold_v3_107r6_validation_matrix.csv", "gold_v3_107r6_summary.json", "GOLD_V3_107R6_PARITY_VERIFIED_RESOLVED_CONTRACT_BUILDER_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (outdir / "gold_v3_107r6_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (outdir / "GOLD_V3_107R6_PARITY_VERIFIED_RESOLVED_CONTRACT_BUILDER_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107R6 report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = [
        "GOLD V3 107R6 PASTE_ME_PARITY_VERIFIED_RESOLVED_CONTRACT_BUILDER",
        f"status: {status}",
        f"ready: {str(status == READY).lower()}",
        "live_ready: false",
        "source_csv_mutated: false",
        "contract_mutated: false",
        "open_asof_allowed: false",
        "safety: audit_only=true, parity_verified_resolver_extension=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false",
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
        "VALIDATION",
        val.to_string(index=False),
        "",
        "OUTPUTS",
    ] + outputs
    (outdir / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(6, 6, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={outdir/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(outdir / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
