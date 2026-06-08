#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "GOLD_V3_01_CANDLE_NORMALIZATION_TIME_AUDIT"
OUT_NAME = "01_candle_normalization_time_audit"
SOURCE_SET = "gold_hash_2025_primary"
SYMBOL = "GOLD#"
TIMEFRAMES = ["m1", "m5", "m15", "h1", "h4", "d1"]
EXPECTED_ROWS = {"m1": 353074, "m5": 70684, "m15": 23563, "h1": 5894, "h4": 1541, "d1": 258}
STEP_MIN = {"m1": 1, "m5": 5, "m15": 15, "h1": 60, "h4": 240, "d1": 1440}
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def fx_inputs_root() -> Path:
    return files_root() / "FX_INPUTS"


def fx_outputs_root() -> Path:
    return files_root() / "FX_OUTPUTS"


def raw_dir() -> Path:
    return fx_inputs_root() / "gold_v3" / "raw_candles"


def v3_output_root() -> Path:
    return fx_outputs_root() / "gold_v3"


def out_dir() -> Path:
    p = v3_output_root() / OUT_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def canonical_dir() -> Path:
    p = out_dir() / "canonical_candles"
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


def read_primary(tf: str) -> tuple[Path | None, pd.DataFrame]:
    p = raw_dir() / f"gold#_{tf}.csv"
    if not p.exists():
        return None, pd.DataFrame()
    df = pd.read_csv(p, sep=";", encoding="utf-8-sig")
    return p, df


def normalize(tf: str, p: Path, df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["time_utc"] = pd.to_datetime(d["time_utc"] if "time_utc" in d.columns else d["time"], errors="coerce", utc=True)
    if "time_jst" in d.columns:
        j = pd.to_datetime(d["time_jst"], errors="coerce")
        d["time_jst"] = j.dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        d["time_jst"] = (d["time_utc"] + pd.Timedelta(hours=9)).dt.strftime("%Y-%m-%d %H:%M:%S")
    for c in ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]:
        d[c] = pd.to_numeric(d[c], errors="coerce") if c in d.columns else 0
    d = d.sort_values("time_utc").reset_index(drop=True)
    d["symbol"] = SYMBOL
    d["source_set"] = SOURCE_SET
    d["timeframe"] = tf.upper()
    d["bar_index"] = range(len(d))
    d["source_file"] = p.name
    d["source_sha256"] = sha256_file(p)
    d["time_utc"] = d["time_utc"].dt.strftime("%Y-%m-%d %H:%M:%S%z")
    cols = ["symbol", "source_set", "timeframe", "time_utc", "time_jst", "open", "high", "low", "close", "tick_volume", "spread", "real_volume", "bar_index", "source_file", "source_sha256"]
    return d[cols]


def audit(tf: str, norm: pd.DataFrame, expected: int) -> dict[str, Any]:
    t = pd.to_datetime(norm["time_utc"], errors="coerce", utc=True)
    o = pd.to_numeric(norm["open"], errors="coerce")
    h = pd.to_numeric(norm["high"], errors="coerce")
    l = pd.to_numeric(norm["low"], errors="coerce")
    c = pd.to_numeric(norm["close"], errors="coerce")
    gaps = t.diff().dt.total_seconds() / 60.0
    step = STEP_MIN[tf]
    dup = int(t.duplicated().sum())
    null_ohlc = int((o.isna() | h.isna() | l.isna() | c.isna()).sum())
    invalid = int(((h < pd.concat([o, c], axis=1).max(axis=1)) | (l > pd.concat([o, c], axis=1).min(axis=1))).sum())
    non_mono = int((gaps.dropna() <= 0).sum())
    large_gap = int((gaps.dropna() > step * 3).sum())
    weekend = int(t.dt.weekday.isin([5, 6]).sum())
    if tf in ["m1", "m5", "m15"]:
        mod_ok = bool((t.dt.minute % step).eq(0).all())
    elif tf == "h1":
        mod_ok = bool(t.dt.minute.eq(0).all())
    elif tf == "h4":
        mod_ok = bool((t.dt.minute.eq(0) & (t.dt.hour % 4).eq(0)).all())
    else:
        mod_ok = bool((t.dt.hour.eq(0) & t.dt.minute.eq(0)).all())
    return {
        "timeframe": tf.upper(),
        "row_count": int(len(norm)),
        "expected_row_count": expected,
        "row_count_match": int(len(norm)) == expected,
        "first_time_utc": str(t.iloc[0]) if len(t) else None,
        "last_time_utc": str(t.iloc[-1]) if len(t) else None,
        "duplicate_time_count": dup,
        "non_monotonic_count": non_mono,
        "null_ohlc_rows": null_ohlc,
        "invalid_ohlc_rows": invalid,
        "weekend_rows": weekend,
        "max_gap_minutes": float(gaps.max()) if len(gaps.dropna()) else None,
        "large_gap_count": large_gap,
        "open_minute_mod_ok": mod_ok,
        "hard_ok": int(len(norm)) == expected and dup == 0 and non_mono == 0 and null_ohlc == 0 and invalid == 0 and mod_ok,
    }


