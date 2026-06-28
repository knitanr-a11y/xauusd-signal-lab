# GML1 M1 Microstructure V5 Realized-Volatility Rate Clarification

Date: 2026-06-28  
Mode: audit-only

The first label-free event generation showed zero rows for MS03 and MS08. No label or outcome had been joined.

The cause was dimensional: `RV5 / RV30` compares cumulative realized-volatility magnitudes over unequal windows and is structurally bounded near or below one. The intended acceleration measure is a rate comparison.

The exact frozen definition is therefore:

`rv5_to_rv30_rate = (RV5 / sqrt(5)) / (RV30 / sqrt(30)) = RV5 / RV30 * sqrt(6)`

MS03 and MS08 use this rate for the rolling quantiles and fixed 1.25 / 1.35 thresholds. All other features, events, chronology and gates remain unchanged. This clarification is made before any label, WR, PF, R, 2025 outcome or 2026 outcome is inspected.
