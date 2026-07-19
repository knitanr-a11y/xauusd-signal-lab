# Stage M6B — Alert Function Context Map Contract

Status: `MOCHIPOYO_M6B_ALERT_FUNCTION_CONTEXT_MAP_AUDIT_ONLY`

## Purpose

Stage M6B identifies the market contexts in which a received Mochipoyo alert
expanded favorably, expanded only after material adverse movement, failed to
expand, or reached the source EXIT with a positive/negative result.

This is the first context-map stage toward an independent selection layer. It
is not a trading gate and does not approve automatic orders.

## Source identity and chart labels

Webhook/SQLite source event IDs are the authoritative event identity.

A repeated same-direction alert remains a separate `REENTRY_ALERT` even when
the TradingView script intentionally keeps the original label position and
does not draw or redraw a label for the repeated notification.

Therefore:

- chart label movement/redraw is not required to detect a reentry
- chart label absence does not mean that no repeated notification occurred
- reentry time and identity come from the immutable webhook/SQLite row
- no estimated chart time is substituted for a stored webhook timestamp

## Entry-time context only

A/B/C context classes are assigned using only the Stage M5 snapshot attached
to the source entry alert. M6A outcomes are not available to the context-class
function.

The stored invariant is:

```text
outcome_used_for_context_class = 0
```

The following entry-time dimensions are used:

- H1/H4/D1 EMA20/30/40 directional state
- M15 MACD 6/13/4 histogram direction
- M5 RCI9/14 pullback or chasing extreme
- M15 close position within the preceding 20-bar range
- primary versus reentry source role
- Japanese-time six-hour observation block

EMA alignment is a classification input, not a mandatory rejection rule.
RCI, MACD, and EMA are not all required simultaneously.

## Fixed provisional classes

### A_CONTINUATION_CONTEXT

Primary alert where:

- at least two of H1/H4/D1 EMA stacks align with the alert direction
- M15 MACD is not opposed
- M15 is not at the directional chasing outer quarter

### B_WAIT_OR_REVERSAL_CONTEXT

Primary alert where at least one of the following is true:

- at least two of H1/H4/D1 EMA stacks oppose the alert direction
- M15 MACD opposes the alert direction
- M15 price is at the directional chasing outer quarter

This label means that later research should test a delayed M5 confirmation. It
does not itself authorize or reject an entry.

### C_REENTRY_CONTEXT

Any independently received same-direction `REENTRY_ALERT`. Its higher-timeframe
and lower-timeframe context remains stored for later subdivision.

### UNCLASSIFIED_CONTEXT

Primary alert that does not satisfy the fixed A or B definitions.

These definitions are fixed before reading M6A outcomes and are not optimized
against the current 22 resolved entries.

## Function outcome labels

M6A post-entry data is used only after the context class has been assigned.

The fixed descriptive threshold is one entry-time M5 ATR14:

- `CLEAN_EXPANSION`: MFE >= 1.0 ATR and MAE <= 1.0 ATR
- `VOLATILE_EXPANSION`: MFE >= 1.0 ATR and MAE > 1.0 ATR
- `NO_EXPANSION`: MFE < 1.0 ATR
- `OPEN_UNRESOLVED`: source episode has no EXIT yet

The source EXIT is recorded separately:

- `POSITIVE_EXIT`
- `NONPOSITIVE_EXIT`
- `OPEN_UNRESOLVED`

This separation allows the audit to distinguish:

1. an alert that never expanded
2. an alert that expanded but required large adverse tolerance
3. an alert that expanded but gave back profit before the source EXIT
4. an alert that expanded cleanly and retained profit at the source EXIT

## Cohorts

Descriptive cohorts are generated for:

- ticker
- direction
- primary/reentry role
- A/B/C/unclassified context
- higher-timeframe EMA context
- M15 MACD context
- M5 RCI context
- M15 range-location context
- JST observation block
- ticker/direction/role/context composite

Every cohort is marked with sample status:

- fewer than 5 resolved rows: `VERY_SMALL_SAMPLE`
- 5–19 resolved rows: `SMALL_SAMPLE`
- 20 or more resolved rows: `OBSERVATIONAL_SAMPLE`

No cohort is an approved rule at this stage.

## Safety and immutability

M6B may rebuild only:

- `alert_function_contexts`
- `alert_function_cohorts`
- `alert_function_context_build_runs`

It must not modify:

- `raw_alerts`
- `episodes` or `episode_events`
- `mt5_alignment`
- `feature_snapshots`
- `virtual_entries`
- `outcomes`
- `outcome_path_metrics`
- MT5 CSV files

The following remain OFF:

```text
entry_gate = false
automatic_trading_rule_approved = false
discord_send = false
mt5_order = false
live_ready = false
final_signal = false
```

If Stage M3, M5, or M6A is stale, M6B fails before replacing the prior
successful context map.
