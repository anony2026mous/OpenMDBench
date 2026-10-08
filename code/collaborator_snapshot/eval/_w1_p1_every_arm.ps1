# P1: every arm produces data - 3 LLM arms x 14 IE scenarios at seed 7, withheld口径.
#
# Acceptance: all three arms have a reading on all 14 scenarios (no blank arm).
# Idempotent: an existing (and FRESH) result file is skipped, so the in-flight
# pwsh-3 episodes (IE-11 for llm-rule / llm-rl) are reused rather than re-run.
#
# Concurrency: one invocation per arm, each with --jobs 6, run sequentially so the
# endpoint never sees more than 6 concurrent episodes (9 previously caused a
# step_timeout abort).
$ErrorActionPreference = 'Continue'
$eval = 'C:\Code\source-code\openmd\code\eval'
$py   = 'C:\Code\source-code\source_codes\.venv\Scripts\python.exe'
$THETA = '_w1_runs/rl/theta_arm5_llm_reward_v9.npz'
$JOBS = 6
$CUTOFF = Get-Date '2026-09-27 00:00'   # older files are leftovers, not valid skips

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:OPENMDBENCH_ROOT = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:MPLCONFIGDIR = 'C:\Code\source-code\.mplcache'
Set-Location $eval

$SC = @('IE-01-SINGLE-TARGET','IE-02-DUAL-THREAT','IE-03-SURFACE-RAID',
        'IE-04-COMBINED-ARMS','IE-05-MULTI-AXIS','IE-06-DECOY-MIXED',
        'IE-07-CROSS-DOMAIN','IE-08-ISLAND-STRIKE','IE-09-STAGGERED-WAVES',
        'IE-10-DUAL-AXIS-PINCER','IE-11-DECOY-SCREEN','IE-12-FOG-ONSET',
        'IE-13-DEEP-STRIKE','IE-14-SATURATION-THREE-WAVE')

$arms = @(
  @{ p='llm';      tag='whd' },
  @{ p='llm-rl';   tag='whd' },
  @{ p='pure-llm'; tag='whd' }
)

$sw = [Diagnostics.Stopwatch]::StartNew()
foreach ($a in $arms) {
    $todo = @()
    foreach ($sc in $SC) {
        $stem = 'ie_' + ($a.p -replace '-','') + '_' + $sc.ToLower() + '_' + $a.tag
        $f = Join-Path $eval ("_w1_runs\$stem.json")
        if (Test-Path -LiteralPath $f) {
            if ((Get-Item $f).LastWriteTime -gt $CUTOFF) {
                Write-Output "  [skip fresh] $stem.json"
            } else {
                Write-Output "  [stale, will run] $stem.json"
                $todo += $sc
            }
        } else { $todo += $sc }
    }
    Write-Output ""
    Write-Output ("=" * 76)
    Write-Output ("P1 arm={0}  -> {1}/{2} scenarios to run (jobs={3}, withheld)" -f `
                  $a.p, $todo.Count, $SC.Count, $JOBS)
    Write-Output ("=" * 76)
    if ($todo.Count -eq 0) { continue }

    $argv = @('_w1_ie_sweep.py','--planner',$a.p,'--scenarios') + $todo +
            @('--jobs',$JOBS,'--tag',$a.tag,'--seed','7',
              '--step-timeout','180','--wall-limit','7200','--episode-timeout','7800',
              '--llm-briefing','withheld')
    if ($a.p -eq 'pure-llm') { $argv += @('--pure-llm-envelope','executor') }
    if ($a.p -eq 'llm-rl') {
        $argv += @('--rl-theta',$THETA,'--decision-interval','5',
                   '--rl-stochastic','--rl-speed-source','legacy_tags')
    }
    & $py @argv 2>&1 | Select-Object -Last 8
    Write-Output ("  [arm {0} done] elapsed {1:n1} min" -f $a.p, $sw.Elapsed.TotalMinutes)
}

$sw.Stop()
Write-Output ""
Write-Output ("P1 COMPLETE: {0:n1} min" -f $sw.Elapsed.TotalMinutes)
