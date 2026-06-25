from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

from cost_stress_contract import (
    BRIDGE,
    RAW,
    backup_output,
    load_json,
    load_registries,
    scenarios_from,
    sha256_file,
    validate_config,
    verify_bridge,
    verify_raw,
)
from cost_stress_engine import M1Engine, build_risk_lookup, replay_raw
from cost_stress_reports import (
    bridge_candidate_summary,
    bridge_trade_audit,
    bridge_year_summary,
    candidate_summary,
    json_clean,
    lineage_summary,
    overall_gate,
    records,
    write_csvs,
    write_text_summary,
    year_summary,
)


def run(args: argparse.Namespace) -> int:
    output = args.output_dir.resolve()
    backup = backup_output(output)
    config_path = args.config.resolve()
    config = load_json(config_path)
    candidates, lineage_by_candidate = validate_config(config)
    scenarios = scenarios_from(config)
    raw_dir = args.raw_dir.resolve()
    bridge_dir = args.bridge_dir.resolve()
    if not bridge_dir.exists():
        raise FileNotFoundError(bridge_dir)

    raw_audit = verify_raw(raw_dir, config)
    bridge_audit = verify_bridge(bridge_dir, config, candidates)
    registry, registry_audit = load_registries(
        bridge_dir, config, candidates, lineage_by_candidate
    )
    raw_registry = registry[registry["trade_core_source"] == RAW].copy()
    bridge_registry = registry[registry["trade_core_source"] == BRIDGE].copy()
    if raw_registry.empty or bridge_registry.empty:
        raise RuntimeError("RAW and bridge populations must both be present")

    engine = M1Engine(pd.read_csv(raw_dir / "gold_v3_2023_2026_m1.csv"))
    risk_lookup = build_risk_lookup(raw_dir, lineage_by_candidate)
    raw_trades, checks = replay_raw(
        raw_registry,
        engine,
        config,
        lineage_by_candidate,
        scenarios,
        risk_lookup,
    )
    expected_raw_rows = len(raw_registry) * len(scenarios)
    if len(raw_trades) != expected_raw_rows:
        raise RuntimeError(
            f"RAW trade/scenario rows {len(raw_trades)} != {expected_raw_rows}"
        )

    bridge_trades = bridge_trade_audit(bridge_registry)
    raw_candidate = candidate_summary(raw_trades, config)
    bridge_candidate = bridge_candidate_summary(bridge_trades)
    candidate = pd.concat([raw_candidate, bridge_candidate], ignore_index=True, sort=False)

    raw_year = year_summary(raw_trades, config)
    bridge_year = bridge_year_summary(bridge_trades)
    year = pd.concat([raw_year, bridge_year], ignore_index=True, sort=False)
    lineage = lineage_summary(candidate)
    gate = overall_gate(raw_candidate, len(scenarios))
    if set(gate.candidate_id.astype(str)) != set(candidates):
        raise RuntimeError("Overall gate candidate set mismatch")

    trade_audit = pd.concat([raw_trades, bridge_trades], ignore_index=True, sort=False)
    write_csvs(output, trade_audit, candidate, year, lineage, gate)

    config_hash = sha256_file(config_path)
    provenance = {
        "run_status": "PASS",
        "run_time_local": datetime.now().isoformat(timespec="seconds"),
        "config": str(config_path),
        "config_sha256": config_hash,
        "raw_dir": str(raw_dir),
        "bridge_dir": str(bridge_dir),
        "output_dir": str(output),
        "previous_output_backup": str(backup) if backup else None,
        "raw_audit": raw_audit,
        "bridge_audit": bridge_audit,
        "registry_audit": registry_audit,
        "raw_baseline_parity_checks": checks,
        "raw_registry_rows": int(len(raw_registry)),
        "bridge_exact_core_rows": int(len(bridge_registry)),
        "raw_scenario_count": len(scenarios),
        "raw_trade_scenario_rows": len(raw_trades),
        "bridge_stress_replay_status": "NOT_CALCULATED_AUDIT_ONLY",
        "audit_only": True,
    }
    (output / "input_provenance.json").write_text(
        json.dumps(json_clean(provenance), ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )

    passes = int((gate.candidate_overall_stress_gate == "PASS").sum())
    fails = int((gate.candidate_overall_stress_gate == "FAIL").sum())
    summary = {
        "status": "PASS",
        "exit_code": 0,
        "phase": config["phase"],
        "audit_only": True,
        "primary_population": RAW,
        "bridge_population": BRIDGE,
        "raw_scenario_grid": [item.__dict__ for item in scenarios],
        "raw_baseline_parity_checks": checks,
        "bridge_stress_replay_status": "NOT_CALCULATED_AUDIT_ONLY",
        "bridge_reporting_contract": "EXACT_CORE_BASELINE_METRICS_SEPARATE",
        "candidate_overall_gate": records(gate),
        "candidate_overall_gate_counts": {"PASS": passes, "FAIL": fails},
        "raw_candidate_scenario_results": records(raw_candidate),
        "bridge_candidate_exact_core_results": records(bridge_candidate),
        "raw_lineage_results": records(lineage[lineage.population == RAW]),
        "bridge_lineage_results": records(lineage[lineage.population == BRIDGE]),
        "caveats": config["caveats"],
        "blockers": [
            "WARMUP_BRIDGE_EXACT exact spread/slippage replay is blocked by absent pre-2023 indicator state and incomplete price fields; no synthetic result is fabricated.",
            "Fresh prospective confirmation after the frozen cutoff is incomplete.",
            "Registration, promotion and all execution switches remain unauthorized and OFF.",
        ],
        "automatic_next_action": None,
        "execution_switches": config["execution_switches"],
    }
    (output / "cost_stress_summary.json").write_text(
        json.dumps(json_clean(summary), ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    write_text_summary(
        output,
        config_path,
        config_hash,
        backup,
        scenarios,
        checks,
        registry,
        candidate,
        gate,
    )
    (output / "COST_STRESS_RUN_ERROR.txt").write_text(
        "status=PASS\nerror=NONE\n", encoding="utf-8"
    )

    missing = sorted(
        set(config["required_outputs"])
        - {path.name for path in output.iterdir() if path.is_file()}
    )
    if missing:
        raise RuntimeError(f"Required outputs missing: {missing}")

    print("=" * 72)
    print("GOLD_ML_V1 COST STRESS - RUN STATUS: PASS")
    print(f"RAW baseline parity checks: {checks}")
    print(f"RAW candidate stress gate: PASS={passes} FAIL={fails}")
    print("WARMUP_BRIDGE_EXACT: separate exact-core audit only")
    print("No automatic next phase was performed.")
    print("=" * 72)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit-only cost stress for the frozen GOLD_ML_V1 candidates"
    )
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--bridge-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/gold_ml_v1/cost_stress_raw_reconstructed"),
    )
    args = parser.parse_args()
    try:
        return run(args)
    except Exception as exc:
        output = args.output_dir.resolve()
        output.mkdir(parents=True, exist_ok=True)
        (output / "COST_STRESS_RUN_ERROR.txt").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
        lines = [
            "GOLD_ML_V1 COST STRESS",
            "run_status=FAIL",
            "exit_code=4",
            f"run_time_local={datetime.now().isoformat(timespec='seconds')}",
            f"error_type={type(exc).__name__}",
            f"error={exc}",
            "automatic_next_action=NONE",
            "live_ready=false",
        ]
        (output / "LATEST_RUN_SUMMARY.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        print(f"[FAIL] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
