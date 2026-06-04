@echo off
cd /d "%~dp0\..\..\.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python scripts\gold_v2_runtime\rebuild_coreb_mapping_from_12a_audit_only.py %*
pause
