# REPOSITORY CLEANUP AND DEPRECATION POLICY

Last updated: 2026-05-19

## Purpose

The repository has accumulated many research scripts, live wrappers, dry-run loops, and handoff documents while GOLD/BTC signal research evolved.

A major issue was found: some historical backtests may have benefited from completed higher-timeframe candles that were not actually closed at the lower-timeframe trigger time.

Therefore the repository must be reorganized around a strict no-future policy.

This document defines how to treat older files and folders **before deleting or moving anything**.

---

## Current high-level status

### GOLD

Current signal design target:

```text
docs/GOLD_STRICT_7_SIGNAL_CANDIDATES_CURRENT_SCOPE.md
```

The current GOLD design target is the strict seven-candidate set documented there.

Older GOLD signal candidates and previous GOLD multi-strategy files are historical unless explicitly reopened.

### BTC

BTC requires a separate strict rebuild.

Current status:

```text
BTC D1_LOW_BREAK_SELL and PULLBACK_REJECT_SELL are no longer trusted as active candidates.
BTC BUY trend/breakout style may remain a research direction, but no current BTC production candidate is approved.
```

BTC should not be connected further until a strict no-future BTC candidate set is separately defined.

---

## Do not delete first

Do not immediately delete old scripts or docs.

Reasons:

```text
- Some old scripts are still useful as implementation references.
- Runtime ledgers may still refer to old strategy_id values.
- AI review summaries may contain old strategy identifiers.
- Deleting scripts too early can break reproducibility of historical results.
- Some BAT files may still be used for current demo runtime until the replacement is explicitly approved.
```

Therefore the safe order is:

```text
1. Mark old files as non-current in docs.
2. Create a current-scope index.
3. Stop using old files for new research decisions.
4. Add archive/deprecated headers later.
5. Move files only after scripts/BAT references are audited.
6. Delete only after no runtime or doc references remain.
```

---

## Current source-of-truth documents

Use these docs first:

```text
docs/GOLD_STRICT_7_SIGNAL_CANDIDATES_CURRENT_SCOPE.md
docs/REPOSITORY_CLEANUP_AND_DEPRECATION_POLICY.md
```

The following handoff remains useful for the AI review pipeline mechanics, but its signal assumptions are stale:

```text
docs/NEXT_CHAT_HANDOFF_BACKTEST_AI_REVIEW.md
```

Important:

```text
Use NEXT_CHAT_HANDOFF_BACKTEST_AI_REVIEW.md for AI review pipeline mechanics only.
Do not use its BTC/GOLD old signal target statements as current strategy selection truth.
```

---

## Deprecated / historical GOLD areas

The following areas should be treated as historical or compatibility-only for the rebuild:

```text
scripts/run_gold_c_env_rr2_72h_live_scan_once.py
scripts/run_gold_c_env_rr2_72h_dry_run_cycle.py
scripts/run_gold_h1h4_bear_ab_live_scan_once.py
scripts/run_gold_h1h4_bear_ab_dry_run_loop.py
scripts/run_gold_alt_pf_signal_pack_dry_run_cycle.py
scripts/run_gold_m5_scalp_signal_pack_dry_run_cycle.py
scripts/run_gold_multi_strategy_dry_run_cycle.py
scripts/run_gold_multi_strategy_demo_dry_run_cycle.py
scripts/run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state*.py
scripts/run_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state*.bat
```

Meaning:

```text
- Do not use these as the active GOLD signal design source.
- Do not delete yet.
- Do not route new research through them unless explicitly requested.
- They can remain as historical/reference/runtime compatibility files.
```

Existing Mochipoyo GOLD live/autotrade scripts are also not the source of the new strict seven-candidate design.

---

## Deprecated / historical BTC areas

The following areas should be treated as historical or compatibility-only until BTC is rebuilt:

```text
scripts/btc_multi_strategy_signals.py
scripts/run_btc_multi_strategy_dry_run_cycle.py
scripts/run_btc_multi_strategy_guarded_demo_send_once.py
scripts/run_btc_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.py
scripts/run_btc_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.bat
```

