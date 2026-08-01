# GOLD CHALLENGER C1 V2 DATA V3 — RESEARCH PREREGISTRATION

Created before DATA_V3 router, wave, candidate, execution, or robustness results were calculated.

## Classification

- Candidate: `GOLD_CHALLENGER_C1_V2_DATA_V3`
- Old 123/PF1.947: `UNEXPECTED_DISCOVERY_DIAGNOSTIC` only.
- `(2)` sources are unavailable and are not a reproduction target.
- This research uses only the frozen `(3)` source manifest.

## Fixed hypothesis

`chosen_rank < P90` in the E40-selected direction, with frozen V17 aggregate wave state `IMPULSE_LATE` or `CORRECTION_EARLY`, first causal state-event onset only. LONG and SHORT remain.

## Time contract

CSV `time` is bar-open time. M15 `time=T` becomes available at `T+15m`; decision and entry use the exact M1 open at `T+15m`. H1/H4 are usable only after `time + timeframe <= decision_dt`.

## Data V3 M15 derivation

No sharp M15 `(3)` file exists. A deterministic sharp M15 is derived from sharp M1. The algorithm was fixed only after it reproduced the old `(3)` broker M15 on 81,781/81,781 rows exactly. Its hash is in `source_manifest.json`.

## Separation

Candidate generation sees only whitelisted entry columns and cannot access outcome columns. Exact M1 execution and portfolio accounting are separate modules. V19 is read-only and is never modified or anticipated from the future.

## Interpretation

Even a full pass is capped at `RETROSPECTIVE_STRUCTURAL_ROBUSTNESS_ONLY`. No Shadow, Discord, AI, order, or deployment authorization follows.
