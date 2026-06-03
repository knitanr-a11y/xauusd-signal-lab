@echo off
cd /d "%~dp0\..\..\.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python scripts\gold_v2_runtime\freeze_gold_v2_coreb_source_rule_conditions_audit_only.py %*
pause
