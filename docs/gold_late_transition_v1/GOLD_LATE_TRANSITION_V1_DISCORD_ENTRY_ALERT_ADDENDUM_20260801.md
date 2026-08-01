# GOLD Late Transition V1 Discord Entry Alert Addendum

Date: 2026-08-01  
Scope: observation-only Challenger delivery sidecar

## Authorization

The user explicitly authorized Discord entry notifications together with the Late Transition V1 Prospective Shadow.

This authorization changes delivery only. It does not authorize live-ready promotion, final signals, AI judgement, MT5 orders, or live trading.

## Event

Send one notification only when the Challenger runtime's `counters.accepted_trades` increases by exactly one during a continuously running notifier session.

Do not notify:

- NO_SIGNAL
- ordinary V19 or Challenger decision rows
- suppressed Challenger events
- V19 priority entries
- recovery replay
- entries missed while the notifier was stopped
- delayed replay
- exits, TP, SL, TIME, or V19 preemption

## Message and chart

The compact Japanese message includes:

- LONG or SHORT
- MT5 broker-server entry time
- Entry
- TP20
- SL10
- `IMPULSE_LATE` or `CORRECTION_EARLY`
- selected-direction rank below P90
- V19 priority notice
- observation-only / no real order notice

An M15 chart is attached when chart generation succeeds. Chart failure falls back to text-only and never changes the Shadow result.

## Webhook security

The Challenger does not store another webhook URL.

`06_CONFIGURE_DISCORD.bat` validates and references the existing ignored local V19 configuration:

`config/gold_wave_shadow_v19/local_config.json`

The URL is not copied, printed, logged, committed, added to an Issue/PR, or sent to chat.

## Runtime separation

- Challenger notifier is a separate sidecar and process lock.
- V19 notifier remains unchanged.
- Discord failure cannot create, suppress, delay, preempt, or modify a Shadow observation.
- Startup baselines the current Challenger accepted count.
- If more than one Challenger entry occurred while the notifier was unavailable, delayed alerts are suppressed rather than replayed.
