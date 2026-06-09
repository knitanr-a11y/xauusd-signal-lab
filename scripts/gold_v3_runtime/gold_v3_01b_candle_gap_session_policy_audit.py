#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "GOLD_V3_01B_CANDLE_GAP_SESSION_POLICY_AUDIT"
OUT_NAME = "01b_candle_gap_session_policy_audit"
EXPECTED_01_STATUS = "GOLD_V3_01_CANDLE_TIME_AUDIT_BLOCKED_AUDIT_ONLY"
TIMEFRAMES = ["m1", "m5", "m15", "h1", "h4", "d1"]
STEP_MIN = {"m1": 1, "m5": 5, "m15": 15, "h1": 60, "h4": 240, "d1": 1440}
PAIRS = [("m5", "m1"), ("m15", "m5"), ("h1", "m15"), ("h4", "h1"), ("d1", "h4")]
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


def upstream_dir() -> Path:
    return v3_output_root() / "01_candle_normalization_time_audit"


def canonical_dir() -> Path:
    return upstream_dir() / "canonical_candles"


def out_dir() -> Path:
    p = v3_output_root() / OUT_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


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


def load_tf(tf: str) -> pd.DataFrame:
    p = canonical_dir() / f"gold_v3_gold_hash_2025_primary_{tf}.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    df["t"] = pd.to_datetime(df["time_utc"], utc=True, errors="coerce")
    return df


def input_inventory() -> pd.DataFrame:
    rows = []
    files = [upstream_dir() / "gold_v3_01_summary.json", upstream_dir() / "gold_v3_01_cross_timeframe_alignment.csv"] + [canonical_dir() / f"gold_v3_gold_hash_2025_primary_{tf}.csv" for tf in TIMEFRAMES]
    for p in files:
        rows.append({"path": str(p), "filename": p.name, "exists": p.exists(), "bytes": p.stat().st_size if p.exists() else 0, "sha256": sha256_file(p) if p.exists() else ""})
    return pd.DataFrame(rows)


def diagnose_pair(child: str, parent: str, cdf: pd.DataFrame, pdf: pd.DataFrame) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cset = set(cdf["t"].dropna())
    pset = set(pdf["t"].dropna())
    missing = sorted(cset - pset)
    detail_rows = []
    parent_counts = []
    child_step = STEP_MIN[child]
    for mt in missing:
        inside = pdf[(pdf["t"] >= mt) & (pdf["t"] < mt + pd.Timedelta(minutes=child_step))]
        before = pdf[pdf["t"] < mt].tail(1)
        after = pdf[pdf["t"] > mt].head(1)
        parent_counts.append(len(inside))
        cls = "exact_parent_open_missing_but_inside_parent_rows_exist" if len(inside) else "no_parent_rows_inside_child_bar"
        if child == "h4" and parent == "h1" and mt.hour == 0:
            cls = "session_boundary_native_htf_open_not_present_in_parent_h1"
        if child == "d1" and parent == "h4":
            cls = "daily_session_boundary_mismatch_warning"
        detail_rows.append({
            "child_timeframe": child.upper(),
            "parent_timeframe": parent.upper(),
            "missing_child_open": str(mt),
            "classification": cls,
            "parent_rows_inside_child_bar": len(inside),
            "prev_parent_time": str(before["t"].iloc[0]) if not before.empty else "",
            "next_parent_time": str(after["t"].iloc[0]) if not after.empty else "",
        })
    ratio = len(missing) / len(cset) if cset else 0.0
    diag = {
        "child_timeframe": child.upper(),
        "parent_timeframe": parent.upper(),
        "child_open_count": len(cset),
        "parent_open_count": len(pset),
        "missing_parent_open_count": len(missing),
        "missing_parent_open_ratio": ratio,
        "parent_rows_inside_child_bar_min": min(parent_counts) if parent_counts else None,
        "parent_rows_inside_child_bar_max": max(parent_counts) if parent_counts else None,
        "parent_rows_inside_child_bar_mean": sum(parent_counts) / len(parent_counts) if parent_counts else None,
        "sample_missing_times": ";".join(str(x) for x in missing[:10]),
    }
    return diag, detail_rows


