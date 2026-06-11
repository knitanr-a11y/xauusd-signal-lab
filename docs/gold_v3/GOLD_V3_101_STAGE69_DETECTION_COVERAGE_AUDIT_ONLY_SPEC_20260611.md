# GOLD V3 Stage101 — Stage69 Detection Coverage Audit-Only Spec

Created JST: `2026-06-11`

Stage name:

`GOLD_V3_101_STAGE69_DETECTION_COVERAGE_AUDIT_ONLY`

READY status:

`GOLD_V3_101_STAGE69_DETECTION_COVERAGE_READY_AUDIT_ONLY`

## Purpose

Stage100 proved the latest closed M15 row had zero condition candidates in all 128 replay points.

Stage101 checks whether Stage69 condition detection itself is active by reading each Stage99 replay folder and summarizing:

- Stage69 total detected condition rows,
- Stage51 rows,
- Stage51 missing detection count,
- latest candidate rows,
- last detected condition timestamp before/asof,
- distance from replay asof to last detected condition,
- candidate label counts from detected condition files.

## Important distinction

Stage100 answers:

```text
Was there a candidate on the latest replay candle?
```

Stage101 answers:

```text
Was Stage69 detecting any candidates at all near the replay window?
```

## Safety

Audit-only. Reads Stage99 replay outputs only. No MT5, Discord, AI API, live hook, live evaluator, final signal, source CSV mutation, or candidate pool mutation.
