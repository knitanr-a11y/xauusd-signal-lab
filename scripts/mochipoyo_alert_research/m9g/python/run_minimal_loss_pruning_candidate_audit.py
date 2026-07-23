from __future__ import annotations

import csv
import json
import math
import os
import shutil
import statistics
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

EXPECTED_FIRST_TURN_ROWS = 852
STAGE = "M9G_MINIMAL_LOSS_PRUNING_CANDIDATE_AUDIT"
CONTRACT = "MOCHIPOYO_M9G_MINIMAL_LOSS_PRUNING_V1"


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


def as_float(value: Any) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"non-finite numeric value: {value!r}")
    return result


def profit_factor(values: list[float]) -> float | None:
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = abs(sum(value for value in values if value < 0))
    return None if gross_loss == 0 else gross_profit / gross_loss


def max_drawdown(values: list[float]) -> float:
    cumulative = 0.0
    peak = 0.0
    worst = 0.0
    for value in values:
        cumulative += value
        peak = max(peak, cumulative)
        worst = max(worst, peak - cumulative)
    return worst


def max_losing_streak(values: list[float]) -> int:
    current = 0
    worst = 0
    for value in values:
        if value < 0:
            current += 1
            worst = max(worst, current)
        else:
            current = 0
    return worst


def metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: (row["decision_time"], row["proxy_trade_id"]))
    values = [as_float(row["return_bps"]) for row in ordered]
    if not values:
        return {
            "count": 0,
            "win_rate": None,
            "profit_factor_bps": None,
            "net_bps": 0.0,
            "mean_bps": None,
            "median_bps": None,
            "max_drawdown_bps": 0.0,
            "max_losing_streak": 0,
        }
    return {
        "count": len(values),
        "win_rate": sum(value > 0 for value in values) / len(values),
        "profit_factor_bps": profit_factor(values),
        "net_bps": sum(values),
        "mean_bps": statistics.fmean(values),
        "median_bps": statistics.median(values),
        "max_drawdown_bps": max_drawdown(values),
        "max_losing_streak": max_losing_streak(values),
    }


def is_btc_long_fresh_conflict(row: dict[str, str]) -> bool:
    return (
        row["ticker"] == "BTCUSD"
        and row["direction"] == "LONG"
        and row["within_3_bars_signature"] == "BOTH"
    )


def is_btc_short_supportive_only_hidden(row: dict[str, str]) -> bool:
    return (
        row["ticker"] == "BTCUSD"
        and row["direction"] == "SHORT"
        and row["within_3_bars_signature"] == "SUPPORTIVE_ONLY"
        and int(float(row["within_3_bars_supportive_hidden_count"])) > 0
    )


def is_btc_short_supportive_only(row: dict[str, str]) -> bool:
    return (
        row["ticker"] == "BTCUSD"
        and row["direction"] == "SHORT"
        and row["within_3_bars_signature"] == "SUPPORTIVE_ONLY"
    )


def accept_all(row: dict[str, str]) -> bool:
    return True


def accept_p1(row: dict[str, str]) -> bool:
    return not is_btc_long_fresh_conflict(row)


def accept_p2(row: dict[str, str]) -> bool:
    return not (is_btc_long_fresh_conflict(row) or is_btc_short_supportive_only_hidden(row))


def accept_p3(row: dict[str, str]) -> bool:
    return not (is_btc_long_fresh_conflict(row) or is_btc_short_supportive_only(row))


POLICIES: list[tuple[str, str, Callable[[dict[str, str]], bool]]] = [
    ("P0_CONTROL_ALL", "accept all first-turn candidates", accept_all),
    (
        "P1_BTC_LONG_FRESH_CONFLICT",
        "reject BTCUSD LONG when within_3_bars_signature=BOTH",
        accept_p1,
    ),
    (
        "P2_MINIMAL_TWO_BRANCH",
        "P1 plus reject BTCUSD SHORT supportive-only when fresh supportive hidden divergence is present",
        accept_p2,
    ),
    (
        "P3_BROADER_TWO_BRANCH_SENSITIVITY",
        "P1 plus reject all BTCUSD SHORT within_3_bars_signature=SUPPORTIVE_ONLY",
        accept_p3,
    ),
]


