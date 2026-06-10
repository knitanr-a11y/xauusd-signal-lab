# GOLD V3 63 H4 closed-bar live state builder audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_63_H4_CLOSED_BAR_LIVE_STATE_BUILDER_SPEC_READY_AUDIT_ONLY`

## Purpose

Build an audit-only H4 live-readiness state from `goldsharp_h4.csv`.

Important user-confirmed input contract:

- Open/in-progress candles are **not** written into the CSV.
- Therefore Stage63 does not filter out an open H4 candle.
- The latest H4 CSV row is treated as the latest available closed H4 bar under the CSV export contract.

Stage63 verifies this closed-only input contract at the state level and prepares a small H4 state artifact for later audit-only live-readiness stages.

## Upstream source of truth

- Stage62B canonical plan READY
- `goldsharp_h4.csv` in the MT5 Files directory

## Non-negotiable safety boundaries

- GOLD V3 remains audit-only.
- No MT5 orders.
- No MT5 execution BAT.
- No Discord live notification.
- No AI API call.
- No live hook.
- No final signal.
- No candidate pool mutation.
- No high-vol profile demotion/removal.
- No GOLD V2 / old GOLD / DISC8.
- No Stage41 feature-only trading source.

## Audit checks

Stage63 checks:

1. Stage62B is READY.
2. H4 CSV exists.
3. H4 CSV has at least one data row.
4. A timestamp column can be identified.
5. H4 timestamps are parseable.
6. H4 timestamps are monotonic increasing.
7. The latest row is exported as closed-only by input contract.
8. No live/MT5/Discord/final signal flag is enabled.

## Outputs

Default output folder:

`Files\\FX_OUTPUTS\\gold_v3\\63_h4_closed_bar_live_state_builder_audit_only`

Files:

- `gold_v3_63_h4_closed_bar_live_state.csv`
- `gold_v3_63_h4_csv_inventory.csv`
- `gold_v3_63_validation_matrix.csv`
- `gold_v3_63_h4_closed_bar_state_summary.json`
- `gold_v3_63_PASTE_ME_H4_CLOSED_BAR_STATE_SUMMARY.txt`
- `GOLD_V3_63_REPORT.md`

## Success condition

Stage63 READY means:

- Stage62B canonicalization is READY.
- H4 CSV is readable and has a valid latest timestamp.
- The latest H4 CSV row is captured as the latest closed H4 bar by CSV contract.
- No live capability is enabled.

READY does not approve live trading.

## Next stage

Stage64 should implement:

`GOLD_V3_64_M15_M5_ALIGNMENT_STATE_BUILDER_AUDIT_ONLY`

It must remain audit-only.
