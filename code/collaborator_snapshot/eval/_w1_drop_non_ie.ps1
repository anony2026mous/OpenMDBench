# Remove the 10 non-IE scenario packages (archived first, verified recoverable).
# Tracked packages -> git rm -r (index + worktree). Untracked -> Remove-Item.
# NOTE: keep this file pure ASCII - the host reads it as GBK and mangles literals.
$sub  = 'C:\Code\source-code\openmd\source-code'
$f    = Join-Path $sub 'source_codes\scenarios\formal'
$arch = Join-Path $env:USERPROFILE 'openmd_private_archive\scenario_cleanup_20260205'

$pkgs = @('md_ad_002_easy','md_ad_002_medium','md_ad_002_hard',
          'md_int_003_easy','md_int_003_medium','md_int_003_hard',
          'md_ad_004_deception','md_int_002_air_surface',
          'md_int_005_stealth_multi_axis','md_int_006_saturation_roe')

Write-Output "=== archive precondition ==="
$missing = 0
foreach ($p in $pkgs) {
    $a = Join-Path $arch "scenarios\formal\$p\scenario.yaml"
    if (-not (Test-Path -LiteralPath $a)) { Write-Output "  NOT ARCHIVED: $p"; $missing++ }
}
if ($missing -gt 0) { Write-Output "ABORT: $missing package(s) not in archive"; exit 1 }
Write-Output "all packages present in archive: OK"

Write-Output ""
Write-Output "=== removing ==="
foreach ($p in $pkgs) {
    $dir = Join-Path $f $p
    if (-not (Test-Path -LiteralPath $dir)) { Write-Output ("  already gone: {0}" -f $p); continue }
    Push-Location $sub
    git ls-files --error-unmatch "source_codes/scenarios/formal/$p/scenario.yaml" *>$null
    $tracked = ($LASTEXITCODE -eq 0)
    Pop-Location
    if ($tracked) {
        Push-Location $sub
        git rm -r -q "source_codes/scenarios/formal/$p" 2>&1 | Out-Null
        Pop-Location
        Write-Output ("  git rm -r      {0}" -f $p)
    } else {
        Remove-Item -LiteralPath $dir -Recurse -Force
        Write-Output ("  Remove-Item -r {0}" -f $p)
    }
}

Write-Output ""
Write-Output "=== scenarios/formal now ==="
$left = Get-ChildItem $f -Directory | Sort-Object Name
$left | ForEach-Object { "  " + $_.Name }
Write-Output ("directories: " + $left.Count)
