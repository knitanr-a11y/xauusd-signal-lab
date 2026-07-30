# BTC BCR05A — outcome-blind Track A source-signature result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T13:46:00+09:00`
- status: `READY_OUTCOME_BLIND_TRACK_A_SOURCE_SIGNATURE_COMPARISON_CORRECTED`
- profitability outcomes: not opened
- final trigger formula: not selected

## 1. Input populations

BCR05A used only the accepted BCR04 decision universe:

- BCR04 package SHA256: `5044fc3c79f8ca4d4962f41f29156e9db8035383d97a1fa4d7cfdea7019496a8`
- LONG primary source events: `16`
- SHORT primary source events: `10`
- core-feature-eligible IDLE controls: `438`

LONG and SHORT were analyzed separately. ACTIVE-state controls, exits, reentries and opposite-ignored events were not mixed into the primary-entry comparison.

## 2. Pre-acceptance correction

The first local comparison output incorrectly tested:

`distance_to_nearest_source_event_bin=EVENT`

as though it were a market feature. Event rows are definitionally in that bin, so the variable identified the label rather than an alert mechanism.

The invalid pre-acceptance package SHA256 was:

`838dc8cacdcb086302cfa48f3a5818fdbc7e2ac61c041337381be57df996dcdb`

It is not a research result.

The corrected v1.0.1 run:

- removed current/nearest/next event-distance variables from inference;
- separated source-state age and previous genuine-source-event distance as fidelity context only;
- excluded source-derived context from candidate-feature shortlist ranking;
- recomputed all affected FDR groups;
- opened no outcome data.

## 3. RCI9 turn anchor specificity

The direction-correct RCI9 turn was prior evidence, not a new discovery. BCR05A measured its specificity against the full compatible IDLE-control universe.

### LONG

- source events with RCI9 turn-up: `16 / 16` = `100%`
- IDLE controls with RCI9 turn-up: `51 / 438` = `11.64%`
- prevalence difference: `+88.36 percentage points`
- corrected odds ratio: `248.30`
- FDR q-value: `1.98e-13`

### SHORT

- source events with RCI9 turn-down: `10 / 10` = `100%`
- IDLE controls with RCI9 turn-down: `64 / 438` = `14.61%`
- prevalence difference: `+85.39 percentage points`
- corrected odds ratio: `121.93`
- FDR q-value: `1.86e-7`

This confirms that RCI9 reversal is a strong source-fidelity anchor, but it is not sufficient by itself because the same turn still appears in a meaningful number of non-event controls.

## 4. EMA structure

Direction-correct EMA alignment was enriched at source events.

### LONG

- bullish EMA20 > EMA30 > EMA40: `14 / 16` = `87.5%`
- IDLE controls: `57.31%`
- corrected odds ratio: `4.32`
- q-value: `0.0246`

No LONG source event occurred under a bearish stack. The automatic family ranking used `absence of bearish stack` as its lowest-q representative, but the canonical interpretable form is the direction-correct bullish stack above.

### SHORT

- bearish EMA20 < EMA30 < EMA40: `9 / 10` = `90.0%`
- IDLE controls: `38.81%`
- corrected odds ratio: `9.97`
- q-value: `0.00199`

No SHORT source event occurred under a bullish stack.

## 5. RCI shape beyond the binary turn

### LONG

- source RCI9 median: `-70.83`
- IDLE-control median: `20.00`
- source RCI9 one-bar delta median: `+10.83`
- control median delta: `0.00`
- RCI9-delta Cliff's delta: `+0.609`
- q-value: `0.000203`

The LONG source signature is therefore not merely any turn-up. It usually occurs while the short RCI remains in a depressed region and reverses upward.

Longer RCIs do not always reverse at the same moment. RCI14 and RCI18 frequently remain weak or continue downward while RCI9 turns upward. That supports a multi-speed pullback-turn interpretation, but no final multi-RCI gate is selected in BCR05A.

### SHORT

- source RCI9 median: `+74.17`
- IDLE-control median: `20.00`
- source RCI9 one-bar delta median: `-11.67`
- control median delta: `0.00`
- RCI9-level Cliff's delta: `+0.495`
- RCI9-level q-value: `0.0398`

The SHORT source signature is the mirror: RCI9 is usually elevated and turns downward. Longer RCIs may still be rising when the short RCI turns, again indicating a multi-speed turn rather than all RCIs reversing simultaneously.

## 6. Previous fully closed M15 return

The immediately previous fully closed M15 return also differed from IDLE controls.

### LONG

- source-event median: `+8.09 bps`
- control median: `+0.22 bps`
- Cliff's delta: `+0.405`
- q-value: `0.0711`

### SHORT

- source-event median: `-14.88 bps`
- control median: `+0.22 bps`
- Cliff's delta: `-0.676`
- q-value: `0.00306`

This is a source-fidelity feature, not yet an independent edge. The return and RCI9 delta are mechanically related because both respond to the newest closed bar. A later finite grammar must test them as separate optional gates and must not count their correlation as two independent confirmations.

## 7. Families retained for finite grammar work

Under the frozen FDR, effect-size and leave-out-stability rules, both directions retained:

- `A_RCI_SHAPE`
- `B_EMA_STRUCTURE`
- `D_CLOSED_BAR_LOCATION`

Not retained in either direction:

- `C_VOLATILITY_COMPRESSION`
- `E_CLOCK_SEQUENCE`

This means no ATR, compression, realized-volatility, broker-hour or weekday gate should be added to the first finite Track A grammar merely because it seems plausible.

Source-state age and genuine-source-event cadence remain descriptive fidelity context only. They are not directly promoted into a standalone candidate.

## 8. Stability and limitations

- LONG events span `8` UTC calendar days.
- SHORT events span `5` UTC calendar days.
- shortlisted representative effects retained their sign in every leave-one-event-day-out and leave-one-event-out run.
- Benjamini-Hochberg correction was applied separately by direction, feature family and statistic type.

However:

- the sample is small;
- all rows come from one short prospective source interval;
- this is not independent OOS profitability evidence;
- no threshold was selected for expected return;
- no candidate formula, exit or risk rule exists yet.

## 9. Accepted artifacts

Corrected deterministic package:

- file: `BCR05A_OUTCOME_BLIND_TRACK_A_SIGNATURE_COMPARISON_20260730.zip`
- SHA256: `b49b9118d0e15184d8b7aea3452b70899ed0406b82360580fd076ae972d9255b`
- extended generator SHA256: `ee615ab860945713a272995fe448f3dce997ba81e5ec64baa98994a0945fb6c6`

GitHub core reproducer:

- `scripts/btc_ml_v1/BCR05A_outcome_blind_track_a_signature/python/run_bcr05a_core_reproduction.py`
- commit: `63fa6d46c0fe435d476b8a7cd8e7e395873733a9`

Tests:

- `tests/btc_ml_v1/test_bcr05a_corrected_core_reproduction.py`
- commit: `8ea64c8c0059d207f17fe7437f498a5e402413df`
- result: `3 passed`, plus actual frozen-input core reproduction.

## 10. Decision

BCR05A passes after correction.

It authorizes only a small, finite, outcome-blind entry-grammar stage. It does not authorize profitability evaluation, TP/SL design, exit optimization, FF06, shadow, Discord or MT5 order actions.
