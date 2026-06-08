@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c110_corea_medium_entrytime_selection_contrast_audit_only.py
endlocal
