[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [object[]]$RemainingArgs
)

$replacement = Join-Path $PSScriptRoot "archive_legacy_gold_local_v2.ps1"
if (-not (Test-Path -LiteralPath $replacement -PathType Leaf)) {
    throw "Replacement archive tool not found: $replacement"
}

Write-Host "This wrapper forwards to archive_legacy_gold_local_v2.ps1." -ForegroundColor Yellow
& $replacement @RemainingArgs
exit $LASTEXITCODE
