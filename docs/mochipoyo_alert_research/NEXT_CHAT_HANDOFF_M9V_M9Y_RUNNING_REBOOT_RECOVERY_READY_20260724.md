# NEXT CHAT HANDOFF — M9V/M9Y RUNNING / FORCED-REBOOT RECOVERY READY

Date: 2026-07-24  
Repo: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

## Current running state

Keep these audit-only monitors running in parallel:

1. Genuine source Cloudflare collector
2. M7C prospective shadow
3. M8C forward shadow
4. M9V v2 GOLD multi-timeframe breadth shadow
5. M9Y GOLD payoff / 損小利大 shadow

All trading/notification actions remain OFF:
- Discord send OFF
- MT5 orders OFF
- live-ready OFF
- final signal OFF
- real entry gate OFF

Immutable starts:
- M7C valid prospective start UTC: `2026-07-20T14:54:15Z`
- M9V start MT5 server time: `2026.07.24 11:04:00`
- M9Y start MT5 server time: `2026.07.24 12:45:00`

Never reset/reinitialize those starts.

## Why forced reboot needs a special recovery step

Collector, M7C, M9V and M9Y use exclusive lock files. Under normal stop their Python `finally`/context cleanup removes the lock. Windows forced reboot/power loss can prevent that cleanup, leaving a stale lock even though the process is gone.

Formal contract:

`config/mochipoyo_alert_research/forced_reboot_recovery_contract_20260724.json`

Recovery BAT:

`scripts/mochipoyo_alert_research/recovery/bat/01_recover_after_forced_reboot.bat`

Recovery behavior:
- verifies protected collector/M7C/M9V/M9Y processes are not running,
- if any protected process is running => BLOCK and touch no lock,
- archives confirmed stale lock files,
- removes only those stale locks,
- never deletes/resets runtime manifests, prospective starts, SQLite DB, M8C state or output history.

## Exact restart order after a forced reboot

Do NOT rerun any initializer.

1. Confirm MT5 terminal / CSV-producing export has restarted and `goldsharp_*` / `btcusdsharp_*` CSVs are updating again.
2. Pull latest branch if local code does not yet contain the recovery BAT.
3. Run once:

   `scripts/mochipoyo_alert_research/recovery/bat/01_recover_after_forced_reboot.bat`

4. After `[REBOOT RECOVERY PASS]`, restart:

   `scripts/mochipoyo_alert_research/run_collect_events_cloudflare_forever.bat`

5. Then:

   `scripts/mochipoyo_alert_research/run_m7c_prospective_shadow_forever.bat`

6. Then:

   `scripts/mochipoyo_alert_research/m8c/bat/02_run_forward_shadow_forever.bat`

7. Then:

   `scripts/mochipoyo_alert_research/m9v/bat/03_run_shadow_forever.bat`

8. Then:

   `scripts/mochipoyo_alert_research/m9y/bat/03_run_shadow_forever.bat`

Never after reboot:
- rerun/reset M7C initializer,
- rerun/reset M8C initializer/start,
- run M9V BAT00 or BAT01,
- run M9Y BAT01,
- manually delete runtime manifests/start receipts,
- move prospective start forward/backward to cover downtime.

## Downtime data rule

The monitor processes themselves can stop temporarily without invalidating the frozen start. Their reports are reconstructed from the frozen start and currently available source data.

However recovery of the downtime interval depends on the underlying source data becoming complete again:
- Cloudflare source events use preserved cursor/database and can catch up backlog.
- MT5 CSVs must actually restore/contain the closed bars from the PC-off interval.
- If a permanent MT5 CSV gap remains, that gap must be recorded as unobserved; never silently count it as valid forward evidence.

## How long to keep the monitors running

Not by a fixed calendar date. Use frozen review checkpoints.

### M7C
- operational: 5 supported events
- interim: 15 supported events
- formal: >=30 supported events
- formal minimums also include per ticker >=10, PRIMARY_LONG >=5, PRIMARY_SHORT >=5, total exits >=10

### M8C
Formal review when all are met:
- total future proxy PRIMARY >=30
- BTCUSD PRIMARY_LONG >=8
- challenger accepted >=15

### M9V
- operational: total accepted arm events >=20
- interim: >=60
- H1 S3 branch review: >=10 S3 candidates
- formal: >=120

### M9Y
- operational: Y0 accepted >=20
- interim: >=60
- N6 risk layer: >=10 N6-flagged actual entries
- formal: Y0 accepted >=120

At the first operational checkpoint, manually inspect implementation integrity, frequency, PF, win rate, payoff ratio, DD/tails, overlap behavior and regime weakness. A checkpoint is a review trigger, NOT automatic promotion.

Historical M9Y-like W1 frequency was about 25 trades/month, so 20 Y0 entries is roughly a few weeks under similar conditions, 60 roughly 2–3 months, 120 roughly 4–5 months. This is only a planning estimate; forward market regime controls actual cadence.

The genuine source collector should continue while any M7C/M8C/source-attribution research remains active.

## Current payoff research context

M9X deterministic historical reproduction PASS:
- canonical N3 1495
- W1 reclaim 1054
- one-position 50% runner + N6: n1008, PF1.6629, avg win +17.40bps, avg loss -15.08bps
- one-position 75% runner + N6: n1008, PF1.6483, avg win +18.95bps, avg loss -15.27bps

This is historical/research-exposed, not fresh validation.

M9Y fresh arms:
- Y0 W1 native exit
- Y1 W1 + N6 half-risk native exit
- Y2 W1 + N6 + 50% selective runner
- Y3 W1 + N6 + 75% selective runner

M9Y remains separate from M9V and reads M9V S2 candidates read-only only when PRIMARY time is strictly after the independent M9Y start.

## Read first in a new chat

1. `docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9V_M9Y_RUNNING_REBOOT_RECOVERY_READY_20260724.md`
2. `config/mochipoyo_alert_research/current_state_20260723.json`
3. `config/mochipoyo_alert_research/next_action_20260723.json`
4. `config/mochipoyo_alert_research/forced_reboot_recovery_contract_20260724.json`
5. `config/mochipoyo_alert_research/m9y_initial_local_pass_20260724.json`
6. `config/mochipoyo_alert_research/m9x_gold_payoff_decoupling_local_reproduction_result_20260724.json`

## Next-chat prompt

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

もちぽよアラート研究の続きです。
最初に次を順番どおり読んでください。

1. docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9V_M9Y_RUNNING_REBOOT_RECOVERY_READY_20260724.md
2. config/mochipoyo_alert_research/current_state_20260723.json
3. config/mochipoyo_alert_research/next_action_20260723.json
4. config/mochipoyo_alert_research/forced_reboot_recovery_contract_20260724.json

M7C/M8C/M9V/M9Y/genuine source collectorはfresh forward継続中です。
M9V start=2026.07.24 11:04:00 MT5 server time、M9Y start=2026.07.24 12:45:00です。
reset/backfill/reinitialize禁止です。

強制再起動時は専用 recovery BAT でstale lockだけ安全に回復し、initializerは再実行しません。
現在は固定日数ではなくreview gateで運用し、M9Vは20/60/120、M9YはY0 20/60/120（N6>=10）で段階確認します。
```
