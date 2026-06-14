# NEXT CHAT HANDOFF — GOLD V3 107S created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_107S_RESOLVED_ONLY_HEALTH_GATE_REPLAY_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

User asked whether `exit_dt` is an entry condition or entry-before information.

Clarification:

```text
exit_dt is NOT an entry feature.
exit_dt is NOT used to decide the current entry.
exit_dt is only used to decide whether a past trade outcome was already known before the current entry.
```

Strict rule:

```text
past_trade.exit_dt <= current_trade.entry_dt
```

107R6 produced full exit coverage for the 107Q best-family ledger:

```text
best_family_rows: 5571
best_family_resolved_rows: 5571
best_family_exit_dt_coverage: 1.0
```

107R6 remained blocked only because full-source parity failed outside the selected 107Q best rows:

```text
source_parity_fail_rows: 1206188
source_resolve_error_rows: 1205549
```

Therefore 107S intentionally uses only:

```text
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_resolved_107q_best_family_ledger.csv
```

## What 107S does

107S performs resolved-only health gate replay.

It compares:

1. pass-through 107Q best-family baseline
2. candidate-level rolling PF health gate
3. side-level rolling PF health gate
4. all-selected rolling PF health gate

Sweep:

```text
window: 20, 50, 100
min_history: 5, 10, 20
pf_threshold: 1.0, 1.15, 1.3, 1.5
```

For each current entry, the health history is updated only by rows with:

```text
exit_dt <= current entry_dt
```

The current row's own `result_usd` and `exit_dt` are not used to decide itself.

## Files created

```text
docs/gold_v3/GOLD_V3_107S_RESOLVED_ONLY_HEALTH_GATE_REPLAY_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_107s_resolved_only_health_gate_replay_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107s_resolved_only_health_gate_replay.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107S_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_107s_resolved_only_health_gate_replay.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/107sc/paste_me.txt
```

## Expected decisions

```text
RESOLVED_ONLY_HEALTH_GATE_PRIMARY_READY_FOR_STAGE108_REVIEW
RESOLVED_ONLY_HEALTH_GATE_REVIEW_READY_FOR_STAGE108_REVIEW
RESOLVED_ONLY_HEALTH_GATE_NO_IMPROVEMENT_KEEP_107Q_BASE_FOR_REVIEW
RESOLVED_ONLY_HEALTH_GATE_BLOCKED_INPUT_INCOMPLETE
```

If health gate does not improve base, do not force it. Keep 107Q base for review.

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
