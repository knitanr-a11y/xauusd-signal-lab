# GOLD SCALP EVENT-SEQUENCE GRAMMAR V1 — Consolidated Audit

Date: 2026-08-02  
Formal status: **`RETROSPECTIVE_EVENT_SEQUENCE_MULTI_VECTOR_COMPLETE_NO_FORMAL_CANDIDATE`**

## Contract

- Existing GOLD candle data only.
- MT5 broker-server naive time and closed rows only.
- Exact M1 entry/outcome resolution.
- Standard spread 0.30 USD once.
- Initial SL no greater than 5 USD and TP no lower than 5 USD.
- Breakeven movement allowed.
- Protective-stop-first same-M1 handling.
- One-position non-overlap.
- Sequential pseudo-forward blocks; the immediately prior block was calibration and older rows selected the exit.
- No post-result hour, month, side or volatility deletion.

## Vector A — ordered existing-event grammars

Twenty fixed two- and three-stage grammars were tested, including sweep/reclaim to effort expansion, false break to expansion, HTF pullback to micro impulse, compression to sweep to expansion, and failed pullback to opposite false break.

- completed sequence candidates: 40,766;
- natural sequence-policy rows: 109,951;
- frozen half-year calibration passes: zero;
- target trades opened: zero.

Ordering individually noisy events did not increase stable directional quality.

## Vector B — causal strength and dwell progression

Each stage received a causal 120-calendar-day within-event quality percentile. Sixty-eight components tested high final confirmation, non-decreasing stage strength, fast confirmation, all-stage strength and contracting dwell times.

- filtered candidates: 27,779;
- CORE aggregate: 169 trades, WR 30.77%, PF 0.7014, net -146.30 USD, DD 147.14 USD;
- HQ aggregate: 53 trades, WR 22.64%, PF 0.3147, net -111.91 USD;
- no formal candidate.

## Vector C — sequence direction and timing

Five fixed interpretations were tested:

1. immediate inversion;
2. next-M5 follow confirmation;
3. next-M5 denial and fade;
4. inside pullback then original-side resume;
5. midpoint retest and reclaim.

Candidate counts included 40,766 immediate inversions, 19,833 follow confirmations, 9,687 denial fades, 6,439 midpoint reclaims and 2,268 inside pullbacks.

- CATALOG aggregate: 49 trades, WR 32.65%, PF 0.9744, net -2.65 USD;
- BALANCED produced only four trades despite descriptive PF 5.0;
- no formal candidate.

The same sequence did not consistently represent continuation or exhaustion across periods.

## Vector D — raw M5 finite-state grammars

Fourteen grammars were built directly from candle geometry: HTF two-bar pullback resume, three-bar compression to impulse, inside-inside break, outside-inside break, sweep confirmation, double rejection, impulse-pause-resume, climax absorption break, failed close break reversal, two gap grammars, sweep-neutral-reclaim, alternation break and staircase continuation.

- grammar candidates: 58,075;
- BALANCED aggregate: 214 trades, WR 30.84%, PF 0.5954, net -221.97 USD, DD 221.97 USD;
- no formal candidate.

## Vector E — pseudo-forward candidate promotion

All components from the strength, timing and raw-M5 studies were combined into a 1,042,192-row natural policy ledger. A component was paper-tracked only after passing the current causal calibration gate.

- component/block paper observations: 22;
- promotion rules: one prior positive target block, two prior positive target blocks, or two consecutive positive target blocks;
- eligible promoted components: zero under all rules.

No grammar both produced a positive target block and subsequently re-qualified under the same calibration contract. This means the weakness was not merely portfolio overlap; individual grammar survival was not repeatable.

## Observation-only rows

The catalog retains only descriptive rows:

- failed HTF pullback to opposite false break with rising ranks: 22 trades in 2024H2, WR 40.91%, PF 1.4581, +19.36 USD;
- sweep/reclaim to run resume with rising ranks: 17 trades in 2025H2, WR 35.29%, PF 1.1981, +4.96 USD;
- two July 2026 timing rows with only two or three trades.

None is a validated candidate or authorized stack component.

## Formal conclusion

**`NO_FORMAL_CANDIDATE`**

Event-sequence grammar was materially different from the earlier single-event, first-passage and regime-router studies, but it did not solve cross-period directional instability. Apparently good calibration patterns repeatedly reversed in the following block.

## Next materially distinct boundary

A future candle-only study should avoid selecting named patterns from one calibration block. A materially different hypothesis is continuous path-shape matching with an outcome-independent representation:

1. normalize the preceding 30–90 M1 returns by causal volatility;
2. learn the representation without trade outcomes, using reconstruction or contrastive objectives;
3. match a new path only to historical neighbors strictly before its decision time;
4. require agreement across multiple historical eras, rather than only the latest calibration block;
5. let structural events define the proposed side, while era-balanced neighbors decide follow, fade or abstain;
6. add an engine to the catalog only after at least two pseudo-forward target-block successes.

This is different from the prior supervised CNN because the representation must not optimize trade outcomes.

No Shadow, Discord, MT5 order, live trading, promotion or merge authorization follows. Frozen V19 and Challenger C1 were not modified, stopped, reconfigured or used as candidate inputs.
