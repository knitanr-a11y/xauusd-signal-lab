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

$ScriptVersion = "1.0.0"
$SessionId = Get-Date -Format "yyyyMMdd_HHmmss"
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.."))
$ArchiveRoot = [System.IO.Path]::GetFullPath($ArchiveRoot)
$SessionRoot = Join-Path $ArchiveRoot ("GOLD_OLD_ARCHIVE_" + $SessionId)
$StagingRoot = Join-Path $SessionRoot "_staging"

function Read-YesNo {
    param(
        [Parameter(Mandatory = $true)][string]$Prompt,
        [bool]$Default = $false
    )

    if ($NonInteractive) {
        return $Default
    }

    $suffix = if ($Default) { "[Y/n]" } else { "[y/N]" }
    while ($true) {
        $answer = (Read-Host "$Prompt $suffix").Trim().ToLowerInvariant()
        if ([string]::IsNullOrWhiteSpace($answer)) {
            return $Default
        }
        if ($answer -in @("y", "yes")) {
            return $true
        }
        if ($answer -in @("n", "no")) {
            return $false
        }
        Write-Host "Y または N を入力してください。" -ForegroundColor Yellow
    }
}

function Get-CanonicalPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
}

function Test-IsUnderPath {
    param(
        [Parameter(Mandatory = $true)][string]$Child,
        [Parameter(Mandatory = $true)][string]$Parent
    )

    $childPath = (Get-CanonicalPath $Child) + [System.IO.Path]::DirectorySeparatorChar
    $parentPath = (Get-CanonicalPath $Parent) + [System.IO.Path]::DirectorySeparatorChar
    return $childPath.StartsWith($parentPath, [System.StringComparison]::OrdinalIgnoreCase)
}

function Get-ShortPathHash {
    param([Parameter(Mandatory = $true)][string]$Text)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        $hash = $sha.ComputeHash($bytes)
        return ([System.BitConverter]::ToString($hash).Replace("-", "").ToLowerInvariant()).Substring(0, 10)
    }
    finally {
        $sha.Dispose()
    }
}

function Convert-ToSafeName {
    param([Parameter(Mandatory = $true)][string]$Text)
    $safe = $Text -replace '[^A-Za-z0-9._-]', '_'
    $safe = $safe.Trim('_')
    if ([string]::IsNullOrWhiteSpace($safe)) {
        return "archive"
    }
    if ($safe.Length -gt 80) {
        $safe = $safe.Substring(0, 80)
    }
    return $safe
}

function Get-DirectoryFiles {
    param([Parameter(Mandatory = $true)][string]$SourcePath)
    return @(Get-ChildItem -LiteralPath $SourcePath -File -Recurse -Force -ErrorAction Stop | Sort-Object FullName)
}

function Get-FileManifestRows {
    param(
        [Parameter(Mandatory = $true)][string]$SourceKey,
        [Parameter(Mandatory = $true)][string]$SourceRoot,
        [Parameter(Mandatory = $true)][System.IO.FileInfo[]]$Files,
        [Parameter(Mandatory = $true)][string]$ArchiveZip
    )

    $rows = New-Object System.Collections.Generic.List[object]
    foreach ($file in $Files) {
        $relative = [System.IO.Path]::GetRelativePath($SourceRoot, $file.FullName)
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $rows.Add([pscustomobject]@{
            source_key        = $SourceKey
            source_root       = $SourceRoot
            original_full_path = $file.FullName
            relative_path     = $relative
            size_bytes        = [int64]$file.Length
            last_write_utc    = $file.LastWriteTimeUtc.ToString("o")
            sha256            = $hash
            archive_zip       = $ArchiveZip
        })
    }
    return @($rows)
}

