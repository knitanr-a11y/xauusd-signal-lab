@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c102_non_id_discriminator_full_set_audit_only.py
endlocal
