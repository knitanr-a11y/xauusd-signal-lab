# NEXT CHAT HANDOFF — M10W3 PASS / M10W4 GOLD LONG difference forensics next

Repo: `knitanr-a11y/xauusd-signal-lab`
Branch: `feature/mochipoyo-alert-research`
Date: 2026-07-27

## Read first
1. this file
2. `config/mochipoyo_alert_research/current_state_20260727.json`
3. `config/mochipoyo_alert_research/next_action_20260727.json`
4. `config/mochipoyo_alert_research/m10w3_user_local_result_20260727.json`
5. `config/mochipoyo_alert_research/m10w4_gold_long_portfolio_difference_forensics_contract_20260727.json`
6. `config/mochipoyo_alert_research/m10v_short_family_comparison_preregistration_20260727.json`

## Scope / running systems
New M10 research is GOLD/XAUUSD only. M7C remains frozen BTCUSD+XAUUSD background source-fidelity collection. Keep collector/M7C/M8C/M9V/M9Y/M10B/M10E/M10P/M10P2 running unchanged. Never change frozen starts or rerun M10P/M10P2 BAT01.

## SHORT fresh remains separate
M10P and M10P2 remain fresh SHORT shadows. Latest recorded M10Q was 0 resolved for both, next gate 5. M10V is forbidden until BOTH M10P >=20 resolved and M10P2 >=20 resolved with integrity PASS. M10W historical LONG research must not bypass or read those fresh outcomes for selection.

## M10W3 PASS
Uploaded package SHA256:
`1c8646f028c17ce9c4b34158bcd32809b6b5a172b61ad7d3f5025469cedb8248`

Single-capital results:
- CORE_BASELINE: n935, PF 1.9623457969, net +4790.231951 bps, DD 328.823566 bps
- CORE_FILTERED: n913, PF 2.2149685288, net +5016.368868 bps, DD 252.988001 bps
- EXTENDED_BASELINE: n906, PF 2.3542115765, net +6812.558036 bps, DD 377.403475 bps
- EXTENDED_FILTERED: n887, PF 2.6330860824, net +6995.111625 bps, DD 357.307797 bps

Filtered-minus-baseline:
- CORE: PF +0.252623, net +226.136917 bps, DD -75.835565 bps
- EXTENDED: PF +0.278875, net +182.553589 bps, DD -20.095678 bps

Additional +2 bps per accepted trade:
- CORE_BASELINE PF 1.507454
- CORE_FILTERED PF 1.653789
- EXTENDED_BASELINE PF 1.866272
- EXTENDED_FILTERED PF 2.043549

Yearly PF is higher in filtered views for 2023/2024/2025/2026. However 2025 net falls by -151.193196 bps in CORE and -88.766578 bps in EXTENDED. This tradeoff must be explained before freezing a historical portfolio representative.

All pairwise exact same entry timestamp counts were zero. No fail-closed tie was encountered.

Interpretation: filtered H1 is now a stronger historical portfolio challenger, but not an operational replacement. M10E fresh evidence remains mandatory before operational H1 replacement.

## Next stage — M10W4
Stage:
`M10W4_GOLD_LONG_PORTFOLIO_DIFFERENCE_FORENSICS_AUDIT_ONLY`

Purpose: compare actual accepted-trade sets between baseline-H1 and filtered-H1 scenarios and explain where the portfolio delta comes from, especially 2025. This is forensics only, not a new filter search.

Run:
`scripts/mochipoyo_alert_research/m10w4/bat/01_run_gold_long_portfolio_difference_forensics.bat`

Upload:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W4\LATEST\99_UPLOAD_PACKAGE.zip`

M10W4 freezes the exact M10W3 accepted-ledger hashes. H1 baseline M10A and filtered M10D trade IDs are normalized to the same canonical H1 event identity for set comparison. It reports common, baseline-only and filtered-only accepted trades, family/year decomposition, 2025 changed trades, top absolute changed trades, and common-trade return parity.

## Prohibitions
No threshold changes, no neighborhood rescue, no new filter search, no historical backfill, no SHORT ledger use, no M10E fresh outcomes for selection, no M10P/M10P2 outcomes for selection, no running monitor modification, no Discord send, no MT5 order, no live_ready, no final_signal, no automatic promotion. MT5 server time and CLOSED-row contracts remain unchanged.
