@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0\..\.."

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set TRADE_OUTCOME_CSV=data\gold_specialist_8\verification\trade_outcomes\gold_specialist_8_validation_trade_outcome_ledger.csv
set GROUP_CSV=data\gold_specialist_8\verification\trade_outcomes\gold_specialist_8_group_trade_ledger_validation.csv
set COMPONENT_CSV=data\gold_specialist_8\verification\trade_outcomes\gold_specialist_8_component_signal_ledger_validation.csv
set REVIEW_LEDGER=data\gold_specialist_8\verification\ai_review_validation\trade_ai_review_ledger.jsonl

echo ============================================================
echo GOLD specialist 8 AI review AUDIT ONLY - NO API
echo ============================================================
echo This BAT does NOT call OpenAI API.
echo It only counts validation rows and existing review ledger rows.
echo ============================================================

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$trade='%TRADE_OUTCOME_CSV%'; $group='%GROUP_CSV%'; $component='%COMPONENT_CSV%'; $ledger='%REVIEW_LEDGER%';" ^
  "$tradeRows=if(Test-Path $trade){(Import-Csv $trade).Count}else{0};" ^
  "$groupRows=if(Test-Path $group){(Import-Csv $group).Count}else{0};" ^
  "$componentRows=if(Test-Path $component){(Import-Csv $component).Count}else{0};" ^
  "$ledgerRows=if(Test-Path $ledger){(Get-Content $ledger | Where-Object {$_.Trim().Length -gt 0}).Count}else{0};" ^
  "Write-Host '';" ^
  "Write-Host 'trade outcome rows : ' $tradeRows;" ^
  "Write-Host 'group rows         : ' $groupRows;" ^
  "Write-Host 'component rows     : ' $componentRows;" ^
  "Write-Host 'AI review rows     : ' $ledgerRows;" ^
  "Write-Host '';" ^
  "if(Test-Path $trade){" ^
  "  Write-Host 'Top strategy_id in trade outcome:';" ^
  "  Import-Csv $trade | Group-Object strategy_id | Sort-Object Count -Descending | Select-Object -First 20 Count,Name | Format-Table -AutoSize;" ^
  "}" ^
  "if(Test-Path $ledger -and $ledgerRows -gt 0){" ^
  "  Write-Host 'Top strategy_id in AI review ledger:';" ^
  "  Get-Content $ledger | Where-Object {$_.Trim().Length -gt 0} | ConvertFrom-Json | Group-Object strategy_id | Sort-Object Count -Descending | Select-Object -First 20 Count,Name | Format-Table -AutoSize;" ^
  "}"

echo.
echo AUDIT ONLY finished. No API call was made.
pause
exit /b 0
