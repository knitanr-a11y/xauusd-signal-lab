from __future__ import annotations

import bisect
import csv
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
M9P_PYTHON = THIS.parents[2] / "m9p" / "python"
if str(M9P_PYTHON) not in sys.path:
    sys.path.insert(0, str(M9P_PYTHON))
import run_gold_dynamic_core_reproduction_audit as m9p

STAGE = "M9V_GOLD_MULTI_TIMEFRAME_FRESH_PROSPECTIVE_SHADOW"
CONTRACT_STAGE = STAGE
TIME_FORMAT = m9p.TIME_FORMAT
LONG_EXIT_RCI9 = m9p.LONG_EXIT_RCI9
SHORT_EXIT_RCI9 = m9p.SHORT_EXIT_RCI9
TURN_LOOKBACK = m9p.TURN_LOOKBACK
TIMEFRAME_SECONDS = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600, "H4": 14400, "D1": 86400}
BRANCH_PRIORITY = {"S1_M5": 1, "S2_M15": 2, "S3_H1": 3, "S4_H4": 4}
ARM_BRANCHES = {
    "V0_M15_ONLY": {"S2_M15"},
    "V1_M15_PLUS_H1": {"S2_M15", "S3_H1"},
    "V2_ALL_TIMEFRAMES": {"S1_M5", "S2_M15", "S3_H1", "S4_H4"},
}


class M9VContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class Episode:
    timeframe: str
    direction: str
    primary_time: datetime
    signal_bid: float
    exit_time: datetime | None
    primary_post_start: bool


def parse_time(text: str) -> datetime:
    return datetime.strptime(text, TIME_FORMAT)


