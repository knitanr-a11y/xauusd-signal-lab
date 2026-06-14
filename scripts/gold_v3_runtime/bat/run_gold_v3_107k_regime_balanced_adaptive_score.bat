@echo off
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_107k_regime_balanced_adaptive_score_audit.py
pause
