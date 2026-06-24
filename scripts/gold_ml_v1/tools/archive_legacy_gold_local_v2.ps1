[CmdletBinding()]
param(
    [string]$ArchiveRoot = (Join-Path $env:USERPROFILE "Documents\GOLD_OLD_ARCHIVES"),
    [string[]]$AdditionalPaths = @(),
    [switch]$IncludeLegacyProjectFolders,
    [switch]$IncludeRootGoldCsvs,
    [switch]$RemoveOriginals,
    [switch]$RemoveRootGoldCsvs,
    [switch]$NonInteractive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$ScriptVersion = "2.0.0"
$SessionId = Get-Date -Format "yyyyMMdd_HHmmss"
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.."))
$ArchiveRoot = [System.IO.Path]::GetFullPath($ArchiveRoot)
$SessionRoot = Join-Path $ArchiveRoot ("GOLD_OLD_ARCHIVE_" + $SessionId)
$StagingRoot = Join-Path $SessionRoot "_staging"

function Read-YesNo {
    param([string]$Prompt, [bool]$Default = $false)
    if ($NonInteractive) { return $Default }
    $suffix = if ($Default) { "[Y/n]" } else { "[y/N]" }
    while ($true) {
        $answer = (Read-Host "$Prompt $suffix").Trim().ToLowerInvariant()
        if ([string]::IsNullOrWhiteSpace($answer)) { return $Default }
        if ($answer -in @("y", "yes")) { return $true }
        if ($answer -in @("n", "no")) { return $false }
        Write-Host "Y または N を入力してください。" -ForegroundColor Yellow
    }
}

function Get-CanonicalPath {
    param([string]$Path)
    return [System.IO.Path]::GetFullPath($Path).TrimEnd([char[]]@('\', '/'))
}

function Get-RelativePathCompat {
    param([string]$BasePath, [string]$TargetPath)
    $baseFull = (Get-CanonicalPath $BasePath) + [System.IO.Path]::DirectorySeparatorChar
    $targetFull = Get-CanonicalPath $TargetPath
    $baseUri = New-Object System.Uri($baseFull)
    $targetUri = New-Object System.Uri($targetFull)
    $relative = [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString())
    return $relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
}

function Test-IsUnderPath {
    param([string]$Child, [string]$Parent)
    $childPath = (Get-CanonicalPath $Child) + [System.IO.Path]::DirectorySeparatorChar
    $parentPath = (Get-CanonicalPath $Parent) + [System.IO.Path]::DirectorySeparatorChar
    return $childPath.StartsWith($parentPath, [System.StringComparison]::OrdinalIgnoreCase)
}

function Get-ShortHash {
    param([string]$Text)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        $hash = $sha.ComputeHash($bytes)
        return ([System.BitConverter]::ToString($hash).Replace("-", "").ToLowerInvariant()).Substring(0, 10)
    }
    finally { $sha.Dispose() }
}

function Get-SafeName {
    param([string]$Text)
    $safe = ($Text -replace '[^A-Za-z0-9._-]', '_').Trim('_')
    if ([string]::IsNullOrWhiteSpace($safe)) { $safe = "archive" }
    if ($safe.Length -gt 80) { $safe = $safe.Substring(0, 80) }
    return $safe
}

function Get-FilesRecursive {
    param([string]$SourcePath)
    return @(Get-ChildItem -LiteralPath $SourcePath -File -Recurse -Force -ErrorAction Stop | Sort-Object FullName)
}

function Test-ZipEntryCount {
    param([string]$ZipPath, [int]$ExpectedCount)
    $zip = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $actual = @($zip.Entries | Where-Object { -not [string]::IsNullOrEmpty($_.Name) }).Count
    }
    finally { $zip.Dispose() }
    if ($actual -ne $ExpectedCount) {
        throw "ZIP_ENTRY_COUNT_MISMATCH: expected=$ExpectedCount actual=$actual zip=$ZipPath"
    }
}

function New-ManifestRow {
    param(
        [string]$SourceKey,
        [string]$SourceRoot,
        [System.IO.FileInfo]$File,
        [string]$RelativePath,
        [string]$ArchiveZip
    )
    return [pscustomobject]@{
        source_key = $SourceKey
        source_root = $SourceRoot
        original_full_path = $File.FullName
        relative_path = $RelativePath
        size_bytes = [int64]$File.Length
        last_write_utc = $File.LastWriteTimeUtc.ToString("o")
        sha256 = (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        archive_zip = $ArchiveZip
    }
}

function Archive-Directory {
    param([string]$SourcePath, [string]$Label)
    $sourceFull = Get-CanonicalPath $SourcePath
    $files = Get-FilesRecursive $sourceFull
    if ($files.Count -eq 0) {
        return [pscustomobject]@{
            status = "SKIPPED_EMPTY"; label = $Label; source_path = $sourceFull
            archive_zip = $null; archive_sha256 = $null; file_count = 0
            total_bytes = 0; verified = $false; removed = $false
            manifest_rows = @(); file_group = $false; original_files = @()
        }
    }

    $pathHash = Get-ShortHash $sourceFull
    $safeLabel = Get-SafeName $Label
    $zipPath = Join-Path $SessionRoot ("{0}_{1}_{2}.zip" -f $safeLabel, $pathHash, $SessionId)
    $sourceKey = "{0}_{1}" -f $safeLabel, $pathHash

    Write-Host ""
    Write-Host "[ARCHIVE DIRECTORY] $sourceFull" -ForegroundColor Cyan
    Write-Host "  ファイル数: $($files.Count)"

    $rows = @()
    foreach ($file in $files) {
        $relative = Get-RelativePathCompat -BasePath $sourceFull -TargetPath $file.FullName
        $rows += New-ManifestRow -SourceKey $sourceKey -SourceRoot $sourceFull -File $file -RelativePath $relative -ArchiveZip $zipPath
    }

    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        $sourceFull, $zipPath, [System.IO.Compression.CompressionLevel]::Optimal, $false
    )
    Test-ZipEntryCount -ZipPath $zipPath -ExpectedCount $files.Count

    $zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $totalBytes = [int64](($files | Measure-Object -Property Length -Sum).Sum)
    Write-Host "  ZIP検証: PASS" -ForegroundColor Green
    Write-Host "  ZIP: $zipPath"

    return [pscustomobject]@{
        status = "ARCHIVED_VERIFIED"; label = $Label; source_path = $sourceFull
        archive_zip = $zipPath; archive_sha256 = $zipHash; file_count = $files.Count
        total_bytes = $totalBytes; verified = $true; removed = $false
        manifest_rows = @($rows); file_group = $false; original_files = @()
    }
}

function Archive-FileGroup {
    param([System.IO.FileInfo[]]$Files, [string]$Label, [string]$GroupRoot)
    if ($Files.Count -eq 0) { return $null }

    $rootFull = Get-CanonicalPath $GroupRoot
    $pathHash = Get-ShortHash $rootFull
    $safeLabel = Get-SafeName $Label
    $stageDir = Join-Path $StagingRoot ("{0}_{1}" -f $safeLabel, $pathHash)
    New-Item -ItemType Directory -Path $stageDir -Force | Out-Null

    foreach ($file in $Files) {
        Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $stageDir $file.Name) -Force
    }

    $stagedFiles = Get-FilesRecursive $stageDir
    $zipPath = Join-Path $SessionRoot ("{0}_{1}_{2}.zip" -f $safeLabel, $pathHash, $SessionId)
    $sourceKey = "{0}_{1}" -f $safeLabel, $pathHash

    Write-Host ""
    Write-Host "[ARCHIVE FILE GROUP] $Label" -ForegroundColor Cyan
    Write-Host "  元フォルダ: $rootFull"
    Write-Host "  ファイル数: $($Files.Count)"

    $rows = @()
    foreach ($file in $Files) {
        $rows += New-ManifestRow -SourceKey $sourceKey -SourceRoot $rootFull -File $file -RelativePath $file.Name -ArchiveZip $zipPath
    }

    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        $stageDir, $zipPath, [System.IO.Compression.CompressionLevel]::Optimal, $false
    )
    Test-ZipEntryCount -ZipPath $zipPath -ExpectedCount $stagedFiles.Count

    $zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $totalBytes = [int64](($Files | Measure-Object -Property Length -Sum).Sum)
    Write-Host "  ZIP検証: PASS" -ForegroundColor Green
    Write-Host "  ZIP: $zipPath"

    return [pscustomobject]@{
        status = "ARCHIVED_VERIFIED"; label = $Label; source_path = $rootFull
        archive_zip = $zipPath; archive_sha256 = $zipHash; file_count = $Files.Count
        total_bytes = $totalBytes; verified = $true; removed = $false
        manifest_rows = @($rows); file_group = $true; original_files = @($Files.FullName)
    }
}

Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host " GOLD_ML_V1 旧GOLDローカルアーカイブ v$ScriptVersion" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "Git管理中の旧コードは削除・移動しません。"
Write-Host "旧成果物は研究入力として解析せず、ZIP圧縮とSHA256記録だけを行います。"
Write-Host "保存先: $SessionRoot"

