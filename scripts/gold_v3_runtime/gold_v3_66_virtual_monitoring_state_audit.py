#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 66 virtual monitoring state audit-only.

Builds candidate-level virtual monitoring state from Stage51 opportunity ledger
and Stage65 M15 asof Q70 state.
No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_66_VIRTUAL_MONITORING_STATE_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_66_VIRTUAL_MONITORING_STATE_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_66_VIRTUAL_MONITORING_STATE_BLOCKED_AUDIT_ONLY"
STAGE65_READY = "GOLD_V3_65_ROLLING_PRIOR_60D_Q70_STATE_READY_AUDIT_ONLY"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "65_rolling_prior_60d_q70_state_audit_only").exists():
            return d
    raise FileNotFoundError("Stage65 output directory not found. Pass --candle-dir.")


def read_csv_auto(path: Path) -> tuple[pd.DataFrame, str]:
    attempts: list[tuple[str | None, str]] = [(None, "auto"), (";", "semicolon"), (",", "comma"), ("\t", "tab")]
    last_err: Exception | None = None
    for sep, label in attempts:
        try:
            if sep is None:
                df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
            else:
                df = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
            if len(df.columns) > 1:
                return df, label
        except Exception as e:
            last_err = e
    if last_err:
        raise last_err
    raise ValueError(f"Could not parse CSV with multiple columns: {path}")


def detect_time_column(df: pd.DataFrame) -> str:
    priority = ["m15_time", "entry_m15_time", "candidate_m15_time", "time", "datetime", "date", "timestamp", "entry_time"]
    lower = {str(c).lower(): str(c) for c in df.columns}
    for p in priority:
        if p in lower:
            return lower[p]
    candidates = []
    for c in df.columns:
        lc = str(c).lower()
        score = 0
        if "m15" in lc:
            score += 5
        if "time" in lc or "date" in lc or "timestamp" in lc:
            score += 5
        if score:
            candidates.append((score, str(c)))
    if candidates:
        return sorted(candidates, reverse=True)[0][1]
    return str(df.columns[0])


