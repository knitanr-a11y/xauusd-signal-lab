param(
  [string]$RawDir = "",
  [string]$Python = "py -3.12",
  [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path

function Test-RawDir([string]$Path) {
  $required = @(
    "gold_v3_2023_2026_m1.csv",
    "gold_v3_2023_2026_m5.csv",
    "gold_v3_2023_2026_m15.csv",
    "gold_v3_2023_2026_h1.csv",
    "gold_v3_2023_2026_h4.csv",
    "gold_v3_2023_2026_d1.csv"
  )
  if (-not (Test-Path $Path -PathType Container)) { return $false }
  foreach ($name in $required) {
    if (-not (Test-Path (Join-Path $Path $name) -PathType Leaf)) { return $false }
  }
  return $true
}

if ([string]::IsNullOrWhiteSpace($RawDir)) {
  if (-not [string]::IsNullOrWhiteSpace($env:GML1_RAW_DIR)) {
    $RawDir = $env:GML1_RAW_DIR
  } else {
    $terminalRoot = Join-Path $env:APPDATA "MetaQuotes\Terminal"
    $matches = @()
    if (Test-Path $terminalRoot) {
      Get-ChildItem $terminalRoot -Directory | ForEach-Object {
        $candidate = Join-Path $_.FullName "MQL5\Files\gold_v3_2023_2026"
        if (Test-RawDir $candidate) { $matches += $candidate }
      }
    }
    if ($matches.Count -eq 1) {
      $RawDir = $matches[0]
    } elseif ($matches.Count -eq 0) {
      throw "gold_v3_2023_2026 raw CSV directory was not found. Pass -RawDir or set GML1_RAW_DIR."
    } else {
      throw "Multiple raw CSV directories were found. Pass -RawDir explicitly: $($matches -join ', ')"
    }
  }
}

if (-not (Test-RawDir $RawDir)) {
  throw "RawDir is missing one or more required 2023-2026 CSVs: $RawDir"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
  $OutputDir = Join-Path $RepoRoot "outputs\gold_ml_v1\research_challenger_local_runtime"
}

$truthDir = Join-Path $RepoRoot "config\gold_ml_v1\research_challenger\runtime_20260628\registries"
$script = Join-Path $RepoRoot "scripts\gold_ml_v1\research_challenger\build_local_runtime.py"

if (-not (Test-Path $script -PathType Leaf)) {
  throw "Runtime script was not found: $script"
}
if (-not (Test-Path $truthDir -PathType Container)) {
  throw "Historical exclusion registry directory was not found: $truthDir"
}

Write-Host "RepoRoot:  $RepoRoot"
Write-Host "RawDir:    $RawDir"
Write-Host "TruthDir:  $truthDir"
Write-Host "OutputDir: $OutputDir"

$parts = $Python -split ' '
$exe = $parts[0]
$prefix = @()
if ($parts.Count -gt 1) { $prefix = $parts[1..($parts.Count - 1)] }
$args = $prefix + @(
  $script,
  "--raw-dir", $RawDir,
  "--truth-dir", $truthDir,
  "--output-dir", $OutputDir
)

& $exe @args
if ($LASTEXITCODE -ne 0) {
  throw "Research challenger local runtime failed with exit code $LASTEXITCODE"
}

Write-Host "PASS: final research challenger matches the frozen 2024-2026 row hashes and metrics."
