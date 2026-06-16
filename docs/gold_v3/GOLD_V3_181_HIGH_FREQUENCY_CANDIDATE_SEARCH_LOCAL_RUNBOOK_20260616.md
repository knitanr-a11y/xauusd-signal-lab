# GOLD V3 Stage181 High-Frequency Candidate Search Local Runbook

Status: AUDIT_ONLY

## Run

From Windows Explorer or CMD, run:

`scripts\gold_v3_runtime\bat\run_gold_v3_181_high_frequency_candidate_search_audit.bat`

## Output to paste

Paste:

`MQL5\Files\FX_OUTPUTS\gold_v3\181\paste_me.txt`

## Optional parameters

Default target full trade count is 150 and default cost is 3.0 points.

Examples:

- More aggressive frequency target:
  - `run_gold_v3_181_high_frequency_candidate_search_audit.bat --target-full-n 200`
- Stricter negative-month requirement:
  - `run_gold_v3_181_high_frequency_candidate_search_audit.bat --max-neg-months 0`
- Different cost assumption:
  - `run_gold_v3_181_high_frequency_candidate_search_audit.bat --cost-points 5`

## Reminder

This is audit-only. It does not enable live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade.
