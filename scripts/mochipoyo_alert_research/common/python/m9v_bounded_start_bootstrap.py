from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from typing import Any, Callable

import bounded_csv_source_adapter as adapter
import run_bounded_adapter_loop as runner


ALLOWED_FROZEN_STATES = {"IDLE", "ACTIVE_LONG", "ACTIVE_SHORT"}


def replay_from_frozen_start(
    legacy: Any,
    bars: list[Any],
    timeframe: str,
    start: Any,
    frozen_state: dict[str, Any],
) -> tuple[list[Any], dict[str, Any]]:
    """Replay only decisions after the immutable start from its frozen state.

    The bounded MT5 source may legitimately lose very old head rows after an MT5
    restart. Recomputing the whole pre-start state machine from the new bounded
    head is therefore invalid. The runtime's frozen state_at_start remains the
    authoritative bootstrap; retained journal rows are used only for indicator
    context and post-start decisions.
    """
    state = str(frozen_state.get("state_at_start", ""))
    inherited_text = frozen_state.get("inherited_active_primary_time")
    if state not in ALLOWED_FROZEN_STATES:
        raise legacy.M9VContractError(f"invalid frozen state-at-start for {timeframe}: {state}")
    if state == "IDLE" and inherited_text is not None:
        raise legacy.M9VContractError(
            f"IDLE frozen state has inherited primary time for {timeframe}: {inherited_text}"
        )
    if state != "IDLE" and not inherited_text:
        raise legacy.M9VContractError(f"active frozen state lacks inherited primary time: {timeframe}")

    closes = [bar.close for bar in bars]
    rci9 = legacy.m9p.rci_series(closes, 9)
    ema20 = legacy.m9p.ema(closes, 20)
    ema30 = legacy.m9p.ema(closes, 30)
    ema40 = legacy.m9p.ema(closes, 40)

    open_direction: str | None = None
    open_time: Any | None = None
    signal_bid: float | None = None
    inherited_active = state != "IDLE"
    if inherited_active:
        open_direction = "LONG" if state == "ACTIVE_LONG" else "SHORT"
        open_time = legacy.parse_time(str(inherited_text))
        by_time = {bar.time: bar for bar in bars}
        inherited_bar = by_time.get(open_time)
        # A pre-start inherited episode is never candidate-eligible. Its price is
        # retained only to satisfy the immutable Episode shape until its first
        # post-start exit; use the exact bar when still present, otherwise a safe
        # non-null placeholder that cannot enter candidate/payoff calculations.
        signal_bid = float(inherited_bar.open) if inherited_bar is not None else 0.0

    episodes: list[Any] = []
    for current_index in range(50, len(bars)):
        decision = bars[current_index].time
        if decision <= start:
            continue
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

        if state == "IDLE":
            if turn_up and bullish:
                state = "ACTIVE_LONG"
                open_direction = "LONG"
                open_time = decision
                signal_bid = float(bars[current_index].open)
            elif turn_down and bearish:
                state = "ACTIVE_SHORT"
                open_direction = "SHORT"
                open_time = decision
                signal_bid = float(bars[current_index].open)
        elif state == "ACTIVE_LONG" and current_rci >= legacy.LONG_EXIT_RCI9:
            if open_time is None or signal_bid is None or open_direction != "LONG":
                raise legacy.M9VContractError(f"{timeframe} LONG exit without frozen/post-start primary")
            episodes.append(
                legacy.Episode(timeframe, "LONG", open_time, signal_bid, decision, open_time > start)
            )
            state = "IDLE"
            open_direction = None
            open_time = None
            signal_bid = None
        elif state == "ACTIVE_SHORT" and current_rci <= legacy.SHORT_EXIT_RCI9:
            if open_time is None or signal_bid is None or open_direction != "SHORT":
                raise legacy.M9VContractError(f"{timeframe} SHORT exit without frozen/post-start primary")
            episodes.append(
                legacy.Episode(timeframe, "SHORT", open_time, signal_bid, decision, open_time > start)
            )
            state = "IDLE"
            open_direction = None
            open_time = None
            signal_bid = None

    if state in ("ACTIVE_LONG", "ACTIVE_SHORT"):
        if open_time is None or signal_bid is None or open_direction is None:
            raise legacy.M9VContractError(f"{timeframe} active state without frozen/post-start primary")
        episodes.append(
            legacy.Episode(timeframe, open_direction, open_time, signal_bid, None, open_time > start)
        )

    return episodes, {
        "timeframe": timeframe,
        "state_at_start": str(frozen_state["state_at_start"]),
        "inherited_active_primary_time": inherited_text,
        "pre_start_active_seen": inherited_active,
        "eligible_post_start_primary_count": sum(ep.primary_post_start for ep in episodes),
        "all_episode_count": len(episodes),
        "bootstrap_source": "IMMUTABLE_RUNTIME_STATE_AT_START",
        "bounded_head_replay_before_start": False,
    }