if (-not $NonInteractive) {
    if (-not $PSBoundParameters.ContainsKey("IncludeLegacyProjectFolders")) {
        $IncludeLegacyProjectFolders = Read-YesNo "repo外の旧プロジェクトフォルダも圧縮しますか？" $true
    }
    if (-not $PSBoundParameters.ContainsKey("IncludeRootGoldCsvs")) {
        $IncludeRootGoldCsvs = Read-YesNo "MT5 Files直下の旧ローソク足CSVもバックアップしますか？" $true
    }
}

New-Item -ItemType Directory -Path $SessionRoot -Force | Out-Null
New-Item -ItemType Directory -Path $StagingRoot -Force | Out-Null

$directoryCandidates = @()
$fileGroups = @()
$seenPaths = @{}

function Add-DirectoryCandidate {
    param([string]$Path, [string]$Label)
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return }
    $full = Get-CanonicalPath $Path
    $key = $full.ToLowerInvariant()
    if (-not $seenPaths.ContainsKey($key)) {
        $seenPaths[$key] = $true
        $script:directoryCandidates += [pscustomobject]@{ path = $full; label = $Label }
    }
}

# Git管理中の旧ソースではなく、存在する場合のローカル出力だけを対象にする。
Add-DirectoryCandidate -Path (Join-Path $RepoRoot "FX_OUTPUTS\gold_v3") -Label "repo_local_FX_OUTPUTS_gold_v3"

