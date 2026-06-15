@echo off
setlocal
cd /d "%~dp0\..\..\.."

set "MT5_FILES=C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"

echo GOLD V3 127 REBUILD CANDIDATE SOURCES THEN JUNE15
echo MT5_FILES=%MT5_FILES%

echo [01] 107GB
py -3 scripts\gold_v3_runtime\gold_v3_107gb_dual_edge_walkforward_density_and_conflict_audit.py --mt5-files-dir "%MT5_FILES%"
if errorlevel 1 goto err

echo [02] 107GC
py -3 scripts\gold_v3_runtime\gold_v3_107gc_edge_quality_density_rebalance_audit.py --mt5-files-dir "%MT5_FILES%"
if errorlevel 1 goto err

echo [03] 107GD
py -3 scripts\gold_v3_runtime\gold_v3_107gd_edge_sharpening_and_diversification_audit.py --mt5-files-dir "%MT5_FILES%"
if errorlevel 1 goto err

echo [04] 107GL
py -3 scripts\gold_v3_runtime\gold_v3_107gl_new_long_short_vector_family_generation_audit.py --mt5-files-dir "%MT5_FILES%"
if errorlevel 1 goto err

echo [05] 107GN
py -3 scripts\gold_v3_runtime\gold_v3_107gn_atomic_vector_discovery_v2_audit.py --mt5-files-dir "%MT5_FILES%"
if errorlevel 1 goto err

echo [06] 107GO
py -3 scripts\gold_v3_runtime\gold_v3_107go_atomic_vector_portfolio_and_short_gap_diagnosis_audit.py --mt5-files-dir "%MT5_FILES%"
if errorlevel 1 goto err

echo [07] 107GU
py -3 scripts\gold_v3_runtime\gold_v3_107gu_bank_oos_selection_audit.py --mt5-files-dir "%MT5_FILES%"
if errorlevel 1 goto err

echo [08] 107K2
py -3 scripts\gold_v3_runtime\gold_v3_107k2_direct_regime_balanced_adaptive_score_audit.py --mt5-files-dir "%MT5_FILES%"
if errorlevel 1 goto err

echo [09] 107L to 119
call scripts\gold_v3_runtime\bat\run_gold_v3_122_regenerate_107l_then_june_01_15_audit.bat
if errorlevel 1 goto err

echo DONE
echo Check %MT5_FILES%\FX_OUTPUTS\gold_v3\119\paste_me.txt
pause
exit /b 0

:err
echo FAILED.
echo Check paste_me under %MT5_FILES%\FX_OUTPUTS\gold_v3\<stage>\paste_me.txt
pause
exit /b 1
