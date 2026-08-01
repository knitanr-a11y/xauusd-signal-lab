# GOLD Late Transition V1 — trust re-audit and runtime block

Date: 2026-08-01

## Formal correction

The Challenger GitHub runtime is **BLOCKED_NOT_ACTIVATION_READY**.

Repeated user-PC failures occurred before Challenger bootstrap activation:

- ZIP bad magic
- packaged payload SHA256 mismatch
- Base64 padding failure
- UTF-8 source SHA256 mismatch

These incidents invalidate prior claims that the Challenger user-PC delivery was fully verified. Challenger bootstrap and both Challenger loops must not be run until a new implementation has been verified from an actual Windows checkout.

The existing frozen V19 runtime and notifier are not modified or stopped.

## Historical result re-audit

Historical performance was re-run from the raw M1 CSV union and the frozen `SEMIANNUAL_EXPANDING` router/wave decision ledger using two separate sequential implementations:

1. the archived independent runtime replay;
2. a newly written minimal replay that did not import the archived runtime implementation.

Both reproduced:

- candidate event onsets: 184
- Challenger resolved trades: 123
- Challenger PF: 1.9467405272114702
- Challenger net: +545.19
- Challenger exit-order DD: 70.00
- V19 resolved trades: 169
- V19 PF: 2.0299563195716415
- V19 net: +730.96
- V19 exit-order DD: 80.00
- combined trades: 292
- combined PF: 1.992680232739033
- combined net: +1,276.15
- combined exit-order DD: 60.22

The archived replay also re-passed 5/5 checkpoint restart tests and 4/4 no-backfill recovery tests.

## Interpretation

This re-audit supports that the historical arithmetic and sequential replay are reproducible from the supplied raw data and frozen decision ledger. It does **not** prove prospective profitability. The candidate remains retrospectively discovered and selection-biased.

Historical research evidence and GitHub runtime readiness are separate claims:

- historical replay: reproduced;
- prospective user-PC runtime: blocked and not trusted yet.