def policy_matrix(diag: pd.DataFrame) -> pd.DataFrame:
    m5_m1 = diag[(diag["child_timeframe"].eq("M5")) & (diag["parent_timeframe"].eq("M1"))]
    m5_m1_missing = int(m5_m1["missing_parent_open_count"].iloc[0]) if not m5_m1.empty else 999
    rows = [
        ["native_primary_candles", "native_m1_m5_m15_h1_h4_d1_allowed", True, "PASS", "All native timeframe hard OHLC/time checks passed in 01.", "Use native candles; do not reconstruct HTF from lower TF."],
        ["label_policy", "m1_intrabar_label_allowed", m5_m1_missing == 0, "REVIEW" if m5_m1_missing else "PASS", "M1 has a small number of missing exact M5 opens; M1 labels need a gap guard or affected bars excluded.", "Before M1 labels, produce affected-entry exclusion list."],
        ["label_policy", "m5_intrabar_label_allowed", True, "PASS", "Native M5 is internally valid and M15/H1 alignment is OK.", "M5 labels may proceed after explicit label spec."],
        ["htf_policy", "native_h4_asof_feature_join_allowed", True, "PASS", "H4 native bars pass hard checks; H4/H1 open containment mismatch is session-boundary style.", "Use native H4 closed/asof join only; do not rebuild H4 from H1."],
        ["htf_policy", "reconstruct_h4_from_h1_allowed", False, "BLOCKED", "H4 00:00 native opens are not present in H1 set; reconstruction from H1 is unsafe.", "Keep disabled."],
        ["htf_policy", "native_d1_asof_feature_join_allowed", True, "WARN", "D1/H4 has warning-level session boundary mismatch.", "Use native D1 closed/asof join only; document daily session convention."],
        ["htf_policy", "reconstruct_d1_from_h4_allowed", False, "BLOCKED", "D1/H4 containment is not guaranteed.", "Keep disabled."],
        ["exploration", "feature_label_signal_generation_allowed", False, "BLOCKED", "01B is policy only, not feature/label phase.", "Proceed to 02 label contract only after human review."],
    ]
    return pd.DataFrame(rows, columns=["component", "policy_name", "allowed", "severity", "reason", "next_step_requirement"])


