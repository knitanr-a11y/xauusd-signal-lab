#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 12J: build CoreB required feature snapshot audit-only.

This script builds candidate feature columns required by the audit-only CoreB
mapping. It does not change signal conditions, evaluate signals, connect step 13,
or perform external actions.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import pandas as pd

POLICY_DEFAULT = "configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json"
COREB_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_coreB_20260603.json"
COREB_COMPONENT = "HIGH_B_CoreB_RR125_BUY_CONFLUENCE"
EXTERNAL_ACTIONS_OFF = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}
FORMULA_STATUS = "CANDIDATE_FORMULA_REQUIRES_SOURCE_VERIFICATION"

@dataclass
class AuditCheck:
    check_name: str
    status: str
    message: str
    detail: str = ""


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build GOLD V2 CoreB required feature snapshot audit-only")
    p.add_argument("--policy", default=POLICY_DEFAULT)
    p.add_argument("--coreb-mapping", default=COREB_MAPPING_DEFAULT)
    p.add_argument("--m15-csv", default=None)
    p.add_argument("--m5-csv", default=None)
    p.add_argument("--search-root", action="append", default=[])
    p.add_argument("--audit-output-dir", default=None)
    p.add_argument("--max-rows", type=int, default=0, help="0 means all rows")
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def default_search_roots() -> List[Path]:
    roots = [files_dir_from_repo(), repo_root()]
    out: List[Path] = []
    seen: Set[str] = set()
    for p in roots:
        rp = p.resolve()
        if rp.exists() and str(rp) not in seen:
            out.append(rp)
            seen.add(str(rp))
    return out


def default_audit_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_coreb_required_feature_snapshot_audit_only"


def resolve_path(text: str) -> Path:
    p = Path(text).expanduser()
    return p.resolve() if p.is_absolute() else (repo_root() / p).resolve()


def add_check(rows: List[AuditCheck], name: str, ok: bool, message: str, detail: str = "") -> None:
    rows.append(AuditCheck(name, "OK" if ok else "ERROR", message, detail))


def load_json(label: str, path: Path, checks: List[AuditCheck]) -> Optional[Dict[str, Any]]:
    if not path.exists():
        add_check(checks, f"{label}_exists", False, f"missing: {path}")
        return None
    add_check(checks, f"{label}_exists", True, str(path))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        add_check(checks, f"{label}_parse", False, "JSON parse failed", repr(exc))
        return None


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def validate_policy(policy: Dict[str, Any], checks: List[AuditCheck]) -> bool:
    safety = policy.get("safety", {})
    ok = True
    for key in ["ai_api_enabled", "discord_enabled", "mt5_order_enabled", "live_hook_enabled"]:
        flag_ok = safety.get(key) is False
        add_check(checks, f"safety_{key}_false", flag_ok, f"{key}={safety.get(key)!r}")
        ok = ok and flag_ok
    audit_ok = safety.get("audit_only") is True
    add_check(checks, "safety_audit_only_true", audit_ok, f"audit_only={safety.get('audit_only')!r}")
    return ok and audit_ok


def required_fields(mapping: Dict[str, Any]) -> List[str]:
    return sorted({str(c.get("field")) for c in mapping.get("mapped_conditions", []) or [] if c.get("field")})


def normalize_ohlc_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename: Dict[str, str] = {}
    lower = {str(c).lower().strip(): c for c in df.columns}
    aliases = {
        "time": ["time", "datetime", "date", "timestamp", "open_time", "entry_time"],
        "open": ["open", "o"],
        "high": ["high", "h"],
        "low": ["low", "l"],
        "close": ["close", "c"],
    }
    for target, names in aliases.items():
        for n in names:
            if n in lower:
                rename[lower[n]] = target
                break
    out = df.rename(columns=rename).copy()
    if "time" in out.columns:
        out["time"] = pd.to_datetime(out["time"], errors="coerce")
        out = out.dropna(subset=["time"]).sort_values("time").drop_duplicates(subset=["time"], keep="last")
    for c in ["open", "high", "low", "close"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def has_ohlc_header(path: Path) -> bool:
    try:
        cols = [str(c).lower().strip() for c in pd.read_csv(path, nrows=0).columns]
    except Exception:
        return False
    return any(c in cols for c in ["time", "datetime", "date", "timestamp", "open_time"]) and all(c in cols for c in ["open", "high", "low", "close"])


def find_ohlc_csv(roots: Iterable[Path], timeframe: str) -> Optional[Path]:
    tf = timeframe.lower()
    scored: List[Tuple[int, Path]] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.csv"):
            name = p.name.lower()
            if tf not in name:
                continue
            if any(skip in name for skip in ["audit", "report", "summary", "mapping", "ledger", "condition"]):
                continue
            if has_ohlc_header(p):
                score = 0
                if "gold" in name or "xau" in name:
                    score += 5
                if "sharp" in name:
                    score += 2
                if name.startswith("gold"):
                    score += 2
                scored.append((score, p.resolve()))
    if not scored:
        return None
    scored.sort(key=lambda x: (x[0], str(x[1])), reverse=True)
    return scored[0][1]


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    return pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)


