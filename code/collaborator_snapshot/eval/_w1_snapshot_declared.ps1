# Snapshot the current (declared-briefing / pre-fix) state before changing anything.
#   - all episode result JSONs  -> archive
#   - the code that produced them (harness + key docs) -> archive
#   - a manifest with sha256 so the snapshot can be verified later
$stamp  = Get-Date -Format 'yyyyMMdd_HHmm'
$root   = 'C:\Code\source-code\openmd'
$eval   = Join-Path $root 'code\eval'
$runs   = Join-Path $eval '_w1_runs'
$arch   = Join-Path $env:USERPROFILE ("<private-archive>\declared_briefing_snapshot_$stamp")

New-Item -ItemType Directory -Force -Path $arch | Out-Null
if (-not (Test-Path -LiteralPath $arch -PathType Container)) { throw "archive dir failed: $arch" }
Write-Output "archive root: $arch"

# ---- 1. result JSONs (episodes) -------------------------------------------
$dst1 = Join-Path $arch 'results'
New-Item -ItemType Directory -Force -Path $dst1 | Out-Null
$jsons = Get-ChildItem $runs -File -Filter '*.json' -ErrorAction SilentlyContinue
foreach ($f in $jsons) { Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $dst1 $f.Name) -Force }
Write-Output ("  results copied: {0} files, {1:n1} MB" -f $jsons.Count,
              (($jsons | Measure-Object Length -Sum).Sum / 1MB))

# ---- 2. code that produced them -------------------------------------------
$dst2 = Join-Path $arch 'code'
New-Item -ItemType Directory -Force -Path $dst2 | Out-Null
$codeFiles = @(
  'run_episode.py','llm_planner.py','pure_llm_agent.py','rule_planner.py',
  'v2_executor.py','rl_executor.py','rl_agent.py','interception_graph.py',
  'strategy_metrics.py','goai_protocol.py','attack_driver.py','ie_goal_features.py',
  '_w1_ie_sweep.py','_w1_claim_table.py','_w1_four_arm_analysis.py','_w1_results_table.py'
)
foreach ($n in $codeFiles) {
  $p = Join-Path $eval $n
  if (Test-Path -LiteralPath $p) { Copy-Item -LiteralPath $p -Destination (Join-Path $dst2 $n) -Force }
}
$docs = @('LLMRL_RESULTS_TABLE.md','LLMRL_CLAIM_TABLE.md','LLMRL_CURRENT_AUDIT.md',
          'LLMRL_EXPERIMENT_DESIGN.md','IE_EXT_SCENARIOS.md','PAPER_READINESS_GAPS.md')
foreach ($n in $docs) {
  $p = Join-Path $eval $n
  if (Test-Path -LiteralPath $p) { Copy-Item -LiteralPath $p -Destination (Join-Path $dst2 $n) -Force }
}
Write-Output ("  code/docs copied: {0} files" -f (Get-ChildItem $dst2 -File).Count)

# ---- 3. scenario packages (the 14 IE + catalogs) ---------------------------
$dst3 = Join-Path $arch 'scenarios'
New-Item -ItemType Directory -Force -Path $dst3 | Out-Null
$sc = Join-Path $root 'source-code\source_codes\scenarios\formal'
foreach ($d in (Get-ChildItem $sc -Directory | Where-Object { $_.Name -like 'ie_*' })) {
  Copy-Item -LiteralPath $d.FullName -Destination (Join-Path $dst3 $d.Name) -Recurse -Force
}
$reg = Join-Path $sc 'registry.yaml'
if (Test-Path $reg) { Copy-Item -LiteralPath $reg -Destination (Join-Path $dst3 'registry.yaml') -Force }
$cat = Join-Path $root 'source-code\source_codes\catalog\v2'
foreach ($n in @('ie_set.yaml','md_ad_006.yaml')) {
  $p = Join-Path $cat $n
  if (Test-Path $p) { Copy-Item -LiteralPath $p -Destination (Join-Path $dst3 $n) -Force }
}
Write-Output ("  scenario packages copied: {0} dirs" -f (Get-ChildItem $dst3 -Directory).Count)

# ---- 4. manifest with hashes ----------------------------------------------
$manifest = Join-Path $arch '_manifest_sha256.csv'
$rows = Get-ChildItem $arch -Recurse -File |
        Where-Object { $_.Name -ne '_manifest_sha256.csv' } |
        ForEach-Object {
            [pscustomobject]@{
                rel  = $_.FullName.Substring($arch.Length + 1)
                bytes = $_.Length
                sha256 = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
            }
        }
$rows | Export-Csv -Path $manifest -NoTypeInformation -Encoding UTF8
Write-Output ("  manifest rows: {0}" -f $rows.Count)

# ---- 5. verify ------------------------------------------------------------
$src = (Get-ChildItem $runs -File -Filter '*.json' | Measure-Object Length -Sum)
$cop = (Get-ChildItem $dst1 -File -Filter '*.json' | Measure-Object Length -Sum)
Write-Output ""
Write-Output ("VERIFY results: src={0} files/{1:n0} B   copy={2} files/{3:n0} B   match={4}" -f `
    $src.Count, $src.Sum, $cop.Count, $cop.Sum, (($src.Count -eq $cop.Count) -and ($src.Sum -eq $cop.Sum)))
$tot = (Get-ChildItem $arch -Recurse -File | Measure-Object Length -Sum)
Write-Output ("ARCHIVE TOTAL: {0} files, {1:n1} MB" -f $tot.Count, ($tot.Sum / 1MB))
Write-Output "ARCHIVE PATH: $arch"
