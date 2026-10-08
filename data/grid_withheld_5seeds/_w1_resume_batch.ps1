# Resume + extend: finish pure-llm (32 left) then run llm-rl (26).
#
# State at interruption (2026-09-26 ~22:00):
#   llm-rule  : 16/16 DONE  (tag=top)
#   pure-llm  : 10/42       (tag=envfix, seed 7 files have no suffix;
#                            IE-08/12/13/14 were cut mid-run and have no result file)
#   rl        : n>=3 already, nothing needed
#   llm-rl    : 0/26        (the remaining arm, added here as tag=topb)
#
# Idempotent: every invocation skips scenarios whose result JSON already exists,
# honouring the sweep's seed-suffix rule (seed 7 -> no suffix, else "_s<seed>").
$ErrorActionPreference = 'Continue'
$eval = 'C:\Code\source-code\openmd\code\eval'
$py   = 'C:\Code\source-code\source_codes\.venv\Scripts\python.exe'
$JOBS = 6
$THETA = '_w1_runs/rl/theta_arm5_llm_reward_v9.npz'

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:OPENMDBENCH_ROOT = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:MPLCONFIGDIR = 'C:\Code\source-code\.mplcache'
Set-Location $eval

$all14 = @('IE-01-SINGLE-TARGET','IE-02-DUAL-THREAT','IE-03-SURFACE-RAID',
           'IE-04-COMBINED-ARMS','IE-05-MULTI-AXIS','IE-06-DECOY-MIXED',
           'IE-07-CROSS-DOMAIN','IE-08-ISLAND-STRIKE','IE-09-STAGGERED-WAVES',
           'IE-10-DUAL-AXIS-PINCER','IE-11-DECOY-SCREEN','IE-12-FOG-ONSET',
           'IE-13-DEEP-STRIKE','IE-14-SATURATION-THREE-WAVE')
# llm-rl: IE-03 already has 5 seed families; the rest need seeds 11 and 13
$llmrl_sc = @('IE-01-SINGLE-TARGET','IE-02-DUAL-THREAT','IE-04-COMBINED-ARMS',
              'IE-05-MULTI-AXIS','IE-06-DECOY-MIXED','IE-07-CROSS-DOMAIN',
              'IE-08-ISLAND-STRIKE','IE-09-STAGGERED-WAVES','IE-10-DUAL-AXIS-PINCER',
              'IE-11-DECOY-SCREEN','IE-12-FOG-ONSET','IE-13-DEEP-STRIKE',
              'IE-14-SATURATION-THREE-WAVE')

$steps = @(
  @{ n='pure-llm seed7 (finish)'; p='pure-llm'; s=$all14;     seed=7;  tag='envfix'; rl=$false },
  @{ n='pure-llm seed11';         p='pure-llm'; s=$all14;     seed=11; tag='envfix'; rl=$false },
  @{ n='pure-llm seed13';         p='pure-llm'; s=$all14;     seed=13; tag='envfix'; rl=$false },
  @{ n='llm-rl  seed11';          p='llm-rl';   s=$llmrl_sc;  seed=11; tag='topb';   rl=$true  },
  @{ n='llm-rl  seed13';          p='llm-rl';   s=$llmrl_sc;  seed=13; tag='topb';   rl=$true  }
)

$sw = [Diagnostics.Stopwatch]::StartNew()
$i = 0
foreach ($st in $steps) {
    $i++
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
    if ($st.p -eq 'pure-llm') {
        $argv += @('--pure-llm-envelope', 'executor')
    }
    if ($st.rl) {
        # same口径 as the claim table default for hybrid B
        $argv += @('--rl-theta', $THETA, '--decision-interval', '5',
                   '--rl-stochastic', '--rl-speed-source', 'legacy_tags')
    }
    & $py @argv 2>&1 | Select-Object -Last 10
    Write-Output ("  [step done] total elapsed {0:n1} min" -f $sw.Elapsed.TotalMinutes)
}

$sw.Stop()
Write-Output ""
Write-Output ("=" * 78)
Write-Output ("RESUME BATCH COMPLETE: {0} steps, {1:n1} min" -f $steps.Count, $sw.Elapsed.TotalMinutes)
Write-Output ("=" * 78)
