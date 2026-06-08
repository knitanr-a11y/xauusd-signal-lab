# NEXT CHAT HANDOFF - GOLD V2 25C93 done / 25C94 next

Created: 2026-06-08

Repo: `knitanr-a11y/xauusd-signal-lab`

## Current status

GOLD V2 remains **audit-only**.

Latest completed step:

```text
25C93_NON_ORACLE_COMPONENT_SELECTOR_AUDIT_ONLY
```

Latest status:

```text
NON_ORACLE_COMPONENT_SELECTOR_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

This is the first non-oracle reconstruction candidate that fully matches CoreB top 125 for `same_count` / `source_rule_count` / `unique_origins`.

It is **not** source recovery approval and does **not** unlock live.

## Hard guardrails to preserve

- GOLD V2 is audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- Prefer audited source-of-truth artifacts.
- A002 is demoted to auxiliary-only and is not used for CoreB metrics.
- Discord / MT5 / AI API / live hook / live evaluator / final signal remain OFF unless explicitly approved.
- NO_SIGNAL must not notify Discord.
- Do not use `latest_start` / `closest_start` as live logic until reviewed and explicitly approved.

## Important historical CoreB facts

CoreB historical direct SOT source:

```text
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
```

Direct filter in `rr125_top_ledgers.csv`:

```text
policy == RR125_from_RR1_rules
filter == same_count>=15
```

CoreB historical metrics:

```text
2025: 104 trades, WR 72.1154%, PF 3.443512, total R 143.0175
2026: 21 trades, WR 80.9524%, PF 5.153846, total R 40.5
total: 125 trades, WR 73.6%, PF 3.687740, total R 183.5175
```

CoreB historical SOT report is allowed.

CoreB live evaluator remains blocked.

## A002 status

A002 is not CoreB.

A002 is an audit ID for a broad fixed event set from:

```text
rr125_raw_signal_ledger.csv
policy = RR125_from_RR1_rules
raw RR1 / unique_origins>=2 / after 2025-02-24 12:00
```

A002 membership was proven, but profit binding is ambiguous and A002 is **not used** for CoreB performance.

## Completed local official chain after 25C79

The local official chain had stopped at 25C79. From there:

- 25C80 local sync from 25C79: required CoreB direct SOT inputs present.
- 25C81 CoreB direct SOT local replay: passed.
- 25C82 local CoreB historical SOT report package: ready.
- 25C83 cluster representative logic recovery: simple raw/group/profit probes did not recover original logic.
- 25C84 deep cluster reconstruction: no complete reconstruction from time windows / feature conditions / repository keyword scan alone.
- 25C85 local source candidate content review: no true generator found; partial local logic/configs found.
- 25C86 frozen same-count rule replay: rule-level condition pass counts did not match.
- 25C87 condition-object and time-alignment replay: condition-object counts did not match.
- 25C88 source-universe filtered component reconstruction: independent source-universe value filters did not help.
- 25C89 source-universe rule tuple membership: candidate/origin/variant/filter tuple filtering did not help.
- 25C90 base-condition rule membership: base_condition tuple filtering did not help.
- 25C91 raw cluster parameter sweep: best raw-only component was `entry_gap=15m`, 66/125 exact.
- 25C92 nearby component oracle boundary: `entry_gap=15m` components contain the correct answer for 125/125 when oracle-selection is allowed.
- 25C93 non-oracle component selector: `latest_start` and `closest_start` select the correct component for 125/125 without target same_count.

## 25C91 result summary

25C91 status:

```text
RAW_CLUSTER_PARAMETER_SWEEP_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED
```

Best raw-only direct selector:

```text
family = entry_gap
gap_min = 15
same_count_exact = 66 / 125
source_rule_count_exact = 66 / 125
```

This showed raw clustering was partially close but not enough by itself.

## 25C92 result summary

25C92 status:

```text
NEARBY_COMPONENT_ORACLE_FULL_COUNT_FOUND_AUDIT_ONLY_NOT_LIVE_LOGIC
```

Best oracle boundary:

```text
family = entry_gap
gap_min = 15
nearby_min = 0
same_count_oracle_exact = 125 / 125
source_rule_count_oracle_exact = 125 / 125
unique_origins_oracle_exact = 125 / 125
```

Interpretation:

- The correct component exists among the components covering each top-row entry time.
- Oracle matching is not live logic.
- Remaining problem moved from component generation to component selector / representative logic.

## 25C93 result summary

25C93 status:

```text
NON_ORACLE_COMPONENT_SELECTOR_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Fixed reconstruction:

```text
component_family = entry_gap
gap_min = 15
```

Best non-oracle selectors:

```text
latest_start:
  selected_rows = 125 / 125
  same_count_exact = 125 / 125
  source_rule_count_exact = 125 / 125
  unique_origins_exact = 125 / 125
  profit_sum_exact = 0 / 125
  status = FULL

closest_start:
  selected_rows = 125 / 125
  same_count_exact = 125 / 125
  source_rule_count_exact = 125 / 125
  unique_origins_exact = 125 / 125
  profit_sum_exact = 0 / 125
  status = FULL
```

Decision matrix:

```text
full_non_oracle_selector = True
coreb_live_evaluator_allowed = False
a002_used = False
```

Blockers:

```text
B93-001 non_oracle_selector REVIEW HARD Candidate requires human review
B93-002 CoreB live evaluator OPEN HARD Live remains blocked
B93-003 A002 CLOSED_FOR_COREB_MAIN_PATH INFO A002 not used
```

## What 25C93 did NOT solve

25C93 solved:

```text
component selection for count fields
```

25C93 did NOT solve:

```text
representative profit / top_candidate profit binding
```

In 25C93, `profit_sum_exact = 0 / 125` for the two FULL selectors. Therefore, the next step must review whether:

1. CoreB historical profit is the selected top row's stored representative value and not derived by component profit aggregation.
2. profit binding needs a second selector over raw rows within the selected component.
3. `top_candidate_id` has to be used after component selection to bind representative row/profit.

Do not claim live readiness until representative profit binding is reviewed.

## Next step

Next recommended step:

```text
25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY
```

Suggested goal:

```text
Review 25C93 latest_start / closest_start selector candidate and determine whether it is stable, source-compatible, and whether representative profit/top_candidate_id binding can be recovered without oracle logic.
```

Recommended checks for 25C94:

1. Verify `latest_start` and `closest_start` select identical components for all 125 rows.
2. Produce per-row selected component fields:
   - selected component id
   - component_min_entry
   - component_max_exit
   - component_count
   - unique_origins
   - candidate_ids
   - origin_ids
   - top_candidate_id presence
3. Test representative profit selectors inside the selected component:
   - row with `candidate_id == top_candidate_id`
   - row with `origin_id == top_candidate_id`
   - latest entry row
   - earliest entry row
   - max profit row
   - min profit row
   - row with exact top profit if non-oracle tie-break can identify it
4. Compare selected representative profit against CoreB top `profit` for all 125 rows.
5. If profit binding fails, keep status as historical SOT / live blocked.
6. If profit binding succeeds, still mark human review required before any live evaluator step.

Expected output status names:

If only selector count review passes but profit binding fails:

```text
NON_ORACLE_SELECTOR_COUNT_MATCHED_PROFIT_BINDING_BLOCKED_AUDIT_ONLY_LIVE_BLOCKED
```

If count and profit binding both pass:

```text
NON_ORACLE_SELECTOR_AND_PROFIT_BINDING_CANDIDATE_READY_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

## Existing 25C93 files

Script:

```text
scripts/gold_v2_runtime/audit_gold_v2_25c93_non_oracle_component_selector_audit_only.py
```

BAT:

```text
scripts/gold_v2_runtime/bat/25C93_NON_ORACLE_COMPONENT_SELECTOR_AUDIT_ONLY.bat
```

Spec:

```text
docs/gold_v2/GOLD_V2_25C93_NON_ORACLE_COMPONENT_SELECTOR_AUDIT_ONLY_SPEC_20260608.md
```

Local output directory:

```text
Files/FX_OUTPUTS/gold_v2_25c93_non_oracle_component_selector_audit_only
```

Uploaded output files from 25C93:

```text
25c93_summary.json
25c93_selector_summary.csv
25c93_selector_rows.csv
25c93_best_candidate_matrix.csv
25c93_decision_matrix.csv
25c93_blocker_matrix.csv
GOLD_V2_25C93_NON_ORACLE_COMPONENT_SELECTOR_AUDIT_ONLY_REPORT.md
```

## Exact prompt to paste into next chat

```text
repo: knitanr-a11y/xauusd-signal-lab

Please read and continue from:
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C93_DONE_25C94_NEXT_NON_ORACLE_SELECTOR_REVIEW_AUDIT_ONLY_20260608.md

GOLD V2 remains audit-only.
REQUEST_MORE_AUDIT is not source recovery approval.
Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
Approximate reimplementation is prohibited.
A002 is auxiliary-only and must not be used for CoreB metrics.
Discord / MT5 / AI API / live hook / live evaluator / final signal remain OFF unless explicitly approved.
NO_SIGNAL must not notify Discord.

25C93 found a non-oracle selector candidate:
- component_family = entry_gap
- gap_min = 15
- best selectors = latest_start and closest_start
- same_count/source_rule_count/unique_origins exact = 125/125
- profit_sum exact = 0/125
- status = NON_ORACLE_COMPONENT_SELECTOR_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED

Next step:
25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY

Goal:
Review whether latest_start/closest_start are stable and recover representative profit/top_candidate_id binding without oracle logic. Do not unlock live.
```
