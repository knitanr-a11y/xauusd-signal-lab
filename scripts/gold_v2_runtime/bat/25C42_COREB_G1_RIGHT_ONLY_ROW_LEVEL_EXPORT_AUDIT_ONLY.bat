@echo off
cd /d "%~dp0\..\..\.."
py scripts\gold_v2_runtime\audit_gold_v2_25c42_coreb_g1_right_only_row_level_export_audit_only.py --accept-25c42-row-level-export
pause