$mql5Roots = @()
$terminalRoot = Join-Path $env:APPDATA "MetaQuotes\Terminal"
if (Test-Path -LiteralPath $terminalRoot -PathType Container) {
    foreach ($terminal in Get-ChildItem -LiteralPath $terminalRoot -Directory -Force -ErrorAction SilentlyContinue) {
        $filesRoot = Join-Path $terminal.FullName "MQL5\Files"
        if (Test-Path -LiteralPath $filesRoot -PathType Container) {
            $mql5Roots += Get-CanonicalPath $filesRoot
            Add-DirectoryCandidate -Path (Join-Path $filesRoot "FX_OUTPUTS\gold_v3") -Label ("mt5_{0}_FX_OUTPUTS_gold_v3" -f $terminal.Name)
        }
    }
}

if ($IncludeLegacyProjectFolders) {
    $legacyNames = @("gold_ai_system", "gold_signal_system_step1", "gold_signal_system_step2", "gold_signal_system_step3")
    $searchBases = @(
        (Split-Path -Parent $RepoRoot),
        (Join-Path $env:USERPROFILE "Documents"),
        (Join-Path $env:USERPROFILE "Desktop")
    ) | Select-Object -Unique

    foreach ($base in $searchBases) {
        if (-not (Test-Path -LiteralPath $base -PathType Container)) { continue }
        foreach ($name in $legacyNames) {
            $candidate = Join-Path $base $name
            if (Test-Path -LiteralPath $candidate -PathType Container) {
                $full = Get-CanonicalPath $candidate
                if (-not (Test-IsUnderPath -Child $full -Parent $RepoRoot)) {
                    Add-DirectoryCandidate -Path $full -Label ("legacy_project_{0}" -f $name)
                }
            }
        }
    }
}

