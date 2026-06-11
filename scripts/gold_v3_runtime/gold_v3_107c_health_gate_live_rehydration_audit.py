#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, math, os
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "GOLD_V3_107C_HEALTH_GATE_LIVE_REHYDRATION_AUDIT_ONLY"
READY = "GOLD_V3_107C_HEALTH_GATE_LIVE_REHYDRATION_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_107C_HEALTH_GATE_LIVE_REHYDRATION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
FORBIDDEN = ("gold_v2", "old_gold", "legacy_gold", "disc8", "stage41", "gold_specialist_8")
ROOT = Path(__file__).resolve().parents[2]


def bad(p: Path) -> bool:
    s = str(p).replace("\\", "/").lower()
    return any(x in s for x in FORBIDDEN)


def files_dir(arg: str) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    env = os.environ.get("MT5_FILES_DIR") or os.environ.get("MQL5_FILES_DIR")
    if env:
        return Path(env).expanduser().resolve()
    p = ROOT
    while p.parent != p:
        if p.name.lower() == "files" and p.parent.name.lower() == "mql5":
            return p
        p = p.parent
    return ROOT


def ok(cid: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {"check_id": cid, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": "BLOCKER"}


def block(bid: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": bid, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def read_csv(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, encoding="utf-8-sig")


def metric(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, avg_result_usd=0.0)
    x = df[pd.to_numeric(df.result_usd, errors="coerce").notna()].copy()
    if x.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, avg_result_usd=0.0)
    x["result_usd"] = pd.to_numeric(x.result_usd, errors="coerce")
    gp = x.loc[x.result_usd > 0, "result_usd"].sum(); gl = -x.loc[x.result_usd < 0, "result_usd"].sum()
    pf = gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)
    return dict(trades=int(len(x)), wins=int((x.result_usd > 0).sum()), losses=int((x.result_usd < 0).sum()), win_rate=float((x.result_usd > 0).mean()), profit_factor=float(pf), sum_result_usd=float(x.result_usd.sum()), avg_result_usd=float(x.result_usd.mean()))


def summarize(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows = []
    if df.empty:
        return pd.DataFrame()
    for k, g in df.groupby(by, dropna=False):
        if not isinstance(k, tuple): k = (k,)
        d = {c: v for c, v in zip(by, k)}; d.update(metric(g)); rows.append(d)
    return pd.DataFrame(rows)


def pf(vals: list[float]) -> float:
    a = np.array(vals, float); gp = a[a > 0].sum(); gl = -a[a < 0].sum()
    return gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)


def loss_streak(vals: list[float]) -> int:
    n = 0
    for v in reversed(vals):
        if v < 0: n += 1
        else: break
    return n


def allowed_by_history(vals: list[float], min_n: int, pf_thr: float, loss_lt: int) -> tuple[bool, Any, Any]:
    if len(vals) < min_n:
        return True, "", ""
    hp = pf(vals); ls = loss_streak(vals)
    return hp >= pf_thr and ls < loss_lt, hp, ls


def filter_hv(df: pd.DataFrame, include_hv: bool) -> pd.DataFrame:
    x = df.copy()
    if not include_hv and "hv_sibling" in x.columns:
        x = x[~x.hv_sibling.astype(bool)].copy()
    return x


def stage45_entry_update_gate(df: pd.DataFrame, include_hv: bool, win: int, min_n: int, pf_thr: float, loss_lt: int) -> pd.DataFrame:
    x = filter_hv(df, include_hv)
    if x.empty: return x
    hist = defaultdict(lambda: deque(maxlen=win)); chosen = []
    for _, g in x.sort_values(["entry_dt", "priority", "candidate_label"]).groupby("entry_dt", sort=True):
        allowed = []
        for _, r in g.sort_values(["priority", "candidate_label"]).iterrows():
            vals = list(hist[r.candidate_label]); okrow, hp, ls = allowed_by_history(vals, min_n, pf_thr, loss_lt)
            if okrow:
                d = r.to_dict(); d.update(mode="entry_update_stage45_style", include_hv_siblings=include_hv, health_history_n=len(vals), health_pf=hp, health_loss_streak=ls); allowed.append(d)
        if allowed: chosen.append(allowed[0])
        for _, r in g.iterrows():
            if pd.notna(r.result_usd): hist[r.candidate_label].append(float(r.result_usd))
    return pd.DataFrame(chosen)


def live_rehydrated_gate(df: pd.DataFrame, include_hv: bool, win: int, min_n: int, pf_thr: float, loss_lt: int) -> pd.DataFrame:
    x = filter_hv(df, include_hv)
    if x.empty: return x
    x = x.sort_values(["entry_dt", "priority", "candidate_label"]).copy()
    completed = x[pd.to_datetime(x.exit_dt, errors="coerce").notna() & pd.to_numeric(x.result_usd, errors="coerce").notna()].copy()
    completed["exit_dt"] = pd.to_datetime(completed.exit_dt, errors="coerce")
    by_exit = completed.sort_values(["exit_dt", "entry_dt", "priority", "candidate_label"]).to_dict("records")
    ptr = 0; hist = defaultdict(lambda: deque(maxlen=win)); chosen = []
    for entry_dt, g in x.groupby("entry_dt", sort=True):
        now = pd.Timestamp(entry_dt)
        while ptr < len(by_exit) and pd.Timestamp(by_exit[ptr]["exit_dt"]) <= now:
            rec = by_exit[ptr]; hist[rec["candidate_label"]].append(float(rec["result_usd"])); ptr += 1
        allowed = []
        pending_known = len(by_exit) - ptr
        for _, r in g.sort_values(["priority", "candidate_label"]).iterrows():
            vals = list(hist[r.candidate_label]); okrow, hp, ls = allowed_by_history(vals, min_n, pf_thr, loss_lt)
            if okrow:
                d = r.to_dict(); d.update(mode="exit_known_live_rehydrated", include_hv_siblings=include_hv, health_history_n=len(vals), health_pf=hp, health_loss_streak=ls, unresolved_future_rows_not_in_history=pending_known); allowed.append(d)
        if allowed: chosen.append(allowed[0])
    return pd.DataFrame(chosen)


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True); df.to_csv(p, index=False, encoding="utf-8-sig")


