# Verify every staged file is present in the backup with identical length, then purge.
$backup = Join-Path $env:USERPROFILE 'openmd_backup_20260205'
$stage  = Join-Path $env:USERPROFILE 'openmd_gc_staging'
$manifest = Join-Path $stage '_restore_manifest.csv'

$rows = Import-Csv -LiteralPath $manifest
Write-Output ("manifest rows: {0}" -f $rows.Count)

$missing = 0; $sizemismatch = 0; $checked = 0; $badBytes = 0
foreach ($r in $rows) {
    $src = Join-Path $backup $r.rel
    if (-not (Test-Path -LiteralPath $src -PathType Leaf)) {
        $missing++
        if ($missing -le 10) { Write-Output ("  MISSING in backup: {0}" -f $r.rel) }
        continue
    }
    $len = (Get-Item -LiteralPath $src).Length
    if ($len -ne [int64]$r.bytes) {
        $sizemismatch++
        if ($sizemismatch -le 10) { Write-Output ("  SIZE DIFF: {0} backup={1} manifest={2}" -f $r.rel, $len, $r.bytes) }
    } else { $checked++ }
    $badBytes += [int64]$r.bytes
}
Write-Output ""
Write-Output ("checked-ok={0}  missing={1}  size-mismatch={2}" -f $checked, $missing, $sizemismatch)
Write-Output ("staged bytes covered by backup: {0:n2} MB" -f ($badBytes / 1MB))

if ($missing -eq 0 -and $sizemismatch -eq 0) {
    Write-Output ""
    Write-Output "ALL STAGED FILES ARE RECOVERABLE FROM THE BACKUP -> purging staging"
    Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction Stop
    if (Test-Path -LiteralPath $stage) {
        Write-Output "PURGE FAILED - staging still present"
    } else {
        Write-Output "PURGE OK - staging removed"
    }
} else {
    Write-Output ""
    Write-Output "ABORTING PURGE: backup does not fully cover staging"
}
