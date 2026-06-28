# GML1 Loss-Feature Pruning V2 Compute Addendum

Date: 2026-06-28
Mode: audit-only

This addendum is frozen before greedy rule-subset selection and before reading 2025 or 2026 results.

Composite enumeration creates many expressions with identical or nearly redundant validation roles. The following deterministic compaction is applied after the frozen 2024 validation gate:

1. Rules with the same complete 2024 raw-proposal hit mask are reduced to one rule using fewer conditions, then larger 2023 support, then lexical canonical expression.
2. Within each frozen scope (`candidate_id` or `direction`), rank the remaining rules by:
   - more negative 2024 total Strong R inside the excluded region;
   - lower 2024 Strong PF inside the excluded region;
   - higher 2024 loss rate;
   - larger 2024 hit count;
   - fewer conditions;
   - lexical rule ID.
3. Retain at most 300 rules per candidate-specific scope and at most 500 rules per direction-pooled scope.
4. Greedy subset selection tests every retained rule at every step using the exact cross-family dedup then candidate one-position result.

This compaction uses 2024 validation information only. It does not read 2025 or 2026 and does not change any rule expression or threshold.