def compute_base_features(df: pd.DataFrame, prefix: str = "") -> pd.DataFrame:
    out = pd.DataFrame({"time": df["time"]})
    tr = true_range(df)
    atr = tr.rolling(14, min_periods=14).mean().replace(0, pd.NA)
    out[prefix + "atr14_candidate"] = atr
    for n in sorted({4, 16, 24, 32, 48, 72, 96, 144}):
        roll_high = df["high"].rolling(n, min_periods=n).max()
        roll_low = df["low"].rolling(n, min_periods=n).min()
        rng = (roll_high - roll_low).replace(0, pd.NA)
        out[prefix + f"ret_{n}_atr"] = (df["close"] - df["close"].shift(n)) / atr
        out[prefix + f"abs_ret_{n}_atr"] = out[prefix + f"ret_{n}_atr"].abs()
        out[prefix + f"range_{n}_atr"] = (roll_high - roll_low) / atr
        out[prefix + f"dist_low_{n}_atr"] = (df["close"] - roll_low) / atr
        out[prefix + f"dist_high_{n}_atr"] = (roll_high - df["close"]) / atr
        out[prefix + f"donch_pos_{n}"] = (df["close"] - roll_low) / rng
    for period in [20, 50, 100]:
        ema = df["close"].ewm(span=period, adjust=False, min_periods=period).mean()
        for n in [4, 16]:
            out[prefix + f"ema{period}_slope_{n}_atr"] = (ema - ema.shift(n)) / atr
    for a, b in [(16, 96), (32, 96), (48, 144)]:
        a_col = prefix + f"range_{a}_atr"
        b_col = prefix + f"range_{b}_atr"
        out[prefix + f"compression_range_{a}_{b}"] = out[a_col] / out[b_col].replace(0, pd.NA)
    out[prefix + "upper_wick_atr"] = (df["high"] - pd.concat([df["open"], df["close"]], axis=1).max(axis=1)) / atr
    return out


