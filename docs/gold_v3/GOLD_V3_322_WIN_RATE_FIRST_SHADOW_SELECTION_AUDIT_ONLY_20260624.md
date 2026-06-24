# GOLD V3 Stage322 — Win-Rate-First Shadow Selection Audit

## Purpose

Stage321 selected `ANY_OF_THREE` with a general composite score. The user’s current priority is more specific: improve win rate without collapsing the sample size.

Stage322 therefore re-ranks only Stage321 lanes that already passed the fixed Stage321 robustness gate and retain at least 20 trades in 2024–2025.

No raw feature threshold is added.

## Selection contract

- 2024 and 2025 only for selection and ranking
- 2026 display only
- Stage321 gate-pass lanes only
- at least 20 selection trades
- duplicate and source integrity inherited from Stage321

Ranking priority:

1. highest 2024–2025 win rate
2. highest 2024–2025 PF
3. lowest 2024–2025 DD
4. highest minimum leave-one-quarter-out R
5. highest 2024–2025 total R
6. highest trade count
7. stable lane name

## Redundancy audit

Stage321 showed:

- Balanced-only unique trades: zero
- `ANY_OF_THREE` is therefore effectively the same unique trade set as `CORE_OR_PREMIUM`
- the three labels are not three independent diversifying streams

Stage322 records and verifies this explicitly.

## Expected comparison focus

The primary comparison is:

- broad: `ANY_OF_THREE` / effectively `CORE_OR_PREMIUM`
- conservative: `BALANCED_OR_PREMIUM`

Both had the same 2024–2025 win rate in Stage321. The conservative lane had the higher PF, so the win-rate-first contract should prefer it when source files match the audited Stage321 result.

The 2026 display-only result remains excluded from selection.

## Outputs

- `stage322_win_rate_first_shadow_selection_audit.json`
- `stage322_win_rate_first_shadow_leaderboard.csv`
- `stage322_selected_conservative_shadow_trades.csv`

## Preserved state

- GOLD V3 audit-only
- Stage319 contract unchanged and frozen
- Stage314 contract unchanged and active
- Stage321 result unchanged
- Stage280 exact recovery remains blocked
- Stage307 candidate unchanged
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
