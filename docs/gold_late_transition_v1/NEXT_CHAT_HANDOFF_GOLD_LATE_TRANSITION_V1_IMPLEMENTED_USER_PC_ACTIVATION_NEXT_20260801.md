# NEXT CHAT HANDOFF — GOLD Late Transition V1 implemented; user-PC activation next

Repository: `knitanr-a11y/xauusd-signal-lab`  
Working branch: `feature/gold-v19-wave-shadow`  
Existing Draft PR: `#82`

## Read first

1. `START_HERE_GOLD_LATE_TRANSITION_V1_SHADOW.md`
2. `docs/gold_late_transition_v1/GOLD_LATE_TRANSITION_V1_PROSPECTIVE_SHADOW_IMPLEMENTATION_20260801.md`
3. `docs/gold_late_transition_v1/GOLD_LATE_TRANSITION_V1_DISCORD_ENTRY_ALERT_ADDENDUM_20260801.md`
4. `config/gold_late_transition_v1/frozen_contract_20260801.json`
5. `config/gold_late_transition_v1/discord_alert_contract_20260801.json`
6. `config/gold_late_transition_v1/current_state_20260801.json`
7. `config/gold_late_transition_v1/next_action_20260801.json`
8. `config/gold_late_transition_v1/implementation_verification_20260801.json`

## Frozen Challenger

```text
SEMIANNUAL_EXPANDING
+ chosen direction rank < P90
+ IMPULSE_LATE or CORRECTION_EARLY
+ first confirmable state-event onset only
+ TP20 / SL10 / 480 exact M1
+ V19 always priority
```

Do not add low-vol exclusion, July rescue, a rank floor, a different P90 ceiling, direction deletion, state deletion, runner, second entry, TP/SL change, or timing change.

## User authorization

On 2026-08-01, the user explicitly authorized:

- separate observation-only Prospective Shadow
- Discord notification for each newly accepted Challenger entry
- Japanese compact message
- M15 chart attachment

Still OFF:

- live-ready
- final signal
- AI judgement
- MT5 order
- live trading
- NO_SIGNAL alerts
- exit alerts

## V19 must remain unchanged

The existing V19 runtime and Discord notifier are already running on the user's PC.

The Challenger:

- has a separate code namespace and state root;
- reads V19 score ledger and runtime state only;
- never writes V19 files;
- reconstructs V19 first-P90 episode priority sequentially;
- verifies V19 accepted count and open position parity every iteration;
- fails closed when V19 is unavailable or inconsistent.

Do not rerun V19 bootstrap merely to activate this Challenger.

## Verification completed

- repository unit tests: 12 passed
- Python compile check: passed
- historical Challenger entries: 123/123 exact
- historical Challenger PnL and exit index: 123/123 exact
- historical V19 entries: 169/169 exact
- historical V19 PnL and exit index: 169/169 exact
- restart/no-backfill contract: covered by tests and prior preregistration audit

## User-PC next steps

1. Keep V19 `03_RUN_LOOP.bat` and V19 `08_RUN_DISCORD_ALERTS.bat` running.
2. Pull `feature/gold-v19-wave-shadow`.
3. Run `scripts\gold_late_transition_v1\01_INSTALL.bat`.
4. Run `02_BOOTSTRAP_ACTIVATE.bat` once.
5. Run `04_STATUS.bat`; require `READY` and V19 parity PASS.
6. Run `06_CONFIGURE_DISCORD.bat`.
7. Run `07_TEST_DISCORD.bat`; confirm Japanese test message and M15 chart.
8. Run `03_RUN_LOOP.bat` and keep it open.
9. Run `08_RUN_DISCORD_ALERTS.bat` and keep it open.
10. Inspect with `04_STATUS.bat` and `09_DISCORD_STATUS.bat`.

Do not claim user-PC activation, continuous Challenger collection, or Discord delivery success until the user reports these steps completed.
