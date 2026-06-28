# GML1 M1 Microstructure V5 Event Specification

Date: 2026-06-28  
Mode: audit-only

All events are evaluated at an M5 decision time using only M1 bars whose close time is at or before that decision. Windows crossing an M1 gap are invalid. LONG and SHORT are exact directional mirrors. Direct states emit only on false-to-true onset.

For directional notation, `d=+1` for LONG and `d=-1` for SHORT. Directional return is `d * net_return`. Favorable sweep means a low sweep/reclaim for LONG and high sweep/reclaim for SHORT. Favorable wick means lower wick for LONG and upper wick for SHORT.

Rolling thresholds use the previous 256 valid M5 decisions, excluding the current decision. `Q20`, `Q33`, `Q67`, `Q80` and `Q90` mean the corresponding rolling quantile for that feature.

## MS01 — Spread normalization continuation

- 15-minute spread 90th percentile was at or above its rolling Q80;
- current spread is no greater than 1.10 times the 15-minute spread median;
- directional five-minute net return is positive;
- five-minute directional efficiency is at or above its rolling Q67;
- five-minute volume/return alignment is positive.

## MS02 — Tick-volume burst continuation

- five-minute maximum tick volume is at or above its rolling Q90;
- five-minute tick-volume burst count is at least one;
- directional five-minute net return is positive;
- five-minute directional efficiency is at or above rolling Q67;
- the just-closed M5 body is in the candidate direction.

## MS03 — Low-volatility release

- prior decision's 30-minute realized volatility is at or below rolling Q20;
- current five-to-thirty-minute realized-volatility ratio is at or above rolling Q80 and greater than 1.25;
- directional five-minute net return is positive;
- five-minute realized volatility is at or above rolling Q67;
- current spread is no greater than 1.25 times the 30-minute spread median.

## MS04 — High-volatility exhaustion reclaim

- 15-minute realized volatility is at or above rolling Q80;
- directional 15-minute net return is negative;
- directional five-minute net return is positive;
- at least one favorable sweep/reclaim occurred in the last 15 minutes;
- favorable wick share exceeds adverse wick share over 15 minutes.

## MS05 — Micro sweep/reclaim

- at least one favorable sweep/reclaim occurred in the last five minutes;
- directional five-minute net return is positive;
- five-minute close-location average is favorable: at least 0.55 after direction normalization;
- current spread is no greater than the 15-minute spread 90th percentile.

## MS06 — High-efficiency continuation

- 15-minute directional efficiency is at or above rolling Q80;
- directional 15-minute and five-minute net returns are both positive;
- 15-minute volume/return alignment is positive;
- current spread-to-15-minute-median ratio is no greater than 1.25.

## MS07 — Low-efficiency failed-move reversal

- 15-minute directional efficiency is at or below rolling Q20;
- directional 15-minute net return is negative;
- directional five-minute net return is positive;
- at least one favorable sweep/reclaim occurred in the last 15 minutes;
- five-minute efficiency exceeds 15-minute efficiency.

## MS08 — Realized-volatility acceleration

- five-to-thirty-minute realized-volatility ratio is at or above rolling Q80 and greater than 1.35;
- directional five-minute net return is positive;
- five-minute positive-return fraction after direction normalization is at least 0.60;
- current spread is no greater than 1.25 times its 15-minute median.

## MS09 — Stagnation breakout

- prior decision's 30-minute stagnant-return fraction is at or above rolling Q80;
- current five-minute realized volatility is at or above rolling Q80;
- directional five-minute net return is positive;
- five-minute directional efficiency is at or above rolling Q67.

## MS10 — Repeated rejection reversal

- at least two favorable sweep/reclaims occurred in the last 15 minutes;
- favorable wick share exceeds adverse wick share over 15 minutes;
- directional five-minute net return is positive;
- five-minute close-location average is at least 0.55 after direction normalization.

## MS11 — Spread/volume normalized re-entry

- five-to-thirty-minute spread ratio is at or below rolling Q33;
- five-to-thirty-minute tick-volume rate is at or above rolling Q67;
- directional five-minute net return is positive;
- five-minute efficiency is at or above rolling Q67;
- 15-minute directional return is not negative.

## MS12 — Intrabar wick-imbalance reversal

- favorable-minus-adverse 15-minute wick share is at or above rolling Q80;
- directional 15-minute net return is non-positive;
- directional five-minute net return is positive;
- five-minute close-location average is at least 0.60 after direction normalization;
- at least one favorable sweep/reclaim occurred in the last 15 minutes.

## Label-free density handling

The original rules are immutable. Families failing the pre-registered density gate are retained for audit but are not performance-selected or rescued by ML in V5. No threshold may be changed after the label join.