def parse_times(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    parsed = pd.to_datetime(s, errors="coerce")
    if parsed.notna().sum() == 0:
        parsed = pd.to_datetime(s.str.replace(".", "-", regex=False), errors="coerce")
    return parsed


def find_stage51_ledger(gold_v3_dir: Path) -> Path | None:
    candidates = []
    for p in gold_v3_dir.glob("51*/*virtual*opportunit*ledger*.csv"):
        candidates.append(p)
    for p in gold_v3_dir.glob("51*/*opportunit*ledger*.csv"):
        candidates.append(p)
    for p in gold_v3_dir.glob("**/gold_v3_51*opportunit*.csv"):
        candidates.append(p)
    candidates = [p for p in candidates if p.is_file()]
    if not candidates:
        return None
    # Prefer largest file with opportunity in name.
    candidates.sort(key=lambda p: (p.stat().st_size, str(p)), reverse=True)
    return candidates[0]


def build_candidate_key(df: pd.DataFrame) -> tuple[pd.Series, str]:
    cols = list(map(str, df.columns))
    lower = {c.lower(): c for c in cols}
    for c in ["candidate_key", "candidate_id", "rule_candidate_id", "strategy_id", "strategy_name", "candidate", "rule_id"]:
        if c in lower:
            col = lower[c]
            return df[col].astype(str), col
    pieces = []
    used = []
    for c in cols:
        lc = c.lower()
        if any(tok in lc for tok in ["rule", "profile", "candidate", "tp", "sl", "horizon", "family"]):
            pieces.append(df[c].astype(str))
            used.append(c)
    if pieces:
        key = pieces[0]
        for s in pieces[1:]:
            key = key + "|" + s
        return key, "+".join(used)
    return pd.Series(["single_candidate"] * len(df), index=df.index), "fallback_single_candidate"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage51-dir", default="")
    p.add_argument("--stage65-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    g = cdir / "FX_OUTPUTS" / "gold_v3"
    s65 = Path(a.stage65_dir).expanduser().resolve() if a.stage65_dir else g / "65_rolling_prior_60d_q70_state_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else g / "66_virtual_monitoring_state_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p65s = s65 / "gold_v3_65_q70_state_summary.json"
    p65m15 = s65 / "gold_v3_65_m15_asof_q70_state.csv"
    p51 = None
    if a.stage51_dir:
        s51 = Path(a.stage51_dir).expanduser().resolve()
        for pat in ["*virtual*opportunit*ledger*.csv", "*opportunit*ledger*.csv", "gold_v3_51*opportunit*.csv"]:
            found = list(s51.glob(pat))
            if found:
                p51 = sorted(found, key=lambda p: p.stat().st_size, reverse=True)[0]
                break
    if p51 is None:
        p51 = find_stage51_ledger(g)

    val: list[dict[str, Any]] = []
    val.append(ok("stage65_summary_present", p65s.exists(), str(p65s), "exists"))
    val.append(ok("stage65_m15_asof_q70_present", p65m15.exists(), str(p65m15), "exists"))
    val.append(ok("stage51_virtual_opportunity_ledger_present", p51 is not None and p51.exists(), str(p51) if p51 else "not_found", "exists"))
    if not p65s.exists() or not p65m15.exists() or p51 is None or not p51.exists():
        pd.DataFrame(val).to_csv(out / "gold_v3_66_validation_matrix.csv", index=False, encoding="utf-8-sig")
        raise SystemExit(1)

    j65 = read_json(p65s)
    val.append(ok("stage65_status_ready", j65.get("status") == STAGE65_READY, j65.get("status"), STAGE65_READY))
    val.append(ok("stage65_q70_ready", j65.get("rolling_prior_60d_q70_state_ready") is True, j65.get("rolling_prior_60d_q70_state_ready"), True))
    for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
        val.append(ok(f"stage65_{key}_false", j65.get(key) is False, j65.get(key), False))

    opp, opp_sep = read_csv_auto(p51)
    q70, q70_sep = read_csv_auto(p65m15)
    opp_time_col = detect_time_column(opp)
    q70_time_col = detect_time_column(q70)
    opp["_m15_time"] = parse_times(opp[opp_time_col])
    q70["_m15_time"] = parse_times(q70[q70_time_col])
    opp["candidate_key"], candidate_key_source = build_candidate_key(opp)

    opp_rows = int(len(opp))
    q70_rows = int(len(q70))
    opp_parseable = int(opp["_m15_time"].notna().sum())
    q70_parseable = int(q70["_m15_time"].notna().sum())
    candidate_count = int(opp["candidate_key"].nunique()) if opp_rows else 0
    opp_min = opp["_m15_time"].min()
    opp_max = opp["_m15_time"].max()

    q70_cols = [c for c in ["m15_time", "h4_time", "h4_true_range", "prior_60d_obs", "prior_60d_q70_true_range", "is_high_vol_q70", "after_first_valid_h4_q70"] if c in q70.columns]
    q70_work = q70.copy().sort_values("_m15_time")
    q70_work = q70_work.drop_duplicates("_m15_time", keep="last")
    opp_work = opp.copy().sort_values("_m15_time")
    joined = pd.merge_asof(
        opp_work,
        q70_work[["_m15_time"] + [c for c in q70_cols if c != "m15_time"]],
        on="_m15_time",
        direction="backward",
    )
    joined["q70_state_attached"] = joined.get("prior_60d_q70_true_range", pd.Series(index=joined.index, dtype=float)).notna()
    joined["is_high_vol_q70"] = joined.get("is_high_vol_q70", False).fillna(False).astype(bool)
    joined["audit_only"] = True
    joined["live_ready"] = False
    joined.to_csv(out / "gold_v3_66_virtual_opportunity_q70_joined_ledger.csv", index=False, encoding="utf-8-sig")

    agg = joined.groupby("candidate_key", dropna=False).agg(
        virtual_opportunity_count=("candidate_key", "size"),
        first_opportunity_m15_time=("_m15_time", "min"),
        last_opportunity_m15_time=("_m15_time", "max"),
        q70_attached_count=("q70_state_attached", "sum"),
        high_vol_q70_count=("is_high_vol_q70", "sum"),
    ).reset_index()
    agg["q70_coverage_ratio"] = agg["q70_attached_count"] / agg["virtual_opportunity_count"].replace(0, pd.NA)
    agg["high_vol_q70_ratio"] = agg["high_vol_q70_count"] / agg["virtual_opportunity_count"].replace(0, pd.NA)
    agg["candidate_retained"] = True
    agg["manual_candidate_demotion_or_removal"] = False
    agg["live_ready"] = False
    agg["audit_only"] = True
    agg.to_csv(out / "gold_v3_66_candidate_virtual_monitoring_state.csv", index=False, encoding="utf-8-sig")

    inv = pd.DataFrame([
        {"artifact_id": "stage51_virtual_opportunity_ledger", "path": str(p51), "separator": opp_sep, "rows": opp_rows, "columns": "|".join(map(str, opp.columns)), "time_column": opp_time_col, "parseable_time_rows": opp_parseable, "candidate_key_source": candidate_key_source, "candidate_count": candidate_count},
        {"artifact_id": "stage65_m15_asof_q70_state", "path": str(p65m15), "separator": q70_sep, "rows": q70_rows, "columns": "|".join(map(str, q70.columns)), "time_column": q70_time_col, "parseable_time_rows": q70_parseable, "candidate_key_source": "n/a", "candidate_count": "n/a"},
    ])
    inv.to_csv(out / "gold_v3_66_virtual_monitoring_inventory.csv", index=False, encoding="utf-8-sig")

    q70_attached = int(joined["q70_state_attached"].sum())
    q70_missing = int((~joined["q70_state_attached"]).sum())
    high_vol = int(joined["is_high_vol_q70"].sum())
    latest_per_candidate = joined.sort_values("_m15_time").groupby("candidate_key").tail(1)
    latest_high_vol_candidates = int(latest_per_candidate["is_high_vol_q70"].sum()) if not latest_per_candidate.empty else 0

    val.append(ok("opportunity_rows_present", opp_rows > 0, opp_rows, ">0"))
    val.append(ok("q70_rows_present", q70_rows > 0, q70_rows, ">0"))
    val.append(ok("opportunity_timestamps_parseable", opp_parseable == opp_rows and opp_rows > 0, f"{opp_parseable}/{opp_rows}", "all_rows"))
    val.append(ok("q70_timestamps_parseable", q70_parseable == q70_rows and q70_rows > 0, f"{q70_parseable}/{q70_rows}", "all_rows"))
    val.append(ok("candidate_key_constructed", candidate_count > 0, {"candidate_count": candidate_count, "candidate_key_source": candidate_key_source}, ">0"))
    val.append(ok("all_candidates_retained", int(agg["candidate_retained"].sum()) == candidate_count, int(agg["candidate_retained"].sum()), candidate_count))
    val.append(ok("manual_candidate_demotion_or_removal_false", not bool(agg["manual_candidate_demotion_or_removal"].any()), "all_false", "all_false"))
    val.append(ok("q70_attached_some_rows", q70_attached > 0, q70_attached, ">0"))
    val.append(ok("joined_rows_equal_opportunity_rows", len(joined) == opp_rows, len(joined), opp_rows))

    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_66_validation_matrix.csv", index=False, encoding="utf-8-sig")

    summary = {
        "step": STEP,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "audit_only": True,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "mt5_bat_created": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "signals_generated": False,
        "final_signal_enabled": False,
        "contract_mutated": False,
        "manual_candidate_demotion_or_removal": False,
        "open_asof_allowed": False,
        "live_ready": False,
        "virtual_monitoring_state_ready": failed.empty,
        "stage51_virtual_opportunity_ledger": str(p51),
        "virtual_opportunity_rows": opp_rows,
        "candidate_count": candidate_count,
        "candidate_key_source": candidate_key_source,
        "first_opportunity_m15_time": str(opp_min),
        "last_opportunity_m15_time": str(opp_max),
        "q70_attached_count": q70_attached,
        "q70_missing_count": q70_missing,
        "high_vol_q70_opportunity_count": high_vol,
        "latest_high_vol_candidate_count": latest_high_vol_candidates,
        "validation_failure_count": int(len(failed)),
    }
    (out / "gold_v3_66_virtual_monitoring_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = []
    paste.append("GOLD V3 66 PASTE_ME_VIRTUAL_MONITORING_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("virtual_monitoring_state_ready: " + str(failed.empty).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append("csv_contract: open/in-progress candles are not written to CSV")
    paste.append(f"stage51_virtual_opportunity_ledger: {p51}")
    paste.append(f"virtual_opportunity_rows: {opp_rows}")
    paste.append(f"candidate_count: {candidate_count}")
    paste.append(f"candidate_key_source: {candidate_key_source}")
    paste.append(f"first_opportunity_m15_time: {opp_min}")
    paste.append(f"last_opportunity_m15_time: {opp_max}")
    paste.append(f"q70_attached_count: {q70_attached}")
    paste.append(f"q70_missing_count: {q70_missing}")
    paste.append(f"high_vol_q70_opportunity_count: {high_vol}")
    paste.append(f"latest_high_vol_candidate_count: {latest_high_vol_candidates}")
    paste.append("")
    paste.append("CANDIDATE_VIRTUAL_MONITORING_STATE_HEAD")
    paste.append(agg.head(20).to_string(index=False))
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_66_virtual_opportunity_q70_joined_ledger.csv")
    paste.append("gold_v3_66_candidate_virtual_monitoring_state.csv")
    paste.append("gold_v3_66_virtual_monitoring_inventory.csv")
    paste.append("gold_v3_66_validation_matrix.csv")
    paste.append("gold_v3_66_virtual_monitoring_summary.json")
    (out / "gold_v3_66_PASTE_ME_VIRTUAL_MONITORING_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    (out / "GOLD_V3_66_REPORT.md").write_text(f"# GOLD V3 66 virtual monitoring state audit-only report\n\nStatus: `{status}`\n\nAudit-only. No MT5, Discord, AI API, live hook, or final signal.\n", encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_66_PASTE_ME_VIRTUAL_MONITORING_SUMMARY.txt")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
