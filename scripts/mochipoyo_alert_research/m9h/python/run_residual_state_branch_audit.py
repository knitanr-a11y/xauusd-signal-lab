from __future__ import annotations

import csv
import json
import os
import shutil
import statistics
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED = 852


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fnum(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def pf(values: list[float]) -> float | None:
    wins = sum(x for x in values if x > 0)
    losses = abs(sum(x for x in values if x < 0))
    return None if losses == 0 else wins / losses


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda r: r["turn_entry_time"])
    vals = [float(r["return_from_first_turn_bps"]) for r in ordered]
    if not vals:
        return {"count": 0, "win_rate": None, "profit_factor_bps": None, "net_bps": 0.0, "mean_bps": None, "median_bps": None, "max_drawdown_bps": 0.0, "max_losing_streak": 0}
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    streak = 0
    max_streak = 0
    for value in vals:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "count": len(vals),
        "win_rate": sum(x > 0 for x in vals) / len(vals),
        "profit_factor_bps": pf(vals),
        "net_bps": sum(vals),
        "mean_bps": statistics.fmean(vals),
        "median_bps": statistics.median(vals),
        "max_drawdown_bps": max_dd,
        "max_losing_streak": max_streak,
    }


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    m9d = local_root / "outputs" / "M9D" / "LATEST" / "04_first_turn_rich_feature_panel.csv"
    m9f = local_root / "outputs" / "M9F" / "LATEST" / "03_decision_recency_panel.csv"
    if not m9d.is_file() or not m9f.is_file():
        print("[M9H BLOCKED] M9D/M9F LATEST input is missing")
        return 2

    rich = read_csv(m9d)
    panel = [r for r in read_csv(m9f) if r.get("panel_kind") == "FIRST_TURN"]
    if len(rich) != EXPECTED or len(panel) != EXPECTED:
        print(f"[M9H BLOCKED] expected {EXPECTED} first-turn rows; rich={len(rich)} panel={len(panel)}")
        return 2

    panel_by_id = {r["proxy_trade_id"]: r for r in panel}
    if len(panel_by_id) != EXPECTED:
        print("[M9H BLOCKED] duplicate/missing proxy_trade_id in M9F first-turn panel")
        return 2

    rows: list[dict[str, Any]] = []
    for r in rich:
        p = panel_by_id.get(r["proxy_trade_id"])
        if p is None:
            print(f"[M9H BLOCKED] M9F row missing for {r['proxy_trade_id']}")
            return 2
        row = dict(r)
        row.update({
            "within_3_bars_signature": p.get("within_3_bars_signature", ""),
            "within_3_bars_supportive_hidden_count": p.get("within_3_bars_supportive_hidden_count", "0"),
            "month": p.get("month", ""),
        })
        p1 = row["ticker"] == "BTCUSD" and row["direction"] == "LONG" and row["within_3_bars_signature"] == "BOTH"
        p2_short = row["ticker"] == "BTCUSD" and row["direction"] == "SHORT" and row["within_3_bars_signature"] == "SUPPORTIVE_ONLY" and float(row["within_3_bars_supportive_hidden_count"] or 0) > 0
        row["p2_keep"] = not (p1 or p2_short)
        row["state_btc_long_high_m15_range"] = bool(row["p2_keep"] and row["ticker"] == "BTCUSD" and row["direction"] == "LONG" and (fnum(row.get("turnrich_m15_bar_range_atr")) or -999) >= 1.0)
        row["state_xau_long_h1_rci9_extreme"] = bool(row["p2_keep"] and row["ticker"] == "XAUUSD" and row["direction"] == "LONG" and (fnum(row.get("turn_h1_directional_rci9")) or -999) >= 80.0)
        xau_short_rci = fnum(row.get("turnrich_m1_rci18"))
        row["state_xau_short_m1_rci18_extreme"] = bool(row["p2_keep"] and row["ticker"] == "XAUUSD" and row["direction"] == "SHORT" and xau_short_rci is not None and xau_short_rci <= -80.0)
        rows.append(row)

    policies = {
        "H0_P2_BASELINE": lambda r: bool(r["p2_keep"]),
        "H1_P2_PLUS_BTC_LONG_HIGH_M15_RANGE": lambda r: bool(r["p2_keep"]) and not r["state_btc_long_high_m15_range"],
        "H2_H1_PLUS_XAU_LONG_H1_RCI9_EXTREME": lambda r: bool(r["p2_keep"]) and not r["state_btc_long_high_m15_range"] and not r["state_xau_long_h1_rci9_extreme"],
        "H3_H2_PLUS_XAU_SHORT_M1_RCI18_EXTREME": lambda r: bool(r["p2_keep"]) and not r["state_btc_long_high_m15_range"] and not r["state_xau_long_h1_rci9_extreme"] and not r["state_xau_short_m1_rci18_extreme"],
    }

    policy_summary: list[dict[str, Any]] = []
    monthly: list[dict[str, Any]] = []
    branch: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for pid, keep_fn in policies.items():
        kept = [r for r in rows if keep_fn(r)]
        rej = [r for r in rows if bool(r["p2_keep"]) and not keep_fn(r)]
        km = metrics(kept)
        rm = metrics(rej)
        policy_summary.append({"policy_id": pid, "retention_fraction_vs_852": len(kept) / EXPECTED, **{f"accepted_{k}": v for k, v in km.items()}, **{f"rejected_{k}": v for k, v in rm.items()}})
        for month in sorted({r["month"] for r in kept}):
            group = [r for r in kept if r["month"] == month]
            monthly.append({"policy_id": pid, "month": month, **metrics(group)})
        for ticker, direction in sorted({(r["ticker"], r["direction"]) for r in kept}):
            group = [r for r in kept if r["ticker"] == ticker and r["direction"] == direction]
            branch.append({"policy_id": pid, "ticker": ticker, "direction": direction, **metrics(group)})
        if pid != "H0_P2_BASELINE":
            for r in rej:
                rejected.append({
                    "policy_id": pid,
                    "proxy_trade_id": r["proxy_trade_id"],
                    "ticker": r["ticker"],
                    "direction": r["direction"],
                    "turn_entry_time": r["turn_entry_time"],
                    "return_from_first_turn_bps": r["return_from_first_turn_bps"],
                    "state_btc_long_high_m15_range": r["state_btc_long_high_m15_range"],
                    "state_xau_long_h1_rci9_extreme": r["state_xau_long_h1_rci9_extreme"],
                    "state_xau_short_m1_rci18_extreme": r["state_xau_short_m1_rci18_extreme"],
                })

    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M9H_RESIDUAL_STATE_BRANCH_AUDIT",
        "status": "PASS_EXPLORATORY_ONLY",
        "run_at_utc": built,
        "population_tier": "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH",
        "first_turn_population": EXPECTED,
        "p2_forward_candidate": False,
        "policy_count": len(policies),
        "thresholds_optimized_in_run": False,
        "same_sample_validation": False,
        "automatic_forward_promotion": False,
        "m7c_formula_changed": False,
        "m7c_threshold_changed": False,
        "m8c_reset": False,
    }

    out_root = local_root / "outputs" / "M9H"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    (archive / "00_READ_ME_FIRST.txt").write_text("M9H is exploratory only. P2 is rejected as a forward candidate. H1-H3 use frozen natural state anchors and must not be treated as validation.\n", encoding="utf-8")
    dump_json(archive / "01_summary.json", summary)
    write_csv(archive / "02_policy_summary.csv", policy_summary)
    write_csv(archive / "03_monthly_policy_summary.csv", monthly)
    write_csv(archive / "04_ticker_direction_summary.csv", branch)
    write_csv(archive / "05_rejected_trade_detail.csv", rejected)
    (archive / "06_audit.log").write_text(f"status=PASS_EXPLORATORY_ONLY\nfirst_turn_population={EXPECTED}\npolicy_count={len(policies)}\np2_forward_candidate=false\nthresholds_optimized_in_run=false\nm7c_formula_changed=false\nm7c_threshold_changed=false\nm8c_reset=false\n", encoding="utf-8")
    names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_policy_summary.csv", "03_monthly_policy_summary.csv", "04_ticker_direction_summary.csv", "05_rejected_trade_detail.csv", "06_audit.log"]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)
    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    print(f"[M9H PASS] population={EXPECTED} policies={len(policies)}")
    print("[M9H OUTPUT]", latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
