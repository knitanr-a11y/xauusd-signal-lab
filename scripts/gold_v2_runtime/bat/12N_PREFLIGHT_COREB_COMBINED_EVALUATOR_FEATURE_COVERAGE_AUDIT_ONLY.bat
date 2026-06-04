@echo off
cd /d "%~dp0\..\..\.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python scripts\gold_v2_runtime\preflight_coreb_combined_evaluator_feature_coverage_audit_only.py %*
pause
