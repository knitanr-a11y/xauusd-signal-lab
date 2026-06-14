# NEXT CHAT HANDOFF — GOLD V3 109 created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_109_BASE_POLICY_SELECTION_REVIEW_PACKET_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

108B completed READY:

```text
status: GOLD_V3_108B_HEALTH_GATE_DELTA_REVIEW_READY_AUDIT_ONLY
decision: HEALTH_GATE_DELTA_REVIEW_READY_BASE_PREFERRED
```

Key 108B metrics:

```text
base_trades: 5571
kept_trades: 5291
skipped_trades: 280
retention: 0.9497397235684796
base_wr: 0.6372285047567762
kept_wr: 0.6401436401436401
skipped_wr: 0.5821428571428572
base_pf: 3.129035220079588
kept_pf: 3.184031677596181
skipped_pf: 2.133074039652912
base_sum_result_usd: 18065.748437500006
kept_sum_result_usd: 17562.617633928578
skipped_sum_result_usd: 503.1308035714292
```

Interpretation:

```text
Health gate is strict and valid, but skipped trades were net positive.
WR/PF improvement was small.
Therefore KEEP_107Q_BASE is preferred for next audit review.
```

## What 109 does

109 fixes the review candidate as:

```text
selected_option: KEEP_107Q_BASE
selected_policy_key: 107Q_BASE_RESOLVED_PASS_THROUGH
health_gate_adopted: false
```

It reads:

```text
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_resolved_107q_best_family_ledger.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_summary.json
FX_OUTPUTS/gold_v3/108c/gold_v3_108_summary.json
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_summary.json
```

It writes:

```text
gold_v3_109_selected_base_policy_ledger.csv
gold_v3_109_selected_policy_summary.csv
gold_v3_109_base_policy_monthly_metrics.csv
gold_v3_109_base_policy_regime_metrics.csv
gold_v3_109_selection_reason_matrix.csv
gold_v3_109_quality_gate_matrix.csv
```

## Files created

```text
docs/gold_v3/GOLD_V3_109_BASE_POLICY_SELECTION_REVIEW_PACKET_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_109_base_policy_selection_review_packet_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_109_base_policy_selection_review_packet.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_109_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_109_base_policy_selection_review_packet.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/109c/paste_me.txt
```

Expected decision:

```text
BASE_POLICY_SELECTION_READY_FOR_STAGE110_AUDIT_MONITORING_DESIGN
```

## Important interpretation

`exit_dt` is not an entry condition. It is only used for resolved-only history:

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
