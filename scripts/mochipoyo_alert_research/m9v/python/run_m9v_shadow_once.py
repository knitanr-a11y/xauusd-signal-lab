from __future__ import annotations

import json
import math
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import m9v_core as core

THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parents[4]
DEFAULT_CONTRACT = REPO_ROOT / "config" / "mochipoyo_alert_research" / "m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    core.m9p.write_csv(path, rows)


def dump_json(path: Path, value: Any) -> None:
    core.m9p.dump_json(path, value)


def grouped(rows: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    resolved = [row for row in rows if row.get("return_bps") is not None]
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in resolved:
        current = core.parse_time(str(row["turn_entry_time"]))
        if mode == "year":
            label = str(current.year)
        elif mode == "quarter":
            label = f"{current.year}Q{(current.month - 1)//3 + 1}"
        else:
            label = f"{current.year}-{current.month:02d}"
        groups.setdefault(label, []).append(row)
    return [{mode: label, **core.m9p.metrics(group)} for label, group in sorted(groups.items())]


def resolve_environment() -> tuple[Path, float, Path, Path]:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    if not metadata_path.is_file():
        raise core.M9VContractError(f"M8B symbol metadata missing: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    mt5_root = Path(str(metadata.get("mt5_files_root", "")))
    point = float(metadata.get("symbols", {}).get("XAUUSD", {}).get("point", "nan"))
    if not mt5_root.is_dir() or not math.isfinite(point):
        raise core.M9VContractError(f"MT5 Files root or XAUUSD point unavailable: {mt5_root} point={point}")
    runtime = local_root / "m9v_runtime" / "m9v_runtime_manifest.json"
    output_root = local_root / "outputs" / "M9V"
    return mt5_root, point, runtime, output_root


def main() -> int:
    try:
        contract_path = Path(os.environ.get("M9V_CONTRACT", str(DEFAULT_CONTRACT)))
        if not contract_path.is_file():
            raise core.M9VContractError(f"M9V contract missing: {contract_path}")
        contract = core.load_json(contract_path)
        core.validate_contract(contract)

        data_override = os.environ.get("M9V_GOLD_DATA_ROOT")
        point_override = os.environ.get("M9V_POINT")
        runtime_override = os.environ.get("M9V_RUNTIME_MANIFEST")
        output_override = os.environ.get("M9V_OUTPUT_ROOT")

        if data_override and point_override and runtime_override:
            data_root = Path(data_override)
            point = float(point_override)
            runtime_path = Path(runtime_override)
            output_root = Path(output_override or "/tmp/m9v_output")
        else:
            data_root, point, runtime_path, output_root = resolve_environment()
            if data_override:
                data_root = Path(data_override)
            if point_override is not None:
                point = float(point_override)
            if runtime_override:
                runtime_path = Path(runtime_override)
            if output_override:
                output_root = Path(output_override)

        if not runtime_path.is_file():
            raise core.M9VContractError(f"M9V runtime manifest missing; initialize once first: {runtime_path}")
        runtime = core.load_json(runtime_path)
        result = core.audit(data_root=data_root, contract=contract, runtime=runtime, point=point)

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        arm_counts = {name: len(rows) for name, rows in result["arms"].items()}
        review = contract["review_gates"]
        max_accepted = max(arm_counts.values()) if arm_counts else 0
        h1_candidates = len([row for row in result["candidates"] if row["branch"] == "S3_H1"])
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": core.STAGE,
            "status": "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
            "built_at_utc": now,
            "prospective_start_server_time": result["start_server_time"],
            "latest_server_open": result["latest_server_open"],
            "branch_metrics": result["branch_metrics"],
            "arm_metrics": result["arm_metrics"],
            "arm_accepted_counts": arm_counts,
            "candidate_count": len(result["candidates"]),
            "confirmation_metadata_count": len(result["confirmations"]),
            "review_readiness": {
                "operational_checkpoint": max_accepted >= int(review["operational_checkpoint_total_accepted_arm_events"]),
                "interim_checkpoint": max_accepted >= int(review["interim_checkpoint_total_accepted_arm_events"]),
                "minimum_H1_S3_candidates": h1_candidates >= int(review["minimum_H1_S3_candidates_for_branch_review"]),
                "formal_portfolio_checkpoint": max_accepted >= int(review["formal_portfolio_review_total_accepted_arm_events"]),
                "automatic_live_promotion": False,
            },
            "guardrails": {
                "audit_only": True,
                "historical_backfill": False,
                "pre_start_primary_candidate_eligibility": False,
                "pyramiding": False,
                "generic_agreement_score": False,
                "m9r_overlay_included": False,
                "discord_send": False,
                "mt5_order": False,
                "live_ready": False,
                "final_signal": False,
                "m8c_reset": False,
            },
        }

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M9V is a fresh GOLD multi-timeframe audit-only prospective shadow. V0=M15 N3 only, V1=M15+H1, V2=M5+M15+H1+H4. "
            "Each arm allows one GOLD LONG position only; later branch candidates while active are ordered confirmation metadata, not pyramiding. "
            "M9R half-risk/runner overlays are intentionally excluded. No historical backfill is allowed.\n",
            encoding="utf-8",
        )
        dump_json(archive / "01_summary.json", summary)
        write_csv(archive / "02_branch_candidate_ledger.csv", result["candidates"])
        write_csv(archive / "03_rejected_first_turns.csv", result["rejected_turns"])
        for index, name in enumerate(("V0_M15_ONLY", "V1_M15_PLUS_H1", "V2_ALL_TIMEFRAMES"), start=4):
            write_csv(archive / f"{index:02d}_{name}_ledger.csv", result["arms"][name])
        write_csv(archive / "07_ordered_confirmation_metadata.csv", result["confirmations"])
        dump_json(archive / "08_bootstrap_state_audit.json", result["bootstrap_audit"])
        dump_json(archive / "09_runtime_manifest_copy.json", runtime)
        dump_json(archive / "10_data_quality.json", {
            "data_root": str(data_root),
            "point": point,
            "closed_rows_contract": True,
            "nearest_m1_fallback": False,
            "prefix_integrity_verified": True,
            "latest_server_open": result["latest_server_open"],
        })
        period_rows: list[dict[str, Any]] = []
        for name, rows in result["arms"].items():
            for mode in ("month", "quarter", "year"):
                for row in grouped(rows, mode):
                    period_rows.append({"arm": name, "period_mode": mode, **row})
        write_csv(archive / "11_arm_period_metrics.csv", period_rows)
        (archive / "12_audit.log").write_text("\n".join([
            "status=PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
            f"prospective_start_server_time={result['start_server_time']}",
            f"candidates={len(result['candidates'])}",
            *(f"{name}={len(result['arms'][name])}" for name in ("V0_M15_ONLY", "V1_M15_PLUS_H1", "V2_ALL_TIMEFRAMES")),
            f"confirmations={len(result['confirmations'])}",
            "historical_backfill=false",
            "pre_start_primary_candidate_eligibility=false",
            "pyramiding=false",
            "generic_agreement_score=false",
            "m9r_overlay_included=false",
            "discord_send=false",
            "mt5_order=false",
            "m8c_reset=false",
            "",
        ]), encoding="utf-8")

        names = [path.name for path in archive.iterdir() if path.is_file()]
        with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            for name in sorted(names):
                zf.write(archive / name, name)

        latest = output_root / "LATEST"
        shutil.rmtree(latest, ignore_errors=True)
        shutil.copytree(archive, latest)
        print(f"[M9V PASS] CANDIDATES={len(result['candidates'])} V0={len(result['arms']['V0_M15_ONLY'])} V1={len(result['arms']['V1_M15_PLUS_H1'])} V2={len(result['arms']['V2_ALL_TIMEFRAMES'])}")
        print("[M9V OUTPUT]", latest)
        return 0
    except Exception as exc:
        print(f"[M9V BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] M8C, M7C and collector are not modified by M9V.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
