# GOLD V3 Stage107G Spec — DUAL_EDGE_CONDITION_CANDIDATE_DESIGN_AUDIT_ONLY

Created JST: `2026-06-12`

Repo: `knitanr-a11y/xauusd-signal-lab`

Stage:

```text
GOLD_V3_107G_DUAL_EDGE_CONDITION_CANDIDATE_DESIGN_AUDIT_ONLY
```

## Purpose

Stage107G is the first audit stage that designs **new LONG-edge and SHORT-edge entry condition candidates** from OHLC data.

This is different from Stage107F, which only split existing Stage107 ledger rows into LONG/SHORT baselines.

Stage107G must:

```text
1. build live-knowable features from closed OHLC candles only
2. generate LONG-specific entry condition candidates
3. generate SHORT-specific entry condition candidates
4. evaluate them independently without regime arbitration
5. keep a no-regime baseline path
6. optionally evaluate conflict arbitration after both LONG and SHORT edges exist
7. evaluate fixed TP/SL and TP-min-5 / SL=TP/RR candidates where exact M5 data exists
```

## Guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 as a trading source.

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

## Uploaded/exact OHLC sources

Stage107G accepts exact OHLC filenames only. It must not broadly scan MQL5/Files.

Known filenames from the user upload:

```text
gold#_m1.csv
gold#_m5.csv
gold#_m15.csv
gold#_h1.csv
gold#_h4.csv
gold#_d1.csv
goldsharp_m1.csv
goldsharp_m5.csv
goldsharp_m15.csv
goldsharp_h1.csv
goldsharp_h4.csv
goldsharp_d1.csv
```

The user noted that live data and 2025 data may overlap. Stage107G must de-duplicate by timestamp per timeframe and report year coverage.

## Live-only requirement

All candidate conditions must be built from information known at the M15 entry close:

- current and past closed M15 candles;
- H1/H4/D1 bars merged by as-of timestamp;
- rolling indicators computed from past/current closed rows only;
- no future TP/SL result, no future high/low/close, no unresolved horizon result.

Outcome columns are allowed only for post-hoc scoring.

## Initial feature set

At minimum:

```text
M15: ATR14/28, EMA20/50/100, RSI14, ret1/ret4/ret16, candle body/range
H1: ret4, EMA20/50 direction
H4: ret4, EMA20/50 direction
D1: ret3, EMA20/50 direction
Time: hour, weekday
Volatility: ATR rolling median/q70/q85 state
```

## Initial candidate families

LONG-edge condition families may include combinations of:

```text
h4_up
h1_up
m15_uptrend
pullback_long
momentum_long
rsi_low_or_mid
high_vol / non_high_vol
session bucket
```

SHORT-edge condition families may include mirror or independently discovered combinations:

```text
h4_down
h1_down
m15_downtrend
pullback_short
momentum_short
rsi_high_or_mid
high_vol / non_high_vol
session bucket
```

Stage107G must make clear these are audit-generated candidates, not final runtime conditions.

## TP/SL profiles

Fixed profiles:

```text
TP5_SL2.5_RR2_H64
TP10_SL5_RR2_H64
TP15_SL7.5_RR2_H64
TP20_SL10_RR2_H64
```

Volatility/RR profiles:

```text
TP = max(5.0, m15_atr28 * tp_mult)
SL = TP / rr
```

Grid:

```text
tp_mult: 0.50, 0.75, 1.00, 1.25
rr: 1.50, 2.00, 2.50, 3.00
horizon_m15: 64
```

No fixed 5 USD SL floor is allowed.

## Required outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107gc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107gc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107g_input_coverage.csv
gold_v3_107g_feature_coverage.csv
gold_v3_107g_long_edge_candidate_summary.csv
gold_v3_107g_short_edge_candidate_summary.csv
gold_v3_107g_top_edge_candidates.csv
gold_v3_107g_top_candidate_trade_ledger.csv
gold_v3_107g_dual_edge_conflict_audit.csv
gold_v3_107g_blocker_matrix.csv
gold_v3_107g_validation_matrix.csv
gold_v3_107g_summary.json
GOLD_V3_107G_DUAL_EDGE_CONDITION_CANDIDATE_DESIGN_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107G_DUAL_EDGE_CONDITION_CANDIDATE_DESIGN_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107G_DUAL_EDGE_CONDITION_CANDIDATE_DESIGN_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```

Even when BLOCKED, Stage107G must write `FX_OUTPUTS/gold_v3/107gc/paste_me.txt`.

## Non-goals

Stage107G does not approve live trading and does not modify runtime signal conditions.
