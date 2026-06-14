# GOLD V3 Stage107K Spec — REGIME_BALANCED_ADAPTIVE_SCORE_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107K_REGIME_BALANCED_ADAPTIVE_SCORE_AUDIT_ONLY
```

## Purpose

This stage corrects the direction after Stage107H/107I2 found a strong 2026 May window.

The project goal is not to fit only May 2026. The goal is a flexible GOLD V3 method that can handle materially different regimes:

```text
2025 regime: lower / different volatility structure
2026 regime: higher volatility structure
```

Stage107K therefore evaluates whether the same adaptive score-gate methodology can produce acceptable OOS results in both 2025 and 2026 high-volatility conditions.

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

## Regime windows

The audit must evaluate at least:

```text
REGIME_2025_H2
train: 2025-01-01 to 2025-07-01
test:  2025-07-01 to 2026-01-01
```

```text
REGIME_2026_HIGHVOL_MAYJUN
train: 2025-01-01 to 2026-05-01
test:  2026-05-01 to 2027-01-01
```

Optional if data exists:

```text
REGIME_2026_Q1Q2
train: 2025-01-01 to 2026-01-01
test:  2026-01-01 to 2026-05-01
```

## Method

For each regime window:

1. Use only train period data to create feature-bin score tables.
2. Use only entry-time as-of features.
3. Score OOS entries in that regime.
4. Evaluate score thresholds.
5. Produce per-regime OOS metrics.

Then aggregate by adaptive policy key:

```text
policy_key = tier + base_top_n + score_quantile
```

A policy is useful only if it has acceptable performance in both 2025 and 2026 regimes.

## Gates

Regime pass gate per regime:

```text
OOS WR >= 60%
OOS PF >= 1.50
OOS trades >= 30
```

Strict regime pass gate per regime:

```text
OOS WR >= 65%
OOS PF >= 1.50
OOS trades >= 30
```

Balanced policy gate:

```text
2025 regime pass == true
2026 high-vol regime pass == true
min_regime_wr >= 60%
min_regime_pf >= 1.50
min_regime_trades >= 30
```

Strict balanced policy gate:

```text
2025 strict pass == true
2026 high-vol strict pass == true
```

## Outputs

```text
FX_OUTPUTS/gold_v3/107kc/
```

Mandatory paste file:

```text
FX_OUTPUTS/gold_v3/107kc/paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107K_REGIME_BALANCED_ADAPTIVE_SCORE_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107K_REGIME_BALANCED_ADAPTIVE_SCORE_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
