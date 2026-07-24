# NEXT CHAT HANDOFF — M9V RUNNING / M9W PAYOFF FOUND / M9X NEXT

Date: 2026-07-24  
Repo: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

## Current operating state

- M7C remains unchanged, audit-only.
- M8C remains running, never reset.
- Genuine source collector remains running.
- M9V runtime v2 fresh GOLD multi-timeframe forward start is immutable at MT5 server time `2026.07.24 11:04:00`.
- M9V runtime contract = `M9V_RUNTIME_V2_APPEND_SAFE_PREFIX`.
- Never rerun M9V BAT 00 or BAT 01.
- Never delete/reset/backfill M9V v2.
- M9V V0/V1/V2 remains the base multi-timeframe forward breadth experiment.
- Discord send, MT5 orders, live-ready, final signal and real entry gate remain OFF.

## Objective clarification

Final goal is not exact source reproduction. Goal is robust multi-timeframe / multi-asset trading edge with useful portfolio frequency and preferably positive reward/risk (損小利大), not merely high win rate.

The user explicitly wants:
- better entry location,
- smaller losses without arbitrary tight stops,
- profit taking as a separate vector from alert-state EXIT,
- allowing winners to run when native EXIT occurs but higher-timeframe momentum remains favorable.

## M9W assistant-side historical exploration

Formal result:

`config/mochipoyo_alert_research/m9w_gold_entry_exit_decoupling_assistant_side_result_20260724.json`

Status:

`PASS_EXPLORATORY_ASSISTANT_SIDE_ONLY_NOT_FORWARD_VALIDATED`

The 2023-2026 GOLD sample is research-exposed. M9W is not independent validation and must not be promoted from historical results alone.

### Baseline N3

- n = 1495
- ~35.6 trades/month
- WR = 62.27%
- PF = 1.3659
- avg win = +17.20 bps
- avg loss = -20.87 bps
- DD = 510.5 bps
- max losing streak = 11

### Path diagnosis

Winning N3 trades:
- avg MFE +23.85 bps
- avg MAE -12.83 bps
- avg hold ~127 min

Losing N3 trades:
- avg MFE only +6.05 bps
- avg MAE -43.67 bps
- avg hold ~251 min

Large losers usually do not move favorably much and remain open longer.

However, simple loss-cut rules failed:
- first-turn M1 pivot stop PF ~0.83
- recent M5/M15 structure stops mostly PF around/below 1 and worse DD
- representative 60-min MFE/time fail exit reduced avg loss but PF fell to ~1.319 and DD worsened

Conclusion: do NOT solve payoff by blindly tightening the initial stop.

## Native EXIT is not necessarily best economic full exit

After native M7C EXIT, N3 still shows average post-exit MFE:
- 15m +7.14 bps
- 30m +10.81
- 60m +16.04
- 120m +22.53
- 240m +32.57

When latest closed H1 MACD(6,13) is still rising at native EXIT:
- n=1116
- post-60m avg MFE +16.97 bps
- post-120m +23.74
- post-240m +33.28
- average extension to next causal M15 RCI9 turn-down +1.34 bps

When H1 MACD is not rising, average extension to that same runner exit is -0.93 bps.

Therefore native source EXIT should be treated as a profit-management event, not automatically as 100% economic exit.

## Entry-location discovery

Key finding: deepest pullback is NOT best.

Using first-turn bid/open versus original PRIMARY bid/open and entry-time latest closed M5 ATR14:

- first-turn bid already >= PRIMARY bid: n502, WR63.75%, PF1.698, avg win +16.41, avg loss -16.98, every year PF>1
- first-turn still >0.5 M5 ATR below PRIMARY: n369, PF1.145, avg loss -25.72, 2024 PF<1

Thus the useful concept is **reclaim confirmation**, not bottom fishing.

## W1 reclaim-entry reference family

Reference rule for deterministic reproduction:

`W1_RECLAIM_0P10_ATR5_WITHIN_10M`

At canonical M15 N3 first-turn:
1. Use ATR14 from the latest fully closed M5 available at that decision.
2. Reclaim level = original PRIMARY bid - 0.10 * M5 ATR14.
3. If first-turn bid/open is already >= level, enter normally.
4. Otherwise wait at most 10 fully closed M1 bars.
5. After the first causal M1 close >= level, enter at the exact next M1 open, paying historical spread.
6. If no reclaim before timeout/native M7C exit, skip the trade.

Reference entry-only result:
- n=1054
- ~25.1 trades/month
- WR62.33%
- PF1.5875
- avg win +16.37
- avg loss -17.11
- DD358.9
- maxLS8
- +2bps cost PF1.2446
- yearly PF = 1.261 / 1.534 / 1.542 / 1.985

