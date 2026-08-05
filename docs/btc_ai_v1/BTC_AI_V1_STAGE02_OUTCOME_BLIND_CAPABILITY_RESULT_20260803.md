# BTC AI V1 Stage 02 — Outcome-Blind Capability Result

Date: 2026-08-03  
Status: `COMPLETE_OUTCOME_BLIND_CAPABILITY_RESULT`

## Scope

This stage implemented causal closed-bar features, a deterministic 1,200-candidate registry, expanding validation-fold masks, exact-M1 entry availability checks, and structural/event-overlap diversity selection.

No PnL, TP/SL result, 2026 final-test result, or post-result threshold selection was used.

## Implementation correction before acceptance

The first dry run incorrectly allowed some families to consume their 200-candidate quota on LONG rules before SHORT rules were generated. That run was rejected and not used.

The accepted run generated exactly 100 LONG and 100 SHORT definitions per family, 1,200 total.

## Accepted result

- feature rows: 125,567
- development rows, 2024–2025: 70,066
- raw candidates: 1,200
- explicit capability passes before deduplication: 740
- exact duplicate definitions/events: 328
- unique explicit passes: 721
- selected capability survivors: 300
- near-duplicate rejections: 164

## Selected survivors

By family:

```json
{
  "CANDLE_SWING_EPISODE_STATE": 99,
  "BREAKOUT_COMPRESSION_EXPANSION": 75,
  "TREND_CONTINUATION_PULLBACK_RECLAIM": 57,
  "MULTI_TIMEFRAME_ALIGNMENT_OR_DISAGREEMENT": 54,
  "VOLATILITY_STATE_AND_TRANSITION": 15
}
```

By direction:

```json
{
  "SHORT": 161,
  "LONG": 139
}
```

## Frozen boundaries maintained

- 2026-01-01 through 2026-07-31 untouched final test: not opened.
- fixed spread: not used at capability stage.
- old BTC BCR candidates: not used as seeds.
- GOLD candidate definitions: not copied.

## Output hashes

- candidate registry: `25e13f91e9a848a9b9516127c96ef681446eeb7e4f2951294a3cdbac26a400e1`
- capability survivors: `01133d4e4e4b42c2f854d82e9deace4f6b8ccd8e704fce11bad2585e5fe29bad`
