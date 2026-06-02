# GOLD legacy quarantine

Created: 2026-06-02
Status: legacy / forensic only

## Purpose

This folder marks prior GOLD/XAUUSD documentation as quarantined after discovery of a critical higher-timeframe timestamp interpretation risk.

The repository may still contain old GOLD documents in `docs/` and other folders. They are not deleted here because they are useful evidence for tracing how the system changed. However, they must not be used as implementation source of truth.

## Rule

Any GOLD document, handoff, postmortem, audit spec, AI-tag design, numeric-gate design, demo-runtime design, or operational manifest note created before GOLD V2 revalidation is considered:

```text
LEGACY_FORENSIC_ONLY
NOT_IMPLEMENTATION_SOT
NOT_RUNTIME_AUTHORITY
NOT_DISPATCH_AUTHORITY
```

## Why

MT5 candle timestamps are open times. A prior static-rule run claimed no higher-timeframe future use using `close_time <= M15 close_time`, but if the stored source timestamp is candle open time, the correct confirmation check must add the timeframe duration:

```text
H1 open_time + 1h <= M15 eval_time
H4 open_time + 4h <= M15 eval_time
D1 open_time + 1d <= M15 eval_time
```

Therefore, prior performance tables and DISC rules must be revalidated before any GOLD demo/live use.

## Canonical replacement document

Use this as the new starting point:

```text
docs/gold_v2/GOLD_V2_START_HERE_AFTER_HTF_OPEN_TIME_BUG_20260602.md
```

## Prohibited use of legacy documents

Do not use legacy documents to justify:

- enabling dispatch_ready
- sending Discord alerts for GOLD autotrade
- sending MT5 orders
- selecting DISC8 membership
- trusting AI tag gates
- trusting numeric gates
- trusting win rate / PF / TotalR
- claiming HTF no-future safety

## Required next step

Run a GOLD V2 open-time HTF audit against the uploaded static rule ledger and only then decide which GOLD strategy documentation should be rebuilt.