def build_m9v_runner(
    local_root: Path,
    source_root: Path,
    journal: Path,
    point: float,
) -> Callable[[], int]:
    runner.add_module_path(runner.MR / "m9v" / "python")
    runner.add_module_path(runner.MR / "m9p" / "python")
    legacy = importlib.import_module("m9v_core")
    core = importlib.import_module("m9v_core_v2")
    wrapper = importlib.import_module("run_m9v_shadow_once_v2")
    runtime_path = local_root / adapter.RUNTIME_SPECS["M9V"][0]
    runtime = adapter.load_json(runtime_path)
    contract_path = (
        runner.ROOT
        / "config"
        / "mochipoyo_alert_research"
        / "m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json"
    )
    contract = adapter.load_json(contract_path)
    file_map = contract["data"]["live_file_map"]
    by_filename = {
        str(filename): runtime["frozen_row_prefixes"][timeframe]
        for timeframe, filename in file_map.items()
    }

    def adapter_audit(
        *,
        data_root: Path,
        contract: dict[str, Any],
        runtime: dict[str, Any],
        point: float,
    ) -> dict[str, Any]:
        contract_sha = core.sha256_bytes(
            json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        core.validate_runtime_manifest(runtime, contract, contract_sha)
        adapter.validate_loop(local_root, "M9V", source_root, point)
        original_prefix = legacy.prefix_fingerprint
        original_replay = legacy.replay_episodes

        def compatibility_prefix(path: Path, cutoff: Any) -> dict[str, Any]:
            frozen = by_filename.get(path.name)
            if not isinstance(frozen, dict):
                raise core.M9VContractError(
                    f"unexpected adapter file during compatibility check: {path.name}"
                )
            return dict(frozen)

        def replay_with_immutable_start(
            bars: list[Any],
            timeframe: str,
            start: Any,
        ) -> tuple[list[Any], dict[str, Any]]:
            frozen = runtime.get("state_at_start", {}).get(timeframe)
            if not isinstance(frozen, dict):
                raise core.M9VContractError(f"missing immutable state-at-start: {timeframe}")
            return replay_from_frozen_start(legacy, bars, timeframe, start, frozen)

        runtime_compat = dict(runtime)
        runtime_compat["prefix_fingerprints"] = dict(runtime["frozen_row_prefixes"])
        legacy.prefix_fingerprint = compatibility_prefix
        legacy.replay_episodes = replay_with_immutable_start
        try:
            return legacy.audit(
                data_root=data_root,
                contract=contract,
                runtime=runtime_compat,
                point=point,
            )
        finally:
            legacy.prefix_fingerprint = original_prefix
            legacy.replay_episodes = original_replay

    core.audit = adapter_audit
    os.environ["M9V_GOLD_DATA_ROOT"] = str(journal)
    os.environ["M9V_RUNTIME_MANIFEST"] = str(runtime_path)
    return wrapper.legacy.main
