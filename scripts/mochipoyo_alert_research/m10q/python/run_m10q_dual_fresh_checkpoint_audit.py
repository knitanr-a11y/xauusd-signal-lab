from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STAGE = "M10Q_DUAL_SHORT_FRESH_CHECKPOINT_AUDIT"
SPECS = {
    "M10P": {
        "stage": "M10P_C056_G013_FRESH_PROSPECTIVE_SHADOW",
        "start": "2026.07.24 23:56:00",
        "summary": Path("outputs/M10P/LATEST/01_summary.json"),
        "runtime": Path("m10p_runtime/m10p_runtime_manifest.json"),
        "gates": [5, 10, 20, 40, 60],
    },
    "M10P2": {
        "stage": "M10P2_C0212_FRESH_PROSPECTIVE_SHADOW",
        "start": "2026.07.27 01:39:00",
        "summary": Path("outputs/M10P2/LATEST/01_summary.json"),
        "runtime": Path("m10p2_runtime/m10p2_runtime_manifest.json"),
        "gates": [5, 10, 20],
    },
}


class AuditError(RuntimeError):
    pass


def local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip()
    if not base:
        raise AuditError("LOCALAPPDATA unavailable")
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AuditError(f"missing required file: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AuditError(f"JSON object required: {path}")
    return payload


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_one(root: Path, name: str, spec: dict[str, Any]) -> dict[str, Any]:
    summary_path = root / Path(spec["summary"])
    runtime_path = root / Path(spec["runtime"])
    summary = load_json(summary_path)
    runtime = load_json(runtime_path)

    if summary.get("stage") != spec["stage"]:
        raise AuditError(f"{name} summary stage mismatch")
    if summary.get("status") != "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY":
        raise AuditError(f"{name} summary status mismatch")
    if summary.get("prospective_start_server_time") != spec["start"]:
        raise AuditError(f"{name} summary start changed")
    if runtime.get("stage") != spec["stage"]:
        raise AuditError(f"{name} runtime stage mismatch")
    if runtime.get("prospective_start_server_time") != spec["start"]:
        raise AuditError(f"{name} runtime start changed")
    if runtime.get("reset_allowed") is not False:
        raise AuditError(f"{name} reset_allowed must remain false")
    if runtime.get("historical_backfill_allowed") is not False:
        raise AuditError(f"{name} historical_backfill_allowed must remain false")

    guard = summary.get("guardrails", {})
    for key in ("historical_backfill", "pre_start_candidate_eligibility", "threshold_refit_from_prospective_outcomes", "discord_send", "mt5_order", "live_ready", "final_signal", "automatic_live_promotion"):
        if guard.get(key) is not False:
            raise AuditError(f"{name} unsafe or missing guardrail: {key}")
    if guard.get("audit_only") is not True:
        raise AuditError(f"{name} audit_only must remain true")

    metrics = summary.get("metrics", {})
    resolved = int(metrics.get("resolved_count", 0))
    gates = [int(x) for x in spec["gates"]]
    reached = [g for g in gates if resolved >= g]
    next_gate = next((g for g in gates if resolved < g), None)
    return {
        "name": name,
        "stage": spec["stage"],
        "prospective_start_server_time": spec["start"],
        "summary_sha256": sha256(summary_path),
        "runtime_sha256": sha256(runtime_path),
        "candidate_match_count": int(metrics.get("candidate_match_count", 0)),
        "accepted_count": int(metrics.get("accepted_count", 0)),
        "resolved_count": resolved,
        "open_count": int(metrics.get("open_count", 0)),
        "entry_data_gap_count": int(metrics.get("entry_data_gap_count", 0)),
        "exit_data_gap_count": int(metrics.get("exit_data_gap_count", 0)),
        "overlap_skip_count": int(summary.get("overlap_skip_count", 0)),
        "actual": metrics.get("actual", {}),
        "fixed0p20": metrics.get("fixed0p20", {}),
        "reached_review_gates": reached,
        "next_review_gate": next_gate,
        "all_review_gates_reached": next_gate is None,
        "latest_server_open": summary.get("latest_server_open", {}),
    }


def main() -> int:
    try:
        root = local_root()
        rows = [inspect_one(root, name, spec) for name, spec in SPECS.items()]
        out_root = root / "outputs" / "M10Q"
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = out_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)

        payload = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_READ_ONLY_DUAL_FRESH_CHECKPOINT_AUDIT",
            "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "monitors": rows,
            "interpretation": {
                "M10P": {"5": "operational", "10": "interim", "20": "formal", "40": "stability", "60": "adoption_review"},
                "M10P2": {"5": "operational", "10": "interim", "20": "formal"},
                "pf2_claim_before_20_resolved": False,
                "automatic_live_promotion": False,
            },
            "guardrails": {
                "read_only": True,
                "audit_only": True,
                "runtime_modified": False,
                "prospective_start_modified": False,
                "threshold_modified": False,
                "historical_backfill": False,
                "discord_send": False,
                "mt5_order": False,
                "live_ready": False,
                "final_signal": False,
            },
        }
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10Q read-only joint checkpoint audit for M10P and M10P2. No runtime/start/threshold modification.\n",
            encoding="utf-8",
        )
        (archive / "01_dual_checkpoint_summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "02_audit.log").write_text(
            "\n".join([
                "status=PASS_READ_ONLY_DUAL_FRESH_CHECKPOINT_AUDIT",
                *[f"{row['name']}_resolved={row['resolved_count']} next_gate={row['next_review_gate']}" for row in rows],
                "runtime_modified=false",
                "prospective_start_modified=false",
                "threshold_modified=false",
                "historical_backfill=false",
                "",
            ]),
            encoding="utf-8",
        )
        latest = out_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in ("00_READ_ME_FIRST.txt", "01_dual_checkpoint_summary.json", "02_audit.log"):
                zf.write(latest / name, arcname=name)

        print("[M10Q PASS] dual fresh checkpoint audit completed")
        for row in rows:
            print(f"[{row['name']}] resolved={row['resolved_count']} next_gate={row['next_review_gate']}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10Q BLOCKED] {type(exc).__name__}: {exc}")
        print("[SAFE] No M10P/M10P2 runtime, start, threshold, or ledger was modified.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
