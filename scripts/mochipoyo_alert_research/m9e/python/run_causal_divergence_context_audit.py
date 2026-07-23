from __future__ import annotations

import bisect
import csv
import json
import os
import shutil
import statistics
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
EXPECTED_CHECKPOINT_ROWS = 3039
EXPECTED_TURN_ROWS = 852
TIMEFRAMES = ("M1", "M5", "M15", "H1", "H4")
SCALES = {
    "short": {"depth": 5, "right": 2},
    "medium": {"depth": 12, "right": 3},
}
OSCILLATORS = ("RCI9", "RCI14", "RCI18", "MACD_LINE", "MACD_HISTOGRAM")

THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parents[4]
RESEARCH_ROOT = REPO_ROOT / "scripts" / "mochipoyo_alert_research"
if str(RESEARCH_ROOT) not in sys.path:
    sys.path.insert(0, str(RESEARCH_ROOT))

from feature_snapshot_builder import load_indicator_series
from mt5_csv_contract import FILE_MAP, TIMEFRAME_SECONDS


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


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def oscillator_value(series: Any, oscillator: str, index: int) -> float | None:
    if oscillator == "RCI9":
        value = series.rci[9][index]
    elif oscillator == "RCI14":
        value = series.rci[14][index]
    elif oscillator == "RCI18":
        value = series.rci[18][index]
    elif oscillator == "MACD_LINE":
        value = series.macd_line[index]
    elif oscillator == "MACD_HISTOGRAM":
        value = series.macd_histogram[index]
    else:
        raise ValueError(f"unknown oscillator: {oscillator}")
    return None if value is None else float(value)


def precompute_confirmed_pivots(series: Any, *, depth: int, right: int) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {"LOW": [], "HIGH": []}
    bars = series.bars
    minimum_confirmation = depth - 1 + right
    for confirmation_index in range(minimum_confirmation, len(bars)):
        pivot_index = confirmation_index - right
        start = pivot_index - depth + 1
        if start < 0:
            continue
        window = bars[start : confirmation_index + 1]
        pivot = bars[pivot_index]
        highs = [bar.high_price for bar in window]
        lows = [bar.low_price for bar in window]
        is_high = pivot.high_price == max(highs) and highs.count(pivot.high_price) == 1
        is_low = pivot.low_price == min(lows) and lows.count(pivot.low_price) == 1
        if is_high == is_low:
            continue
        side = "HIGH" if is_high else "LOW"
        output[side].append(
            {
                "side": side,
                "pivot_index": pivot_index,
                "confirmation_index": confirmation_index,
                "pivot_time": pivot.server_open,
                "confirmation_time": bars[confirmation_index].server_open,
                "price": pivot.high_price if is_high else pivot.low_price,
            }
        )
    return output


