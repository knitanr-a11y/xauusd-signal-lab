# NEXT CHAT HANDOFF — GOLD V19 Shadow READY + Discord entry alert next

repo: `knitanr-a11y/xauusd-signal-lab`  
working branch: `feature/gold-v19-wave-shadow`  
base: `main` at implementation start `7c3e9ee3e8bfb21f024a273cc3d695d273c0abd5`  
Draft PR: `#82`

## Read first

1. `START_HERE_GOLD_V19_SHADOW.md`
2. `docs/gold_wave_shadow_v19/GOLD_V19_PROSPECTIVE_SHADOW_IMPLEMENTATION_20260801.md`
3. `docs/gold_wave_shadow_v19/GOLD_V19_DISCORD_ENTRY_ALERT_ADDENDUM_20260801.md`
4. `config/gold_wave_shadow_v19/frozen_contract_20260801.json`
5. `config/gold_wave_shadow_v19/discord_alert_contract_20260801.json`
6. `config/gold_wave_shadow_v19/current_state_20260801.json`
7. `config/gold_wave_shadow_v19/next_action_20260801.json`
8. `config/gold_wave_shadow_v19/implementation_verification_20260801.json`
9. `scripts/gold_wave_shadow_v19/discord_notifier.py`

## Frozen candidate

`SEMIANNUAL_EXPANDING + P90 + FIRST_P90_PER_IMPULSE_EARLY_EPISODE + TP20/SL10`

Do not change:

- P90
- six causal wave scales
- episode definition
- first eligible candidate only
- TP20 / SL10
- 480-minute value horizon
- LONG and SHORT
- one-position non-overlap
- fixed USD 0.30 spread
- recorded spread gate <= 30 points
- exact M1 and SL-first collision handling

## User-PC Shadow activation observed

The user ran bootstrap and reported:

- `activated: true`
- `status: READY`
- `activation_cutoff_decision_time: 2026-07-31T11:45:00`
- `last_processed_decision_time: 2026-07-31T11:45:00`
- `active_model_boundary: 2026-07-01T00:00:00`
- `latest_full_feature_decision_time: 2026-07-31T22:15:00`
- `latest_session_guarded_decision_time: 2026-07-31T11:45:00`
- `score_history_rows: 920`
- `pending_score_rows: 6`
- `automatic_semiannual_update: true`
- `next_update_boundary: 2027-01-01T00:00:00`
- `accepted_trades: 0`
- `open_trade: null`

The user has not yet explicitly confirmed in chat that `03_RUN_LOOP.bat` is currently running. Do not claim continuous collection is active until confirmed.

## Discord authorization and implementation

On 2026-08-01, the user explicitly authorized Discord notifications in order to inspect candidate entry timing visually.

Authorization scope:

- delivery only
- newly accepted Shadow entry only
- Japanese compact message
- M15 chart attachment
- observation-only

Still prohibited:

- AI judgement
- MT5 order
- live trading
- no-signal notifications
- recovery/backfill notifications
- missed-entry delayed replay
- strategy changes based on Discord

Implementation is a separate sidecar:

- `scripts/gold_wave_shadow_v19/discord_notifier.py`
- `06_CONFIGURE_DISCORD.bat`
- `07_TEST_DISCORD.bat`
- `08_RUN_DISCORD_ALERTS.bat`
- `09_DISCORD_STATUS.bat`

The sidecar watches future increments of `runtime_state.json -> counters.accepted_trades`.

Startup policy:

`NO_BACKFILL; baseline current accepted_trades and notify future increments only`

If more than one entry occurred while the notifier was unavailable, delayed alerts are suppressed rather than replayed.

A process lock prevents duplicate notifier instances.

The notifier message contains:

- LONG / SHORT
- MT5 broker-server entry time
- Entry
- TP20
- SL10
- `IMPULSE_EARLY`
- observation-only / no real order notice

The attached M15 chart shows the recent candles, entry time, Entry, TP and SL lines. Chart failure falls back to text-only and never changes the Shadow result.

## Webhook security

The webhook URL must be entered locally through `06_CONFIGURE_DISCORD.bat`.

It is stored only in:

`config/gold_wave_shadow_v19/local_config.json`

That path is now ignored by Git.

Never ask the user to paste the webhook URL into chat. Never commit it, add it to an Issue or PR, or print it in logs.

## Local next steps

The user is already on `feature/gold-v19-wave-shadow` in the dedicated clone `C:\gold-v19-shadow`.

1. In GitHub Desktop, `Fetch origin`, then `Pull origin`.
2. Run `scripts\gold_wave_shadow_v19\01_INSTALL.bat` again because `matplotlib` was added.
3. Run `06_CONFIGURE_DISCORD.bat` and enter the webhook URL locally. Input is hidden.
4. Run `07_TEST_DISCORD.bat`.
5. Confirm the Japanese test message and M15 chart arrive.
6. Run or keep `03_RUN_LOOP.bat` open for Shadow collection.
7. Open `08_RUN_DISCORD_ALERTS.bat` alongside it.
8. Use `04_STATUS.bat` for Shadow and `09_DISCORD_STATUS.bat` for notification delivery.

Do not rerun `02_BOOTSTRAP_ACTIVATE.bat` merely to configure Discord. Existing Shadow activation and CSV paths should remain unchanged.

## Verification

Repository-side Discord tests:

- no-backfill accepted-trade baseline
- LONG TP20/SL10 calculation
- SHORT Japanese observation-only message
- duplicate notifier process lock

Result: `4 passed`

The actual webhook and chart delivery test is intentionally local-only and remains pending until the user runs `07_TEST_DISCORD.bat`.

## Current formal status

`V19_FROZEN_PROSPECTIVE_SHADOW_AUTHORIZED_OBSERVATION_ONLY_DISCORD_ENTRY_DELIVERY_AUTHORIZED`

The branch and PR remain unmerged. Do not merge until user-PC notification test and market-open observation are reviewed.
