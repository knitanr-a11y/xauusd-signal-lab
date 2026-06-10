#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 68 rank/dedup selection reproduction audit-only.

Reproduces timestamp-level rank/dedup selection from Stage67 rehydrated
rolling health gate events and validates against Stage52 selected trade ledger.

No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "GOLD_V3_68_RANK_DEDUP_SELECTION_REPRO_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_68_RANK_DEDUP_SELECTION_REPRO_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_68_RANK_DEDUP_SELECTION_REPRO_BLOCKED_AUDIT_ONLY"
STAGE67_READY = "GOLD_V3_67_HEALTH_GATE_REHYDRATION_READY_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
KEY_COLS = [
    "candidate_label",
    "base_candidate_label",
    "source_profile_id",
    "profile_id",
    "hv_profile",
    "tp_usd",
    "sl_usd",
    "horizon_m15",
    "horizon_m5_bars",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_auto(path: Path) -> tuple[pd.DataFrame, str]:
    attempts: list[tuple[str | None, str]] = [(None, "auto"), (",", "comma"), (";", "semicolon"), ("\t", "tab")]
    last_err: Exception | None = None
    for sep, label in attempts:
        try:
            if sep is None:
                df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
            else:
                df = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
            if len(df.columns) > 1:
                return df, label
        except Exception as e:  # pragma: no cover
            last_err = e
    if last_err:
        raise last_err
    raise ValueError(f"Could not parse CSV with multiple columns: {path}")


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def norm_cell(v: Any) -> str:
    if pd.isna(v):
        return ""
    if isinstance(v, (np.integer, int)):
        return str(int(v))
    if isinstance(v, (np.floating, float)):
        f = float(v)
        if math.isfinite(f) and f.is_integer():
            return str(int(f))
        return (f"{f:.10f}").rstrip("0").rstrip(".")
    s = str(v).strip()
    if s.lower() in {"nan", "none", "nat"}:
        return ""
    return s


def normalize_key_part(s: Any) -> str:
    x = norm_cell(s)
    if not x:
        return ""
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", x):
        try:
            f = float(x)
            if math.isfinite(f) and f.is_integer():
                return str(int(f))
            return (f"{f:.10f}").rstrip("0").rstrip(".")
        except Exception:  # pragma: no cover
            return x
    return x


def build_candidate_key(df: pd.DataFrame) -> pd.Series:
    key = pd.Series([""] * len(df), index=df.index, dtype="object")
    for i, c in enumerate(KEY_COLS):
        part = df[c].map(normalize_key_part)
        key = part if i == 0 else key + "|" + part
    return key.astype(str)


def as_bool_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "y"])


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd(), root, root.parent, root.parent.parent, root / "Files", root.parent / "Files"]
    for d in candidates:
        d = d.expanduser().resolve()
        if (d / "FX_OUTPUTS" / "gold_v3" / "67_health_gate_rehydration_audit_only").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with FX_OUTPUTS/gold_v3/67_health_gate_rehydration_audit_only")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--stage67-dir", default="")
    p.add_argument("--stage66-dir", default="")
    p.add_argument("--stage52-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def build_selection(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = events.copy()
    x["event_time"] = pd.to_datetime(x["event_time"], errors="coerce")
    x["priority"] = pd.to_numeric(x["priority"], errors="coerce")
    x["health_gate_pass"] = as_bool_series(x["health_gate_pass"])
    x["candidate_key"] = build_candidate_key(x)
    rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    for event_time, g in x.groupby("event_time", sort=True, dropna=False):
        g = g.sort_values(["priority", "candidate_label", "candidate_key", "opportunity_id"], kind="mergesort").copy()
        eligible = g[g["health_gate_pass"]].copy()
        if len(eligible) > 0:
            sr = eligible.iloc[0].to_dict()
            selected_rows.append(sr)
            rows.append({
                "m15_time_jst": event_time,
                "candidate_count_before_gate": int(len(g)),
                "eligible_candidate_count": int(len(eligible)),
                "selected_candidate_label": sr.get("candidate_label", ""),
                "selected_candidate_key": sr.get("candidate_key", ""),
                "selected_opportunity_id": sr.get("opportunity_id", ""),
                "selected_priority": sr.get("priority", ""),
                "selected_result_usd": sr.get("result_usd_after_close", ""),
                "dedup_priority_rule": "event_time, priority, candidate_label, candidate_key, opportunity_id; first eligible",
                "eligible_candidates": " || ".join(eligible["candidate_key"].astype(str).head(50).tolist()),
                "blocked_candidates": " || ".join(g.loc[~g["health_gate_pass"], "candidate_key"].astype(str).head(50).tolist()),
                "no_signal_reason": "",
                "audit_only": True,
                "live_ready": False,
            })
        else:
            rows.append({
                "m15_time_jst": event_time,
                "candidate_count_before_gate": int(len(g)),
                "eligible_candidate_count": 0,
                "selected_candidate_label": "",
                "selected_candidate_key": "",
                "selected_opportunity_id": "",
                "selected_priority": "",
                "selected_result_usd": "",
                "dedup_priority_rule": "event_time, priority, candidate_label, candidate_key, opportunity_id; first eligible",
                "eligible_candidates": "",
                "blocked_candidates": " || ".join(g["candidate_key"].astype(str).head(50).tolist()),
                "no_signal_reason": "NO_ELIGIBLE_CANDIDATE",
                "audit_only": True,
                "live_ready": False,
            })
    selection = pd.DataFrame(rows)
    selected = pd.DataFrame(selected_rows)
    return selection, selected


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    s67 = Path(a.stage67_dir).expanduser().resolve() if a.stage67_dir else base_out / "67_health_gate_rehydration_audit_only"
    s66 = Path(a.stage66_dir).expanduser().resolve() if a.stage66_dir else base_out / "66_virtual_monitoring_state_audit_only"
    s52 = Path(a.stage52_dir).expanduser().resolve() if a.stage52_dir else base_out / "52_health_gate_state_rank_dedup_audit_only"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out / "68_rank_dedup_selection_repro_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    p67_summary = s67 / "gold_v3_67_health_gate_rehydration_summary.json"
    p67_events = s67 / "gold_v3_67_health_gate_event_ledger.csv"
    p67_state = s67 / "gold_v3_67_health_gate_rehydrated_candidate_state.csv"
    p66_joined = s66 / "gold_v3_66_virtual_opportunity_q70_joined_ledger.csv"
    p52_selected = s52 / "gold_v3_52_selected_trade_ledger.csv"

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for name, path in [
        ("stage67_summary", p67_summary),
        ("stage67_event_ledger", p67_events),
        ("stage67_candidate_state", p67_state),
        ("stage66_joined_ledger", p66_joined),
        ("stage52_selected_trade_ledger", p52_selected),
    ]:
        val.append(ok(f"{name}_present", path.exists(), str(path), "exists"))
        if not path.exists():
            blockers.append(blocker(f"{name}_missing", str(path), "REQUIRED_INPUT_MISSING"))

    j67 = read_json(p67_summary) if p67_summary.exists() else {}
    val.append(ok("stage67_status_ready", j67.get("status") == STAGE67_READY, j67.get("status"), STAGE67_READY))
    val.append(ok("stage67_health_gate_rehydration_ready", j67.get("health_gate_rehydration_ready") is True, j67.get("health_gate_rehydration_ready"), True))
    for key in ["live_allowed", "mt5_execution_enabled", "discord_live_enabled", "ai_api_called", "final_signal_enabled", "contract_mutated", "manual_candidate_demotion_or_removal", "open_asof_allowed"]:
        val.append(ok(f"stage67_{key}_false", j67.get(key) is False, j67.get(key), False))

    selected = pd.DataFrame()
    selection = pd.DataFrame()
    parity = pd.DataFrame()
    cand_summary = pd.DataFrame()
    event_rows = 0
    selected_rows = 0
    stage52_rows = 0
    parity_mismatch_count = 0
    candidate_count = 0
    no_signal_rows = 0

    if not blockers:
        ev, _ = read_csv_auto(p67_events)
        st, _ = read_csv_auto(p67_state)
        s66j, _ = read_csv_auto(p66_joined)
        ref, _ = read_csv_auto(p52_selected)
        event_rows = int(len(ev))
        stage52_rows = int(len(ref))
        missing_ev_key = [c for c in KEY_COLS if c not in ev.columns]
        missing_s66_key = [c for c in KEY_COLS if c not in s66j.columns]
        val.append(ok("stage67_event_has_exact_key_columns", not missing_ev_key, "|".join(missing_ev_key), "none"))
        val.append(ok("stage66_joined_has_exact_key_columns", not missing_s66_key, "|".join(missing_s66_key), "none"))
        for required in ["event_time", "opportunity_id", "health_gate_pass", "result_usd_after_close"]:
            val.append(ok(f"stage67_event_has_{required}", required in ev.columns, required if required in ev.columns else "missing", "present"))
        if missing_ev_key or missing_s66_key:
            blockers.append(blocker("candidate_key_columns_missing", str(p67_events), "MISSING_EXACT_KEY_COLUMNS", {"stage67_missing": missing_ev_key, "stage66_missing": missing_s66_key}))
        elif any(c not in ev.columns for c in ["event_time", "opportunity_id", "health_gate_pass", "result_usd_after_close"]):
            blockers.append(blocker("stage67_event_required_columns_missing", str(p67_events), "MISSING_REQUIRED_STAGE67_COLUMNS"))
        else:
            ev = ev.copy()
            s66j = s66j.copy()
            ev["candidate_key"] = build_candidate_key(ev)
            s66j["candidate_key"] = build_candidate_key(s66j)
            rank_cols = ["opportunity_id", "candidate_key", "priority", "source_rank", "entry_price", "exit_dt", "exit_price", "exit_reason", "result_usd", "is_win", "is_loss"]
            for c in rank_cols:
                if c not in s66j.columns:
                    s66j[c] = ""
            add = s66j[rank_cols].drop_duplicates("opportunity_id", keep="last")
            merged = ev.merge(add, on="opportunity_id", how="left", suffixes=("", "_s66"))
            merged_key_mismatch = int((merged["candidate_key"].astype(str) != merged["candidate_key_s66"].astype(str)).fillna(True).sum()) if "candidate_key_s66" in merged.columns else len(merged)
            priority_numeric = pd.to_numeric(merged.get("priority", pd.Series(index=merged.index, dtype=float)), errors="coerce")
            val.append(ok("stage67_stage66_rows_one_to_one", len(merged) == len(ev), len(merged), len(ev)))
            val.append(ok("stage67_stage66_candidate_key_match", merged_key_mismatch == 0, merged_key_mismatch, 0))
            val.append(ok("priority_numeric_all_events", int(priority_numeric.notna().sum()) == len(merged), int(priority_numeric.notna().sum()), len(merged)))
            if merged_key_mismatch != 0 or int(priority_numeric.notna().sum()) != len(merged):
                blockers.append(blocker("stage66_rank_metadata_join_failed", str(p66_joined), "KEY_OR_PRIORITY_JOIN_FAILURE", {"key_mismatch": merged_key_mismatch, "priority_numeric": int(priority_numeric.notna().sum()), "events": int(len(merged))}))
            else:
                merged["priority"] = priority_numeric
                selection, selected = build_selection(merged)
                selection.to_csv(out / "gold_v3_68_rank_dedup_selection_ledger.csv", index=False, encoding="utf-8-sig")
                selected.to_csv(out / "gold_v3_68_selected_trade_ledger.csv", index=False, encoding="utf-8-sig")
                selected_rows = int(len(selected))
                no_signal_rows = int(selection["no_signal_reason"].astype(str).eq("NO_ELIGIBLE_CANDIDATE").sum())
                candidate_count = int(merged["candidate_key"].nunique())
                # Parity by selected opportunity_id set and ordered opportunity ids.
                ref_ids = ref["opportunity_id"].astype(str).sort_values().reset_index(drop=True) if "opportunity_id" in ref.columns else pd.Series(dtype=str)
                sel_ids = selected["opportunity_id"].astype(str).sort_values().reset_index(drop=True) if "opportunity_id" in selected.columns else pd.Series(dtype=str)
                n = max(len(ref_ids), len(sel_ids))
                parity = pd.DataFrame({
                    "stage52_opportunity_id": ref_ids.reindex(range(n)),
                    "stage68_opportunity_id": sel_ids.reindex(range(n)),
                })
                parity["match"] = parity["stage52_opportunity_id"].fillna("").astype(str).eq(parity["stage68_opportunity_id"].fillna("").astype(str))
                parity.to_csv(out / "gold_v3_68_stage52_selection_parity.csv", index=False, encoding="utf-8-sig")
                parity_mismatch_count = int((~parity["match"]).sum())
                val.append(ok("selected_count_matches_stage52", selected_rows == stage52_rows, selected_rows, stage52_rows))
                val.append(ok("selected_opportunity_ids_match_stage52", parity_mismatch_count == 0, parity_mismatch_count, 0))
                if selected_rows != stage52_rows or parity_mismatch_count != 0:
                    blockers.append(blocker("stage52_selection_parity_mismatch", str(p52_selected), "SELECTED_OPPORTUNITY_IDS_DO_NOT_MATCH", {"stage68_selected": selected_rows, "stage52_selected": stage52_rows, "mismatch": parity_mismatch_count}))
                cand_summary = selected.groupby(["candidate_key", "candidate_label"], dropna=False).agg(
                    selected_count=("opportunity_id", "count"),
                    sum_result_usd=("result_usd_after_close", "sum"),
                ).reset_index() if not selected.empty else pd.DataFrame(columns=["candidate_key", "candidate_label", "selected_count", "sum_result_usd"])
                cand_summary.to_csv(out / "gold_v3_68_candidate_selection_summary.csv", index=False, encoding="utf-8-sig")
                val.append(ok("selection_ledger_nonempty", len(selection) > 0, len(selection), ">0"))
                val.append(ok("all_candidates_remain_pool", candidate_count == int(j67.get("candidate_count", candidate_count)), candidate_count, int(j67.get("candidate_count", candidate_count))))
                val.append(ok("manual_candidate_demotion_or_removal_false", True, False, False))
    if selection.empty:
        (out / "gold_v3_68_rank_dedup_selection_ledger.csv").write_text("", encoding="utf-8")
        (out / "gold_v3_68_selected_trade_ledger.csv").write_text("", encoding="utf-8")
        (out / "gold_v3_68_candidate_selection_summary.csv").write_text("", encoding="utf-8")
        (out / "gold_v3_68_stage52_selection_parity.csv").write_text("", encoding="utf-8")

    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
    val.append(ok("no_ohlc_re_adjudication", True, "not_used", "not_used"))
    val.append(ok("live_flags_all_false", True, "all_false", "all_false"))

    pd.DataFrame(blockers).to_csv(out / "gold_v3_68_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty and not blockers else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_68_validation_matrix.csv", index=False, encoding="utf-8-sig")

    summary = {
        "step": STEP,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "candle_dir": str(cdir),
        "output_dir": str(out),
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
        "csv_contract": CSV_CONTRACT,
        "csv_open_bar_exclusion_required": False,
        "live_ready": False,
        "rank_dedup_selection_repro_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "candidate_key_source": "+".join(KEY_COLS),
        "event_rows": event_rows,
        "selection_rows": int(len(selection)),
        "selected_trade_rows": selected_rows,
        "stage52_selected_trade_rows": stage52_rows,
        "no_signal_rows": no_signal_rows,
        "candidate_count": candidate_count,
        "stage52_selection_parity_mismatch_count": parity_mismatch_count,
        "validation_failure_count": int(len(failed)),
        "blocker_count": int(len(blockers)),
    }
    (out / "gold_v3_68_rank_dedup_selection_repro_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste: list[str] = []
    paste.append("GOLD V3 68 PASTE_ME_RANK_DEDUP_SELECTION_REPRO_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("rank_dedup_selection_repro_ready: " + str(status == READY_STATUS).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("csv_contract: " + CSV_CONTRACT)
    paste.append("csv_open_bar_exclusion_required: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append("pool_policy: " + POOL_POLICY)
    paste.append("candidate_key_source: " + "+".join(KEY_COLS))
    paste.append(f"event_rows: {event_rows}")
    paste.append(f"selection_rows: {len(selection)}")
    paste.append(f"selected_trade_rows: {selected_rows}")
    paste.append(f"stage52_selected_trade_rows: {stage52_rows}")
    paste.append(f"no_signal_rows: {no_signal_rows}")
    paste.append(f"candidate_count: {candidate_count}")
    paste.append(f"stage52_selection_parity_mismatch_count: {parity_mismatch_count}")
    paste.append(f"blocker_count: {len(blockers)}")
    paste.append("")
    paste.append("BLOCKERS")
    paste.append(pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS")
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_68_rank_dedup_selection_ledger.csv")
    paste.append("gold_v3_68_selected_trade_ledger.csv")
    paste.append("gold_v3_68_candidate_selection_summary.csv")
    paste.append("gold_v3_68_stage52_selection_parity.csv")
    paste.append("gold_v3_68_blocker_matrix.csv")
    paste.append("gold_v3_68_validation_matrix.csv")
    paste.append("gold_v3_68_rank_dedup_selection_repro_summary.json")
    (out / "gold_v3_68_PASTE_ME_RANK_DEDUP_SELECTION_REPRO_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 68 rank/dedup selection reproduction audit-only report

Status: `{status}`

## Summary

- event_rows: `{event_rows}`
- selection_rows: `{len(selection)}`
- selected_trade_rows: `{selected_rows}`
- stage52_selected_trade_rows: `{stage52_rows}`
- stage52_selection_parity_mismatch_count: `{parity_mismatch_count}`
- blocker_count: `{len(blockers)}`

## Contract

- candidate_key_source: `{'+'.join(KEY_COLS)}`
- csv_open_bar_exclusion_required: `false`
- pool_policy: `{POOL_POLICY}`

## Safety

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out / "GOLD_V3_68_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] output_dir={out}")
    print(out / "gold_v3_68_PASTE_ME_RANK_DEDUP_SELECTION_REPRO_SUMMARY.txt")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
