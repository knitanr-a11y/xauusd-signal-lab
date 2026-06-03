# GOLD V2 12I_PREFLIGHT_COREB_MAPPED_PREDICATE_FEATURE_COVERAGE_AUDIT_ONLY specification

Date: 2026-06-03  
Repo: `knitanr-a11y/xauusd-signal-lab`

## 1. Purpose

12I runs after 12H.

12H confirms:

```text
CoreB = MAPPING_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED
CoreB unmapped_condition_count = 0
CoreB mapped_rule_count = 33
CoreB mapped_condition_count = 181
CoreA/MEDIUM/global blockers remain
```

12I checks whether CoreB's mapped predicate fields are present in available feature/data CSV headers.

This is a preflight audit only. It does not emit signals and does not evaluate trading eligibility.

## 2. Inputs

Default inputs:

```text
configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json
```

Optional feature input:

```text
--feature-csv path\to\feature_file.csv
```

If `--feature-csv` is omitted, 12I searches candidate CSV files under:

```text
Files/FX_OUTPUTS
```

The search is header-only. It does not treat any row as a signal.

## 3. Output folder

Default:

```text
Files/FX_OUTPUTS/gold_v2_coreb_mapped_predicate_feature_coverage_preflight_audit_only
```

Generated files:

```text
GOLD_V2_COREB_MAPPED_PREDICATE_FEATURE_COVERAGE_PREFLIGHT_AUDIT_ONLY_REPORT.md
gold_v2_coreb_mapped_predicate_feature_coverage_preflight_summary.json
gold_v2_coreb_required_predicate_fields.csv
gold_v2_coreb_candidate_feature_file_coverage.csv
gold_v2_coreb_selected_feature_field_coverage.csv
gold_v2_coreb_missing_feature_fields.csv
gold_v2_coreb_feature_coverage_audit_checks.csv
```

## 4. Required-field extraction

12I extracts exact field names from:

```text
live_evaluator_mapping_coreB_20260603.json -> mapped_conditions[].field
```

No aliasing or approximate matching is allowed.

For example, `m5_ret_4_atr` must exist exactly as `m5_ret_4_atr`. It must not be accepted as `ret_4_atr`, `M5_ret_4_atr`, or any other approximation.

## 5. Coverage status

Possible output statuses:

```text
COREB_PREDICATE_FEATURE_COVERAGE_READY_AUDIT_ONLY
COREB_PREDICATE_FEATURE_COVERAGE_BLOCKED_MISSING_FIELDS
COREB_PREDICATE_FEATURE_COVERAGE_BLOCKED_NO_FEATURE_DATA
COREB_PREDICATE_FEATURE_COVERAGE_BLOCKED_POLICY_OR_MAPPING
```

Even if status is READY, final signal remains blocked.

## 6. Non-negotiable guards

12I must not:

```text
modify mapping JSON
create final signals
connect step 13
use historical entry_time matches as signals
send Discord notifications
place MT5 orders
call AI API
call live hooks
notify on NO_SIGNAL
```

Expected safety fields:

```text
live_evaluator_connection_allowed=false
final_signal_allowed=false
step13_allowed=false
notification_should_send=false
```

## 7. BAT specification

BAT:

```text
scripts\gold_v2_runtime\bat\12I_PREFLIGHT_COREB_MAPPED_PREDICATE_FEATURE_COVERAGE_AUDIT_ONLY.bat
```

Executed command:

```text
python scripts\gold_v2_runtime\preflight_gold_v2_coreb_mapped_predicate_feature_coverage_audit_only.py %*
```

Examples:

```bat
scripts\gold_v2_runtime\bat\12I_PREFLIGHT_COREB_MAPPED_PREDICATE_FEATURE_COVERAGE_AUDIT_ONLY.bat
scripts\gold_v2_runtime\bat\12I_PREFLIGHT_COREB_MAPPED_PREDICATE_FEATURE_COVERAGE_AUDIT_ONLY.bat --feature-csv "C:\path\to\features.csv"
```

Exit codes:

| Code | Meaning |
|---:|---|
| 0 | Audit completed and outputs were written. |
| 2 | Policy/mapping unsafe or unreadable. |
| other | Unexpected runtime error. |

## 8. Next step after 12I

If all CoreB predicate fields are present, CoreB can move to a deeper non-signal dry-run evaluator preflight.

If fields are missing, the next step is to fix feature generation/schema mapping, not to approximate field names.

Do not connect step 13 while CoreA/arbitration/global blockers remain.
