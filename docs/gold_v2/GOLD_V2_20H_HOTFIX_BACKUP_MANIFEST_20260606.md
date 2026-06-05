# GOLD V2 20H hotfix backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: backup manifest before fixing 20H `next_gates()` DataFrame column mismatch.

## Runtime error

The first 20H run failed with:

```text
ValueError: 3 columns passed, passed data had 4 columns
```

Cause:

- `next_gates()` defined DataFrame columns as `next_step`, `purpose`, `allowed_after_20h_success`.
- The 20I row had 4 values: `next_step`, `name`, `purpose`, `allowed_after_20h_success`.
- The other rows had 3 values.

## Verified pre-hotfix file

| role | path | observed blob sha | note |
| --- | --- | --- | --- |
| 20H script before hotfix | `scripts/gold_v2_runtime/audit_gold_v2_20h_value_capture_auth_gate.py` | `f2c32fccba4b19bbf4371288d451a944239f10fe` | Contains the mismatched `next_gates()` table. |

## Hotfix boundary

This hotfix may update only:

- `scripts/gold_v2_runtime/audit_gold_v2_20h_value_capture_auth_gate.py`

This hotfix must not change:

- signal conditions
- candidate sets
- source ledger
- source-of-truth status
- TP/SL
- entry/exit logic
- live evaluator logic
- Discord notification logic
- MT5 order logic
- AI API logic

## Intended fix

Change `next_gates()` to use a consistent 4-column schema:

- `next_step`
- `name`
- `purpose`
- `allowed_after_20h_success`

All rows must contain exactly 4 values.

## Prohibitions retained

The hotfix must not collect a decision value, infer a decision value, approve source recovery, execute source recovery, finalize/recover source identity, promote source-of-truth, run OHLC replay, enable live/final paths, send Discord/NO_SIGNAL Discord, place MT5 orders, or call AI APIs.
