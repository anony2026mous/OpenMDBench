# Stage open-source cleanup targets into a quarantine folder (MOVE, not delete).
# Keeps all theta_*.npz weights. Writes a restore manifest.
$root = 'C:\Code\source-code\openmd'
$sub  = Join-Path $root 'source-code\source_codes'
$eval = Join-Path $root 'code\eval'
$runs = Join-Path $eval '_w1_runs'
# NOTE: do not hardcode the user name here. This script file is UTF-8 but is
# read as GBK by the host, which mangles non-ASCII characters in literals.
# USERPROFILE is resolved by the shell and survives intact.
$stage = Join-Path $env:USERPROFILE 'openmd_gc_staging'

New-Item -ItemType Directory -Force -Path $stage -ErrorAction Stop | Out-Null
if (-not (Test-Path -LiteralPath $stage -PathType Container)) {
    throw "staging root was not created: $stage"
}
$probe = Join-Path $stage '.write_probe'
Set-Content -LiteralPath $probe -Value 'ok' -ErrorAction Stop
Remove-Item -LiteralPath $probe -Force
Write-Output "staging root OK: $stage"
Write-Output ("root char codes: " + (( $stage.ToCharArray() | ForEach-Object { [int]$_ } ) -join ','))
$rows = New-Object System.Collections.ArrayList

function Stage-Items {
    param([string]$Group, $Items)
    $n = 0; $bytes = 0
    foreach ($src in $Items) {
        if (-not $src) { continue }
        if (-not (Test-Path -LiteralPath $src -PathType Leaf)) { continue }
        $full = (Resolve-Path -LiteralPath $src).Path
        if ($full -notlike "$root\*") { Write-Output "  SKIP (outside repo): $full"; continue }
        $rel  = $full.Substring($root.Length + 1)
        $dst  = Join-Path $stage $rel
        $dir  = Split-Path $dst -Parent
        if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir -ErrorAction Stop | Out-Null }
        $len = (Get-Item -LiteralPath $full).Length
        try {
            Move-Item -LiteralPath $full -Destination $dst -Force -ErrorAction Stop
            $n++; $bytes += $len
            [void]$rows.Add([pscustomobject]@{ group = $Group; rel = $rel; bytes = $len })
        } catch {
            Write-Output ("  FAIL {0}: {1}" -f $rel, $_.Exception.Message)
        }
    }
    '{0,-42} {1,5} files {2,12:n2} MB' -f $Group, $n, ($bytes / 1MB)
}

Write-Output "staging root: $stage"
Write-Output ""

# A1 engine caches
$a1 = Get-ChildItem $sub -Recurse -Directory -Force -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -in @('__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.ipynb_checkpoints') } |
      ForEach-Object { Get-ChildItem $_.FullName -Recurse -File -Force -ErrorAction SilentlyContinue } |
      Select-Object -ExpandProperty FullName
Stage-Items 'A1 engine __pycache__/.pytest_cache' $a1

# A2 eval caches
$a2 = Get-ChildItem $eval -Recurse -Directory -Force -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -in @('__pycache__', '.pytest_cache') } |
      ForEach-Object { Get-ChildItem $_.FullName -Recurse -File -Force -ErrorAction SilentlyContinue } |
      Select-Object -ExpandProperty FullName
Stage-Items 'A2 code/eval __pycache__' $a2

# B1 *.bak
$b1 = @()
$b1 += Get-ChildItem $eval -File -Filter '*.bak' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
$b1 += Get-ChildItem $runs -File -Filter '*.bak' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
Stage-Items 'B1 *.bak backups' $b1

# C1 _tmp_* scratch
$c1 = Get-ChildItem $eval -File -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -like '_tmp_*' } | Select-Object -ExpandProperty FullName
Stage-Items 'C1 _tmp_* scratch' $c1

# D1 full-episode checkpoints
$d1 = Get-ChildItem (Join-Path $runs 'checkpoints') -File -ErrorAction SilentlyContinue |
      Select-Object -ExpandProperty FullName
Stage-Items 'D1 _w1_runs/checkpoints blobs' $d1

# D2 rollout_* only (theta_* all kept)
$d2 = Get-ChildItem (Join-Path $runs 'rl') -File -Filter 'rollout_*.npz' -ErrorAction SilentlyContinue |
      Select-Object -ExpandProperty FullName
Stage-Items 'D2 rollout_* buffers' $d2

$manifest = Join-Path $stage '_restore_manifest.csv'
$rows | Export-Csv -Path $manifest -NoTypeInformation -Encoding UTF8
Write-Output ""
Write-Output ("manifest: {0}  rows={1}" -f $manifest, $rows.Count)
$tot = ($rows | Measure-Object -Property bytes -Sum)
Write-Output ("STAGED TOTAL: {0} files  {1:n2} MB" -f $tot.Count, ($tot.Sum / 1MB))
