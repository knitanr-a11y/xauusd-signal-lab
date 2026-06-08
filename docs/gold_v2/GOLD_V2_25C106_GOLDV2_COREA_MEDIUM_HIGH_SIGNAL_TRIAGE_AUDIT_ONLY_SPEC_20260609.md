# GOLD V2 25C106 scoped CoreA/MEDIUM high-signal triage audit-only spec

Created: 2026-06-09

Status: `GOLDV2_COREA_MEDIUM_HIGH_SIGNAL_TRIAGE_SPEC_READY_AUDIT_ONLY`

## Purpose

25C105 found broad CoreA/MEDIUM future-leakage risk markers:

```text
status = COREA_MEDIUM_FUTURE_LEAKAGE_TRIAGE_RISK_FOUND_AUDIT_ONLY_LIVE_BLOCKED
corea_medium_files_found = 1085
hard_future_hit_files = 475
profit_selection_hit_files = 429
medium_arbitration_hit_files = 759
```

However, 25C105 intentionally scanned broadly and includes older/non-GOLD-V2 items such as `CORE_AB`, AI guardrail docs, strict7, and general research files. 25C106 narrows the result to high-signal GOLD V2 CoreA/MEDIUM evidence by reusing 25C105 output files only.

This is fast triage only. It does not replay CoreA/MEDIUM and does not approve source recovery.

## Source-of-truth inputs

Use local 25C105 outputs only:

```text
25c105_summary.json
25c105_file_inventory.csv
25c105_suspicious_file_hits.csv
25c105_component_risk_summary.csv
25c105_decision_matrix.csv
25c105_blocker_matrix.csv
```

Required upstream status:

```text
25c105_summary.status = COREA_MEDIUM_FUTURE_LEAKAGE_TRIAGE_RISK_FOUND_AUDIT_ONLY_LIVE_BLOCKED
```

## High-signal filter

A file is high-signal if:

```text
relative_path contains docs/gold_v2 or scripts/gold_v2_runtime or FX_OUTPUTS/gold_v2
and relative_path or token/snippet contains corea, core_a, coreb, medium, arbitration, frozen_core, final_sot, live_evaluator
```

Exclude obvious non-GOLD-V2 families from high-signal scoring:

```text
GOLD_H1H4_BEAR
STRICT_7
gold_strict_7
AI_EVALUATION_GUARDRAILS
mochipoyo
multi_strategy
btc
```

The excluded rows are still output for transparency.

## Evidence classes

Classify high-signal rows into:

```text
hard_future_or_outcome
profit_or_representative_selection
medium_arbitration_or_final_sot
safety_marker_only
```

Rows with only safety markers and no suspicious token are not risk evidence.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c106_goldv2_corea_medium_high_signal_triage_audit_only
```

Output files:

```text
GOLD_V2_25C106_GOLDV2_COREA_MEDIUM_HIGH_SIGNAL_TRIAGE_AUDIT_ONLY_REPORT.md
25c106_summary.json
25c106_input_inventory.csv
25c106_high_signal_file_inventory.csv
25c106_excluded_noise_inventory.csv
25c106_high_signal_suspicious_hits.csv
25c106_high_signal_component_risk_summary.csv
25c106_decision_matrix.csv
25c106_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c106_goldv2_corea_medium_high_signal_triage_audit_only.zip
```

## Status names

If inputs are missing or upstream status fails:

```text
GOLDV2_COREA_MEDIUM_HIGH_SIGNAL_TRIAGE_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If high-signal suspicious hits remain for CoreA or MEDIUM:

```text
GOLDV2_COREA_MEDIUM_HIGH_SIGNAL_RISK_REMAINS_AUDIT_ONLY_LIVE_BLOCKED
```

If broad 25C105 risk is mostly excluded as noise and no high-signal rows remain:

```text
GOLDV2_COREA_MEDIUM_HIGH_SIGNAL_NO_OBVIOUS_RISK_AFTER_NOISE_FILTER_AUDIT_ONLY_LIVE_BLOCKED
```

Even `NO_OBVIOUS_RISK` does not approve source recovery.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB/CoreA/MEDIUM metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not infer safety from absence of high-signal tokens alone.
