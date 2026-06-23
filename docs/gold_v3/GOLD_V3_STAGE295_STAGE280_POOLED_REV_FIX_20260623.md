# GOLD V3 Stage295 — Stage280 pooled REV parity fix

## Root cause

The fixed Stage280 parity values were produced by the audited pooled REV model.
That model includes both H4 directions:

- H4 up -> predicted REV direction is SHORT
- H4 down -> predicted REV direction is LONG

The Stage289 retraining implementation incorrectly filtered to H4 down before fitting, so it trained only the LONG half of the REV population.

Observed incorrect population:

- fit_n: 1714
- cal_n: 492

Audited pooled population:

- fit_n: 4974
- cal_n: 1809

Stage281 parity already matched exactly and is unchanged.

## Fix

Stage280 training now:

1. keeps all non-neutral H4 rows;
2. sets predicted REV direction to `-h4_trend`;
3. defines target as event onset in that REV direction;
4. direction-normalizes signed returns, EMA distances, slopes, candle bodies and positions;
5. swaps upper/lower wick sides for SHORT normalization;
6. trains and calibrates on the original pooled population;
7. verifies population count, threshold and fixture score before writing artifacts.

The live LONG candidate remains H4-down only. Its normalized direction is +1, so live candidate semantics are unchanged.