function New-VerifiedDirectoryZip {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$Label
    )

    $sourceFull = Get-CanonicalPath $SourcePath
    $files = Get-DirectoryFiles $sourceFull
    if ($files.Count -eq 0) {
        return [pscustomobject]@{
            status = "SKIPPED_EMPTY"
            label = $Label
            source_path = $sourceFull
            archive_zip = $null
            archive_sha256 = $null
            file_count = 0
            total_bytes = 0
            manifest_rows = @()
            verified = $false
            removed = $false
        }
    }

    $pathHash = Get-ShortPathHash $sourceFull
    $zipName = "{0}_{1}_{2}.zip" -f (Convert-ToSafeName $Label), $pathHash, $SessionId
    $zipPath = Join-Path $SessionRoot $zipName
    $sourceKey = "{0}_{1}" -f (Convert-ToSafeName $Label), $pathHash

    Write-Host ""
    Write-Host "[ARCHIVE] $sourceFull" -ForegroundColor Cyan
    Write-Host "  ファイル数: $($files.Count)"

    $manifestRows = Get-FileManifestRows -SourceKey $sourceKey -SourceRoot $sourceFull -Files $files -ArchiveZip $zipPath
    $totalBytes = [int64](($files | Measure-Object -Property Length -Sum).Sum)

    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }

    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        $sourceFull,
        $zipPath,
        [System.IO.Compression.CompressionLevel]::Optimal,
        $false
    )

    $zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
    try {
        $entryCount = @($zip.Entries | Where-Object { -not [string]::IsNullOrEmpty($_.Name) }).Count
    }
    finally {
        $zip.Dispose()
    }

    if ($entryCount -ne $files.Count) {
        throw "ZIP_ENTRY_COUNT_MISMATCH: source=$sourceFull expected=$($files.Count) actual=$entryCount"
    }

    $zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Host "  ZIP検証: PASS" -ForegroundColor Green
    Write-Host "  ZIP: $zipPath"
    Write-Host "  SHA256: $zipHash"

    return [pscustomobject]@{
        status = "ARCHIVED_VERIFIED"
        label = $Label
        source_path = $sourceFull
        archive_zip = $zipPath
        archive_sha256 = $zipHash
        file_count = $files.Count
        total_bytes = $totalBytes
        manifest_rows = $manifestRows
        verified = $true
        removed = $false
    }
}

function New-VerifiedFileGroupZip {
    param(
        [Parameter(Mandatory = $true)][System.IO.FileInfo[]]$Files,
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$GroupRoot
    )

    if ($Files.Count -eq 0) {
        return $null
    }

    $rootFull = Get-CanonicalPath $GroupRoot
    $pathHash = Get-ShortPathHash $rootFull
    $safeLabel = Convert-ToSafeName $Label
    $stageDir = Join-Path $StagingRoot ("{0}_{1}" -f $safeLabel, $pathHash)
    New-Item -ItemType Directory -Path $stageDir -Force | Out-Null

    $seenNames = @{}
    foreach ($file in $Files) {
        $targetName = $file.Name
        if ($seenNames.ContainsKey($targetName)) {
            $targetName = "{0}_{1}{2}" -f $file.BaseName, (Get-ShortPathHash $file.FullName), $file.Extension
        }
        $seenNames[$targetName] = $true
        Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $stageDir $targetName) -Force
    }

    $stagedFiles = Get-DirectoryFiles $stageDir
    $zipName = "{0}_{1}_{2}.zip" -f $safeLabel, $pathHash, $SessionId
    $zipPath = Join-Path $SessionRoot $zipName
    $sourceKey = "{0}_{1}" -f $safeLabel, $pathHash

    Write-Host ""
    Write-Host "[ARCHIVE] $Label" -ForegroundColor Cyan
    Write-Host "  元フォルダ: $rootFull"
    Write-Host "  ファイル数: $($Files.Count)"

    $rows = New-Object System.Collections.Generic.List[object]
    foreach ($file in $Files) {
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $rows.Add([pscustomobject]@{
            source_key        = $sourceKey
            source_root       = $rootFull
            original_full_path = $file.FullName
            relative_path     = $file.Name
            size_bytes        = [int64]$file.Length
            last_write_utc    = $file.LastWriteTimeUtc.ToString("o")
            sha256            = $hash
            archive_zip       = $zipPath
        })
    }

    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        $stageDir,
        $zipPath,
        [System.IO.Compression.CompressionLevel]::Optimal,
        $false
    )

    $zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
    try {
        $entryCount = @($zip.Entries | Where-Object { -not [string]::IsNullOrEmpty($_.Name) }).Count
    }
    finally {
        $zip.Dispose()
    }

    if ($entryCount -ne $stagedFiles.Count) {
        throw "ZIP_ENTRY_COUNT_MISMATCH: group=$Label expected=$($stagedFiles.Count) actual=$entryCount"
    }

    $zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $totalBytes = [int64](($Files | Measure-Object -Property Length -Sum).Sum)
    Write-Host "  ZIP検証: PASS" -ForegroundColor Green
    Write-Host "  ZIP: $zipPath"
    Write-Host "  SHA256: $zipHash"

    return [pscustomobject]@{
        status = "ARCHIVED_VERIFIED"
        label = $Label
        source_path = $rootFull
        archive_zip = $zipPath
        archive_sha256 = $zipHash
        file_count = $Files.Count
        total_bytes = $totalBytes
        manifest_rows = @($rows)
        original_files = @($Files.FullName)
        verified = $true
        removed = $false
        file_group = $true
    }
}

Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host " GOLD_ML_V1 旧GOLDローカルアーカイブ" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "Git管理中の旧コードは削除・移動しません。"
Write-Host "旧ファイルの内容を研究用途では読みません。圧縮とSHA記録だけを行います。"
Write-Host "保存先: $SessionRoot"