Neighborhood tested:
- reclaim offsets 0.00/0.05/0.10/0.15/0.20 ATR
- waits 5/10/15/20/30 minutes

Improvement exists across a broad nearby family; do not select a single historical best cell.

## Separate risk vector

N6 remains sizing only:
- H4 RCI9 percentile >25% and <=50% in trailing100 closed H4 bars
- evaluate at ACTUAL delayed/reclaim entry time
- size/risk 0.5x
- do not suppress the signal

## Separate profit vector

At native M7C LONG_EXIT:
- inspect latest fully closed H1 MACD(6,13)
- if H1 MACD line is still rising, native EXIT becomes a partial-profit event
- runner exits at the first later M15 decision whose latest fully closed M15 RCI9 makes causal turn-down: current < previous and previous >= previous2

Runner share is not frozen yet.

### W1 + N6 + selective runner sensitivity

25% runner:
- WR60.15%
- PF1.6615
- avg win +15.84
- avg loss -14.39
- DD290.0
- +2bps PF1.3051

50% runner:
- WR57.97%
- PF1.6576
- avg win +17.22
- avg loss -14.33
- DD291.5
- +2bps PF1.3149
- yearly PF 1.408 / 1.457 / 1.427 / 2.511

75% runner:
- WR55.88%
- PF1.6441
- avg win +18.86
- avg loss -14.53
- DD300.2
- +2bps PF1.3195
- payoff about 1.30:1

100% runner:
- WR54.27%
- PF1.6263
- avg win +20.57
- avg loss -15.01
- DD320.8
- +2bps PF1.3215

The family shows a clear tradeoff: larger runner lowers WR but creates true positive reward/risk. Do not pick historical optimum; 50-75% is the central research range.

Remaining weak quarters persist:
- 2024Q4 PF <1
- 2025Q3 PF <1

So M9W is promising but not complete.

## Next: M9X

Stage:

`M9X_GOLD_PAYOFF_DECOUPLING_DETERMINISTIC_REPRODUCTION_AND_ROBUSTNESS`

Do assistant-side first. No new user BAT yet.

Required M9X work:
1. Deterministically reproduce canonical M9P N3.
2. Reproduce W1 reclaim entry exactly using closed bars only.
3. Verify M5 Wilder ATR14 timing and PRIMARY bid/open semantics.
4. Recompute N6 at actual delayed entry time.
5. Reproduce H1-MACD selective runner and exact M15 RCI9-turn-down exit.
6. Reproduce component attribution: entry only, entry+N6, entry+runner, combined.
7. Reproduce runner shares 25/50/75/100 without optimizing to best history.
8. Stress reclaim offset 0.00-0.20 ATR and waits 5-30m.
9. Output year/quarter/month frequency, PF, payoff, DD, max streak, tails, +1/+2bps sensitivity.
10. Do not modify M9V fresh forward and do not start a new payoff forward shadow until M9X deterministic PASS.

## Files to read first in next chat

1. `docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9V_RUNNING_M9W_PAYOFF_FOUND_M9X_NEXT_20260724.md`
2. `config/mochipoyo_alert_research/current_state_20260723.json`
3. `config/mochipoyo_alert_research/next_action_20260723.json`
4. `config/mochipoyo_alert_research/m9w_gold_entry_exit_decoupling_assistant_side_result_20260724.json`
5. `config/mochipoyo_alert_research/m9v_v2_initial_local_pass_20260724.json`
6. `config/mochipoyo_alert_research/m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json`
7. `config/mochipoyo_alert_research/m9u_multitimeframe_portfolio_deterministic_reproduction_result_20260724.json`

## Next-chat prompt

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

もちぽよアラート期待値・発火条件研究の続きです。
まず次を順番どおり読んでください。

1. docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9V_RUNNING_M9W_PAYOFF_FOUND_M9X_NEXT_20260724.md
2. config/mochipoyo_alert_research/current_state_20260723.json
3. config/mochipoyo_alert_research/next_action_20260723.json
4. config/mochipoyo_alert_research/m9w_gold_entry_exit_decoupling_assistant_side_result_20260724.json

M8C / M7C / genuine source collector / M9V v2 fresh forwardは変更・停止・resetしないでください。
M9V startはMT5 server time 2026.07.24 11:04:00でimmutableです。BAT00/01は再実行禁止です。

M9Wで損小利大方向として、ENTRY reclaim確認＋N6半リスク＋native EXITとは別のselective runnerが有望と判明しました。ただしhistorical research-exposedで未forwardです。
次はM9X deterministic reproduction/robustnessをassistant-sideで進めてください。新しいBATはまだ不要です。
```
