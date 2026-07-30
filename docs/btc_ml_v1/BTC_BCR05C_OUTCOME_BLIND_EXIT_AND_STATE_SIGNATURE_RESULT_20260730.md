# BTC BCR05C — outcome-blind exit and state-signature result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T18:15:00+09:00`
- status: `READY_OUTCOME_BLIND_EXIT_AND_STATE_SIGNATURE_RESULT`
- profitability outcomes: not opened
- final exit formula: not selected
- resynchronization policy: not selected

## 1. Frozen inputs

- BCR04 package SHA256: `5044fc3c79f8ca4d4962f41f29156e9db8035383d97a1fa4d7cfdea7019496a8`
- M7C package SHA256: `870ea28c530f1db603afb190a0daa84963b6c7c3d4142ca0859dce1ddb655295`
- implementation preregistration commit: `542ed4bec923734033e12aebfa64965689f7e122`

Populations:

- LONG exits: `17`
- compatible ACTIVE_LONG controls: `223`
- SHORT exits: `10`
- compatible ACTIVE_SHORT controls: `168`

LONG and SHORT were analyzed separately. IDLE controls and opposite-position controls were not mixed into exit comparisons.

## 2. Exit signature is an extreme-state signature, not an RCI turn

Every observed LONG source exit occurred with RCI9 in the fixed positive-extreme zone:

- LONG exits with `RCI9 >= 40`: `17 / 17`
- ACTIVE_LONG controls in the same zone: `22.87%`
- prevalence difference: `+77.13 percentage points`
- corrected odds ratio: `117.23`
- FDR q-value: `4.91e-10`

Every observed SHORT source exit occurred in the fixed negative-extreme zone:

- SHORT exits with `RCI9 <= -40`: `10 / 10`
- ACTIVE_SHORT controls in the same zone: `23.81%`
- prevalence difference: `+76.19 percentage points`
- corrected odds ratio: `66.63`
- FDR q-value: `7.55e-6`

The observed source ranges were narrower:

- LONG exit RCI9 range: `70.00` to `91.67`, median `81.67`
- SHORT exit RCI9 range: `-88.33` to `-70.00`, median `-76.67`

A direction-opposite RCI9 turn was present at none of the exact exit boundaries:

- LONG exit turn-down: `0 / 17`
- SHORT exit turn-up: `0 / 10`

Therefore the source exit signature is not a local reversal-turn mirror of the entry signature. It is more consistent with a position-direction extension reaching an extreme RCI state. This is source-fidelity evidence only; it does not prove that the exit is economically optimal.

## 3. Trend and displacement context

The frozen family rules shortlisted three context families in each direction.

### LONG exit

- `X1_RCI_EXIT_SHAPE`: positive-extreme RCI9 zone
- `X2_EMA_TREND_STRUCTURE`: EMA30 four-bar slope
  - event median: `+5.57 bps`
  - control median: `-2.16 bps`
  - Cliff's delta: `+0.736`
  - q-value: `1.57e-6`
- `X3_CLOSED_BAR_REVERSAL_LOCATION`: current open relative to EMA20 in ATR14 units
  - event median: `+0.966 ATR`
  - control median: `-0.185 ATR`
  - Cliff's delta: `+0.711`
  - q-value: `1.16e-5`

### SHORT exit

- `X1_RCI_EXIT_SHAPE`: negative-extreme RCI9 zone
- `X2_EMA_TREND_STRUCTURE`: EMA20 four-bar slope
  - event median: `-5.55 bps`
  - control median: `+2.32 bps`
  - Cliff's delta: `-0.507`
  - q-value: `0.0557`
- `X3_CLOSED_BAR_REVERSAL_LOCATION`: four-bar fully closed return
  - event median: `-26.77 bps`
  - control median: approximately `0 bps`
  - Cliff's delta: `-0.533`
  - q-value: `0.0517`

No volatility family was advanced into the maximum-three-family shortlist. ATR or compression must not be added to the first exit grammar merely because they sound plausible.

## 4. M7C exact, late and missed decomposition

For the `26` exits covered by the accepted M7C comparison package:

### LONG exits

- exact: `9`
- one M15 bar late: `4`
- missed: `4`

### SHORT exits

- exact: `4`
- one M15 bar late: `2`
- missed: `3`

The later raw alert `193` is retained as a genuine SHORT exit but is labeled `COMPARISON_NOT_AVAILABLE` because it occurred after the accepted M7C evidence endpoint.

Exact and one-bar-late results remain separate. The six one-bar-late cases were not reclassified as exact successes.

## 5. One-bar-late timing

The one-bar-late cases did not wait for an opposite RCI turn. Instead, the RCI extreme intensified or remained extreme one bar later.

Examples:

- LONG raw `68`: RCI9 `70.00` at source exit, then `93.33` when M7C exited one bar late
- LONG raw `135`: `73.33` then `98.33`
- SHORT raw `113`: `-73.33` then `-98.33`
- SHORT raw `127`: `-73.33` then `-86.67`

Post-source rows are labeled `POST_SOURCE_EXIT_ONE_BAR_TIMING_DESCRIPTIVE_ONLY`. They are not allowed to become exact-time candidate features.

## 6. State-path consequences

Among the 26 exits with M7C comparison evidence:

- proxy/source state already differed before the source exit: `3`
- proxy/source state differed immediately after the source exit: `13`

All six one-bar-late exits created one divergent decision boundary. Missed exits created longer divergence episodes.

Three missed exits encountered a later genuine primary source alert before state resynchronization:

| missed exit raw ID | divergent boundaries | later primary raw ID |
|---:|---:|---:|
| `85` | `45` | `86` |
| `97` | `9` | `98` |
| `169` | `18` | `172` |

At all three later primary boundaries:

- the appropriate BCR05B full-coverage entry predicate passed;
- proxy state was not IDLE;
- the corresponding primary transition was not emitted.

They are therefore recorded as `STATE_BLOCKED_FULL_COVERAGE_PRIMARY` events. No price outcome was attached.

This proves the path-dependent mechanism anticipated in BCR02A: a missed exit can suppress a later otherwise valid primary entry.

## 7. What is not concluded

BCR05C does not establish:

- that the source exit improves profit;
- that earlier exit is economically better;
- that a fixed RCI threshold should be deployed;
- that state should be forcibly reset;
- that any missed source entry was profitable;
- that a time stop, TP or SL should be added.

No WR, PF, DD, MFE, MAE, future return, TP/SL result or trade outcome was opened.

## 8. Accepted artifacts

Package:

- file: `BCR05C_OUTCOME_BLIND_EXIT_AND_STATE_SIGNATURE_20260730.zip`
- SHA256: `221280603569054f3ffc23c6698446e377f9d650d288fa3d08d224a8e3925af3`
- deterministic two-run SHA match: true

The package contains comparison tables, FDR manifest, leave-out stability, one-bar timing, exact/late/missed decomposition, state-divergence consequence ledger and integrity evidence.

## 9. Decision

BCR05C passes.

The next stage may preregister a small finite exit grammar using only the shortlisted source-fidelity families. It must evaluate source-exit recall and compatible ACTIVE-control fire rate without profitability outcomes. Only after finite entry and exit variants are replayed as complete state machines may a small integrated Track A source-fidelity family be frozen.
