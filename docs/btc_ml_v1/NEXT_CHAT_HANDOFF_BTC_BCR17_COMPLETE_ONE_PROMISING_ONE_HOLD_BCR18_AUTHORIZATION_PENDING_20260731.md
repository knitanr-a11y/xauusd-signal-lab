# NEXT CHAT HANDOFF — BTC BCR17 complete, one promising, one hold, BCR18 authorization pending

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- verified at: `2026-07-31T01:30:00+09:00`
- status: `BTC_REDESIGN_BCR17_COMPLETE_ONE_PROMISING_ONE_HOLD_SIX_REJECT_NO_SUPPORTED_BCR18_AUTHORIZATION_PENDING`
- completed stage: `BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE`
- BCR18 authorization: `PENDING_EXPLICIT_USER_AUTHORIZATION`
- deployable candidates: `0`

## 1. Current formal decision

`ACCEPT_BCR17_DETERMINISTIC_VALUE_RESULT_FREEZE_R12_B075_W16_AS_PROMISING_RESEARCH_SURVIVOR_R12_B100_W16_AS_COST_SENSITIVE_HOLD_NO_PROMOTION`

BCR17 is complete. The package, trade arithmetic, C0/C2 aggregate values, exact monthly Wilcoxon tests and Holm adjustments passed audit.

No machine is value-supported or deployable.

## 2. Authoritative result

1. `docs/btc_ml_v1/BTC_BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE_RESULT_20260731.md`
2. `configs/btc_ml_v1/btc_bcr17_b5_shared_retrospective_value_gate_result_20260731.json`

Result commits:

- Markdown: `b945a6ba4f5a0b38c5e61d1dce3ea037a714fa76`
- JSON: `c079a0bcaf861af68e9d98a08b910067758135cf`

## 3. Accepted package

- outer SHA256: `7e157046a11f65c18a030cc1a18665d0de737f652b0e02ca32b260b7edb3b1b8`
- accepted inner package SHA256: `dc8420a6edb104799919a51195cc03b7023377bca2c1d1eb75b0792164337ec7`
- deterministic run A/B: exact match
- manifest hashes and byte counts: exact
- frozen BTC M15 SHA: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- accepted BCR16 package SHA: `c469be9455bd5639de336684e0fdcaebf6a72dc6f0bae623acefa5e0cb506653`
- trade rows: `844`

## 4. Classification result

- `VALUE_SUPPORTED_RETROSPECTIVE`: `0`
- `VALUE_PROMISING_RETROSPECTIVE`: `1`
- `HOLD_COST_SENSITIVE`: `1`
- `REJECT_RETROSPECTIVE_VALUE`: `6`

Promising research survivor:

`TRACK_B_B5_R12_B075_W16_H1_IMPULSE_M15_RECLAIM`

- trades: `107`
- C0 PF/net: `1.0495 / +1,509.24`
- C2 PF/net: `1.0079 / +245.49`
- C2 expectancy: `+2.29 USD per 1 lot trade`
- C2 maximum drawdown: `9,803.00`
- C2 Holm-adjusted monthly p: `1.0`
- positive/negative C2 months: `5 / 6`

Cost-sensitive hold:

`TRACK_B_B5_R12_B100_W16_H1_IMPULSE_M15_RECLAIM`

- C0 PF/net: `1.0384 / +961.99`
- C2 PF/net: `0.9979 / -54.26`

## 5. Critical diagnostics

The promising machine is not robust:

- LONG C2 PF/net: `0.8915 / -1,654.90`
- SHORT C2 PF/net: `1.1210 / +1,900.39`
- same-server-date C2 PF/net: `1.4062 / +7,965.94`
- rollover-exposed pre-swap C2 PF/net: `0.3196 / -7,720.45`

These are diagnostics only.

Do not:

- delete LONG;
- create a SHORT-only candidate;
- use future same-server-date membership as an entry filter;
- retrospectively add rollover-flat or maximum-holding rescue;
- retune thresholds or exits.

## 6. Honest traction assessment

BCR17 is the first positive value indication in the current redesign, but it is weak.

- C2 PF is only `1.0079`;
- C2 net is only `+245.49` against `9,803.00` drawdown;
- monthly Holm p is `1.0`;
- no machine is value-supported.

Formal assessment:

`MODEST_FIRST_POSITIVE_SIGNAL_NOT_ROBUST`

## 7. Recommended next stage

`BCR18_B5_PROMISING_SURVIVOR_PROSPECTIVE_PREREGISTRATION`

BCR18 requires new explicit user authorization. The BCR17 result upload is not that authorization.

If authorized, BCR18 must preserve:

- exact `R12_B075_W16` machine;
- both LONG and SHORT;
- no threshold or exit changes;
- no retrospective same-day/rollover filter;
- fixed future boundary after contract freeze;
- BCR17 C0/C2 contract;
- no automatic promotion.

## 8. Current prohibitions

Until explicit BCR18 authorization:

- no BCR18 contract or prospective start;
- no shadow runtime;
- no candidate promotion;
- no machine or direction deletion;
- no portfolio construction;
- no Discord, MT5 order, live-ready or final signal;
- no Collector/M7C/M8C/M9/M10 change;
- no GOLD/MOCHIPOYO writeback.

## 9. Restart

Read `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md` first and use only ref `feature/btc-fresh-forward-research`. Default branch, main, old handoffs, GOLD files and unreferenced state files are forbidden as restart authority.