def fmt_time(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise M9VContractError(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise M9VContractError(f"JSON is not object: {path}")
    return value


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prefix_fingerprint(path: Path, cutoff: datetime) -> dict[str, Any]:
    digest = hashlib.sha256()
    count = 0
    first: datetime | None = None
    last: datetime | None = None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != m9p.HEADER:
            raise M9VContractError(f"unexpected header: {path.name}")
        for row in reader:
            current = parse_time(row["time"])
            if current > cutoff:
                break
            if first is None:
                first = current
            last = current
            count += 1
            canonical = "|".join(str(row[name]).strip() for name in m9p.HEADER).encode("utf-8")
            digest.update(canonical + b"\n")
    if count == 0 or first is None or last is None:
        raise M9VContractError(f"no prefix rows at/before start in {path.name}")
    return {
        "row_count": count,
        "first_server_open": fmt_time(first),
        "last_server_open": fmt_time(last),
        "sha256": digest.hexdigest(),
    }


def tail_snapshot(path: Path) -> dict[str, Any]:
    count = 0
    first: datetime | None = None
    last: datetime | None = None
    previous: datetime | None = None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != m9p.HEADER:
            raise M9VContractError(f"unexpected header: {path.name}")
        for row in reader:
            current = parse_time(row["time"])
            if previous is not None and current <= previous:
                raise M9VContractError(f"non-ascending timestamp in {path.name}: {row['time']}")
            if first is None:
                first = current
            previous = current
            last = current
            count += 1
    if count == 0 or first is None or last is None:
        raise M9VContractError(f"empty live CSV: {path.name}")
    return {
        "row_count": count,
        "first_server_open": fmt_time(first),
        "last_server_open": fmt_time(last),
        "byte_size": path.stat().st_size,
    }


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("project") != "MOCHIPOYO_ALERT_RESEARCH" or contract.get("stage") != CONTRACT_STAGE:
        raise M9VContractError("unexpected M9V contract")
    if str(contract.get("status")) != "DESIGN_FROZEN_NOT_STARTED":
        raise M9VContractError("M9V contract status is not frozen design")
    data = contract.get("data", {})
    if data.get("ticker") != "XAUUSD" or data.get("time_basis") != "MT5_SERVER_TIME":
        raise M9VContractError("unsafe M9V data contract")
    if data.get("historical_backfill") is not False:
        raise M9VContractError("historical backfill must be false")
    safety = contract.get("safety", {})
    expected_false = (
        "discord_send", "mt5_order", "live_ready", "final_signal", "entry_gate_enabled",
        "m7c_formula_changed", "m7c_threshold_changed", "m8c_reset",
        "m7c_runtime_manifest_reset", "m8c_prospective_start_reset",
    )
    if safety.get("audit_only") is not True:
        raise M9VContractError("audit_only must be true")
    for key in expected_false:
        if safety.get(key) is not False:
            raise M9VContractError(f"unsafe M9V flag: {key}")
    if set(contract.get("arms", {})) != set(ARM_BRANCHES):
        raise M9VContractError("M9V arms mismatch")


def validate_runtime_manifest(runtime: dict[str, Any], contract: dict[str, Any], contract_sha256: str) -> None:
    validate_contract(contract)
    if runtime.get("stage") != STAGE or runtime.get("runtime_status") != "FROZEN_FRESH_START":
        raise M9VContractError("unexpected M9V runtime manifest")
    if runtime.get("contract_sha256") != contract_sha256:
        raise M9VContractError("M9V contract changed after runtime freeze")
    if runtime.get("historical_backfill_allowed") is not False:
        raise M9VContractError("runtime backfill flag unsafe")
    if runtime.get("prospective_start_server_time") is None:
        raise M9VContractError("missing M9V prospective start")
    if runtime.get("reset_allowed") is not False:
        raise M9VContractError("runtime reset flag unsafe")


def ema_bps(bars: list[m9p.Bar], fast_period: int = 6, slow_period: int = 13) -> list[float]:
    closes = [bar.close for bar in bars]
    fast = m9p.ema(closes, fast_period)
    slow = m9p.ema(closes, slow_period)
    return [(f - s) / abs(close) * 10000.0 for f, s, close in zip(fast, slow, closes)]


def close_times(bars: list[m9p.Bar], timeframe: str) -> list[datetime]:
    return [bar.time + timedelta(seconds=TIMEFRAME_SECONDS[timeframe]) for bar in bars]


def selected_closed_index(times: list[datetime], decision: datetime) -> int:
    return bisect.bisect_right(times, decision) - 1


def quantile_window(values: list[float | None], index: int, window: int, q: float) -> float | None:
    start = index - window + 1
    if start < 0:
        return None
    selected = values[start:index + 1]
    if len(selected) != window or any(value is None or not math.isfinite(float(value)) for value in selected):
        return None
    ordered = sorted(float(value) for value in selected if value is not None)
    return m9p.quantile_sorted(ordered, q)


def replay_episodes(bars: list[m9p.Bar], timeframe: str, start: datetime) -> tuple[list[Episode], dict[str, Any]]:
    closes = [bar.close for bar in bars]
    rci9 = m9p.rci_series(closes, 9)
    ema20 = m9p.ema(closes, 20)
    ema30 = m9p.ema(closes, 30)
    ema40 = m9p.ema(closes, 40)

    state = "IDLE"
    open_direction: str | None = None
    open_time: datetime | None = None
    signal_bid: float | None = None
    episodes: list[Episode] = []
    pre_start_active_seen = False

    for current_index in range(50, len(bars)):
        selected = current_index - 1
        current_rci = rci9[selected]
        previous = rci9[selected - 1]
        previous2 = rci9[selected - 2]
        if current_rci is None or previous is None or previous2 is None:
            continue
        decision = bars[current_index].time
        turn_up = current_rci > previous and previous <= previous2
        turn_down = current_rci < previous and previous >= previous2
        bullish = ema20[selected] > ema30[selected] > ema40[selected]
        bearish = ema20[selected] < ema30[selected] < ema40[selected]

        if state == "IDLE":
            if turn_up and bullish:
                state = "ACTIVE_LONG"
                open_direction = "LONG"
                open_time = decision
                signal_bid = bars[current_index].open
                if decision <= start:
                    pre_start_active_seen = True
            elif turn_down and bearish:
                state = "ACTIVE_SHORT"
                open_direction = "SHORT"
                open_time = decision
                signal_bid = bars[current_index].open
                if decision <= start:
                    pre_start_active_seen = True
        elif state == "ACTIVE_LONG" and current_rci >= LONG_EXIT_RCI9:
            if open_time is None or signal_bid is None or open_direction != "LONG":
                raise M9VContractError(f"{timeframe} LONG exit without primary")
            episodes.append(Episode(timeframe, "LONG", open_time, signal_bid, decision, open_time > start))
            state = "IDLE"
            open_direction = None
            open_time = None
            signal_bid = None
        elif state == "ACTIVE_SHORT" and current_rci <= SHORT_EXIT_RCI9:
            if open_time is None or signal_bid is None or open_direction != "SHORT":
                raise M9VContractError(f"{timeframe} SHORT exit without primary")
            episodes.append(Episode(timeframe, "SHORT", open_time, signal_bid, decision, open_time > start))
            state = "IDLE"
            open_direction = None
            open_time = None
            signal_bid = None

    if state in ("ACTIVE_LONG", "ACTIVE_SHORT"):
        if open_time is None or signal_bid is None or open_direction is None:
            raise M9VContractError(f"{timeframe} active state without open primary")
        episodes.append(Episode(timeframe, open_direction, open_time, signal_bid, None, open_time > start))

    audit_state = "IDLE"
    audit_open: datetime | None = None
    for current_index in range(50, len(bars)):
        decision = bars[current_index].time
        if decision > start:
            break
        selected = current_index - 1
        current_rci = rci9[selected]
        previous = rci9[selected - 1]
        previous2 = rci9[selected - 2]
        if current_rci is None or previous is None or previous2 is None:
            continue
        turn_up = current_rci > previous and previous <= previous2
        turn_down = current_rci < previous and previous >= previous2
        bullish = ema20[selected] > ema30[selected] > ema40[selected]
        bearish = ema20[selected] < ema30[selected] < ema40[selected]
        if audit_state == "IDLE":
            if turn_up and bullish:
                audit_state, audit_open = "ACTIVE_LONG", decision
            elif turn_down and bearish:
                audit_state, audit_open = "ACTIVE_SHORT", decision
        elif audit_state == "ACTIVE_LONG" and current_rci >= LONG_EXIT_RCI9:
            audit_state, audit_open = "IDLE", None
        elif audit_state == "ACTIVE_SHORT" and current_rci <= SHORT_EXIT_RCI9:
            audit_state, audit_open = "IDLE", None

    return episodes, {
        "timeframe": timeframe,
        "state_at_start": audit_state,
        "inherited_active_primary_time": None if audit_open is None else fmt_time(audit_open),
        "pre_start_active_seen": pre_start_active_seen,
        "eligible_post_start_primary_count": sum(ep.primary_post_start for ep in episodes),
        "all_episode_count": len(episodes),
    }


def first_turn_for_episode(episode: Episode, m1: list[m9p.Bar], m1_index: dict[datetime, int], point: float) -> dict[str, Any] | None:
    if episode.direction != "LONG" or not episode.primary_post_start:
        return None
    if episode.primary_time not in m1_index:
        return None
    entry_index = m1_index[episode.primary_time]
    if episode.exit_time is not None and episode.exit_time in m1_index:
        end_exclusive = m1_index[episode.exit_time]
    else:
        end_exclusive = len(m1)
    if end_exclusive <= entry_index + 2:
        return None

    for current_index in range(entry_index + 1, end_exclusive):
        turn_index = current_index + 1
        if turn_index >= end_exclusive or turn_index >= len(m1):
            break
        history = m1[max(0, current_index - TURN_LOOKBACK):current_index]
        if len(history) < TURN_LOOKBACK:
            continue
        previous = m1[current_index - 1]
        current = m1[current_index]
        candidate = previous.low <= min(bar.low for bar in history) and previous.low < episode.signal_bid and current.close > previous.close
        if not candidate:
            continue
        turn_bar = m1[turn_index]
        entry_exec = turn_bar.open + turn_bar.spread * point
        exit_exec: float | None = None
        return_bps: float | None = None
        if episode.exit_time is not None and episode.exit_time in m1_index:
            exit_bar = m1[m1_index[episode.exit_time]]
            exit_exec = exit_bar.open
            return_bps = (exit_exec - entry_exec) / abs(entry_exec) * 10000.0
        return {
            "signal_timeframe": episode.timeframe,
            "proxy_primary_time": fmt_time(episode.primary_time),
            "turn_entry_time": fmt_time(turn_bar.time),
            "native_exit_time": None if episode.exit_time is None else fmt_time(episode.exit_time),
            "entry_exec": entry_exec,
            "exit_exec": exit_exec,
            "return_bps": return_bps,
            "status": "RESOLVED" if return_bps is not None else "OPEN",
        }
    return None


def build_candidate_features(row: dict[str, Any], bars: dict[str, list[m9p.Bar]], closes: dict[str, list[datetime]], ratio20_m5: list[float | None], macd: dict[str, list[float]], rci9: dict[str, list[float | None]], d1_ema: tuple[list[float], list[float], list[float]]) -> tuple[str | None, dict[str, Any]]:
    decision = parse_time(str(row["turn_entry_time"]))
    timeframe = str(row["signal_timeframe"])
    indices = {tf: selected_closed_index(closes[tf], decision) for tf in ("M5", "M15", "H1", "H4", "D1")}
    details: dict[str, Any] = {"decision_server_time": row["turn_entry_time"], "selected_indices": indices}

    if timeframe == "M5":
        i5, i15, ih1 = indices["M5"], indices["M15"], indices["H1"]
        if min(i5, i15, ih1) < 0:
            return None, details
        q_m5_volume = quantile_window(ratio20_m5, i5, 200, 0.50)
        q_m5_macd = quantile_window(macd["M5"], i5, 200, 0.75)
        q_m15 = quantile_window(macd["M15"], i15, 100, 0.75)
        q_h1_macd = quantile_window(macd["H1"], ih1, 100, 0.50)
        q_h1_rci = quantile_window(rci9["H1"], ih1, 100, 0.50)
        own_core = (q_m5_volume is not None and ratio20_m5[i5] is not None and float(ratio20_m5[i5]) <= q_m5_volume) or (q_m5_macd is not None and macd["M5"][i5] >= q_m5_macd)
        passed = own_core and q_m15 is not None and q_h1_macd is not None and q_h1_rci is not None and macd["M15"][i15] >= q_m15 and macd["H1"][ih1] >= q_h1_macd and rci9["H1"][ih1] is not None and float(rci9["H1"][ih1]) >= q_h1_rci
        details.update({"own_core": own_core, "m15_macd_threshold": q_m15, "h1_macd_threshold": q_h1_macd, "h1_rci9_threshold": q_h1_rci})
        return ("S1_M5" if passed else None), details

    if timeframe == "M15":
        i5, i15 = indices["M5"], indices["M15"]
        if min(i5, i15) < 0:
            return None, details
        q1 = quantile_window(ratio20_m5, i5, 200, 0.50)
        q2 = quantile_window(macd["M15"], i15, 200, 0.75)
        n1 = q1 is not None and ratio20_m5[i5] is not None and float(ratio20_m5[i5]) <= q1
        n2 = q2 is not None and macd["M15"][i15] >= q2
        details.update({"N1": n1, "N2": n2, "N1_threshold": q1, "N2_threshold": q2})
        return ("S2_M15" if (n1 or n2) else None), details

    if timeframe == "H1":
        ih4, id1 = indices["H4"], indices["D1"]
        if min(ih4, id1) < 0:
            return None, details
        q_h4 = quantile_window(macd["H4"], ih4, 100, 0.75)
        q_d1 = quantile_window(macd["D1"], id1, 100, 0.50)
        passed = q_h4 is not None and q_d1 is not None and macd["H4"][ih4] >= q_h4 and macd["D1"][id1] >= q_d1
        details.update({"h4_macd_threshold": q_h4, "d1_macd_threshold": q_d1})
        return ("S3_H1" if passed else None), details

    if timeframe == "H4":
        id1 = indices["D1"]
        if id1 < 0:
            return None, details
        q_d1 = quantile_window(rci9["D1"], id1, 100, 0.50)
        e20, e30, e40 = d1_ema
        passed = q_d1 is not None and rci9["D1"][id1] is not None and float(rci9["D1"][id1]) >= q_d1 and e20[id1] > e30[id1] > e40[id1]
        details.update({"d1_rci9_threshold": q_d1, "d1_bullish_stack": e20[id1] > e30[id1] > e40[id1]})
        return ("S4_H4" if passed else None), details

    raise M9VContractError(f"unsupported signal timeframe: {timeframe}")


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = [row for row in rows if row.get("return_bps") is not None]
    if not resolved:
        return {"resolved_count": 0, "open_count": len(rows), "win_rate": None, "profit_factor_bps": None, "net_bps": 0.0, "max_drawdown_bps": 0.0, "max_losing_streak": 0, "average_win_bps": None, "average_loss_bps": None, "tail_le_minus_100_fraction": None}
    base = m9p.metrics(resolved)
    return {"resolved_count": len(resolved), "open_count": len(rows) - len(resolved), **base}


def build_arm(name: str, candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eligible = ARM_BRANCHES[name]
    events = [row for row in candidates if str(row["branch"]) in eligible]
    events.sort(key=lambda row: (parse_time(str(row["turn_entry_time"])), -BRANCH_PRIORITY[str(row["branch"])]))
    accepted: list[dict[str, Any]] = []
    confirmations: list[dict[str, Any]] = []
    active_until: datetime | None = None
    active_id: str | None = None
    active_open = False

    for row in events:
        entry = parse_time(str(row["turn_entry_time"]))
        if active_open:
            confirmations.append({"arm": name, "active_trade_id": active_id, "confirmation_branch": row["branch"], "confirmation_turn_entry_time": row["turn_entry_time"], "confirmation_source_candidate_id": row["candidate_id"], "relation": "DURING_OPEN_TRADE"})
            continue
        if active_until is not None and entry < active_until:
            confirmations.append({"arm": name, "active_trade_id": active_id, "confirmation_branch": row["branch"], "confirmation_turn_entry_time": row["turn_entry_time"], "confirmation_source_candidate_id": row["candidate_id"], "relation": "DURING_RESOLVED_TRADE_HOLDING_WINDOW"})
            continue
        accepted_row = dict(row)
        accepted_row["arm"] = name
        accepted_row["arm_trade_id"] = f"{name}_T{len(accepted)+1:06d}"
        accepted.append(accepted_row)
        active_id = str(accepted_row["arm_trade_id"])
        if row.get("native_exit_time") is None:
            active_open = True
            active_until = None
        else:
            active_open = False
            active_until = parse_time(str(row["native_exit_time"]))
    return accepted, confirmations


def audit(*, data_root: Path, contract: dict[str, Any], runtime: dict[str, Any], point: float) -> dict[str, Any]:
    contract_sha = sha256_bytes(json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    validate_runtime_manifest(runtime, contract, contract_sha)
    start = parse_time(str(runtime["prospective_start_server_time"]))
    file_map = contract["data"]["live_file_map"]

    paths: dict[str, Path] = {}
    for timeframe, filename in file_map.items():
        path = data_root / str(filename)
        if not path.is_file():
            raise M9VContractError(f"missing live GOLD CSV: {path}")
        paths[timeframe] = path
        frozen_prefix = runtime["prefix_fingerprints"].get(timeframe)
        if not isinstance(frozen_prefix, dict):
            raise M9VContractError(f"missing frozen prefix fingerprint: {timeframe}")
        current_prefix = prefix_fingerprint(path, start)
        if current_prefix != frozen_prefix:
            raise M9VContractError(f"historical prefix changed after M9V start: {timeframe}")

    bars = {timeframe: m9p.load_bars(path) for timeframe, path in paths.items()}
    m1 = bars["M1"]
    m1_index = {bar.time: idx for idx, bar in enumerate(m1)}
    if len(m1_index) != len(m1):
        raise M9VContractError("duplicate M1 timestamp")

    episodes_by_tf: dict[str, list[Episode]] = {}
    bootstrap_audit: dict[str, Any] = {}
    for timeframe in ("M5", "M15", "H1", "H4"):
        episodes, audit_row = replay_episodes(bars[timeframe], timeframe, start)
        episodes_by_tf[timeframe] = episodes
        bootstrap_audit[timeframe] = audit_row
        frozen_state = runtime["state_at_start"].get(timeframe)
        if not isinstance(frozen_state, dict):
            raise M9VContractError(f"missing frozen state: {timeframe}")
        if audit_row["state_at_start"] != frozen_state.get("state_at_start") or audit_row["inherited_active_primary_time"] != frozen_state.get("inherited_active_primary_time"):
            raise M9VContractError(f"state-at-start changed after freeze: {timeframe}")

    turns: list[dict[str, Any]] = []
    for timeframe in ("M5", "M15", "H1", "H4"):
        for episode in episodes_by_tf[timeframe]:
            row = first_turn_for_episode(episode, m1, m1_index, point)
            if row is not None:
                turns.append(row)
    turns.sort(key=lambda row: (row["turn_entry_time"], row["signal_timeframe"]))

    closes = {timeframe: close_times(bars[timeframe], timeframe) for timeframe in ("M5", "M15", "H1", "H4", "D1")}
    ratio20_m5 = m9p.m5_ratio20(bars["M5"])
    macd = {timeframe: ema_bps(bars[timeframe]) for timeframe in ("M5", "M15", "H1", "H4", "D1")}
    rci9 = {timeframe: m9p.rci_series([bar.close for bar in bars[timeframe]], 9) for timeframe in ("H1", "D1")}
    d1_closes = [bar.close for bar in bars["D1"]]
    d1_ema = (m9p.ema(d1_closes, 20), m9p.ema(d1_closes, 30), m9p.ema(d1_closes, 40))

    candidates: list[dict[str, Any]] = []
    rejected_turns: list[dict[str, Any]] = []
    for row in turns:
        branch, details = build_candidate_features(row, bars, closes, ratio20_m5, macd, rci9, d1_ema)
        if branch is None:
            rejected_turns.append({**row, "branch": "NONE", "feature_details": json.dumps(details, ensure_ascii=False, sort_keys=True)})
            continue
        candidate = {**row, "branch": branch, "feature_details": json.dumps(details, ensure_ascii=False, sort_keys=True)}
        candidate["candidate_id"] = f"M9V_C{len(candidates)+1:06d}"
        candidates.append(candidate)

    arms: dict[str, list[dict[str, Any]]] = {}
    confirmations: list[dict[str, Any]] = []
    arm_metrics: dict[str, Any] = {}
    for name in ("V0_M15_ONLY", "V1_M15_PLUS_H1", "V2_ALL_TIMEFRAMES"):
        accepted, conf = build_arm(name, candidates)
        arms[name] = accepted
        confirmations.extend(conf)
        arm_metrics[name] = metrics(accepted)

    branch_metrics = {branch: metrics([row for row in candidates if row["branch"] == branch]) for branch in BRANCH_PRIORITY}
    latest_times = {timeframe: fmt_time(bars[timeframe][-1].time) for timeframe in bars}
    return {"start_server_time": fmt_time(start), "latest_server_open": latest_times, "bootstrap_audit": bootstrap_audit, "turns": turns, "rejected_turns": rejected_turns, "candidates": candidates, "branch_metrics": branch_metrics, "arms": arms, "arm_metrics": arm_metrics, "confirmations": confirmations}
