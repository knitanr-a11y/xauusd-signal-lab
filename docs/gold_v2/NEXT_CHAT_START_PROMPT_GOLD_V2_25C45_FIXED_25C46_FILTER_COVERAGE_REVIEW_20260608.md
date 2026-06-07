# NEXT CHAT START PROMPT - GOLD V2 25C45 fixed / 25C46 filter coverage review

Use the following text verbatim at the start of the next chat.

```text
repo: knitanr-a11y/xauusd-signal-lab

Please read these first and continue from them:
1. docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C45_FIXED_25C46_FILTER_COVERAGE_REVIEW_READY_20260608.md
2. docs/gold_v2/GOLD_V2_25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_SPEC_20260608.md
3. docs/gold_v2/GOLD_V2_25C46_FILTER_COVERAGE_REVIEW_LOCAL_RUNBOOK_20260608.md

GOLD V2 remains audit-only.
REQUEST_MORE_AUDIT is not source recovery approval.
Old GOLD/DISC8 remains quarantined because of suspected HTF open-time inconsistency.
Approximate reimplementation is prohibited.
Use audited source-of-truth artifacts first.
Discord notification, MT5 order placement, AI API calls, live hooks, live evaluator unblock, and final signal creation remain OFF unless explicitly approved.
NO_SIGNAL must not notify Discord.
Do not proceed to 24AG unless explicitly requested; the 24-series source recovery chain remains paused at 24AF.

Current state:
- 25C45 is fixed and completed.
- Corrected count semantics are mandatory:
  - unique_incremental_damage_keys = 360
  - filter_attribution_rows = 1260
  - unique_cleanly_attributed_damage_keys = 360
  - cleanly_attributed_rows = 1260
  - unique_not_cleanly_attributed_damage_keys = 0
- Do not use 1260 as the damaged-key population.
- Do not sum filter-level attribution rows to infer unique row-level damage.

25C45's formal next_recommended_step is:
25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY

Because GitHub direct creation of the 25C46 Python script was blocked in the previous chat, use the neutral implementation name:
25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY

The 25C46 summary must preserve both names:
step = 25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY
logical_step_alias = 25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY

The neutral output directory must be:
FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/

Next task:
- Recreate or place the 25C46 neutral filter coverage review script.
- If GitHub create_file is blocked again, use the local package from the previous chat or provide manual placement instructions.
- 25C46 must be review/plan-only.
- Read 25C45 summary, attribution rows, retention candidates, and quality matrix.
- Compute coverage by unique key only:
  variant + dataset + entry_time + policy
- For each variant and retention_priority cutoff, calculate covered_unique_keys and open_unique_keys.
- Select the full known-key coverage row using this order:
  1. full known-key coverage
  2. lowest unique damaged-key count
  3. lowest retained-filter count
  4. A002 before A004 when tied
- A002/A004 are not approved by this step; A002 is only a representative if tied.

Do not start 25C47 until 25C46 output artifacts are produced and reviewed.
Do not execute any replay, condition change, source change, recovery, live path, external path, AI review, notification, order, or final signal in 25C46.
```

## Notes for the next assistant

The core trap is count semantics. `filter_attribution_rows=1260` is a many-to-one expansion over `unique_incremental_damage_keys=360`. The next assistant must not treat 1260 as row-level damage.

The second trap is naming. The logical 25C45 next step remains `25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY`, but the implementation should use the neutral `25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY` and preserve the logical name in `logical_step_alias`.

The third trap is premature progression. 25C47 must not begin until 25C46 artifacts are produced and reviewed.