if (-not $NonInteractive) {
    if (-not $PSBoundParameters.ContainsKey("IncludeLegacyProjectFolders")) {
        $IncludeLegacyProjectFolders = Read-YesNo "repo外の旧プロジェクトフォルダも検出して圧縮しますか？" $true
    }
    if (-not $PSBoundParameters.ContainsKey("IncludeRootGoldCsvs")) {
        $IncludeRootGoldCsvs = Read-YesNo "MT5 Files直下の旧goldsharpローソク足CSVもバックアップしますか？" $true
    }
}

New-Item -ItemType Directory -Path $SessionRoot -Force | Out-Null
New-Item -ItemType Directory -Path $StagingRoot -Force | Out-Null

$directoryCandidates = New-Object System.Collections.Generic.List[object]
$rawGroups = New-Object System.Collections.Generic.List[object]
$seen = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)

function Add-DirectoryCandidate {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        return
    }
    $full = Get-CanonicalPath $Path
    if ($full.StartsWith((Get-CanonicalPath $SessionRoot), [System.StringComparison]::OrdinalIgnoreCase)) {
        return
    }
    if ($seen.Add($full)) {
        $directoryCandidates.Add([pscustomobject]@{ path = $full; label = $Label })
    }
}

# Repo内にローカル出力が存在する場合だけ対象。Git管理中の旧コードは対象外。
Add-DirectoryCandidate -Path (Join-Path $RepoRoot "FX_OUTPUTS\gold_v3") -Label "repo_local_FX_OUTPUTS_gold_v3"

$mql5Roots = New-Object System.Collections.Generic.List[string]
$terminalRoot = Join-Path $env:APPDATA "MetaQuotes\Terminal"
if (Test-Path -LiteralPath $terminalRoot -PathType Container) {
    foreach ($terminal in Get-ChildItem -LiteralPath $terminalRoot -Directory -Force -ErrorAction SilentlyContinue) {
        $filesRoot = Join-Path $terminal.FullName "MQL5\Files"
        if (Test-Path -LiteralPath $filesRoot -PathType Container) {
            $mql5Roots.Add((Get-CanonicalPath $filesRoot))
            Add-DirectoryCandidate -Path (Join-Path $filesRoot "FX_OUTPUTS\gold_v3") -Label ("mt5_{0}_FX_OUTPUTS_gold_v3" -f $terminal.Name)
        }
    }
}

