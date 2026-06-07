# GOLD V2 25B9 CoreB feature source discovery audit spec

Date: 2026-06-07
Step: `25B9_COREB_FEATURE_SOURCE_DISCOVERY_AUDIT_ONLY`
Mode: audit-only source discovery, no feature reconstruction

## Purpose

25B8 showed that the raw signal ledger has 18 columns and none of the 38 condition-object feature fields required by CoreB frozen rules.

25B9 scans local repo files and FX_OUTPUTS for a source-of-truth feature data file or verified builder script that covers the required fields.

25B9 does not rebuild features, does not execute replay, does not mutate source artifacts, and does not unblock CoreB.

## Inputs

```text
Files/FX_OUTPUTS/gold_v2_25b8_coreb_condition_object_dry_run_plan_audit_only/gold_v2_25b8_coreb_condition_object_dry_run_plan_summary.json
Files/FX_OUTPUTS/gold_v2_25b8_coreb_condition_object_dry_run_plan_audit_only/gold_v2_25b8_required_feature_manifest.csv
Files/FX_OUTPUTS/gold_v2_25b8_coreb_condition_object_dry_run_plan_audit_only/gold_v2_25b8_missing_feature_source_requirements.csv
```

## Scan roots

Default runtime scan roots:

```text
repo root
Files/FX_OUTPUTS
```

The script may also accept explicit `--scan-root` paths.

## Required outputs

```text
GOLD_V2_25B9_COREB_FEATURE_SOURCE_DISCOVERY_AUDIT_ONLY_REPORT.md
gold_v2_25b9_input_audit.csv
gold_v2_25b9_scan_root_audit.csv
gold_v2_25b9_feature_source_candidate_inventory.csv
gold_v2_25b9_feature_coverage_by_candidate.csv
gold_v2_25b9_builder_script_hits.csv
gold_v2_25b9_missing_features_after_discovery.csv
gold_v2_25b9_file_request_list.csv
gold_v2_25b9_next_step_plan.csv
gold_v2_25b9_coreb_feature_source_discovery_summary.json
```

## Discovery rules

25B9 may inspect schemas/headers/text only:

```text
CSV: header only
Parquet: schema only when available
JSON/PY/MD/TXT: text search for required feature names
```

It must not calculate feature values, infer missing feature values, or use target rows to fit source behavior.

## File request output format

The report must put unnecessary files first, then necessary files:

```text
【不要・貼らなくてOK】
1. ...

【必要・貼ってほしい】
1. ...
```

## Safety

CoreB remains blocked. Source recovery execution, source mutation, final signal, live hook, Discord, MT5, and AI remain off.

Expected status when no complete feature source is accepted:

```text
COREB_FEATURE_SOURCE_DISCOVERY_COMPLETED_AUDIT_ONLY_SOURCE_NOT_ACCEPTED
```

Expected status if a candidate source covers all required fields:

```text
COREB_FEATURE_SOURCE_DISCOVERY_COMPLETED_AUDIT_ONLY_CANDIDATE_REVIEW_REQUIRED
```
