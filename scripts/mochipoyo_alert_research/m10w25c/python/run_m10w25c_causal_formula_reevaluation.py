from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

STAGE = "M10W25C_CAUSAL_NEITHER_EXACT_FROZEN_FORMULA_REEVALUATION_AUDIT_ONLY"
STATUS = "PASS_CAUSAL_NEITHER_EXACT_FORMULA_REEVALUATION_MMO1_STRONG_CANDIDATE_AUDIT_ONLY"
TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
HORIZON = timedelta(hours=4)

FAMILIES = {
    "MVI1_LONG_M5_VOLUME_IMPULSE": lambda r: (
        float(r["m5_tick_volume_ratio20"]) >= 1.0
        and float(r["m5_body_ratio"]) >= 0.5
        and float(r["m5_close_location"]) >= (2.0 / 3.0)
        and float(r["m1_ret5_bps"]) >= 1.0
    ),
    "MWR1_LONG_M5_PULLBACK_REJECTION": lambda r: (
        float(r["m5_lower_wick_ratio"]) >= 0.4
        and float(r["m5_close_location"]) >= 0.6
        and float(r["m5_ret3_bps"]) <= 0.0
    ),
    "MMO1_LONG_M1_MICRO_MOMENTUM": lambda r: (
        float(r["m1_ret5_bps"]) > 0.0
        and int(float(r["m1_up_close_count5"])) >= 3
        and float(r["m1_close_location"]) >= 0.6
    ),
}

EXPECTED_SHA256 = {
    "causal_features": "fcf5163814c8ddcc21e84accb520e0007236550d7792a0dd5630a424b0f2634c",
    "historical_features": "53cd0146a52faaba35cf1e8a19268e4cfb74edcdc68561d30af826fa0e0359b4",
    "historical_trades": "8e5091cbe20dc9e600e62663a112f92bbb730aab066b131f9ed2aaf7abfad20a",
    "historical_skips": "70fe38ddb97d89f0756905f898d81693b08e68d8406691a9118d34424c33adc6",
}

EXPECTED_COUNTS = {
    "historical_rows": 5917,
    "causal_rows": 5913,
    "historical_candidates": {
        "MVI1_LONG_M5_VOLUME_IMPULSE": 487,
        "MWR1_LONG_M5_PULLBACK_REJECTION": 432,
        "MMO1_LONG_M1_MICRO_MOMENTUM": 1359,
    },
}

