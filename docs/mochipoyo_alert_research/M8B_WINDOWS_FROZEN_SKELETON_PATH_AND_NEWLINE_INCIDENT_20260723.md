# M8B Windows frozen skeleton path/newline incident — 2026-07-23

## Scope

Stage: `M8B_EXTRA_SIGNAL_OUTCOME_AUDIT`

This incident occurred before any M8B outcome result was produced. No M7C formula, threshold, runtime manifest, prospective start, candidate timestamp, trade pairing, or outcome rule was changed.

## Incident 1: raw-byte SHA mismatch

The frozen CSV was committed with LF line endings. A Windows checkout may present CRLF line endings. The original runner compared raw bytes, so identical CSV values could fail SHA256 verification after checkout.

Correction: normalize only UTF-8 BOM and newline representation before SHA verification. CSV rows and field values remain unchanged.

## Incident 2: config-relative path failure

The first correction still referenced the canonical frozen CSV through a repo-relative `config/...` path from the BAT. On the user's Windows/MT5 nested checkout this dependency failed with `FileNotFoundError` before outcome reading.

Correction: add an operational mirror at:

`scripts/mochipoyo_alert_research/m8b/data/m8b_frozen_trade_skeleton_20260723.csv`

The operational mirror has the exact same Git blob SHA as the canonical config file:

`e101bdbc2b6877a2d7324e687d5f1edbc01cff1e`

The BAT now reads only this adjacent M8B data mirror and still normalizes BOM/newline bytes before the existing frozen content SHA256 check.

## Frozen population remains unchanged

- finalized extra signals: 36
- extra-entry trades evaluated for WR/PF: 18
- extra exit actions: 18, not double-counted as trades
- pending source-arrival-grace: excluded
- expected normalized skeleton SHA256: `f42ce896f00b717320662ff1b64991718bf3e1ce7dfe0d671c62f362731f7acc`

## Safety

- audit-only: ON
- Discord send: OFF
- MT5 order: OFF
- live ready: OFF
- final signal: OFF
- entry gate: OFF

No outcome was used to make either correction.
