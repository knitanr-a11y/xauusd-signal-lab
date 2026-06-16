# GOLD V3 Stage201 No-Send Preview Packet Format Audit Spec

Date: 2026-06-16
Status: AUDIT_ONLY

## Purpose

Stage201 formats the Stage200 no-send preview packet.

It does not change signal logic, candidate rules, portfolio selection, or live behavior.

## Inputs

- `gold_v3_200_no_send_latest_tail96.csv`
- `gold_v3_200_decision.csv`
- `gold_v3_199_portfolio_summary_cost3_cost5.csv`

## Formatting requirements

- NO_SIGNAL rows must not display `nan/nan/nan`.
- Missing TP/SL/Horizon must display `-`.
- Latest preview must be separated from tail96 detail.
- Tail96 detail should show compact latest row and compact signal rows.
- Use `SECONDARY_AUDIT_CANDIDATE` or `補助戦略候補` for the secondary scalping system.
- Keep no-send, no-order, and no-notification safety text explicit.

## Outputs

- `gold_v3_201_latest_role_preview.csv`
- `gold_v3_201_latest_compact_preview.csv`
- `gold_v3_201_tail96_signal_rows_compact.csv`
- `gold_v3_201_no_send_preview_packet_clean.md`
- `gold_v3_201_summary.json`
- `gold_v3_201_decision.csv`
- `paste_me.txt`

## Pass conditions

- blocker_count == 0
- no `nan` string in the clean preview packet
- no legacy secondary-candidate label string in the clean preview packet
- no send enabled
- no order enabled
- no notification enabled
- no payload/live hook/autotrade enabled
- NO_SIGNAL notification remains disabled

## Cost interpretation

- `cost5` is an all-in worse-execution stress proxy.
- It can include wider spread, slippage, commission conversion, and execution drag.
- It is not spread-only.

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
- no notification
- no order
- no AI API
- no live hook
- no payload
- no autotrade
- NO_SIGNAL must not notify
