# GOLD V3 Stage109B Spec — LOSS_FEATURE_FINGERPRINT_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_109B_LOSS_FEATURE_FINGERPRINT_AUDIT_ONLY
```

## Why this stage exists

Stage109 selected the review candidate:

```text
selected_option: KEEP_107Q_BASE
selected_policy_key: 107Q_BASE_RESOLVED_PASS_THROUGH
health_gate_adopted: false
```

The user asked whether we can reduce losses by finding entry-time features that frequently appear in losing trades.

This is a valid next audit-only direction. It must be treated as diagnostic/post-hoc mining first, not as an approved live filter.

## Purpose

Stage109B mines the selected base-policy ledger for loss-heavy entry-time feature patterns.

It must:

1. Read the Stage109 selected base ledger.
2. Separate wins and losses by `result_usd`.
3. Identify entry-known boolean/categorical patterns with elevated loss rates.
4. Identify entry-known numeric feature bins with elevated loss rates.
5. Run post-hoc removal diagnostics for candidate filters.
6. Produce train-only replay recommendations for the next stage.

## Strict data rule

Stage109B must not use future/outcome columns as candidate filter features.

Forbidden as filter features:

```text
result_usd
recomputed_result_usd
result_delta
exit_dt
exit_price
exit_reason
result_parity_pass
health_gate_*
selected_option
stage109_selection_reason
any column beginning with exit_
any column containing result, win, loss, pnl, profit, parity
```

Allowed examples:

```text
side
family
condition
profile_id
source_name
global_candidate_key
score
feature_score
m15_*, h1_*, h4_*, d1_* features
entry_month / entry hour diagnostics only
```

Time/month diagnostics must be marked diagnostic-only and not final unless later justified as operational calendar policy.

## Outputs

```text
FX_OUTPUTS/gold_v3/109bc/gold_v3_109b_loss_feature_overview.csv
FX_OUTPUTS/gold_v3/109bc/gold_v3_109b_boolean_categorical_loss_profile.csv
FX_OUTPUTS/gold_v3/109bc/gold_v3_109b_numeric_bin_loss_profile.csv
FX_OUTPUTS/gold_v3/109bc/gold_v3_109b_candidate_filter_diagnostics.csv
FX_OUTPUTS/gold_v3/109bc/gold_v3_109b_top_loss_patterns.csv
FX_OUTPUTS/gold_v3/109bc/gold_v3_109b_recommended_next_actions.csv
FX_OUTPUTS/gold_v3/109bc/gold_v3_109b_blocker_matrix.csv
FX_OUTPUTS/gold_v3/109bc/gold_v3_109b_validation_matrix.csv
FX_OUTPUTS/gold_v3/109bc/gold_v3_109b_summary.json
FX_OUTPUTS/gold_v3/109bc/GOLD_V3_109B_LOSS_FEATURE_FINGERPRINT_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/109bc/paste_me.txt
```

## Candidate filter diagnostics

Each candidate filter must be clearly marked:

```text
posthoc_diagnostic_only: true
requires_train_only_revalidation: true
final_rule_approval: false
live_ready: false
```

Post-hoc improvements are not enough for adoption.

## Next stage

If Stage109B finds plausible loss-heavy filters, next stage should be:

```text
109C_TRAIN_ONLY_LOSS_FEATURE_FILTER_REPLAY_AUDIT_ONLY
```

109C must select filters using only past/train windows and validate forward, avoiding post-hoc overfitting.

## Decisions

Allowed decisions:

```text
LOSS_FEATURE_FINGERPRINT_READY_FOR_109C_TRAIN_ONLY_REPLAY
LOSS_FEATURE_FINGERPRINT_NO_ACTIONABLE_PATTERN_KEEP_109_BASE
LOSS_FEATURE_FINGERPRINT_BLOCKED_INPUT_INCOMPLETE
```

## Guardrails

GOLD V3 remains audit-only.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime, Stage69 runtime, live evaluator, live hook, final signal, Discord, MT5, or AI API.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.
