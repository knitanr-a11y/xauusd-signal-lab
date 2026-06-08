# NEXT CHAT HANDOFF - GOLD V2 25C94 implemented / local run required

Created: 2026-06-08

Repo: `knitanr-a11y/xauusd-signal-lab`

## Current status

GOLD V2 remains **audit-only**.

25C94 implementation files were added on GitHub, but the audit has not been executed in this chat because the local `Files/FX_OUTPUTS` source artifacts are not available inside the GitHub connector runtime.

Latest implementation status:

```text
25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY_IMPLEMENTED_LOCAL_RUN_REQUIRED
```

This is not source recovery approval and does not unlock live.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB metrics.
- Discord / MT5 / AI API / live hook / live evaluator / final signal remain OFF unless explicitly approved.
- NO_SIGNAL must not notify Discord.
- Do not use `latest_start` / `closest_start` as live logic until reviewed and explicitly approved.
- Stored top-row `profit` self-binding is diagnostic/historical only and cannot unlock live by itself.

## What was implemented

25C94 was implemented as an audit-only review of the 25C93 non-oracle selector candidate.

The implementation fixes:

```text
component_family = entry_gap
gap_min = 15
selectors_under_review = latest_start, closest_start
```

It does **not** restart broad count exploration.

It checks:

1. Required input inventory and hashes.
2. 25C93 upstream status.
3. raw RR125 source rows = 6834.
4. CoreB top rows = 125.
5. `latest_start` count fields match all 125 rows.
6. `closest_start` count fields match all 125 rows.
7. `latest_start` and `closest_start` select the same component for all 125 rows.
8. Non-oracle representative profit / `top_candidate_id` binding candidates.
9. Diagnostic-only top-profit presence inside selected raw component rows.
10. Decision matrix and blocker matrix.

## Files added

Spec:

```text
docs/gold_v2/GOLD_V2_25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY_SPEC_20260608.md
```

Script:

```text
scripts/gold_v2_runtime/audit_gold_v2_25c94_non_oracle_selector_candidate_review_audit_only.py
```

BAT:

```text
scripts/gold_v2_runtime/bat/25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY.bat
```

This handoff:

```text
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C94_IMPLEMENTED_LOCAL_RUN_REQUIRED_20260608.md
```

## Input files the local run must find

```text
25c93_summary.json
rr125_raw_signal_ledger.csv
rr125_top_ledgers.csv
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
```

Expected source counts:

```text
raw RR125 rows = 6834
CoreB top rows = 125
direct historical SOT rows = 125 if present/usable
```

## BAT execution order

Run only:

```text
scripts/gold_v2_runtime/bat/25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY.bat
```

This executes:

```text
python scripts\gold_v2_runtime\audit_gold_v2_25c94_non_oracle_selector_candidate_review_audit_only.py
```

Do not run any Discord, MT5, AI API, live hook, live evaluator, or final signal script.

## Expected output directory

```text
Files/FX_OUTPUTS/gold_v2_25c94_non_oracle_selector_candidate_review_audit_only
```

Expected output files:

```text
GOLD_V2_25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md
25c94_summary.json
25c94_input_inventory.csv
25c94_selector_component_rows.csv
25c94_selector_pair_stability.csv
25c94_profit_binding_summary.csv
25c94_profit_binding_rows.csv
25c94_profit_presence_diagnostics.csv
25c94_decision_matrix.csv
25c94_blocker_matrix.csv
```

Expected zip:

```text
Files/FX_OUTPUTS/gold_v2_25c94_non_oracle_selector_candidate_review_audit_only.zip
```

## Success conditions

The strongest possible 25C94 result is still audit-only:

```text
NON_ORACLE_SELECTOR_AND_PROFIT_BINDING_CANDIDATE_READY_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

This requires:

```text
inputs_present = true
25c93 status = NON_ORACLE_COMPONENT_SELECTOR_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
raw_rr125_rows = 6834
top125_rows = 125
latest_start count fields = 125 / 125
closest_start count fields = 125 / 125
latest_start and closest_start same component = 125 / 125
at least one non-oracle raw-row or aggregation profit binding method = 125 / 125
```

Even if this passes, live remains blocked and human review is required before any next audit stage.

## Stop conditions

Stop as audit-only / live blocked if any occur:

```text
missing input
25c93 upstream status mismatch
raw_rr125_rows != 6834
top125_rows != 125
latest_start count fields fail
closest_start count fields fail
latest_start and closest_start choose different components for any row
no non-oracle profit binding method reaches 125 / 125
only stored top-profit self-binding or raw profit presence matches
```

## Expected blocked status if profit binding is not recovered

```text
NON_ORACLE_SELECTOR_COUNT_MATCHED_PROFIT_BINDING_BLOCKED_AUDIT_ONLY_LIVE_BLOCKED
```

## What not to do next

- Do not claim 25C94 was run until the BAT is executed locally and outputs are reviewed.
- Do not claim source recovery approval.
- Do not unlock CoreB live evaluator.
- Do not use A002 metrics for CoreB.
- Do not treat top-row stored `profit` self-match as recovered live representative binding.
- Do not proceed to Discord / MT5 / AI API / live hook / final signal.
