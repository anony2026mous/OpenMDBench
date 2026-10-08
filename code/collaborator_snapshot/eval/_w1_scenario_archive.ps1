# Pre-change archive for the scenario-set cleanup.
# Captures everything that is NOT recoverable from git:
#   - the 10 non-IE packages            (6 tracked -> recoverable, 4 untracked -> NOT)
#   - the island-strike package         (untracked -> NOT recoverable)
#   - catalog/v2/{ie_set,md_ad_006}.yaml (untracked -> NOT recoverable)
#   - the working-tree contents of the 6 modified engine files
#     plus a diff-vs-HEAD so the uncommitted edits are preserved exactly
$sub  = 'C:\Code\source-code\openmd\source-code'
$sc   = Join-Path $sub 'source_codes'
$arch = Join-Path $env:USERPROFILE 'openmd_private_archive\scenario_cleanup_20260205'

New-Item -ItemType Directory -Force -Path $arch | Out-Null
if (-not (Test-Path -LiteralPath $arch -PathType Container)) { throw "archive dir not created: $arch" }
$probe = Join-Path $arch '.w'; Set-Content -LiteralPath $probe -Value ok; Remove-Item $probe -Force

$rows = New-Object System.Collections.ArrayList
function Save-Item([string]$group, [string]$src, [string]$rel) {
    if (-not (Test-Path -LiteralPath $src)) { Write-Output "  skip(absent) $rel"; return }
    $dst = Join-Path $arch $rel
    $d = Split-Path $dst -Parent
    if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
    Copy-Item -LiteralPath $src -Destination $dst -Recurse -Force
    $len = (Get-ChildItem -LiteralPath $src -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    [void]$rows.Add([pscustomobject]@{ group=$group; rel=$rel; bytes=$len })
}

$nonIe = @('md_ad_002_easy','md_ad_002_medium','md_ad_002_hard',
           'md_int_003_easy','md_int_003_medium','md_int_003_hard',
           'md_ad_004_deception','md_int_002_air_surface',
           'md_int_005_stealth_multi_axis','md_int_006_saturation_roe')
foreach ($p in $nonIe) {
    Save-Item 'non_ie_package' (Join-Path $sc "scenarios\formal\$p") "scenarios/formal/$p"
}
Save-Item 'ie08_package_pre_rename' (Join-Path $sc 'scenarios\formal\md_ad_006_island_strike') 'scenarios/formal/md_ad_006_island_strike'
Save-Item 'catalog' (Join-Path $sc 'catalog\v2\ie_set.yaml')   'catalog/v2/ie_set.yaml'
Save-Item 'catalog' (Join-Path $sc 'catalog\v2\md_ad_006.yaml') 'catalog/v2/md_ad_006.yaml'
Save-Item 'registry' (Join-Path $sc 'scenarios\formal\registry.yaml') 'scenarios/formal/registry.yaml'

$engineFiles = @('openmdbench/benchmark.py','openmdbench/combat/system_v2.py',
                 'openmdbench/missions/engine_v2.py','openmdbench/release_validation.py',
                 'openmdbench/scenarios/declarative_v2.py','openmdbench/sessions/lifecycle_v2.py')
foreach ($f in $engineFiles) {
    Save-Item 'engine_modified' (Join-Path $sc $f) "source_codes/$f"
    # engine tests we are about to edit
    Get-ChildItem (Join-Path $sc 'tests') -Recurse -File -Filter '*.py' |
      Where-Object { $_.FullName -match 'test_all_scenarios_load|test_map_terrain_v2|test_jamming_observation_v2|test_md_int_003_scenarios|test_md_ad_002_v2_migration|test_md_ad_002_registration' } |
      ForEach-Object {
        $r2 = 'source_codes/' + $_.FullName.Substring($sc.Length + 1).Replace('\','/')
        Save-Item 'engine_test' $_.FullName $r2
      }
}

# exact uncommitted edits
Push-Location $sub
git diff > (Join-Path $arch 'engine_uncommitted.diff') 2>$null
git status --porcelain > (Join-Path $arch 'engine_status.txt') 2>$null
Pop-Location

$rows | Export-Csv -Path (Join-Path $arch '_archive_manifest.csv') -NoTypeInformation -Encoding UTF8
$tot = ($rows | Measure-Object -Property bytes -Sum)
Write-Output ""
Write-Output ("archived groups: {0}" -f (($rows | Group-Object group | ForEach-Object { "$($_.Name)=$($_.Count)" }) -join ' '))
Write-Output ("archive: {0} entries, {1:n1} KB  ->  {2}" -f $rows.Count, ($tot.Sum/1KB), $arch)
