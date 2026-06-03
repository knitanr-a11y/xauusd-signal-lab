# GOLD V2 12J_BUILD_COREB_REQUIRED_FEATURE_SNAPSHOT_AUDIT_ONLY specification

Date: 2026-06-04  
Repo: `knitanr-a11y/xauusd-signal-lab`

## 1. Purpose

12I proved that the current file set does not contain any CSV header with CoreB's 38 required predicate fields.

12J builds a **candidate CoreB required feature snapshot** from OHLC CSVs so the feature layer can be audited separately from signal logic.

This is audit-only. It does not create signals and does not permit step 13.

## 2. What 12J protects

12J must not change any CoreA/CoreB/MEDIUM signal condition.

It only creates feature columns with exact names required by:

```text
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json -> mapped_conditions[].field
```

The CoreB rule thresholds, rules, same_count, direction, RR policy, and mapping JSON are not modified.

## 3. Inputs

Default inputs:

```text
configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json
```

OHLC inputs can be passed explicitly:

```text
--m15-csv path\to\M15.csv
--m5-csv path\to\M5.csv
```

If omitted, the script searches under:

```text
Files
repository root
```

for likely M15 and M5 CSVs. The search is audit-only and never treats any row as a signal.

## 4. Output folder

Default:

```text
Files/FX_OUTPUTS/gold_v2_coreb_required_feature_snapshot_audit_only
```

Generated files:

```text
GOLD_V2_COREB_REQUIRED_FEATURE_SNAPSHOT_AUDIT_ONLY_REPORT.md
gold_v2_coreb_required_feature_snapshot_summary.json
gold_v2_coreb_required_feature_snapshot.csv
gold_v2_coreb_required_feature_schema.csv
gold_v2_coreb_feature_build_audit_checks.csv
```

## 5. Candidate feature formulas

12J uses explicit candidate formulas for audit review:

```text
TR = max(high-low, abs(high-prev_close), abs(low-prev_close))
ATR = rolling mean(TR, 14)
ret_N_atr = (close - close.shift(N)) / ATR
abs_ret_N_atr = abs(ret_N_atr)
range_N_atr = (rolling_high_N - rolling_low_N) / ATR
dist_low_N_atr = (close - rolling_low_N) / ATR
dist_high_N_atr = (rolling_high_N - close) / ATR
donch_pos_N = (close - rolling_low_N) / (rolling_high_N - rolling_low_N)
emaP_slope_N_atr = (EMA(P) - EMA(P).shift(N)) / ATR
compression_range_A_B = range_A_atr / range_B_atr
upper_wick_atr = (high - max(open, close)) / ATR
```

For `m5_*` fields, the same formulas are computed on M5 OHLC and then as-of merged onto M15 timestamps.

## 6. Formula status

Because the original CoreB exploration feature-generation code has not yet been identified in the repository, 12J outputs:

```text
feature_formula_status = CANDIDATE_FORMULA_REQUIRES_SOURCE_VERIFICATION
```

This means:

```text
feature headers may become available for preflight
but feature values are not source-of-truth until formula verification is completed
```

## 7. Safety requirements

12J must not:

```text
modify CoreA/CoreB/MEDIUM mapping JSON
create signals
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

## 8. Success condition

12J succeeds if:

```text
policy is audit-only / external actions OFF
CoreB mapping is readable
M15 OHLC is readable
required CoreB fields are extracted
feature snapshot CSV is written
schema CSV is written
```

If M5 OHLC is unavailable, M15 features are still generated and all `m5_*` fields are written as missing/NaN with a blocking note.

## 9. BAT specification

BAT:

```text
scripts\gold_v2_runtime\bat\12J_BUILD_COREB_REQUIRED_FEATURE_SNAPSHOT_AUDIT_ONLY.bat
```

Executed command:

```text
python scripts\gold_v2_runtime\build_gold_v2_coreb_required_feature_snapshot_audit_only.py %*
```

Examples:

```bat
scripts\gold_v2_runtime\bat\12J_BUILD_COREB_REQUIRED_FEATURE_SNAPSHOT_AUDIT_ONLY.bat
scripts\gold_v2_runtime\bat\12J_BUILD_COREB_REQUIRED_FEATURE_SNAPSHOT_AUDIT_ONLY.bat --m15-csv "C:\path\to\goldsharp_m15.csv" --m5-csv "C:\path\to\goldsharp_m5.csv"
```

## 10. Next step after 12J

After 12J, rerun 12I with:

```bat
scripts\gold_v2_runtime\bat\12I_PREFLIGHT_COREB_MAPPED_PREDICATE_FEATURE_COVERAGE_AUDIT_ONLY.bat --feature-csv "<12J output>\gold_v2_coreb_required_feature_snapshot.csv"
```

Even if 12I becomes coverage-ready, final signal remains blocked until CoreA/arbitration/global blockers and feature formula source verification are resolved.