def month_of(row: dict[str, str]) -> str:
    return row["decision_time"][:7]


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    m9f_latest = local_root / "outputs" / "M9F" / "LATEST"
    summary_path = m9f_latest / "01_summary.json"
    panel_path = m9f_latest / "03_decision_recency_panel.csv"
    if not summary_path.is_file() or not panel_path.is_file():
        print("[M9G BLOCKED] M9F LATEST summary/panel is missing")
        return 2

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "PASS_EXPLORATORY_ONLY"
        or summary.get("stage") != "M9F_DIVERGENCE_RECENCY_LOCALITY_AUDIT"
        or int(summary.get("first_turn_rows", -1)) != EXPECTED_FIRST_TURN_ROWS
        or summary.get("population_tier") != "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH"
    ):
        print("[M9G BLOCKED] M9F LATEST does not match the reviewed population")
        return 2

    panel = read_csv(panel_path)
    first_turn = [row for row in panel if row.get("panel_kind") == "FIRST_TURN"]
    if len(first_turn) != EXPECTED_FIRST_TURN_ROWS:
        print(f"[M9G BLOCKED] expected {EXPECTED_FIRST_TURN_ROWS} first-turn rows, got {len(first_turn)}")
        return 2
    if len({row["proxy_trade_id"] for row in first_turn}) != EXPECTED_FIRST_TURN_ROWS:
        print("[M9G BLOCKED] first-turn proxy_trade_id is not unique")
        return 2

    policy_summary: list[dict[str, Any]] = []
    monthly_summary: list[dict[str, Any]] = []
    ticker_direction_summary: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []

    for policy_id, description, accept_fn in POLICIES:
        accepted = [row for row in first_turn if accept_fn(row)]
        rejected = [row for row in first_turn if not accept_fn(row)]
        accepted_metrics = metrics(accepted)
        rejected_metrics = metrics(rejected)
        policy_summary.append(
            {
                "policy_id": policy_id,
                "description": description,
                "baseline_count": EXPECTED_FIRST_TURN_ROWS,
                "accepted_count": len(accepted),
                "retention_fraction": len(accepted) / EXPECTED_FIRST_TURN_ROWS,
                **{f"accepted_{key}": value for key, value in accepted_metrics.items() if key != "count"},
                "rejected_count": len(rejected),
                **{f"rejected_{key}": value for key, value in rejected_metrics.items() if key != "count"},
                "same_sample_validation": False,
            }
        )

        months = sorted({month_of(row) for row in first_turn})
        for month in months:
            month_all = [row for row in first_turn if month_of(row) == month]
            month_accepted = [row for row in accepted if month_of(row) == month]
            month_rejected = [row for row in rejected if month_of(row) == month]
            am = metrics(month_accepted)
            rm = metrics(month_rejected)
            monthly_summary.append(
                {
                    "policy_id": policy_id,
                    "month": month,
                    "baseline_count": len(month_all),
                    "accepted_count": len(month_accepted),
                    "retention_fraction": len(month_accepted) / len(month_all) if month_all else None,
                    **{f"accepted_{key}": value for key, value in am.items() if key != "count"},
                    "rejected_count": len(month_rejected),
                    **{f"rejected_{key}": value for key, value in rm.items() if key != "count"},
                }
            )

        for ticker, direction in sorted({(row["ticker"], row["direction"]) for row in first_turn}):
            selected = [row for row in accepted if row["ticker"] == ticker and row["direction"] == direction]
            block = metrics(selected)
            ticker_direction_summary.append(
                {
                    "policy_id": policy_id,
                    "ticker": ticker,
                    "direction": direction,
                    **block,
                }
            )

        for row in rejected:
            rejected_rows.append(
                {
                    "policy_id": policy_id,
                    "proxy_trade_id": row["proxy_trade_id"],
                    "ticker": row["ticker"],
                    "direction": row["direction"],
                    "decision_time": row["decision_time"],
                    "return_bps": row["return_bps"],
                    "within_3_bars_signature": row["within_3_bars_signature"],
                    "within_3_bars_supportive_regular_count": row["within_3_bars_supportive_regular_count"],
                    "within_3_bars_supportive_hidden_count": row["within_3_bars_supportive_hidden_count"],
                    "within_3_bars_opposing_regular_count": row["within_3_bars_opposing_regular_count"],
                    "within_3_bars_opposing_hidden_count": row["within_3_bars_opposing_hidden_count"],
                }
            )

    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": STAGE,
        "contract": CONTRACT,
        "status": "PASS_EXPLORATORY_ONLY",
        "run_at_utc": built_at,
        "population_tier": "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH",
        "first_turn_population": EXPECTED_FIRST_TURN_ROWS,
        "policy_count": len(POLICIES),
        "interpretation_contract": {
            "same_sample_hypothesis_generation_only": True,
            "same_sample_validation": False,
            "automatic_best_policy_promotion": False,
            "future_new_prospective_sample_required": True,
            "m8c_start_reuse_or_reset": False,
        },
        "safety": {
            "audit_only": True,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
            "entry_gate_enabled": False,
            "m7c_formula_changed": False,
            "m7c_threshold_changed": False,
            "m8c_reset": False,
        },
    }

    out_root = local_root / "outputs" / "M9G"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)

    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M9G compares a small frozen set of M9F-derived loss-pruning hypotheses on the SAME Tier-B first-turn sample. "
        "This run is exploratory only and cannot validate or promote a live gate. Preserve monthly frequency, PF, DD and losing-streak context.\n",
        encoding="utf-8",
    )
    dump_json(archive / "01_summary.json", result)
    write_csv(archive / "02_policy_summary.csv", policy_summary)
    write_csv(archive / "03_monthly_policy_summary.csv", monthly_summary)
    write_csv(archive / "04_ticker_direction_summary.csv", ticker_direction_summary)
    write_csv(archive / "05_rejected_trade_detail.csv", rejected_rows)
    (archive / "06_audit.log").write_text(
        "\n".join(
            [
                "status=PASS_EXPLORATORY_ONLY",
                f"contract={CONTRACT}",
                f"first_turn_population={EXPECTED_FIRST_TURN_ROWS}",
                f"policy_count={len(POLICIES)}",
                "same_sample_validation=false",
                "automatic_gate_promotion=false",
                "m7c_formula_changed=false",
                "m7c_threshold_changed=false",
                "m8c_reset=false",
                "",
            ]
        ),
        encoding="utf-8",
    )

    names = [
        "00_READ_ME_FIRST.txt",
        "01_summary.json",
        "02_policy_summary.csv",
        "03_monthly_policy_summary.csv",
        "04_ticker_direction_summary.csv",
        "05_rejected_trade_detail.csv",
        "06_audit.log",
    ]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)

    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)

    print(f"[M9G PASS] first_turn={EXPECTED_FIRST_TURN_ROWS} policies={len(POLICIES)}")
    print("[M9G OUTPUT]", latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
