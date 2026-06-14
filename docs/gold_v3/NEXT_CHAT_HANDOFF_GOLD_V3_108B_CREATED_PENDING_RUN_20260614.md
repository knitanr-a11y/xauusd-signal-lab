# NEXT CHAT HANDOFF — GOLD V3 108B created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_108B_HEALTH_GATE_DELTA_REVIEW_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

108 completed READY:

```text
status: GOLD_V3_108_RESOLVED_ONLY_STAGE_REVIEW_PACKET_READY_AUDIT_ONLY
decision: STAGE108_REVIEW_PACKET_READY_HUMAN_DECISION_REQUIRED
```

The tradeoff is:

```text
base_trades: 5571
health_trades: 5291
trade_delta: -280
retention: 0.9497397235684796
base_win_rate: 0.6372285047567762
health_win_rate: 0.6401436401436401
wr_gain: 0.002915135386863943
base_profit_factor: 3.129035220079588
health_profit_factor: 3.184031677596181
pf_gain: 0.0549964575165931
base_sum_result_usd: 18065.74843750001
health_sum_result_usd: 17562.617633928578
sum_delta: -503.1308035714319
```

Health gate improves WR/PF but lowers total sum_result_usd.

## What 108B does

108B compares the base 107Q ledger and the 107S best health gate ledger.

It identifies skipped trades and reports:

```text
skipped trade count
skipped win rate
skipped PF
skipped sum_result_usd
monthly delta
regime delta
side delta
candidate delta top rows
```

It recommends one of:

```text
HEALTH_GATE_DELTA_REVIEW_READY_BASE_PREFERRED
HEALTH_GATE_DELTA_REVIEW_READY_HEALTH_GATE_PREFERRED
HEALTH_GATE_DELTA_REVIEW_READY_LIGHTER_HEALTH_GATE_REVIEW
HEALTH_GATE_DELTA_REVIEW_READY_HUMAN_DECISION_REQUIRED
```

## Files created

```text
docs/gold_v3/GOLD_V3_108B_HEALTH_GATE_DELTA_REVIEW_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_108b_health_gate_delta_review_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_108b_health_gate_delta_review.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_108B_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_108b_health_gate_delta_review.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/108bc/paste_me.txt
```

## Hard guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to:

- GOLD V2
- old GOLD
- DISC8
- Stage41 feature-only snapshot as a trading source

Do not mutate:

- source CSVs
- CSV contract
- candidate pool
- Stage45 runtime
- Stage69 runtime
- live evaluator
- live hook
- final signal
- Discord
- MT5 execution
- AI API

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
csv_open_bar_exclusion_required=false
```

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```
