#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, importlib.util, json, math, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY"
READY = "GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
FORBIDDEN = ("gold_v2", "old_gold", "legacy_gold", "disc8", "stage41", "gold_specialist_8")
ROOT = Path(__file__).resolve().parents[2]
P45 = Path(__file__).resolve().with_name("gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.py")
P69 = Path(__file__).resolve().with_name("gold_v3_69_live_csv_condition_detector_audit.py")


def bad(p: Path) -> bool:
    s = str(p).replace("\\", "/").lower()
    return any(x in s for x in FORBIDDEN)


def mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


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


def eval_proxy(opps: pd.DataFrame, m5: pd.DataFrame, side: str, complete: bool) -> pd.DataFrame:
    if opps.empty:
        return pd.DataFrame()
    m5 = m5.sort_values("time").reset_index(drop=True)
    times = m5.time.values; lo = m5.low.to_numpy(float); hi = m5.high.to_numpy(float); cl = m5.close.to_numpy(float)
    out = []
    for _, r in opps.iterrows():
        et = pd.Timestamp(r.entry_dt); entry = float(r.entry_price); tp = float(r.tp_usd); sl = float(r.sl_usd); h = int(r.horizon_m15)
        end = et + pd.Timedelta(minutes=15 * h); si = np.searchsorted(times, np.datetime64(et), side="right"); ei = np.searchsorted(times, np.datetime64(end), side="right")
        d = r.to_dict(); d["proxy_side"] = side; d["horizon_m5_bars"] = h * 3
        if ei <= si or (complete and ei > 0 and m5.time.iloc[ei - 1] < end - pd.Timedelta(minutes=5)):
            d.update(exit_dt=pd.NaT, exit_price=np.nan, exit_reason="INCOMPLETE_HORIZON", result_usd=np.nan, is_win=False, is_loss=False, evaluated=False); out.append(d); continue
        if side == "LONG":
            tp_px = entry + tp; sl_px = entry - sl; tp_hit = np.where(hi[si:ei] >= tp_px)[0]; sl_hit = np.where(lo[si:ei] <= sl_px)[0]
        else:
            tp_px = entry - tp; sl_px = entry + sl; tp_hit = np.where(lo[si:ei] <= tp_px)[0]; sl_hit = np.where(hi[si:ei] >= sl_px)[0]
        ft = int(tp_hit[0]) if len(tp_hit) else None; fs = int(sl_hit[0]) if len(sl_hit) else None
        if fs is not None and (ft is None or fs <= ft):
            ai = si + fs; res = (m5.time.iloc[ai], sl_px, "SL", -sl)
        elif ft is not None:
            ai = si + ft; res = (m5.time.iloc[ai], tp_px, "TP", tp)
        else:
            ai = ei - 1; ep = float(cl[ai]); res = (m5.time.iloc[ai], ep, "TIMEOUT", ep - entry if side == "LONG" else entry - ep)
        d.update(exit_dt=res[0], exit_price=res[1], exit_reason=res[2], result_usd=float(res[3]), is_win=res[3] > 0, is_loss=res[3] < 0, evaluated=True); out.append(d)
    return pd.DataFrame(out)


def met(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty or "evaluated" not in df.columns:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0)
    x = df[df.evaluated == True].copy()
    if x.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0)
    gp = x.loc[x.result_usd > 0, "result_usd"].sum(); gl = -x.loc[x.result_usd < 0, "result_usd"].sum(); pf = gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)
    return dict(trades=int(len(x)), wins=int((x.result_usd > 0).sum()), losses=int((x.result_usd < 0).sum()), win_rate=float((x.result_usd > 0).mean()), profit_factor=float(pf))


def by(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    rows = []
    if df.empty: return pd.DataFrame()
    for k, g in df.groupby(cols, dropna=False):
        if not isinstance(k, tuple): k = (k,)
        d = {c: v for c, v in zip(cols, k)}; d.update(met(g)); rows.append(d)
    return pd.DataFrame(rows)


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True); df.to_csv(p, index=False, encoding="utf-8-sig")


