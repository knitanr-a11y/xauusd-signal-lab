# GOLD V2 25C51 dry-run source concretion review implementation note

Date: 2026-06-08

Repo: `knitanr-a11y/xauusd-signal-lab`

## Implemented step

```text
25C51_COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_AUDIT_ONLY
```

Mode: audit-only source concretion review.

## What was implemented

Added a repository-backed audit-only Python script and BAT launcher for 25C51.

```text
scripts/gold_v2_runtime/audit_gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only.py
scripts/gold_v2_runtime/bat/25C51_COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_AUDIT_ONLY.bat
```

The BAT keeps the command window open with `pause` on both success and STOP/error paths.

## Input files

25C51 reads from:

```text
FX_OUTPUTS/gold_v2_25c50_coreb_g1_representative_dry_run_readiness_review_audit_only/
```

Required files:

```text
02_25c50_representative_dry_run_readiness_review_summary.json
04_25c50_contract_audit.csv
05_25c50_readiness_matrix.csv
06_25c50_unresolved_source_matrix.csv
07_25c50_execution_boundary_matrix.csv
08_25c50_gates.csv
09_25c50_next_step_plan.csv
10_25c50_handoff_notes.csv
```

## Output directory

```text
FX_OUTPUTS/gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only/
```

Expected outputs:

```text
00_不要_25c51_file_request_list.csv
01_25c51_GOLD_V2_COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_AUDIT_ONLY_REPORT.md
02_25c51_dry_run_source_concretion_review_summary.json
03_25c51_input_audit.csv
04_25c51_contract_audit.csv
05_25c51_source_search_spec_matrix.csv
06_25c51_source_candidate_matrix.csv
07_25c51_source_selection_matrix.csv
08_25c51_execution_boundary_matrix.csv
09_25c51_gates.csv
10_25c51_next_step_plan.csv
11_25c51_handoff_notes.csv
```

## Source-of-truth facts

25C51 preserves the 25C50 facts:

```text
source_concretion_required = true
exact_baseline_replay_signal_source_confirmed = false
future_dry_run_execution_allowed = false
representative_variant_code = A002
representative_approval_status = NOT_APPROVED_REVIEW_ONLY
```

## Candidate search behavior

25C51 scans local `FX_OUTPUTS` only by path/name scoring. It looks for CSV/JSON/MD artifacts whose paths include terms such as:

```text
25c10
replay
signal
rows
coreb
g1
baseline
```

The script does not read raw OHLC, does not reconstruct signals, and does not approximate exploration logic.

## Result meaning

A top candidate is not a confirmed source.

Expected source status:

```text
source_confirmed = false
source_candidate_review_required = true
future_dry_run_execution_allowed = false
```

## Success status

```text
COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_READY_AUDIT_ONLY_SOURCE_CANDIDATE_REVIEW_REQUIRED
```

## Stop conditions

```text
25C51_STOP_MISSING_INPUT_AUDIT_ONLY
25C51_STOP_25C50_CONTRACT_UNSAFE_AUDIT_ONLY
25C51_STOP_SOURCE_SEARCH_UNSAFE_AUDIT_ONLY
```

## Run order

From the repository root:

```bat
scripts\gold_v2_runtime\bat\25C51_COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_AUDIT_ONLY.bat
```

Or:

```bat
python scripts\gold_v2_runtime\audit_gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only.py
```

## Next step

25C51 may recommend only this next audit-only source candidate review step:

```text
25C52_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY
```

25C52 must review/bind the source candidate before any dry-run execution can be considered.

## Explicit boundaries

25C51 does not confirm any source candidate, approve A002/A004 or any variant, execute replay, execute dry-run, change conditions, change sources, recover sources, run live paths, call AI API, notify Discord, place MT5 orders, run live hooks, or create final signals.

NO_SIGNAL Discord notification remains disabled.