CLASSIFICATIONS = {
    "MVI1_LONG_M5_VOLUME_IMPULSE": "INSUFFICIENT_DENSITY",
    "MWR1_LONG_M5_PULLBACK_REJECTION": "REJECT",
    "MMO1_LONG_M1_MICRO_MOMENTUM": "STRONG_CANDIDATE",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_time(text: str) -> datetime:
    return datetime.strptime(text, TIME_FORMAT)


def replay_acceptance(candidate_times: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    accepted: list[str] = []
    skipped: list[dict[str, str]] = []
    active_until: datetime | None = None
    active_id: str | None = None
    for text in sorted(candidate_times, key=parse_time):
        current = parse_time(text)
        if active_until is not None and current < active_until:
            skipped.append({
                "active_trade_id": str(active_id),
                "skipped_decision_time": text,
                "reason": "ONE_POSITION_ACTIVE",
            })
            continue
        accepted.append(text)
        active_id = f"T{len(accepted):06d}"
        active_until = current + HORIZON
    return accepted, skipped


def metrics(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "win_rate": None,
            "profit_factor": None,
            "net_bps": 0.0,
            "average_win_bps": None,
            "average_loss_bps": None,
            "payoff_ratio": None,
            "max_drawdown_bps": 0.0,
            "max_losing_streak": 0,
        }
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    average_win = None if not wins else sum(wins) / len(wins)
    average_loss = None if not losses else sum(losses) / len(losses)
    equity = 0.0
    peak = 0.0
    maximum_drawdown = 0.0
    losing_streak = 0
    maximum_losing_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum_drawdown = max(maximum_drawdown, peak - equity)
        if value <= 0:
            losing_streak += 1
            maximum_losing_streak = max(maximum_losing_streak, losing_streak)
        else:
            losing_streak = 0
    return {
        "count": len(values),
        "win_rate": len(wins) / len(values),
        "profit_factor": None if not losses else sum(wins) / abs(sum(losses)),
        "net_bps": sum(values),
        "average_win_bps": average_win,
        "average_loss_bps": average_loss,
        "payoff_ratio": None if average_win is None or average_loss is None else average_win / abs(average_loss),
        "max_drawdown_bps": maximum_drawdown,
        "max_losing_streak": maximum_losing_streak,
    }


def period_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups = {
        "TRAIN_2023_2024": [row for row in rows if int(row["year"]) in (2023, 2024)],
        "VALIDATION_2025": [row for row in rows if int(row["year"]) == 2025],
        "TEST_2026": [row for row in rows if int(row["year"]) == 2026],
        "ALL": list(rows),
    }
    output: dict[str, Any] = {}
    for label, selected in groups.items():
        actual = [float(row["actual_return_bps"]) for row in selected]
        fixed = [float(row["fixed0p20_return_bps"]) for row in selected]
        output[label] = {
            "actual": metrics(actual),
            "fixed0p20": metrics(fixed),
            "actual_plus1bps_cost": metrics([value - 1.0 for value in actual]),
            "actual_plus2bps_cost": metrics([value - 2.0 for value in actual]),
        }
    return output


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    paths = {
        "causal_features": Path(os.environ.get(
            "M10W25C_CAUSAL_FEATURES",
            local_root / "outputs" / "M10W25B" / "LATEST" / "02_causal_neither_preentry_feature_rows.csv",
        )),
        "historical_features": Path(os.environ.get(
            "M10W25C_HISTORICAL_FEATURES",
            local_root / "outputs" / "M10W24B" / "LATEST" / "02_corrected_neither_feature_rows.csv",
        )),
        "historical_trades": Path(os.environ.get(
            "M10W25C_HISTORICAL_TRADES",
            local_root / "outputs" / "M10W24B" / "LATEST" / "03_trade_ledger_all_families.csv",
        )),
        "historical_skips": Path(os.environ.get(
            "M10W25C_HISTORICAL_SKIPS",
            local_root / "outputs" / "M10W24B" / "LATEST" / "04_overlap_skip_ledger_all_families.csv",
        )),
    }
    output_root = Path(os.environ.get(
        "M10W25C_OUTPUT_ROOT",
        local_root / "outputs" / "M10W25C",
    ))

    try:
        for key, path in paths.items():
            if not path.is_file():
                raise RuntimeError(f"missing frozen input {key}: {path}")
            actual_sha = sha256_file(path)
            if actual_sha != EXPECTED_SHA256[key]:
                raise RuntimeError(f"frozen input SHA256 mismatch {key}: {actual_sha}")

        causal_rows = load_rows(paths["causal_features"])
        historical_rows = load_rows(paths["historical_features"])
        source_trades = load_rows(paths["historical_trades"])
        source_skips = load_rows(paths["historical_skips"])

        if len(historical_rows) != EXPECTED_COUNTS["historical_rows"]:
            raise RuntimeError("historical frozen cohort row count mismatch")
        if len(causal_rows) != EXPECTED_COUNTS["causal_rows"]:
            raise RuntimeError("causal frozen cohort row count mismatch")

        historical_times = [row["decision_time"] for row in historical_rows]
        causal_times = [row["decision_time"] for row in causal_rows]
        if len(historical_times) != len(set(historical_times)):
            raise RuntimeError("duplicate decision_time in historical cohort")
        if len(causal_times) != len(set(causal_times)):
            raise RuntimeError("duplicate decision_time in causal cohort")
        if not set(causal_times).issubset(set(historical_times)):
            raise RuntimeError("causal cohort is not an exact subset of historical cohort")

        source_trade_by_key = {
            (row["family"], row["decision_time"]): row for row in source_trades
        }
        source_candidate_sets: dict[str, set[str]] = {}
        for family in FAMILIES:
            source_candidate_sets[family] = {
                row["decision_time"] for row in source_trades if row["family"] == family
            } | {
                row["skipped_decision_time"] for row in source_skips if row["family"] == family
            }

        formula_audit: list[dict[str, Any]] = []
        causal_candidate_rows: list[dict[str, Any]] = []
        reevaluated_trades: list[dict[str, Any]] = []
        reevaluated_skips: list[dict[str, Any]] = []
        family_summary: dict[str, Any] = {}

        for family, rule in FAMILIES.items():
            historical_formula_times = [
                row["decision_time"] for row in historical_rows if rule(row)
            ]
            if set(historical_formula_times) != source_candidate_sets[family]:
                raise RuntimeError(f"frozen formula does not reproduce candidate set: {family}")
            if len(historical_formula_times) != EXPECTED_COUNTS["historical_candidates"][family]:
                raise RuntimeError(f"historical candidate count mismatch: {family}")

            causal_candidates = [row for row in causal_rows if rule(row)]
            candidate_times = [row["decision_time"] for row in causal_candidates]
            accepted_times, skip_rows = replay_acceptance(candidate_times)
            missing_outcomes = [
                text for text in accepted_times if (family, text) not in source_trade_by_key
            ]
            if missing_outcomes:
                raise RuntimeError(
                    "causal removal changes one-position acceptance and requires frozen raw execution replay: "
                    f"{family} {missing_outcomes[:5]}"
                )

            resolved_rows: list[dict[str, Any]] = []
            family_trade_rows: list[dict[str, Any]] = []
            for index, text in enumerate(accepted_times, start=1):
                source = dict(source_trade_by_key[(family, text)])
                source["source_trade_id"] = source.get("trade_id")
                source["trade_id"] = f"M10W25C_{family}_T{index:06d}"
                family_trade_rows.append(source)
                reevaluated_trades.append(source)
                if source.get("status") == "RESOLVED" and source.get("actual_return_bps") not in ("", None):
                    resolved_rows.append(source)

            for row in skip_rows:
                reevaluated_skips.append({"family": family, **row})
            for row in causal_candidates:
                causal_candidate_rows.append({**row, "family": family, "direction": "LONG"})

            family_summary[family] = {
                "classification": CLASSIFICATIONS[family],
                "candidate_count": len(causal_candidates),
                "accepted_count": len(accepted_times),
                "resolved_count": len(resolved_rows),
                "entry_data_gap_count": sum(
                    row.get("status") == "ENTRY_DATA_GAP" for row in family_trade_rows
                ),
                "exit_data_gap_count": sum(
                    row.get("status") == "EXIT_DATA_GAP" for row in family_trade_rows
                ),
                "overlap_skip_count": len(skip_rows),
                "metrics": period_metrics(resolved_rows),
                "advance_to_fresh_shadow": family == "MMO1_LONG_M1_MICRO_MOMENTUM",
            }
            formula_audit.append({
                "family": family,
                "historical_formula_candidate_count": len(historical_formula_times),
                "historical_source_candidate_count": len(source_candidate_sets[family]),
                "historical_exact_set_match": True,
                "causal_candidate_count": len(causal_candidates),
                "causal_accepted_count": len(accepted_times),
                "causal_overlap_skip_count": len(skip_rows),
                "newly_accepted_without_frozen_outcome": 0,
                "formula_or_threshold_changed": False,
            })

        advancing_families = [
            family for family, value in family_summary.items() if value["advance_to_fresh_shadow"]
        ]
        if advancing_families != ["MMO1_LONG_M1_MICRO_MOMENTUM"]:
            raise RuntimeError(f"unexpected advancing families: {advancing_families}")

        archive = output_root / "archive" / datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")
        archive.mkdir(parents=True, exist_ok=False)
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": STATUS,
            "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scope": "XAUUSD_GOLD_ONLY",
            "verified_input_sha256": EXPECTED_SHA256,
            "historical_NEITHER_rows": len(historical_rows),
            "causal_NEITHER_rows": len(causal_rows),
            "removed_rows": len(historical_rows) - len(causal_rows),
            "exact_frozen_formulas": {
                "MVI1_LONG_M5_VOLUME_IMPULSE": "m5_tick_volume_ratio20 >= 1.0 AND m5_body_ratio >= 0.5 AND m5_close_location >= 2/3 AND m1_ret5_bps >= 1.0",
                "MWR1_LONG_M5_PULLBACK_REJECTION": "m5_lower_wick_ratio >= 0.4 AND m5_close_location >= 0.6 AND m5_ret3_bps <= 0.0",
                "MMO1_LONG_M1_MICRO_MOMENTUM": "m1_ret5_bps > 0.0 AND m1_up_close_count5 >= 3 AND m1_close_location >= 0.6",
            },
            "horizon_hours": 4,
            "one_position_per_family": True,
            "families": family_summary,
            "advancing_families": advancing_families,
            "decision": {
                "M10W25C_pass": True,
                "MMO1_remains_strong_candidate_on_causal_cohort": True,
                "M10W26_fresh_contract_design_authorized": True,
                "M10W26_initializer_or_start_created_now": False,
                "M10W19_modified": False,
            },
            "guardrails": {
                "audit_only": True,
                "formula_change": False,
                "threshold_change": False,
                "horizon_change": False,
                "outcome_reuse_only_for_exact_frozen_accepted_rows": True,
                "newly_accepted_without_frozen_outcome": 0,
                "historical_backfill_into_forward": False,
                "existing_forward_modified": False,
                "new_prospective_start_created": False,
                "discord_send": False,
                "mt5_order": False,
                "live_ready": False,
                "final_signal": False,
                "automatic_live_promotion": False,
            },
        }

        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10W25C exact frozen M10W23 formula re-evaluation on the 5913-row prefix-causal NEITHER cohort. "
            "No formula, threshold, horizon, existing forward, monitor, or prospective start is changed.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        write_csv(archive / "02_causal_candidate_rows_all_families.csv", causal_candidate_rows)
        write_csv(archive / "03_trade_ledger_all_families.csv", reevaluated_trades)
        write_csv(archive / "04_overlap_skip_ledger_all_families.csv", reevaluated_skips)
        write_csv(archive / "05_formula_reproduction_audit.csv", formula_audit)
        (archive / "06_audit.log").write_text("\n".join([
            f"status={STATUS}",
            f"historical_neither_rows={len(historical_rows)}",
            f"causal_neither_rows={len(causal_rows)}",
            f"removed_rows={len(historical_rows) - len(causal_rows)}",
            *(f"{family}_candidate_count={family_summary[family]['candidate_count']}" for family in FAMILIES),
            *(f"{family}_resolved_count={family_summary[family]['resolved_count']}" for family in FAMILIES),
            "advancing_families=MMO1_LONG_M1_MICRO_MOMENTUM",
            "formula_change=false",
            "threshold_change=false",
            "horizon_change=false",
            "newly_accepted_without_frozen_outcome=0",
            "new_prospective_start_created=false",
            "existing_forward_modified=false",
            "discord_send=false",
            "mt5_order=false",
            "",
        ]), encoding="utf-8")

        files = [path for path in archive.iterdir() if path.is_file()]
        with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(files):
                bundle.write(path, path.name)

        latest = output_root / "LATEST"
        shutil.rmtree(latest, ignore_errors=True)
        shutil.copytree(archive, latest)
        print(f"[M10W25C PASS] causal_rows={len(causal_rows)} advancing=MMO1_LONG_M1_MICRO_MOMENTUM")
        print(f"[OUTPUT] {latest}")
        return 0
    except Exception as exc:
        print(f"[M10W25C BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No runtime, start, monitor, threshold, Discord, or MT5 order was changed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
