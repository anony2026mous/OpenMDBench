# No-intel test for the two arms whose briefing channel is CLOSED:
#   llm-rule (--planner llm) and llm-rl (--planner llm-rl).
# pure-llm is excluded: its own timeline injection (pure_llm_agent.py:297) is not
# yet gated, so it cannot run a clean withheld口径 yet.
#
# Concurrency: the sweep takes ONE seed per invocation, so 5 invocations are
# launched as background processes at once -> effectively 5 concurrent episodes.
# Each invocation uses --jobs 1 so total concurrency stays at 5 (safe).
#
# Tag is NEW and target files are age-checked, so the 9/25 leftovers cannot
# silently satisfy the skip test (that bug cost a whole batch).
$ErrorActionPreference = 'Continue'
$eval = 'C:\Code\source-code\openmd\code\eval'
$py   = 'C:\Code\source-code\source_codes\.venv\Scripts\python.exe'
$THETA = '_w1_runs/rl/theta_arm5_llm_reward_v9.npz'
$TAG_LR = 'wheld2'
$TAG_RL = 'wheld2r'

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:OPENMDBENCH_ROOT = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:MPLCONFIGDIR = 'C:\Code\source-code\.mplcache'
Set-Location $eval
$SC = 'IE-11-DECOY-SCREEN'

# jobs to launch: label, planner, seed, tag
$jobs = @(
  @{ n='llm-rule s11'; p='llm';    s=11; tag=$TAG_LR },
  @{ n='llm-rule s13'; p='llm';    s=13; tag=$TAG_LR },
  @{ n='llm-rl   s7 '; p='llm-rl'; s=7;  tag=$TAG_RL },
  @{ n='llm-rl   s11'; p='llm-rl'; s=11; tag=$TAG_RL },
  @{ n='llm-rl   s13'; p='llm-rl'; s=13; tag=$TAG_RL }
)

$procs = @()
foreach ($j in $jobs) {
    $suf = if ($j.s -eq 7) { '' } else { "_s$($j.s)" }
    $stem = 'ie_' + ($j.p -replace '-','') + '_' + $SC.ToLower() + '_' + $j.tag + $suf
    $out = Join-Path $eval ("_w1_runs\$stem.json")
    if (Test-Path -LiteralPath $out) { Write-Output "  [exists, skip] $stem"; continue }
    $argv = @('_w1_ie_sweep.py','--planner',$j.p,'--scenarios',$SC,
              '--jobs','1','--tag',$j.tag,'--seed',$j.s,
              '--step-timeout','180','--wall-limit','7200','--episode-timeout','7800',
              '--llm-briefing','withheld')
    if ($j.p -eq 'llm-rl') {
        $argv += @('--rl-theta',$THETA,'--decision-interval','5',
                   '--rl-stochastic','--rl-speed-source','legacy_tags')
    }
    Write-Output ("  launch {0}" -f $j.n)
    $procs += Start-Process -FilePath $py -ArgumentList $argv -PassThru -NoNewWindow `
                            -RedirectStandardOutput "$eval\_w1_runs\logs\_stdout_$($stem).txt" `
                            -RedirectStandardError  "$eval\_w1_runs\logs\_stderr_$($stem).txt"
}
Write-Output ""
Write-Output ("launched {0} concurrent sweeps" -f $procs.Count)
$procs | Wait-Process
Write-Output "ALL DONE"
