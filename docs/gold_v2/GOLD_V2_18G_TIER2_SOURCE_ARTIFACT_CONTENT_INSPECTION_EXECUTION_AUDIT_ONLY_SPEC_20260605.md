# GOLD V2 18G TIER2 source artifact content inspection execution audit-only specification

Date: 2026-06-05
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `18G_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_EXECUTION_AUDIT_ONLY`
Mode: audit-only
Authorization basis: user explicitly approved proceeding after 18F.

## Purpose

18G executes read-only content inspection of the 13 candidate artifacts carried by 18F.

18G is content-inspection audit-only. It may inspect file structure, CSV schemas, row counts, JSON key sets, ZIP member lists, Markdown headings, and required identity field presence. It must not recover the final TIER2 row-level source identity, must not synthesize source rows, must not reconstruct from OHLC, must not implement predicates, must not implement arbitration, must not evaluate OHLC, must not run replay, must not rediscover candidates, must not create final signals, must not send Discord notifications, must not place MT5 orders, must not call AI API, and must not install a live hook.

## Source of truth

Use only audited 18F outputs:

1. `FX_OUTPUTS/gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_audit_only/gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_summary.json`
2. `FX_OUTPUTS/gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_audit_only/gold_v2_18f_authorization_gate_checks.csv`
3. `FX_OUTPUTS/gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_audit_only/gold_v2_18f_authorization_matrix.csv`
4. `FX_OUTPUTS/gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_audit_only/gold_v2_18f_blocked_execution_plan.csv`
5. `FX_OUTPUTS/gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_audit_only/gold_v2_18f_required_next_gates.csv`
6. `FX_OUTPUTS/gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_audit_only/gold_v2_18f_blockers.csv`
7. `FX_OUTPUTS/gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_audit_only/gold_v2_18f_safety_matrix.csv`

Do not use OHLC. Do not rediscover candidates. Do not infer a recovered row-level identity beyond structural field-presence observations.

## Expected input state

18F must have status:

`TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_AUTHORIZATION_GATE_READY_AUDIT_ONLY_CONTENT_INSPECTION_BLOCKED`

Expected 18F state:

- authorization gate ready true
- selected priority artifacts 13
- blocked execution rows 13
- content inspection authorized false in 18F output
- content inspection executed false in 18F output
- source recovery executed false
- implementation allowed false
- OHLC replay allowed false
- live enabled false
- final signal false
- all external actions false
- NO_SIGNAL Discord notification false

The 18F output remains a blocked gate. The permission to create and run 18G is provided externally by the current user instruction.

## Inspection policy

18G may perform only read-only structural inspection:

- CSV: header, columns, row count, required identity field presence.
- JSON: top-level keys, nested key names at limited depth, required identity field presence.
- ZIP: member names, member suffixes, member sizes, required identity-field-like member names.
- Markdown: headings, required identity-field term presence in headings/text.

18G must not:

- choose a final source row,
- emit a recovered TIER2 identity,
- write executable rule payloads,
- run OHLC replay,
- implement any live/final/external workflow.

## Output folder

`FX_OUTPUTS/gold_v2_18g_tier2_source_artifact_content_inspection_execution_audit_only`

## Main outputs

- `GOLD_V2_18G_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_EXECUTION_AUDIT_ONLY_REPORT.md`
- `gold_v2_18g_tier2_source_artifact_content_inspection_execution_summary.json`
- `gold_v2_18g_input_audit.csv`
- `gold_v2_18g_content_inspection_checks.csv`
- `gold_v2_18g_inspected_artifact_results.csv`
- `gold_v2_18g_csv_schema_results.csv`
- `gold_v2_18g_json_key_results.csv`
- `gold_v2_18g_zip_member_results.csv`
- `gold_v2_18g_markdown_heading_results.csv`
- `gold_v2_18g_required_identity_field_presence.csv`
- `gold_v2_18g_required_next_gates.csv`
- `gold_v2_18g_blockers.csv`
- `gold_v2_18g_safety_matrix.csv`

## Success status

`TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_EXECUTED_AUDIT_ONLY_SOURCE_RECOVERY_BLOCKED`

This means read-only structural content inspection has executed. It does not mean the TIER2 row-level source identity has been recovered.

## Stop conditions

Stop if:

- any required input is missing,
- 18F status is not expected,
- 18F checks or safety contain STOP,
- no candidate execution rows are available,
- any source recovery or implementation/live/final/external action flag is true,
- NO_SIGNAL Discord notification is true.

## Recommended next step after success

After 18G success, the next possible step is:

`18H_TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_PLAN_AUDIT_ONLY`

18H must remain a plan/audit-only step unless explicit approval is separately provided for source identity extraction. Source recovery execution must remain blocked after 18G.
