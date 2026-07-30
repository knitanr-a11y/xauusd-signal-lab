# BTC BCR13 — B3 outcome-blind density and state-machine result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T23:26:00+09:00`
- stage: `BCR13_B3_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_AUDIT`
- status: `BCR13_COMPLETE_ZERO_OF_EIGHT_B3_MACHINES_PASS_CAPABILITY`
- B3 value outcome access: not opened
- candidate promotion: zero
- BCR14 value gate: not applicable because there are no BCR13 capability survivors

## 1. Accepted upload and integrity

Received outer upload:

- user filename: `99_UPLOAD_PACKAGE(104).zip`
- outer SHA256: `e5aa622dfa87d1c75f14e07758f005e237778735f126cad62ebd07e6cbad5323`

The outer ZIP contained exactly:

1. `BCR13_B3_OUTCOME_BLIND_DENSITY_AUDIT_20260730.zip`
2. `deterministic_repeat.json`
3. `package_sha256.txt`

Accepted inner package:

- SHA256: `cc1483c0e8b538eb32b67dce0a10df8733c5e7f5f924c9080f945ebddc72e51d`
- `deterministic_repeat_match`: true
- run A SHA: `cc1483c0e8b538eb32b67dce0a10df8733c5e7f5f924c9080f945ebddc72e51d`
- run B SHA: `cc1483c0e8b538eb32b67dce0a10df8733c5e7f5f924c9080f945ebddc72e51d`
- `package_sha256.txt`: exact match
- ZIP CRC test: passed for outer and inner ZIPs
- all manifest member SHA256 and byte counts: exact match

## 2. Frozen input verification

The append-only MT5 source had grown and was accepted only through exact frozen-prefix rehydration.

- current source SHA256: `fb174125b9234b9c600a9dd8c5971379530bebb0fd80bbeac8ee527ef7991e59`
- frozen prefix SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- frozen rows: `30,661`
- first M15 open: `2025-09-13 08:00:00`
- last M15 open: `2026-07-30 06:15:00`
- prefix rehydrated: yes
- sorting, interpolation, nearest/next row and similar-file fallback: none

## 3. Outcome isolation

The package contains no forbidden value fields.

Verified absent from every CSV header and JSON key:

- return;
- win/loss;
- PF;
- PnL;
- MFE;
- MAE;
- future-exit result;
- entry price;
- exit price.

The summary also records:

- `outcome_fields_opened = false`;
- `value_evaluation_performed = false`;
- `candidate_promoted = false`;
- `portfolio_selected = false`;
- `prospective_start_set = false`;
- `shadow_started = false`;
- `discord_sent = false`;
- `mt5_order_sent = false`.

## 4. Complete eight-machine result

All eight frozen B3 machines were reported. Capability result:

- pass: `0 / 8`;
- fail: `8 / 8`.

| machine | entries | closed L/S | months | max month share | p90 holding | max closed holding | occupancy | endpoint open |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| L32 D0.25 W4 | 7 | 3 / 3 | 2 | 71.43% | 993.0 | 1,149 | 97.99% | 1 |
| L32 D0.25 W8 | 8 | 3 / 4 | 2 | 75.00% | 957.8 | 1,139 | 97.98% | 1 |
| L32 D0.50 W4 | 6 | 3 / 2 | 2 | 66.67% | 1,018.2 | 1,139 | 97.93% | 1 |
| L32 D0.50 W8 | 7 | 3 / 3 | 2 | 71.43% | 988.0 | 1,139 | 97.95% | 1 |
| L64 D0.25 W4 | 5 | 3 / 1 | 2 | 60.00% | 1,055.4 | 1,149 | 97.91% | 1 |
| L64 D0.25 W8 | 6 | 3 / 2 | 2 | 66.67% | 1,018.2 | 1,139 | 97.90% | 1 |
| L64 D0.50 W4 | 5 | 3 / 1 | 2 | 60.00% | 1,048.4 | 1,139 | 97.86% | 1 |
| L64 D0.50 W8 | 6 | 3 / 2 | 2 | 66.67% | 1,018.2 | 1,139 | 97.88% | 1 |

Every machine failed the same five frozen capability checks:

1. fewer than `50` closed episodes;
2. fewer than `20` closed episodes in each direction;
3. fewer than `6` entry months;
4. one month exceeded `35%` of entries;
5. p90 holding exceeded `384` M15 bars.

Every machine passed:

- maximum closed holding at most `1,500` bars;
- at most one endpoint-open episode;
- state integrity;
- no fallback/interpolation.

No threshold, side or machine rescue is allowed.

## 5. State-machine phenotype

Across the eight machines:

- breakouts: `16–25`;
- retests: `10–20`;
- re-accelerations and entries: `5–8`;
- closed episodes: `4–7`;
- distinct entry months: exactly `2` for every machine;
- simultaneous LONG/SHORT conflicts: `0`;
- gap cancellations: `0`;
- exact-entry-missing events: `0`;
- active decision unavailable gaps: `46` per machine;
- state integrity: true for every machine.

Each machine finished with one endpoint-open SHORT episode.

- D0.25 machines entered the endpoint-open episode at `2025-10-10 22:30:00`;
- D0.50 machines entered at `2025-10-11 00:00:00`;
- endpoint-open holding at the frozen endpoint: `28,058–28,064` theoretical M15 bars.

The one-position rule therefore left every machine active for approximately `97.86%–97.99%` of eligible boundaries and prevented later setup participation. This is label-free state behavior, not a PnL interpretation.

The implementation reports p90 and maximum holding from closed episodes and reports endpoint-open duration separately in the episode ledger. This does not affect the decision because every machine independently fails the five capability checks listed above.

## 6. Formal decision

`ACCEPT_BCR13_DETERMINISTIC_LABEL_FREE_RESULT_CLOSE_B3_FAMILY_ZERO_CAPABILITY_SURVIVORS_NO_PROMOTION`

Consequences:

- B3 family capability survivors: `0`;
- B3 candidate promoted: `0`;
- deployable candidates: `0`;
- BCR14 retrospective value/PnL gate: `NOT_APPLICABLE`;
- B3 threshold loosening: forbidden;
- B3 direction deletion: forbidden;
- B3 exit rescue or additional machine inside the frozen family: forbidden;
- portfolio, prospective start and shadow: none.

BCR14 was reserved for value evaluation of BCR13 capability survivors. Since there are no survivors, opening B3 return, win/loss, PF, PnL, MFE or MAE would violate the preregistered boundary and is not authorized.

## 7. Recommended next stage and authorization boundary

The next technically coherent stage is a materially new outcome-blind Track B family design, not a B3 rescue:

`BCR15_MATERIALLY_NEW_OUTCOME_BLIND_TRACK_B_MECHANISM_DESIGN`

BCR15 is not authorized by this result upload. Before explicit user authorization, do not create a BCR15 contract, formula, implementation, BAT or historical result.

Collector, M7C, M8C, M9 and M10 remain unchanged. No GOLD/MOCHIPOYO writeback, Discord, MT5 order, live-ready or final-signal work is authorized.