foreach ($path in $AdditionalPaths) {
    if ([string]::IsNullOrWhiteSpace($path)) { continue }
    $expanded = [Environment]::ExpandEnvironmentVariables($path)
    if (Test-Path -LiteralPath $expanded -PathType Container) {
        $full = Get-CanonicalPath $expanded
        $repoLocalOutput = Get-CanonicalPath (Join-Path $RepoRoot "FX_OUTPUTS\gold_v3")
        if ((Test-IsUnderPath -Child $full -Parent $RepoRoot) -and -not $full.Equals($repoLocalOutput, [System.StringComparison]::OrdinalIgnoreCase)) {
            Write-Warning "Git作業ツリー内の追加パスは除外しました: $full"
        }
        else {
            Add-DirectoryCandidate -Path $full -Label "additional_legacy_path"
        }
    }
    elseif (Test-Path -LiteralPath $expanded -PathType Leaf) {
        $file = Get-Item -LiteralPath $expanded -Force
        $fileGroups += [pscustomobject]@{ label = "additional_legacy_files"; root = $file.DirectoryName; files = @($file) }
    }
    else {
        Write-Warning "追加パスが見つかりません: $expanded"
    }
}

if ($IncludeRootGoldCsvs) {
    $rootCsvNames = @(
        "goldsharp_m1.csv", "goldsharp_m5.csv", "goldsharp_m15.csv",
        "goldsharp_h1.csv", "goldsharp_h4.csv", "goldsharp_d1.csv",
        "candles_history_M1.csv", "candles_history_M5.csv", "candles_history_M15.csv",
        "candles_history_H1.csv", "candles_history_H4.csv", "candles_history_D1.csv",
        "M5_backtest.csv"
    )
    foreach ($root in $mql5Roots) {
        $files = @()
        foreach ($name in $rootCsvNames) {
            $candidate = Join-Path $root $name
            if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                $files += Get-Item -LiteralPath $candidate -Force
            }
        }
        if ($files.Count -gt 0) {
            $terminalId = Split-Path -Leaf (Split-Path -Parent (Split-Path -Parent $root))
            $fileGroups += [pscustomobject]@{
                label = ("mt5_{0}_legacy_root_gold_csvs" -f $terminalId)
                root = $root
                files = @($files)
            }
        }
    }
}

Write-Host ""
Write-Host "検出された旧ディレクトリ: $($directoryCandidates.Count)" -ForegroundColor White
foreach ($item in $directoryCandidates) { Write-Host "  - $($item.path)" }
Write-Host "検出された旧CSVグループ: $($fileGroups.Count)" -ForegroundColor White
foreach ($group in $fileGroups) { Write-Host "  - $($group.label): $(@($group.files).Count) files" }

if ($directoryCandidates.Count -eq 0 -and $fileGroups.Count -eq 0) {
    [ordered]@{
        script_version = $ScriptVersion
        session_id = $SessionId
        status = "NO_LEGACY_LOCAL_ARTIFACTS_FOUND"
        repository_root = $RepoRoot
        archive_root = $SessionRoot
        timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $SessionRoot "archive_session.json") -Encoding UTF8
    Remove-Item -LiteralPath $StagingRoot -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "対象が見つかりませんでした。Git管理中の旧コードには何もしていません。" -ForegroundColor Yellow
    exit 0
}

if (-not $NonInteractive -and -not (Read-YesNo "上記をZIP化しますか？" $true)) {
    Remove-Item -LiteralPath $SessionRoot -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "キャンセルしました。元ファイルは変更していません。" -ForegroundColor Yellow
    exit 0
}

$results = @()
$manifestRows = @()
$errors = @()

foreach ($item in $directoryCandidates) {
    try {
        $result = Archive-Directory -SourcePath $item.path -Label $item.label
        $results += $result
        $manifestRows += @($result.manifest_rows)
    }
    catch {
        $errors += [pscustomobject]@{ label = $item.label; source_path = $item.path; error = $_.Exception.Message }
        Write-Host "[ERROR] $($item.path): $($_.Exception.Message)" -ForegroundColor Red
    }
}

foreach ($group in $fileGroups) {
    try {
        $result = Archive-FileGroup -Files @($group.files) -Label $group.label -GroupRoot $group.root
        if ($null -ne $result) {
            $results += $result
            $manifestRows += @($result.manifest_rows)
        }
    }
    catch {
        $errors += [pscustomobject]@{ label = $group.label; source_path = $group.root; error = $_.Exception.Message }
        Write-Host "[ERROR] $($group.root): $($_.Exception.Message)" -ForegroundColor Red
    }
}

$verifiedDirectories = @($results | Where-Object { $_.verified -and -not $_.file_group })
$verifiedFileGroups = @($results | Where-Object { $_.verified -and $_.file_group })