def inventory_row(tf: str, p: Path | None, df: pd.DataFrame) -> dict[str, Any]:
    return {
        "timeframe": tf.upper(),
        "required_file": f"gold#_{tf}.csv",
        "exists": bool(p and p.exists()),
        "path": str(p) if p else "",
        "rows": int(len(df)) if not df.empty else 0,
        "expected_rows": EXPECTED_ROWS[tf],
        "sha256": sha256_file(p) if p and p.exists() else "",
        "columns": ";".join(df.columns) if not df.empty else "",
    }


def cross_alignment(canon: dict[str, pd.DataFrame]) -> pd.DataFrame:
    pairs = [("m5", "m1"), ("m15", "m5"), ("h1", "m15"), ("h4", "h1"), ("d1", "h4")]
    rows = []
    sets = {tf: set(pd.to_datetime(df["time_utc"], utc=True).astype(str)) for tf, df in canon.items()}
    for child, parent in pairs:
        child_set = sets.get(child, set())
        parent_set = sets.get(parent, set())
        missing = sorted(child_set - parent_set)
        rows.append({
            "child_timeframe": child.upper(),
            "parent_timeframe": parent.upper(),
            "child_rows": len(child_set),
            "missing_from_parent": len(missing),
            "subset_ok": len(missing) == 0,
            "severity": "WARN" if child == "d1" and missing else "HARD",
            "sample_missing": ";".join(missing[:10]),
        })
    return pd.DataFrame(rows)