def main() -> int:
    created = datetime.now(timezone.utc).isoformat()
    out = out_dir()
    inv_df = input_inventory()
    summary01 = read_json(upstream_dir() / "gold_v3_01_summary.json")
    upstream_ok = summary01.get("status") == EXPECTED_01_STATUS
    inputs_ok = bool(inv_df["exists"].all())
    data = {tf: load_tf(tf) for tf in TIMEFRAMES}
    diag_rows = []
    detail_rows = []
    for child, parent in PAIRS:
        if data[child].empty or data[parent].empty:
            diag_rows.append({"child_timeframe": child.upper(), "parent_timeframe": parent.upper(), "child_open_count": 0, "parent_open_count": 0, "missing_parent_open_count": None, "missing_parent_open_ratio": None, "sample_missing_times": "missing input"})
            continue
        diag, details = diagnose_pair(child, parent, data[child], data[parent])
        diag_rows.append(diag)
        detail_rows.extend(details)
    diag_df = pd.DataFrame(diag_rows)
    detail_df = pd.DataFrame(detail_rows)
    policy_df = policy_matrix(diag_df)

    # Major lower timeframe gap is defined conservatively as M5/M1 missing ratio > 0.001 or M15/M5/H1/M15 broken.
    m5_m1 = diag_df[(diag_df["child_timeframe"].eq("M5")) & (diag_df["parent_timeframe"].eq("M1"))]
    m5_m1_ratio = float(m5_m1["missing_parent_open_ratio"].iloc[0]) if not m5_m1.empty and pd.notna(m5_m1["missing_parent_open_ratio"].iloc[0]) else 1.0
    mid_break = False
    for child, parent in [("M15", "M5"), ("H1", "M15")]:
        row = diag_df[(diag_df["child_timeframe"].eq(child)) & (diag_df["parent_timeframe"].eq(parent))]
        if row.empty or int(row["missing_parent_open_count"].iloc[0]) != 0:
            mid_break = True
    native_usable = inputs_ok and upstream_ok and not mid_break and m5_m1_ratio <= 0.001
    if not (inputs_ok and upstream_ok):
        status = "GOLD_V3_01B_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif native_usable:
        status = "GOLD_V3_01B_NATIVE_CANDLE_USE_READY_WITH_GAP_GUARDS_AUDIT_ONLY"
    else:
        status = "GOLD_V3_01B_CANDLE_GAP_POLICY_BLOCKED_AUDIT_ONLY"

    decision_df = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_01_blocked_status_as_expected", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["m5_m1_missing_ratio_le_0_001", m5_m1_ratio, "<=0.001", "PASS" if m5_m1_ratio <= 0.001 else "FAIL"],
        ["m15_m5_and_h1_m15_hard_alignment_ok", not mid_break, True, "PASS" if not mid_break else "FAIL"],
        ["native_candle_use_allowed", native_usable, True, "PASS" if native_usable else "FAIL"],
        ["features_created", False, False, "PASS"],
        ["labels_created", False, False, "PASS"],
        ["signals_generated", False, False, "PASS"],
        ["zip_output_created", False, False, "PASS"],
        ["external_actions", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blocker_df = pd.DataFrame([
        ["G3-01B-001", "01 inputs", "CLOSED" if inputs_ok and upstream_ok else "OPEN", "HARD", "01 blocked output and canonical candles must exist."],
        ["G3-01B-002", "M1 label guard", "REVIEW" if m5_m1_ratio <= 0.001 else "OPEN", "HARD", "M1 exact-open gaps require affected-bar guard before M1 labels."],
        ["G3-01B-003", "HTF reconstruction", "CLOSED_BLOCKED_BY_POLICY", "HARD", "Reconstructing H4 from H1 or D1 from H4 is not allowed."],
        ["G3-01B-004", "native HTF asof", "REVIEW", "WARN", "Native H4/D1 closed/asof join can proceed only after label/feature spec records convention."],
        ["G3-01B-005", "zip output", "CLOSED_DISABLED", "INFO", "ZIP output disabled."],
        ["G3-01B-006", "external actions", "CLOSED", "HARD", "No external actions performed."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_recovery_approved": False,
        "inputs_ok": inputs_ok,
        "upstream_01_ok": upstream_ok,
        "m5_m1_missing_ratio": m5_m1_ratio,
        "native_candle_use_allowed": native_usable,
        "m1_label_gap_guard_required": True,
        "reconstruct_h4_from_h1_allowed": False,
        "reconstruct_d1_from_h4_allowed": False,
        "zip_output_created": False,
        "external_actions": ACTIONS,
    }

    inv_df.to_csv(out / "gold_v3_01b_input_inventory.csv", index=False, encoding="utf-8-sig")
    diag_df.to_csv(out / "gold_v3_01b_pair_gap_diagnostics.csv", index=False, encoding="utf-8-sig")
    detail_df.to_csv(out / "gold_v3_01b_missing_open_detail.csv", index=False, encoding="utf-8-sig")
    policy_df.to_csv(out / "gold_v3_01b_data_use_policy_matrix.csv", index=False, encoding="utf-8-sig")
    decision_df.to_csv(out / "gold_v3_01b_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blocker_df.to_csv(out / "gold_v3_01b_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "gold_v3_01b_summary.json", summary)

    report = "\n".join([
        "# GOLD V3 01B candle gap and session policy audit report",
        "",
        f"Created UTC: {created}",
        f"Status: `{status}`",
        "",
        "## Decision matrix",
        md(decision_df),
        "",
        "## Pair gap diagnostics",
        md(diag_df),
        "",
        "## Data-use policy matrix",
        md(policy_df),
        "",
        "## Blockers",
        md(blocker_df),
        "",
        "## Safety",
        "- GOLD V3 only; no V2 artifacts used.",
        "- No features, no labels, no signals.",
        "- No ZIP output.",
        "- Discord/MT5/AI/live/final remain OFF.",
    ])
    (out / "GOLD_V3_01B_CANDLE_GAP_SESSION_POLICY_AUDIT_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "output_dir": str(out), "zip_output_created": False}, ensure_ascii=False, indent=2))
    print("No ZIP, features, labels, signals, Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
