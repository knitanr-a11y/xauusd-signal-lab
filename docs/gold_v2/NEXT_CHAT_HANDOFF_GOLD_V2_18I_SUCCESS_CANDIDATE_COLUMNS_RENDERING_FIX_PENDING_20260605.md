# GOLD V2 handoff after 18I success / candidate_columns rendering fix pending

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Current completed step: `18I_TIER2_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_DESIGN_AUDIT_ONLY`

## Latest status

18I completed successfully with status:

`TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_DESIGN_READY_AUDIT_ONLY_SOURCE_RECOVERY_BLOCKED`

18I outputs confirm:

- dry_run_design_ready: true
- selected_artifacts: 5
- recipe_rows: 45
- dry_run_implemented: false
- source_rows_read: false
- row_hash_computed: false
- source_recovery_executed: false
- implementation_allowed: false
- oh_lc_replay_allowed: false
- live_enabled: false
- final_signal_allowed: false
- external actions: all false
- no_signal_discord_notified: false

## Important caution before 18J

The 18I report is logically successful, but the dry-run field recipe rendered `candidate_columns` as `nan` for derived fields.

Cause:

- The 18I script reads 18H CSV output with pandas.
- Blank `direct_column` cells are read as NaN.
- The recipe code converts NaN to string `nan` before falling back to `candidate_columns_present`.
- Therefore, derived-field candidate columns are present in 18H, but appear as `nan` in 18I report.

This is a rendering/data-cleaning issue in the 18I report generation, not a source recovery or safety issue.

## Attempted fix

A patch was prepared to add helper functions similar to:

- clean NaN/None/blank cells to empty string
- choose direct_column if present, otherwise candidate_columns_present

However, updating the 18I Python script through the GitHub connector was blocked by the connector safety checks.

## Required next action

Before generating 18J, fix and rerun 18I so that `gold_v2_18i_dry_run_field_recipe.csv` shows real candidate columns instead of `nan` for derived fields.

The intended correction is in `scripts/gold_v2_runtime/audit_gold_v2_18i_tier2_source_identity_extraction_dry_run_design_audit_only.py` around the recipe creation logic:

Current problematic logic:

`cols = str(r.get("direct_column", "")) or str(r.get("candidate_columns_present", ""))`

Required behavior:

- If direct_column is blank or NaN, use candidate_columns_present.
- If candidate_columns_present is also blank or NaN, use an empty string.

## Do not proceed to 18J until fixed

18J should be generated only after corrected 18I output is available, because 18J relies on the field recipe.

## Safety state preserved

Do not do any of the following before explicit later gates:

- source row reads
- row hash computation
- source identity recovery
- OHLC reconstruction
- predicate/arbitration implementation
- replay
- live/final enablement
- Discord/MT5/AI/live hook actions
- NO_SIGNAL Discord notification
