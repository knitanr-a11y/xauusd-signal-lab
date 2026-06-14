# NEXT CHAT HANDOFF — GOLD V3 109B created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_109B_LOSS_FEATURE_FINGERPRINT_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

109 completed READY:

```text
selected_option: KEEP_107Q_BASE
selected_policy_key: 107Q_BASE_RESOLVED_PASS_THROUGH
health_gate_adopted: false
trades: 5571
win_rate: 0.6372285047567762
profit_factor: 3.129035220079588
sum_result_usd: 18065.748437500006
negative_month_count: 0
```

User asked whether we can reduce losses by finding entry-time features that appear frequently in losing trades.

## What 109B does

109B mines the selected base policy ledger for loss-heavy entry-time features.

It reads:

```text
FX_OUTPUTS/gold_v3/109c/gold_v3_109_selected_base_policy_ledger.csv
FX_OUTPUTS/gold_v3/109c/gold_v3_109_summary.json
```

It writes:

```text
gold_v3_109b_loss_feature_overview.csv
gold_v3_109b_boolean_categorical_loss_profile.csv
gold_v3_109b_numeric_bin_loss_profile.csv
gold_v3_109b_candidate_filter_diagnostics.csv
gold_v3_109b_top_loss_patterns.csv
gold_v3_109b_recommended_next_actions.csv
```

## Important safety rule

109B must not use future/outcome columns as filter features.

Forbidden as filter features:

```text
result_usd
recomputed_result_usd
result_delta
exit_dt
exit_price
exit_reason
result_parity_pass
health_gate_*
selected_option
stage109_selection_reason
any column beginning with exit_
any column containing result, win, loss, pnl, profit, parity
```

All candidate filters are:

```text
posthoc_diagnostic_only: true
requires_train_only_revalidation: true
final_rule_approval: false
live_ready: false
```

## Files created

```text
docs/gold_v3/GOLD_V3_109B_LOSS_FEATURE_FINGERPRINT_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_109b_loss_feature_fingerprint_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_109b_loss_feature_fingerprint.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_109B_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_109b_loss_feature_fingerprint.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/109bc/paste_me.txt
```

## Expected decision

If posthoc loss-heavy filters exist:

```text
LOSS_FEATURE_FINGERPRINT_READY_FOR_109C_TRAIN_ONLY_REPLAY
```

If no strong patterns:

```text
LOSS_FEATURE_FINGERPRINT_NO_ACTIONABLE_PATTERN_KEEP_109_BASE
```

## If ready for 109C

Create 109C to validate top filters using train-only / walk-forward selection. Do not adopt 109B filters directly.

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
