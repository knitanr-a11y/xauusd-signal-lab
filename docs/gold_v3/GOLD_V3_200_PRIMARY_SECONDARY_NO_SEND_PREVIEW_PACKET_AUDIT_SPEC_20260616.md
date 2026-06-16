# GOLD V3 Stage200 Primary + Secondary No-Send Preview Packet Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage200 creates a no-send preview packet for the combined decision surface:

- ABC = PRIMARY
- `SCALP_ONE_POSITION_FILTERED_V1_OHLC_RECOMPUTED` = SECONDARY_AUDIT_CANDIDATE / 補助戦略候補

This stage does not send Discord messages, does not place MT5 orders, and does not enable any live hook.

## Terminology

Do not classify the scalping system as a watchlist.

Allowed terms:

- SECONDARY_AUDIT_CANDIDATE
- SCALP_SECONDARY_CANDIDATE
- 補助戦略候補

## Inputs

- Stage193 selected scalping candidates
- Stage199 portfolio summary
- closed M15/H1/H4/D1 OHLC via Stage177 contract

## Behavior

1. Rebuild PRIMARY ABC detector entries from closed OHLC-derived features.
2. Rebuild SECONDARY_AUDIT_CANDIDATE detector entries from closed OHLC-derived features.
3. Apply only the fixed secondary filter:
   - exclude `SCALP_002_tp15_sl5_hz64_SHORT` when MT5 `entry_hour == 09`
4. For the latest 96 closed M15 rows, pick:
   - best PRIMARY candidate by ABC priority
   - best SECONDARY_AUDIT_CANDIDATE by selected secondary priority
5. Create a no-send preview markdown packet.

## Output route rule

- If PRIMARY signal exists, final route is PRIMARY.
- Else if SECONDARY_AUDIT_CANDIDATE signal exists, final route is SECONDARY_AUDIT_CANDIDATE.
- Else final route is NO_SIGNAL.

Regardless of route, Stage200 always sets send action to `NO_SEND_AUDIT_ONLY`.

NO_SIGNAL sends nothing.

## Outputs

- `gold_v3_200_source_coverage.csv`
- `gold_v3_200_primary_detector_entries.csv`
- `gold_v3_200_secondary_detector_entries.csv`
- `gold_v3_200_no_send_latest_tail96.csv`
- `gold_v3_200_no_send_preview_packet.md`
- `gold_v3_200_summary.json`
- `gold_v3_200_decision.csv`
- `paste_me.txt`

## Cost interpretation

- `cost3` means 3.0 price-point all-in execution friction assumption.
- `cost5` means 5.0 price-point all-in worse-execution stress assumption.
- cost5 can include wider spread, slippage, commission conversion, and execution drag.
- cost5 is not spread-only.

## Guardrails

- audit-only
- review-only
- no send
- no source CSV mutation
- no contract mutation
- no open/as-of interpretation
- no candidate pool removal
- no F002 bypass
- no final live approval
- no Discord notification
- no MT5 order
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify Discord
