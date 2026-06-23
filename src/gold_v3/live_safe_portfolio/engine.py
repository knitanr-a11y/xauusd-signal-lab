from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from .config import LiveSafeConfig
from .models import Candidate, Decision, DecisionStatus, Source
from .rollover import interval_overlaps_hours
from .state import SQLiteStateStore
from .timeutil import parse_dt


class SafePortfolioEngine:
    """Causal Stage286 safe-portfolio admission engine."""

    def __init__(self, config: LiveSafeConfig, store: SQLiteStateStore):
        config.validate()
        self.config = config
        self.store = store

    def process_batch(self, candidates: Iterable[Candidate]) -> list[Decision]:
        ordered = sorted(candidates, key=lambda c: (
            c.entry_dt,
            self.config.admission.priorities[c.source.value],
            c.candidate_id,
        ))
        return [self.process_candidate(candidate) for candidate in ordered]

    def process_candidate(self, candidate: Candidate) -> Decision:
        candidate.validate(self.config.time_basis)
        priority = self.config.admission.priorities[candidate.source.value]
        with self.store.transaction() as conn:
            if self.store.candidate_exists(conn, candidate.candidate_id):
                state = self.store.get_state(conn)
                dd = float(state["peak_equity"]) - float(state["equity"])
                return Decision(candidate.candidate_id, DecisionStatus.DUPLICATE,
                                "DUPLICATE_CANDIDATE_ID", dd,
                                float(state["equity"]), float(state["peak_equity"]))

            state_before = self.store.get_state(conn)
            last_entry_text = state_before.get("last_processed_entry_dt")
            last_priority = state_before.get("last_processed_priority")
            if last_entry_text is not None:
                last_entry = parse_dt(last_entry_text)
                if candidate.entry_dt < last_entry:
                    raise ValueError("out-of-order candidate entry_dt would violate live causality")
                if candidate.entry_dt == last_entry and last_priority is not None and priority < int(last_priority):
                    raise ValueError("out-of-order same-entry priority; submit one complete bar batch")

            applied = self.store.apply_resolved_through(conn, candidate.entry_dt)
            state = self.store.get_state(conn)
            equity = float(state["equity"])
            peak = float(state["peak_equity"])
            dd = peak - equity
            diagnostics = self._diagnostics(candidate, dd, applied)
            reason = self._reject_reason(conn, candidate, state, dd)
            if reason is None:
                decision = Decision(candidate.candidate_id, DecisionStatus.ACCEPTED_SHADOW,
                                    "SAFE_PORTFOLIO_ACCEPT", dd, equity, peak, diagnostics)
            else:
                decision = Decision(candidate.candidate_id, DecisionStatus.REJECTED_SHADOW,
                                    reason, dd, equity, peak, diagnostics)
            self.store.insert_candidate(conn, candidate, decision, priority)
            return decision

    def _diagnostics(self, candidate: Candidate, dd: float, applied: list[dict]) -> dict:
        guards = self.config.runtime_guards
        return {
            "realized_dd": dd,
            "resolutions_applied_before_decision": applied,
            "spread_guard_would_block": candidate.entry_spread_usd is not None and candidate.entry_spread_usd > guards.entry_spread_cap_usd,
            "quote_age_guard_would_block": candidate.quote_age_seconds is not None and candidate.quote_age_seconds > guards.quote_age_seconds_max,
            "runtime_guard_enforcement": guards.enforcement,
        }

    def _reject_reason(self, conn, candidate: Candidate, state: dict, dd: float) -> str | None:
        rollover = self.config.rollover
        if rollover.enabled and candidate.source.value in rollover.sources and interval_overlaps_hours(
            candidate.entry_dt, candidate.max_holding_minutes, rollover.blocked_server_hours
        ):
            return "BASE_ROLLOVER_00_01_SHADOW_ONLY"

        if self.store.active_position_at(conn, candidate.entry_dt) is not None:
            return "ONE_POSITION_ACTIVE"

        if candidate.source == Source.BASE:
            return None

        admission = self.config.admission
        if dd > admission.common_realized_dd_max:
            return "COMMON_REALIZED_DD_GT_30"

        last_entry = state["last_candidate_entry_dt"]
        if last_entry is not None:
            cutoff = parse_dt(last_entry) + timedelta(hours=admission.shared_candidate_cooldown_hours)
            if candidate.entry_dt < cutoff:
                return "SHARED_CANDIDATE_COOLDOWN_12H"

        if candidate.source == Source.SHORT_STRICT:
            if dd > admission.strict_short_realized_dd_max:
                return "STRICT_SHORT_REALIZED_DD_GT_10"
            last_loss = state["last_candidate_loss_exit_dt"]
            if last_loss is not None:
                cutoff = parse_dt(last_loss) + timedelta(hours=admission.candidate_loss_lockout_hours)
                if candidate.entry_dt < cutoff:
                    return "STRICT_SHORT_CANDIDATE_LOSS_LOCKOUT_24H"
        return None
