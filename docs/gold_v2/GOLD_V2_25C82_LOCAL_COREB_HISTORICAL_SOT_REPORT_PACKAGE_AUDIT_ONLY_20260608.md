# GOLD V2 25C82 local CoreB historical SOT report package audit-only spec

Created: 2026-06-08

Status: `LOCAL_COREB_HISTORICAL_SOT_REPORT_PACKAGE_SPEC_READY_AUDIT_ONLY`

## Purpose

Package the 25C81 local PASS result into a local-official CoreB historical SOT report.

This step does not perform new strategy selection. It summarizes and freezes the local fact that CoreB 125 historical SOT rows are locally replayed and internally consistent.

## Required upstream state

25C81 must be present locally with:

```text
status = COREB_DIRECT_SOT_LOCAL_REPLAY_PASSED_AUDIT_ONLY_LIVE_BLOCKED
coreb_direct_sot_local_official_ready = true
a002_used_for_coreb_metrics = false
```

## CoreB historical SOT state to freeze

```text
CoreB historical SOT source:
  gold_v2_13c_coreb_rr125_selected_top_ledgers.csv

Top-ledger equivalence:
  rr125_top_ledgers.csv
  policy == RR125_from_RR1_rules
  filter == same_count>=15

CoreB-specific SOT join key:
  dataset + entry_time + coreb_cluster_id + coreb_profit_r
```

## Expected frozen metrics

```text
2025: count 104, wins 75, losses 29, WR 72.1154%, PF 3.443512, total R 143.0174667
2026: count 21, wins 17, losses 4, WR 80.9524%, PF 5.153846, total R 40.5
total: count 125, wins 92, losses 33, WR 73.6%, PF 3.687740, total R 183.5174667
```

## Required report content

25C82 should produce:

- CoreB historical SOT final status.
- 25C81 local replay PASS evidence.
- Direct metrics by dataset and total.
- Top-ledger filter parity PASS.
- 13C final SOT and final portfolio join parity PASS.
- A002 demotion statement.
- Live evaluator blocker carry-forward.
- External action guardrails.

## Status if successful

```text
LOCAL_COREB_HISTORICAL_SOT_REPORT_PACKAGE_READY_AUDIT_ONLY_LIVE_BLOCKED
```

## Guardrails

- A002 remains auxiliary evidence only.
- CoreB historical SOT report is allowed.
- CoreB live evaluator remains blocked.
- Discord, MT5, AI API, live hook, and final signal remain OFF.
- No source recovery approval is implied.

## Next recommended step

After 25C82 passes, choose one:

```text
25C83_CLUSTER_REPRESENTATIVE_LOGIC_RECOVERY_AUDIT_ONLY
```

or

```text
25C83_COREB_HISTORICAL_REPORT_ONLY_HANDOFF_AUDIT_ONLY
```
