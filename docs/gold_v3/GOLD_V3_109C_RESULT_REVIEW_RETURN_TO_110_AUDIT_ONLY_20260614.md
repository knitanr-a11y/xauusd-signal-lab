# GOLD V3 109C Result Review — return to Stage110 audit monitoring

Created JST: `2026-06-14`

Stage reviewed:

```text
GOLD_V3_109C_TRAIN_ONLY_LOSS_FEATURE_FILTER_REPLAY_AUDIT_ONLY
```

## 109C result

```text
status: GOLD_V3_109C_TRAIN_ONLY_LOSS_FEATURE_FILTER_REPLAY_READY_AUDIT_ONLY
decision: TRAIN_ONLY_LOSS_FEATURE_FILTER_NOT_CONFIRMED_KEEP_109_BASE
ready: true
live_ready: false
train_only_selection: true
final_rule_approval: false
blocker_count: 0
```

## Key metrics

```text
ledger_rows: 5571
feature_universe_rows: 40
combo_rows: 4
best_combo_key: L50_T5
best_primary_gate: false
best_review_gate: false
```

Best combo:

```text
lookback_active_days: 50
target_active_days: 5
fold_count: 10
base_trades: 2786
base_wr: 0.6600861450107681
base_pf: 3.250861829674625
base_sum: 9732.55120535715
kept_trades: 1988
kept_wr: 0.6634808853118712
kept_pf: 3.274037510419948
kept_sum: 6651.048973214289
retention: 0.7135678391959799
wr_gain: 0.003394740301103094
pf_gain: 0.023175680745322946
sum_delta: -3081.5022321428605
```

## Interpretation

The loss-feature idea improved WR/PF slightly in the best train-only combo, but not enough to pass gates:

```text
primary_wr_gain_ge_0_5pct: FAIL
primary_pf_ge_base: PASS
primary_retention_ge_70: PASS
primary_sum_ge_base: FAIL
```

The key failure is large forward sum reduction:

```text
sum_delta: -3081.5022321428605
```

Therefore loss-feature filtering is **not confirmed** and should not replace Stage109 base policy.

## Surviving feature families

109C still found repeated feature families worth noting for future research, but not adoption:

```text
h1_range_atr >=
m15_dist_atr >=
entry_price <=
h4_atr28 >=
h1_atr28 <=
d1_rsi14 <=
d1_atr28 >=
m15_atr28 >=
h1_atr28 >=
m15_rsi14 <=
```

These are research leads only.

## Confirmed selected policy remains

```text
selected_option: KEEP_107Q_BASE
selected_policy_key: 107Q_BASE_RESOLVED_PASS_THROUGH
health_gate_adopted: false
loss_feature_filter_adopted: false
```

## Next stage

Return to the previously-created Stage110:

```text
GOLD_V3_110_AUDIT_MONITORING_DESIGN
```

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_110_audit_monitoring_design.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/110c/paste_me.txt
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