def main() -> int:
    created = datetime.now(timezone.utc).isoformat()
    out = out_dir()
    canon_dir = canonical_dir()
    inv_rows = []
    audit_rows = []
    manifest_rows = []
    canon: dict[str, pd.DataFrame] = {}
    for tf in TIMEFRAMES:
        p, df = read_primary(tf)
        inv_rows.append(inventory_row(tf, p, df))
        if p is None or df.empty:
            continue
        nd = normalize(tf, p, df)
        canon[tf] = nd
        out_csv = canon_dir / f"gold_v3_gold_hash_2025_primary_{tf}.csv"
        nd.to_csv(out_csv, index=False, encoding="utf-8-sig")
        audit_rows.append(audit(tf, nd, EXPECTED_ROWS[tf]))
        manifest_rows.append({"timeframe": tf.upper(), "canonical_csv": str(out_csv), "rows": len(nd), "sha256": sha256_file(out_csv), "source_file": str(p)})
    inv_df = pd.DataFrame(inv_rows)
    audit_df = pd.DataFrame(audit_rows)
    manifest_df = pd.DataFrame(manifest_rows)
    cross_df = cross_alignment(canon) if len(canon) == len(TIMEFRAMES) else pd.DataFrame()

    inputs_ok = bool(inv_df["exists"].all() and inv_df["rows"].eq(inv_df["expected_rows"]).all())
    hard_time_ok = bool(audit_df["hard_ok"].all()) if not audit_df.empty else False
    hard_cross_ok = True
    if not cross_df.empty:
        hard_cross = cross_df[cross_df["severity"].eq("HARD")]
        hard_cross_ok = bool(hard_cross["subset_ok"].all())
    if not inputs_ok:
        status = "GOLD_V3_01_CANDLE_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif not (hard_time_ok and hard_cross_ok):
        status = "GOLD_V3_01_CANDLE_TIME_AUDIT_BLOCKED_AUDIT_ONLY"
    else:
        status = "GOLD_V3_01_CANDLE_NORMALIZATION_TIME_AUDIT_READY_AUDIT_ONLY"
    decision_df = pd.DataFrame([
        ["primary_files_present_and_row_counts_match", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["timeframe_hard_checks_ok", hard_time_ok, True, "PASS" if hard_time_ok else "FAIL"],
        ["cross_timeframe_hard_alignment_ok", hard_cross_ok, True, "PASS" if hard_cross_ok else "FAIL"],
        ["features_created", False, False, "PASS"],
        ["labels_created", False, False, "PASS"],
        ["signals_generated", False, False, "PASS"],
        ["external_actions", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blocker_rows = [
        ["G3-01-001", "primary input files", "CLOSED" if inputs_ok else "OPEN", "HARD", "All GOLD# primary files and expected rows required."],
        ["G3-01-002", "time/OHLC hard checks", "CLOSED" if hard_time_ok else "OPEN", "HARD", "Duplicate/null/invalid/modulo checks must pass."],
        ["G3-01-003", "cross timeframe hard alignment", "CLOSED" if hard_cross_ok else "OPEN", "HARD", "M5/M15/H1/H4 containment must pass."],
        ["G3-01-004", "D1/H4 session alignment", "REVIEW" if not cross_df.empty and bool((cross_df[(cross_df["child_timeframe"].eq("D1"))]["missing_from_parent"] > 0).any()) else "CLOSED", "WARN", "D1/H4 broker session convention may differ."],
        ["G3-01-005", "external actions", "CLOSED", "HARD", "No external actions performed."],
    ]
    blocker_df = pd.DataFrame(blocker_rows, columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_recovery_approved": False,
        "inputs_ok": inputs_ok,
        "hard_time_ok": hard_time_ok,
        "hard_cross_ok": hard_cross_ok,
        "canonical_dir": str(canon_dir),
        "external_actions": ACTIONS,
    }

    inv_df.to_csv(out / "gold_v3_01_primary_input_inventory.csv", index=False, encoding="utf-8-sig")
    manifest_df.to_csv(out / "gold_v3_01_normalized_candle_manifest.csv", index=False, encoding="utf-8-sig")
    audit_df.to_csv(out / "gold_v3_01_timeframe_audit.csv", index=False, encoding="utf-8-sig")
    cross_df.to_csv(out / "gold_v3_01_cross_timeframe_alignment.csv", index=False, encoding="utf-8-sig")
    decision_df.to_csv(out / "gold_v3_01_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blocker_df.to_csv(out / "gold_v3_01_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "gold_v3_01_summary.json", summary)

    report = "\n".join([
        "# GOLD V3 01 candle normalization and time audit report",
        "",
        f"Created UTC: {created}",
        f"Status: `{status}`",
        "",
        "## Decision matrix",
        decision_df.to_markdown(index=False),
        "",
        "## Timeframe audit",
        audit_df.to_markdown(index=False),
        "",
        "## Cross-timeframe alignment",
        cross_df.to_markdown(index=False) if not cross_df.empty else "_No rows._",
        "",
        "## Blockers",
        blocker_df.to_markdown(index=False),
        "",
        "## Safety",
        "- GOLD V3 only; no V2 artifacts used.",
        "- No features, no labels, no signals.",
        "- Discord/MT5/AI/live/final remain OFF.",
    ])
    (out / "GOLD_V3_01_CANDLE_NORMALIZATION_TIME_AUDIT_REPORT.md").write_text(report, encoding="utf-8")

    zip_path = v3_output_root() / f"{OUT_NAME}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            if p.is_file():
                z.write(p, arcname=p.name)
        for p in canon_dir.iterdir():
            if p.is_file():
                z.write(p, arcname=f"canonical_candles/{p.name}")
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2))
    print("No features, labels, signals, Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
