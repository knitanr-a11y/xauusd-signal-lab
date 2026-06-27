# GML1 research challenger local runtime

Date: 2026-06-28  
Mode: audit-only historical parity

## Implemented endpoint

The runtime reconstructs the final research challenger in this order:

1. Build the completion sleeves.
2. Replace WATCH-022-B with WATCH-022-C inside A_CORE.
3. Add WATCH-024-A as the last sleeve.

| Component | Candidate | Runtime source |
|---|---|---|
| A_CORE | GML1-WATCH-022-C | raw 2023-2026 CSVs |
| B_STATE | GML1-H1D1-STATEFUL-REENTRY24-C | raw 2023-2026 CSVs |
| P16 | GML1-PROV-016-APPROX | raw pre-ML generator plus frozen historical ML truth |
| P18 | GML1-PROV-018-APPROX | raw 2023-2026 CSVs |
| P19 | GML1-PROV-019-APPROX | raw pre-ML generator plus frozen historical ML truth |
| W024A | GML1-WATCH-024-A | raw 2023-2026 CSVs |

P16 and P19 historical truth is used only to reproduce the frozen 2024-2026 research result. It is not a live rule and is rejected for any decision timestamp outside the frozen truth registry.

## Raw CSV contract

The runner looks for:

```text
gold_v3_2023_2026_m1.csv
gold_v3_2023_2026_m5.csv
gold_v3_2023_2026_m15.csv
gold_v3_2023_2026_h1.csv
gold_v3_2023_2026_h4.csv
gold_v3_2023_2026_d1.csv
```

The PowerShell runner searches the user's MT5 terminal directories for:

```text
MQL5\Files\gold_v3_2023_2026
```

An explicit directory can be supplied with `-RawDir` or the `GML1_RAW_DIR` environment variable.

The live `goldsharp_m1/m5/m15/h1/h4/d1.csv` files are recognized by the input validator, but this runtime does not produce a live signal from them.

## Run on Windows

From the repository root:

```bat
scripts\gold_ml_v1\research_challenger\run_local_runtime.bat
```

Or with an explicit path:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\gold_ml_v1\research_challenger\run_local_runtime.ps1 `
  -RawDir "C:\path\to\MQL5\Files\gold_v3_2023_2026"
```

Outputs:

```text
outputs/gold_ml_v1/research_challenger_local_runtime/
  research_challenger_local_2024.csv
  research_challenger_local_2025.csv
  research_challenger_local_2026.csv
  metrics_by_year.csv
  parity_report.json
```

The process exits non-zero if any decision time, exit time, direction, component, size, weighted R or annual metric differs from the frozen final artifacts.

## Verified result

| Period | Trades | Win rate | PF | Total R | Max DD |
|---|---:|---:|---:|---:|---:|
| 2024 | 271 | 65.6827% | 2.494489 | 137.480836 | 5.907692 |
| 2025 | 402 | 59.2040% | 2.012162 | 148.092790 | 7.384615 |
| 2026 partial | 101 | 61.3861% | 1.877287 | 42.055775 | 6.799792 |

## Controls

- audit-only;
- no model promotion;
- no live signal;
- no Discord output;
- no MT5 order;
- no P16/P19 live inference;
- no substitution with ML-04 or another model.
