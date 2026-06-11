#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, itertools, json, math, os
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "GOLD_V3_107D_RESOLVED_ONLY_GATE_AND_ENTRY_WEAKNESS_DIAGNOSIS_AUDIT_ONLY"
READY = "GOLD_V3_107D_RESOLVED_ONLY_GATE_AND_ENTRY_WEAKNESS_DIAGNOSIS_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_107D_RESOLVED_ONLY_GATE_AND_ENTRY_WEAKNESS_DIAGNOSIS_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"
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
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, avg_result_usd=0.0, negative_month_count=0)
    x = df[pd.to_numeric(df.result_usd, errors="coerce").notna()].copy()
    if x.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, avg_result_usd=0.0, negative_month_count=0)
    x["result_usd"] = pd.to_numeric(x.result_usd, errors="coerce")
    gp = x.loc[x.result_usd > 0, "result_usd"].sum(); gl = -x.loc[x.result_usd < 0, "result_usd"].sum()
    pf = gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)
    if "entry_month" not in x.columns: x["entry_month"] = pd.to_datetime(x.entry_dt, errors="coerce").dt.to_period("M").astype(str)
    mon = x.groupby("entry_month").result_usd.sum()
    return dict(trades=int(len(x)), wins=int((x.result_usd > 0).sum()), losses=int((x.result_usd < 0).sum()), win_rate=float((x.result_usd > 0).mean()), profit_factor=float(pf), sum_result_usd=float(x.result_usd.sum()), avg_result_usd=float(x.result_usd.mean()), negative_month_count=int((mon < 0).sum()))


def summarize(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows = []
    if df.empty: return pd.DataFrame()
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


def allow(vals: list[float], min_n: int, pf_thr: float, loss_lt: int) -> bool:
    if len(vals) < min_n: return True
    return pf(vals) >= pf_thr and loss_streak(vals) < loss_lt


def population(df: pd.DataFrame, pop: str) -> pd.DataFrame:
    x = df.copy()
    hv = x.hv_sibling.astype(bool) if "hv_sibling" in x.columns else pd.Series(False, index=x.index)
    thv = x.is_high_vol.astype(bool) if "is_high_vol" in x.columns else pd.Series(False, index=x.index)
    if pop == "normal_only": return x[~hv].copy()
    if pop == "hv_named_only": return x[hv].copy()
    if pop == "true_high_vol_only": return x[thv].copy()
    if pop == "non_true_high_vol_only": return x[~thv].copy()
    return x


def resolved_gate(df: pd.DataFrame, win: int, min_n: int, pf_thr: float, loss_lt: int) -> pd.DataFrame:
    if df.empty: return df
    x = df.sort_values(["entry_dt", "priority", "candidate_label"]).copy()
    completed = x[pd.to_datetime(x.exit_dt, errors="coerce").notna() & pd.to_numeric(x.result_usd, errors="coerce").notna()].copy()
    completed = completed.sort_values(["exit_dt", "entry_dt", "priority", "candidate_label"])
    recs = completed.to_dict("records"); ptr = 0; hist = defaultdict(lambda: deque(maxlen=win)); chosen = []
    for entry_dt, g in x.groupby("entry_dt", sort=True):
        now = pd.Timestamp(entry_dt)
        while ptr < len(recs) and pd.Timestamp(recs[ptr]["exit_dt"]) <= now:
            r = recs[ptr]; hist[r["candidate_label"]].append(float(r["result_usd"])); ptr += 1
        allowed = []
        for _, r in g.sort_values(["priority", "candidate_label"]).iterrows():
            vals = list(hist[r.candidate_label])
            if allow(vals, min_n, pf_thr, loss_lt):
                d = r.to_dict(); d.update(health_history_n=len(vals)); allowed.append(d)
        if allowed: chosen.append(allowed[0])
    return pd.DataFrame(chosen)


def score(m: dict[str, Any], recent: dict[str, Any]) -> float:
    if m["trades"] < 20: return -999999.0
    pfv = 10.0 if math.isinf(m["profit_factor"]) else float(m["profit_factor"])
    rpf = 10.0 if math.isinf(recent["profit_factor"]) else float(recent["profit_factor"])
    return pfv * 1000.0 + rpf * 450.0 + float(m["sum_result_usd"]) / 10.0 + float(recent["sum_result_usd"]) / 8.0 - float(m["negative_month_count"]) * 250.0


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True); df.to_csv(p, index=False, encoding="utf-8-sig")


