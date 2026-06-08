@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c106_goldv2_corea_medium_high_signal_triage_audit_only.py
endlocal
