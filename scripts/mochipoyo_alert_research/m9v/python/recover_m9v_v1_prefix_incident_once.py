from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import m9v_core_v2 as core

INCIDENT_ID = "M9V_V1_PREFIX_FREEZE_SEMANTICS_INCIDENT_20260724"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def parse_args() -> argparse.Namespace:
    default_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    p = argparse.ArgumentParser(description="Archive the invalid M9V v1 prefix-freeze runtime after the known implementation incident.")
    p.add_argument("--local-root", type=Path, default=default_root)
    return p.parse_args()


def matching_success_summaries(local_root: Path, start: str) -> list[str]:
    out = local_root / "outputs" / "M9V"
    candidates: list[Path] = []
    latest = out / "LATEST" / "01_summary.json"
    if latest.is_file():
        candidates.append(latest)
    archive = out / "archive"
    if archive.is_dir():
        candidates.extend(archive.glob("*/01_summary.json"))
    matches: list[str] = []
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if (
            data.get("stage") == core.STAGE
            and data.get("status") == "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY"
            and str(data.get("prospective_start_server_time")) == start
        ):
            matches.append(str(path))
    return sorted(set(matches))


def main() -> int:
    args = parse_args()
    try:
        local_root = args.local_root
        runtime_dir = local_root / "m9v_runtime"
        runtime = runtime_dir / "m9v_runtime_manifest.json"
        receipt = runtime_dir / "m9v_runtime_start_receipt.json"
        lock = runtime_dir / "m9v_shadow_loop.lock"
        if lock.exists():
            raise RuntimeError("M9V forever loop lock exists; do not recover while M9V loop is running")
        if not runtime.is_file():
            raise RuntimeError(f"M9V runtime manifest not found: {runtime}")
        data = json.loads(runtime.read_text(encoding="utf-8"))
        if data.get("stage") != core.STAGE:
            raise RuntimeError("runtime manifest is not M9V")
        if data.get("runtime_contract_version") == core.RUNTIME_CONTRACT_VERSION:
            raise RuntimeError("runtime is already M9V v2; recovery BAT must not archive a valid v2 start")
        start = str(data.get("prospective_start_server_time", ""))
        if not start:
            raise RuntimeError("old runtime has no prospective start")
        successful = matching_success_summaries(local_root, start)
        if successful:
            raise RuntimeError(
                "cannot auto-invalidate: a successful M9V prospective output exists for the old start: "
                + "; ".join(successful)
            )

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")
        dest = runtime_dir / "invalidated" / f"{INCIDENT_ID}_{stamp}"
        dest.mkdir(parents=True, exist_ok=False)
        archived: dict[str, Any] = {}
        for source in (runtime, receipt):
            if not source.is_file():
                continue
            before_hash = sha256(source)
            target = dest / source.name
            shutil.copy2(source, target)
            after_hash = sha256(target)
            if before_hash != after_hash:
                raise RuntimeError(f"archive verification failed for {source.name}")
            archived[source.name] = {"sha256": before_hash, "archived_path": str(target)}

        incident = {
            "status": "PASS_INVALID_START_ARCHIVED_NO_PROSPECTIVE_PASS_FOUND",
            "incident_id": INCIDENT_ID,
            "reason": "M9V v1 froze all rows with server-open <= start; normal later M5 catch-up/appends could change that set and block the first one-shot.",
            "old_prospective_start_server_time": start,
            "successful_m9v_outputs_for_old_start": successful,
            "archived": archived,
            "m8c_modified": False,
            "m7c_modified": False,
            "collector_modified": False,
            "new_m9v_start_created": False,
            "next_required_action": "Run the updated 01 initializer once to create M9V runtime v2, then run 02 once.",
            "created_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        atomic_json(dest / "incident_recovery_receipt.json", incident)

        runtime.unlink()
        receipt.unlink(missing_ok=True)
        print("[M9V RECOVERY PASS] invalid v1 start archived; no successful prospective output existed")
        print(f"[ARCHIVE] {dest}")
        print("[SAFE] M8C, M7C and collector were not modified. M9V is NOT started now.")
        print("[NEXT] Run 01_initialize_fresh_runtime_once.bat once after pulling the v2 fix.")
        return 0
    except Exception as exc:
        print(f"[M9V RECOVERY BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] Nothing was deleted or replaced. M8C, M7C and collector are unchanged.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