Meaning:

```text
- Do not use D1_LOW_BREAK_SELL or PULLBACK_REJECT_SELL as current trusted candidates.
- Do not delete yet because live ledgers and AI review output may reference these IDs.
- BTC needs a separate strict no-future rebuild before new connection work.
```

---

## Proposed folder organization

Do not move files automatically yet. First use this target structure as a cleanup plan.

```text
docs/
  current/
    GOLD_STRICT_7_SIGNAL_CANDIDATES_CURRENT_SCOPE.md
    BTC_STRICT_REBUILD_SCOPE.md                # future
  deprecated/
    old_gold_multi_strategy_docs/
    old_btc_multi_strategy_docs/
  handoffs/
    historical_next_chat_handoffs/

scripts/
  current/
    research/
      # strict no-future rebuild scripts, after approval
    live/
      # approved live wrappers only, after approval
    ai_review/
      # shared AI review pipeline scripts
  deprecated/
    gold_old_multi_strategy/
    btc_old_multi_strategy/
    old_mochipoyo_research/
  compatibility/
    # wrappers required by old ledgers or historical reproduction

data/
  research_results/
    gold_strict_7_signal_candidates/
    btc_strict_rebuild/
  runtime_state/
    # live/demo ledgers only
  runtime_logs/
    # live/demo logs only
```

Because GitHub path moves can break references, only do this after a reference audit.

---

## Reference audit required before moving files

Before moving or deleting any script:

```text
1. Search for the filename across docs, BAT, py, json, and markdown.
2. Check whether a BAT calls it.
3. Check whether another Python script imports it.
4. Check whether runtime ledgers reference its strategy_id.
5. Check whether AI review normalization relies on that strategy_id.
6. If still referenced, keep it in place or create a compatibility wrapper.
```

Minimum search targets:

```text
*.py
*.bat
*.md
*.json
*.csv metadata / strategy_id values
```

---

## Rules for new scripts from this point

No new signal implementation script should be created unless the user explicitly approves implementation.

Research scripts are allowed only after the user approves the specific research task.

Any new signal research script must include:

```text
- strict_no_future_ok column
- context H1/H4/D1 close_time columns if higher timeframe is used
- explicit trigger timeframe
- explicit outcome timeframe
- explicit TP/SL pips
- monthly summary output
- full trade detail output
- no MT5 calls
- no Discord calls
- no OpenAI calls unless specifically an AI review step
```

---

## Cleanup priority

### Phase 1: Documentation freeze

```text
- Add current GOLD strict seven-candidate scope doc.
- Add cleanup/deprecation policy doc.
- Mark old signal docs as stale in future edits.
```

### Phase 2: Research output consolidation

```text
- Recreate seven GOLD candidate trade details in one strict output folder.
- Keep all new research outputs under data/research_results/gold_strict_7_signal_candidates/.
- Stop writing new exploratory results into many unrelated folders.
```

### Phase 3: Script index

```text
- Create a scripts/current index after the strict research script is approved.
- Create a deprecated script index listing old script names and why they are not current.
```

### Phase 4: Physical moves

```text
- Move only after reference audit.
- Prefer compatibility wrappers if old BAT files or ledgers still need old paths.
```

### Phase 5: deletion

```text
- Delete only files with no references and no historical value.
- Deletion must be explicit and reviewed.
```

---

## Current instruction to future chats

When continuing this project, future chats should not start from the old GOLD/BTC signal candidates.

Start from:

```text
docs/GOLD_STRICT_7_SIGNAL_CANDIDATES_CURRENT_SCOPE.md
docs/REPOSITORY_CLEANUP_AND_DEPRECATION_POLICY.md
```

Then ask whether the user wants:

```text
1. Further research only
2. strict seven-candidate trade detail regeneration
3. AI review of strict backtest trades
4. cleanup/reference audit
5. Discord/autotrade integration design
```

Do not assume implementation approval.
