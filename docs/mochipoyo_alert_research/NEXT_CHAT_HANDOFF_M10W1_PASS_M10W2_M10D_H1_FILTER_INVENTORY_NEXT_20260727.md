# NEXT CHAT HANDOFF — M10W1 PASS / M10W2 M10D H1 filter inventory next

Repo: `knitanr-a11y/xauusd-signal-lab`
Branch: `feature/mochipoyo-alert-research`
Date: 2026-07-27

## Read first
1. this file
2. `config/mochipoyo_alert_research/current_state_20260727.json`
3. `config/mochipoyo_alert_research/next_action_20260727.json`
4. `config/mochipoyo_alert_research/m10w1_user_local_result_20260727.json`
5. `config/mochipoyo_alert_research/m10w2_m10d_h1_filtered_reference_inventory_contract_20260727.json`
6. `config/mochipoyo_alert_research/m10v_short_family_comparison_preregistration_20260727.json`

## Scope
New M10 research remains GOLD/XAUUSD only. M7C remains its frozen BTCUSD+XAUUSD source-fidelity background track. Do not add BTC to M10 research.

## Keep running unchanged
collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2.
Do not reset/reinitialize for historical research.
M10P BAT01 and M10P2 BAT01 remain permanently forbidden.

## M10W1 result
Package SHA256: `00dfd7663daebeebfd3b048b393e4d94afb0825b7e94e48dbd1db959f97e42e7`

CORE = M5_RUNNER75 + H1_RUNNER50:
- independent: n=996, PF=2.0132204808, net=+5194.3677 bps, DD=351.5425 bps
- single-capital: n=935, PF=1.9623457969, net=+4790.2320 bps, DD=328.8236 bps
- skips=61
- +2 bps sensitivity PF=1.5074543874

EXTENDED sensitivity = CORE + H4_ENTRY:
- independent: n=1053, PF=2.3216560485, net=+7665.9642 bps, DD=408.6469 bps
- single-capital: n=906, PF=2.3542115765, net=+6812.5580 bps, DD=377.4035 bps
- skips=147
- +2 bps sensitivity PF=1.8662724162

Exact same entry timestamps across families: 0.
H4 improves historical PF/net/payoff but increases DD and blocks many M5/H1 entries, especially 70 M5 entries blocked by H4 in the extended view. Keep CORE and EXTENDED as separate views; do not promote H4 to core solely from historical-exposed results.

## SHORT fresh parallel remains unchanged
M10P: resolved 0, next gate 5.
M10P2: resolved 0, next gate 5.
M10V remains forbidden until BOTH reach at least 20 resolved and integrity checks pass.

## Why M10W2 is next
M10E is already running a fresh baseline-vs-filtered H1 comparison using a historical M10D compound-loss filter. Before later GOLD LONG portfolio reconstruction, do not assume baseline H1_RUNNER50 is the final H1 representative without checking the actual M10D historical evidence.

Expected M10D exclusion rule from frozen M10E contract:
- exclude H1 LONG when M5 MACD bps slope <= -0.1308
- AND H1 EMA30-EMA40 >= 17.3333 bps
- causal closed bars only

## M10W2
Stage: `M10W2_M10D_H1_FILTERED_REFERENCE_INVENTORY_AUDIT_ONLY`

Run:
`scripts/mochipoyo_alert_research/m10w2/bat/01_run_m10d_h1_filtered_reference_inventory.bat`

Upload only:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W2\LATEST\99_UPLOAD_PACKAGE.zip`

M10W2 is read-only. It inventories actual M10D local output hashes, JSON/CSV structures, metrics and ledgers. It does not use M10E fresh outcomes for historical selection and does not read M10P/M10P2.

After the package is reviewed, freeze whether baseline H1, filtered H1, or both as separate reference views are eligible for further GOLD LONG portfolio research.

## Safety
Audit-only. No historical backfill, no future leakage, no nearest-M1 fallback, no threshold refit, no start reset, no Discord send, no MT5 order, no live_ready, no final_signal, no automatic promotion. MT5 server time remains the project basis and newest CSV row remains CLOSED by contract.
