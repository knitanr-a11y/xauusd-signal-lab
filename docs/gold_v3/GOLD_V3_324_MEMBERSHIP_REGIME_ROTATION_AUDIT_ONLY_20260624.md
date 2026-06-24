# GOLD V3 Stage324 — Membership Regime Rotation Audit

## Purpose

Stage323 confirmed that the Stage322 conservative shadow lane,

`BALANCED_OR_PREMIUM`

remains profitable under spread-cost stress up to 3.0x.

Stage324 does not narrow the entry rule. Instead, it audits whether the source of edge is stable across periods or rotates between membership subgroups.

## Source integrity

Stage324 requires:

- Stage323 status and decision to match
- Stage323 stressed-trade CSV SHA256 to match
- exact 1.0x parity within `1e-12`
- no overlapping positions
- selected lane exactly `BALANCED_OR_PREMIUM`

## Fixed groups

No new raw feature threshold is added. Only existing membership labels are used:

- `SELECTED_ALL`
- `PREMIUM_INVOLVED`
- `BALANCED_WITHOUT_PREMIUM`
- `TRIPLE_CONSENSUS`
- `PREMIUM_WITHOUT_BALANCED`
- `BALANCED_AND_PREMIUM`

## Time contract

- 2024 and 2025 are the historical selection period
- 2026 is display only
- 2026 cannot promote, remove, retune, or rank any subgroup

## Fixed cost views

Membership stability is shown at:

- 1.0x recorded spread cost
- 1.5x spread cost

## Rotation test

Rotation is reported when all four descriptive conditions hold:

1. Premium-involved win rate is higher in 2024–2025.
2. Premium-involved average R per trade is higher in 2024–2025.
3. Balanced-without-premium win rate is higher in the 2026 display period.
4. Balanced-without-premium average R per trade is higher in the 2026 display period.

This test is descriptive only. It does not use 2026 to select a candidate.

## Expected interpretation

The Stage323 trade registry indicates:

- 2024–2025 Premium-involved trades were the stronger subgroup.
- 2026 display-only Balanced-without-premium trades were the stronger subgroup.

Therefore, narrowing to Premium alone may raise historical win rate but discard the subgroup that carried the later display period. The combined `BALANCED_OR_PREMIUM` shadow remains the safer research object.

## Outputs

- `stage324_membership_regime_rotation_audit.json`
- `stage324_membership_regime_group_summary.csv`
- `stage324_membership_regime_timeline.csv`

## Preserved state

- GOLD V3 audit-only
- Stage319 contract unchanged and frozen
- Stage314 contract unchanged and active
- Stage323 result unchanged
- Stage280 exact recovery remains blocked
- Stage307 candidate unchanged
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
