@echo off
setlocal
set "GML1_MT5_SYMBOL=GOLD#"
set "GML1_MT5_VOLUME=0.01"
set "GML1_MT5_VOLUME_A_CORE=0.01"
set "GML1_MT5_VOLUME_B_STATE=0.01"
set "GML1_MT5_VOLUME_P18=0.01"
set "GML1_MT5_VOLUME_W024A=0.01"
call "%~dp0run_live_autotrade_loop.bat"
exit /b %ERRORLEVEL%
