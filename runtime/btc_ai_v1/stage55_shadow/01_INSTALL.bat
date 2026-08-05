@echo off
setlocal
title BTC Stage55 Shadow - Install
cd /d "%~dp0"
echo ============================================================
echo BTC STAGE55 SHADOW - INSTALL
echo Observation only / MT5 orders OFF
echo ============================================================
py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo [BTC_STAGE55_SHADOW] Install finished.
pause
