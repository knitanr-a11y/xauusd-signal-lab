# GOLD V2 21A completion-to-live/final-signal roadmap audit-only

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Mode: audit-only roadmap

## Current confirmed position

Current completed gate:

`20T_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_ENTRY_READINESS_TEMPLATE_AUDIT_ONLY`

Current 20T status:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_ENTRY_READINESS_TEMPLATE_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

Current decision state:

- `decision_value=UNSET`
- `selected_allowed_value=UNSET`
- no actual value recorded
- source recovery blocked
- source identity finalization blocked
- live evaluator blocked
- final signal blocked
- Discord blocked
- MT5 blocked
- AI API blocked
- live hook blocked

## Completion target selected by operator

The operator views completion target as the full downstream objective:

1. actual decision value recorded safely
2. source recovery decision path audited
3. source identity finalization audited
4. live evaluator readiness audited
5. final signal readiness audited
6. Discord notification path gated
7. MT5 order path gated
8. AI API and live hook remain off unless separately authorized

## Non-negotiable safety boundary

A generic phrase such as `proceed` is not enough to:

- record the actual decision value
- execute source recovery
- finalize source identity
- enable live evaluator
- emit final signals
- send Discord messages
- place MT5 orders
- call AI APIs
- enable live hooks

Each high-risk transition must have a separate explicit gate.

## Allowed decision values at the next human-selection boundary

The next human value must be exactly one of:

- `DEFER`
- `REQUEST_MORE_AUDIT`
- `REJECT_SOURCE_RECOVERY`
- `EXPLICIT_APPROVAL_CANDIDATE`

Until exactly one value is selected, all downstream execution remains blocked.

## Recommended staged path to completion target

### Phase A: value entry and value audit

- 20U: explicit value selection intake gate, audit-only
- 20V: selected value draft generation, audit-only
- 20W: selected value load-smoke, audit-only
- 20X: selected value content audit, audit-only
- 20Y: selected value reconciliation, audit-only
- 20Z: selected value final audit, audit-only

If value is `DEFER`, stop.
If value is `REQUEST_MORE_AUDIT`, return to audit planning.
If value is `REJECT_SOURCE_RECOVERY`, record rejection and stop source recovery path.
If value is `EXPLICIT_APPROVAL_CANDIDATE`, continue to Phase B, but still do not execute source recovery.

### Phase B: source recovery authorization and dry-run

- 21B: source recovery authorization readiness, audit-only
- 21C: source recovery dry-run plan, audit-only
- 21D: source recovery dry-run load-smoke, audit-only
- 21E: source recovery dry-run content audit, audit-only
- 21F: source recovery dry-run reconciliation, audit-only
- 21G: source recovery dry-run final audit, audit-only

No source recovery execution happens in this phase.

### Phase C: source identity finalization readiness

- 22A: source identity finalization readiness, audit-only
- 22B: finalization dry-run draft, audit-only
- 22C: finalization dry-run audit, audit-only
- 22D: finalization final gate, audit-only

No live or final signal is enabled in this phase.

### Phase D: live evaluator readiness

- 23A: live evaluator read-only design audit
- 23B: live evaluator parity contract audit
- 23C: live evaluator dry-run output audit
- 23D: live evaluator safety final audit

Live evaluator remains disabled until explicitly authorized.

### Phase E: final signal readiness

- 24A: final signal rule contract audit
- 24B: final signal dry-run audit
- 24C: final signal no-external-action audit
- 24D: final signal final readiness audit

Final signal remains disabled until explicitly authorized.

### Phase F: external integrations

Each integration requires a separate gate:

- Discord notification gate
- NO_SIGNAL Discord suppression gate
- MT5 order gate
- AI API gate
- live hook gate

Default for every integration remains OFF.

## Immediate next safe step

Next safe repo step:

`20U_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_SELECTION_INTAKE_GATE_AUDIT_ONLY`

20U should only prepare a gate that validates the operator-selected value later. It must not choose or record a value by itself.

## Stop condition

Stop before 20U value record if the operator has not explicitly selected one allowed value.
