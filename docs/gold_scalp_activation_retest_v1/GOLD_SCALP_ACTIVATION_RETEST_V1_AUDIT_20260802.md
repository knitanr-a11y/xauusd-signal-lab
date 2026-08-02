# GOLD SCALP ACTIVATION / RETEST V1 — Consolidated Audit

Date: 2026-08-02  
Formal status: **`RETROSPECTIVE_ACTIVATION_RETEST_FIVE_VECTOR_COMPLETE_PROVISIONAL_VOLUME_ABSORPTION_PARTIAL_EXIT_CATALOG_LEAD_NO_DEPLOYMENT`**

## Contract

- Existing GOLD candle data only.
- MT5 broker-server naive time and closed rows only.
- Setup events are not entries.
- Exact M1 activation, retest, confirmation, entry and outcome resolution.
- Spread 0.30 USD once.
- Initial SL no greater than 5 USD.
- TP no lower than 5 USD.
- Protective-stop-first same-M1 handling.
- One-position non-overlap.

## Vector A — broad activation/retest layer

170,664 structural setup rows were passed through 138 frozen state-machine contracts. Four modes were tested: frozen-level reclaim follow, favorable-extreme pullback resume, pre-activation failure fade, and post-activation collapse fade. The generated ledger contained 4,176,176 entry rows and 3,864 event/side/mode/parameter components.

Pseudo-forward profile results:

- CATALOG: 922 trades, WR 34.27%, PF 0.9724, net -70.44, median 22/month.
- BALANCED: 1,376 trades, WR 35.25%, PF 0.9644, net -138.13, median 45/month.
- BROAD: 2,012 trades, WR 36.13%, PF 1.0060, net +33.02, DD 334.69, median 68/month.

No broad portfolio passed.

## Vector B — volume-absorption quality layer

A post-result exploratory study isolated the recurring VOLUME_ABSORPTION SHORT activation/retest family and tested activation speed, retest duration, confirmation body fraction, entry overshoot and confirmation volume. Allowing all original exits produced 81–92 trades, PF 1.56–1.64 and net about +140, but WR remained 44–46%. Every selected exit was TP10/SL5.

## Vector C — partial exits added to the full exit menu

Four partial exits were added. The historical selector still chose full TP10/SL5 in every opened block, so the result was materially unchanged.

## Vector D — partial-only specialist

The exit menu was then restricted before the rerun to staged exits. The dominant policy was:

- close 50% at +5 USD;
- move the remaining 50% stop to breakeven;
- close the remainder at +10 USD;
- initial SL 5 USD;
- horizon 240 minutes.

Results:

- CATALOG: 60 trades, WR 60.00%, PF 1.6181, net +74.17, DD 23.33, median 2/month.
- BALANCED: 74 trades, WR 58.11%, PF 1.4785, net +74.17, DD 25.00, median 3/month.

CATALOG blocks: 2024H2 n12 WR50% PF1.0 net0; 2025H1 n4 WR25% PF0.444 net-8.33; 2025H2 n24 WR66.67% PF2.25 net+50; 2026H1 n16 WR62.5% PF1.667 net+20; 2026JUL n4 WR75% PF3.5 net+12.5.

BALANCED blocks: 2025H1 n14 WR42.86% PF0.917 net-3.33; 2025H2 n24 WR66.67% PF2.25 net+50; 2026H1 n31 WR54.84% PF1.179 net+12.5; 2026JUL n5 WR80% PF4.0 net+15.

## Vector E — partial-only all-event stack

The exact same P50 TP5/TP10 SL5 exit was applied to all 3,864 activation/retest components. It failed:

- CATALOG: 1,800 trades, WR 48.11%, PF 0.9420, net -265.48.
- BALANCED: 2,255 trades, WR 48.03%, PF 0.9356, net -368.35.
- BROAD: 3,581 trades, WR 47.70%, PF 0.9011, net -910.79.

Therefore the improvement is not a generic partial-profit effect.

## Provisional observation family

The family begins with the frozen M5 VOLUME_ABSORPTION SHORT setup: tick-volume z-score above 1.5, M5 range below 0.85 ATR, upper-wick fraction above 0.35 and close-location below 0.45. It then requires a 3 USD favorable move within 15 minutes before a 1 USD adverse move.

Two confirmation subengines remain observation-only:

- LEVEL_RECLAIM_BASE: 1 USD pullback through the frozen activation level, then a later bearish close back below that level.
- EXTREME_RESUME_BASE: 0.5 USD retracement from the favorable extreme, then a later bearish close below both the previous M1 low and activation level.

Entry is the next M1 open.

## Why this is not formal

- The volume-absorption family was isolated after Vector A results were visible.
- The partial-only restriction was motivated by the observed TP10 dependency.
- Frequency is only 2–3 trades/month.
- 2025H1 remained negative.
- The broad all-event replication failed.
- No fresh no-backfill prospective period exists yet.

Do not present this as untouched validation. Do not start Shadow, Discord, MT5 orders or live trading. Frozen V19 and Challenger C1 were not modified or used as candidate inputs.
