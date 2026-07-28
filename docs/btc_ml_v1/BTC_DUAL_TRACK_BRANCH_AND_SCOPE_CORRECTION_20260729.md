# BTC dual-track branch and scope correction

Date: 2026-07-29

## Correct model

There are two legitimate BTC-related research tracks.

1. BTC ML V1 five-candidate research
   - authoritative base: `main`
   - working branch: `feature/btc-fresh-forward-research`
   - next stage: FF01 availability read-only

2. MOCHIPOYO M7C background research
   - branch: `feature/mochipoyo-alert-research`
   - symbols: BTCUSD and XAUUSD
   - immutable start: `2026-07-20T14:54:15Z`
   - collector/M7C/M8C remain running unchanged

The active M10 candidate/value line remains GOLD-only.

## Correction to the earlier handoff

The earlier wording that treated all Mochipoyo paths as if they were irrelevant to BTC was too broad. M7C is a valid BTC-related background track and must be acknowledged and preserved.

This does not mean BTC ML V1 should be implemented on the Mochipoyo branch. The two tracks must remain separate and must not automatically exchange features, entries, outcomes, formulas, thresholds, starts or runtime state.

## Working rule

- Do not work directly on `main`.
- Do not use `feature/mochipoyo-alert-research` for BTC ML V1 FF01.
- Use `feature/btc-fresh-forward-research` in a separate clone or worktree.
- Do not checkout or disturb the existing GOLD/MOCHIPOYO working folder.
- Do not merge the Mochipoyo branch into the BTC FF01 branch.
- A future M7C-versus-BTC-ML comparison requires a separate preregistered stage and explicit user approval.

Authoritative references:

- `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_DUAL_TRACK_FF01_M7C_PRESERVED_20260729.md`
- `configs/btc_ml_v1/btc_dual_track_scope_20260729.json`
- `configs/btc_ml_v1/btc_working_branch_policy_20260729.json`
- `configs/btc_ml_v1/btc_gold_scope_firewall_20260729.json`
