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

STEP = "GOLD_V3_125_JUNE15_NO_TRADE_VS_STALE_SOURCE_AUDIT_ONLY"
READY = STEP + "_READY"
BLOCKED = STEP + "_BLOCKED"


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


def cov(path: Path, label: str) -> dict:
    row = {"label": label, "path": str(path), "exists": path.exists(), "rows": 0, "time_col": "", "min_dt": "", "max_dt": "", "error": ""}
    if not path.exists():
        row["error"] = "missing"
        return row
    try:
        df = pd.read_csv(path, sep=detect_sep(path), encoding="utf-8-sig", low_memory=False)
        row["rows"] = int(len(df))
        candidates = ["entry_dt", "exit_dt", "oos_max_entry_dt", "oos_min_entry_dt", "max_entry_dt", "time", "datetime", "date", "timestamp", "dt"]
        tcol = ""
        for c in candidates:
            if c in df.columns:
                tcol = c
                break
        if not tcol:
            for c in df.columns:
                cl = str(c).lower()
                if ("entry" in cl and "dt" in cl) or cl.endswith("time"):
                    tcol = c
                    break
        row["time_col"] = str(tcol)
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


def parse_dt(v: str) -> pd.Timestamp:
    return pd.to_datetime(v, errors="coerce")


def load(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, sep=detect_sep(path), encoding="utf-8-sig", low_memory=False)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    ap.add_argument("--target", default="2026-06-15")
    args = ap.parse_args()

    target = pd.Timestamp(args.target)
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    out = root / "125"
    out.mkdir(parents=True, exist_ok=True)

    paths = {
        "ohlc_m15_goldsharp": mt5 / "goldsharp_m15.csv",
        "ohlc_m15_gold_hash": mt5 / "gold#_m15.csv",
        "107h_input_coverage_from_107k2": root / "107k2c" / "gold_v3_107h_input_ledger_coverage.csv",
        "107h_feature_join_from_107k2": root / "107k2c" / "gold_v3_107h_feature_join_coverage.csv",
        "107k2_frontier": root / "107k2c" / "gold_v3_107k2_regime_frontier.csv",
        "107k2_best_policy_rows": root / "107k2c" / "gold_v3_107k2_best_policy_regime_rows.csv",
        "107k2_all_regime_ledgers": root / "107k2c" / "gold_v3_107k2_all_regime_ledgers.csv",
        "107l_best_policy_ledger": root / "107lc" / "gold_v3_107l_rehydrated_best_policy_ledger.csv",
        "119_summary": root / "119" / "gold_v3_119_summary.json",
    }

    rows = []
    for label, path in paths.items():
        if path.suffix.lower() == ".json":
            rows.append({"label": label, "path": str(path), "exists": path.exists(), "rows": 0, "time_col": "", "min_dt": "", "max_dt": "", "error": "json_not_scanned"})
        else:
            rows.append(cov(path, label))
    coverage = pd.DataFrame(rows)
    save(coverage, out / "gold_v3_125_key_coverage.csv")

    input_cov_path = paths["107h_input_coverage_from_107k2"]
    input_cov = load(input_cov_path)
    if not input_cov.empty:
        for c in input_cov.columns:
            if c.lower() in ["path", "source_name", "exists", "rows", "error"]:
                continue
        save(input_cov, out / "gold_v3_125_107h_input_coverage_copy.csv")

    best_rows = load(paths["107k2_best_policy_rows"])
    if not best_rows.empty:
        save(best_rows, out / "gold_v3_125_107k2_best_policy_rows_copy.csv")

    all_max = parse_dt(coverage.loc[coverage.label == "107k2_all_regime_ledgers", "max_dt"].iloc[0])
    l_max = parse_dt(coverage.loc[coverage.label == "107l_best_policy_ledger", "max_dt"].iloc[0])
    ohlc_maxes = [parse_dt(x) for x in coverage[coverage.label.astype(str).str.startswith("ohlc_m15")]["max_dt"].tolist()]
    ohlc_max = max([x for x in ohlc_maxes if pd.notna(x)], default=pd.NaT)

    highvol_max = pd.NaT
    highvol_trades = 0
    best_policy_key = ""
    if not best_rows.empty:
        if "policy_key" in best_rows.columns and len(best_rows):
            best_policy_key = str(best_rows.iloc[0].get("policy_key", ""))
        hv = best_rows[best_rows.get("regime_group", pd.Series(dtype=str)).astype(str).str.contains("HIGHVOL", case=False, na=False)].copy()
        if not hv.empty:
            col = "oos_max_entry_dt" if "oos_max_entry_dt" in hv.columns else "max_entry_dt" if "max_entry_dt" in hv.columns else ""
            if col:
                highvol_max = pd.to_datetime(hv[col], errors="coerce").max()
            if "oos_trades" in hv.columns:
                highvol_trades = int(pd.to_numeric(hv["oos_trades"], errors="coerce").fillna(0).sum())

    blockers = []
    if pd.isna(ohlc_max) or ohlc_max < target:
        decision = "OHLC_SOURCE_STALE_UPDATE_CSV_FIRST"
        blockers.append({"blocker_id": "ohlc_does_not_reach_target", "observed": str(ohlc_max), "required": str(target)})
    elif pd.isna(all_max) or all_max < target:
        decision = "CANDIDATE_LEDGER_SOURCE_STALE_BEFORE_TARGET"
        blockers.append({"blocker_id": "107k2_all_regime_ledgers_do_not_reach_target", "observed": str(all_max), "required": str(target), "action": "rebuild the upstream candidate ledger chain before 107K2"})
    elif pd.notna(l_max) and l_max < target:
        decision = "BEST_POLICY_VALID_NO_TRADE_AFTER_LAST_107L_ENTRY"
    else:
        decision = "BEST_POLICY_LEDGER_REACHES_TARGET_RERUN_119"

    status = READY if not blockers else BLOCKED
    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": decision,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "target": str(target),
        "ohlc_m15_max_dt": str(ohlc_max) if pd.notna(ohlc_max) else "",
        "107k2_all_regime_ledgers_max_dt": str(all_max) if pd.notna(all_max) else "",
        "107l_best_policy_ledger_max_dt": str(l_max) if pd.notna(l_max) else "",
        "107k2_best_policy_key": best_policy_key,
        "107k2_highvol_best_oos_max_entry_dt": str(highvol_max) if pd.notna(highvol_max) else "",
        "107k2_highvol_best_oos_trades": highvol_trades,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "review_only": True,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    write_json(out / "gold_v3_125_summary.json", summary | {"blockers": blockers})
    save(pd.DataFrame([summary]), out / "gold_v3_125_decision.csv")

    lines = ["GOLD V3 125 PASTE_ME_JUNE15_NO_TRADE_VS_STALE_SOURCE_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "KEY_COVERAGE", coverage.to_string(index=False)]
    lines += ["", "107H_INPUT_COVERAGE_FROM_107K2", input_cov.to_string(index=False) if not input_cov.empty else "NO_INPUT_COVERAGE_ROWS"]
    lines += ["", "107K2_BEST_POLICY_ROWS", best_rows.to_string(index=False) if not best_rows.empty else "NO_BEST_POLICY_ROWS"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
