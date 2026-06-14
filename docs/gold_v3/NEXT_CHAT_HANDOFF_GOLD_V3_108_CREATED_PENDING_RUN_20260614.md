# NEXT CHAT HANDOFF — GOLD V3 108 created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_108_RESOLVED_ONLY_STAGE_REVIEW_PACKET_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

107S completed READY:

```text
status: GOLD_V3_107S_RESOLVED_ONLY_HEALTH_GATE_REPLAY_READY_AUDIT_ONLY
decision: RESOLVED_ONLY_HEALTH_GATE_PRIMARY_READY_FOR_STAGE108_REVIEW
resolved_only_strict: true
exit_dt_used_as_entry_feature: false
best_policy_key: candidate_pf_gate||W50||N5||PF1.5
```

Best 107S policy:

```text
base_trades: 5571
health_trades: 5291
retention: 0.9497397235684796
base_win_rate: 0.6372285047567762
health_win_rate: 0.6401436401436401
wr_gain: 0.002915135386863943
base_profit_factor: 3.129035220079588
health_profit_factor: 3.184031677596181
pf_gain: 0.0549964575165931
base_sum_result_usd: 18065.748437500006
health_sum_result_usd: 17562.617633928578
```

This is strict resolved-only and passes primary gates, but total sum_result_usd is lower. Therefore it needs a review packet rather than automatic adoption.

## What 108 does

108 prepares a decision packet comparing:

1. 107Q/107S pass-through base
2. 107S best candidate-level PF health gate

It outputs:

```text
gold_v3_108_decision_review_summary.csv
gold_v3_108_adoption_options.csv
gold_v3_108_monthly_diff.csv
gold_v3_108_regime_review.csv
gold_v3_108_human_decision_template.md
```

Decision logic:

- If health gate improves WR/PF but lowers total sum_result_usd, do not auto-approve.
- Output human decision required.

Expected decision:

```text
STAGE108_REVIEW_PACKET_READY_HUMAN_DECISION_REQUIRED
```

## Files created

```text
docs/gold_v3/GOLD_V3_108_RESOLVED_ONLY_STAGE_REVIEW_PACKET_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_108_resolved_only_stage_review_packet_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_108_resolved_only_stage_review_packet.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_108_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_108_resolved_only_stage_review_packet.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/108c/paste_me.txt
```

## Important interpretation

`exit_dt` is not an entry condition. It is only used to determine whether past outcomes are known before the current entry:

```text
past_trade.exit_dt <= current_trade.entry_dt
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
