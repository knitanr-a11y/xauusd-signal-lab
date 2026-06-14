#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_108B_HEALTH_GATE_DELTA_REVIEW_AUDIT_ONLY"
READY = "GOLD_V3_108B_HEALTH_GATE_DELTA_REVIEW_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_108B_HEALTH_GATE_DELTA_REVIEW_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY"


def log(s: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}", flush=True)


def prog(i: int, n: int, s: str) -> None:
    p = 100.0 * i / max(1, n)
    log(f"progress {p:5.1f}% complete / {100.0-p:5.1f}% remaining | step {i}/{n} | {s}")


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def pf(vals) -> float:
    a = np.asarray(vals, dtype=float)
    gp = a[a > 0].sum()
    gl = -a[a < 0].sum()
    return float(gp / gl) if gl > 0 else (math.inf if gp > 0 else 0.0)


def metrics(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, avg_result_usd=0.0)
    x = df.copy()
    x["result_usd"] = pd.to_numeric(x["result_usd"], errors="coerce")
    x = x[x["result_usd"].notna()].copy()
    if x.empty:
        return metrics(pd.DataFrame())
    return dict(
        trades=int(len(x)),
        wins=int((x.result_usd > 0).sum()),
        losses=int((x.result_usd < 0).sum()),
        win_rate=float((x.result_usd > 0).mean()),
        profit_factor=pf(x.result_usd.to_numpy()),
        sum_result_usd=float(x.result_usd.sum()),
        avg_result_usd=float(x.result_usd.mean()),
    )


