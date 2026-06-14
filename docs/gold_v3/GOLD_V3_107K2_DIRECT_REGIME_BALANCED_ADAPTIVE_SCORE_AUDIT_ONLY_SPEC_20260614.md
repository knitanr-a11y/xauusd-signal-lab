# GOLD V3 Stage107K2 Spec — DIRECT_REGIME_BALANCED_ADAPTIVE_SCORE_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107K2_DIRECT_REGIME_BALANCED_ADAPTIVE_SCORE_AUDIT_ONLY
```

## Purpose

Stage107K was BLOCKED with `no_regime_frontier` because it looked for new regime split names inside an older config file. That is not a strategy failure; it is an evaluation design error.

Stage107K2 fixes this by directly projecting the existing Stage107 candidate key bank into separate regime windows:

```text
2025 regime
2026 Q1/Q2 regime
2026 high-vol regime
```

No May-only selection is allowed.

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
FX_OUTPUTS/gold_v3/107guc/gold_v3_107gu_selected_candidate_keys.csv
```

Exact candidate ledgers and exact OHLC files are loaded via the Stage107H helper.

## Regime windows

```text
REGIME_2025_H2
train: 2025-01-01 to 2025-07-01
test:  2025-07-01 to 2026-01-01
```

```text
REGIME_2026_Q1Q2
train: 2025-01-01 to 2026-01-01
test:  2026-01-01 to 2026-05-01
```

```text
REGIME_2026_HIGHVOL_MAYJUN
train: 2025-01-01 to 2026-05-01
test:  2026-05-01 to 2027-01-01
```

## Method

1. Build candidate groups from Stage107GU selected candidate keys by `tier + top_n`.
2. For each regime, train feature-bin scores only from that regime's train period.
3. Apply score thresholds to that regime's test period.
4. Evaluate per-regime performance.
5. Aggregate policies across 2025 and 2026 high-vol windows.

## Gates

Balanced 60 gate:

```text
2025 pass WR >= 60%, PF >= 1.50, trades >= 30
2026 high-vol pass WR >= 60%, PF >= 1.50, trades >= 30
```

Balanced 65 gate:

```text
2025 pass WR >= 65%, PF >= 1.50, trades >= 30
2026 high-vol pass WR >= 65%, PF >= 1.50, trades >= 30
```

## Outputs

```text
FX_OUTPUTS/gold_v3/107k2c/
```

Mandatory paste file:

```text
FX_OUTPUTS/gold_v3/107k2c/paste_me.txt
```
