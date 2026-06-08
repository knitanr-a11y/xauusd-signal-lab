#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "GOLD_V3_02_LABEL_CONTRACT_AUDIT_ONLY"
OUT_NAME = "02_label_contract_audit_only"
EXPECTED_01B_STATUS = "GOLD_V3_01B_NATIVE_CANDLE_USE_READY_WITH_GAP_GUARDS_AUDIT_ONLY"
STRATEGY_ID = "GOLD_V3_LABEL_BASE_M15_CLOSE_M5_FIRST_TOUCH_TP10_SL5_H28_V1"
TP_USD = 10.0
SL_USD = 5.0
HORIZON_M15_BARS = 28
HORIZON_MINUTES = 420
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def fx_outputs_root() -> Path:
    return files_root() / "FX_OUTPUTS"


def v3_output_root() -> Path:
    return fx_outputs_root() / "gold_v3"


def out_dir() -> Path:
    p = v3_output_root() / OUT_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def upstream01b_dir() -> Path:
    return v3_output_root() / "01b_candle_gap_session_policy_audit"


def canonical_dir() -> Path:
    return v3_output_root() / "01_candle_normalization_time_audit" / "canonical_candles"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def clean(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, list):
        return [clean(v) for v in x]
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    return x.isoformat() if hasattr(x, "isoformat") else x


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def md(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ")[:500] for c in d.columns) + " |")
    return "\n".join(lines)


def input_inventory(paths: list[Path]) -> pd.DataFrame:
    rows = []
    for p in paths:
        rows.append({"path": str(p), "filename": p.name, "exists": p.exists(), "bytes": p.stat().st_size if p.exists() else 0, "sha256": sha256_file(p) if p.exists() else ""})
    return pd.DataFrame(rows)


def load_candles(tf: str) -> pd.DataFrame:
    p = canonical_dir() / f"gold_v3_gold_hash_2025_primary_{tf}.csv"
    df = pd.read_csv(p)
    df["t"] = pd.to_datetime(df["time_utc"], utc=True, errors="coerce")
    return df


def build_contract(m15: pd.DataFrame, m5: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    m5_times = set(m5["t"].dropna())
    last_m5 = m5["t"].max()
    rows = []
    excluded = []
    entry_universe = []
    m5_open_map = dict(zip(m5["t"], m5["open"]))
    for _, r in m15.iterrows():
        feature_open = r["t"]
        if pd.isna(feature_open):
            excluded.append({"feature_bar_open_utc": "", "entry_time_utc": "", "reason": "invalid_m15_time"})
            continue
        entry = feature_open + pd.Timedelta(minutes=15)
        horizon_end = entry + pd.Timedelta(minutes=HORIZON_MINUTES)
        if entry not in m5_times:
            excluded.append({"feature_bar_open_utc": str(feature_open), "entry_time_utc": str(entry), "reason": "missing_native_m5_entry_open"})
            continue
        if horizon_end > last_m5:
            excluded.append({"feature_bar_open_utc": str(feature_open), "entry_time_utc": str(entry), "reason": "insufficient_m5_lookahead_window"})
            continue
        entry_price = float(m5_open_map[entry])
        entry_universe.append({"feature_bar_open_utc": str(feature_open), "entry_time_utc": str(entry), "entry_price": entry_price, "horizon_end_utc": str(horizon_end)})
        for direction in ["LONG", "SHORT"]:
            if direction == "LONG":
                tp_price = entry_price + TP_USD
                sl_price = entry_price - SL_USD
            else:
                tp_price = entry_price - TP_USD
                sl_price = entry_price + SL_USD
            rows.append({
                "strategy_id": STRATEGY_ID,
                "feature_timeframe": "M15",
                "evaluation_timeframe": "M5",
                "feature_bar_open_utc": str(feature_open),
                "entry_time_utc": str(entry),
                "direction": direction,
                "entry_price_source": "native_m5_open_at_entry_time",
                "entry_price": entry_price,
                "tp_usd": TP_USD,
                "sl_usd": SL_USD,
                "tp_price": tp_price,
                "sl_price": sl_price,
                "horizon_m15_bars": HORIZON_M15_BARS,
                "horizon_minutes": HORIZON_MINUTES,
                "horizon_end_utc": str(horizon_end),
                "same_bar_priority": "SL_FIRST",
                "outcome": "NOT_EVALUATED_CONTRACT_ONLY",
                "ai_api_called": False,
            })
    return pd.DataFrame(rows), pd.DataFrame(excluded), pd.DataFrame(entry_universe)


def main() -> int:
    created = datetime.now(timezone.utc).isoformat()
    out = out_dir()
    paths = [
        upstream01b_dir() / "gold_v3_01b_summary.json",
        upstream01b_dir() / "gold_v3_01b_data_use_policy_matrix.csv",
        canonical_dir() / "gold_v3_gold_hash_2025_primary_m15.csv",
        canonical_dir() / "gold_v3_gold_hash_2025_primary_m5.csv",
    ]
    inv_df = input_inventory(paths)
    summary01b = read_json(paths[0])
    upstream_ok = summary01b.get("status") == EXPECTED_01B_STATUS
    inputs_ok = bool(inv_df["exists"].all())
    if inputs_ok:
        m15 = load_candles("m15")
        m5 = load_candles("m5")
    else:
        m15 = pd.DataFrame()
        m5 = pd.DataFrame()
    contract_df, excluded_df, entry_df = build_contract(m15, m5) if inputs_ok else (pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    contract_obj = {
        "strategy_id": STRATEGY_ID,
        "feature_bar_timeframe": "M15",
        "entry_time_rule": "feature_bar_open_utc + 15 minutes",
        "evaluation_timeframe": "M5",
        "entry_price_source": "native M5 open at entry_time",
        "directions": ["LONG", "SHORT"],
        "tp_usd": TP_USD,
        "sl_usd": SL_USD,
        "horizon_m15_bars": HORIZON_M15_BARS,
        "horizon_minutes": HORIZON_MINUTES,
        "same_bar_priority": "SL_FIRST",
        "outcome_policy": "NOT_EVALUATED_CONTRACT_ONLY in GOLD_V3_02",
        "ai_api_called": False,
        "features_created": False,
        "signals_generated": False,
        "zip_output_created": False,
    }
    source_m15_rows = int(len(m15))
    source_m5_rows = int(len(m5))
    entry_universe_rows = int(len(entry_df))
    contract_rows = int(len(contract_df))
    direction_counts = contract_df["direction"].value_counts().to_dict() if not contract_df.empty else {}
    outcome_counts = contract_df["outcome"].value_counts().to_dict() if not contract_df.empty else {}
    strategy_counts = contract_df["strategy_id"].value_counts().to_dict() if not contract_df.empty else {}
    excluded_counts = excluded_df["reason"].value_counts().to_dict() if not excluded_df.empty else {}
    material_missing = int(excluded_counts.get("missing_native_m5_entry_open", 0)) > 0
    no_entries = contract_rows == 0
    if not (inputs_ok and upstream_ok):
        status = "GOLD_V3_02_LABEL_CONTRACT_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif no_entries or material_missing:
        status = "GOLD_V3_02_LABEL_CONTRACT_BLOCKED_AUDIT_ONLY"
    else:
        status = "GOLD_V3_02_LABEL_CONTRACT_READY_AUDIT_ONLY"
    audit_summary = pd.DataFrame([
        ["source_m15_rows", source_m15_rows],
        ["source_m5_rows", source_m5_rows],
        ["entry_universe_rows_before_direction_expansion", entry_universe_rows],
        ["contract_rows_after_long_short_expansion", contract_rows],
        ["expected_max_raw_direction_rows", source_m15_rows * 2],
        ["excluded_entry_count", int(len(excluded_df))],
        ["strategy_id_count", len(strategy_counts)],
        ["unique_entry_time_count", int(contract_df["entry_time_utc"].nunique()) if not contract_df.empty else 0],
        ["long_count", int(direction_counts.get("LONG", 0))],
        ["short_count", int(direction_counts.get("SHORT", 0))],
        ["outcome_not_evaluated_count", int(outcome_counts.get("NOT_EVALUATED_CONTRACT_ONLY", 0))],
        ["ai_api_called", False],
        ["zip_output_created", False],
    ], columns=["metric", "value"])
    decision_df = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_01b_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["entry_universe_nonempty", entry_universe_rows > 0, True, "PASS" if entry_universe_rows > 0 else "FAIL"],
        ["missing_native_m5_entry_open_count", int(excluded_counts.get("missing_native_m5_entry_open", 0)), 0, "PASS" if int(excluded_counts.get("missing_native_m5_entry_open", 0)) == 0 else "FAIL"],
        ["outcomes_evaluated", False, False, "PASS"],
        ["features_created", False, False, "PASS"],
        ["signals_generated", False, False, "PASS"],
        ["ai_api_called", False, False, "PASS"],
        ["zip_output_created", False, False, "PASS"],
        ["external_actions", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blocker_df = pd.DataFrame([
        ["G3-02-001", "01B inputs", "CLOSED" if inputs_ok and upstream_ok else "OPEN", "HARD", "01B ready status and M15/M5 canonical candles required."],
        ["G3-02-002", "M5 entry open availability", "CLOSED" if not material_missing else "OPEN", "HARD", "Every contract entry_time must exist as native M5 open."],
        ["G3-02-003", "lookahead window availability", "REVIEW" if len(excluded_df) else "CLOSED", "INFO", "Late M15 bars can be excluded due insufficient M5 horizon."],
        ["G3-02-004", "outcome evaluation", "CLOSED_BLOCKED_BY_POLICY", "HARD", "02 is contract-only; no outcomes evaluated."],
        ["G3-02-005", "zip output", "CLOSED_DISABLED", "INFO", "ZIP output disabled by user request."],
        ["G3-02-006", "external actions", "CLOSED", "HARD", "No external actions performed."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_recovery_approved": False,
        "strategy_id": STRATEGY_ID,
        "source_m15_rows": source_m15_rows,
        "source_m5_rows": source_m5_rows,
        "entry_universe_rows": entry_universe_rows,
        "contract_rows": contract_rows,
        "excluded_counts": excluded_counts,
        "direction_counts": direction_counts,
        "outcome_counts": outcome_counts,
        "ai_api_called": False,
        "features_created": False,
        "labels_evaluated": False,
        "signals_generated": False,
        "zip_output_created": False,
        "external_actions": ACTIONS,
    }
    inv_df.to_csv(out / "gold_v3_02_input_inventory.csv", index=False, encoding="utf-8-sig")
    audit_summary.to_csv(out / "gold_v3_02_label_contract_audit_summary.csv", index=False, encoding="utf-8-sig")
    contract_df.to_csv(out / "gold_v3_02_entry_universe_contract_only.csv", index=False, encoding="utf-8-sig")
    excluded_df.to_csv(out / "gold_v3_02_excluded_entry_times.csv", index=False, encoding="utf-8-sig")
    decision_df.to_csv(out / "gold_v3_02_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blocker_df.to_csv(out / "gold_v3_02_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "gold_v3_02_label_contract.json", contract_obj)
    write_json(out / "gold_v3_02_summary.json", summary)
    report = "\n".join([
        "# GOLD V3 02 label contract audit-only report",
        "",
        f"Created UTC: {created}",
        f"Status: `{status}`",
        "",
        "## Contract",
        f"- strategy_id: `{STRATEGY_ID}`",
        "- M15 closed-bar entry contract, M5 first-touch evaluation contract, TP10/SL5/H28.",
        "- Outcomes are not evaluated in this step.",
        "- ZIP output is disabled.",
        "",
        "## Audit summary",
        md(audit_summary),
        "",
        "## Decision matrix",
        md(decision_df),
        "",
        "## Excluded entries by reason",
        md(pd.DataFrame([{"reason": k, "count": v} for k, v in excluded_counts.items()])),
        "",
        "## Blockers",
        md(blocker_df),
        "",
        "## Safety",
        "- GOLD V3 only; no V2 artifacts used.",
        "- No features, no evaluated labels/outcomes, no candidates, no signals.",
        "- No ZIP package is written.",
        "- Discord/MT5/AI/live/final remain OFF.",
    ])
    (out / "GOLD_V3_02_LABEL_CONTRACT_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "output_dir": str(out), "zip_output_created": False}, ensure_ascii=False, indent=2))
    print("No ZIP, features, evaluated labels, signals, Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
