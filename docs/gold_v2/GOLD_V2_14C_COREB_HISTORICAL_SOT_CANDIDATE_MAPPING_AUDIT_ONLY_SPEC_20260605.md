# GOLD V2 14C CoreB historical SOT candidate mapping audit-only spec

Created: 2026-06-05

## Purpose

14B confirmed that CoreB source top-ledger rows are readable, but live same_count replay remains blocked.

14C creates an audit-only historical SOT candidate mapping for CoreB. This mapping records the exact historical source: RR125 top ledger with `same_count>=15`, but it must not be used as a live trigger.

## Inputs

```text
FX_OUTPUTS/gold_v2_14b_coreb_cluster_source_read_and_replay_audit_only/gold_v2_14b_coreb_cluster_source_read_and_replay_summary.json
FX_OUTPUTS/gold_v2_14b_coreb_cluster_source_read_and_replay_audit_only/gold_v2_14b_coreb_source_top_ledger_target_rows.csv
FX_OUTPUTS/gold_v2_14b_coreb_cluster_source_read_and_replay_audit_only/gold_v2_14b_coreb_source_rule_rows.csv
```

## Checks

```text
14B status is COREB_SOURCE_TOP_LEDGER_READABLE_BUT_LIVE_REPLAY_BLOCKED_AUDIT_ONLY
target rows == 125
source rule rows == 12
CoreB historical SOT allowed == true
CoreB live evaluator allowed == false
final signal allowed == false
external actions false
```

## Outputs

```text
FX_OUTPUTS/gold_v2_14c_coreb_historical_sot_candidate_mapping_audit_only
```

```text
GOLD_V2_14C_COREB_HISTORICAL_SOT_CANDIDATE_MAPPING_AUDIT_ONLY_REPORT.md
gold_v2_14c_input_audit.csv
gold_v2_14c_coreb_historical_sot_candidate_mapping.json
gold_v2_14c_mapping_checks.csv
gold_v2_14c_decision_matrix.csv
gold_v2_14c_blockers.csv
gold_v2_14c_coreb_historical_sot_candidate_mapping_summary.json
```

## Expected status

```text
COREB_HISTORICAL_SOT_CANDIDATE_MAPPING_BUILT_AUDIT_ONLY_LIVE_BLOCKED
```

## Prohibitions

No Discord, no MT5, no AI API, no live hook, no final signal, no CoreB live enablement.
