# GOLD V2 AI tag Phase 3 rule-rubric replay

Created: 2026-06-03
Status: audit-only / not runtime approved

## Purpose

Phase 2 showed that free AI judgement was stable as an API call, but not useful as a stack policy. It mostly returned CAP_3 and did not identify the large-loss tail rows.

Phase 3 therefore tests a deterministic numeric rubric first. The AI should not be used as a free judge until a rule table is proven.

## Baselines on the same 174-row audit

| Policy | Count | Win rate | PF | TotalR | Worst | Max DD | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| representative fixed | 174 | 64.37% | 2.19 | +74.0R | -1.0R | 5.0R | 4 |
| CAP2 fixed | 174 | 59.77% | 2.41 | +136.5R | -2.0R | 10.0R | 3 |
| CAP3 fixed | 174 | 64.37% | 2.51 | +174.0R | -3.0R | 14.0R | 5 |
| uncapped fixed | 174 | 64.37% | 2.99 | +263.0R | -11.0R | 13.0R | 3 |
| Phase 2 AI stack | 174 | 64.37% | 2.51 | +174.0R | -3.0R | 14.0R | 5 |
| Phase 3 rule rubric | 174 | 65.52% | 3.62 | +285.5R | -3.0R | 9.0R | 3 |

## Rule rubric tested

Evaluation starts from stacked audit permission, then caps specific risk contexts.

1. `top_score >= 7.865301 AND ret96 <= -4.9362` -> CAP_3
2. `regime == LOW_VOL_RANGE AND top_direction == SELL AND same_direction_score_sum >= 21.304476 AND unique_same_direction_origins <= 2` -> CAP_3
3. `regime == LOW_VOL_RANGE AND top_direction == SELL AND same_direction_score_sum >= 33.09413 AND top_score <= 8.764954` -> CAP_3
4. `top_direction == SELL AND regime in [MID_MIXED, LOW_VOL_RANGE] AND same_direction_count == 4` -> CAP_3
5. Else if `same_direction_count >= 4` -> ALLOW_STACKED_AUDIT_ONLY
6. Else -> CAP_3

## Result interpretation

The rule rubric beats the fixed baselines on this 174-row audit:

- vs CAP3 fixed: +111.5R
- vs uncapped fixed: +22.5R
- worst trade improves from uncapped -11R to -3R
- max drawdown improves from CAP3 fixed 14.0R to 9.0R

Important: this is selected on the same 174-row audit. Treat it as a candidate rubric, not proof.

## Large-loss tail handling

All four Phase 2 large-loss tail rows are capped to CAP_3 by the rubric.

## Next step

Do not run more free AI yet. Validate this deterministic rubric on a new walk-forward / out-of-sample split. If it survives, AI can be used only as a rule-applier and explainer, not as a free judgement model.
