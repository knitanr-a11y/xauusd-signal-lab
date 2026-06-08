# NEXT CHAT HANDOFF - GOLD V2 25C82 done, 25C83 CoreB historical report-only

Created: 2026-06-08

## Official local status

`25C82_LOCAL_COREB_HISTORICAL_SOT_REPORT_PACKAGE_READY_AUDIT_ONLY_LIVE_BLOCKED`

This supersedes the earlier local stop at 25C79 for the CoreB historical-report path only. It does **not** unblock CoreB live evaluator or source recovery.

## Core guardrails

- GOLD V2 remains audit-only.
- REQUEST_MORE_AUDIT is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation remains prohibited.
- Discord / MT5 / AI API / live hook / live evaluator / final signal remain OFF unless explicitly approved.
- NO_SIGNAL must not notify Discord.
- A002 remains demoted to auxiliary evidence only.

## What 25C82 established locally

CoreB historical SOT is locally reportable from the 125-row direct SOT.

Source:

```text
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
```

Top-ledger equivalence:

```text
rr125_top_ledgers.csv
policy == RR125_from_RR1_rules
filter == same_count>=15
```

Final SOT join key:

```text
dataset + entry_time + coreb_cluster_id + coreb_profit_r
```

## CoreB historical SOT metrics

| dataset | count | wins | losses | win_rate | pf | total_r |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2025 | 104 | 75 | 29 | 72.1154% | 3.443512 | 143.0174667 |
| 2026 | 21 | 17 | 4 | 80.9524% | 5.153846 | 40.5 |
| total | 125 | 92 | 33 | 73.6% | 3.687740 | 183.5174667 |

## 25C82 PASS evidence

25C82 final status checks all passed:

- 25C81 upstream status PASS.
- upstream files present PASS.
- CoreB total count 125 PASS.
- top-ledger parity PASS.
- final SOT join parity PASS.
- A002 not used for CoreB metrics PASS.
- CoreB live evaluator allowed false PASS.
- final signal allowed false PASS.

## A002 position

A002 is not CoreB.

A002 role is now:

```text
DEMOTED_AUXILIARY_ONLY
```

Do not use A002 WR/PF for CoreB performance.

## Remaining blocker

CoreB live evaluator remains blocked because the source logic for future/OHLC generation of the following has not been recovered:

```text
same_count
cluster_id
representative profit
```

This means:

- Historical CoreB SOT report: allowed.
- Live CoreB from current/future OHLC: blocked.
- Final signal: blocked.

## Next recommended step

Proceed with either:

```text
25C83_CLUSTER_REPRESENTATIVE_LOGIC_RECOVERY_AUDIT_ONLY
```

or, if the goal is to pause live recovery and preserve a clean audit handoff:

```text
25C83_COREB_HISTORICAL_REPORT_ONLY_HANDOFF_AUDIT_ONLY
```

Recommended now:

```text
25C83_COREB_HISTORICAL_REPORT_ONLY_HANDOFF_AUDIT_ONLY
```

## Do not do next unless explicitly approved

- Do not enable live evaluator.
- Do not send Discord notifications.
- Do not place MT5 orders.
- Do not call AI API.
- Do not promote CoreB historical SOT into a live/final signal.
- Do not treat A002 as CoreB performance.
