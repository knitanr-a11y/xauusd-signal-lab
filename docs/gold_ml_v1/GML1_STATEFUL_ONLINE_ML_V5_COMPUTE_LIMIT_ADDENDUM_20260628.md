# GML1 Stateful Online ML V5 Compute-Limit Addendum

Date: 2026-06-28
Mode: audit-only

The pre-registered `EXTRA_TREES_STABLE` configuration requires nine 300-tree estimators for each monthly global-plus-direction bundle. The first 2024 month did not complete within the bounded interactive audit run after the complete Logistic/Ridge cache had been generated, and no ExtraTrees performance result was inspected.

Therefore:

- V5 is completed using the pre-registered `LOGISTIC_RIDGE` family only.
- `EXTRA_TREES_STABLE` status is `NOT_EVALUATED_COMPUTE_LIMIT`, not failed and not promoted.
- Tree count, depth and leaf parameters are not reduced after the fact.
- The stateful-history, monthly training-mode, architecture, score-behavior, retention and probability grids remain unchanged.
- 2025 and 2026 remain unavailable to configuration selection.
- A later tree experiment would require a separately versioned contract and must not use V5 confirmation or diagnostic results for parameter design.
