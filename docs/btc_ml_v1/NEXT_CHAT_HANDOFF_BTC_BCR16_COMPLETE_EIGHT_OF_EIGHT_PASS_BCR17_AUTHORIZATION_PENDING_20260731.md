# NEXT CHAT HANDOFF — BTC BCR16 complete, eight of eight pass, BCR17 authorization pending

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- verified at: `2026-07-31T00:33:00+09:00`
- status: `BTC_REDESIGN_BCR16_COMPLETE_EIGHT_OF_EIGHT_B5_MACHINES_PASS_CAPABILITY_BCR17_AUTHORIZATION_PENDING`
- completed stage: `BCR16_B5_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_AUDIT`
- BCR17 authorization: `PENDING_EXPLICIT_USER_AUTHORIZATION`

## 1. Current formal decision

`ACCEPT_BCR16_DETERMINISTIC_LABEL_FREE_RESULT_FREEZE_EIGHT_B5_CAPABILITY_SURVIVORS_AWAIT_EXPLICIT_BCR17_VALUE_GATE_AUTHORIZATION`

BCR16 is complete. The uploaded deterministic package passed integrity, frozen-input, complete-H1, state-machine and outcome-isolation checks. All eight B5 machines passed the unchanged capability gate.

No B5 return, win/loss, PF, PnL, MFE or MAE was opened.

## 2. Authoritative BCR16 result

1. `docs/btc_ml_v1/BTC_BCR16_B5_OUTCOME_BLIND_CAPABILITY_RESULT_20260731.md`
2. `configs/btc_ml_v1/btc_bcr16_b5_outcome_blind_capability_result_20260731.json`

Result commits:

- Markdown: `04ce341ee21b59e7a08becc0225085bfe51e93ad`
- JSON: `ad2d4f50313f43d4d70d7deefbd78122c958c6eb`

## 3. Accepted package

- received outer upload SHA256: `2504c83c0e1cd6b9c336420cb8435f4c599493c076a5bed0028f3717e834229f`
- accepted inner package SHA256: `c469be9455bd5639de336684e0fdcaebf6a72dc6f0bae623acefa5e0cb506653`
- deterministic run A/B match: true
- manifest hashes and byte counts: exact
- outer and inner ZIP CRC checks: passed

Frozen input:

- rows: `30,661`
- SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- first time: `2025-09-13 08:00:00`
- last time: `2026-07-30 06:15:00`
- complete causal H1 bars: `7,630`
- append-only prefix: exact SHA match
- fallback/interpolation: none

## 4. Capability result

- machines reported: `8`
- capability pass: `8`
- capability fail: `0`
- candidate promoted: `0`
- deployable candidates: `0`

Observed ranges:

- H1 impulses: `253–421`;
- entries and closed episodes: `82–131`;
- closed LONG: `42–67`;
- closed SHORT: `40–66`;
- distinct entry months: `11` in every machine;
- maximum month share: `10.47%–13.00%`;
- median holding: `9–12` bars;
- p90 holding: `32` bars in every machine;
- maximum holding: `32–33` bars;
- occupancy: `3.87%–5.68%`;
- endpoint-open episodes: `0` in every machine.

All machines passed state integrity. Simultaneous conflicts and exact-entry-missing events were zero. No fallback or interpolation was used.

## 5. Honest traction assessment

This is the first materially new Track B family in the current redesign to pass capability across every frozen machine.

Candidate-level traction is now real at the capability level:

- adequate density;
- balanced directions;
- broad monthly coverage;
- finite holding;
- low occupancy;
- deterministic state integrity.

Profitability traction is still unknown because the value fields remain unopened.

Structural-success, structural-failure and expiry exit categories in BCR16 are state-machine closure categories, not trading wins or losses.

## 6. Prior families remain closed

- B1: rejected, no rescue;
- B2: blocked, no threshold rescue;
- B3: `CLOSED_NO_CAPABILITY_SURVIVOR_NO_RESCUE`;
- B4 and Track A: preserved as audit evidence, active rescue closed.

Do not reuse prior-family result filters to select B5 machines.

## 7. BCR17 boundary

Recommended next stage:

`BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE`

BCR17 is not yet authorized.

If explicitly authorized, it must:

- evaluate all eight B5 capability survivors;
- use the frozen BCR08 symbol/execution/cost provenance;
- report C0 and C2;
- report all eight trials, including failures;
- apply multiple-testing control;
- prohibit post-result machine or direction deletion;
- describe results as retrospective, not independent OOS;
- create no prospective or shadow claim without a later separately committed boundary.

## 8. Currently forbidden

- B5 return, win/loss, PF, PnL, MFE or MAE before BCR17 authorization;
- threshold rescue;
- LONG-only or SHORT-only rescue;
- machine deletion based on outcome;
- portfolio construction;
- prospective start or shadow;
- Discord, MT5 order, live-ready or final signal;
- Collector/M7C/M8C/M9/M10 changes;
- GOLD/MOCHIPOYO writeback.

## 9. Restart rules

Read the files listed by `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md` in exact order using ref `feature/btc-fresh-forward-research`.

Do not use main/default branch, AGENTS.md, GOLD documents, old BTC handoffs, FF05 recovery V3-V11 or unreferenced state/action/handoff as restart authority.
