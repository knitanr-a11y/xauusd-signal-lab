# GML1 New Candidate Discovery V1 — State-Machine Addendum

Date: 2026-06-28  
Mode: audit-only

This addendum is frozen before proposal-density replay and before any label or performance inspection.

It applies to NCD-001, NCD-002, NCD-003 and NCD-005.

## Pending setup rules

- Each candidate ID may hold at most one pending setup at a time.
- A new setup trigger is ignored while that candidate ID already has a pending setup.
- The setup bar itself cannot also be the confirmation bar.
- Setup age is counted in subsequently closed M15 bars: the first later bar has age 1.
- On every later closed bar, checks occur in this exact order:
  1. expiry;
  2. invalidation;
  3. confirmation.
- Therefore a bar satisfying both invalidation and confirmation is invalidated and emits no proposal.
- After confirmation, invalidation or expiry, the pending state is cleared.
- A fresh setup may begin only on a later closed bar; the clearing bar is not reused as a new setup bar.
- Higher-timeframe context is required and frozen at the setup bar. It is not re-evaluated using future higher-timeframe bars while the setup is pending.
- Frozen price levels and setup-bar values are never recomputed after setup creation.

## Family expiry

- NCD-001 expires after age 8.
- NCD-002 expires after age 6.
- NCD-003 expires after age 12; age 1 cannot confirm.
- NCD-005 expires after age 4.

## NCD-004 onset rule

NCD-004 has no pending setup. Its active condition is evaluated on each newly closed M15 bar. A raw proposal is emitted only when the active condition changes from false to true. The previous active state is carried forward sequentially and cannot be recomputed from future bars.

## 2026 prospective replay

The same state objects are advanced one closed M15 bar at a time through 2026. No state may be hydrated using a setup that would not have been observable from the preceding closed-bar stream. Prefix replay must produce identical proposals for every already-processed timestamp.
