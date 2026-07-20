from __future__ import annotations

from datetime import datetime

from scripts.mochipoyo_alert_research.m7c_prospective_shadow import (
    ProxySignal,
    SourceTransition,
    compare,
    readiness,
)


def manifest() -> dict:
    return {
        "matching": {"source_arrival_grace_minutes": 120},
        "review_gates": {
            "operational_checkpoint_events": 5,
            "interim_checkpoint_events": 15,
            "formal_minimum_supported_source_events": 30,
            "formal_minimum_supported_events_per_ticker": 10,
            "formal_minimum_events_per_primary_direction": 5,
            "formal_minimum_exit_events": 10,
        },
    }


def source(raw_id: int, ticker: str, text: str, transition: str) -> SourceTransition:
    states = {
        "PRIMARY_LONG": ("IDLE", "ACTIVE_LONG"),
        "PRIMARY_SHORT": ("IDLE", "ACTIVE_SHORT"),
        "LONG_EXIT": ("ACTIVE_LONG", "IDLE"),
        "SHORT_EXIT": ("ACTIVE_SHORT", "IDLE"),
        "REENTRY_LONG": ("ACTIVE_LONG", "ACTIVE_LONG"),
        "REENTRY_SHORT": ("ACTIVE_SHORT", "ACTIVE_SHORT"),
    }
    before, after = states[transition]
    return SourceTransition(
        raw_alert_id=raw_id,
        ticker=ticker,
        decision_time_utc=datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ"),
        transition=transition,
        state_before=before,
        state_after=after,
        event_role="REENTRY_ALERT" if transition.startswith("REENTRY") else "PRIMARY_ALERT",
    )


def signal(ticker: str, text: str, transition: str) -> ProxySignal:
    states = {
        "PRIMARY_LONG": ("IDLE", "ACTIVE_LONG", "KERNEL-L1"),
        "PRIMARY_SHORT": ("IDLE", "ACTIVE_SHORT", "KERNEL-S1"),
        "LONG_EXIT": ("ACTIVE_LONG", "IDLE", "EXIT-L0"),
        "SHORT_EXIT": ("ACTIVE_SHORT", "IDLE", "EXIT-S0"),
    }
    before, after, kernel = states[transition]
    return ProxySignal(
        ticker=ticker,
        decision_time_utc=datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ"),
        transition=transition,
        kernel_id=kernel,
        state_before=before,
        state_after=after,
        features={},
    )


def test_exact_and_one_bar_matches_are_one_to_one() -> None:
    comparisons, extras, summary = compare(
        [
            source(100, "BTCUSD", "2026-07-20T00:15:00Z", "PRIMARY_LONG"),
            source(101, "BTCUSD", "2026-07-20T01:00:00Z", "LONG_EXIT"),
        ],
        [
            signal("BTCUSD", "2026-07-20T00:15:00Z", "PRIMARY_LONG"),
            signal("BTCUSD", "2026-07-20T00:45:00Z", "LONG_EXIT"),
        ],
        {"BTCUSD": datetime(2026, 7, 20, 2, 0)},
        "2026-07-20T04:00:00Z",
        manifest(),
    )
    assert [row["classification"] for row in comparisons] == [
        "EXACT_MATCH",
        "EARLY_1_BAR",
    ]
    assert extras == []
    assert summary["within_one_bar_match_count"] == 2


def test_reentry_is_not_scored_and_old_unmatched_proxy_is_extra() -> None:
    comparisons, extras, summary = compare(
        [source(102, "XAUUSD", "2026-07-20T00:30:00Z", "REENTRY_LONG")],
        [signal("XAUUSD", "2026-07-20T00:45:00Z", "LONG_EXIT")],
        {"XAUUSD": datetime(2026, 7, 20, 1, 0)},
        "2026-07-20T04:00:00Z",
        manifest(),
    )
    assert comparisons[0]["classification"] == "UNSUPPORTED_REENTRY_NOT_SCORED"
    assert extras[0]["classification"] == "FINALIZED_EXTRA_PROXY_SIGNAL"
    assert summary["unsupported_reentry_count"] == 1
    assert summary["scored_source_event_count"] == 0


def test_formal_gate_never_auto_claims_reproduction() -> None:
    rows = []
    raw_id = 1
    for ticker in ("BTCUSD", "XAUUSD"):
        for transition, count in (
            ("PRIMARY_LONG", 5),
            ("PRIMARY_SHORT", 5),
            ("LONG_EXIT", 3),
            ("SHORT_EXIT", 2),
        ):
            for _ in range(count):
                rows.append(
                    {
                        "raw_alert_id": raw_id,
                        "ticker": ticker,
                        "source_decision_time_utc": "2026-07-20T00:00:00Z",
                        "source_transition": transition,
                        "classification": "EXACT_MATCH",
                    }
                )
                raw_id += 1
    result = readiness(rows, manifest())
    assert result["formal_review_state"] == "READY_FOR_MANUAL_REPRODUCTION_REVIEW"
    assert result["automatic_reproduction_claim"] is False
