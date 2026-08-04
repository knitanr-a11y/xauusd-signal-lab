# GOLD Challenger C1 Shadow — separate-clone operation

Date: 2026-08-04

## Required checkout isolation

Do not operate `feature/gold-v19-challenger-c1-audit` and `feature/gold-scalp-state-survival-shadow` by switching branches inside one active Windows checkout.

Use permanent separate clones:

- `C:\gold-challenger-c1` → `feature/gold-v19-challenger-c1-audit`
- `C:\gold-p75-state-survival` → `feature/gold-scalp-state-survival-shadow`

A branch switch legitimately removes repository paths that do not exist on the selected branch. Long-running processes must never depend on a checkout that is being switched to another branch.

## State continuity

Challenger C1 keeps its local config, runtime state and virtual environment outside the repository:

`%LOCALAPPDATA%\xauusd_signal_lab\gold_challenger_c1_shadow`

Do not delete, rename, reset or replace this directory.

P75 State Survival separately uses:

`%LOCALAPPDATA%\xauusd_signal_lab\gold_scalp_state_survival_shadow`

The two state roots must remain separate.

## Safe operation

1. Keep `C:\gold-challenger-c1` permanently on `feature/gold-v19-challenger-c1-audit`.
2. Fetch and pull that branch without switching it.
3. Start `scripts\gold_challenger_c1\03_RUN_SHADOW_LOOP.bat`.
4. Start `scripts\gold_challenger_c1\08_RUN_DISCORD_ALERTS.bat` when Discord entry notification is required.
5. Run P75 only from the separate `C:\gold-p75-state-survival` clone.

## Console identity

All launchers use `GOLD Challenger C1 Shadow` in their Windows title. Runtime and notifier log lines use `[GOLD_CHALLENGER_C1_SHADOW]`.

The former repeated pandas `FutureWarning` caused by concatenating empty history/pending frames is removed without changing V19 score ranks, Challenger candidate decisions, V19 priority, entries, exits, no-backfill state or observation boundaries.
