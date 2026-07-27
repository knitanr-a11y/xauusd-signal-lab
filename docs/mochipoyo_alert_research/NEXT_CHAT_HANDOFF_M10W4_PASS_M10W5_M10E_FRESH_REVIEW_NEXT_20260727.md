# NEXT CHAT HANDOFF — M10W4 PASS / M10W5 M10E fresh review next

Repo: `knitanr-a11y/xauusd-signal-lab`
Branch: `feature/mochipoyo-alert-research`
Date: 2026-07-27

## Read first
1. this file
2. `config/mochipoyo_alert_research/current_state_20260727.json`
3. `config/mochipoyo_alert_research/next_action_20260727.json`
4. `config/mochipoyo_alert_research/m10w4_user_local_result_20260727.json`
5. `config/mochipoyo_alert_research/m10w5_m10e_fresh_checkpoint_review_contract_20260727.json`
6. `config/mochipoyo_alert_research/m10v_short_family_comparison_preregistration_20260727.json`

## Scope and running systems
New M10 research remains GOLD/XAUUSD only. M7C keeps its existing frozen BTCUSD+XAUUSD background source-fidelity scope.
Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2 running unchanged.
Never reinitialize M10P or M10P2. Never reset M10E.

Immutable starts include:
- M10E `2026.07.24 22:06:00`
- M10P `2026.07.24 23:56:00`
- M10P2 `2026.07.27 01:39:00`
all MT5 server time.

## SHORT fresh track remains separate
M10V remains forbidden until BOTH M10P >=20 resolved and M10P2 >=20 resolved with integrity PASS. LONG research does not bypass this gate.

## M10W4 result
Uploaded package SHA256:
`9d133b694edc3bd0d74f7dbdf96ae2dc24990e7e8bf1c8aada99f40849d0656c`

CORE filtered-minus-baseline accepted-set forensics:
- common 905
- baseline-only 30 trades, net -122.315329 bps
- filtered-only 8 trades, net +103.821587 bps
- baseline-only is entirely H1
- filtered-only is 1 filtered-H1 trade + 7 M5 trades

Year deltas filtered-minus-baseline CORE:
- 2023 +166.127437 bps
- 2024 +103.308488 bps
- 2025 -151.193196 bps
- 2026 +107.894188 bps

2025 explanation:
- baseline-only H1: 15 trades, net +223.306287 bps
- 9 winners total +504.439504 bps
- 6 losers total -281.133217 bps
- includes one large loss -243.155057 bps
- filtered-only freed-capacity M5: 5 trades, net +72.113091 bps
Thus the filter still removes a large loss, but in 2025 it also sacrifices enough H1 winners that the freed M5 capacity does not replace the removed positive H1 net.

EXTENDED 2025:
- baseline-only H1 net +223.306287 bps
- baseline-only M5 net +26.089223 bps
- filtered-only M5 net +72.113091 bps
- filtered-only H4 net +88.515842 bps
- resulting delta -88.766578 bps

Interpretation:
- filtered H1 remains a strong historical challenger
- overall portfolio improvement is explained by accepted-trade composition, not an accounting mismatch
- 2025 is a real historical tradeoff, not an integrity failure
- baseline H1 remains retained
- operational H1 replacement remains forbidden before independent M10E fresh evidence

## Next stage — M10W5
Stage:
`M10W5_M10E_H1_FILTER_FRESH_CHECKPOINT_REVIEW_AUDIT_ONLY`

No new historical search is required first. M10E is already running the exact frozen baseline-versus-filtered H1 fresh comparison.

Do NOT run any M10E initializer/reset.

Upload the CURRENT existing package from:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10E\LATEST\99_UPLOAD_PACKAGE.zip`

M10E fixed filter remains:
- M5 MACD bps slope <= -0.1308
- H1 EMA30-EMA40 >= 17.3333 bps
- exclude only when both are true

Review gates remain:
- 5 accepted: operational integrity review only
- 10 accepted: interim descriptive review
- 20 accepted: formal fresh baseline-versus-filtered review
No automatic promotion at any gate.

Below 5 accepted, still review start/integrity/count coherence and continue accumulation without an efficacy claim.

## Safety
Audit-only. No backfill, no threshold refit, no future leakage, no nearest-M1 fallback, newest CSV row CLOSED, MT5 server time only, no Discord send, no MT5 orders, no live_ready, no final_signal, no automatic promotion.
