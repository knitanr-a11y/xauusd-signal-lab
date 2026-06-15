#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_119_JUNE_CURRENT_PERIOD_BACKTEST_AUDIT_ONLY"
READY = STEP + "_READY"
BLOCKED = STEP + "_BLOCKED"

START = pd.Timestamp("2026-06-01")
END = pd.Timestamp("2026-07-01")


def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    if "entry_dt" in df.columns:
        df["entry_dt"] = pd.to_datetime(df["entry_dt"], errors="coerce")
    if "exit_dt" in df.columns:
        df["exit_dt"] = pd.to_datetime(df["exit_dt"], errors="coerce")
    if "result_usd" in df.columns:
        df["result_usd"] = pd.to_numeric(df["result_usd"], errors="coerce")
    return df


def june(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "entry_dt" not in df.columns:
        return pd.DataFrame()
    x = df[df["entry_dt"].notna()].copy()
    return x[(x["entry_dt"] >= START) & (x["entry_dt"] < END)].copy()


def pf(s) -> float:
    x = pd.to_numeric(s, errors="coerce").dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    if gl > 0:
        return gp / gl
    return math.inf if gp > 0 else 0.0


def dedup(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    keys = [c for c in ["entry_dt", "side", "profile_id", "candidate_key", "global_candidate_key"] if c in df.columns]
    if not keys:
        return df.drop_duplicates().copy()
    return df.sort_values(keys).drop_duplicates(keys, keep="last").copy()


def resolved(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    x = df.copy()
    if "result_usd" in x.columns:
        x = x[x["result_usd"].notna()].copy()
    if "exit_dt" in x.columns:
        x = x[x["exit_dt"].notna()].copy()
    return x


def metrics(name: str, df: pd.DataFrame, note: str, live_valid: bool) -> dict:
    x = resolved(df)
    r = pd.to_numeric(x.get("result_usd", pd.Series(dtype=float)), errors="coerce").dropna()
    trades = int(len(r))
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    out = {
        "bucket": name,
        "note": note,
        "live_valid": bool(live_valid),
        "rows_before_resolved_filter": int(len(df)),
        "resolved_trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate": float((r > 0).mean()) if trades else 0.0,
        "profit_factor": pf(r),
        "sum_result_usd": float(r.sum()) if trades else 0.0,
        "min_entry_dt": str(x["entry_dt"].min()) if trades and "entry_dt" in x.columns else "",
        "max_entry_dt": str(x["entry_dt"].max()) if trades and "entry_dt" in x.columns else "",
    }
    if trades and "side" in x.columns:
        out["long_trades"] = int((x["side"].astype(str).str.upper() == "LONG").sum())
        out["short_trades"] = int((x["side"].astype(str).str.upper() == "SHORT").sum())
    else:
        out["long_trades"] = 0
        out["short_trades"] = 0
    return out


def side_metrics(df: pd.DataFrame, bucket: str) -> pd.DataFrame:
    x = resolved(df)
    if x.empty or "side" not in x.columns:
        return pd.DataFrame()
    rows = []
    for side, g in x.groupby(x["side"].astype(str).str.upper()):
        m = metrics(bucket + "|" + side, g, "direction split", False)
        m["side"] = side
        rows.append(m)
    return pd.DataFrame(rows)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()

    root = gy.mt5_files_dir(args.mt5_files_dir) / "FX_OUTPUTS" / "gold_v3"
    out = root / "119"
    out.mkdir(parents=True, exist_ok=True)

    paths = {
        "selected_109c": root / "109c" / "gold_v3_109_selected_base_policy_ledger.csv",
        "shadow_117j_best": root / "117j" / "gold_v3_117j_shadow_107q_best_family_trade_ledger.csv",
        "upstream_107l": root / "107lc" / "gold_v3_107l_rehydrated_best_policy_ledger.csv",
        "removed_detail_117l": root / "117l" / "gold_v3_117l_june_filter_detail.csv",
    }
    blockers = []
    data = {}
    for k, p in paths.items():
        if not p.exists():
            blockers.append({"blocker_id": "missing_" + k, "path": str(p)})
            data[k] = pd.DataFrame()
        else:
            data[k] = load_csv(p)

    rows = []
    side_rows = []
    if not blockers:
        selected_june = june(data["selected_109c"])
        shadow_june = june(data["shadow_117j_best"])
        upstream_june = june(data["upstream_107l"])
        removed = data["removed_detail_117l"].copy()
        if "filter_removed" in removed.columns:
            removed_true = removed[removed["filter_removed"].astype(str).str.lower().isin(["true", "1", "yes"])].copy()
            kept_true = removed[~removed["filter_removed"].astype(str).str.lower().isin(["true", "1", "yes"])].copy()
        else:
            removed_true = pd.DataFrame()
            kept_true = removed.copy()

        rows.append(metrics("raw_107l_june", upstream_june, "107L upstream June rows before F002 selected exclusion", False))
        rows.append(metrics("dedup_107l_june", dedup(upstream_june), "deduplicated 107L upstream June rows", False))
        rows.append(metrics("health_gate_selected_109c_june", selected_june, "current selected policy after F002 exclusion", True))
        rows.append(metrics("shadow_117j_best_june", shadow_june, "shadow 107Q best family after F002 exclusion", True))
        rows.append(metrics("f002_removed_june_review_only", removed_true, "June rows removed by F002; review-only, not live policy", False))
        rows.append(metrics("f002_kept_june", kept_true, "June rows kept by F002", True))
        rows.append(metrics("restore_all_8_review_only", pd.concat([selected_june, removed_true], ignore_index=True, sort=False), "selected policy plus all removed June rows; review-only", False))
        rows.append(metrics("resolved_only_live_repro_selected_june", resolved(selected_june), "resolved-only view of current selected policy", True))

        save(upstream_june, out / "gold_v3_119_raw_107l_june_rows.csv")
        save(selected_june, out / "gold_v3_119_selected_109c_june_rows.csv")
        save(removed_true, out / "gold_v3_119_f002_removed_june_review_rows.csv")
        side_parts = [side_metrics(upstream_june, "raw_107l_june"), side_metrics(removed_true, "f002_removed_june_review_only"), side_metrics(selected_june, "selected_109c_june")]
        side_rows = [x for x in side_parts if not x.empty]

    comp = pd.DataFrame(rows)
    save(comp, out / "gold_v3_119_june_current_period_backtest_comparison.csv")
    side_df = pd.concat(side_rows, ignore_index=True, sort=False) if side_rows else pd.DataFrame()
    save(side_df, out / "gold_v3_119_june_direction_split.csv")

    status = READY if not blockers else BLOCKED
    summary = {
        "step": STEP,
        "status": status,
        "ready": status == READY,
        "decision": "JUNE_CURRENT_PERIOD_BACKTEST_AUDIT_READY" if status == READY else "JUNE_CURRENT_PERIOD_BACKTEST_AUDIT_BLOCKED",
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "output_dir": str(out),
        "period_start": str(START),
        "period_end_exclusive": str(END),
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "june_restore_auto_adopted": False,
        "review_only": True,
        "blocker_count": len(blockers),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    if not comp.empty:
        for _, r in comp.iterrows():
            if r["bucket"] in ["raw_107l_june", "health_gate_selected_109c_june", "restore_all_8_review_only"]:
                prefix = r["bucket"]
                summary[prefix + "_trades"] = int(r["resolved_trades"])
                summary[prefix + "_wr"] = float(r["win_rate"])
                summary[prefix + "_pf"] = float(r["profit_factor"])
                summary[prefix + "_sum"] = float(r["sum_result_usd"])

    write_json(out / "gold_v3_119_summary.json", summary | {"blockers": blockers})
    save(pd.DataFrame([summary]), out / "gold_v3_119_decision.csv")

    lines = ["GOLD V3 119 PASTE_ME_JUNE_CURRENT_PERIOD_BACKTEST_AUDIT"]
    lines += [f"{k}: {v}" for k, v in summary.items()]
    lines += ["", "COMPARISON", comp.to_string(index=False) if not comp.empty else "NO_ROWS"]
    lines += ["", "DIRECTION_SPLIT", side_df.to_string(index=False) if not side_df.empty else "NO_DIRECTION_ROWS"]
    lines += ["", "BLOCKERS", "NO_BLOCKERS" if not blockers else json.dumps(blockers, ensure_ascii=False)]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"status": status, "ready": status == READY, "decision": summary["decision"], "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
