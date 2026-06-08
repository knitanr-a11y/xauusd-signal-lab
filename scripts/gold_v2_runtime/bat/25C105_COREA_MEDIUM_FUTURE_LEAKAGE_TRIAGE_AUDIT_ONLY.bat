@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c105_corea_medium_future_leakage_triage_audit_only.py
endlocal
