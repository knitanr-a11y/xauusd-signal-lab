# GOLD Shadow Operational Research V1

Date: 2026-08-03

Status: `PREREGISTERED_READ_ONLY_OPERATIONAL_COLLECTION`

## Objective

Measure how the already frozen V19, Challenger C1 and P75 State Survival Shadow behave together in real prospective operation. This is not candidate discovery and does not alter any strategy.

## First-stage questions

1. How often do two systems accept entries at the same MT5 timestamp?
2. How often are accepted entries within 15 or 60 minutes?
3. How often are virtual holding intervals concurrent?
4. When entries are close, do directions agree or oppose?
5. What are standalone and naive combined resolved PnL/DD when available?
6. Are there missed cycles, stale state files, duplicate IDs, restart recovery increments or Discord delivery gaps?

## Source isolation

The collector opens source JSON/CSV files for reading only. It records pre/post file size and modification timestamps and fails the source-integrity check if any source changes during collection. Such a change may be caused by a normally running Shadow loop; the snapshot is then marked concurrent-write and must not be treated as atomic.

No webhook URL or local configuration file is copied. No MT5 API is imported. No Discord request is sent.

## Interpretation boundary

The first stage records natural coexistence. It does not impose a global one-position rule across systems, choose V19 priority for P75, or select the historically best suppression rule. Any later portfolio policy must be preregistered separately and evaluated prospectively.

## Missing systems

A missing optional system is reported as `NOT_AVAILABLE`, not as zero trades or zero loss. Challenger C1 is optional in the initial local config because its runtime may not be active on every machine.

## Output

Each run creates a timestamped snapshot directory and ZIP containing:

- `source_manifest.csv`
- `system_status.json`
- `normalized_entries.csv`
- `normalized_trades.csv`
- `pairwise_overlap.csv`
- `operational_incidents.csv`
- `summary.json`

The collector writes only under its own output root.
