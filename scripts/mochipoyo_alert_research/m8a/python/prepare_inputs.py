from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = [
    "latest_m7c_prospective_shadow.json",
    "latest_m7c_shadow_loop_status.json",
    "latest_m7c_source_event_comparisons.csv",
    "latest_m7c_extra_proxy_signals.csv",
    "latest_m7c_proxy_signals.csv",
    "latest_m7c_proxy_decisions.csv",
    "m7c_shadow_forever.log",
]
EXPECTED_START = "2026-07-20T14:54:15Z"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser(description="Freeze M7C formal-gate inputs for M8A")
    p.add_argument("--source-dir", required=True)
    p.add_argument("--freeze-root", required=True)
    args = p.parse_args()

    source = Path(args.source_dir).expanduser().resolve()
    freeze_root = Path(args.freeze_root).expanduser().resolve()
    missing = [name for name in REQUIRED if not (source / name).is_file()]
    if missing:
        print(f"[M8A PREP BLOCKED] missing={missing}")
        return 2

    with (source / "latest_m7c_prospective_shadow.json").open("r", encoding="utf-8") as f:
        report = json.load(f)
    errors = []
    if report.get("prospective_start_utc") != EXPECTED_START:
        errors.append("prospective_start_utc mismatch")
    if report.get("readiness", {}).get("formal_review_state") != "READY_FOR_MANUAL_REPRODUCTION_REVIEW":
        errors.append("formal gate not ready")
    if any(v is not True for v in report.get("readiness", {}).get("formal_review_requirements", {}).values()):
        errors.append("not all formal gate requirements are true")
    if errors:
        print(f"[M8A PREP BLOCKED] {errors}")
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dst = freeze_root / stamp
    dst.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for name in REQUIRED:
        shutil.copy2(source / name, dst / name)
        hashes[name] = sha256(dst / name)
    manifest = {
        "stage": "M7C_FORMAL_GATE_FREEZE_FOR_M8A",
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prospective_start_utc": report.get("prospective_start_utc"),
        "supported_source_event_count": report.get("comparison_summary", {}).get("supported_source_event_count"),
        "readiness": report.get("readiness", {}),
        "sha256": hashes,
        "note": "Frozen copies only. M7C runtime manifest/formulas/thresholds are not modified.",
    }
    with (dst / "FREEZE_MANIFEST.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    latest = freeze_root / "LATEST"
    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(dst, latest)
    print(f"[M8A PREP PASS] {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
