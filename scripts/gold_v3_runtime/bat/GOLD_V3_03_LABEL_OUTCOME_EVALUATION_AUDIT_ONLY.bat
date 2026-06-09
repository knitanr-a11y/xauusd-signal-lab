@echo off
setlocal
cd /d "%~dp0\..\..\.."
python scripts\gold_v3_runtime\gold_v3_03_label_outcome_evaluation_audit_only.py
endlocal