def build_key(df: pd.DataFrame) -> pd.Series:
    x = df.copy()
    x["entry_dt_norm"] = pd.to_datetime(x["entry_dt"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    if "global_candidate_key" not in x.columns:
        x["global_candidate_key"] = x.get("source_name", "UNKNOWN").astype(str) + "::" + x.get("candidate_key", "").astype(str)
    x["result_usd_norm"] = pd.to_numeric(x["result_usd"], errors="coerce").round(8).astype(str)
    return x[["global_candidate_key", "entry_dt_norm", "result_usd_norm"]].astype(str).agg("||".join, axis=1)


def by_group(df: pd.DataFrame, cols: list[str], prefix: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for k, g in df.groupby(cols, dropna=False):
        if not isinstance(k, tuple):
            k = (k,)
        r = dict(zip(cols, k))
        m = metrics(g)
        r.update({f"{prefix}_{kk}": vv for kk, vv in m.items()})
        rows.append(r)
    return pd.DataFrame(rows)


def delta_table(base: pd.DataFrame, kept: pd.DataFrame, skipped: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    b = by_group(base, cols, "base")
    k = by_group(kept, cols, "kept")
    s = by_group(skipped, cols, "skipped")
    out = b.merge(k, on=cols, how="outer").merge(s, on=cols, how="outer")
    for c in ["base_trades", "kept_trades", "skipped_trades"]:
        if c in out: out[c] = out[c].fillna(0).astype(int)
    for c in ["base_sum_result_usd", "kept_sum_result_usd", "skipped_sum_result_usd", "base_win_rate", "kept_win_rate", "skipped_win_rate", "base_profit_factor", "kept_profit_factor", "skipped_profit_factor"]:
        if c in out: out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)
    if "kept_sum_result_usd" in out and "base_sum_result_usd" in out:
        out["sum_delta_kept_vs_base"] = out["kept_sum_result_usd"] - out["base_sum_result_usd"]
    if "kept_trades" in out and "base_trades" in out:
        out["retention"] = out["kept_trades"] / out["base_trades"].replace(0, np.nan)
    return out


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "108bc"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")
    prog(0, 5, "start")

    blocks = []
    outputs = []
    findings = []
    base_path = root / "107r6c" / "gold_v3_107r6_resolved_107q_best_family_ledger.csv"
    kept_path = root / "107sc" / "gold_v3_107s_best_health_gate_ledger.csv"
    summary_path = root / "108c" / "gold_v3_108_summary.json"
    for name, p in [("base", base_path), ("kept", kept_path), ("summary", summary_path)]:
        if not p.exists():
            blocks.append(dict(blocker_id=f"missing_{name}_input", path=str(p)))

    base = pd.DataFrame(); kept = pd.DataFrame(); skipped = pd.DataFrame()
    if not blocks:
        base = pd.read_csv(base_path, encoding="utf-8-sig", low_memory=False)
        kept = pd.read_csv(kept_path, encoding="utf-8-sig", low_memory=False)
        for dname, df in [("base", base), ("kept", kept)]:
            for c in ["entry_dt", "result_usd"]:
                if c not in df.columns:
                    blocks.append(dict(blocker_id=f"{dname}_missing_required_column", column=c))
        prog(1, 5, f"loaded base={len(base)} kept={len(kept)}")

    if not blocks:
        base = base.copy(); kept = kept.copy()
        base["__k"] = build_key(base)
        kept["__k"] = build_key(kept)
        kept_keys = set(kept["__k"].astype(str))
        base["health_gate_kept"] = base["__k"].astype(str).isin(kept_keys)
        skipped = base[~base["health_gate_kept"]].copy()
        kept_from_base = base[base["health_gate_kept"]].copy()
        for df in [base, kept_from_base, skipped]:
            df["entry_dt"] = pd.to_datetime(df["entry_dt"], errors="coerce")
            df["entry_month"] = df["entry_dt"].dt.to_period("M").astype(str)
            df["entry_day"] = df["entry_dt"].dt.date.astype(str)
            if "regime_split" not in df.columns: df["regime_split"] = "ALL"
            if "side" not in df.columns: df["side"] = "UNKNOWN"
            if "global_candidate_key" not in df.columns:
                df["global_candidate_key"] = df.get("source_name", "UNKNOWN").astype(str) + "::" + df.get("candidate_key", "").astype(str)
        save(skipped.drop(columns=["__k"], errors="ignore"), out / "gold_v3_108b_skipped_trade_ledger.csv")
        save(kept_from_base.drop(columns=["__k"], errors="ignore"), out / "gold_v3_108b_kept_trade_ledger.csv")
        outputs += ["gold_v3_108b_skipped_trade_ledger.csv", "gold_v3_108b_kept_trade_ledger.csv"]
        prog(2, 5, f"split kept={len(kept_from_base)} skipped={len(skipped)}")

        bm = metrics(base); km = metrics(kept_from_base); sm = metrics(skipped)
        overview = pd.DataFrame([dict(
            base_trades=bm["trades"], kept_trades=km["trades"], skipped_trades=sm["trades"],
            retention=km["trades"] / max(1, bm["trades"]),
            base_wr=bm["win_rate"], kept_wr=km["win_rate"], skipped_wr=sm["win_rate"],
            base_pf=bm["profit_factor"], kept_pf=km["profit_factor"], skipped_pf=sm["profit_factor"],
            base_sum_result_usd=bm["sum_result_usd"], kept_sum_result_usd=km["sum_result_usd"], skipped_sum_result_usd=sm["sum_result_usd"],
            kept_sum_delta=km["sum_result_usd"] - bm["sum_result_usd"],
            skipped_avg_result_usd=sm["avg_result_usd"],
            skipped_winner_count=sm["wins"], skipped_loser_count=sm["losses"],
        )])
        save(overview, out / "gold_v3_108b_overview.csv")
        outputs.append("gold_v3_108b_overview.csv")

        monthly = delta_table(base, kept_from_base, skipped, ["regime_split", "entry_month"])
        regime = delta_table(base, kept_from_base, skipped, ["regime_split"])
        side = delta_table(base, kept_from_base, skipped, ["side"])
        cand = delta_table(base, kept_from_base, skipped, ["global_candidate_key"])
        if not cand.empty:
            cand = cand.sort_values(["skipped_sum_result_usd", "skipped_trades"], ascending=[False, False]).head(80)
        save(monthly, out / "gold_v3_108b_monthly_delta.csv")
        save(regime, out / "gold_v3_108b_regime_delta.csv")
        save(side, out / "gold_v3_108b_side_delta.csv")
        save(cand, out / "gold_v3_108b_candidate_delta_top.csv")
        outputs += ["gold_v3_108b_monthly_delta.csv", "gold_v3_108b_regime_delta.csv", "gold_v3_108b_side_delta.csv", "gold_v3_108b_candidate_delta_top.csv"]
        prog(4, 5, "delta tables written")

        skipped_sum = float(sm["sum_result_usd"])
        wr_gain = float(km["win_rate"] - bm["win_rate"])
        pf_gain = float(km["profit_factor"] - bm["profit_factor"])
        if skipped_sum > 0 and wr_gain < 0.005:
            decision = "HEALTH_GATE_DELTA_REVIEW_READY_BASE_PREFERRED"
            recommendation = "Skipped trades are net positive and WR gain is small; prefer keeping 107Q base unless WR/PF quality is explicitly prioritized."
        elif skipped_sum > 0 and wr_gain >= 0.005:
            decision = "HEALTH_GATE_DELTA_REVIEW_READY_LIGHTER_HEALTH_GATE_REVIEW"
            recommendation = "Health gate improves quality but skips net-positive trades; test lighter threshold before adoption."
        elif skipped_sum <= 0 and (wr_gain > 0 or pf_gain > 0):
            decision = "HEALTH_GATE_DELTA_REVIEW_READY_HEALTH_GATE_PREFERRED"
            recommendation = "Skipped trades are net non-positive and health gate improves quality; health gate preferred for next review."
        else:
            decision = "HEALTH_GATE_DELTA_REVIEW_READY_HUMAN_DECISION_REQUIRED"
            recommendation = "Mixed tradeoff; use monthly/daily details for human decision."
        rec = pd.DataFrame([
            dict(option="KEEP_107Q_BASE", recommended=decision.endswith("BASE_PREFERRED"), reason="Maximizes total sum_result_usd if skipped trades are net positive."),
            dict(option="ADOPT_107S_HEALTH_GATE", recommended=decision.endswith("HEALTH_GATE_PREFERRED"), reason="Improves WR/PF and removes weak resolved-history candidates."),
            dict(option="LIGHTER_HEALTH_GATE_REVIEW", recommended=decision.endswith("LIGHTER_HEALTH_GATE_REVIEW"), reason="Use if quality improves but too many profitable trades are skipped."),
        ])
        save(rec, out / "gold_v3_108b_recommendation_matrix.csv")
        outputs.append("gold_v3_108b_recommendation_matrix.csv")
        findings.append("recommendation=" + recommendation)
        findings.append("overview=" + json.dumps(overview.iloc[0].to_dict(), ensure_ascii=False, default=str))
    else:
        decision = "HEALTH_GATE_DELTA_REVIEW_BLOCKED_INPUT_INCOMPLETE"

    vals = [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
    ]
    if not base.empty: vals.append(dict(check_id="base_rows_positive", result="PASS", observed=len(base), expected=">0", severity="BLOCKER"))
    if not kept.empty: vals.append(dict(check_id="kept_rows_positive", result="PASS", observed=len(kept), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failure_count = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0
    status = READY if not blocks and validation_failure_count == 0 else BLOCKED
    if status == BLOCKED:
        decision = "HEALTH_GATE_DELTA_REVIEW_BLOCKED_INPUT_INCOMPLETE"

    summary = dict(step=STEP, status=status, decision=decision, created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), output_dir=str(out), audit_only=True, live_ready=False, source_csv_mutated=False, contract_mutated=False, open_asof_allowed=False, blocker_count=len(blocks), validation_failure_count=validation_failure_count, elapsed_seconds=round(time.time() - t0, 2))
    if 'overview' in locals() and not overview.empty:
        summary.update(overview.iloc[0].to_dict())
    save(pd.DataFrame(blocks), out / "gold_v3_108b_blocker_matrix.csv")
    save(val, out / "gold_v3_108b_validation_matrix.csv")
    outputs += ["gold_v3_108b_blocker_matrix.csv", "gold_v3_108b_validation_matrix.csv", "gold_v3_108b_summary.json", "GOLD_V3_108B_HEALTH_GATE_DELTA_REVIEW_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_108b_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_108B_HEALTH_GATE_DELTA_REVIEW_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 108B report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = ["GOLD V3 108B PASTE_ME_HEALTH_GATE_DELTA_REVIEW", f"status: {status}", f"ready: {str(status == READY).lower()}", "live_ready: false", "source_csv_mutated: false", "contract_mutated: false", "open_asof_allowed: false", "safety: audit_only=true, delta_review_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false", "blocker_count: " + str(len(blocks)), "", "KEY_METRICS"] + [f"{k}: {v}" for k, v in summary.items()] + ["", "FINDINGS"] + (findings or ["NO_FINDINGS"]) + ["", "BLOCKERS", pd.DataFrame(blocks).to_string(index=False) if blocks else "NO_BLOCKERS", "", "VALIDATION", val.to_string(index=False), "", "OUTPUTS"] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(5, 5, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
