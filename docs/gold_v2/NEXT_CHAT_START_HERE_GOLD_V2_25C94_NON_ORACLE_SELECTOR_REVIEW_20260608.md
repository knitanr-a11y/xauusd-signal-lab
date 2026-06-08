# NEXT CHAT START HERE - GOLD V2 25C94 non-oracle selector review

Created: 2026-06-08

Repo: `knitanr-a11y/xauusd-signal-lab`

## Read this first in the new chat

This file is the entry point for the next chat. It exists to prevent the next chat from reading only one partial handoff and missing the non-local / GitHub-only discovery notes.

Read these in order:

```text
1. docs/gold_v2/NEXT_CHAT_START_HERE_GOLD_V2_25C94_NON_ORACLE_SELECTOR_REVIEW_20260608.md
2. docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C93_DONE_25C94_NEXT_NON_ORACLE_SELECTOR_REVIEW_AUDIT_ONLY_20260608.md
3. docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C93_NON_LOCAL_DISCOVERY_ADDENDUM_20260608.md
```

The second file is the main state handoff. The third file contains GitHub-only and chat-side recovery findings that may not exist in a local checkout until the repo is pulled.

## Current state in one screen

Latest completed step:

```text
25C93_NON_ORACLE_COMPONENT_SELECTOR_AUDIT_ONLY
```

Latest status:

```text
NON_ORACLE_COMPONENT_SELECTOR_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

25C93 found the first non-oracle count selector candidate:

```text
component_family = entry_gap
gap_min = 15
selector = latest_start or closest_start
same_count_exact = 125 / 125
source_rule_count_exact = 125 / 125
unique_origins_exact = 125 / 125
profit_sum_exact = 0 / 125
```

Meaning:

```text
CoreB count-field component selection is now reproducible by a non-oracle selector candidate.
Representative profit / top_candidate_id binding is not yet recovered.
CoreB live evaluator remains blocked.
```

## Absolute guardrails

Keep all of these unless the user explicitly overrides them:

```text
GOLD V2 remains audit-only.
REQUEST_MORE_AUDIT is not source recovery approval.
Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
Approximate reimplementation is prohibited.
A002 is auxiliary-only and must not be used for CoreB metrics.
Discord / MT5 / AI API / live hook / live evaluator / final signal remain OFF unless explicitly approved.
NO_SIGNAL must not notify Discord.
Do not treat oracle matching as live logic.
Do not treat latest_start / closest_start as live-ready before human review and profit binding review.
```

## What not to do next

Do not restart broad meta-audits.

Do not redo A002 as CoreB.

Do not use A002 win rate / PF for CoreB.

Do not claim source recovery or live readiness from 25C93.

Do not proceed to Discord, MT5, AI API, live hook, live evaluator, or final signal.

Do not ask for the original clustering script as the only path forward. Continue from the reconstructed component-selector candidate.

## Next step

Proceed to:

```text
25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY
```

Goal:

```text
Review whether latest_start and closest_start select the same component for all 125 rows, and recover representative profit / top_candidate_id binding without oracle logic.
```

## Minimum 25C94 checks

25C94 should produce an audit-only script/report that:

1. Rebuilds raw RR125 `entry_gap=15m` components.
2. Selects the component using both `latest_start` and `closest_start`.
3. Confirms whether both selectors choose the same component for every CoreB top row.
4. Emits per-row selected component details:

```text
entry_time
cluster_id
top_candidate_id
selected_component_id
component_min_entry
component_max_entry
component_count
component_unique_origins
candidate_ids
origin_ids
```

5. Tests representative profit binding inside the selected component:

```text
candidate_id == top_candidate_id
origin_id == top_candidate_id
candidate_id or origin_id contains top_candidate_id
latest raw entry in selected component
earliest raw entry in selected component
max profit raw row
min profit raw row
sum / mean / median / min / max / first / last profit aggregation
```

6. Compares selected representative profit against top `profit` for all 125 rows.
7. Keeps live blocked unless both count and profit binding pass and the user explicitly approves the next audit stage.

## Expected 25C94 statuses

If count selector is confirmed but representative profit binding fails:

```text
NON_ORACLE_SELECTOR_COUNT_MATCHED_PROFIT_BINDING_BLOCKED_AUDIT_ONLY_LIVE_BLOCKED
```

If count selector and representative profit binding both pass:

```text
NON_ORACLE_SELECTOR_AND_PROFIT_BINDING_CANDIDATE_READY_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

If inputs are missing:

```text
NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

## Exact prompt for the new chat

```text
repo: knitanr-a11y/xauusd-signal-lab

Please read and continue from these files in order:
1. docs/gold_v2/NEXT_CHAT_START_HERE_GOLD_V2_25C94_NON_ORACLE_SELECTOR_REVIEW_20260608.md
2. docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C93_DONE_25C94_NEXT_NON_ORACLE_SELECTOR_REVIEW_AUDIT_ONLY_20260608.md
3. docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C93_NON_LOCAL_DISCOVERY_ADDENDUM_20260608.md

GOLD V2 remains audit-only.
REQUEST_MORE_AUDIT is not source recovery approval.
Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
Approximate reimplementation is prohibited.
A002 is auxiliary-only and must not be used for CoreB metrics.
Discord / MT5 / AI API / live hook / live evaluator / final signal remain OFF unless explicitly approved.
NO_SIGNAL must not notify Discord.

25C93 found a non-oracle selector candidate:
- component_family = entry_gap
- gap_min = 15
- best selectors = latest_start and closest_start
- same_count/source_rule_count/unique_origins exact = 125/125
- profit_sum exact = 0/125
- status = NON_ORACLE_COMPONENT_SELECTOR_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED

Next step:
25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY

Goal:
Review whether latest_start/closest_start are stable and recover representative profit/top_candidate_id binding without oracle logic. Do not unlock live.
```
