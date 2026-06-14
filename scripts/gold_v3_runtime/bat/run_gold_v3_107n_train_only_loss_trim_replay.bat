@echo off
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_107n_train_only_loss_trim_replay_audit.py
pause
