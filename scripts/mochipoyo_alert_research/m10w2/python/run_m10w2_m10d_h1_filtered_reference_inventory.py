from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STAGE = "M10W2_M10D_H1_FILTERED_REFERENCE_INVENTORY_AUDIT_ONLY"
TEXT_SUFFIXES = {".json", ".csv", ".txt", ".log", ".md"}
MAX_SINGLE_COPY_BYTES = 100 * 1024 * 1024
MAX_TOTAL_COPY_BYTES = 300 * 1024 * 1024


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_source(base: Path) -> Path:
    root = base / "outputs" / "M10D"
    if not root.is_dir():
        raise RuntimeError(f"M10D output root missing: {root}")
    latest = root / "LATEST"
    if latest.is_dir():
        return latest
    archive = root / "archive"
    if archive.is_dir():
        dirs = [p for p in archive.iterdir() if p.is_dir()]
        if dirs:
            return max(dirs, key=lambda p: p.stat().st_mtime_ns)
    dirs = [p for p in root.iterdir() if p.is_dir() and p.name.lower() != "archive"]
    if dirs:
        return max(dirs, key=lambda p: p.stat().st_mtime_ns)
    raise RuntimeError(f"No usable M10D result directory found under: {root}")


def primitive_paths(obj: Any, prefix: str = "", out: dict[str, Any] | None = None) -> dict[str, Any]:
    if out is None:
        out = {}
    if len(out) >= 600:
        return out
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            low = str(key).lower()
            if isinstance(value, (str, int, float, bool)) or value is None:
                if any(token in low for token in ("stage", "status", "arm", "metric", "candidate", "ticker", "symbol", "direction", "filter", "exclude", "threshold", "pf", "drawdown", "win", "payoff", "count", "bps")):
                    out[path] = value
            else:
                primitive_paths(value, path, out)
            if len(out) >= 600:
                break
    elif isinstance(obj, list):
        for index, value in enumerate(obj[:100]):
            primitive_paths(value, f"{prefix}[{index}]", out)
            if len(out) >= 600:
                break
    return out


def inspect_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    result: dict[str, Any] = {"type": type(payload).__name__}
    if isinstance(payload, dict):
        result["top_level_keys"] = list(payload.keys())
        for key in ("project", "stage", "status", "ticker", "symbol"):
            if key in payload:
                result[key] = payload[key]
    result["selected_primitive_paths"] = primitive_paths(payload)
    return result


def inspect_csv(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames or [])
        distinct_cols = [c for c in columns if any(k in c.lower() for k in ("arm", "status", "direction", "filter", "exclude", "branch", "family"))]
        time_cols = [c for c in columns if any(k in c.lower() for k in ("time", "date", "dt"))]
        distinct: dict[str, set[str]] = {c: set() for c in distinct_cols}
        time_min: dict[str, str] = {}
        time_max: dict[str, str] = {}
        row_count = 0
        for row in reader:
            row_count += 1
            for c in time_cols:
                value = (row.get(c) or "").strip()
                if value:
                    if c not in time_min or value < time_min[c]:
                        time_min[c] = value
                    if c not in time_max or value > time_max[c]:
                        time_max[c] = value
            for c in distinct_cols:
                value = (row.get(c) or "").strip()
                if value and len(distinct[c]) < 100:
                    distinct[c].add(value)
    return {"row_count": row_count, "columns": columns, "time_min": time_min, "time_max": time_max, "distinct": {k: sorted(v) for k, v in distinct.items()}}


