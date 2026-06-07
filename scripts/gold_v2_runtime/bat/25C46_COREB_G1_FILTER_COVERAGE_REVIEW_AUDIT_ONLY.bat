@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\..\..\.."

echo [25C46] GOLD V2 CoreB G1 filter coverage review audit-only
echo [25C46] This BAT is review/plan-only. No replay, recovery, live path, AI API, Discord, MT5, or final signal is executed.
echo [25C46] Count semantics: unique_incremental_damage_keys=360; filter_attribution_rows=1260.
echo [25C46] Coverage key: variant + dataset + entry_time + policy.

python scripts\gold_v2_runtime\audit_gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only.py
set EXIT_CODE=%ERRORLEVEL%

echo [25C46] exit_code=%EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [25C46] STOP or error. Do not proceed to 25C47.
  exit /b %EXIT_CODE%
)

echo [25C46] Completed audit-only output creation.
echo [25C46] Review FX_OUTPUTS\gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only before any 25C47 work.
exit /b 0
