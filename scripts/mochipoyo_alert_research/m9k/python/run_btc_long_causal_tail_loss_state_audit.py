from __future__ import annotations

import csv
import json
import math
import os
import shutil
import statistics
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
EXPECTED_M9C_RESOLVED = 952
EXPECTED_M9D_CHECKPOINTS = 3039
EXPECTED_SOURCE_LIKE_BTC_LONG = 113
CHECKPOINT_RATIOS = (0.25, 0.50, 0.75, 1.00, 1.50, 2.00)
TAIL_LABELS = {
    "LOSS_LE_MINUS_50_BPS": -50.0,
    "LOSS_LE_MINUS_100_BPS": -100.0,
    "LOSS_LE_MINUS_200_BPS": -200.0,
}

THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parents[4]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def pf(values: list[float]) -> float | None:
    wins = sum(v for v in values if v > 0)
    losses = abs(sum(v for v in values if v < 0))
    return None if losses == 0 else wins / losses


def metrics(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "win_rate": None, "profit_factor_bps": None, "net_bps": 0.0, "mean_bps": None, "median_bps": None}
    return {
        "count": len(values),
        "win_rate": sum(v > 0 for v in values) / len(values),
        "profit_factor_bps": pf(values),
        "net_bps": sum(values),
        "mean_bps": statistics.fmean(values),
        "median_bps": statistics.median(values),
    }


def safe_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def feature_key_allowed(key: str) -> bool:
    if key in {"elapsed_minutes_from_signal", "realized_adverse_depth_bps", "realized_adverse_depth_atr", "recovery_from_extreme_bps_at_checkpoint", "checkpoint_spread_points"}:
        return True
    if not key.startswith("checkpoint_"):
        return False
    blocked_fragments = (
        "return_", "mfe_", "mae_", "positive_at_", "recovered_original_", "exec_price", "threshold_price",
        "selected_bar_open", "selected_bar_close", "decision_time", "feature_unavailable_reason", "features_available",
    )
    return not any(fragment in key for fragment in blocked_fragments)


def numeric_contrasts(rows: list[dict[str, Any]], label_key: str, *, ratio: float) -> list[dict[str, Any]]:
    subset = [row for row in rows if abs(float(row["checkpoint_atr_ratio"]) - ratio) < 1e-12]
    positive = [row for row in subset if safe_bool(row.get(label_key))]
    negative = [row for row in subset if not safe_bool(row.get(label_key))]
    keys = sorted(set().union(*(row.keys() for row in subset))) if subset else []
    output: list[dict[str, Any]] = []
    for key in keys:
        if not feature_key_allowed(key):
            continue
        avals = [as_float(row.get(key)) for row in positive]
        bvals = [as_float(row.get(key)) for row in negative]
        avals = [v for v in avals if v is not None]
        bvals = [v for v in bvals if v is not None]
        if len(avals) < 8 or len(bvals) < 8:
            continue
        am, bm = statistics.fmean(avals), statistics.fmean(bvals)
        ast = statistics.stdev(avals) if len(avals) > 1 else 0.0
        bst = statistics.stdev(bvals) if len(bvals) > 1 else 0.0
        pooled = math.sqrt((ast * ast + bst * bst) / 2.0)
        smd = None if pooled <= 1e-12 else (am - bm) / pooled
        output.append({
            "checkpoint_atr_ratio": ratio,
            "label": label_key,
            "feature": key,
            "tail_n": len(avals),
            "non_tail_n": len(bvals),
            "tail_mean": am,
            "non_tail_mean": bm,
            "tail_median": statistics.median(avals),
            "non_tail_median": statistics.median(bvals),
            "standardized_mean_difference_tail_minus_non_tail": smd,
            "abs_smd": None if smd is None else abs(smd),
        })
    return sorted(output, key=lambda row: -1 if row["abs_smd"] is None else -float(row["abs_smd"]))


