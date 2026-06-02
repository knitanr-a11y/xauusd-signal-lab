@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ============================================================
echo GOLD DISC8 all 8 strategy demo gate design AUDIT ONLY
echo ============================================================
echo.
echo This BAT reads:
echo   data\runtime_logs\gold_disc8_ai_tag_vs_numeric_gate_replay_568\latest\gold_disc8_ai_tag_vs_numeric_gate_replay_568_strategy_summary.csv
echo   data\runtime_logs\gold_disc8_ai_tag_vs_numeric_gate_replay_568\latest\gold_disc8_ai_tag_vs_numeric_gate_replay_568_overall_summary.csv
echo   data\runtime_logs\gold_disc8_top3_candidate_rule_unique_impact\latest\gold_disc8_top3_candidate_rule_unique_strategy_summary.csv
echo   data\runtime_logs\gold_disc8_top3_candidate_rule_unique_impact\latest\gold_disc8_top3_candidate_rule_unique_classification_summary.csv
echo.
echo This BAT writes:
echo   data\runtime_logs\gold_disc8_all_strategy_demo_gate_design\latest
echo.
echo Please upload after run:
echo   gold_disc8_all_strategy_demo_gate_design_summary.json
echo   gold_disc8_all_strategy_demo_gate_design_strategy_plan.csv
echo   gold_disc8_all_strategy_demo_gate_design_action_summary.csv
echo   gold_disc8_all_strategy_demo_gate_design.audit_only.json
echo.
echo Safety:
echo   No OpenAI API, no Discord, no MT5, no SOT mutation, no runtime gate mutation.
echo   This is all 8 strategy design audit only. It does not enable dispatch_ready.
echo.

python scripts\gold_disc8\audit_gold_disc8_all_strategy_demo_gate_design.py ^
  --replay-root "data\runtime_logs\gold_disc8_ai_tag_vs_numeric_gate_replay_568\latest" ^
  --unique-root "data\runtime_logs\gold_disc8_top3_candidate_rule_unique_impact\latest" ^
  --out-root "data\runtime_logs\gold_disc8_all_strategy_demo_gate_design" ^
  --expected-trade-rows 568

set EXIT_CODE=%ERRORLEVEL%
echo.
echo exit_code=%EXIT_CODE%
echo outputs: data\runtime_logs\gold_disc8_all_strategy_demo_gate_design\latest
pause
exit /b %EXIT_CODE%
