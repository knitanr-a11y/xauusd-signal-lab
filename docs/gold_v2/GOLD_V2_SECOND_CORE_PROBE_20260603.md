# GOLD V2 second Core probe

Created: 2026-06-03
Status: audit-only / exploratory

## Purpose

The current main candidate is:

```text
Core A:
  fold4_rules + ABC entry gate + CAP5 sizing
```

The Tier2 add-on experiments were not decisive. This probe checks whether a stronger, separate `Core B` can be found from rows not selected by Core A.

## Search principle

Core B candidates were searched only from Core A REJECT rows.

Rules use entry-known cluster/market features only. They do not use future profit/outcome fields.

## Candidate quality

| policy | 2025 count | 2025 WR | 2025 PF | 2025 TotalR | 2026 count | 2026 WR | 2026 PF | 2026 TotalR | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| COREB_VOL_TRMEAN32_CAP3 | 92 | 56.52% | 1.62 | +42.75R | 128 | 53.13% | 1.48 | +30.0R | MEDIUM_ADDON_ONLY |
| COREB_RANGE96_192_CAP3 | 73 | 57.53% | 1.68 | +36.0R | 84 | 53.57% | 1.43 | +18.0R | MEDIUM_ADDON_ONLY |
| COREB_RANGE96_CAP3 | 92 | 56.52% | 1.53 | +36.5R | 105 | 53.33% | 1.40 | +21.5R | WEAK_OR_REJECT |
| COREB_ORIGIN010_CAP3 | 103 | 55.34% | 1.36 | +26.45R | 14 | 85.71% | 3.60 | +13.0R | WEAK_OR_REJECT |
| TIER2_STATIC_CAP3 | 39 | 69.23% | 3.83 | +51.0R | 28 | 60.71% | 1.77 | +10.0R | MEDIUM_ADDON_ONLY |
| TIER2_HVT_CAP3 | 20 | 80.00% | 6.83 | +35.0R | 11 | 81.82% | 6.25 | +10.5R | MEDIUM_ADDON_ONLY |

## Combined comparison

| policy | 2025 count | 2025 WR | 2025 PF | 2025 TotalR | 2026 count | 2026 WR | 2026 PF | 2026 TotalR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CORE_A_ONLY | 200 | 65.50% | 2.38 | +230.24R | 125 | 73.60% | 3.80 | +193.5R |
| CORE_A_PLUS_COREB_VOL_TRMEAN32_CAP3 | 292 | 62.67% | 2.16 | +272.99R | 253 | 63.24% | 2.71 | +223.5R |
| CORE_A_PLUS_COREB_RANGE96_192_CAP3 | 273 | 63.37% | 2.21 | +266.24R | 209 | 65.55% | 2.91 | +211.5R |
| CORE_A_PLUS_COREB_RANGE96_CAP3 | 292 | 62.67% | 2.13 | +266.74R | 230 | 64.35% | 2.75 | +215.0R |
| CORE_A_PLUS_COREB_ORIGIN010_CAP3 | 303 | 62.05% | 2.07 | +256.69R | 139 | 74.82% | 3.79 | +206.5R |
| CORE_A_PLUS_TIER2_STATIC_CAP3 | 239 | 66.11% | 2.52 | +281.24R | 153 | 71.24% | 3.48 | +203.5R |
| CORE_A_PLUS_TIER2_HVT_CAP3 | 220 | 66.82% | 2.53 | +265.24R | 136 | 74.26% | 3.87 | +204.0R |

## Interpretation

No clean second Core was found.

The broad volatility candidates add many trades, but standalone quality is much lower than Core A:

```text
COREB_VOL_TRMEAN32_CAP3:
  2025 PF 1.62 / WR 56.52%
  2026 PF 1.48 / WR 53.13%
```

They increase total R but dilute win rate and PF. This is not appropriate as a HIGH-priority Core.

The origin-specific candidate is unstable:

```text
COREB_ORIGIN010_CAP3:
  2025 PF 1.36
  2026 PF 3.60
```

This is too dependent on one origin and not robust enough.

The best high-quality add-ons remain Tier2 variants, especially:

```text
TIER2_HVT_CAP3:
  2025: 20 trades / WR 80.00% / PF 6.83 / +35.0R
  2026: 11 trades / WR 81.82% / PF 6.25 / +10.5R
```

However, this is too small to be a full Core B.

## Recommendation

Do not promote a second Core from this probe.

Current operating hierarchy should remain:

```text
HIGH:
  Core A = fold4_rules + ABC + CAP5

MEDIUM candidate:
  Tier2 HVT / Tier2 confluence only

Reject for HIGH Core:
  broad volatility add-ons
  origin-only add-ons
```

If more trade count is needed, the next search should use a structurally different candidate universe rather than only Core A rejects.
