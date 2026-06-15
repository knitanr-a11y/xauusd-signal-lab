# GOLD V3 122 REGENERATE 107L THEN JUNE 01-15 AUDIT REPORT

Created JST: `2026-06-15`

## Reason

Stage121 showed that OHLC reaches the target date but the 107L ledger is stale.

```text
observed_ohlc_max_dt: 2026-06-15 06:45:00
observed_107l_max_dt: 2026-06-05 15:15:00
```

## Added BAT

```text
scripts/gold_v3_runtime/bat/run_gold_v3_122_regenerate_107l_then_june_01_15_audit.bat
```

## Chain

```text
[1/8] Working directory set
[2/8] Rebuild Stage107L from current Stage107K2 inputs
[3/8] Rebuild Stage107M from refreshed Stage107L
[4/8] Shadow rerun Stage117J from refreshed 107L and 107M
[5/8] Rebuild Stage117L F002 removed detail
[6/8] Rebuild Stage117M review-only restore comparison
[7/8] Run Stage119 period audit through 2026-06-15
[8/8] Output location
```

## Local run command

```bat
scripts\gold_v3_runtime\bat\run_gold_v3_122_regenerate_107l_then_june_01_15_audit.bat
```

## Interpretation

If Stage122 still blocks with:

```text
upstream_107l_does_not_reach_required_target
```

then Stage107K2 itself is stale. In that case, regenerate the 107K2 upstream chain before judging June 01-15.

## Safety flags

```text
audit_only: true
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
candidate_pool_removed: false
f002_exclusion_bypassed: false
period_restore_auto_adopted: false
```
