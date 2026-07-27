# NEXT CHAT HANDOFF — M10W0 PASS / M10W1 GOLD LONG interaction next

Repo: `knitanr-a11y/xauusd-signal-lab`
Branch: `feature/mochipoyo-alert-research`
Date: 2026-07-27

## Read first
1. this file
2. `config/mochipoyo_alert_research/current_state_20260727.json`
3. `config/mochipoyo_alert_research/next_action_20260727.json`
4. `config/mochipoyo_alert_research/m10w0_user_local_result_20260727.json`
5. `config/mochipoyo_alert_research/m10w1_gold_long_family_interaction_contract_20260727.json`
6. `config/mochipoyo_alert_research/m10v_short_family_comparison_preregistration_20260727.json`

## Scope
Current new M10 research is GOLD/XAUUSD only. BTCUSD is not part of new M10 discovery/portfolio work. M7C remains its frozen BTCUSD+XAUUSD background source-fidelity track and must stay unchanged.

## Keep running unchanged
collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2.
Never rerun M10P BAT01 or M10P2 BAT01.

## Fresh SHORT state
M10P C056+G013 start `2026.07.24 23:56:00`, resolved 0, next gate 5.
M10P2 C0212 start `2026.07.27 01:39:00`, resolved 0, next gate 5.
M10V remains forbidden until BOTH reach at least 20 resolved with integrity PASS.

## M10W0 result
Uploaded package SHA256:
`a69ae0d6470ff472966f5d0be1ed01bff8926b87b47983a249f926731336f251`

M10A source status:
`PASS_DETERMINISTIC_HISTORICAL_REPRODUCTION_ONLY`
Sample is research-exposed 2023-01-03 through 2026-06-19 GOLD history, not fresh forward evidence. Historical spread is modeled; commission and swap are NOT modeled.

Historical LONG references:
- M5_ENTRY: n842, PF 1.5373384446, net +1840.0165 bps, DD 227.3232
- M5_RUNNER75: n837, PF 1.6651962764, net +2391.6185 bps, DD 211.0661
- H1_ENTRY: n171, PF 2.8141304039, net +2729.0995 bps, DD 271.5832
- H1_RUNNER50: n159, PF 2.8303858343, net +2802.7492 bps, DD 271.5832
- H4_ENTRY: n57, PF 4.6687987441, net +2471.5965 bps, DD 270.9863

At +2 bps extra cost per trade, PF remains >1 for all five references. M5_RUNNER75=1.166406, H1_RUNNER50=2.515706, H4_ENTRY=4.351631.

Classification frozen after M10W0 review:
- M5_ENTRY = baseline reference only; do not double-count with M5_RUNNER75
- M5_RUNNER75 = core M10A LONG family representative, historical-only
- H1_ENTRY = baseline reference only; do not double-count with H1_RUNNER50
- H1_RUNNER50 = core M10A LONG family representative, historical-only
- H4_ENTRY = low-frequency premium/reference sensitivity; not core until independently justified

## M10W1 next
Stage:
`M10W1_GOLD_LONG_FAMILY_HISTORICAL_INTERACTION_AUDIT_ONLY`

Run:
`scripts/mochipoyo_alert_research/m10w1/bat/01_run_gold_long_family_interaction_audit.bat`

Upload:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W1\LATEST\99_UPLOAD_PACKAGE.zip`

M10W1 reads only the frozen M10A LONG ledgers.
CORE view: M5_RUNNER75 + H1_RUNNER50.
EXTENDED sensitivity: M5_RUNNER75 + H1_RUNNER50 + H4_ENTRY.

It reports individual metrics, pairwise overlap count/minutes, exact same entry timestamp count, independent-arm combined metrics, deterministic single-capital first-come-first-served metrics, cross-family skips, accepted count by family, +0.5/+1/+1.5/+2 bps cost sensitivity, and yearly results.

Single-capital policy is frozen before execution: while one accepted LONG position is active, later LONG family entries are skipped. Exact same entry timestamp across families is fail-closed; no post-outcome tie-break is invented.

M10W1 does NOT read any SHORT ledger, does NOT read M10P/M10P2 fresh outcomes, does NOT execute M10V, and does NOT authorize M10W integrated LONG+SHORT execution.

## Safety
Audit-only. No historical backfill, future leakage, nearest-M1 fallback, threshold refit, start reset, Discord send, MT5 order, live_ready, final_signal, or automatic promotion. Project decisions remain MT5 server time and newest CSV rows remain CLOSED by contract.
