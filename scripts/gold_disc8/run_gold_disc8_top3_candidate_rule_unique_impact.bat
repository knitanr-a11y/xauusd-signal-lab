@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python scripts\gold_disc8\audit_gold_disc8_top3_candidate_rule_unique_impact.py --consolidation-root "data\runtime_logs\gold_disc8_top3_candidate_rule_consolidation\latest" --replay-root "data\runtime_logs\gold_disc8_top3_candidate_rule_replay_568\latest" --out-root "data\runtime_logs\gold_disc8_top3_candidate_rule_unique_impact" --expected-trade-rows 568
set EXIT_CODE=%ERRORLEVEL%
echo exit_code=%EXIT_CODE%
echo outputs: data\runtime_logs\gold_disc8_top3_candidate_rule_unique_impact\latest
pause
exit /b %EXIT_CODE%
