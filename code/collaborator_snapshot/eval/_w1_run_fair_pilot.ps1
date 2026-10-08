# Fair-口径 pilot: run the three LLM arms with --llm-briefing withheld (no enemy intel).
#
# Goal: decide whether the hybrid arms still beat the single architectures once the
# enemy-briefing advantage is removed. If the advantage vanishes, fall back to the
# declared briefing (the previous method).
#
# Scenarios chosen for their role in the DECLARED snapshot:
#   IE-01  briefing matters most (early-terminal, hybrid was 0.903)
#   IE-04  no-signal control scenario
#   IE-05  hybrid won stably
#   IE-06  decoy screening; hybrid won stably
#   IE-11  worst leak + the roe misclassification bug: the key case
#   IE-13  representative new scenario
#
# rule-rule and rl are UNCHANGED by this switch (they never read the briefing), so
# their existing numbers remain valid and are reused as the baselines.
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

$scen = @('IE-01-SINGLE-TARGET','IE-04-COMBINED-ARMS','IE-05-MULTI-AXIS',
          'IE-06-DECOY-MIXED','IE-11-DECOY-SCREEN','IE-13-DEEP-STRIKE')
$seeds = @(7, 11, 13)

$steps = @()
foreach ($s in $seeds) {
  $steps += @{ n="llm-rule s$s"; p='llm';      seed=$s; tag='fair' }
  $steps += @{ n="pure-llm s$s"; p='pure-llm'; seed=$s; tag='fairp' }
  $steps += @{ n="llm-rl   s$s"; p='llm-rl';   seed=$s; tag='fairr' }
}

$sw = [Diagnostics.Stopwatch]::StartNew()
$i = 0
foreach ($st in $steps) {
    $i++
    $seedSuffix = if ($st.seed -eq 7) { '' } else { '_s' + $st.seed }
    $todo = @()
    foreach ($sc in $scen) {
        $stem = 'ie_' + ($st.p -replace '-','') + '_' + $sc.ToLower()
        $out  = Join-Path $eval ("_w1_runs\" + $stem + "_" + $st.tag + $seedSuffix + ".json")
        if (-not (Test-Path -LiteralPath $out)) { $todo += $sc }
    }
    Write-Output ""
    Write-Output ("=" * 74)
    Write-Output ("[{0}/{1}] {2}  -> {3} episodes (withheld briefing)" -f `
                  $i, $steps.Count, $st.n, $todo.Count)
    Write-Output ("=" * 74)
    if ($todo.Count -eq 0) { Write-Output "  nothing to do"; continue }

    $argv = @('_w1_ie_sweep.py', '--planner', $st.p, '--scenarios') + $todo +
            @('--jobs', $JOBS, '--tag', $st.tag, '--seed', $st.seed,
              '--step-timeout', '180', '--wall-limit', '7200', '--episode-timeout', '7800',
              '--llm-briefing', 'withheld')
    if ($st.p -eq 'pure-llm') { $argv += @('--pure-llm-envelope', 'executor') }
    if ($st.p -eq 'llm-rl') {
        $argv += @('--rl-theta', $THETA, '--decision-interval', '5',
                   '--rl-stochastic', '--rl-speed-source', 'legacy_tags')
    }
    & $py @argv 2>&1 | Select-Object -Last 10
    Write-Output ("  [step done] elapsed {0:n1} min" -f $sw.Elapsed.TotalMinutes)
}

$sw.Stop()
Write-Output ""
Write-Output ("=" * 74)
Write-Output ("FAIR PILOT COMPLETE: {0} steps, {1:n1} min" -f $steps.Count, $sw.Elapsed.TotalMinutes)
Write-Output ("=" * 74)
