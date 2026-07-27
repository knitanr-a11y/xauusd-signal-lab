# NEXT CHAT HANDOFF — M10Q PASS / M10W0 GOLD LONG inventory next

Repo: `knitanr-a11y/xauusd-signal-lab`
Branch: `feature/mochipoyo-alert-research`
Date: 2026-07-27

## Read first
1. this file
2. `config/mochipoyo_alert_research/current_state_20260727.json`
3. `config/mochipoyo_alert_research/next_action_20260727.json`
4. `config/mochipoyo_alert_research/m10w0_gold_long_reference_inventory_contract_20260727.json`
5. `config/mochipoyo_alert_research/m10v_short_family_comparison_preregistration_20260727.json`
6. `docs/mochipoyo_alert_research/M10P_AND_AFTER_SHORT_ADOPTION_ROADMAP_20260725.md`

## Scope
Current new M10 research is GOLD/XAUUSD only. Do not add BTCUSD. M7C remains its already-frozen BTCUSD+XAUUSD background source-fidelity track and stays unchanged.

## Keep running unchanged
collector / M7C / M8C / M9V / M9Y / M10B / M10E / M10P / M10P2.

Immutable starts include M10P `2026.07.24 23:56:00` and M10P2 `2026.07.27 01:39:00` MT5 server time. Never rerun M10P BAT01 or M10P2 BAT01.

## Latest M10Q
M10P: candidate 0, resolved 0, next gate 5.
M10P2: candidate 0, resolved 0, next gate 5.
No fresh condition yet. Do not loosen thresholds.

M10V remains preregistration-only and must not execute before BOTH M10P >=20 resolved and M10P2 >=20 resolved with integrity PASS.

## Next stage: M10W0
`M10W0_GOLD_LONG_REFERENCE_INVENTORY_AUDIT_ONLY`

Purpose: inspect the actual existing M10A GOLD LONG historical/deterministic artifacts before deciding which LONG arms may enter future M10W LONG+SHORT reconstruction.

Run:
`scripts/mochipoyo_alert_research/m10w0/bat/01_run_gold_long_reference_inventory.bat`

Upload only:
`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W0\LATEST\99_UPLOAD_PACKAGE.zip`

M10W0 is read-only. It inventories hashes, JSON structures, CSV row counts/columns/time ranges and arm/branch/direction fields, and packages readable M10A artifacts. It does not select a LONG arm, does not use M10P/M10P2 fresh outcomes for selection, and does not modify any running monitor.

After the M10W0 package is reviewed, freeze an explicit M10W LONG eligibility inventory from actual evidence before implementing LONG+SHORT historical reconstruction.

## Safety
Audit-only. No historical backfill, no future leakage, no nearest-M1 fallback, no prospective threshold refit, no start reset, no Discord send, no MT5 orders, no live_ready, no final_signal, no automatic promotion. Project time basis remains MT5 server time and newest CSV row remains CLOSED by contract.
