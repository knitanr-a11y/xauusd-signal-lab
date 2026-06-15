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

STEP = "GOLD_V3_128_JUNE_PERIOD_AUDIT_NO_TRADE_AWARE_AUDIT_ONLY"
READY = STEP + "_READY"
BLOCKED = STEP + "_BLOCKED"


def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def pf(vals) -> float:
    a = pd.to_numeric(pd.Series(vals), errors="coerce").dropna().astype(float)
    if a.empty:
        return 0.0
    gp = float(a[a > 0].sum())
    gl = float(-a[a < 0].sum())
    return gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)


def metrics(df: pd.DataFrame) -> dict:
    if df is None or df.empty or "result_usd" not in df.columns:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, negative_month_count=0, min_entry_dt="", max_entry_dt="", unique_trade_days=0)
    x = df.copy()
    x["entry_dt"] = pd.to_datetime(x["entry_dt"], errors="coerce")
    x["result_usd"] = pd.to_numeric(x["result_usd"], errors="coerce")
    x = x[x.entry_dt.notna() & x.result_usd.notna()].copy()
    if x.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, negative_month_count=0, min_entry_dt="", max_entry_dt="", unique_trade_days=0)
    mon = x.groupby(x.entry_dt.dt.to_period("M").astype(str))["result_usd"].sum()
    return dict(
        trades=int(len(x)),
        wins=int((x.result_usd > 0).sum()),
        losses=int((x.result_usd < 0).sum()),
        win_rate=float((x.result_usd > 0).mean()),
        profit_factor=pf(x.result_usd),
        sum_result_usd=float(x.result_usd.sum()),
        negative_month_count=int((mon < 0).sum()),
        min_entry_dt=str(x.entry_dt.min()),
        max_entry_dt=str(x.entry_dt.max()),
        unique_trade_days=int(x.entry_dt.dt.date.nunique()),
    )


def max_entry(df: pd.DataFrame, col: str = "entry_dt") -> pd.Timestamp:
    if df.empty or col not in df.columns:
        return pd.NaT
    return pd.to_datetime(df[col], errors="coerce").max()


def bools(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def select_best_policy(bal: pd.DataFrame) -> str:
    if bal.empty or "policy_key" not in bal.columns:
        return ""
    b = bal.copy()
    for c in ["all_regime_pass_65", "all_regime_pass_60"]:
        if c in b.columns:
            b[c] = bools(b[c])
        else:
            b[c] = False
    if "balanced_score" not in b.columns:
        b["balanced_score"] = 0.0
    b["balanced_score"] = pd.to_numeric(b["balanced_score"], errors="coerce").fillna(0.0)
    b = b.sort_values(["all_regime_pass_65", "all_regime_pass_60", "balanced_score"], ascending=[False, False, False])
    return str(b.iloc[0].policy_key)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--start", default="2026-06-01")
    ap.add_argument("--end-exclusive", default="2026-06-16")
    ap.add_argument("--require-min-upstream-max-entry-dt", default="2026-06-15")
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "128"
    out.mkdir(parents=True, exist_ok=True)

    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end_exclusive)
    required = pd.Timestamp(args.require_min_upstream_max_entry_dt) if args.require_min_upstream_max_entry_dt else pd.NaT

    bal_path = root / "107k2c" / "gold_v3_107k2_balanced_policy_summary.csv"
    all_path = root / "107k2c" / "gold_v3_107k2_all_regime_ledgers.csv"
    best_rows_path = root / "107k2c" / "gold_v3_107k2_best_policy_regime_rows.csv"
    gu_path = root / "107guc" / "gold_v3_107gu_selected_candidate_keys.csv"

    bal = load_csv(bal_path)
    all_led = load_csv(all_path)
    best_rows = load_csv(best_rows_path)
    gu = load_csv(gu_path)

    blockers = []
    for label, path, df in [("107k2_balanced_policy_summary", bal_path, bal), ("107k2_all_regime_ledgers", all_path, all_led)]:
        if not path.exists() or df.empty:
            blockers.append({"blocker_id": "missing_or_empty_required_input", "label": label, "path": str(path)})

    best_key = select_best_policy(bal)
    if not best_key:
        blockers.append({"blocker_id": "best_policy_key_not_found", "path": str(bal_path)})

    upstream_max = max_entry(all_led, "entry_dt")
    if pd.notna(required) and (pd.isna(upstream_max) or upstream_max < required):
        blockers.append({"blocker_id": "upstream_107k2_all_regime_ledgers_do_not_reach_required_target", "observed_max_entry_dt": str(upstream_max) if pd.notna(upstream_max) else "", "required_min_entry_dt": str(required)})

    selected = pd.DataFrame()
    period = pd.DataFrame()
    if not blockers:
        all_led["entry_dt"] = pd.to_datetime(all_led["entry_dt"], errors="coerce")
        selected = all_led[all_led.policy_key.astype(str) == best_key].copy()
        period = selected[(selected.entry_dt >= start) & (selected.entry_dt < end)].copy()
        save(selected, out / "gold_v3_128_selected_best_policy_ledger_from_107k2.csv")
        save(period, out / "gold_v3_128_selected_best_policy_period_rows.csv")

    m = metrics(period)
    direction = pd.DataFrame()
    if not period.empty and "side" in period.columns:
        rows = []
        for side, g in period.groupby(period.side.astype(str)):
            rows.append(dict(side=side, **metrics(g)))
        direction = pd.DataFrame(rows)
    save(direction, out / "gold_v3_128_direction_split.csv")

    no_trade_after_last = False
    selected_max = max_entry(selected, "entry_dt") if not selected.empty else pd.NaT
    if not blockers and (period.empty or (pd.notna(selected_max) and selected_max < required)) and pd.notna(upstream_max) and upstream_max >= required:
        no_trade_after_last = True

    status = READY if not blockers else BLOCKED
    decision = "PERIOD_AUDIT_READY_NO_TRADE_AWARE" if status == READY else "PERIOD_AUDIT_BLOCKED_UPSTREAM_COVERAGE"
    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "period_start": str(start),
        "period_end_exclusive": str(end),
        "required_min_upstream_max_entry_dt": str(required) if pd.notna(required) else "",
        "coverage_basis": "107K2 all_regime_ledgers max entry_dt, not selected trade ledger max; selected ledger may legitimately have no trades after its last entry",
        "observed_107k2_all_regime_ledgers_max_entry_dt": str(upstream_max) if pd.notna(upstream_max) else "",
        "selected_best_policy_key": best_key,
        "selected_best_policy_max_entry_dt": str(selected_max) if pd.notna(selected_max) else "",
        "period_no_trade_after_last_selected_entry": bool(no_trade_after_last),
        **{f"period_{k}": v for k, v in m.items()},
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "period_restore_auto_adopted": False,
        "review_only": True,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }

    write_json(out / "gold_v3_128_summary.json", summary | {"blockers": blockers})
    save(pd.DataFrame([summary]), out / "gold_v3_128_decision.csv")

    lines = ["GOLD V3 128 PASTE_ME_JUNE_PERIOD_AUDIT_NO_TRADE_AWARE"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "BEST_POLICY_REGIME_ROWS", best_rows.to_string(index=False) if not best_rows.empty else "NO_BEST_POLICY_REGIME_ROWS"]
    lines += ["", "DIRECTION_SPLIT", direction.to_string(index=False) if not direction.empty else "NO_DIRECTION_ROWS"]
    lines += ["", "PERIOD_ROWS_HEAD", period.head(50).to_string(index=False) if not period.empty else "NO_PERIOD_ROWS"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
