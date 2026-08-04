# GOLD P75 State Survival Shadow — separate-clone operation

Date: 2026-08-04

## Required checkout isolation

Do not operate `feature/gold-scalp-state-survival-shadow` and `feature/gold-v19-challenger-c1-audit` by switching branches inside one active Windows checkout.

Use permanent separate clones:

- `C:\gold-challenger-c1` → `feature/gold-v19-challenger-c1-audit`
- `C:\gold-p75-state-survival` → `feature/gold-scalp-state-survival-shadow`

A branch switch legitimately removes repository paths that do not exist on the selected branch. An already-running Python process can then fail when it reloads a checkout-local configuration file.

## State continuity

The P75 prospective state is outside the repository:

`%LOCALAPPDATA%\xauusd_signal_lab\gold_scalp_state_survival_shadow`

Do not delete, rename, reset or replace this directory. A new clone must reuse this same state directory through the frozen local configuration.

The Challenger C1 state is separately stored at:

`%LOCALAPPDATA%\xauusd_signal_lab\gold_challenger_c1_shadow`

## Safe P75 relocation

1. Stop only the failed old P75 loop window.
2. Clone `https://github.com/knitanr-a11y/xauusd-signal-lab.git` into `C:\gold-p75-state-survival`.
3. Switch that clone to `feature/gold-scalp-state-survival-shadow` and pull the latest head.
4. Run `scripts\gold_scalp_state_survival_shadow\01_INSTALL.bat`.
5. Run `02_BOOTSTRAP_ACTIVATE_SHADOW.bat` only to create `config\gold_scalp_state_survival_shadow\local_config.json` when it is missing; close it after the editor opens.
6. Set `v19_local_config_path` to the existing frozen V19 local config. The exact path can be copied from `%LOCALAPPDATA%\xauusd_signal_lab\gold_challenger_c1_shadow\local_config.json` under `v19.local_config_path`.
7. Keep `state_dir` unchanged as `%LOCALAPPDATA%\xauusd_signal_lab\gold_scalp_state_survival_shadow`.
8. Do not use `--force` and do not delete existing runtime state.
9. Run `04_SHADOW_STATUS.bat`. The existing cursor/trade state must appear.
10. Start `03_RUN_SHADOW_LOOP.bat`.

When the state already exists, a second bootstrap is neither required nor authorized. Resume from the existing state by status-checking and starting the loop.

## Console identity

All launchers use `GOLD P75 State Survival Shadow` in their Windows title. Runtime log lines use `[GOLD_P75_STATE_SURVIVAL_SHADOW]`.

This change is operational only. Candidate state/action pairs, entry logic, exit logic, health rules, no-backfill policy, Discord scope and MT5-order prohibition are unchanged.
