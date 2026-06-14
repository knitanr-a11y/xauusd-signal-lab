# NEXT CHAT HANDOFF — GOLD V3 107R2 created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_107R2_EXIT_DT_SOURCE_INTELLIGENCE_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

107R found exact `exit_dt` sources but could not join them to the 107Q best-family ledger:

```text
status: GOLD_V3_107R_RESOLVED_EXIT_DT_REHYDRATION_BLOCKED_AUDIT_ONLY
decision: RESOLVED_EXIT_DT_REHYDRATION_BLOCKED_PARTIAL_OR_AMBIGUOUS_JOIN
best_family_rows: 5571
source_catalog_rows: 1594
exact_exit_dt_source_count: 19
join_attempt_rows: 0
resolved_rows: 0
```

This means the blocker is **not** simply “no exit_dt exists”. The blocker is that the 19 exact exit_dt sources did not expose the expected join key sets, or the join intelligence did not inspect them deeply enough.

## What 107R2 does

107R2 performs source intelligence, not final live replay.

It reads:

```text
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_best_family_trade_ledger.csv
FX_OUTPUTS/gold_v3/107rc/gold_v3_107r_exit_dt_source_catalog.csv
```

It inspects every exact `exit_dt` source and writes:

```text
gold_v3_107r2_exact_exit_dt_source_detail.csv
gold_v3_107r2_shared_column_matrix.csv
gold_v3_107r2_candidate_key_diagnostics.csv
gold_v3_107r2_recommended_next_action.csv
```

If a strict full-coverage join exists, it can proceed toward 107S.

If not, it should produce a concrete 107R3 reconstruction plan.

## Files created

```text
docs/gold_v3/GOLD_V3_107R2_EXIT_DT_SOURCE_INTELLIGENCE_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_107r2_exit_dt_source_intelligence_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107r2_exit_dt_source_intelligence.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107R2_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_107r2_exit_dt_source_intelligence.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/107r2c/paste_me.txt
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
