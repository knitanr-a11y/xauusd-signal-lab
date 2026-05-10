# GOLD multi-strategy Mochipoyo-loop FOREVER minute-aligned DRY-RUN runner.
# PowerShell launcher.
#
# Why this exists:
# - The .bat launcher works, but Windows cmd.exe may ask
#   "Terminate batch job (Y/N)?" after Ctrl+C.
# - This PowerShell launcher calls Python directly, so Ctrl+C is handled by
#   the Python runner's graceful KeyboardInterrupt path without the extra
#   batch-job prompt.
#
# Safety:
# - This launcher never passes --send.
# - It calls only the independent aligned dry-run Python runner.
# - It does not call existing Mochipoyo production/demo BATs.
# - It does not write production position_registry.csv.
# - It does not intentionally mutate existing Mochipoyo ledgers or trigger-state files.
#
# Stop:
# - Press Ctrl+C in this PowerShell window.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

$OutDir = "data\research_results\gold_multi_strategy_mochipoyo_loop_dry_run_aligned"

Write-Host "============================================================"
Write-Host "GOLD multi-strategy Mochipoyo-loop FOREVER minute-aligned DRY-RUN runner"
Write-Host "PowerShell launcher / NO --send / independent wrapper only / every minute at second 02"
Write-Host "OUT_DIR=$OutDir"
Write-Host "Stop with Ctrl+C"
Write-Host "============================================================"

python scripts\run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.py `
  --out-dir $OutDir `
  --max-cycles 0 `
  --interval-minutes 1 `
  --offset-seconds 2 `
  --no-run-immediately

$ExitCode = $LASTEXITCODE

Write-Host "============================================================"
Write-Host "GOLD forever minute-aligned dry-run loop exit code: $ExitCode"
Write-Host "summary_json: $OutDir\latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json"
Write-Host "aligned_loop_log_csv: $OutDir\aligned_loop_log.csv"
Write-Host "============================================================"

exit $ExitCode
