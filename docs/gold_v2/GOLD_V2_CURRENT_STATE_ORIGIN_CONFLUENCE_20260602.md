# GOLD V2 current state — origin candidates and confluence-score audit

Created: 2026-06-02
Status: CURRENT WORKING STATE SNAPSHOT

## 1. Context

GOLD V2 was reset after discovering that older GOLD/DISC documents and ledgers may have treated MT5 candle open times as close times. Old GOLD documents remain legacy forensic material only.

Canonical reset document:

```text
docs/gold_v2/GOLD_V2_START_HERE_AFTER_HTF_OPEN_TIME_BUG_20260602.md
```

Legacy quarantine document:

```text
docs/gold_legacy_quarantine/README_GOLD_LEGACY_QUARANTINE_20260602.md
```

## 2. Current V2 rule-development principle

Do not reuse old DISC performance as runtime source of truth.

Current exploration uses:

```text
M15 open-time candles
M15 entry after bar close
M5/M1 paths after entry only
M5/M15 features for rule conditions
No H1/H4/D1 condition features for the current origin candidate set
No AI/API scoring
No Discord send
No MT5 order_send
No dispatch_ready enable
```

## 3. Current exploration stages completed

### 3.1 Big-move and origin exploration

A new GOLD V2 origin-style exploration was performed to find M15/M5 states that tend to precede strong movement or favorable TP/SL outcomes.

Important outputs generated in the working environment:

```text
gold_v2_origin_reexplore_outputs.zip
gold_v2_origin_candidate_rules_selected.csv
gold_v2_origin_candidate_rules_all.csv
gold_v2_origin_feature_enrichment.csv
gold_v2_origin_base_pattern_performance.csv
```

### 3.2 Frequency and TP/SL sweeps

The initial origin candidates were tested with M1 first-touch, non-overlap, and cooldown.

TP/SL grids were expanded to include:

```text
SL25, SL50, SL75, SL100, SL125, SL150
RR1, RR1.5, RR2
```

Important outputs:

```text
gold_v2_all_origin_rr_expanded_grid_outputs.zip
gold_v2_all_origin_rr_expanded_summary.csv
gold_v2_all_origin_rr_expanded_monthly.csv
gold_v2_all_origin_rr_expanded_best_by_candidate.csv
gold_v2_all_origin_rr_expanded_top80.csv
```

### 3.3 High-win filters across all origins

All 13 origin candidates were screened for additional M15/M5 filters that can reduce trade frequency and raise win rate.

Important outputs:

```text
gold_v2_all_origin_filter_fast_outputs.zip
gold_v2_all_origin_filter_fast_all_results.csv
gold_v2_all_origin_filter_fast_highwin_shortlist.csv
gold_v2_all_origin_filter_fast_transformation_candidates.csv
gold_v2_all_origin_filter_fast_top_by_origin.csv
gold_v2_all_origin_filter_fast_top_by_direction.csv
gold_v2_all_origin_filter_fast_practical_highwin.csv
```

Representative finding:

```text
Low-win / high-frequency candidates can improve substantially when filtered.
ORIGIN_010 is not the only candidate.
ORIGIN_011, ORIGIN_004, ORIGIN_002, ORIGIN_005, ORIGIN_007, ORIGIN_003, ORIGIN_006, and ORIGIN_012 all have follow-up value.
```

### 3.4 Strict global no-overlap portfolio audit

A conservative portfolio audit was run where any open position blocks all other candidate signals until exit.

Important outputs:

```text
gold_v2_portfolio_overlap_audit_outputs.zip
gold_v2_portfolio_overlap_scenario_summary.csv
gold_v2_portfolio_overlap_monthly_summary.csv
gold_v2_portfolio_overlap_kept_trades.csv
gold_v2_portfolio_overlap_rejected_overlaps.csv
gold_v2_portfolio_overlap_selected_rules.csv
```

Key conservative results:

```text
PRACTICAL_ONE_PER_ORIGIN:
  test win rate ~73%
  test PF ~2.98
  test total R ~+79R
  avg monthly trades ~87

DIVERSIFIED_TOP1_PER_ORIGIN:
  test win rate ~73%
  test PF ~3.08
  test total R ~+83R
  avg monthly trades ~85

HIGHWIN_TOP20_ALL:
  test win rate ~75%
  test PF ~3.59
  test total R ~+85.5R
  avg monthly trades ~77
```

Caution: these are still holdout-test comparisons from a selected candidate universe, not final live proof.

## 4. Confluence-score audit added

A confluence-score audit was then run using the raw signals behind the strict overlap portfolio output.

Inputs:

```text
gold_v2_portfolio_overlap_kept_trades.csv
gold_v2_portfolio_overlap_rejected_overlaps.csv
```

Method:

```text
1. Reconstruct raw overlapping signal clusters.
2. Keep signals that overlap in time in the same cluster.
3. Score same-direction convergence instead of discarding overlaps.
4. Representative mode: use the highest-score signal in the cluster.
5. Stacked mode: sum same-direction signal outcomes as a unit-lot stacking proxy.
```

Important outputs:

```text
gold_v2_confluence_score_outputs.zip
gold_v2_confluence_score_summary.json
gold_v2_confluence_score_policy_summary.csv
gold_v2_confluence_monthly_summary.csv
gold_v2_confluence_cluster_ledger.csv
gold_v2_confluence_cluster_members.csv
gold_v2_confluence_count_bucket_summary.csv
gold_v2_confluence_top_score_policies.csv
```

Top test-policy examples from confluence audit:

```text
HIGHWIN_TOP20_ALL + stacked_min_same_count_3:
  test clusters: 39
  test win rate: 89.74%
  test PF: 21.41
  test total R: +173.5
  avg monthly clusters: 13

HIGHWIN_TOP20_ALL + representative_min_same_count_3:
  test clusters: 39
  test win rate: 89.74%
  test PF: 11.13
  test total R: +40.5
  avg monthly clusters: 13

DIVERSIFIED_TOP1_PER_ORIGIN + stacked_score_sum_ge_20:
  test clusters: 30
  test win rate: 90.0%
  test PF: 9.89
  test total R: +84.5
  avg monthly clusters: 10
```

## 5. Important interpretation

The confluence-score results are promising, but they are not a runtime rule yet.

Reasons:

```text
1. Candidate selection bias remains.
2. Confluence clusters are built from already-selected high-win/filter candidates.
3. Stacked mode assumes unit-lot additions and needs strict risk caps.
4. Representative mode is safer and should be treated as the first implementation model.
5. Need walk-forward / month-by-month validation before demo MT5 use.
```

## 6. Current preferred next step

Do not jump to live/demo send.

Next should be:

```text
GOLD V2 confluence walk-forward audit
```

Required checks:

```text
1. Build candidate/filter/confluence policies using earlier months only.
2. Test the next month.
3. Compare representative-only and stacked-same-direction modes.
4. Cap max stack count and total risk.
5. Report monthly win rate, PF, total R, max loss streak, and trade count.
```

## 7. Current safety status

```text
OpenAI API: not used for V2 candidate selection
Discord send: disabled
MT5 order_send: disabled
dispatch_ready: false
runtime gate mutation: forbidden
old GOLD docs: not implementation SOT
```
