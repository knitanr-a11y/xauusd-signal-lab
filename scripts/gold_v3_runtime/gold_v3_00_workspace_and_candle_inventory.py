#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, shutil, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "GOLD_V3_00_WORKSPACE_AND_CANDLE_INVENTORY"
OUT_NAME = "00_workspace_and_candle_inventory"
ACTIONS = {
    "discord_send_allowed": False,
    "mt5_order_allowed": False,
    "ai_api_allowed": False,
    "live_hook_allowed": False,
    "live_evaluator_allowed": False,
    "final_signal_allowed": False,
}
TIMEFRAMES = ["m1", "m5", "m15", "h1", "h4", "d1"]
PRIMARY_PREFIX = "gold#_"
REFERENCE_PREFIX = "goldsharp_"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def fx_inputs_root() -> Path:
    return files_root() / "FX_INPUTS"


def fx_outputs_root() -> Path:
    return files_root() / "FX_OUTPUTS"


def v3_input_raw() -> Path:
    return fx_inputs_root() / "gold_v3" / "raw_candles"


def v3_output_root() -> Path:
    return fx_outputs_root() / "gold_v3"


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


def sniff_sep(path: Path) -> str:
    raw = path.read_bytes()[:8192]
    text = raw.decode("utf-8-sig", errors="ignore")
    return ";" if text.count(";") >= text.count(",") else ","


def parse_time_series(df: pd.DataFrame) -> pd.Series | None:
    for c in ["time_utc", "time", "datetime", "date"]:
        if c in df.columns:
            s = pd.to_datetime(df[c], errors="coerce", utc=True)
            if s.notna().any():
                return s
    return None


def inspect_csv(path: Path) -> dict[str, Any]:
    sep = sniff_sep(path)
    header = pd.read_csv(path, sep=sep, nrows=0, encoding="utf-8-sig")
    row_count = sum(1 for _ in path.open("rb")) - 1
    sample = pd.read_csv(path, sep=sep, nrows=min(1000, max(row_count, 0)), encoding="utf-8-sig") if row_count > 0 else pd.DataFrame(columns=header.columns)
    ts = parse_time_series(sample)
    first_time = None
    last_time = None
    if row_count > 0:
        first_df = pd.read_csv(path, sep=sep, nrows=1, encoding="utf-8-sig")
        tail_df = pd.read_csv(path, sep=sep, skiprows=max(1, row_count), nrows=1, names=header.columns, header=None, encoding="utf-8-sig") if row_count > 1 else first_df
        t1 = parse_time_series(first_df)
        t2 = parse_time_series(tail_df)
        first_time = str(t1.iloc[0]) if t1 is not None and len(t1) else None
        last_time = str(t2.iloc[0]) if t2 is not None and len(t2) else None
    return {
        "path": str(path),
        "filename": path.name,
        "sep": sep,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "rows": int(max(row_count, 0)),
        "columns": ";".join(map(str, header.columns)),
        "first_time_utc_parse": first_time,
        "last_time_utc_parse": last_time,
    }


def classify_file(path: Path) -> tuple[str, str]:
    n = path.name.lower()
    if n.startswith(PRIMARY_PREFIX):
        return "primary_gold_hash_2025", n.replace(PRIMARY_PREFIX, "").replace(".csv", "")
    if n.startswith(REFERENCE_PREFIX):
        return "reference_goldsharp", n.replace(REFERENCE_PREFIX, "").replace(".csv", "")
    if n == "fetch_summary.json":
        return "primary_gold_hash_2025_metadata", "metadata"
    return "unknown", "unknown"


def find_input_candidates() -> list[Path]:
    roots = [v3_input_raw(), files_root(), repo_root(), Path.cwd()]
    names = [f"{PRIMARY_PREFIX}{tf}.csv" for tf in TIMEFRAMES] + [f"{REFERENCE_PREFIX}{tf}.csv" for tf in TIMEFRAMES] + ["fetch_summary.json"]
    found: dict[str, Path] = {}
    for root in roots:
        if not root.exists():
            continue
        for name in names:
            for p in root.rglob(name):
                found.setdefault(name, p)
    return [found[n] for n in names if n in found]


def ensure_workspace() -> pd.DataFrame:
    dirs = [
        fx_inputs_root() / "gold_v3",
        v3_input_raw(),
        v3_output_root(),
        v3_output_root() / "_run_index",
        v3_output_root() / "_archive",
        out_dir(),
    ]
    rows = []
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        rows.append({"directory": str(d), "exists": d.exists()})
    return pd.DataFrame(rows)


def copy_manifest(candidates: list[Path]) -> pd.DataFrame:
    rows = []
    for src in candidates:
        dst = v3_input_raw() / src.name
        copied = False
        if src.resolve() != dst.resolve():
            if not dst.exists() or sha256_file(src) != sha256_file(dst):
                shutil.copy2(src, dst)
                copied = True
        rows.append({"source_path": str(src), "dest_path": str(dst), "copied_or_updated": copied, "dest_exists": dst.exists()})
    return pd.DataFrame(rows)