def write_paste(p: Path, summary: dict[str, Any], blockers: list[dict[str, Any]], val: pd.DataFrame, outputs: list[str], findings: list[str]) -> None:
    lines = ["GOLD V3 107C PASTE_ME_HEALTH_GATE_LIVE_REHYDRATION", f"status: {summary['status']}", "ready: " + str(summary["status"] == READY).lower(), "live_ready: false", "source_csv_mutated: false", "contract_mutated: false", "manual_candidate_demotion_or_removal: false", "open_asof_allowed: false", "csv_contract: " + CSV_CONTRACT, "csv_open_bar_exclusion_required: false", "safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false", "pool_policy: " + POOL_POLICY, "source: Stage107 outputs only", f"blocker_count: {len(blockers)}", "", "KEY_METRICS"]
    for k, v in summary.items():
        lines.append(f"{k}: {v}")
    lines += ["", "FINDINGS"] + (findings or ["NO_FINDINGS"])
    lines += ["", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS", "", "VALIDATION", val.to_string(index=False), "", "OUTPUTS"] + outputs
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=STEP); ap.add_argument("--mt5-files-dir", default=""); ap.add_argument("--output-dir", default=""); ap.add_argument("--health-window", type=int, default=30); ap.add_argument("--health-min-history", type=int, default=20); ap.add_argument("--strict-pf-threshold", type=float, default=1.10); ap.add_argument("--strict-loss-streak-lt", type=int, default=3); args = ap.parse_args()
    cdir = files_dir(args.mt5_files_dir); in107 = cdir / "FX_OUTPUTS" / "gold_v3" / "107c"; out = Path(args.output_dir).expanduser().resolve() if args.output_dir else cdir / "FX_OUTPUTS" / "gold_v3" / "107cc"; out.mkdir(parents=True, exist_ok=True)
    ledger_p = in107 / "gold_v3_107_long_short_proxy_ledger.csv"; summary_p = in107 / "gold_v3_107_direction_assumption_summary.json"
    blockers = []; vals = []
    for name, p in [("stage107_ledger", ledger_p), ("stage107_summary", summary_p)]:
        passed = p.exists() and not bad(p); vals.append(ok(name + "_present", passed, str(p), "exists and allowed"))
        if not passed: blockers.append(block(name + "_missing_or_forbidden", str(p), "REQUIRED_STAGE107_OUTPUT_MISSING_OR_FORBIDDEN"))
    outputs = []; findings = []
    selected = pd.DataFrame(); diff = pd.DataFrame(); lag = pd.DataFrame()
    if not blockers:
        try:
            df = read_csv(ledger_p); df["entry_dt"] = pd.to_datetime(df.entry_dt, errors="coerce"); df["exit_dt"] = pd.to_datetime(df.exit_dt, errors="coerce"); df["entry_month"] = df.entry_dt.dt.to_period("M").astype(str); df["result_usd"] = pd.to_numeric(df.result_usd, errors="coerce")
            if "is_high_vol" not in df.columns and "is_high_vol_value" in df.columns: df["is_high_vol"] = df["is_high_vol_value"]
            if "is_high_vol" in df.columns: df["is_high_vol"] = df["is_high_vol"].astype(str).str.lower().isin(["true", "1", "yes"])
            else: df["is_high_vol"] = False
            parts = []
            for side, g in df.groupby("proxy_side", dropna=False):
                for include_hv in [False, True]:
                    x1 = stage45_entry_update_gate(g, include_hv, args.health_window, args.health_min_history, args.strict_pf_threshold, args.strict_loss_streak_lt)
                    x2 = live_rehydrated_gate(g, include_hv, args.health_window, args.health_min_history, args.strict_pf_threshold, args.strict_loss_streak_lt)
                    if not x1.empty: parts.append(x1)
                    if not x2.empty: parts.append(x2)
            selected = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
            if not selected.empty:
                selected["surface"] = np.where(selected.include_hv_siblings.astype(bool), "strict_health_gate_plus_hv_siblings", "strict_health_gate_no_hv")
                selected["entry_month"] = pd.to_datetime(selected.entry_dt, errors="coerce").dt.to_period("M").astype(str)
            side_sum = summarize(selected, ["surface", "proxy_side", "mode"]); monthly = summarize(selected, ["surface", "entry_month", "proxy_side", "mode"])
            save(selected, out / "gold_v3_107c_selected_trade_ledger.csv"); save(side_sum, out / "gold_v3_107c_gate_mode_summary.csv"); save(monthly, out / "gold_v3_107c_gate_mode_monthly_summary.csv")
            outputs += ["gold_v3_107c_selected_trade_ledger.csv", "gold_v3_107c_gate_mode_summary.csv", "gold_v3_107c_gate_mode_monthly_summary.csv"]
            if not side_sum.empty:
                piv = side_sum.pivot_table(index=["surface", "proxy_side"], columns="mode", values=["trades", "win_rate", "profit_factor", "sum_result_usd"], aggfunc="first").reset_index()
                piv.columns = ["_".join([str(x) for x in c if str(x) != ""]).strip("_") if isinstance(c, tuple) else str(c) for c in piv.columns]
                save(piv, out / "gold_v3_107c_gate_mode_diff_summary.csv"); outputs.append("gold_v3_107c_gate_mode_diff_summary.csv")
                diff = piv
            complete = df[pd.to_datetime(df.exit_dt, errors="coerce").notna()].copy(); complete["lag_minutes"] = (complete.exit_dt - complete.entry_dt).dt.total_seconds() / 60.0
            lag = complete.groupby(["proxy_side", "hv_sibling", "is_high_vol"], dropna=False).lag_minutes.agg(["count", "mean", "median", "max"]).reset_index(); save(lag, out / "gold_v3_107c_pending_lag_summary.csv"); outputs.append("gold_v3_107c_pending_lag_summary.csv")
            def get(surface, side, mode):
                r = side_sum[(side_sum.surface == surface) & (side_sum.proxy_side == side) & (side_sum.mode == mode)]
                return r.iloc[0].to_dict() if len(r) else {}
            a = get("strict_health_gate_plus_hv_siblings", "LONG", "entry_update_stage45_style"); b = get("strict_health_gate_plus_hv_siblings", "LONG", "exit_known_live_rehydrated")
            findings.append(f"plus_hv_LONG_entry_update: trades={a.get('trades')} win_rate={a.get('win_rate')} pf={a.get('profit_factor')} sum={a.get('sum_result_usd')}")
            findings.append(f"plus_hv_LONG_exit_known: trades={b.get('trades')} win_rate={b.get('win_rate')} pf={b.get('profit_factor')} sum={b.get('sum_result_usd')}")
            findings.append("If exit_known differs materially from entry_update, Stage45-style backtest gate may be using outcomes before they are live-knowable.")
            vals.append(ok("selected_trade_rows_positive", len(selected) > 0, len(selected), ">0"))
        except Exception as e:
            vals.append(ok("stage107c_runtime", False, repr(e), "no_exception")); blockers.append(block("stage107c_runtime_exception", str(ledger_p), "RUNTIME_EXCEPTION", repr(e)))
    vals += [ok("audit_only", True, True, True), ok("source_csv_mutated", True, False, False), ok("candidate_pool_mutated", True, False, False), ok("open_asof_allowed", True, False, False)]
    valdf = pd.DataFrame(vals); status = READY if not blockers and valdf.result.eq("PASS").all() else BLOCKED
    summary = dict(step=STEP, status=status, created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), input_dir=str(in107), output_dir=str(out), audit_only=True, live_ready=False, source_csv_mutated=False, contract_mutated=False, manual_candidate_demotion_or_removal=False, open_asof_allowed=False, csv_contract=CSV_CONTRACT, csv_open_bar_exclusion_required=False, pool_policy=POOL_POLICY, blocker_count=len(blockers), validation_failure_count=int((~valdf.result.eq("PASS")).sum()))
    save(pd.DataFrame(blockers), out / "gold_v3_107c_blocker_matrix.csv"); save(valdf, out / "gold_v3_107c_validation_matrix.csv"); (out / "gold_v3_107c_health_gate_live_rehydration_summary.json").write_text(json.dumps(summary | {"findings": findings}, ensure_ascii=False, indent=2, default=str), encoding="utf-8"); (out / "GOLD_V3_107C_HEALTH_GATE_LIVE_REHYDRATION_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107C health gate live rehydration audit-only report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    outputs += ["gold_v3_107c_blocker_matrix.csv", "gold_v3_107c_validation_matrix.csv", "gold_v3_107c_health_gate_live_rehydration_summary.json", "GOLD_V3_107C_HEALTH_GATE_LIVE_REHYDRATION_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    write_paste(out / "paste_me.txt", summary, blockers, valdf, outputs, findings)
    print(json.dumps({"status": status, "ready": status == READY, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2)); return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
