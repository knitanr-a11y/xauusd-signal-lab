# NEXT CHAT HANDOFF — M9X IMPLEMENTED / LOCAL REPRODUCTION NEXT

Date: 2026-07-24  
Repo: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

Read first:
1. `docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9V_RUNNING_M9W_PAYOFF_FOUND_M9X_NEXT_20260724.md`
2. `config/mochipoyo_alert_research/current_state_20260723.json`
3. `config/mochipoyo_alert_research/next_action_20260723.json`
4. `config/mochipoyo_alert_research/m9w_gold_entry_exit_decoupling_assistant_side_result_20260724.json`

## Current live/audit state

- M8C running unchanged; never reset.
- M7C unchanged; genuine source collector running.
- M9V v2 fresh multi-timeframe forward remains immutable at MT5 server time `2026.07.24 11:04:00`.
- M9V runtime = `M9V_RUNTIME_V2_APPEND_SAFE_PREFIX`.
- Never rerun M9V BAT00 or BAT01.
- Never reset/backfill M9V.
- M9W/M9X is historical research only and is NOT inserted into M9V.
- Discord/MT5 order/live-ready/final-signal/real-entry-gate remain OFF.

## M9W finding

The strongest payoff direction is not tighter fixed stops. It is:

1. improve entry by requiring fast reclaim near the original PRIMARY price,
2. use N6 as half-risk sizing rather than signal suppression,
3. treat native M7C EXIT as a profit-management event,
4. when latest closed H1 MACD still rises, keep a runner until causal M15 RCI9 turn-down.

Reference W1 entry:
- reclaim level = PRIMARY bid - 0.10 * latest closed M5 ATR14
- if first-turn bid is already above level, enter normally
- otherwise wait at most 10 fully closed M1 bars for a close reclaim
- enter at exact next M1 open with historical spread
- no reclaim before timeout/native exit => skip

Historical/exposed reference:
- W1 entry only: n1054, ~25.1/month, WR62.33%, PF1.5875, avg win +16.37, avg loss -17.11, DD358.9
- W1 + N6 half risk + 50% runner: PF1.6576, WR57.97%, avg win +17.22, avg loss -14.33, DD291.5, +2bps PF1.3149
- 75% runner: PF1.6441, WR55.88%, avg win +18.86, avg loss -14.53, DD300.2, payoff ~1.30:1
- weak quarters 2024Q4 and 2025Q3 remain

Do NOT call this forward validated.

## M9X implemented

Implementation:

`scripts/mochipoyo_alert_research/m9x/python/run_gold_payoff_decoupling_reproduction.py`

The script deterministically rebuilds canonical M9P N3 and asserts the historical M9W reference numbers before emitting output.

It also outputs:
- component attribution,
- runner share 25/50/75/100,
- reclaim offset 0.00/0.05/0.10/0.15/0.20 ATR,
- wait 5/10/15/20/30 minutes,
- year/quarter/month metrics,
- +1/+2bps cost stress,
- audit/data-quality files.

## User action now

Keep M8C/M7C/collector/M9V running unchanged.

Pull latest `feature/mochipoyo-alert-research`, then run exactly once:

`scripts/mochipoyo_alert_research/m9x/bat/01_run_gold_payoff_decoupling_reproduction.bat`

Expected line begins:

`[M9X PASS] N3=1495 W1=1054`

After PASS run:

`scripts/mochipoyo_alert_research/m9x/bat/02_open_latest_results.bat`

Submit:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9X\LATEST\99_UPLOAD_PACKAGE.zip`

If BLOCKED, send the full screen output and do not change M9V.

## Next after M9X PASS

- verify exact ledger/metrics against M9W,
- assess neighborhood plateau rather than historical optimum,
- decide whether a NEW separate payoff prospective shadow is justified,
- never retrofit W1 into the existing M9V start,
- continue M9V base breadth forward separately.

## Next-chat prompt

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

もちぽよアラート研究の続きです。
最初に以下を順番どおり読んでください。

1. docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9X_IMPLEMENTED_LOCAL_REPRODUCTION_NEXT_20260724.md
2. docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9V_RUNNING_M9W_PAYOFF_FOUND_M9X_NEXT_20260724.md
3. config/mochipoyo_alert_research/current_state_20260723.json
4. config/mochipoyo_alert_research/next_action_20260723.json
5. config/mochipoyo_alert_research/m9w_gold_entry_exit_decoupling_assistant_side_result_20260724.json

M8C/M7C/genuine source collector/M9V v2を停止・reset・backfillしないでください。M9V startはMT5 server time 2026.07.24 11:04:00でimmutableです。M9V BAT00/01再実行禁止です。

M9WでENTRY reclaim＋N6 half-risk＋separate runnerが損小利大方向として有望でしたがhistorical research-exposedです。M9X deterministic implementationは作成済みで、次は番号付きBATによるlocal reproduction確認です。
```
