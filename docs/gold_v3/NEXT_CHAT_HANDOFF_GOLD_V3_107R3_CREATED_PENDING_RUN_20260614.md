# NEXT CHAT HANDOFF — GOLD V3 107R3 created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_107R3_EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

107R2 completed:

```text
status: GOLD_V3_107R2_EXIT_DT_SOURCE_INTELLIGENCE_READY_AUDIT_ONLY
decision: EXIT_DT_SOURCE_INTELLIGENCE_RECONSTRUCTION_PLAN_READY
best_family_rows: 5571
exact_exit_dt_source_count: 19
shared_column_source_count: 19
candidate_key_diagnostic_rows: 189
strict_join_pass_count: 0
resolved_rows: 0
```

This means exact `exit_dt` sources exist and share columns, but literal-column joins did not produce strict full coverage.

The best observed diagnostics were entry_dt-only and insufficient:

```text
selected_rows: 5571
selected_unique_keys(entry_dt): 453
selected_duplicate_keys(entry_dt): 5118
coverage: about 11.34%
strict_join_pass: false
```

## What 107R3 does

107R3 attempts one final safe join reconstruction before requiring a new resolved source ledger.

It uses alias-aware normalized columns, for example:

```text
side: side, direction, trade_side, candidate_side, signal_side, portfolio_side
profile_id: profile_id, profile, tp_sl_profile, tp_sl_profile_id, risk_profile
family: family, rule_family, candidate_family
condition: condition, rule_condition, candidate_condition
candidate_key: candidate_key, rule_key, strategy_key, global_candidate_key
result_usd: result_usd, pnl_usd, profit_usd, net_usd
score: score, ledger_score, feature_score
```

It then attempts synthetic-key joins between:

```text
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_best_family_trade_ledger.csv
```

and the 107R2 exact `exit_dt` sources.

A join only passes if:

```text
coverage == 100%
non_null_exit_dt == selected_rows
exit_dt >= entry_dt for all rows
source duplicate key count == 0
```

## Files created

```text
docs/gold_v3/GOLD_V3_107R3_EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_107r3_exit_dt_alias_synthetic_key_reconstruction_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107r3_exit_dt_alias_synthetic_key_reconstruction.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107R3_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_107r3_exit_dt_alias_synthetic_key_reconstruction.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/107r3c/paste_me.txt
```

## If 107R3 blocks

Do not keep trying arbitrary joins.

The next required action is to generate or expose a resolved source ledger from the same TP/SL outcome resolution process that created `result_usd`, with this contract:

```text
entry_dt
exit_dt
side
result_usd
profile_id
candidate_key or global_candidate_key
family
condition
source_name
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