if (-not $NonInteractive -and $verifiedDirectories.Count -gt 0 -and -not $PSBoundParameters.ContainsKey("RemoveOriginals")) {
    Write-Host ""
    foreach ($result in $verifiedDirectories) { Write-Host "  - $($result.source_path)" }
    $RemoveOriginals = Read-YesNo "ZIP検証済みの上記元フォルダを削除して容量を空けますか？" $false
}

if (-not $NonInteractive -and $verifiedFileGroups.Count -gt 0 -and -not $PSBoundParameters.ContainsKey("RemoveRootGoldCsvs")) {
    Write-Host "旧ローソク足CSVは非常用バックアップとして残すことを推奨します。" -ForegroundColor Yellow
    $RemoveRootGoldCsvs = Read-YesNo "ZIP検証済みの元CSVも削除しますか？" $false
}

if ($RemoveOriginals) {
    foreach ($result in $verifiedDirectories) {
        try {
            if (Test-Path -LiteralPath $result.source_path -PathType Container) {
                Remove-Item -LiteralPath $result.source_path -Recurse -Force
            }
            $result.removed = $true
            Write-Host "[REMOVED] $($result.source_path)" -ForegroundColor DarkYellow
        }
        catch {
            $errors += [pscustomobject]@{ label = $result.label; source_path = $result.source_path; error = "REMOVE_FAILED: $($_.Exception.Message)" }
        }
    }
}

if ($RemoveRootGoldCsvs) {
    foreach ($result in $verifiedFileGroups) {
        $allRemoved = $true
        foreach ($filePath in $result.original_files) {
            try {
                if (Test-Path -LiteralPath $filePath -PathType Leaf) { Remove-Item -LiteralPath $filePath -Force }
                Write-Host "[REMOVED CSV] $filePath" -ForegroundColor DarkYellow
            }
            catch {
                $allRemoved = $false
                $errors += [pscustomobject]@{ label = $result.label; source_path = $filePath; error = "REMOVE_FILE_FAILED: $($_.Exception.Message)" }
            }
        }
        $result.removed = $allRemoved
    }
}

$manifestPath = Join-Path $SessionRoot "file_manifest.csv"
if ($manifestRows.Count -gt 0) {
    $manifestRows | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding UTF8
}
else {
    "source_key,source_root,original_full_path,relative_path,size_bytes,last_write_utc,sha256,archive_zip" | Set-Content -LiteralPath $manifestPath -Encoding UTF8
}

$summaryResults = @($results | ForEach-Object {
    [ordered]@{
        status = $_.status; label = $_.label; source_path = $_.source_path
        archive_zip = $_.archive_zip; archive_sha256 = $_.archive_sha256
        file_count = $_.file_count; total_bytes = $_.total_bytes
        verified = $_.verified; removed = $_.removed; file_group = $_.file_group
    }
})

$status = if ($errors.Count -eq 0) { "ARCHIVE_COMPLETE" } else { "ARCHIVE_COMPLETE_WITH_ERRORS" }
$sessionJsonPath = Join-Path $SessionRoot "archive_session.json"
[ordered]@{
    script_version = $ScriptVersion
    session_id = $SessionId
    status = $status
    repository_root = $RepoRoot
    archive_root = $SessionRoot
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
    operation = "OPAQUE_COMPRESSION_AND_SHA256_ONLY"
    git_tracked_old_source_modified = $false
    old_content_used_for_research = $false
    results = $summaryResults
    errors = @($errors)
    manifest_csv = $manifestPath
} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $sessionJsonPath -Encoding UTF8

@"
GOLD_ML_V1 legacy local archive
Session: $SessionId
Status: $status

Opaque compression and SHA256 recording only.
Archived old content was not parsed or used as GOLD_ML_V1 research input.
Git-tracked old source files were not removed or modified.

Manifest: $manifestPath
Session report: $sessionJsonPath
"@ | Set-Content -LiteralPath (Join-Path $SessionRoot "README.txt") -Encoding UTF8

Remove-Item -LiteralPath $StagingRoot -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "完了: $status" -ForegroundColor Green
Write-Host "保存先: $SessionRoot"
Write-Host "マニフェスト: $manifestPath"
Write-Host "実行記録: $sessionJsonPath"
if ($errors.Count -gt 0) {
    Write-Host "一部エラーがあります。エラー対象の元ファイルは削除されていません。" -ForegroundColor Yellow
}
Write-Host "============================================================" -ForegroundColor DarkCyan