def read_ohlc(path: Path, max_rows: int, checks: List[AuditCheck], label: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
        if max_rows and len(df) > max_rows:
            df = df.tail(max_rows).copy()
        df = normalize_ohlc_columns(df)
    except Exception as exc:
        add_check(checks, f"{label}_read", False, str(path), repr(exc))
        return pd.DataFrame()
    needed = {"time", "open", "high", "low", "close"}
    ok = needed.issubset(df.columns) and not df.empty
    add_check(checks, f"{label}_ohlc_ready", ok, f"{path} rows={len(df)}")
    return df if ok else pd.DataFrame()


def build_snapshot(m15: pd.DataFrame, m5: pd.DataFrame, fields: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    m15_feat = compute_base_features(m15, prefix="")
    out = m15_feat.copy()
    if not m5.empty:
        m5_feat = compute_base_features(m5, prefix="m5_").sort_values("time")
        out = pd.merge_asof(out.sort_values("time"), m5_feat.sort_values("time"), on="time", direction="backward")
    for f in fields:
        if f not in out.columns:
            out[f] = pd.NA
    keep_cols = ["time"] + fields
    out = out[keep_cols].copy()
    schema_rows = []
    for f in fields:
        schema_rows.append({
            "field": f,
            "present_in_snapshot": f in out.columns,
            "non_null_count": int(out[f].notna().sum()) if f in out.columns else 0,
            "formula_status": FORMULA_STATUS,
        })
    return out, pd.DataFrame(schema_rows)


def build_report(summary: Dict[str, Any]) -> str:
    lines = [
        "# GOLD V2 CoreB required feature snapshot audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Status: `{summary['status']}`",
        f"Audit only: `{summary['audit_only']}`",
        f"feature_formula_status: `{summary['feature_formula_status']}`",
        f"m15_csv: `{summary.get('m15_csv')}`",
        f"m5_csv: `{summary.get('m5_csv')}`",
        f"row_count: `{summary['row_count']}`",
        f"required_field_count: `{summary['required_field_count']}`",
        f"present_field_count: `{summary['present_field_count']}`",
        "",
        "## Safety",
        "",
        f"live_evaluator_connection_allowed: `{summary['live_evaluator_connection_allowed']}`",
        f"final_signal_allowed: `{summary['final_signal_allowed']}`",
        f"step13_allowed: `{summary['step13_allowed']}`",
        f"notification_should_send: `{summary['notification_should_send']}`",
        "",
        "## Important",
        "",
        "This creates candidate feature columns only. It does not change CoreB rules or evaluate signals.",
        "Feature formulas require source verification before any evaluator use.",
    ]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.audit_output_dir).expanduser().resolve() if args.audit_output_dir else default_audit_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    checks: List[AuditCheck] = []
    policy = load_json("policy", resolve_path(args.policy), checks) or {}
    policy_ok = validate_policy(policy, checks) if policy else False
    mapping = load_json("coreb_mapping", resolve_path(args.coreb_mapping), checks)
    mapping_ok = bool(mapping and mapping.get("status") == "MAPPING_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED" and mapping.get("component") == COREB_COMPONENT)
    add_check(checks, "coreb_mapping_ready_audit_only", mapping_ok, str(mapping.get("status") if mapping else None))
    fields = required_fields(mapping or {})
    roots = [resolve_path(x) for x in args.search_root] if args.search_root else default_search_roots()
    m15_path = resolve_path(args.m15_csv) if args.m15_csv else find_ohlc_csv(roots, "m15")
    m5_path = resolve_path(args.m5_csv) if args.m5_csv else find_ohlc_csv(roots, "m5")
    add_check(checks, "m15_csv_found", m15_path is not None, str(m15_path))
    add_check(checks, "m5_csv_found", m5_path is not None, str(m5_path))
    m15 = read_ohlc(m15_path, int(args.max_rows), checks, "m15") if m15_path else pd.DataFrame()
    m5 = read_ohlc(m5_path, int(args.max_rows), checks, "m5") if m5_path else pd.DataFrame()
    if not m15.empty and mapping_ok and policy_ok:
        snapshot, schema = build_snapshot(m15, m5, fields)
    else:
        snapshot = pd.DataFrame(columns=["time"] + fields)
        schema = pd.DataFrame([{"field": f, "present_in_snapshot": f in snapshot.columns, "non_null_count": 0, "formula_status": FORMULA_STATUS} for f in fields])
    snapshot_path = out_dir / "gold_v2_coreb_required_feature_snapshot.csv"
    schema_path = out_dir / "gold_v2_coreb_required_feature_schema.csv"
    snapshot.to_csv(snapshot_path, index=False, encoding="utf-8-sig")
    schema.to_csv(schema_path, index=False, encoding="utf-8-sig")
    present_count = int(schema["present_in_snapshot"].sum()) if not schema.empty else 0
    non_null_ready = int((schema["non_null_count"] > 0).sum()) if not schema.empty else 0
    if not policy_ok or not mapping_ok:
        status = "COREB_REQUIRED_FEATURE_SNAPSHOT_BLOCKED_POLICY_OR_MAPPING"
    elif m15.empty:
        status = "COREB_REQUIRED_FEATURE_SNAPSHOT_BLOCKED_NO_M15_OHLC"
    elif present_count < len(fields):
        status = "COREB_REQUIRED_FEATURE_SNAPSHOT_SCHEMA_INCOMPLETE"
    else:
        status = "COREB_REQUIRED_FEATURE_SNAPSHOT_READY_FORMULA_UNVERIFIED_AUDIT_ONLY"
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "audit_only": True,
        "policy_safety_ok": bool(policy_ok),
        "mapping_ok": bool(mapping_ok),
        "feature_formula_status": FORMULA_STATUS,
        "m15_csv": str(m15_path) if m15_path else None,
        "m5_csv": str(m5_path) if m5_path else None,
        "row_count": int(len(snapshot)),
        "required_field_count": int(len(fields)),
        "present_field_count": present_count,
        "non_null_ready_field_count": non_null_ready,
        "snapshot_csv": str(snapshot_path),
        "schema_csv": str(schema_path),
        "live_evaluator_connection_allowed": False,
        "final_signal_allowed": False,
        "step13_allowed": False,
        "notification_should_send": False,
        "external_actions": dict(EXTERNAL_ACTIONS_OFF),
        "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL",
        "output_dir": str(out_dir),
        "important_note": "Feature headers are candidate/generated for audit only. Formula source verification remains required. No signal conditions were changed.",
    }
    pd.DataFrame([asdict(c) for c in checks]).to_csv(out_dir / "gold_v2_coreb_feature_build_audit_checks.csv", index=False, encoding="utf-8-sig")
    write_json(out_dir / "gold_v2_coreb_required_feature_snapshot_summary.json", summary)
    (out_dir / "GOLD_V2_COREB_REQUIRED_FEATURE_SNAPSHOT_AUDIT_ONLY_REPORT.md").write_text(build_report(summary), encoding="utf-8")
    print(f"[DONE] status={status} audit_dir={out_dir}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("Candidate feature snapshot only. Step 13 remains blocked.")
    if not policy_ok or not mapping_ok or m15.empty:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
