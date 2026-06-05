@echo off
cd /d "%~dp0\..\..\.."
python scripts\gold_v2_runtime\audit_gold_v2_17v_live_parity_safety_gate_plan_audit_only.py
pause
