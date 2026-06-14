# NEXT CHAT HANDOFF — GOLD V3 107R6 created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_107R6_PARITY_VERIFIED_RESOLVED_CONTRACT_BUILDER_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

107R5 completed:

```text
status: GOLD_V3_107R5_INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGET_READY_AUDIT_ONLY
decision: INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGETS_READY_FOR_107R6
best_family_rows: 5571
source_distribution_rows: 4
active_patch_target_rows: 4
needs_patch_count: 4
missing_producer_count: 0
```

Patch targets:

```text
atomic_current_107GO: 31 rows, missing exit_dt|source_name
atomic_top_107GN: 266 rows, missing exit_dt|source_name
fixed_diversified_107GD: 109 rows, missing exit_dt|family|source_name|candidate_key_or_global_candidate_key
broad_candidate_107GB: 5165 rows, missing exit_dt|family|source_name|candidate_key_or_global_candidate_key
```

107GB is dominant, with 5165/5571 rows.

## Source review

107GB:

- `one()` resolves TP/SL using M5 but returns only numeric result.
- `eval_cond()` writes `entry_dt`, `entry_month`, `side`, `condition`, `profile_id`, `cooldown_bars`, `result_usd` but not `exit_dt`.

107GN:

- `result_idx()` resolves TP/SL using M5 but returns only numeric result.
- `eval_seed()` writes result ledger rows without `exit_dt`.

Therefore 107R6 creates a separate parity-verified resolved contract builder instead of mutating producer scripts.

## What 107R6 does

107R6:

1. Loads active input ledgers:

```text
107goc/gold_v3_107go_portfolio_ledger.csv
107gnc/gold_v3_107gn_top_candidate_trade_ledger.csv
107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
```

2. Loads exact M15/M5 OHLC:

```text
goldsharp_m15.csv or gold#_m15.csv
goldsharp_m5.csv or gold#_m5.csv
```

3. Recomputes TP/SL result and exit time per row.
4. Accepts rows only if:

```text
abs(recomputed_result_usd - result_usd) <= 1e-8
exit_dt is non-null
exit_dt >= entry_dt
```

5. Writes combined resolved input ledger.
6. Joins it back to 107Q best-family ledger.
7. If coverage is 100%, next is 107S resolved-only health gate replay.

## Files created

```text
docs/gold_v3/GOLD_V3_107R6_PARITY_VERIFIED_RESOLVED_CONTRACT_BUILDER_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_107r6_parity_verified_resolved_contract_builder_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107r6_parity_verified_resolved_contract_builder.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107R6_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_107r6_parity_verified_resolved_contract_builder.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/107r6c/paste_me.txt
```

## Expected outcomes

If full 107Q best coverage and parity pass:

```text
PARITY_VERIFIED_RESOLVED_CONTRACT_READY_FOR_107S
```

If partial:

```text
PARITY_VERIFIED_RESOLVED_CONTRACT_PARTIAL_NEED_PRODUCER_PATCH
```

If missing OHLC/inputs:

```text
PARITY_VERIFIED_RESOLVED_CONTRACT_BLOCKED_INPUT_INCOMPLETE
```

## Hard guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to:

- GOLD V2
- old GOLD
- DISC8
- Stage41 feature-only snapshot as a trading source

Do not mutate:

- source CSVs
- CSV contract
- candidate pool
- Stage45 runtime
- Stage69 runtime
- live evaluator
- live hook
- final signal
- Discord
- MT5 execution
- AI API

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
csv_open_bar_exclusion_required=false
```

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```