def categorical_contrasts(rows: list[dict[str, Any]], label_key: str, *, ratio: float) -> list[dict[str, Any]]:
    subset = [row for row in rows if abs(float(row["checkpoint_atr_ratio"]) - ratio) < 1e-12]
    positive = [row for row in subset if safe_bool(row.get(label_key))]
    negative = [row for row in subset if not safe_bool(row.get(label_key))]
    keys = [
        key for key in sorted(set().union(*(row.keys() for row in subset)))
        if key.startswith("checkpoint_") and (key.endswith("ema_alignment") or key.endswith("rci9_turn_up") or key.endswith("rci9_turn_down"))
    ] if subset else []
    output: list[dict[str, Any]] = []
    for key in keys:
        pc = Counter(str(row.get(key)) for row in positive if row.get(key) not in (None, ""))
        nc = Counter(str(row.get(key)) for row in negative if row.get(key) not in (None, ""))
        for value in sorted(set(pc) | set(nc)):
            output.append({
                "checkpoint_atr_ratio": ratio,
                "label": label_key,
                "feature": key,
                "value": value,
                "tail_count": pc[value],
                "tail_fraction": pc[value] / sum(pc.values()) if pc else None,
                "non_tail_count": nc[value],
                "non_tail_fraction": nc[value] / sum(nc.values()) if nc else None,
            })
    return output


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    m9c = local_root / "outputs" / "M9C" / "LATEST"
    m9d = local_root / "outputs" / "M9D" / "LATEST"
    m9j = local_root / "outputs" / "M9J" / "LATEST"
    required = [
        m9c / "01_summary.json", m9c / "04_m1_resolved_trade_outcomes.csv",
        m9d / "01_summary.json", m9d / "02_adverse_checkpoint_feature_panel.csv",
        m9j / "01_summary.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print(f"[M9K BLOCKED] required upstream file missing: {missing}")
        return 2

    m9c_summary = json.loads((m9c / "01_summary.json").read_text(encoding="utf-8"))
    m9d_summary = json.loads((m9d / "01_summary.json").read_text(encoding="utf-8"))
    m9j_summary = json.loads((m9j / "01_summary.json").read_text(encoding="utf-8"))
    if (
        m9c_summary.get("status") != "PASS_EXPLORATORY_ONLY"
        or int(m9c_summary.get("m1_resolved_trade_count", -1)) != EXPECTED_M9C_RESOLVED
        or m9d_summary.get("status") != "PASS_EXPLORATORY_ONLY"
        or int(m9d_summary.get("checkpoint_rows", -1)) != EXPECTED_M9D_CHECKPOINTS
        or m9j_summary.get("status") != "PASS_EXPLORATORY_HOLDOUT_ONLY"
    ):
        print("[M9K BLOCKED] upstream M9C/M9D/M9J reviewed population mismatch")
        return 2

    outcomes = read_csv(m9c / "04_m1_resolved_trade_outcomes.csv")
    checkpoints = read_csv(m9d / "02_adverse_checkpoint_feature_panel.csv")
    source_like = [
        row for row in outcomes
        if row.get("ticker") == "BTCUSD" and row.get("direction") == "LONG"
        and as_float(row.get("entry_rci9")) is not None and float(row["entry_rci9"]) < 0.0
    ]
    if len(source_like) != EXPECTED_SOURCE_LIKE_BTC_LONG:
        print(f"[M9K BLOCKED] expected {EXPECTED_SOURCE_LIKE_BTC_LONG} BTC LONG RCI9<0 trades, got {len(source_like)}")
        return 2

    trade_ids = {row["proxy_trade_id"] for row in source_like}
    checkpoint_rows = [row for row in checkpoints if row.get("proxy_trade_id") in trade_ids]
    outcome_by_id = {row["proxy_trade_id"]: row for row in source_like}
    enriched: list[dict[str, Any]] = []
    for row in checkpoint_rows:
        outcome = outcome_by_id[row["proxy_trade_id"]]
        final_return = float(outcome["return_bps"])
        record: dict[str, Any] = dict(row)
        record["entry_rci9"] = float(outcome["entry_rci9"])
        record["final_immediate_return_bps"] = final_return
        record["final_win"] = final_return > 0
        for label, threshold in TAIL_LABELS.items():
            record[label] = final_return <= threshold
        enriched.append(record)

    trade_returns = [float(row["return_bps"]) for row in source_like]
    winners = [value for value in trade_returns if value > 0]
    losses = [value for value in trade_returns if value < 0]
    checkpoint_summary: list[dict[str, Any]] = []
    for ratio in CHECKPOINT_RATIOS:
        selected = [row for row in enriched if abs(float(row["checkpoint_atr_ratio"]) - ratio) < 1e-12]
        original_returns = [float(row["final_immediate_return_bps"]) for row in selected]
        checkpoint_returns = [float(row["return_from_checkpoint_to_proxy_exit_bps"]) for row in selected]
        checkpoint_summary.append({
            "checkpoint_atr_ratio": ratio,
            "trades_reaching_checkpoint": len(selected),
            "fraction_of_113": len(selected) / EXPECTED_SOURCE_LIKE_BTC_LONG,
            "original_final_win_fraction": sum(v > 0 for v in original_returns) / len(original_returns) if original_returns else None,
            "tail_le_minus_50_fraction": sum(safe_bool(row["LOSS_LE_MINUS_50_BPS"]) for row in selected) / len(selected) if selected else None,
            "tail_le_minus_100_fraction": sum(safe_bool(row["LOSS_LE_MINUS_100_BPS"]) for row in selected) / len(selected) if selected else None,
            "tail_le_minus_200_fraction": sum(safe_bool(row["LOSS_LE_MINUS_200_BPS"]) for row in selected) / len(selected) if selected else None,
            "recovered_original_signal_fraction": sum(safe_bool(row.get("recovered_original_signal_bid_before_proxy_exit")) for row in selected) / len(selected) if selected else None,
            "checkpoint_to_exit_metrics": metrics(checkpoint_returns),
            "mean_elapsed_minutes": statistics.fmean(float(row["elapsed_minutes_from_signal"]) for row in selected) if selected else None,
        })

    numeric_rows: list[dict[str, Any]] = []
    categorical_rows: list[dict[str, Any]] = []
    for ratio in CHECKPOINT_RATIOS:
        numeric_rows.extend(numeric_contrasts(enriched, "LOSS_LE_MINUS_100_BPS", ratio=ratio))
        categorical_rows.extend(categorical_contrasts(enriched, "LOSS_LE_MINUS_100_BPS", ratio=ratio))

    top_features: list[dict[str, Any]] = []
    for ratio in CHECKPOINT_RATIOS:
        candidates = [
            row for row in numeric_rows
            if abs(float(row["checkpoint_atr_ratio"]) - ratio) < 1e-12 and row.get("abs_smd") is not None
        ][:12]
        top_features.extend(candidates)

    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M9K_BTC_LONG_CAUSAL_TAIL_LOSS_STATE_AUDIT",
        "status": "PASS_EXPLORATORY_ONLY",
        "run_at_utc": run_at,
        "population_tier": "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH",
        "population": {
            "btc_long_entry_rci9_lt_0": len(source_like),
            "checkpoint_rows": len(enriched),
            "win_rate": sum(v > 0 for v in trade_returns) / len(trade_returns),
            "profit_factor_bps": pf(trade_returns),
            "net_bps": sum(trade_returns),
            "average_win_bps": statistics.fmean(winners) if winners else None,
            "average_loss_bps": statistics.fmean(losses) if losses else None,
            "losses_le_minus_50_bps": sum(v <= -50 for v in trade_returns),
            "losses_le_minus_100_bps": sum(v <= -100 for v in trade_returns),
            "losses_le_minus_200_bps": sum(v <= -200 for v in trade_returns),
            "worst_bps": min(trade_returns),
        },
        "checkpoint_summary": checkpoint_summary,
        "tail_definition_role": "EVALUATION_LABEL_ONLY_NOT_STOP_OR_ENTRY_RULE",
        "research_question": "Can causal state observed after a source-like BTC LONG begins moving adversely distinguish recoverable pullbacks from the large-loss tail without further mining the entry RCI threshold?",
        "guardrails": {
            "checkpoint_depth_is_gate": False,
            "tail_bps_label_is_gate": False,
            "future_outcome_used_only_for_evaluation": True,
            "same_sample_rule_promotion_allowed": False,
            "automatic_threshold_selection": False,
            "m7c_formula_changed": False,
            "m7c_threshold_changed": False,
            "m8c_reset": False,
            "audit_only": True,
        },
    }
    quality = {
        "expected_m9c_resolved": EXPECTED_M9C_RESOLVED,
        "expected_m9d_checkpoints": EXPECTED_M9D_CHECKPOINTS,
        "expected_source_like_btc_long": EXPECTED_SOURCE_LIKE_BTC_LONG,
        "actual_source_like_btc_long": len(source_like),
        "checkpoint_features_reused_from_m9d_closed_bar_contract": True,
        "future_feature_leakage_added_by_m9k": False,
        "commission": "NOT_MODELED",
        "swap": "NOT_MODELED",
    }

    out_root = local_root / "outputs" / "M9K"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    dump_json(archive / "01_summary.json", summary)
    write_csv(archive / "02_source_like_btc_long_trades.csv", source_like)
    write_csv(archive / "03_tail_checkpoint_panel.csv", enriched)
    write_csv(archive / "04_checkpoint_tail_summary.csv", checkpoint_summary)
    write_csv(archive / "05_tail_numeric_feature_contrast.csv", numeric_rows)
    write_csv(archive / "06_tail_categorical_feature_contrast.csv", categorical_rows)
    write_csv(archive / "07_top_tail_feature_candidates.csv", top_features)
    dump_json(archive / "08_data_quality.json", quality)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M9K isolates the M9J BTC LONG RCI9<0 subset and studies causal state only after adverse movement begins. "
        "The -50/-100/-200 bps labels are evaluation labels for tail severity, not entry/stop rules. "
        "Checkpoint features are inherited from M9D's closed-bar causal contract. No live gate is promoted.\n",
        encoding="utf-8",
    )
    (archive / "09_audit.log").write_text(
        "\n".join([
            "status=PASS_EXPLORATORY_ONLY",
            "stage=M9K_BTC_LONG_CAUSAL_TAIL_LOSS_STATE_AUDIT",
            f"source_like_btc_long={len(source_like)}",
            f"checkpoint_rows={len(enriched)}",
            "tail_labels_are_evaluation_only=true",
            "checkpoint_depth_is_not_gate=true",
            "same_sample_rule_promotion_allowed=false",
            "m7c_formula_changed=false",
            "m7c_threshold_changed=false",
            "m8c_reset=false",
            "",
        ]),
        encoding="utf-8",
    )
    names = [
        "00_READ_ME_FIRST.txt", "01_summary.json", "02_source_like_btc_long_trades.csv", "03_tail_checkpoint_panel.csv",
        "04_checkpoint_tail_summary.csv", "05_tail_numeric_feature_contrast.csv", "06_tail_categorical_feature_contrast.csv",
        "07_top_tail_feature_candidates.csv", "08_data_quality.json", "09_audit.log",
    ]
    package = archive / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, arcname=name)
    latest = out_root / "LATEST"
    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(archive, latest)
    print("[M9K PASS]")
    print(f"source_like_btc_long={len(source_like)} checkpoints={len(enriched)}")
    print(f"package={latest / '99_UPLOAD_PACKAGE.zip'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
