# START HERE — GOLD Late Transition V1 Prospective Shadow

Repository: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/gold-v19-wave-shadow`

This package implements the separately authorized observation-only Challenger:

```text
LATE_TRANSITION_VACANCY_V1
+ SEMIANNUAL_EXPANDING chosen-direction rank < P90
+ IMPULSE_LATE or CORRECTION_EARLY
+ first confirmable state-event onset only
+ TP20 / SL10 / 480 exact M1
+ V19 always has portfolio priority
```

It does **not** modify the frozen GOLD V19 contract, V19 runtime, V19 ledgers, V19 state root, or V19 Discord contract.

Read in this order:

1. `docs/gold_late_transition_v1/NEXT_CHAT_HANDOFF_GOLD_LATE_TRANSITION_V1_IMPLEMENTED_USER_PC_ACTIVATION_NEXT_20260801.md`
2. `docs/gold_late_transition_v1/GOLD_LATE_TRANSITION_V1_PROSPECTIVE_SHADOW_IMPLEMENTATION_20260801.md`
3. `docs/gold_late_transition_v1/GOLD_LATE_TRANSITION_V1_DISCORD_ENTRY_ALERT_ADDENDUM_20260801.md`
4. `config/gold_late_transition_v1/frozen_contract_20260801.json`
5. `config/gold_late_transition_v1/discord_alert_contract_20260801.json`
6. `config/gold_late_transition_v1/current_state_20260801.json`
7. `config/gold_late_transition_v1/next_action_20260801.json`
8. `config/gold_late_transition_v1/implementation_verification_20260801.json`

## Local activation

Keep the existing V19 runtime and notifier unchanged and running.

1. `scripts/gold_late_transition_v1/01_INSTALL.bat`
2. `scripts/gold_late_transition_v1/02_BOOTSTRAP_ACTIVATE.bat`
3. `scripts/gold_late_transition_v1/04_STATUS.bat`
4. `scripts/gold_late_transition_v1/06_CONFIGURE_DISCORD.bat`
5. `scripts/gold_late_transition_v1/07_TEST_DISCORD.bat`
6. `scripts/gold_late_transition_v1/03_RUN_LOOP.bat`
7. `scripts/gold_late_transition_v1/08_RUN_DISCORD_ALERTS.bat`
8. Use `04_STATUS.bat` and `09_DISCORD_STATUS.bat` for inspection.

`02_BOOTSTRAP_ACTIVATE.bat` is no-backfill. Do not rerun it after successful activation.

The Challenger reads the existing local V19 score ledger and runtime state only. It never writes to V19 files. The Discord adapter references the existing V19 webhook locally without copying or printing the URL.

Still OFF:

- AI judgement
- MT5 order
- live trading
- final signal
- live-ready promotion
- NO_SIGNAL notifications
- exit notifications
