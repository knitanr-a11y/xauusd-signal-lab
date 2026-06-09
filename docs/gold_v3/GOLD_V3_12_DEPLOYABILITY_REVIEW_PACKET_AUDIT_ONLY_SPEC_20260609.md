# GOLD V3 12 deployability review packet audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 12 extracts only the GOLD V3 11 rule-expression preview rows that are ready for human deployability review.

This is not final approval. It prepares a human-decision packet and keeps all rejected/deferred rows auditable.

## Required upstream

```text
GOLD_V3_11_RULE_EXPRESSION_PREVIEW_READY_AUDIT_ONLY
```

## Inputs

```text
Files/FX_OUTPUTS/gold_v3/11_rule_expression_preview_audit_only/gold_v3_11_summary.json
Files/FX_OUTPUTS/gold_v3/11_rule_expression_preview_audit_only/gold_v3_11_rule_expression_preview_rows.csv
Files/FX_OUTPUTS/gold_v3/11_rule_expression_preview_audit_only/gold_v3_11_boundary_consensus_diagnostics.csv
```

## Review-ready filter

Rows are included in the deployability review packet only when:

```text
readiness_label in {
  REVIEW_READY,
  REVIEW_READY_WITH_NEGATIVE_FOLD_RISK
}
```

Rows with these labels are excluded from the deployability review packet and remain diagnostic-only:

```text
MANUAL_REVIEW_BUCKET_UNSTABLE
MANUAL_REVIEW_BOUNDARY_UNSTABLE
MANUAL_REVIEW_BOUNDARY_MISSING
REVIEW_ONLY_NOT_DEPLOYABLE_RAW_PRICE_LEVEL
```

## Output decision fields

Each review-ready row receives an empty human decision slot:

```text
human_decision = PENDING_HUMAN_REVIEW
allowed_decisions = APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY | REJECT | REQUEST_MORE_AUDIT
```

None of these are set automatically.

`APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY` is not live approval and not final candidate approval.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/12_deployability_review_packet_audit_only/
```

Output files:

```text
GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_AUDIT_ONLY_REPORT.md
gold_v3_12_summary.json
gold_v3_12_input_inventory.csv
gold_v3_12_deployability_review_packet.csv
gold_v3_12_deferred_candidate_diagnostics.csv
gold_v3_12_readiness_summary.csv
gold_v3_12_decision_matrix.csv
gold_v3_12_blocker_matrix.csv
```

ZIP output is disabled.

## Guardrails

- GOLD V3 only.
- No GOLD V2 selected/source/final/arbitration artifacts.
- Human-decision packet only.
- No automatic approval.
- No final candidate approval.
- No threshold finalization.
- No model training.
- No signal generation.
- No ZIP output.
- External actions remain OFF.
