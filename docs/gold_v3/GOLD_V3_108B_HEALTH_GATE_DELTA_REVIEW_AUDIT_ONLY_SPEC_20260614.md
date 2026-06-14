# GOLD V3 Stage108B Spec — HEALTH_GATE_DELTA_REVIEW_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_108B_HEALTH_GATE_DELTA_REVIEW_AUDIT_ONLY
```

## Why this stage exists

Stage108 completed and produced:

```text
status: GOLD_V3_108_RESOLVED_ONLY_STAGE_REVIEW_PACKET_READY_AUDIT_ONLY
decision: STAGE108_REVIEW_PACKET_READY_HUMAN_DECISION_REQUIRED
```

The 107S health gate is strict and valid:

```text
resolved_only_strict: true
exit_dt_used_as_entry_feature: false
```

But it creates a tradeoff:

```text
base_trades: 5571
health_trades: 5291
trade_delta: -280
base_win_rate: 63.7229%
health_win_rate: 64.0144%
base_profit_factor: 3.1290
health_profit_factor: 3.1840
base_sum_result_usd: 18065.7484
health_sum_result_usd: 17562.6176
sum_delta: -503.1308
```

Therefore 108B is needed to inspect exactly what was skipped by the health gate.

## Purpose

Stage108B compares base vs health-gated ledgers and answers:

1. Which skipped trades caused the sum decrease?
2. Were skipped trades mostly winners or losers?
3. Which months/regimes/sides/candidates are affected?
4. Did the health gate reduce weak periods or remove too many profitable trades?
5. Should the next review prefer base, health gate, or a lighter threshold?

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_resolved_107q_best_family_ledger.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_best_health_gate_ledger.csv
FX_OUTPUTS/gold_v3/108c/gold_v3_108_summary.json
```

## Outputs

```text
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_overview.csv
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_skipped_trade_ledger.csv
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_kept_trade_ledger.csv
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_monthly_delta.csv
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_regime_delta.csv
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_side_delta.csv
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_candidate_delta_top.csv
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_recommendation_matrix.csv
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_blocker_matrix.csv
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_validation_matrix.csv
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_summary.json
FX_OUTPUTS/gold_v3/108bc/GOLD_V3_108B_HEALTH_GATE_DELTA_REVIEW_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/108bc/paste_me.txt
```

## Recommendation logic

If skipped trades are net positive and total sum decreases, recommend base or lighter health review.

If skipped trades are net negative and WR/PF improves materially, recommend health gate.

If mixed, recommend human decision with monthly/daily inspection.

## Allowed decisions

```text
HEALTH_GATE_DELTA_REVIEW_READY_BASE_PREFERRED
HEALTH_GATE_DELTA_REVIEW_READY_HEALTH_GATE_PREFERRED
HEALTH_GATE_DELTA_REVIEW_READY_LIGHTER_HEALTH_GATE_REVIEW
HEALTH_GATE_DELTA_REVIEW_READY_HUMAN_DECISION_REQUIRED
HEALTH_GATE_DELTA_REVIEW_BLOCKED_INPUT_INCOMPLETE
```

## Guardrails

GOLD V3 remains audit-only.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime, Stage69 runtime, live evaluator, live hook, final signal, Discord, MT5, or AI API.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.
