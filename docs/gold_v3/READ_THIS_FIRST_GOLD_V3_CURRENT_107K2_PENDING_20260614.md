# READ THIS FIRST — GOLD V3 current handoff / 107K2 pending

Created JST: `2026-06-14`

This file is the current reading guide for the next chat.

## Read these files first, in this order

1. `docs/gold_v3/READ_THIS_FIRST_GOLD_V3_CURRENT_107K2_PENDING_20260614.md`
2. `docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107K2_PENDING_REGIME_BALANCED_20260614.md`
3. `docs/gold_v3/NEXT_CHAT_START_PROMPT_GOLD_V3_107K2_PENDING_REGIME_BALANCED_JA_20260614.md`

The user will attach the Stage107K2 result in the new chat:

```text
FX_OUTPUTS/gold_v3/107k2c/paste_me.txt
```

## Do not read / do not use unless explicitly requested

Do not use the following as current source-of-truth for the next step:

- GOLD V2 docs and outputs.
- Old GOLD docs and outputs.
- DISC8 docs and outputs.
- Stage41 feature-only snapshot as trading source.
- Any old handoff that says to continue Stage62–107J/K unless explicitly requested.
- Stage107J output as a successful health-gate result. It was blocked due missing `exit_dt`.
- Stage107K output as a strategy failure. It was blocked by evaluation design (`no_regime_frontier`).

## Current state

Current status for the next chat:

```text
GOLD_V3_107K2_DIRECT_REGIME_BALANCED_ADAPTIVE_SCORE_PENDING_AUDIT_ONLY
```

The next chat must inspect the attached `107k2c/paste_me.txt` first.

## Important interpretation rule

The core goal is not to fit only 2026 May.

The system must handle materially different regimes:

```text
2025 regime: different / lower volatility structure
2026 regime: higher volatility structure
```

Any candidate that works only in 2026 May or only one narrow regime is not enough.

## Hard guardrails

GOLD V3 remains audit-only.

Do not mutate source CSVs, CSV contracts, candidate pools, Stage45 runtime, Stage69 runtime, live evaluator, live hook, final signal, MT5 execution, Discord, or AI API.

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

Resolved-only rule for any health gate:

```text
history may include only outcomes with exit_dt <= current entry_dt
```

No future TP/SL, future exit result, unresolved horizon, future OHLC, or open/incomplete candle may be used at entry time.