def write_inventory(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = ["relative_path", "suffix", "size_bytes", "sha256", "copied_to_package", "copy_reason"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if not local:
        raise RuntimeError("LOCALAPPDATA unavailable")
    base = Path(local) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    source = resolve_source(base)
    output_root = base / "outputs" / "M10W2"
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    archive = output_root / "archive" / stamp
    latest = output_root / "LATEST"
    archive.mkdir(parents=True, exist_ok=False)

    rows: list[dict[str, Any]] = []
    json_inventory: dict[str, Any] = {}
    csv_inventory: dict[str, Any] = {}
    copied_bytes = 0
    source_copy = archive / "08_source_copy"
    files = sorted(p for p in source.rglob("*") if p.is_file())
    if not files:
        raise RuntimeError(f"M10D source contains no files: {source}")

    for path in files:
        rel = path.relative_to(source)
        suffix = path.suffix.lower()
        size = path.stat().st_size
        digest = sha256_file(path)
        copied = False
        reason = "non_text_artifact_manifest_only"
        if suffix == ".json":
            try:
                json_inventory[str(rel)] = inspect_json(path)
            except Exception as exc:
                json_inventory[str(rel)] = {"parse_error": f"{type(exc).__name__}: {exc}"}
        if suffix == ".csv":
            try:
                csv_inventory[str(rel)] = inspect_csv(path)
            except Exception as exc:
                csv_inventory[str(rel)] = {"parse_error": f"{type(exc).__name__}: {exc}"}
        if suffix in TEXT_SUFFIXES:
            if size > MAX_SINGLE_COPY_BYTES:
                reason = "single_file_copy_limit"
            elif copied_bytes + size > MAX_TOTAL_COPY_BYTES:
                reason = "total_copy_limit"
            else:
                dest = source_copy / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
                copied = True
                copied_bytes += size
                reason = "copied_read_only"
        rows.append({"relative_path": str(rel), "suffix": suffix, "size_bytes": size, "sha256": digest, "copied_to_package": copied, "copy_reason": reason})

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": STAGE,
        "status": "PASS_USER_LOCAL_M10D_H1_FILTERED_REFERENCE_INVENTORY_AUDIT_ONLY",
        "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "XAUUSD_GOLD_ONLY",
        "source_directory": str(source),
        "source_file_count": len(rows),
        "source_total_bytes": sum(int(r["size_bytes"]) for r in rows),
        "copied_text_bytes": copied_bytes,
        "selection_decision_made": False,
        "reads_M10E_fresh_outcomes_for_selection": False,
        "reads_M10P_or_M10P2": False,
        "running_monitors_modified": False,
        "historical_backfill": False,
        "threshold_refit": False,
        "btc_in_scope": False,
        "next": "Upload M10W2 99_UPLOAD_PACKAGE.zip for evidence review before choosing baseline versus filtered H1 LONG representation."
    }
    (archive / "00_READ_ME_FIRST.txt").write_text("M10W2 read-only inventory of M10D GOLD H1 compound-filter historical evidence. No forward runtime is modified.\n", encoding="utf-8")
    (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_inventory(archive / "02_file_inventory.csv", rows)
    (archive / "03_json_inventory.json").write_text(json.dumps(json_inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (archive / "04_csv_inventory.json").write_text(json.dumps(csv_inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (archive / "05_audit.log").write_text("\n".join([
        "status=PASS_USER_LOCAL_M10D_H1_FILTERED_REFERENCE_INVENTORY_AUDIT_ONLY",
        "scope=XAUUSD_GOLD_ONLY",
        f"source_directory={source}",
        f"source_file_count={len(rows)}",
        "selection_decision_made=false",
        "reads_M10E_fresh_outcomes_for_selection=false",
        "reads_M10P_or_M10P2=false",
        "running_monitors_modified=false",
        "historical_backfill=false",
        "threshold_refit=false",
        "btc_in_scope=false",
        "discord_send=false",
        "mt5_order=false",
        "live_ready=false",
        "final_signal=false",
        "",
    ]), encoding="utf-8")

    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(archive, latest)
    package = latest / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(latest.rglob("*")):
            if path.is_file() and path != package:
                zf.write(path, path.relative_to(latest))
    print("[M10W2 PASS] M10D H1 filtered reference inventory completed")
    print(f"[SOURCE] {source}")
    print(f"[FILES] {len(rows)}")
    print(f"[PACKAGE] {package}")
    print("[SAFE] No running monitor/runtime/start/threshold was modified.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[M10W2 BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] Do not modify/delete M10D or forward runtime files to force a pass.", file=sys.stderr)
        raise SystemExit(2)
