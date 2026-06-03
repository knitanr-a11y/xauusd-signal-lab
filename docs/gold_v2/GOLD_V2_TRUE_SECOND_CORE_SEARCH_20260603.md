# GOLD V2 true second Core search

Created: 2026-06-03
Status: audit-only / exploratory

## Purpose

Separate the previously found CoreA Reject add-ons from a true second Core search.

Keep these CoreA Reject add-ons as MEDIUM candidates:

```text
ORIGIN010_REFINED
VOL_TRMEAN32_REFINED
RANGE96_REFINED
```

But the search below is different. It does not start from CoreA REJECT rows. It searches the full selected-rules universe as an independent vector.

## Fixed Core A

```text
Core A:
  fold4_rules + ABC entry gate + CAP5 sizing
```

## Search universe

```text
gold_v2_candidate_universe_wf_selected_rules.csv
abc2025_fixed_rule_raw_signal_ledger.csv
gold_v2_candidate_universe_wf_cluster_members.csv
```

The search grouped selected rules by independent dimensions such as:

```text
scenario
BUY/SELL direction
RR bucket
origin/candidate id
rank bucket
training WR/PF filters
```

2025 uses the 2025 raw fixed-rule signal ledger. 2026 uses the WF TEST cluster members. This is intentionally not CoreA Reject filtering.

## Result

A clean second Core was not found.

The only broad candidates that survived loose screening were:

| Candidate | 2025 count | 2025 WR | 2025 PF | 2025 TotalR | 2025 Worst | 2026 count | 2026 WR | 2026 PF | 2026 TotalR | 2026 Worst |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BUY & RR1.0 | 623 | 56.02% | 1.43 | +211.34R | -3R | 119 | 63.87% | 1.94 | +49.0R | -3R |
| GOLDV2_ORIGIN_003 | 538 | 54.46% | 1.37 | +164.05R | -3R | 79 | 60.76% | 1.58 | +19.0R | -2R |

## Combined with Core A

| Candidate | 2025 combined count | 2025 combined WR | 2025 combined PF | 2025 combined TotalR | 2026 combined count | 2026 combined WR | 2026 combined PF | 2026 combined TotalR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CoreA + BUY & RR1.0 | 787 | 58.07% | 1.65 | +413.58R | 206 | 67.48% | 2.90 | +208.5R |
| CoreA + GOLDV2_ORIGIN_003 | 706 | 57.37% | 1.66 | +380.29R | 181 | 67.96% | 3.08 | +199.5R |

## Interpretation

These are not second Core candidates.

They add many trades, but they dilute Core A too much:

```text
Core A 2026:
  125 trades / WR 73.60% / PF 3.80 / +193.5R

CoreA + BUY&RR1.0 2026:
  206 trades / WR 67.48% / PF 2.90 / +208.5R

CoreA + ORIGIN003 2026:
  181 trades / WR 67.96% / PF 3.08 / +199.5R
```

2025 monthly stability is also poor. BUY&RR1.0 has multiple weak or negative months in 2025, including February, April, June, August, and November. ORIGIN003 is similar.

## Recommendation

Keep the CoreA Reject refined add-ons as MEDIUM candidates:

```text
RANGE96_REFINED
VOL_TRMEAN32_REFINED
TIER2_HVT
ORIGIN010_REFINED as WATCH/MEDIUM optional
```

Do not promote BUY&RR1.0 or ORIGIN003 to HIGH Core B.

A true second Core is still not found. The next search should use a structurally different rule generation step, not only selected-rules grouping. Candidates to explore next:

```text
1. BUY-only dedicated discovery with its own filters
2. LOW_VOL_RANGE dedicated discovery
3. RR1.5/RR2.0 dedicated discovery
4. fold1/fold2/fold3 independent portfolios with strict overlap control
5. Separate TP/SL universe, not reusing the current selected-rules pool
```
