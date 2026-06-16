# NEXT CHAT HANDOFF - GOLD V3 Stage180 done / Stage181 next

Date: 2026-06-16
Status: GOLD_V3_181_HIGH_FREQUENCY_CANDIDATE_SEARCH_READY_AUDIT_ONLY

## Non-negotiables

- GOLD V3 is audit-only.
- Do not read/use/reference/fallback to GOLD V2 / old GOLD / DISC8 / Stage41.
- CSV latest row is contractually closed. Do not use open/as-of/latest-open logic.
- Candidate pool must not be removed silently.
- F002 exclusion must not be bypassed.
- Discord notification, MT5 order execution, AI API, live hook, final signal, payload, autotrade remain OFF.
- NO_SIGNAL must not notify Discord.

## Current state

Stage177 found OHLC-only candidates that beat old PF benchmark 2.237.

Stage178 replayed Stage177 candidates under dedup and fixed cost scenarios. It found candidates still beating the old PF benchmark under `dedup_resolved_only` with `cost_points=3.0`.

Stage179 generated monthly winrate/trade-count table for the selected candidate:

- selected_old_rank: 84
- direction: LONG
- TP/SL: 40 / 20
- horizon_m5: 192
- rule: `d1_dist_close_atr28<=-0.438769 & h4_body_atr14>=0.883347`
- dedup full_n: 110
- full_pf: 16.09367149758454
- test_pf: 5.831521739130435
- full negative months: 0

Stage180 tested selected-candidate stability:

- base_full_n: 110
- base_full_pf: 16.09367149758454
- base_test_pf: 5.831521739130435
- base_recent3m_pf: 6.434782608695652
- base_full_neg_months: 0
- TP/SL/horizon grid rows: 90
- TP/SL/horizon rows beating old PF: 75
- threshold variants: 21
- threshold variants beating old PF: 12

Important Stage180 observations:

- The selected candidate is stable but trade count is low.
- Relaxing both thresholds by 10% increases full_n to 153 and still keeps full_neg_months 0, but test_pf drops to around 3.06.
- Relaxing both by 20% increases full_n to 182 but introduces one negative month, so this needs manual review.
- Dropping either condition entirely increases trade count but hurts robustness; these should not be accepted without more review.

## Stage181 created

Stage181 has been added to search higher-frequency alternatives around the Stage179 candidate.

Files added:

- `scripts/gold_v3_runtime/gold_v3_181_high_frequency_candidate_search_audit.py`
- `scripts/gold_v3_runtime/bat/run_gold_v3_181_high_frequency_candidate_search_audit.bat`
- `docs/gold_v3/GOLD_V3_181_HIGH_FREQUENCY_CANDIDATE_SEARCH_AUDIT_SPEC_20260616.md`

Commits:

- Stage181 script: `836ac180604f2bc50e0aff1b73a30cf7ab42ea89`
- Stage181 BAT: `2dce3bfec37bb3caef89966efae02d67f13cf3cb`
- Stage181 spec: `c122be89dae9f5f5bdeb6f55a5b3ce553920d69f`

## Stage181 run command

Run:

`scripts/gold_v3_runtime/bat/run_gold_v3_181_high_frequency_candidate_search_audit.bat`

Then paste:

`MQL5/Files/FX_OUTPUTS/gold_v3/181/paste_me.txt`

## Stage181 behavior

Stage181:

- starts from Stage179 selected literal rule;
- varies the saved literal thresholds around the selected rule;
- tests TP values 30/35/40/45/50;
- tests SL values 20/25/30;
- tests horizons 128/base/256;
- uses cost_points=3.0 by default;
- default target full trade count is 150;
- ranks candidates by tier.

Candidate tiers:

- `A_HIGH_FREQ_STABLE`: target count met, train/test/full/recent3m/high_vol PF >= 3.0, zero negative months.
- `B_HIGH_FREQ_REVIEW`: target count met, old PF benchmark beaten, recent/high-vol checks pass, and at most one negative month.
- `C_FREQ_OK_WEAKER_RECENT_OR_VOL`: frequency and basic PF pass, but recent or volatility robustness needs manual review.
- `D_FREQ_ONLY_FAILED_ROBUSTNESS`: frequency passes but robustness fails.
- `E_TOO_FEW_TRADES`: target trade count is not met.

## Next review

After user pastes Stage181 output:

1. Check `status`, `ready`, `blocker_count`.
2. Check `candidate_rows_A_B_C` and `tier_counts`.
3. Prefer A candidates if present.
4. If only B/C candidates appear, inspect negative months, recent3m PF, high_vol PF, and test PF before any next-stage decision.
5. Do not approve live. Next step should be another audit-only review such as candidate portfolio comparison or monthly table for the selected high-frequency candidate.
