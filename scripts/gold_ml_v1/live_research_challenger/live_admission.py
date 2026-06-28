from __future__ import annotations

from typing import Any

import pandas as pd

from live_position import CONTRACTS, LiveM1Engine
from live_records import candidate_record, dynamic_update
from live_store import DeferredRun, json_value


def process_component(
    comp: str,
    events: pd.DataFrame,
    prior: dict[str, Any] | None,
    engine: LiveM1Engine,
    now_text: str,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any] | None,
    list[dict[str, Any]],
]:
    contract = CONTRACTS[comp]
    new_records: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    open_until = pd.Timestamp.min
    active = prior

    if active is not None:
        evaluated = engine.evaluate(active["decision_time"], active["atr"], contract)
        if evaluated["position_state"] == "ENTRY_M1_MISSING":
            raise DeferredRun(f"{comp}: existing open position M1 entry row is unavailable")
        if active.get("candidate_key"):
            updates.append(
                dynamic_update(active["candidate_key"], evaluated, now_text)
            )
        if evaluated["position_state"] == "OPEN":
            for row in events.itertuples(index=False):
                audits.append(
                    {
                        "comp": comp,
                        "decision_time": json_value(row.bar_close_time),
                        "admission_state": "SUPPRESSED_BY_OPEN_POSITION",
                    }
                )
            return new_records, updates, active, audits
        open_until = pd.Timestamp(evaluated["exit_time"])
        active = None

    if events.empty:
        return new_records, updates, active, audits

    for event in events.sort_values("bar_close_time", kind="mergesort").itertuples(
        index=False
    ):
        decision = pd.Timestamp(event.bar_close_time)
        if decision < open_until:
            audits.append(
                {
                    "comp": comp,
                    "decision_time": decision.strftime("%Y-%m-%d %H:%M:%S"),
                    "admission_state": "SUPPRESSED_BY_ONE_POSITION",
                    "suppression_until": open_until.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            continue

        evaluated = engine.evaluate(decision, float(event.atr_for_trade), contract)
        if evaluated["position_state"] == "ENTRY_M1_MISSING":
            raise DeferredRun(f"{comp}: M1 entry row is not yet available for {decision}")
        if evaluated["position_state"] == "INVALID_ATR":
            audits.append(
                {
                    "comp": comp,
                    "decision_time": decision.strftime("%Y-%m-%d %H:%M:%S"),
                    "admission_state": "INVALID_ATR",
                }
            )
            continue

        candidate_key: str | None = None
        if bool(event.emit_candidate):
            record = candidate_record(event, evaluated, now_text)
            candidate_key = record["candidate_key"]
            new_records.append(record)
            audits.append(
                {
                    "comp": comp,
                    "decision_time": record["decision_time"],
                    "candidate_key": candidate_key,
                    "admission_state": "ACCEPTED_CANDIDATE",
                    "position_state": evaluated["position_state"],
                }
            )
        else:
            audits.append(
                {
                    "comp": comp,
                    "decision_time": decision.strftime("%Y-%m-%d %H:%M:%S"),
                    "admission_state": "ACCEPTED_PARENT_FILTERED_FROM_FINAL",
                }
            )

        if evaluated["position_state"] == "OPEN":
            active = {
                "decision_time": decision,
                "atr": float(event.atr_for_trade),
                "candidate_key": candidate_key,
            }
            break
        open_until = pd.Timestamp(evaluated["exit_time"])

    return new_records, updates, active, audits
