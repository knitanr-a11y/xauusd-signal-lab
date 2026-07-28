from __future__ import annotations

import bisect
import csv
import json
import math
import os
import shutil
import sys
import zipfile
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
for directory in (MR / "m10a" / "python", MR / "m9p" / "python"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import frozen_core as frozen
import payoff_rules as pay

STAGE = "M10W21_PREREGISTERED_HIGH_ATR_BULLISH_ENTRY_EVALUATION_AUDIT_ONLY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w20_high_atr_bullish_entry_hypothesis_preregistration_20260728.json"
TIME_FORMAT = frozen.TIME_FORMAT
POINT = frozen.POINT
HORIZON = timedelta(minutes=240)
FIXED_SPREAD_USD = 0.20
ATR_GATE = 0.67

FAMILIES = (
    "HBR1_LONG_HIGH_ATR_1H_BREAKOUT",
    "HER1_LONG_HIGH_ATR_EMA20_RECLAIM",
    "HRC1_LONG_HIGH_ATR_RCI9_OVERSOLD_TURN",
)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


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


def resolve_data_root(local_root: Path) -> Path:
    override = os.environ.get("M10A_GOLD_DATA_ROOT", "").strip()
    if override:
        return Path(override)
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    metadata = load_json(metadata_path) if metadata_path.is_file() else {}
    return Path(str(metadata.get("mt5_files_root", ""))) / "gold_v3_2023_2026"


def verify_and_load(data_root: Path) -> tuple[dict[str, list[frozen.Bar]], dict[str, str]]:
    bars: dict[str, list[frozen.Bar]] = {}
    hashes: dict[str, str] = {}
    for timeframe in ("M1", "M15", "H1", "H4", "D1"):
        filename, expected_hash = frozen.EXPECTED_FILES[timeframe]
        path = data_root / filename
        if not path.is_file():
            raise RuntimeError(f"missing frozen GOLD file: {path}")
        actual_hash = frozen.sha256(path)
        if actual_hash != expected_hash:
            raise RuntimeError(f"frozen SHA256 mismatch {timeframe}: {actual_hash} expected={expected_hash}")
        bars[timeframe] = frozen.load_bars(path)
        hashes[timeframe] = actual_hash
    return bars, hashes


def atr_percentile100(bars: list[frozen.Bar]) -> list[float | None]:
    atr = pay.wilder_atr14(bars)
    output: list[float | None] = [None] * len(atr)
    for index in range(99, len(atr)):
        window = atr[index - 99:index + 1]
        if any(value is None or not math.isfinite(float(value)) for value in window):
            continue
        current = float(atr[index])
        values = [float(value) for value in window if value is not None]
        output[index] = sum(value <= current for value in values) / len(values)
    return output


def build_candidates(bars: dict[str, list[frozen.Bar]]) -> dict[str, list[dict[str, Any]]]:
    m15, h1, h4, d1 = bars["M15"], bars["H1"], bars["H4"], bars["D1"]

    m15_closes = [float(bar.close) for bar in m15]
    m15_ema20 = frozen.ema(m15_closes, 20)
    m15_ema30 = frozen.ema(m15_closes, 30)
    m15_rci9 = frozen.rci_series(m15_closes, 9)

    h1_macd = frozen.macd_bps(h1)
    h1_atrp = atr_percentile100(h1)

    h4_closes = [float(bar.close) for bar in h4]
    h4_ema20 = frozen.ema(h4_closes, 20)
    h4_ema30 = frozen.ema(h4_closes, 30)

    d1_closes = [float(bar.close) for bar in d1]
    d1_ema20 = frozen.ema(d1_closes, 20)
    d1_ema30 = frozen.ema(d1_closes, 30)
    d1_ema40 = frozen.ema(d1_closes, 40)

    h1_close_times = [bar.time + timedelta(hours=1) for bar in h1]
    h4_close_times = [bar.time + timedelta(hours=4) for bar in h4]
    d1_close_times = [bar.time + timedelta(days=1) for bar in d1]

    output: dict[str, list[dict[str, Any]]] = {family: [] for family in FAMILIES}

    for i in range(30, len(m15) - 1):
        decision = m15[i + 1].time
        ih1 = bisect.bisect_right(h1_close_times, decision) - 1
        ih4 = bisect.bisect_right(h4_close_times, decision) - 1
        id1 = bisect.bisect_right(d1_close_times, decision) - 1
        if min(ih1, ih4, id1) < 0:
            continue
        atrp = h1_atrp[ih1]
        if atrp is None or float(atrp) < ATR_GATE:
            continue
        regime = (
            float(d1_ema20[id1]) > float(d1_ema30[id1]) > float(d1_ema40[id1])
            and float(h4_ema20[ih4]) > float(h4_ema30[ih4])
            and float(h1_macd[ih1]) > 0.0
        )
        if not regime:
            continue

        common = {
            "direction": "LONG",
            "decision_time": decision.strftime(TIME_FORMAT),
            "entry_time": decision.strftime(TIME_FORMAT),
            "scheduled_exit_time": (decision + HORIZON).strftime(TIME_FORMAT),
            "m15_trigger_source_open": m15[i].time.strftime(TIME_FORMAT),
            "h1_source_open": h1[ih1].time.strftime(TIME_FORMAT),
            "h4_source_open": h4[ih4].time.strftime(TIME_FORMAT),
            "d1_source_open": d1[id1].time.strftime(TIME_FORMAT),
            "h1_macd_line_bps": float(h1_macd[ih1]),
            "h1_atr_pct100": float(atrp),
        }

        prior4_high = max(float(m15[j].high) for j in range(i - 4, i))
        if float(m15[i].close) > prior4_high:
            family = "HBR1_LONG_HIGH_ATR_1H_BREAKOUT"
            output[family].append({
                **common,
                "family": family,
                "candidate_id": f"HBR1_{decision.strftime('%Y%m%d_%H%M%S')}",
                "trigger_current_close": float(m15[i].close),
                "trigger_prior4_high": prior4_high,
            })

        if (
            float(m15[i - 1].close) <= float(m15_ema20[i - 1])
            and float(m15[i].close) > float(m15_ema20[i])
            and float(m15_ema20[i]) > float(m15_ema30[i])
        ):
            family = "HER1_LONG_HIGH_ATR_EMA20_RECLAIM"
            output[family].append({
                **common,
                "family": family,
                "candidate_id": f"HER1_{decision.strftime('%Y%m%d_%H%M%S')}",
                "trigger_previous_close": float(m15[i - 1].close),
                "trigger_previous_ema20": float(m15_ema20[i - 1]),
                "trigger_current_close": float(m15[i].close),
                "trigger_current_ema20": float(m15_ema20[i]),
                "trigger_current_ema30": float(m15_ema30[i]),
            })

        previous_rci = m15_rci9[i - 1]
        current_rci = m15_rci9[i]
        if (
            previous_rci is not None
            and current_rci is not None
            and float(previous_rci) <= -80.0
            and float(current_rci) > float(previous_rci)
        ):
            family = "HRC1_LONG_HIGH_ATR_RCI9_OVERSOLD_TURN"
            output[family].append({
                **common,
                "family": family,
                "candidate_id": f"HRC1_{decision.strftime('%Y%m%d_%H%M%S')}",
                "trigger_previous_rci9": float(previous_rci),
                "trigger_current_rci9": float(current_rci),
            })

    return output


def directional_bps(entry_ask: float, exit_bid: float) -> float:
    return (exit_bid - entry_ask) / max(abs(entry_ask), 1e-12) * 10000.0


def build_ledger(
    family: str,
    candidates: list[dict[str, Any]],
    m1: list[frozen.Bar],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_time = {bar.time: bar for bar in m1}
    latest = m1[-1].time
    active_until: datetime | None = None
    active_id: str | None = None
    trades: list[dict[str, Any]] = []
    skips: list[dict[str, Any]] = []
    sequence = 0

    for row in sorted(candidates, key=lambda item: item["decision_time"]):
        decision = datetime.strptime(str(row["decision_time"]), TIME_FORMAT)
        if active_until is not None and decision < active_until:
            skips.append({
                "family": family,
                "active_trade_id": active_id,
                "skipped_candidate_id": row["candidate_id"],
                "skipped_decision_time": row["decision_time"],
                "reason": "ONE_POSITION_ACTIVE",
            })
            continue

        entry_bar = by_time.get(decision)
        if entry_bar is None:
            trades.append({
                **row,
                "trade_id": None,
                "status": "ENTRY_DATA_GAP",
                "actual_return_bps": None,
                "fixed0p20_return_bps": None,
            })
            continue

        exit_time = decision + HORIZON
        exit_bar = by_time.get(exit_time)
        sequence += 1
        trade_id = f"{family}_T{sequence:06d}"
        active_until = exit_time
        active_id = trade_id

        if exit_bar is None:
            status = "EXIT_DATA_GAP" if latest >= exit_time else "OPEN"
            trades.append({
                **row,
                "trade_id": trade_id,
                "status": status,
                "entry_spread_points": int(entry_bar.spread),
                "actual_return_bps": None,
                "fixed0p20_return_bps": None,
            })
            continue

        actual_entry_ask = float(entry_bar.open) + int(entry_bar.spread) * POINT
        fixed_entry_ask = float(entry_bar.open) + FIXED_SPREAD_USD
        exit_bid = float(exit_bar.open)
        trades.append({
            **row,
            "trade_id": trade_id,
            "status": "RESOLVED",
            "entry_bid": float(entry_bar.open),
            "entry_spread_points": int(entry_bar.spread),
            "actual_entry_ask": actual_entry_ask,
            "fixed0p20_entry_ask": fixed_entry_ask,
            "exit_bid": exit_bid,
            "actual_return_bps": directional_bps(actual_entry_ask, exit_bid),
            "fixed0p20_return_bps": directional_bps(fixed_entry_ask, exit_bid),
        })

    return trades, skips


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
    positives = [value for value in values if value > 0]
    negatives = [value for value in values if value < 0]
    gross_win = sum(positives)
    gross_loss = abs(sum(negatives))
    pf = None if gross_loss == 0 else gross_win / gross_loss
    avg_win = sum(positives) / len(positives) if positives else None
    avg_loss = sum(negatives) / len(negatives) if negatives else None
    equity = peak = max_dd = 0.0
    streak = max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "count": len(values),
        "win_rate": sum(value > 0 for value in values) / len(values),
        "profit_factor": pf,
        "net_bps": sum(values),
        "average_win_bps": avg_win,
        "average_loss_bps": avg_loss,
        "payoff_ratio": None if avg_win is None or avg_loss is None else avg_win / abs(avg_loss),
        "max_drawdown_bps": max_dd,
        "max_losing_streak": max_streak,
    }


def split_name(year: int) -> str | None:
    if year in (2023, 2024):
        return "TRAIN_2023_2024"
    if year == 2025:
        return "VALIDATION_2025"
    if year == 2026:
        return "TEST_2026"
    return None


def metric_blocks(trades: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = [
        row for row in trades
        if row.get("status") == "RESOLVED" and row.get("actual_return_bps") is not None
    ]
    groups: dict[str, list[dict[str, Any]]] = {
        "TRAIN_2023_2024": [],
        "VALIDATION_2025": [],
        "TEST_2026": [],
        "ALL": resolved,
    }
    for row in resolved:
        year = datetime.strptime(str(row["entry_time"]), TIME_FORMAT).year
        name = split_name(year)
        if name:
            groups[name].append(row)

    output: dict[str, Any] = {}
    for name, rows in groups.items():
        actual = [float(row["actual_return_bps"]) for row in rows]
        fixed = [float(row["fixed0p20_return_bps"]) for row in rows]
        output[name] = {
            "actual": metrics(actual),
            "fixed0p20": metrics(fixed),
            "actual_plus1bps_cost": metrics([value - 1.0 for value in actual]),
            "actual_plus2bps_cost": metrics([value - 2.0 for value in actual]),
        }
    return output


def pf_value(block: dict[str, Any]) -> float:
    value = block.get("profit_factor")
    if value is None:
        return float("inf") if int(block.get("count", 0)) > 0 else 0.0
    return float(value)


def classify(blocks: dict[str, Any], tiers: dict[str, Any]) -> str:
    split_names = ("TRAIN_2023_2024", "VALIDATION_2025", "TEST_2026")
    counts = [int(blocks[name]["actual"]["count"]) for name in split_names]
    if min(counts) < 20:
        return "INSUFFICIENT_DENSITY"

    split_pfs = [pf_value(blocks[name]["actual"]) for name in split_names]
    split_nets = [float(blocks[name]["actual"]["net_bps"]) for name in split_names]
    all_pf = pf_value(blocks["ALL"]["actual"])
    fixed_pf = pf_value(blocks["ALL"]["fixed0p20"])
    plus2_pf = pf_value(blocks["ALL"]["actual_plus2bps_cost"])

    if min(split_pfs) <= 1.0 or fixed_pf <= 1.0 or plus2_pf <= 1.0:
        return "REJECT"

    strong = tiers["STRONG_RESEARCH_SCREEN"]
    if (
        min(split_pfs) >= float(strong["minimum_pf_each_split"])
        and all_pf >= float(strong["minimum_all_pf"])
        and fixed_pf >= float(strong["minimum_fixed0p20_all_pf"])
        and plus2_pf >= float(strong["minimum_extra2bps_all_pf"])
        and min(split_nets) > 0.0
    ):
        return "STRONG_RESEARCH_SCREEN"

    robust = tiers["ROBUST_RESEARCH_SCREEN"]
    if (
        min(split_pfs) >= float(robust["minimum_pf_each_split"])
        and all_pf >= float(robust["minimum_all_pf"])
        and fixed_pf >= float(robust["minimum_fixed0p20_all_pf"])
        and plus2_pf >= float(robust["minimum_extra2bps_all_pf"])
        and min(split_nets) > 0.0
    ):
        return "ROBUST_RESEARCH_SCREEN"

    return "WEAK_OR_INCONSISTENT"


def flatten_metrics(family: str, blocks: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split, variants in blocks.items():
        for variant, block in variants.items():
            rows.append({"family": family, "split": split, "cost_variant": variant, **block})
    return rows


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    output_root = local_root / "outputs" / "M10W21"
    try:
        contract = load_json(CONTRACT)
        if (
            contract.get("stage") != "M10W20_HIGH_ATR_BULLISH_ENTRY_HYPOTHESIS_PREREGISTRATION_AUDIT_ONLY"
            or contract.get("status") != "HYPOTHESES_FROZEN_BEFORE_ENTRY_OUTCOME_EVALUATION"
        ):
            raise RuntimeError("unexpected M10W20 preregistration contract")
        if tuple(contract.get("frozen_families", {}).keys()) != FAMILIES:
            raise RuntimeError("M10W20 frozen family set/order mismatch")

        data_root = resolve_data_root(local_root)
        if not data_root.is_dir():
            raise RuntimeError(f"frozen GOLD data root unavailable: {data_root}")
        bars, hashes = verify_and_load(data_root)
        candidates_by_family = build_candidates(bars)

        all_candidates: list[dict[str, Any]] = []
        all_trades: list[dict[str, Any]] = []
        all_skips: list[dict[str, Any]] = []
        metric_rows: list[dict[str, Any]] = []
        family_results: dict[str, Any] = {}
        tiers = contract["frozen_evaluation"]["screening_tiers"]

        for family in FAMILIES:
            candidates = candidates_by_family[family]
            trades, skips = build_ledger(family, candidates, bars["M1"])
            blocks = metric_blocks(trades)
            classification = classify(blocks, tiers)
            all_candidates.extend(candidates)
            all_trades.extend(trades)
            all_skips.extend(skips)
            metric_rows.extend(flatten_metrics(family, blocks))

            candidate_year_counts: dict[str, int] = defaultdict(int)
            for row in candidates:
                year = datetime.strptime(str(row["decision_time"]), TIME_FORMAT).year
                candidate_year_counts[str(year)] += 1
            accepted = [row for row in trades if row.get("trade_id")]
            resolved = [row for row in accepted if row.get("status") == "RESOLVED"]
            family_results[family] = {
                "classification": classification,
                "candidate_count": len(candidates),
                "candidate_year_counts": dict(sorted(candidate_year_counts.items())),
                "accepted_count": len(accepted),
                "resolved_count": len(resolved),
                "open_count": sum(row.get("status") == "OPEN" for row in accepted),
                "entry_data_gap_count": sum(row.get("status") == "ENTRY_DATA_GAP" for row in trades),
                "exit_data_gap_count": sum(row.get("status") == "EXIT_DATA_GAP" for row in accepted),
                "overlap_skip_count": len(skips),
                "metrics": blocks,
                "historical_advance_eligibility": classification in ("ROBUST_RESEARCH_SCREEN", "STRONG_RESEARCH_SCREEN"),
                "fresh_shadow_required_before_support": True,
            }

        advancing = [
            family for family in FAMILIES
            if family_results[family]["historical_advance_eligibility"]
        ]
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_PREREGISTERED_RESEARCH_EXPOSED_SCREEN",
            "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scope": "XAUUSD_GOLD_ONLY",
            "preregistration_contract": str(CONTRACT.relative_to(ROOT)),
            "frozen_data_root": str(data_root),
            "verified_sha256": hashes,
            "target_regime": "D1 bullish stack + H4 EMA20>EMA30 + H1 MACD line>0 + H1 ATR percentile100>=0.67",
            "family_results": family_results,
            "historically_screened_advancing_families": advancing,
            "interpretation": {
                "regime_bucket_was_selected_after_M10W17_outcomes": True,
                "historical_results_are_clean_validation": False,
                "historical_pass_is_final_support": False,
                "formula_or_threshold_change_after_results": False,
                "M10W19_modified": False,
                "next_if_any_advance": "Freeze the passing family/families unchanged in a brand-new common-start fresh prospective multi-arm shadow. Do not select by historical PF ranking.",
                "next_if_none_advance": "Do not tune these three triggers. Treat the tested simple entry-timing set as failed and move to genuinely new causal information rather than parameter variants.",
            },
            "guardrails": contract["safety"],
        }

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10W21 evaluates exactly the three M10W20 preregistered LONG entry hypotheses inside the research-exposed M10W17 HIGH-ATR bullish opportunity bucket. No post-result formula, threshold, session, horizon, or combination tuning is allowed. Any historical pass still requires a new independent fresh prospective shadow.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_candidate_ledger.csv", sorted(all_candidates, key=lambda row: (row["family"], row["decision_time"])))
        write_csv(archive / "03_trade_ledger.csv", sorted(all_trades, key=lambda row: (row["family"], row["decision_time"])))
        write_csv(archive / "04_overlap_skip_ledger.csv", sorted(all_skips, key=lambda row: (row["family"], row["skipped_decision_time"])))
        write_csv(archive / "05_metrics_by_family_split.csv", metric_rows)
        (archive / "06_data_quality.json").write_text(json.dumps({
            "scope": "XAUUSD_GOLD_ONLY",
            "verified_sha256": hashes,
            "closed_rows_contract": True,
            "time_basis": "MT5_SERVER_TIME",
            "exact_m1_entry_only": True,
            "exact_m1_exit_only": True,
            "nearest_m1_fallback": False,
            "horizon_minutes": 240,
            "one_position_per_family": True,
            "actual_spread": True,
            "fixed0p20": True,
            "extra_cost_bps": [1.0, 2.0],
            "historical_backfill_into_existing_forward": False,
            "M10W19_modified": False,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "07_audit.log").write_text("\n".join([
            "status=PASS_PREREGISTERED_RESEARCH_EXPOSED_SCREEN",
            "families=" + ",".join(FAMILIES),
            "target_regime=D1_BULLISH|H4_POSITIVE|H1_MACD_POSITIVE|ATR_HIGH_GE_0P67",
            "formula_change_after_results=false",
            "threshold_change_after_results=false",
            "session_filter_search=false",
            "horizon_change=false",
            "trigger_combination_search=false",
            "historical_results_clean_validation=false",
            "fresh_shadow_required_before_support=true",
            "M10W19_modified=false",
            "discord_send=false",
            "mt5_order=false",
            "live_ready=false",
            "final_signal=false",
            "",
        ]), encoding="utf-8")

        latest = output_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = [
            "00_READ_ME_FIRST.txt",
            "01_summary.json",
            "02_candidate_ledger.csv",
            "03_trade_ledger.csv",
            "04_overlap_skip_ledger.csv",
            "05_metrics_by_family_split.csv",
            "06_data_quality.json",
            "07_audit.log",
        ]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            for name in names:
                handle.write(latest / name, arcname=name)

        print("[M10W21 PASS] preregistered high-ATR bullish entry screen complete")
        for family in FAMILIES:
            result = family_results[family]
            all_metrics = result["metrics"]["ALL"]["actual"]
            print(
                f"  {family}: class={result['classification']} resolved={result['resolved_count']} "
                f"PF={all_metrics['profit_factor']} net={all_metrics['net_bps']}"
            )
        print(f"[ADVANCE-ELIGIBLE] {advancing}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10W21 BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] Existing forward monitors, starts, BLC1, M10W19 and all thresholds were not modified.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