def main() -> int:
    created = datetime.now(timezone.utc).isoformat()
    out = out_dir()
    workspace_df = ensure_workspace()
    candidates = find_input_candidates()
    copy_df = copy_manifest(candidates)

    inventory_rows = []
    for p in sorted(v3_input_raw().iterdir() if v3_input_raw().exists() else []):
        file_class, timeframe = classify_file(p)
        if p.suffix.lower() == ".csv":
            row = inspect_csv(p)
        elif p.suffix.lower() == ".json":
            obj = json.loads(p.read_text(encoding="utf-8-sig"))
            row = {"path": str(p), "filename": p.name, "sep": "", "bytes": p.stat().st_size, "sha256": sha256_file(p), "rows": None, "columns": ";".join(obj.keys()), "first_time_utc_parse": obj.get("start_utc"), "last_time_utc_parse": obj.get("end_utc")}
        else:
            continue
        row.update({"file_class": file_class, "timeframe": timeframe})
        inventory_rows.append(row)
    inv_df = pd.DataFrame(inventory_rows)

    source_rows = []
    for tf in TIMEFRAMES:
        primary = inv_df[(inv_df["file_class"].eq("primary_gold_hash_2025")) & (inv_df["timeframe"].eq(tf))] if not inv_df.empty else pd.DataFrame()
        ref = inv_df[(inv_df["file_class"].eq("reference_goldsharp")) & (inv_df["timeframe"].eq(tf))] if not inv_df.empty else pd.DataFrame()
        source_rows.append({
            "timeframe": tf.upper(),
            "primary_gold_hash_present": not primary.empty,
            "primary_rows": int(primary.iloc[0]["rows"]) if not primary.empty and pd.notna(primary.iloc[0]["rows"]) else None,
            "reference_goldsharp_present": not ref.empty,
            "reference_rows": int(ref.iloc[0]["rows"]) if not ref.empty and pd.notna(ref.iloc[0]["rows"]) else None,
            "v3_role": "primary_research_sot" if not primary.empty else "missing_primary",
            "notes": "goldsharp is auxiliary/reference until symbol and time conventions are reconciled",
        })
    source_df = pd.DataFrame(source_rows)

    expected_primary = {"m1", "m5", "m15", "h1", "h4", "d1"}
    primary_present = set(inv_df[inv_df["file_class"].eq("primary_gold_hash_2025")]["timeframe"].dropna().astype(str).str.lower()) if not inv_df.empty else set()
    primary_complete = expected_primary.issubset(primary_present)
    status = "GOLD_V3_00_WORKSPACE_CANDLE_INVENTORY_READY_AUDIT_ONLY" if primary_complete else "GOLD_V3_00_WORKSPACE_CANDLE_INVENTORY_INCOMPLETE_AUDIT_ONLY"
    decision_df = pd.DataFrame([
        ["workspace_created", bool(workspace_df["exists"].all()), True, "PASS" if bool(workspace_df["exists"].all()) else "FAIL"],
        ["primary_gold_hash_all_timeframes_present", primary_complete, True, "PASS" if primary_complete else "FAIL"],
        ["v2_files_modified", False, False, "PASS"],
        ["signals_generated", False, False, "PASS"],
        ["external_actions", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blocker_df = pd.DataFrame([
        ["G3-00-001", "GOLD# primary candle set", "CLOSED" if primary_complete else "OPEN", "HARD", "All primary GOLD# timeframes must be present before Phase 01."],
        ["G3-00-002", "V2 quarantine", "OPEN", "INFO", "V2 remains historical research only; no V3 reuse of V2 SOT artifacts."],
        ["G3-00-003", "Live/external actions", "CLOSED", "HARD", "No external actions performed."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])

    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_recovery_approved": False,
        "v3_input_raw": str(v3_input_raw()),
        "v3_output_root": str(v3_output_root()),
        "candidate_files_found": len(candidates),
        "primary_gold_hash_complete": primary_complete,
        "primary_present_timeframes": sorted(primary_present),
        "external_actions": ACTIONS,
    }

    workspace_df.to_csv(out / "gold_v3_00_workspace_directories.csv", index=False, encoding="utf-8-sig")
    copy_df.to_csv(out / "gold_v3_00_input_copy_manifest.csv", index=False, encoding="utf-8-sig")
    inv_df.to_csv(out / "gold_v3_00_candle_inventory.csv", index=False, encoding="utf-8-sig")
    source_df.to_csv(out / "gold_v3_00_source_selection_matrix.csv", index=False, encoding="utf-8-sig")
    decision_df.to_csv(out / "gold_v3_00_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blocker_df.to_csv(out / "gold_v3_00_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "gold_v3_00_summary.json", summary)

    report = "\n".join([
        "# GOLD V3 00 workspace and candle inventory report",
        "",
        f"Created UTC: {created}",
        f"Status: `{status}`",
        "",
        "## Output roots",
        f"- input raw: `{v3_input_raw()}`",
        f"- output root: `{v3_output_root()}`",
        "",
        "## Decision matrix",
        decision_df.to_markdown(index=False),
        "",
        "## Source selection matrix",
        source_df.to_markdown(index=False),
        "",
        "## Blockers",
        blocker_df.to_markdown(index=False),
        "",
        "## Safety",
        "- GOLD V3 only; no V2 outputs modified or deleted.",
        "- No feature engineering, no labels, no signals.",
        "- Discord/MT5/AI/live/final remain OFF.",
    ])
    (out / "GOLD_V3_00_WORKSPACE_AND_CANDLE_INVENTORY_REPORT.md").write_text(report, encoding="utf-8")

    zip_path = v3_output_root() / f"{OUT_NAME}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
