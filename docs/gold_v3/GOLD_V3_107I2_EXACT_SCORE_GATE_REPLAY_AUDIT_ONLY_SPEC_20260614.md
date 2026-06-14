# GOLD V3 Stage107I2 Spec — EXACT_SCORE_GATE_REPLAY_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107I2_EXACT_SCORE_GATE_REPLAY_AUDIT_ONLY
```

## Purpose

Stage107I detected a large mismatch:

```text
source_oos_trades: 63
rehydrated_trades: 828
metric_match_trades: false
```

This means the Stage107I replay was not reproducing the same Stage107H gate. The likely cause is that Stage107I reused feature-bin scores by only `split/tier/base_top_n`, so duplicate bin sets from multiple 107H frontier rows could be applied together and inflate feature scores.

Stage107I2 fixes this by not reusing the persisted bin table for replay. Instead, for each selected 107H frontier row, it rebuilds the train-only bins from the same train universe and applies the exact stored threshold.

## Guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 as trading sources.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime behavior, Stage69 runtime behavior, live evaluator, final signal, Discord, MT5 execution, or AI API.

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
open/as-of treatment is forbidden
```

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```

## Inputs

```text
FX_OUTPUTS/gold_v3/107hc/gold_v3_107h_score_frontier.csv
FX_OUTPUTS/gold_v3/107guc/gold_v3_107gu_selected_candidate_keys.csv
```

Exact candidate ledgers and exact OHLC files are loaded again. No broad scans.

## Method

1. Load 107H score frontier.
2. Select primary_65 rows first.
3. Load exact candidate ledgers and OHLC features.
4. For each candidate row:
   - rebuild the train universe from split/tier/base_top_n
   - rebuild feature bins from train only
   - score OOS rows with rebuilt bins
   - apply the stored score threshold
   - compare with source metrics
5. Evaluate primary 65 and concentration gates.

## Outputs

```text
FX_OUTPUTS/gold_v3/107i2c/
```

Mandatory paste file:

```text
FX_OUTPUTS/gold_v3/107i2c/paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107I2_EXACT_SCORE_GATE_REPLAY_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107I2_EXACT_SCORE_GATE_REPLAY_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
