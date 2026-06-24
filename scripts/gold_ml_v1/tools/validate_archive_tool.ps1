[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ScriptPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ScriptPath -PathType Leaf)) {
    Write-Error "Archive script not found: $ScriptPath"
    exit 1
}

$tokens = $null
$parseErrors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    $ScriptPath,
    [ref]$tokens,
    [ref]$parseErrors
) | Out-Null

if ($parseErrors.Count -gt 0) {
    Write-Host "PowerShell syntax validation failed:" -ForegroundColor Red
    foreach ($item in $parseErrors) {
        Write-Host ("  Line {0}, Column {1}: {2}" -f $item.Extent.StartLineNumber, $item.Extent.StartColumnNumber, $item.Message) -ForegroundColor Red
    }
    exit 1
}

Write-Host "PowerShell syntax validation: PASS" -ForegroundColor Green
exit 0
