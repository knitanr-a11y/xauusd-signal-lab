# GOLD V2 25C85 local source candidate content review audit-only spec

Created: 2026-06-08

Status: `LOCAL_SOURCE_CANDIDATE_CONTENT_REVIEW_SPEC_READY_AUDIT_ONLY`

## Purpose

25C84 deep reconstruction did not recover the CoreB representative logic from raw/top numerical searches, but it produced a local keyword scan pointing to candidate source/config files.

25C85 reads those local files directly and classifies whether any file contains the actual raw -> top-ledger generator logic.

## Inputs

Resolve from `Files/FX_OUTPUTS`:

```text
25c84_summary.json
25c84_logic_keyword_scan.csv
```

Then read candidate files from the repository paths listed in `25c84_logic_keyword_scan.csv`.

## What counts as a true source candidate

A true source candidate should contain, in one file or a clearly connected script/config pair:

```text
read rr125_raw_signal_ledger.csv
compute/assign cluster_id
compute/assign same_count or source_rule_count
select representative top_candidate_id / profit
write rr125_top_ledgers.csv or equivalent
```

Files that only read already-frozen ledgers or only audit existing outputs are not source recovery.

## Outputs

```text
GOLD_V2_25C85_LOCAL_SOURCE_CANDIDATE_CONTENT_REVIEW_AUDIT_ONLY_REPORT.md
25c85_summary.json
25c85_input_inventory.csv
25c85_candidate_file_classification.csv
25c85_candidate_context_snippets.csv
25c85_decision_matrix.csv
25c85_next_step_plan.csv
```

## Guardrails

- Do not call a keyword hit source recovery.
- Do not promote audit-generated scripts to original logic.
- Do not use A002.
- Do not enable live evaluator.
- No Discord/MT5/AI/live/final actions.