def write_paste(p: Path, summary: dict[str, Any], blockers: list[dict[str, Any]], val: pd.DataFrame, outputs: list[str], findings: list[str]) -> None:
    lines = ["GOLD V3 107D PASTE_ME_RESOLVED_ONLY_GATE_AND_ENTRY_WEAKNESS", f"status: {summary['status']}", "ready: " + str(summary["status"] == READY).lower(), "live_ready: false", "source_csv_mutated: false", "contract_mutated: false", "manual_candidate_demotion_or_removal: false", "open_asof_allowed: false", "csv_contract: " + CSV_CONTRACT, "csv_open_bar_exclusion_required: false", "safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false", "pool_policy: " + POOL_POLICY, "source: Stage107 outputs only; resolved-only histories", f"blocker_count: {len(blockers)}", "", "KEY_METRICS"]
    for k, v in summary.items(): lines.append(f"{k}: {v}")
    lines += ["", "FINDINGS"] + (findings or ["NO_FINDINGS"])
    lines += ["", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS", "", "VALIDATION", val.to_string(index=False), "", "OUTPUTS"] + outputs
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=STEP); ap.add_argument("--mt5-files-dir", default=""); ap.add_argument("--output-dir", default=""); args = ap.parse_args()
    cdir = files_dir(args.mt5_files_dir); in107 = cdir / "FX_OUTPUTS" / "gold_v3" / "107c"; out = Path(args.output_dir).expanduser().resolve() if args.output_dir else cdir / "FX_OUTPUTS" / "gold_v3" / "107dc"; out.mkdir(parents=True, exist_ok=True)
    ledger_p = in107 / "gold_v3_107_long_short_proxy_ledger.csv"; summary_p = in107 / "gold_v3_107_direction_assumption_summary.json"
    blockers = []; vals = []
    for name, p in [("stage107_ledger", ledger_p), ("stage107_summary", summary_p)]:
        passed = p.exists() and not bad(p); vals.append(ok(name + "_present", passed, str(p), "exists and allowed"))
        if not passed: blockers.append(block(name + "_missing_or_forbidden", str(p), "REQUIRED_STAGE107_OUTPUT_MISSING_OR_FORBIDDEN"))
    outputs = []; findings = []; grid = pd.DataFrame(); top_ledger = pd.DataFrame()
    if not blockers:
        try:
            df = read_csv(ledger_p); df["entry_dt"] = pd.to_datetime(df.entry_dt, errors="coerce"); df["exit_dt"] = pd.to_datetime(df.exit_dt, errors="coerce"); df["entry_month"] = df.entry_dt.dt.to_period("M").astype(str); df["result_usd"] = pd.to_numeric(df.result_usd, errors="coerce")
            if "is_high_vol" not in df.columns and "is_high_vol_value" in df.columns: df["is_high_vol"] = df["is_high_vol_value"]
            if "is_high_vol" in df.columns: df["is_high_vol"] = df["is_high_vol"].astype(str).str.lower().isin(["true", "1", "yes"])
            else: df["is_high_vol"] = False
            rows = []; ledgers = {}
            windows = [10, 15, 20, 30]; mins = [5, 8, 10, 15]; pfs = [1.00, 1.10, 1.25, 1.50]; losses = [1, 2, 3]; pops = ["all_rows", "normal_only", "hv_named_only", "true_high_vol_only", "non_true_high_vol_only"]
            for side, pop, win, mn, pft, losslt in itertools.product(["LONG", "SHORT"], pops, windows, mins, pfs, losses):
                base = population(df[df.proxy_side == side].copy(), pop)
                if len(base) < 5: continue
                sel = resolved_gate(base, win, mn, pft, losslt)
                if sel.empty: continue
                m = metric(sel); recent = metric(sel[sel.entry_dt >= pd.Timestamp("2026-03-01")]); recent56 = metric(sel[sel.entry_month.isin(["2026-05", "2026-06"])])
                r = dict(proxy_side=side, population=pop, window=win, min_history=mn, pf_threshold=pft, loss_streak_lt=losslt, **{f"all_{k}": v for k, v in m.items()}, **{f"recent_2026_03_plus_{k}": v for k, v in recent.items()}, **{f"recent_2026_05_06_{k}": v for k, v in recent56.items()})
                r["score"] = score(m, recent)
                rows.append(r)
                key = (side, pop, win, mn, pft, losslt); ledgers[key] = sel
            grid = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()
            save(grid, out / "gold_v3_107d_resolved_only_grid_summary.csv"); outputs.append("gold_v3_107d_resolved_only_grid_summary.csv")
            top = grid.head(25).copy(); save(top, out / "gold_v3_107d_top_resolved_only_configs.csv"); outputs.append("gold_v3_107d_top_resolved_only_configs.csv")
            if not top.empty:
                best = top.iloc[0]; key = (best.proxy_side, best.population, int(best.window), int(best.min_history), float(best.pf_threshold), int(best.loss_streak_lt)); top_ledger = ledgers.get(key, pd.DataFrame()).copy(); top_ledger["selected_config_rank"] = 1; save(top_ledger, out / "gold_v3_107d_top_config_selected_trade_ledger.csv"); outputs.append("gold_v3_107d_top_config_selected_trade_ledger.csv")
                findings.append(f"best_config: side={best.proxy_side} population={best.population} window={best.window} min_history={best.min_history} pf_threshold={best.pf_threshold} loss_streak_lt={best.loss_streak_lt} all_pf={best.all_profit_factor} all_wr={best.all_win_rate} recent03_pf={best.recent_2026_03_plus_profit_factor} score={best.score}")
            raw_month = summarize(df, ["entry_month", "proxy_side", "hv_sibling", "is_high_vol"]); raw_seg = summarize(df, ["proxy_side", "source_rank", "profile_id", "jst_hour", "jst_weekday", "hv_sibling", "is_high_vol"])
            save(raw_month, out / "gold_v3_107d_raw_entry_weakness_by_month.csv"); save(raw_seg, out / "gold_v3_107d_raw_entry_weakness_by_segment.csv"); outputs += ["gold_v3_107d_raw_entry_weakness_by_month.csv", "gold_v3_107d_raw_entry_weakness_by_segment.csv"]
            findings.append("resolved_only_grid_uses_only_exit_dt_le_current_entry_dt_history")
            findings.append("entry_weakness_outputs_are_raw_proxy_diagnostics_not_runtime_changes")
            vals.append(ok("grid_rows_positive", len(grid) > 0, len(grid), ">0"))
        except Exception as e:
            vals.append(ok("stage107d_runtime", False, repr(e), "no_exception")); blockers.append(block("stage107d_runtime_exception", str(ledger_p), "RUNTIME_EXCEPTION", repr(e)))
    vals += [ok("audit_only", True, True, True), ok("source_csv_mutated", True, False, False), ok("candidate_pool_mutated", True, False, False), ok("open_asof_allowed", True, False, False)]
    valdf = pd.DataFrame(vals); status = READY if not blockers and valdf.result.eq("PASS").all() else BLOCKED
    best_summary = {}
    if not grid.empty:
        b = grid.iloc[0].to_dict(); best_summary = {f"best_{k}": v for k, v in b.items() if k in ["proxy_side", "population", "window", "min_history", "pf_threshold", "loss_streak_lt", "all_trades", "all_win_rate", "all_profit_factor", "all_sum_result_usd", "all_negative_month_count", "recent_2026_03_plus_profit_factor", "recent_2026_05_06_profit_factor", "score"]}
    summary = dict(step=STEP, status=status, created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), input_dir=str(in107), output_dir=str(out), audit_only=True, live_ready=False, source_csv_mutated=False, contract_mutated=False, manual_candidate_demotion_or_removal=False, open_asof_allowed=False, csv_contract=CSV_CONTRACT, csv_open_bar_exclusion_required=False, pool_policy=POOL_POLICY, blocker_count=len(blockers), validation_failure_count=int((~valdf.result.eq("PASS")).sum()), grid_rows=int(len(grid))) | best_summary
    save(pd.DataFrame(blockers), out / "gold_v3_107d_blocker_matrix.csv"); save(valdf, out / "gold_v3_107d_validation_matrix.csv"); (out / "gold_v3_107d_summary.json").write_text(json.dumps(summary | {"findings": findings}, ensure_ascii=False, indent=2, default=str), encoding="utf-8"); (out / "GOLD_V3_107D_RESOLVED_ONLY_GATE_AND_ENTRY_WEAKNESS_DIAGNOSIS_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107D resolved-only gate and entry weakness diagnosis audit-only report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    outputs += ["gold_v3_107d_blocker_matrix.csv", "gold_v3_107d_validation_matrix.csv", "gold_v3_107d_summary.json", "GOLD_V3_107D_RESOLVED_ONLY_GATE_AND_ENTRY_WEAKNESS_DIAGNOSIS_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    write_paste(out / "paste_me.txt", summary, blockers, valdf, outputs, findings)
    print(json.dumps({"status": status, "ready": status == READY, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2)); return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