if ($IncludeLegacyProjectFolders) {
    $legacyNames = @(
        "gold_ai_system",
        "gold_signal_system_step1",
        "gold_signal_system_step2",
        "gold_signal_system_step3"
    )
    $searchBases = @(
        (Split-Path -Parent $RepoRoot),
        (Join-Path $env:USERPROFILE "Documents"),
        (Join-Path $env:USERPROFILE "Desktop")
    ) | Select-Object -Unique

    foreach ($base in $searchBases) {
        if (-not (Test-Path -LiteralPath $base -PathType Container)) {
            continue
        }
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
    if ([string]::IsNullOrWhiteSpace($path)) {
        continue
    }
    $expanded = [Environment]::ExpandEnvironmentVariables($path)
    if (Test-Path -LiteralPath $expanded -PathType Container) {
        $full = Get-CanonicalPath $expanded
        if (Test-IsUnderPath -Child $full -Parent $RepoRoot) {
            $allowedRepoLocalOutput = Get-CanonicalPath (Join-Path $RepoRoot "FX_OUTPUTS\gold_v3")
            if (-not $full.Equals($allowedRepoLocalOutput, [System.StringComparison]::OrdinalIgnoreCase)) {
                Write-Warning "Git作業ツリー内の追加パスは安全のため除外しました: $full"
                continue
            }
        }
        Add-DirectoryCandidate -Path $full -Label "additional_legacy_path"
    }
    elseif (Test-Path -LiteralPath $expanded -PathType Leaf) {
        $file = Get-Item -LiteralPath $expanded -Force
        $rawGroups.Add([pscustomobject]@{
            label = "additional_legacy_files"
            root = $file.DirectoryName
            files = @($file)
        })
    }
    else {
        Write-Warning "追加パスが見つかりません: $expanded"
    }
}

if ($IncludeRootGoldCsvs) {
    $rootCsvPatterns = @(
        "goldsharp_m1.csv",
        "goldsharp_m5.csv",
        "goldsharp_m15.csv",
        "goldsharp_h1.csv",
        "goldsharp_h4.csv",
        "goldsharp_d1.csv",
        "candles_history_M1.csv",
        "candles_history_M5.csv",
        "candles_history_M15.csv",
        "candles_history_H1.csv",
        "candles_history_H4.csv",
        "candles_history_D1.csv",
        "M5_backtest.csv"
    )

    foreach ($root in $mql5Roots) {
        $files = New-Object System.Collections.Generic.List[System.IO.FileInfo]
        foreach ($name in $rootCsvPatterns) {
            $path = Join-Path $root $name
            if (Test-Path -LiteralPath $path -PathType Leaf) {
                $files.Add((Get-Item -LiteralPath $path -Force))
            }
        }
        if ($files.Count -gt 0) {
            $terminalName = Split-Path -Leaf (Split-Path -Parent (Split-Path -Parent $root))
            $rawGroups.Add([pscustomobject]@{
                label = ("mt5_{0}_legacy_root_gold_csvs" -f $terminalName)
                root = $root
                files = @($files)
            })
        }
    }
}

Write-Host ""
Write-Host "検出された旧ディレクトリ: $($directoryCandidates.Count)" -ForegroundColor White
foreach ($item in $directoryCandidates) {
    Write-Host "  - $($item.path)"
}
Write-Host "検出された旧CSVグループ: $($rawGroups.Count)" -ForegroundColor White
foreach ($group in $rawGroups) {
    Write-Host "  - $($group.label): $(@($group.files).Count) files"
}

if ($directoryCandidates.Count -eq 0 -and $rawGroups.Count -eq 0) {
    $emptyResult = [ordered]@{
        script_version = $ScriptVersion
        session_id = $SessionId
        status = "NO_LEGACY_LOCAL_ARTIFACTS_FOUND"
        repository_root = $RepoRoot
        archive_root = $SessionRoot
        timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
    }
    $emptyResult | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $SessionRoot "archive_session.json") -Encoding UTF8
    Remove-Item -LiteralPath $StagingRoot -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "対象が見つかりませんでした。Git管理中の旧コードには何もしていません。" -ForegroundColor Yellow
    exit 0
}

if (-not $NonInteractive) {
    $continue = Read-YesNo "上記をZIP化しますか？" $true
    if (-not $continue) {
        Write-Host "キャンセルしました。元ファイルは変更していません。" -ForegroundColor Yellow
        Remove-Item -LiteralPath $SessionRoot -Recurse -Force -ErrorAction SilentlyContinue
        exit 0
    }
}

$results = New-Object System.Collections.Generic.List[object]
$allManifestRows = New-Object System.Collections.Generic.List[object]
$errors = New-Object System.Collections.Generic.List[object]

foreach ($item in $directoryCandidates) {
    try {
        $result = New-VerifiedDirectoryZip -SourcePath $item.path -Label $item.label
        $results.Add($result)
        foreach ($row in @($result.manifest_rows)) {
            $allManifestRows.Add($row)
        }
    }
    catch {
        $errors.Add([pscustomobject]@{
            label = $item.label
            source_path = $item.path
            error = $_.Exception.Message
        })
        Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
    }
}

foreach ($group in $rawGroups) {
    try {
        $result = New-VerifiedFileGroupZip -Files @($group.files) -Label $group.label -GroupRoot $group.root
        if ($null -ne $result) {
            $results.Add($result)
            foreach ($row in @($result.manifest_rows)) {
                $allManifestRows.Add($row)
            }
        }
    }
    catch {
        $errors.Add([pscustomobject]@{
            label = $group.label
            source_path = $group.root
            error = $_.Exception.Message
        })
        Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
    }
}

$verifiedDirectoryResults = @($results | Where-Object { $_.verified -eq $true -and -not ($_.PSObject.Properties.Name -contains "file_group") })
$verifiedFileGroupResults = @($results | Where-Object { $_.verified -eq $true -and ($_.PSObject.Properties.Name -contains "file_group") })

if (-not $NonInteractive -and $verifiedDirectoryResults.Count -gt 0 -and -not $PSBoundParameters.ContainsKey("RemoveOriginals")) {
    Write-Host ""
    Write-Host "ZIP検証済みの旧出力・旧プロジェクトフォルダ:" -ForegroundColor White
    foreach ($result in $verifiedDirectoryResults) {
        Write-Host "  - $($result.source_path)"
    }
    $RemoveOriginals = Read-YesNo "上記の元フォルダを削除して容量を空けますか？" $false
}

