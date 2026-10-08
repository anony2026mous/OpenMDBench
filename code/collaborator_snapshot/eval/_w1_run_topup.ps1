# Batch (corrected): remaining 58 episodes for the three-arm comparison.
#
# Verified gap list (see _w1_gap_authoritative.py):
#   llm-rule : seed 11 on {04,07,12,13,14}  +  seed 13 on {04..14 ex 01,02,03}
#              -> g1 (IE-01/02/03) already has all 5 seed families; step 1 added
#                 seed 7 for IE-01..08.  Nothing else is needed there.
#   pure-llm : ALL 14 scenarios x seeds 7/11/13 (42).  The 30 historical episodes
#              carry no envelope record and are superseded by the 45/10 -> 43/8
#              change, so they must be regenerated rather than topped up.
#   rl       : nothing (n>=3 everywhere).
#
# Idempotent: each invocation skips scenarios whose output JSON already exists.
$ErrorActionPreference = 'Continue'
$eval = 'C:\Code\source-code\openmd\code\eval'
$py   = 'C:\Code\source-code\source_codes\.venv\Scripts\python.exe'
$JOBS = 6

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:OPENMDBENCH_ROOT = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:MPLCONFIGDIR = 'C:\Code\source-code\.mplcache'
Set-Location $eval

$s11 = @('IE-04-COMBINED-ARMS','IE-07-CROSS-DOMAIN','IE-12-FOG-ONSET',
         'IE-13-DEEP-STRIKE','IE-14-SATURATION-THREE-WAVE')
$s13 = @('IE-04-COMBINED-ARMS','IE-05-MULTI-AXIS','IE-06-DECOY-MIXED',
         'IE-07-CROSS-DOMAIN','IE-08-ISLAND-STRIKE','IE-09-STAGGERED-WAVES',
         'IE-10-DUAL-AXIS-PINCER','IE-11-DECOY-SCREEN','IE-12-FOG-ONSET',
         'IE-13-DEEP-STRIKE','IE-14-SATURATION-THREE-WAVE')
$all14 = @('IE-01-SINGLE-TARGET','IE-02-DUAL-THREAT','IE-03-SURFACE-RAID',
           'IE-04-COMBINED-ARMS','IE-05-MULTI-AXIS','IE-06-DECOY-MIXED',
           'IE-07-CROSS-DOMAIN','IE-08-ISLAND-STRIKE','IE-09-STAGGERED-WAVES',
           'IE-10-DUAL-AXIS-PINCER','IE-11-DECOY-SCREEN','IE-12-FOG-ONSET',
           'IE-13-DEEP-STRIKE','IE-14-SATURATION-THREE-WAVE')

$steps = @(
  @{ n='llm-rule seed11'; p='llm';      s=$s11;   seed=11; tag='top' },
  @{ n='llm-rule seed13'; p='llm';      s=$s13;   seed=13; tag='top' },
  @{ n='pure-llm seed7';  p='pure-llm'; s=$all14; seed=7;  tag='envfix' },
  @{ n='pure-llm seed11'; p='pure-llm'; s=$all14; seed=11; tag='envfix' },
  @{ n='pure-llm seed13'; p='pure-llm'; s=$all14; seed=13; tag='envfix' }
)

$sw = [Diagnostics.Stopwatch]::StartNew()
$i = 0
foreach ($st in $steps) {
    $i++
    # idempotent resume: skip scenarios whose result JSON already exists.
    # NOTE the seed suffix: _w1_ie_sweep.py writes the bare tag for seed 7 and
    # "<tag>_s<seed>" for every other seed (because multi-seed runs must not
    # overwrite each other).  Omitting it made the first attempt skip seed 11 on
    # IE-04/IE-07 - the seed-7 file looked like "already done".
    $seedSuffix = if ($st.seed -eq 7) { '' } else { '_s' + $st.seed }
    $todo = @()
    foreach ($sc in $st.s) {
        $stem = 'ie_' + ($st.p -replace '-','') + '_' + $sc.ToLower()
        $out  = Join-Path $eval ("_w1_runs\" + $stem + "_" + $st.tag + $seedSuffix + ".json")
        if (Test-Path -LiteralPath $out) {
            Write-Output ("  [skip] {0}" -f (Split-Path $out -Leaf))
        } else { $todo += $sc }
    }
    Write-Output ""
    Write-Output ("=" * 78)
    Write-Output ("[{0}/{1}] {2}  -> {3} episodes, jobs={4}, seed={5}" -f `
                  $i, $steps.Count, $st.n, $todo.Count, $JOBS, $st.seed)
    Write-Output ("=" * 78)
    if ($todo.Count -eq 0) { Write-Output "  nothing to do"; continue }

    $argv = @('_w1_ie_sweep.py', '--planner', $st.p, '--scenarios') + $todo +
            @('--jobs', $JOBS, '--tag', $st.tag, '--seed', $st.seed,
              '--step-timeout', '180', '--wall-limit', '7200', '--episode-timeout', '7800')
    if ($st.p -eq 'pure-llm') { $argv += @('--pure-llm-envelope', 'executor') }
    & $py @argv 2>&1 | Select-Object -Last 12
    Write-Output ("  [step done] total elapsed {0:n1} min" -f $sw.Elapsed.TotalMinutes)
}

$sw.Stop()
Write-Output ""
Write-Output ("=" * 78)
Write-Output ("BATCH COMPLETE: {0} steps, {1:n1} min" -f $steps.Count, $sw.Elapsed.TotalMinutes)
Write-Output ("=" * 78)
