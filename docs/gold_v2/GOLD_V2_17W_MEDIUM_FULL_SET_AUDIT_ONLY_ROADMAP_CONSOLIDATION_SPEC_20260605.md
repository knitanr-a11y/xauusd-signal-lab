# GOLD V2 17W MEDIUM full-set audit-only roadmap consolidation specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `17W_MEDIUM_FULL_SET_AUDIT_ONLY_ROADMAP_CONSOLIDATION`
Mode: audit-only

## Purpose

17W consolidates the current MEDIUM full-set audit-only roadmap after 17R/17S/17T/17U/17V.

17W is roadmap consolidation only. It does not enable live mode, does not implement arbitration, does not implement predicates, does not evaluate OHLC, does not rediscover candidates, does not create final signals, does not send Discord notifications, does not place MT5 orders, does not call AI API, and does not install a live hook.

## Source of truth

Use only audited 17V outputs:

1. `FX_OUTPUTS/gold_v2_17v_live_parity_safety_gate_plan_audit_only/gold_v2_17v_live_parity_safety_gate_plan_summary.json`
2. `FX_OUTPUTS/gold_v2_17v_live_parity_safety_gate_plan_audit_only/gold_v2_17v_safety_gate_plan_checks.csv`
3. `FX_OUTPUTS/gold_v2_17v_live_parity_safety_gate_plan_audit_only/gold_v2_17v_live_safety_gate_matrix.csv`
4. `FX_OUTPUTS/gold_v2_17v_live_parity_safety_gate_plan_audit_only/gold_v2_17v_non_enablement_matrix.csv`
5. `FX_OUTPUTS/gold_v2_17v_live_parity_safety_gate_plan_audit_only/gold_v2_17v_required_next_gates.csv`
6. `FX_OUTPUTS/gold_v2_17v_live_parity_safety_gate_plan_audit_only/gold_v2_17v_blockers.csv`
7. `FX_OUTPUTS/gold_v2_17v_live_parity_safety_gate_plan_audit_only/gold_v2_17v_safety_matrix.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer executable predicates.

## Expected input state

17V must have status:

`LIVE_PARITY_SAFETY_GATE_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED`

Expected 17V state:

- live parity safety gate plan ready true
- planned safety gates 11
- enabled safety gates now 0
- live enabled false
- live evaluator false
- final signal false
- all external actions false
- NO_SIGNAL Discord notification false

## Roadmap consolidation policy

17W must record the unresolved roadmap in order:

1. Resolve TIER2 row-level source identity.
2. Design component executable parity for RANGE96/VOL/TIER2.
3. Design MEDIUM arbitration replay parity.
4. Re-run safety-gate planning after parity design.
5. Keep live/final/external action gates disabled until explicit approval.

No roadmap item may mark live/final/external actions as allowed.

## Output folder

`FX_OUTPUTS/gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation`

## Main outputs

- `GOLD_V2_17W_MEDIUM_FULL_SET_AUDIT_ONLY_ROADMAP_CONSOLIDATION_REPORT.md`
- `gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation_summary.json`
- `gold_v2_17w_input_audit.csv`
- `gold_v2_17w_consolidation_checks.csv`
- `gold_v2_17w_roadmap_matrix.csv`
- `gold_v2_17w_open_blockers_consolidated.csv`
- `gold_v2_17w_required_next_gates.csv`
- `gold_v2_17w_safety_matrix.csv`

## Success status

`MEDIUM_FULL_SET_AUDIT_ONLY_ROADMAP_CONSOLIDATED_LIVE_BLOCKED`

This means the audit-only roadmap is consolidated. It does not permit live execution, final signals, or external actions.

## Stop conditions

Stop if:

- any required input is missing,
- 17V status is not expected,
- 17V checks/non-enablement/safety contain STOP,
- 17V enabled safety gate count is not zero,
- any roadmap row enables live/final/external actions,
- NO_SIGNAL Discord notification is true.

## Recommended next step after success

After 17W success, the next possible step is:

`18A_EXECUTABLE_PARITY_DESIGN_AUDIT_ONLY`

18A must remain design/audit-only and must not implement predicates, execute OHLC replay, enable live execution, or create final signals.