def latest_two_confirmed(
    events: list[dict[str, Any]],
    confirmation_indices: list[int],
    selected_index: int,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    count = bisect.bisect_right(confirmation_indices, selected_index)
    if count < 2:
        return None
    return events[count - 2], events[count - 1]


def classify_divergence(
    *,
    side: str,
    price1: float,
    price2: float,
    osc1: float,
    osc2: float,
) -> str:
    if side == "LOW":
        if price2 < price1 and osc2 > osc1:
            return "BULLISH_REGULAR"
        if price2 > price1 and osc2 < osc1:
            return "BULLISH_HIDDEN"
    else:
        if price2 > price1 and osc2 < osc1:
            return "BEARISH_REGULAR"
        if price2 < price1 and osc2 > osc1:
            return "BEARISH_HIDDEN"
    return "NONE"


def directional_role(direction: str, divergence_type: str) -> str:
    if divergence_type == "NONE":
        return "NONE"
    bullish = divergence_type.startswith("BULLISH_")
    supportive = bullish if direction == "LONG" else not bullish
    return "SUPPORTIVE" if supportive else "OPPOSING"


def subtype(divergence_type: str) -> str:
    if divergence_type.endswith("_REGULAR"):
        return "REGULAR"
    if divergence_type.endswith("_HIDDEN"):
        return "HIDDEN"
    return "NONE"


def metric_block(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [as_float(row.get(key)) for row in rows]
    values = [value for value in values if value is not None]
    if not values:
        return {"count": 0, "win_rate": None, "profit_factor_bps": None, "net_bps": 0.0, "mean_bps": None}
    wins = sum(value for value in values if value > 0)
    losses = abs(sum(value for value in values if value < 0))
    return {
        "count": len(values),
        "win_rate": sum(value > 0 for value in values) / len(values),
        "profit_factor_bps": None if losses == 0 else wins / losses,
        "net_bps": sum(values),
        "mean_bps": statistics.fmean(values),
    }


def recovery_fraction(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row.get(key) for row in rows if row.get(key) not in (None, "")]
    if not values:
        return None
    return sum(as_bool(value) for value in values) / len(values)


def build_context_for_row(
    *,
    source_row: dict[str, str],
    panel_kind: str,
    decision_time: datetime,
    series_by_ticker: dict[str, dict[str, Any]],
    close_times: dict[str, dict[str, list[datetime]]],
    pivots: dict[str, dict[str, dict[str, dict[str, Any]]]],
) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    ticker = source_row["ticker"]
    direction = source_row["direction"]
    trade_id = source_row["proxy_trade_id"]
    base: dict[str, Any] = {
        "panel_kind": panel_kind,
        "proxy_trade_id": trade_id,
        "ticker": ticker,
        "direction": direction,
        "decision_time": decision_time.strftime(TIME_FORMAT),
        "entry_server_open": source_row.get("entry_server_open", ""),
        "exit_server_open": source_row.get("exit_server_open", ""),
        "checkpoint_atr_ratio": source_row.get("checkpoint_atr_ratio", "") if panel_kind == "CHECKPOINT" else "",
        "supportive_regular_count": 0,
        "supportive_hidden_count": 0,
        "opposing_regular_count": 0,
        "opposing_hidden_count": 0,
        "supportive_any": False,
        "opposing_any": False,
        "supportive_contexts": "",
        "opposing_contexts": "",
    }
    if panel_kind == "CHECKPOINT":
        base["return_bps"] = source_row.get("return_from_checkpoint_to_proxy_exit_bps", "")
        base["recovered_signal"] = source_row.get("recovered_original_signal_bid_before_proxy_exit", "")
        base["positive_at_frozen_proxy_exit"] = source_row.get("positive_at_frozen_proxy_exit", "")
        base["realized_adverse_depth_atr"] = source_row.get("realized_adverse_depth_atr", "")
        base["elapsed_minutes_from_signal"] = source_row.get("elapsed_minutes_from_signal", "")
    else:
        base["return_bps"] = source_row.get("return_from_first_turn_bps", "")
        base["initial_pullback_depth_bps"] = source_row.get("initial_pullback_depth_bps", "")
        base["minutes_to_first_turn"] = source_row.get("minutes_to_first_turn", "")

    detail: list[dict[str, Any]] = []
    unavailable = 0
    supportive_contexts: set[str] = set()
    opposing_contexts: set[str] = set()

    for timeframe in TIMEFRAMES:
        series = series_by_ticker[ticker][timeframe]
        selected_index = bisect.bisect_right(close_times[ticker][timeframe], decision_time) - 1
        if selected_index < 0:
            unavailable += len(SCALES) * len(OSCILLATORS) * 2
            continue

        for scale_name in SCALES:
            scale_pivots = pivots[ticker][timeframe][scale_name]
            for side in ("LOW", "HIGH"):
                events = scale_pivots[side]["events"]
                confirmations = scale_pivots[side]["confirmations"]
                pair = latest_two_confirmed(events, confirmations, selected_index)
                if pair is None:
                    unavailable += len(OSCILLATORS)
                    continue
                first_pivot, second_pivot = pair
                for oscillator in OSCILLATORS:
                    osc1 = oscillator_value(series, oscillator, int(first_pivot["pivot_index"]))
                    osc2 = oscillator_value(series, oscillator, int(second_pivot["pivot_index"]))
                    if osc1 is None or osc2 is None:
                        unavailable += 1
                        continue
                    div_type = classify_divergence(
                        side=side,
                        price1=float(first_pivot["price"]),
                        price2=float(second_pivot["price"]),
                        osc1=osc1,
                        osc2=osc2,
                    )
                    if div_type == "NONE":
                        continue
                    role = directional_role(direction, div_type)
                    div_subtype = subtype(div_type)
                    context_name = f"{timeframe}:{scale_name}:{oscillator}:{div_type}"
                    if role == "SUPPORTIVE":
                        supportive_contexts.add(context_name)
                        if div_subtype == "REGULAR":
                            base["supportive_regular_count"] += 1
                        else:
                            base["supportive_hidden_count"] += 1
                    else:
                        opposing_contexts.add(context_name)
                        if div_subtype == "REGULAR":
                            base["opposing_regular_count"] += 1
                        else:
                            base["opposing_hidden_count"] += 1

                    detail.append(
                        {
                            "panel_kind": panel_kind,
                            "proxy_trade_id": trade_id,
                            "ticker": ticker,
                            "direction": direction,
                            "decision_time": decision_time.strftime(TIME_FORMAT),
                            "checkpoint_atr_ratio": base.get("checkpoint_atr_ratio", ""),
                            "timeframe": timeframe,
                            "scale": scale_name,
                            "oscillator": oscillator,
                            "pivot_side": side,
                            "divergence_type": div_type,
                            "directional_role": role,
                            "divergence_subtype": div_subtype,
                            "first_pivot_time": first_pivot["pivot_time"].strftime(TIME_FORMAT),
                            "second_pivot_time": second_pivot["pivot_time"].strftime(TIME_FORMAT),
                            "second_pivot_confirmed_by": second_pivot["confirmation_time"].strftime(TIME_FORMAT),
                            "first_price": first_pivot["price"],
                            "second_price": second_pivot["price"],
                            "first_oscillator": osc1,
                            "second_oscillator": osc2,
                            "return_bps": base.get("return_bps", ""),
                            "recovered_signal": base.get("recovered_signal", ""),
                            "positive_at_frozen_proxy_exit": base.get("positive_at_frozen_proxy_exit", ""),
                            "created_without_future_pivot_confirmation": second_pivot["confirmation_index"] <= selected_index,
                        }
                    )

    base["supportive_any"] = bool(supportive_contexts)
    base["opposing_any"] = bool(opposing_contexts)
    base["supportive_contexts"] = "|".join(sorted(supportive_contexts))
    base["opposing_contexts"] = "|".join(sorted(opposing_contexts))
    return base, detail, unavailable


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    m9d_latest = local_root / "outputs" / "M9D" / "LATEST"
    m9d_summary_path = m9d_latest / "01_summary.json"
    checkpoint_path = m9d_latest / "02_adverse_checkpoint_feature_panel.csv"
    turn_path = m9d_latest / "04_first_turn_rich_feature_panel.csv"
    meta_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"

    required = [m9d_summary_path, checkpoint_path, turn_path, meta_path]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print(f"[M9E BLOCKED] required upstream file missing: {missing}")
        return 2

    summary = json.loads(m9d_summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("status") != "PASS_EXPLORATORY_ONLY"
        or summary.get("contract") != "MOCHIPOYO_M9D_CAUSAL_ADVERSE_PATH_STATE_V1"
        or int(summary.get("checkpoint_rows", -1)) != EXPECTED_CHECKPOINT_ROWS
        or int(summary.get("turn_rich_feature_rows", -1)) != EXPECTED_TURN_ROWS
    ):
        print("[M9E BLOCKED] M9D LATEST does not match the reviewed population")
        return 2

    checkpoint_source = read_csv(checkpoint_path)
    turn_source = read_csv(turn_path)
    if len(checkpoint_source) != EXPECTED_CHECKPOINT_ROWS or len(turn_source) != EXPECTED_TURN_ROWS:
        print("[M9E BLOCKED] M9D panel row counts changed")
        return 2

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    files_root = Path(meta.get("mt5_files_root", ""))
    if not files_root.is_dir():
        print(f"[M9E BLOCKED] MT5 Files root unavailable: {files_root}")
        return 2

    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        series_by_ticker: dict[str, dict[str, Any]] = defaultdict(dict)
        close_times: dict[str, dict[str, list[datetime]]] = defaultdict(dict)
        pivots: dict[str, dict[str, dict[str, dict[str, Any]]]] = defaultdict(lambda: defaultdict(dict))

        for ticker in ("XAUUSD", "BTCUSD"):
            for timeframe in TIMEFRAMES:
                series = load_indicator_series(files_root / FILE_MAP[ticker][timeframe])
                series_by_ticker[ticker][timeframe] = series
                delta = timedelta(seconds=TIMEFRAME_SECONDS[timeframe])
                close_times[ticker][timeframe] = [bar.server_open + delta for bar in series.bars]
                for scale_name, settings in SCALES.items():
                    precomputed = precompute_confirmed_pivots(
                        series,
                        depth=int(settings["depth"]),
                        right=int(settings["right"]),
                    )
                    pivots[ticker][timeframe][scale_name] = {
                        side: {
                            "events": events,
                            "confirmations": [int(item["confirmation_index"]) for item in events],
                        }
                        for side, events in precomputed.items()
                    }

        checkpoint_panel: list[dict[str, Any]] = []
        turn_panel: list[dict[str, Any]] = []
        event_detail: list[dict[str, Any]] = []
        unavailable_counts: dict[str, int] = defaultdict(int)

        for source_row in checkpoint_source:
            decision_time = parse_time(source_row["checkpoint_decision_time"])
            panel_row, details, unavailable = build_context_for_row(
                source_row=source_row,
                panel_kind="CHECKPOINT",
                decision_time=decision_time,
                series_by_ticker=series_by_ticker,
                close_times=close_times,
                pivots=pivots,
            )
            checkpoint_panel.append(panel_row)
            event_detail.extend(details)
            unavailable_counts["checkpoint_oscillator_pivot_contexts"] += unavailable

        for source_row in turn_source:
            decision_time = parse_time(source_row["turn_entry_time"])
            panel_row, details, unavailable = build_context_for_row(
                source_row=source_row,
                panel_kind="FIRST_TURN",
                decision_time=decision_time,
                series_by_ticker=series_by_ticker,
                close_times=close_times,
                pivots=pivots,
            )
            turn_panel.append(panel_row)
            event_detail.extend(details)
            unavailable_counts["turn_oscillator_pivot_contexts"] += unavailable

    except Exception as exc:
        print(f"[M9E BLOCKED] {exc}")
        return 2

    panel_lookup: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in checkpoint_panel + turn_panel:
        panel_lookup[
            (
                row["panel_kind"],
                row["proxy_trade_id"],
                row["decision_time"],
                str(row.get("checkpoint_atr_ratio", "")),
            )
        ] = row

    context_summary: list[dict[str, Any]] = []
    grouping_keys = ("timeframe", "scale", "oscillator", "divergence_type", "directional_role")
    grouped_events: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for event in event_detail:
        key = tuple(str(event[item]) for item in grouping_keys)
        grouped_events[key].append(event)

    for key, events in sorted(grouped_events.items()):
        by_decision: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for event in events:
            lookup_key = (
                event["panel_kind"],
                event["proxy_trade_id"],
                event["decision_time"],
                str(event.get("checkpoint_atr_ratio", "")),
            )
            by_decision[lookup_key] = panel_lookup[lookup_key]
        decisions = list(by_decision.values())
        checkpoint_decisions = [row for row in decisions if row["panel_kind"] == "CHECKPOINT"]
        turn_decisions = [row for row in decisions if row["panel_kind"] == "FIRST_TURN"]
        checkpoint_metric = metric_block(checkpoint_decisions, "return_bps")
        turn_metric = metric_block(turn_decisions, "return_bps")
        context_summary.append(
            {
                **dict(zip(grouping_keys, key)),
                "unique_decision_count": len(decisions),
                "checkpoint_decision_count": len(checkpoint_decisions),
                "checkpoint_win_rate": checkpoint_metric["win_rate"],
                "checkpoint_pf": checkpoint_metric["profit_factor_bps"],
                "checkpoint_net_bps": checkpoint_metric["net_bps"],
                "checkpoint_recovery_fraction": recovery_fraction(checkpoint_decisions, "recovered_signal"),
                "turn_decision_count": len(turn_decisions),
                "turn_win_rate": turn_metric["win_rate"],
                "turn_pf": turn_metric["profit_factor_bps"],
                "turn_net_bps": turn_metric["net_bps"],
            }
        )

    directional_summary: list[dict[str, Any]] = []
    for panel_kind, panel in (("CHECKPOINT", checkpoint_panel), ("FIRST_TURN", turn_panel)):
        for ticker in ("XAUUSD", "BTCUSD"):
            for direction in ("LONG", "SHORT"):
                subset = [row for row in panel if row["ticker"] == ticker and row["direction"] == direction]
                for label, selector in (
                    ("SUPPORTIVE_ANY", lambda row: bool(row["supportive_any"])),
                    ("NO_SUPPORTIVE", lambda row: not bool(row["supportive_any"])),
                    ("OPPOSING_ANY", lambda row: bool(row["opposing_any"])),
                    ("NO_OPPOSING", lambda row: not bool(row["opposing_any"])),
                    ("SUPPORTIVE_HIDDEN_ANY", lambda row: int(row["supportive_hidden_count"]) > 0),
                    ("SUPPORTIVE_REGULAR_ANY", lambda row: int(row["supportive_regular_count"]) > 0),
                ):
                    selected = [row for row in subset if selector(row)]
                    metric = metric_block(selected, "return_bps")
                    directional_summary.append(
                        {
                            "panel_kind": panel_kind,
                            "ticker": ticker,
                            "direction": direction,
                            "group": label,
                            **metric,
                            "recovery_fraction": recovery_fraction(selected, "recovered_signal")
                            if panel_kind == "CHECKPOINT"
                            else None,
                        }
                    )

    monthly: list[dict[str, Any]] = []
    for panel_kind, panel in (("CHECKPOINT", checkpoint_panel), ("FIRST_TURN", turn_panel)):
        keys = sorted({(row["decision_time"][:7], row["ticker"], row["direction"]) for row in panel})
        for month, ticker, direction in keys:
            subset = [
                row for row in panel
                if row["decision_time"].startswith(month)
                and row["ticker"] == ticker
                and row["direction"] == direction
            ]
            for label, selector in (
                ("SUPPORTIVE_ANY", lambda row: bool(row["supportive_any"])),
                ("NO_SUPPORTIVE", lambda row: not bool(row["supportive_any"])),
            ):
                selected = [row for row in subset if selector(row)]
                if not selected:
                    continue
                monthly.append(
                    {
                        "panel_kind": panel_kind,
                        "month": month,
                        "ticker": ticker,
                        "direction": direction,
                        "group": label,
                        **metric_block(selected, "return_bps"),
                    }
                )

    summary_output = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": "M9E_CAUSAL_DIVERGENCE_CONTEXT_AUDIT",
        "contract": "MOCHIPOYO_M9E_CAUSAL_DIVERGENCE_CONTEXT_V1",
        "status": "PASS_EXPLORATORY_ONLY",
        "run_at_utc": built_at,
        "audit_only": True,
        "population_tier": "TIER_B_FROZEN_PROXY_REPLAY_NOT_SOURCE_TRUTH",
        "checkpoint_rows": len(checkpoint_panel),
        "first_turn_rows": len(turn_panel),
        "divergence_event_rows": len(event_detail),
        "checkpoint_supportive_any_count": sum(bool(row["supportive_any"]) for row in checkpoint_panel),
        "checkpoint_opposing_any_count": sum(bool(row["opposing_any"]) for row in checkpoint_panel),
        "turn_supportive_any_count": sum(bool(row["supportive_any"]) for row in turn_panel),
        "turn_opposing_any_count": sum(bool(row["opposing_any"]) for row in turn_panel),
        "pivot_scales": SCALES,
        "timeframes": list(TIMEFRAMES),
        "oscillators": list(OSCILLATORS),
        "guardrails": {
            "all_pivots_confirmed_by_decision_time": True,
            "future_pivot_confirmation_used": False,
            "same_sample_rule_promotion_allowed": False,
            "automatic_threshold_or_gate_promotion": False,
            "m7c_formula_changed": False,
            "m7c_threshold_changed": False,
            "m8c_reset": False,
        },
    }
    quality = {
        "expected_checkpoint_rows": EXPECTED_CHECKPOINT_ROWS,
        "actual_checkpoint_rows": len(checkpoint_panel),
        "expected_first_turn_rows": EXPECTED_TURN_ROWS,
        "actual_first_turn_rows": len(turn_panel),
        "oscillator_or_pivot_unavailable_counts": dict(unavailable_counts),
        "pivot_method": "INDEPENDENT_CAUSAL_CONFIRMED_PRICE_PIVOT_PROXY",
        "proprietary_zigzag_reconstruction_claim": False,
        "closed_bars_only": True,
        "future_relative_to_decision_used_for_divergence": False,
        "mt5_files_root": str(files_root),
    }

    out_root = local_root / "outputs" / "M9E"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)

    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M9E adds causal regular/hidden divergence context to M9D adverse checkpoints and first-turn entries. "
        "Confirmed price pivots only; no future pivot confirmation is used. This is exploratory Tier B research, "
        "not genuine Mochipoyo source truth and not a promoted trading rule.\n",
        encoding="utf-8",
    )
    dump_json(archive / "01_summary.json", summary_output)
    write_csv(archive / "02_checkpoint_divergence_panel.csv", checkpoint_panel)
    write_csv(archive / "03_first_turn_divergence_panel.csv", turn_panel)
    write_csv(archive / "04_divergence_event_detail.csv", event_detail)
    write_csv(archive / "05_context_summary.csv", context_summary)
    write_csv(archive / "06_directional_summary.csv", directional_summary)
    write_csv(archive / "07_monthly_replication.csv", monthly)
    dump_json(archive / "08_data_quality.json", quality)
    (archive / "09_audit.log").write_text(
        "\n".join(
            [
                "status=PASS_EXPLORATORY_ONLY",
                "contract=MOCHIPOYO_M9E_CAUSAL_DIVERGENCE_CONTEXT_V1",
                f"checkpoint_rows={len(checkpoint_panel)}",
                f"first_turn_rows={len(turn_panel)}",
                f"divergence_event_rows={len(event_detail)}",
                "future_pivot_confirmation_used=false",
                "same_sample_rule_promotion_allowed=false",
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
        "02_checkpoint_divergence_panel.csv",
        "03_first_turn_divergence_panel.csv",
        "04_divergence_event_detail.csv",
        "05_context_summary.csv",
        "06_directional_summary.csv",
        "07_monthly_replication.csv",
        "08_data_quality.json",
        "09_audit.log",
    ]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)

    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)

    print(
        f"[M9E PASS] checkpoints={len(checkpoint_panel)} turns={len(turn_panel)} "
        f"divergence_events={len(event_detail)}"
    )
    print("[M9E OUTPUT]", latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
