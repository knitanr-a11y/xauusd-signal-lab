# GOLD V2 14B CoreB cluster source read and replay audit-only spec

Created: 2026-06-05

## Purpose

14A found CoreB source candidates. 14B reads the top source ledgers and carries forward the earlier 13C3/13C4 finding: `rr125_top_ledgers.csv` contains the source cluster summary, but raw-ledger-only reconstruction of `same_count` was not proven.

14B does not enable CoreB live evaluator.

## Inputs

```text
FX_OUTPUTS/gold_v2_rr125_second_core_probe_outputs/rr125_raw_signal_ledger.csv
FX_OUTPUTS/gold_v2_rr125_second_core_probe_outputs/rr125_top_ledgers.csv
FX_OUTPUTS/gold_v2_rr125_second_core_probe_outputs/rr125_filter_results.csv
FX_OUTPUTS/gold_v2_rr125_second_core_probe_outputs/rr125_recommended_filters.csv
FX_OUTPUTS/gold_v2_13c3_coreb_reconstruct_source_cluster_membership_audit_only/gold_v2_13c3_coreb_reconstruct_source_cluster_membership_summary.json
FX_OUTPUTS/gold_v2_13c4_coreb_original_clustering_script_search_audit_only/gold_v2_13c4_coreb_clustering_script_search_summary.json
```

## Checks

```text
raw source ledger exists
top ledger exists
top ledger has cluster_id and same_count
RR125_from_RR1_rules + same_count>=15 target rows are readable
raw ledger exposes the 12 BUY source rules
13C3 did not prove raw-ledger-only same_count reconstruction
13C4 did not restore original clustering script unless summary says otherwise
CoreB live remains blocked unless original clustering source is found and replayed
```

## Outputs

```text
FX_OUTPUTS/gold_v2_14b_coreb_cluster_source_read_and_replay_audit_only
```

## Expected status

Expected safe status is usually:

```text
COREB_SOURCE_TOP_LEDGER_READABLE_BUT_LIVE_REPLAY_BLOCKED_AUDIT_ONLY
```

If an original clustering algorithm is already found and proven, a later audit can advance this.

## Prohibitions

No Discord, no MT5, no AI API, no live hook, no final signal, no CoreB live enablement.
