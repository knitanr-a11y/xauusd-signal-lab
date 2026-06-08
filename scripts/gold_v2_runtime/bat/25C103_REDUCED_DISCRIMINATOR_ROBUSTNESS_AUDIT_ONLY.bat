@echo off
setlocal
cd /d %~dp0\..\..\..
python scripts\gold_v2_runtime\audit_gold_v2_25c103_reduced_discriminator_robustness_audit_only.py
endlocal
