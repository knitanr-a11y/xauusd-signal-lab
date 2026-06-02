@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ============================================================
echo GOLD DISC8 demo runtime gate candidate config AUDIT ONLY
echo ============================================================
echo.
echo This BAT reads:
echo   data\runtime_logs\gold_disc8_all_strategy_demo_gate_design\latest\gold_disc8_all_strategy_demo_gate_design.audit_only.json
echo   data\runtime_logs\gold_disc8_all_strategy_demo_gate_design\latest\gold_disc8_all_strategy_demo_gate_design_strategy_plan.csv
echo   data\runtime_logs\gold_disc8_top3_candidate_rule_consolidation\latest\gold_disc8_demo_runtime_gate_candidate.audit_only.json
echo.
echo This BAT writes:
echo   data\runtime_logs\gold_disc8_demo_runtime_gate_candidate_config\latest
echo.
echo Please upload after run:
echo   gold_disc8_demo_runtime_gate_candidate_config_summary.json
echo   gold_disc8_demo_runtime_gate_candidate_config_strategy_policy.csv
echo   gold_disc8_demo_runtime_gate_candidate_config.audit_only.json
echo.
echo Safety:
echo   This is still audit-only. It does NOT enable dispatch_ready, Discord, MT5, or runtime gate mutation.
echo.

python scripts\gold_disc8\build_gold_disc8_demo_runtime_gate_candidate_config.py ^
  --design-root "data\runtime_logs\gold_disc8_all_strategy_demo_gate_design\latest" ^
  --detail-root "data\runtime_logs\gold_disc8_top3_candidate_rule_consolidation\latest" ^
  --out-root "data\runtime_logs\gold_disc8_demo_runtime_gate_candidate_config"

set EXIT_CODE=%ERRORLEVEL%
echo.
echo exit_code=%EXIT_CODE%
echo outputs: data\runtime_logs\gold_disc8_demo_runtime_gate_candidate_config\latest
pause
exit /b %EXIT_CODE%
