#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP = "GOLD_V3_03_LABEL_OUTCOME_EVALUATION_AUDIT_ONLY"
OUT_NAME = "03_label_outcome_evaluation_audit_only"
EXPECTED_02B_STATUS = "GOLD_V3_02B_LABEL_GRID_CONTRACT_READY_WITH_SESSION_EXCLUSIONS_AUDIT_ONLY"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def v3_output_root() -> Path:
    return files_root() / "FX_OUTPUTS" / "gold_v3"


def out_dir() -> Path:
    p = v3_output_root() / OUT_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def upstream02b_dir() -> Path:
    return v3_output_root() / "02b_label_grid_contract_audit_only"


def canonical_dir() -> Path:
    return v3_output_root() / "01_candle_normalization_time_audit" / "canonical_candles"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def clean(x: Any) -> Any:
    if isinstance(x, dict): return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, list): return [clean(v) for v in x]
    try:
        if pd.isna(x): return None
    except Exception:
        pass
    return x.isoformat() if hasattr(x, "isoformat") else x


def write_json(p: Path, obj: dict[str, Any]) -> None:
    p.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def read_json(p: Path) -> dict[str, Any]:
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}


def md(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ")[:500] for c in d.columns) + " |")
    return "\n".join(lines)


def input_inventory(paths: list[Path]) -> pd.DataFrame:
    rows=[]
    for p in paths:
        rows.append({"path": str(p), "filename": p.name, "exists": p.exists(), "bytes": p.stat().st_size if p.exists() else 0, "sha256": sha256_file(p) if p.exists() else ""})
    return pd.DataFrame(rows)


def load_contracts(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p)
    df["entry_t"] = pd.to_datetime(df["entry_time_utc"], utc=True, errors="coerce")
    df["horizon_t"] = pd.to_datetime(df["horizon_end_utc"], utc=True, errors="coerce")
    return df


def load_m5(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p)
    df["t"] = pd.to_datetime(df["time_utc"], utc=True, errors="coerce")
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.sort_values("t").reset_index(drop=True)


def evaluate_rows(contract: pd.DataFrame, m5: pd.DataFrame) -> pd.DataFrame:
    times = m5["t"].to_numpy(dtype="datetime64[ns]")
    highs = m5["high"].to_numpy(dtype=float)
    lows = m5["low"].to_numpy(dtype=float)
    closes = m5["close"].to_numpy(dtype=float)
    out = []
    n = len(contract)
    for i, r in contract.iterrows():
        entry = np.datetime64(r["entry_t"].tz_convert(None).to_datetime64()) if pd.notna(r["entry_t"]) else None
        horizon = np.datetime64(r["horizon_t"].tz_convert(None).to_datetime64()) if pd.notna(r["horizon_t"]) else None
        if entry is None or horizon is None:
            outcome = "NO_WINDOW"; touch_t = ""; offset = None; result = 0.0; timeout_close = None; window_bars = 0
        else:
            start = int(np.searchsorted(times, entry, side="left"))
            end = int(np.searchsorted(times, horizon, side="left"))
            if start >= len(times) or end <= start:
                outcome = "NO_WINDOW"; touch_t = ""; offset = None; result = 0.0; timeout_close = None; window_bars = max(0, end-start)
            elif times[start] != entry:
                outcome = "ENTRY_TIME_NOT_FOUND"; touch_t = ""; offset = None; result = 0.0; timeout_close = None; window_bars = max(0, end-start)
            else:
                hh = highs[start:end]; ll = lows[start:end]
                direction = str(r["direction"])
                tp = float(r["tp_price"]); sl = float(r["sl_price"])
                if direction == "LONG":
                    tp_hit = hh >= tp; sl_hit = ll <= sl
                    win_result = float(r["tp_price_distance_usd"]); loss_result = -float(r["sl_price_distance_usd"])
                else:
                    tp_hit = ll <= tp; sl_hit = hh >= sl
                    win_result = float(r["tp_price_distance_usd"]); loss_result = -float(r["sl_price_distance_usd"])
                hit = tp_hit | sl_hit
                if hit.any():
                    j_rel = int(np.argmax(hit))
                    # SL first when both hit on the same bar.
                    if bool(sl_hit[j_rel]):
                        outcome = "SL"; result = loss_result
                    else:
                        outcome = "TP"; result = win_result
                    touch_t = str(pd.Timestamp(times[start + j_rel], tz="UTC"))
                    offset = j_rel
                    timeout_close = None
                    window_bars = int(end-start)
                else:
                    outcome = "TIMEOUT"
                    touch_t = ""
                    offset = None
                    timeout_close = float(closes[end-1])
                    entry_price = float(r["entry_price"])
                    if direction == "LONG":
                        result = timeout_close - entry_price
                    else:
                        result = entry_price - timeout_close
                    window_bars = int(end-start)
        out.append({
            "label_evaluated": True,
            "label_outcome": outcome,
            "first_touch_time_utc": touch_t,
            "first_touch_bar_offset_m5": offset,
            "label_price_distance_result_usd": result,
            "timeout_close_price": timeout_close,
            "window_m5_bars": window_bars,
        })
    return pd.concat([contract.drop(columns=["entry_t", "horizon_t"], errors="ignore").reset_index(drop=True), pd.DataFrame(out)], axis=1)


def summary_by(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if df.empty: return pd.DataFrame()
    g = df.groupby(group_cols, dropna=False)
    rows=[]
    for keys, x in g:
        if not isinstance(keys, tuple): keys=(keys,)
        row={c:v for c,v in zip(group_cols, keys)}
        n=len(x); tp=int((x["label_outcome"]=="TP").sum()); sl=int((x["label_outcome"]=="SL").sum()); timeout=int((x["label_outcome"]=="TIMEOUT").sum())
        row.update({
            "rows": n,
            "tp": tp,
            "sl": sl,
            "timeout": timeout,
            "other": n-tp-sl-timeout,
            "tp_rate": tp/n if n else 0,
            "sl_rate": sl/n if n else 0,
            "timeout_rate": timeout/n if n else 0,
            "avg_result_usd": float(x["label_price_distance_result_usd"].mean()) if n else 0,
            "sum_result_usd": float(x["label_price_distance_result_usd"].sum()) if n else 0,
        })
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    created = datetime.now(timezone.utc).isoformat()
    out = out_dir()
    paths = [
        upstream02b_dir() / "gold_v3_02b_summary.json",
        upstream02b_dir() / "gold_v3_02b_entry_grid_contract_only.csv",
        canonical_dir() / "gold_v3_gold_hash_2025_primary_m5.csv",
    ]
    inv_df = input_inventory(paths)
    summary02b = read_json(paths[0])
    inputs_ok = bool(inv_df["exists"].all())
    upstream_ok = summary02b.get("status") == EXPECTED_02B_STATUS
    if inputs_ok:
        contract = load_contracts(paths[1])
        m5 = load_m5(paths[2])
        evaluated = evaluate_rows(contract, m5)
    else:
        contract = pd.DataFrame(); m5 = pd.DataFrame(); evaluated = pd.DataFrame()
    profile_sum = summary_by(evaluated, ["profile_id"])
    direction_sum = summary_by(evaluated, ["profile_id", "direction"])
    outcome_counts = evaluated["label_outcome"].value_counts().to_dict() if not evaluated.empty else {}
    all_evaluated = (not evaluated.empty) and bool(evaluated["label_evaluated"].all())
    if not (inputs_ok and upstream_ok):
        status = "GOLD_V3_03_LABEL_EVALUATION_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif evaluated.empty or not all_evaluated:
        status = "GOLD_V3_03_LABEL_EVALUATION_BLOCKED_AUDIT_ONLY"
    else:
        status = "GOLD_V3_03_LABEL_OUTCOME_EVALUATION_READY_AUDIT_ONLY"
    decision_df = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_02b_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["evaluated_rows_nonempty", len(evaluated)>0, True, "PASS" if len(evaluated)>0 else "FAIL"],
        ["all_rows_label_evaluated", all_evaluated, True, "PASS" if all_evaluated else "FAIL"],
        ["features_created", False, False, "PASS"],
        ["signals_generated", False, False, "PASS"],
        ["zip_output_created", False, False, "PASS"],
        ["external_actions", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blocker_df = pd.DataFrame([
        ["G3-03-001", "02B inputs", "CLOSED" if inputs_ok and upstream_ok else "OPEN", "HARD", "02B ready status and contract rows required."],
        ["G3-03-002", "label evaluation", "CLOSED" if all_evaluated else "OPEN", "HARD", "All contract rows must receive explicit label classification."],
        ["G3-03-003", "feature/candidate/signal", "CLOSED_BLOCKED_BY_POLICY", "HARD", "No features, candidate selection, or signals in this step."],
        ["G3-03-004", "zip output", "CLOSED_DISABLED", "INFO", "ZIP output disabled."],
        ["G3-03-005", "external actions", "CLOSED", "HARD", "No external actions performed."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_recovery_approved": False,
        "contract_rows": int(len(contract)),
        "evaluated_rows": int(len(evaluated)),
        "outcome_counts": outcome_counts,
        "features_created": False,
        "signals_generated": False,
        "zip_output_created": False,
        "external_actions": ACTIONS,
    }
    inv_df.to_csv(out / "gold_v3_03_input_inventory.csv", index=False, encoding="utf-8-sig")
    evaluated.to_csv(out / "gold_v3_03_evaluated_label_rows.csv", index=False, encoding="utf-8-sig")
    profile_sum.to_csv(out / "gold_v3_03_profile_outcome_summary.csv", index=False, encoding="utf-8-sig")
    direction_sum.to_csv(out / "gold_v3_03_direction_outcome_summary.csv", index=False, encoding="utf-8-sig")
    decision_df.to_csv(out / "gold_v3_03_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blocker_df.to_csv(out / "gold_v3_03_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "gold_v3_03_summary.json", summary)
    report = "\n".join([
        "# GOLD V3 03 label outcome evaluation audit-only report",
        "",
        f"Created UTC: {created}",
        f"Status: `{status}`",
        "",
        "## Outcome counts",
        md(pd.DataFrame([{"outcome": k, "count": v} for k, v in outcome_counts.items()])),
        "",
        "## Profile outcome summary",
        md(profile_sum),
        "",
        "## Direction outcome summary",
        md(direction_sum),
        "",
        "## Decision matrix",
        md(decision_df),
        "",
        "## Blockers",
        md(blocker_df),
        "",
        "## Safety",
        "- GOLD V3 only; no V2 artifacts used.",
        "- Future M5 candles used only to assign labels.",
        "- No features, no candidates, no signals.",
        "- No ZIP output.",
        "- Discord/MT5/AI/live/final remain OFF.",
    ])
    (out / "GOLD_V3_03_LABEL_OUTCOME_EVALUATION_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "output_dir": str(out), "zip_output_created": False}, ensure_ascii=False, indent=2))
    print("No ZIP, features, candidates, signals, Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
