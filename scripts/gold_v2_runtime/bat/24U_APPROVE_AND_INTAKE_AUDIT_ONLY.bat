@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\write_gold_v2_24u_selected_value.py
python scripts\gold_v2_runtime\audit_gold_v2_24u_choice_intake_audit_only.py
pause
