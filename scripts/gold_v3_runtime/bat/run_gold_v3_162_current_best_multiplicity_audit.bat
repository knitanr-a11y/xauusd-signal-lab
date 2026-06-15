@echo off
setlocal
cd /d "%~dp0\..\..\.."
set "MT5_FILES=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
py -3 scripts\gold_v3_runtime\gold_v3_162_current_best_multiplicity_stack_audit.py --mt5-files-dir "%MT5_FILES%"
pause
