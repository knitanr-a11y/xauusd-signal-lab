# GOLD V3 Stage216 Feature Drift Monitoring Rule Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage216 defines how feature drift warnings from Stage212 should be classified before any live release.

## Inputs

- Stage212 decision
- Stage212 feature drift warning rows
- Stage215 signal replay decision

## Outputs

- `gold_v3_216_feature_drift_monitoring_rules.csv`
- `gold_v3_216_feature_drift_summary.csv`
- `gold_v3_216_current_drift_classification.csv`
- `gold_v3_216_validation_checks.csv`
- `gold_v3_216_feature_drift_monitoring_plan.md`
- `gold_v3_216_summary.json`
- `gold_v3_216_decision.csv`
- `paste_me.txt`

## Classification policy

- route parity mismatch: BLOCK
- feature drift with route parity pass: WARN
- feature drift on a SIGNAL row: REVIEW before any send/order enablement
- repeated drift across multiple audits: REVIEW and merge freshness investigation
- NO_SIGNAL rows with unchanged route: WARN only

## Guardrails

- audit-only
- dry-run only
- no live release approval
- no source CSV mutation
- no actual import
- no execution
- no send
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify
