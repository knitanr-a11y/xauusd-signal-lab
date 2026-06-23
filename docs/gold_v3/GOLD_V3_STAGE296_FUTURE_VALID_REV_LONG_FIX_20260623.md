# GOLD V3 Stage296 — Stage280 future-valid REV_LONG parity fix

## Diagnostic result

The Stage295 population diagnostic found one exact population contract:

- H4 trend is non-neutral
- the complete 240-minute future M1 adjudication window is valid

This produces exactly:

- fit_n = 4974
- cal_n = 1809

No server-hour exclusion or D1 condition was required.

## Correct Stage280 contract

Stage280 is `STAGE280_REV_LONG_2026`, not a direction-normalized pooled REV classifier.

Training population:

- retain all future-valid H4 non-neutral rows
- keep original signed feature direction

Positive target:

- event onset
- event direction = LONG
- H4 trend = DOWN

H4-up rows remain in the population as negative examples. Rows without a valid 240-minute future M1 window are unlabelled and excluded, not converted to negative examples.

Stage281 is unchanged because its fixed threshold and fixture score already matched exactly.
