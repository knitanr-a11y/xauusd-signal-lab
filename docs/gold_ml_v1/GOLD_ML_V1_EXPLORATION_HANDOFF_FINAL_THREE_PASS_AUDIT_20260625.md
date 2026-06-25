# GOLD_ML_V1 — Final Three-Pass Exploration / Handoff Audit

Date: 2026-06-25  
Mode: **AUDIT ONLY**

## Final result

**PASS after corrections.**

The exploration cautions, candidate-pool protection, one-click workflow, and next-chat handoff were reviewed three separate times from different perspectives.

## Pass 1 — Exploration methodology

Checked:

- frozen year split;
- leakage and bar-availability rules;
- candidate identity immutability;
- candidate-pool preservation;
- search multiplicity;
- failed-result preservation;
- same-lineage dependence;
- bridge-row restrictions;
- promotion gates.

Finding:

The first handoff did not state the complete fixed year split, multiplicity reporting, failed-cell preservation, and candidate-pool denominator rules strongly enough.

Correction:

Created and froze the authoritative exploration policy:

`config/gold_ml_v1/exploration_guardrails_20260625.json`

It now requires:

- 2023 exploration only;
- 2024 validation only with no retune;
- 2025 final test only with no retune;
- 2026 diagnostic only and never retune;
- predeclared search space and pass gates;
- every attempted rule and parameter cell retained;
- total search count and multiplicity reported;
- failures, nulls, and all survivors preserved;
- no best-seed, best-cell, best-year, PF, or win-rate cherry-picking;
- no silent candidate addition, removal, replacement, or relabeling;
- no same-lineage metric summation;
- new candidate ID for any logic or execution change.

Outcome: PASS.

## Pass 2 — Workflow and stage gates

Checked:

- whether a new chat could begin a new exploration prematurely;
- whether cost stress and fresh prospective confirmation were hard gates;
- whether bridge rows could leak into exploration or live use;
- whether user operation remained one-click;
- whether failure handling was fail-closed.

Finding:

The earlier workflow did not make the new-exploration lock explicit enough.

Correction:

Frozen rules now state:

- no new exploration before cost stress and fresh prospective confirmation;
- a separate branch requires explicit user authorization and stays audit-only;
- the separate branch must not modify the frozen nine;
- `WARMUP_BRIDGE_EXACT` cannot be used for exploration, tuning, model selection, cost-stress primary populations, or live decisions;
- only `RUN_GOLD_ML_V1_NEXT.bat` is user-facing;
- future phases are implemented and committed before the action config changes;
- every runner validates provenance, preserves prior output, writes summaries/errors, and returns 0 only on PASS.

Outcome: PASS.

## Pass 3 — Cross-file consistency and ambiguity

Checked cross-file consistency among:

- `AGENTS.md`;
- `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`;
- current state snapshot;
- next action config;
- exploration guardrails;
- triple-check handoff;
- one-click handoff;
- governance tests;
- CI workflow.

Findings:

1. Two similar exploration policy files existed, which could create ambiguity.
2. The original complete one-click handoff did not include exploration guardrails in its own mandatory read order.
3. Governance tests needed stronger checks for bridge use and authoritative handoff consistency.

Corrections:

- deleted duplicate `config/gold_ml_v1/exploration_governance_20260625.json`;
- retained `config/gold_ml_v1/exploration_guardrails_20260625.json` as the sole authoritative exploration policy;
- created authoritative V2 handoff:
  `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md`;
- marked V2 as superseding the earlier one-click handoff;
- updated AGENTS, START HERE, and current state to V2;
- strengthened `tests/gold_ml_v1/test_exploration_guardrails.py`;
- verified `.github/workflows/gold_ml_v1_batch023_tests.yml` runs that governance test.

Outcome: PASS.

## Authoritative new-chat files

A new chat must read in this order:

1. `AGENTS.md`
2. `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
3. `config/gold_ml_v1/current_state_snapshot_20260624.json`
4. `config/gold_ml_v1/next_local_action.json`
5. `config/gold_ml_v1/exploration_guardrails_20260625.json`
6. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_GUARDRAILS_TRIPLE_CHECK_20260625.md`
7. Batch023 forensic and bridge records listed by AGENTS
8. `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md`
9. This final audit

## Current hard gate

New candidate exploration is **not authorized now**.

The next authorized phase is:

`COST_STRESS_RAW_RECONSTRUCTED_ONLY_REPORT_BRIDGE_SEPARATELY_THEN_FRESH_PROSPECTIVE`

Only after cost stress, separate bridge reporting, fresh prospective confirmation, and an explicit audit authorization may another exploration batch begin.

## CI honesty

The governance test is present in the workflow. A CI run must not be claimed PASS until an actual workflow result is observed.
