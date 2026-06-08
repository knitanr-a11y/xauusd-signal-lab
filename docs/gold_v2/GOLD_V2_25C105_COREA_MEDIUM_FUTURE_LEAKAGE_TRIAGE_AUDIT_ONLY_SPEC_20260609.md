# GOLD V2 25C105 CoreA/MEDIUM future leakage triage audit-only spec

Created: 2026-06-09

Status: `COREA_MEDIUM_FUTURE_LEAKAGE_TRIAGE_SPEC_READY_AUDIT_ONLY`

## Purpose

CoreB representative profit binding is blocked because the non-oracle route does not reproduce `top_profit` in a live-safe way. 25C100/25C104 showed that prefix-only and rule-text historical keys are not sufficient for live recovery.

The user asked whether CoreA and MEDIUM may have the same future-information issue because they were produced in the same exploration family.

25C105 is a **fast triage only**. It does not replay full CoreA/MEDIUM logic and does not approve source recovery. It inventories CoreA/MEDIUM artifacts and scans for obvious future/outcome/profit-selection dependencies.

## Scope

Scan local repository and `Files/FX_OUTPUTS` for files whose path or content references:

```text
CoreA, core_a, corea, frozen_coreA
MEDIUM, medium, arbitration, frozen_medium
```

Classify findings into:

```text
CoreA
MEDIUM
both_or_unknown
```

## Suspicious token families

Hard future/outcome tokens:

```text
exit_time, exit_price, close_time, close_price, future, lookahead, leakage, outcome, result, win, loss, hit, tp_hit, sl_hit, mae, mfe, duration, holding
```

Profit/selection tokens:

```text
profit, profit_r, top_profit, realized, pnl, best, max_profit, min_profit, selected, top_candidate, representative, rank, sort, argmax, argmin
```

MEDIUM arbitration tokens:

```text
arbitration, final_sot, final_signal, choose, chosen, prefer, priority, tie_break, compare
```

Live-safety markers:

```text
audit_only, live_blocked, source_recovery_approved, live_evaluator_allowed, final_signal_allowed
```

## Input assumptions

No specific artifact is required. The script must work with whatever local files are present.

It must not call AI APIs, Discord, MT5, live hooks, live evaluator, or final signal.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c105_corea_medium_future_leakage_triage_audit_only
```

Output files:

```text
GOLD_V2_25C105_COREA_MEDIUM_FUTURE_LEAKAGE_TRIAGE_AUDIT_ONLY_REPORT.md
25c105_summary.json
25c105_file_inventory.csv
25c105_suspicious_file_hits.csv
25c105_component_risk_summary.csv
25c105_decision_matrix.csv
25c105_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c105_corea_medium_future_leakage_triage_audit_only.zip
```

## Status names

If no CoreA/MEDIUM files are found:

```text
COREA_MEDIUM_TRIAGE_NO_SOURCE_FILES_FOUND_AUDIT_ONLY_LIVE_BLOCKED
```

If CoreA or MEDIUM files include hard future/outcome/profit-selection tokens:

```text
COREA_MEDIUM_FUTURE_LEAKAGE_TRIAGE_RISK_FOUND_AUDIT_ONLY_LIVE_BLOCKED
```

If only live-safety markers are found and no suspicious tokens appear:

```text
COREA_MEDIUM_FUTURE_LEAKAGE_TRIAGE_NO_OBVIOUS_RISK_FOUND_AUDIT_ONLY_LIVE_BLOCKED
```

Even `NO_OBVIOUS_RISK_FOUND` does not approve source recovery. It only means this lightweight text/column scan did not find obvious leakage markers.

## Success criteria

- Produce inventory and risk summary quickly.
- Keep CoreA/MEDIUM live blocked.
- Identify whether deeper replay is needed and for which component.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB/CoreA/MEDIUM metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not infer safety from absence of tokens alone.
