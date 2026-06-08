# GOLD V2 25C80 local sync from 25C79 audit-only plan

Created: 2026-06-08

Status: `LOCAL_OFFICIAL_CHAIN_STILL_AT_25C79_SYNC_PLAN_READY_AUDIT_ONLY`

## Purpose

The official local FX_OUTPUTS chain is still stopped at 25C79. The chat-side 25C80-25C89 audits are useful evidence, but they must not be treated as official local completion until they are replayed locally.

This document creates a safe local-sync checkpoint.

## Official local state

```text
Official local chain: 25C79_A002_ID_JOIN_BLOCKED
Local next step: 25C80_LOCAL_SYNC_FROM_25C79_AUDIT_ONLY
```

25C79 remains the last official local step until the user runs and verifies a local replay of the later audit packages.

## Chat-side evidence that exists but is not yet local-official

| chat-side step | role | local-official status |
| --- | --- | --- |
| 25C80 OHLC reproduction preflight | raw outcome replay and feature parity preflight | NOT_LOCAL_OFFICIAL |
| 25C81 formula source/feature reconciliation | raw rule feature inventory and blockers | NOT_LOCAL_OFFICIAL |
| 25C82 field formula implementation | 38 features implemented, raw condition threshold replay passed | NOT_LOCAL_OFFICIAL |
| 25C83 A002 independent source validation | A002 772 membership reproduced from raw ledger | NOT_LOCAL_OFFICIAL |
| 25C84 raw rule universe replay | 16875 raw rows and A002 772 replayed exactly | NOT_LOCAL_OFFICIAL |
| 25C85 cluster/top-ledger reconciliation | top-ledger representative logic still blocked | NOT_LOCAL_OFFICIAL |
| 25C86 representative source logic search | original cluster representative logic not found | NOT_LOCAL_OFFICIAL |
| 25C87 A002 consistency policy | possible but not original SOT; A002 demoted later | NOT_LOCAL_OFFICIAL |
| 25C88 A002 demotion/CoreB direct path | A002 auxiliary only; CoreB direct SOT restored | NOT_LOCAL_OFFICIAL |
| 25C89 CoreB direct SOT parity package | CoreB 125 direct SOT parity package | NOT_LOCAL_OFFICIAL |

## Safe synchronization rule

Do not say:

```text
Local is at 25C89.
```

Say:

```text
Local official chain is at 25C79. Chat-side evidence through 25C89 is available and must be locally replayed before adoption.
```

## What must be replayed locally

The local replay should confirm, in order:

1. 25C79 stop state and `A002_ID_JOIN_BLOCKED` status.
2. raw RR125 universe replay from OHLC + raw rule text.
3. A002 demotion from CoreB main path.
4. CoreB direct 125-row SOT parity using `gold_v2_13c_coreb_rr125_selected_top_ledgers.csv`.
5. CoreB final SOT join using CoreB-specific keys.

## Expected CoreB direct SOT after sync

CoreB direct historical source:

```text
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
```

CoreB direct top-ledger condition:

```text
rr125_top_ledgers.csv
policy == RR125_from_RR1_rules
filter == same_count>=15
```

Expected metrics:

```text
2025: count 104, WR 72.1154%, PF 3.443512, total R 143.0175
2026: count 21,  WR 80.9524%, PF 5.153846, total R 40.5
total: count 125, WR 73.6%, PF 3.687740, total R 183.5175
```

## Guardrails

- A002 remains auxiliary evidence only.
- A002 WR/PF must not be used as CoreB.
- CoreB historical SOT reporting is allowed.
- CoreB live evaluator remains blocked.
- Discord / MT5 / AI / live hook / final signal remain OFF.
- No source recovery approval is implied.

## Next local action

Run the companion script:

```text
scripts/gold_v2_runtime/audit_gold_v2_25c80_local_sync_from_25c79_audit_only.py
```

It does not replay every later audit. It creates a local official-state checkpoint and verifies whether the 25C79 stop condition and later required artifacts are present locally.