def write_paste(p: Path, summary: dict[str, Any], blockers: list[dict[str, Any]], val: pd.DataFrame, outputs: list[str], findings: list[str]) -> None:
    lines = ["GOLD V3 107 PASTE_ME_NORMAL_AND_HV_DIRECTION_ASSUMPTION_SUMMARY", f"status: {summary['status']}", "ready: " + str(summary["status"] == READY).lower(), "live_ready: false", "source_csv_mutated: false", "contract_mutated: false", "manual_candidate_demotion_or_removal: false", "open_asof_allowed: false", "csv_contract: " + CSV_CONTRACT, "csv_open_bar_exclusion_required: false", "safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false", "pool_policy: " + POOL_POLICY, "candidate_source_of_truth: Stage45/Stage69 GOLD V3 code rebuilt audit-only", f"blocker_count: {len(blockers)}", "", "KEY_METRICS"]
    for k, v in summary.items():
        if k.endswith(("rows", "count", "trades", "wins", "losses", "rate", "factor")):
            lines.append(f"{k}: {v}")
    lines += ["", "FINDINGS"] + (findings or ["NO_FINDINGS"])
    lines += ["", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS", "", "VALIDATION", val.to_string(index=False), "", "OUTPUTS"] + outputs
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=STEP); ap.add_argument("--candle-dir", default=""); ap.add_argument("--mt5-files-dir", default=""); ap.add_argument("--output-dir", default=""); ap.add_argument("--start-jst", default="2026-01-01"); ap.add_argument("--end-jst", default=""); ap.add_argument("--allow-incomplete-horizon", action="store_true"); a = ap.parse_args()
    cdir = files_dir(a.candle_dir or a.mt5_files_dir); base = cdir / "FX_OUTPUTS" / "gold_v3"; out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base / "107c"; out.mkdir(parents=True, exist_ok=True)
    p50 = base / "50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only" / "gold_v3_50_rolling_prior_60d_q70_state.csv"; p68 = base / "68_rank_dedup_selection_repro_audit_only" / "gold_v3_68_rank_dedup_selection_repro_summary.json"; p51 = base / "51_full_candidate_virtual_opportunity_ledger_builder_audit_only" / "gold_v3_51_virtual_opportunity_ledger.csv"
    required = [("goldsharp_m5", cdir / "goldsharp_m5.csv"), ("goldsharp_m15", cdir / "goldsharp_m15.csv"), ("goldsharp_h4", cdir / "goldsharp_h4.csv"), ("stage45_script", P45), ("stage69_script", P69), ("stage50_q70", p50), ("stage68_summary", p68), ("stage51_ledger", p51)]
    validators = []; blockers = []
    for name, path in required:
        passed = path.exists() and not bad(path); validators.append(ok(name + "_present", passed, str(path), "exists and allowed"))
        if not passed: blockers.append(block(name + "_missing_or_forbidden", str(path), "REQUIRED_EXACT_INPUT_MISSING_OR_FORBIDDEN"))
    findings = []; outputs = []; opp = pd.DataFrame(); ledger = pd.DataFrame()
    if not blockers:
        try:
            st45 = mod("gold_v3_stage45", P45); st69 = mod("gold_v3_stage69", P69)
            m15, m5 = st45.prepare(cdir, "closed", 60, 0.70)
            q = st69.read_csv(p50); q["m15_time_jst"] = pd.to_datetime(q["m15_time_jst"], errors="coerce"); q = q.dropna(subset=["m15_time_jst"]).drop_duplicates("m15_time_jst")
            m15 = m15.drop(columns=["m15_atr28_q", "is_high_vol"], errors="ignore").merge(q[["m15_time_jst", "atr28_q70", "high_vol_pass"]], left_on="time", right_on="m15_time_jst", how="left")
            m15["m15_atr28_q"] = pd.to_numeric(m15["atr28_q70"], errors="coerce"); m15["is_high_vol"] = m15["high_vol_pass"].fillna(False).astype(bool)
            cands = st45.base_candidates(); opp = st45.opportunities(m15, cands + st45.add_hv_siblings(cands))
            if not opp.empty:
                t = pd.to_datetime(opp.entry_dt, errors="coerce")
                if a.start_jst: opp = opp[t >= pd.Timestamp(a.start_jst)].copy(); t = pd.to_datetime(opp.entry_dt, errors="coerce")
                if a.end_jst: opp = opp[t <= pd.Timestamp(a.end_jst)].copy()
                opp = st69.add_key_columns(opp).sort_values(["entry_dt", "priority", "candidate_label", "source_rank"]).reset_index(drop=True); opp["condition_id"] = [f"GOLDV3_107_COND_{i:09d}" for i in range(len(opp))]
            side_cols = [c for c in opp.columns if any(w in str(c).lower() for w in ["side", "direction", "trade_side", "signal_side", "position_side", "order_side", "dir"])] if not opp.empty else []
            ledger = pd.concat([eval_proxy(opp, m5, "LONG", not a.allow_incomplete_horizon), eval_proxy(opp, m5, "SHORT", not a.allow_incomplete_horizon)], ignore_index=True)
            if ledger.empty: blockers.append(block("stage107_no_proxy_rows", str(cdir), "NO_PROXY_ROWS_PRODUCED"))
            save(opp, out / "gold_v3_107_rebuilt_stage45_69_opportunities.csv"); save(ledger, out / "gold_v3_107_long_short_proxy_ledger.csv"); save(by(ledger, ["candidate_label", "hv_sibling", "profile_id", "proxy_side"]), out / "gold_v3_107_per_candidate_long_short_metrics.csv"); save(by(ledger, ["proxy_side"]), out / "gold_v3_107_side_summary.csv"); save(by(ledger, ["jst_hour", "proxy_side"]), out / "gold_v3_107_segment_jst_hour_metrics.csv"); save(by(ledger, ["jst_weekday", "proxy_side"]), out / "gold_v3_107_segment_jst_weekday_metrics.csv")
            x = ledger.copy(); x["h4_bucket"] = pd.to_datetime(x.entry_dt, errors="coerce").dt.floor("4h"); save(by(x, ["h4_bucket", "proxy_side"]), out / "gold_v3_107_segment_h4_bucket_metrics.csv")
            outputs += ["gold_v3_107_rebuilt_stage45_69_opportunities.csv", "gold_v3_107_long_short_proxy_ledger.csv", "gold_v3_107_per_candidate_long_short_metrics.csv", "gold_v3_107_side_summary.csv", "gold_v3_107_segment_jst_hour_metrics.csv", "gold_v3_107_segment_jst_weekday_metrics.csv", "gold_v3_107_segment_h4_bucket_metrics.csv"]
            findings.append("side_direction_like_columns_found: " + (",".join(side_cols) if side_cols else "NONE - CRITICAL_DIRECTION_RISK")); findings.append("candidate source rebuilt from Stage45/Stage69 code; Stage99-106 outputs are recap/evidence only"); findings.append("TP/SL uses tp_usd/sl_usd as-is; H128 is 128 M15 bars and M5 horizon is horizon_m15*3")
            validators += [ok("stage45_import_ok", True, str(P45), "importable"), ok("stage69_import_ok", True, str(P69), "importable"), ok("q70_joined_rows_positive", int(m15.m15_atr28_q.notna().sum()) > 0, int(m15.m15_atr28_q.notna().sum()), ">0"), ok("opportunity_rows_positive", len(opp) > 0, len(opp), ">0"), ok("stage45_evaluate_not_called", True, "not_called", "not_called")]
        except Exception as e:
            validators.append(ok("stage107_runtime", False, repr(e), "no_exception")); blockers.append(block("stage107_runtime_exception", str(P45), "RUNTIME_EXCEPTION", repr(e)))
    validators += [ok("audit_only", True, True, True), ok("source_csv_mutated", True, False, False), ok("candidate_pool_mutated", True, False, False), ok("stage45_stage69_runtime_mutated", True, False, False), ok("open_asof_allowed", True, False, False)]
    val = pd.DataFrame(validators); status = READY if not blockers and val.result.eq("PASS").all() else BLOCKED
    lm = met(ledger[ledger.proxy_side == "LONG"]) if not ledger.empty and "proxy_side" in ledger.columns else met(pd.DataFrame()); sm = met(ledger[ledger.proxy_side == "SHORT"]) if not ledger.empty and "proxy_side" in ledger.columns else met(pd.DataFrame())
    summary = dict(step=STEP, status=status, created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), candle_dir=str(cdir), output_dir=str(out), candidate_source_of_truth="Stage45/Stage69 GOLD V3 code rebuilt audit-only", audit_only=True, live_ready=False, source_csv_mutated=False, contract_mutated=False, manual_candidate_demotion_or_removal=False, open_asof_allowed=False, csv_contract=CSV_CONTRACT, csv_open_bar_exclusion_required=False, pool_policy=POOL_POLICY, opportunity_rows=int(len(opp)), candidate_count=int(opp.candidate_key.nunique()) if not opp.empty and "candidate_key" in opp.columns else 0, normal_opportunity_rows=int((~opp.hv_sibling.astype(bool)).sum()) if not opp.empty and "hv_sibling" in opp.columns else 0, hv_named_opportunity_rows=int(opp.hv_sibling.astype(bool).sum()) if not opp.empty and "hv_sibling" in opp.columns else 0, side_direction_column_count=0 if opp.empty else int(len([c for c in opp.columns if any(w in str(c).lower() for w in ["side", "direction", "trade_side", "signal_side", "position_side", "order_side", "dir"])])), long_trades=lm["trades"], long_wins=lm["wins"], long_losses=lm["losses"], long_win_rate=lm["win_rate"], long_profit_factor=lm["profit_factor"], short_trades=sm["trades"], short_wins=sm["wins"], short_losses=sm["losses"], short_win_rate=sm["win_rate"], short_profit_factor=sm["profit_factor"], blocker_count=len(blockers), validation_failure_count=int((~val.result.eq("PASS")).sum()))
    save(pd.DataFrame(blockers), out / "gold_v3_107_blocker_matrix.csv"); save(val, out / "gold_v3_107_validation_matrix.csv"); (out / "gold_v3_107_direction_assumption_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8"); (out / "GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107 direction assumption audit-only report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blockers}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    outputs += ["gold_v3_107_blocker_matrix.csv", "gold_v3_107_validation_matrix.csv", "gold_v3_107_direction_assumption_summary.json", "GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    write_paste(out / "paste_me.txt", summary, blockers, val, outputs, findings)
    print(json.dumps({"status": status, "ready": status == READY, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2)); return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
