# GOLD V2 25B4 CoreB same_count replay plan audit spec

Date: 2026-06-07
Step: `25B4_COREB_SAME_COUNT_REPLAY_PLAN_AUDIT_ONLY`
Mode: audit-only replay planning, no replay execution

## 1. Purpose

25B3 confirmed that the six priority CoreB source shortlist files are present and readable.

25B4 freezes the replay contract for a later CoreB same_count parity attempt, without executing that attempt.

25B4 must only define:

```text
which inputs are allowed
which rows/columns are required
which keys must be used for matching
which parity gates must pass
which methods are forbidden
which later script would be needed if human review accepts the source evidence
```

25B4 must not compute CoreB live signals, recompute `same_count`, infer `cluster_id`, create membership, fit to SOT rows, or enable any live/final/external action.

## 2. Source-of-truth inputs

25B4 reads only 25B3 outputs:

```text
Files/FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_coreb_source_shortlist_content_summary.json
Files/FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_shortlist_file_content_audit.csv
Files/FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_csv_profile.csv
Files/FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_json_profile.csv
Files/FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_json_key_inventory.csv
Files/FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_coreb_source_linkage_matrix.csv
Files/FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_unblock_gap_matrix.csv
```

Expected from the uploaded 25B3 run:

```text
shortlist_rows = 6
profiled_csv_files = 2
profiled_json_files = 4
raw_signal_ledger_rows = 16875
target_top_ledgers_rows = 2811
source_universe_rule_count = 33
selected_rule_count = 12
same_count_min = 15
entry_logic = selected_rule_hit AND same_count_source_hit_count >= 15
```

## 3. Output folder

```text
Files/FX_OUTPUTS/gold_v2_25b4_coreb_same_count_replay_plan_audit_only/
```

## 4. Required outputs

```text
GOLD_V2_25B4_COREB_SAME_COUNT_REPLAY_PLAN_AUDIT_ONLY_REPORT.md
gold_v2_25b4_input_audit.csv
gold_v2_25b4_replay_input_contract.csv
gold_v2_25b4_replay_algorithm_contract.csv
gold_v2_25b4_target_key_contract.csv
gold_v2_25b4_parity_gate_matrix.csv
gold_v2_25b4_forbidden_methods.csv
gold_v2_25b4_execution_blockers.csv
gold_v2_25b4_next_step_contract.csv
gold_v2_25b4_coreb_same_count_replay_plan_summary.json
```

## 5. Replay contract to freeze, not execute

The later replay candidate, if authorized, must be based on:

```text
raw signal ledger: rr125_raw_signal_ledger.csv
selected rules: frozen_coreB_rr125_source_rule_conditions_20260603.json or linked selected config
same_count source universe: frozen_coreB_same_count_source_universe_20260604.json
combined evaluator definition: frozen_coreB_combined_evaluator_definition_20260604.json
target-only ledger: rr125_top_ledgers.csv
final portfolio CoreB target: 125 CoreB rows, if later included as a target check
```

The later replay candidate must preserve:

```text
direction = BUY
rr = 1.25
same_count_min = 15
entry_logic = selected_rule_hit AND same_count_source_hit_count >= 15
no entry_time history reuse
no historical same_count live reuse
```

## 6. Required later parity gates

A later execution step cannot unblock CoreB unless all relevant gates pass:

```text
raw ledger sha/path contract matches 25B3
selected rule count matches 12
same_count source universe count matches 33
required field coverage is complete
candidate generated top ledger row/key parity is proven against target top ledger, if target top ledger is used
final CoreB target rows = 125 are reproduced, if final SOT target is used
missing replay keys = 0
extra replay keys = 0
same_count exact match rows = 125 or target-selected denominator
cluster_id/membership exact match rows = 125 if cluster_id remains part of source truth
no fitting/approximation/static-window/raw-count/substitution is used
```

## 7. Forbidden methods

25B4 and any later replay must not use:

```text
post-hoc fitting to final SOT rows
static time windows pretending to be same_count
raw entry_time counts pretending to be same_count
interval cover counts pretending to be same_count
connected components pretending to be original cluster membership
feature-rule hit count substituted for source same_count
manual cluster_id assignment after seeing target rows
old GOLD/DISC8 artifacts
Discord/MT5/AI/live hook/final signal during audit-only steps
```

## 8. Stop condition

25B4 stops if:

```text
any required 25B3 file is missing
25B3 status is not completed
25B3 total_stop_rows != 0
25B3 indicates any replay/source mutation/live/external action happened
required 25B3 source roles are missing
required constants cannot be read from 25B3 profiles/key inventory
```

## 9. Success condition

25B4 succeeds when the replay plan is fully written and all safety flags remain off.

Expected success status:

```text
COREB_SAME_COUNT_REPLAY_PLAN_READY_AUDIT_ONLY_EXECUTION_BLOCKED
```

CoreB remains blocked after 25B4.

## 10. Next step after 25B4

Only after human acceptance of the source evidence and the 25B4 plan, the next safe step would be:

```text
25B5_COREB_SAME_COUNT_REPLAY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY
```

25B5 must still be dry-run/audit-only and must not enable live/final/external actions.