if (-not $NonInteractive -and $verifiedFileGroupResults.Count -gt 0 -and -not $PSBoundParameters.ContainsKey("RemoveRootGoldCsvs")) {
    Write-Host ""
    Write-Host "旧ローソク足CSVは非常用バックアップとして残すことを推奨します。" -ForegroundColor Yellow
    $RemoveRootGoldCsvs = Read-YesNo "ZIP検証済みの元CSVも削除しますか？" $false
}

if ($RemoveOriginals) {
    foreach ($result in $verifiedDirectoryResults) {
        try {
            if (Test-Path -LiteralPath $result.source_path -PathType Container) {
                Remove-Item -LiteralPath $result.source_path -Recurse -Force -ErrorAction Stop
            }
            $result.removed = $true
            Write-Host "[REMOVED] $($result.source_path)" -ForegroundColor DarkYellow
        }
        catch {
            $errors.Add([pscustomobject]@{
                label = $result.label
                source_path = $result.source_path
                error = "REMOVE_FAILED: $($_.Exception.Message)"
            })
            Write-Host "[REMOVE ERROR] $($result.source_path): $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

if ($RemoveRootGoldCsvs) {
    foreach ($result in $verifiedFileGroupResults) {
        foreach ($filePath in @($result.original_files)) {
            try {
                if (Test-Path -LiteralPath $filePath -PathType Leaf) {
                    Remove-Item -LiteralPath $filePath -Force -ErrorAction Stop
                }
                Write-Host "[REMOVED CSV] $filePath" -ForegroundColor DarkYellow
            }
            catch {
                $errors.Add([pscustomobject]@{
                    label = $result.label
                    source_path = $filePath
                    error = "REMOVE_FILE_FAILED: $($_.Exception.Message)"
                })
                Write-Host "[REMOVE CSV ERROR] $filePath: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
        $result.removed = $true
    }
}

$manifestPath = Join-Path $SessionRoot "file_manifest.csv"
if ($allManifestRows.Count -gt 0) {
    @($allManifestRows) | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding UTF8
}
else {
    "source_key,source_root,original_full_path,relative_path,size_bytes,last_write_utc,sha256,archive_zip" | Set-Content -LiteralPath $manifestPath -Encoding UTF8
}

$summaryResults = @($results | ForEach-Object {
    [ordered]@{
        status = $_.status
        label = $_.label
        source_path = $_.source_path
        archive_zip = $_.archive_zip
        archive_sha256 = $_.archive_sha256
        file_count = $_.file_count
        total_bytes = $_.total_bytes
        verified = $_.verified
        removed = $_.removed
    }
})

$sessionStatus = if ($errors.Count -eq 0) { "ARCHIVE_COMPLETE" } else { "ARCHIVE_COMPLETE_WITH_ERRORS" }
$sessionPayload = [ordered]@{
    script_version = $ScriptVersion
    session_id = $SessionId
    status = $sessionStatus
    repository_root = $RepoRoot
    archive_root = $SessionRoot
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
    git_tracked_old_source_modified = $false
    old_content_used_for_research = $false
    operation = "OPAQUE_COMPRESSION_AND_SHA256_ONLY"
    results = $summaryResults
    errors = @($errors)
    manifest_csv = $manifestPath
}
$sessionJsonPath = Join-Path $SessionRoot "archive_session.json"
$sessionPayload | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $sessionJsonPath -Encoding UTF8

$readme = @"
GOLD_ML_V1 legacy local archive
Session: $SessionId
Status: $sessionStatus

This archive was created by opaque byte-level compression and SHA256 recording only.
The archived old content was not parsed or used as GOLD_ML_V1 research input.
Git-tracked old source files were not removed or modified.

Manifest:
$manifestPath

Session report:
$sessionJsonPath
"@
$readme | Set-Content -LiteralPath (Join-Path $SessionRoot "README.txt") -Encoding UTF8

Remove-Item -LiteralPath $StagingRoot -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "完了: $sessionStatus" -ForegroundColor Green
Write-Host "保存先: $SessionRoot"
Write-Host "マニフェスト: $manifestPath"
Write-Host "実行記録: $sessionJsonPath"
if ($errors.Count -gt 0) {
    Write-Host "一部エラーがあります。実行記録を確認してください。エラー対象の元ファイルは削除されていません。" -ForegroundColor Yellow
}
Write-Host "============================================================" -ForegroundColor DarkCyan
