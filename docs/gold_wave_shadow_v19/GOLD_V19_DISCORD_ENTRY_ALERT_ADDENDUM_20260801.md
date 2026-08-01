# GOLD V19 Discord Entry Alert Addendum

Date: 2026-08-01  
Scope: observation-only Discord delivery adapter

## Authorization

The user explicitly authorized Discord notifications in order to visually inspect the entry timing of the frozen GOLD V19 Shadow candidate.

This authorization changes delivery only. It does not change the strategy, model, wave grammar, entry condition, TP/SL, overlap policy, or semiannual update logic.

## Notification event

Send one Discord notification only when `accepted_trades` increases by exactly one during a continuously running notifier session.

The notification represents:

```text
SEMIANNUAL_EXPANDING
+ P90 past-only rank by direction
+ causal IMPULSE_EARLY episode
+ first eligible P90 only per episode
+ TP20 / SL10
```

No notification is sent for:

- `NO_SIGNAL`
- ordinary M15 decisions
- recovery replay
- candidates missed while the notifier was stopped
- suppressed entries
- model-update waiting states

## Message content

The message is short Japanese text containing:

- LONG or SHORT
- MT5 broker-server entry time
- Entry price
- TP20 price
- SL10 price
- `IMPULSE_EARLY`
- observation-only / no real order notice

An M15 candlestick chart is attached when chart generation succeeds. It contains the entry time and Entry/TP/SL reference lines. Chart failure does not alter the Shadow decision and falls back to a text-only message.

## Security

The webhook URL is entered locally with `06_CONFIGURE_DISCORD.bat` and is stored only in:

`config/gold_wave_shadow_v19/local_config.json`

That file is ignored by Git. The webhook URL must never be pasted into a GitHub issue, commit, pull request, log, or chat message.

## Runtime separation

The notifier is a sidecar process. The frozen Shadow runtime is not modified and does not depend on Discord.

- Shadow continues if Discord is unavailable.
- Discord failure cannot create, suppress, delay, or modify a Shadow entry.
- A process lock prevents two notifier instances from sending duplicates.
- Notifier startup uses a no-backfill baseline equal to the current `accepted_trades` count.
- If more than one entry occurred while the notifier was unavailable, delayed notifications are suppressed rather than replayed.

## Local steps

After pulling the updated branch:

1. Stop the Discord notifier if already open. The main Shadow loop may remain running.
2. Run `01_INSTALL.bat` again to install the chart dependency.
3. Run `06_CONFIGURE_DISCORD.bat` and enter the webhook URL locally.
4. Run `07_TEST_DISCORD.bat` and confirm the Japanese test message and chart arrive.
5. Run `08_RUN_DISCORD_ALERTS.bat` and keep that window open alongside `03_RUN_LOOP.bat`.
6. Use `09_DISCORD_STATUS.bat` to inspect notification counters and errors.

The first notifier startup does not send any entry that occurred before the notifier started.
