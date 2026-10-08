# Step 1 of the fair-口径 pilot: IE-11 only, three LLM arms, seeds 7/11/13.
#
# IE-11 is the decisive case: it is where (a) the enemy-briefing leak was most
# severe (full decoy/main-strike plan disclosed at tick 0) and (b) the ROE
# misclassification bug wrongly labelled the real strike as NON-THREAT.
# rule-rule / rl never read the briefing, so their numbers stay valid.
#
# The DECLARED-briefing dataset is preserved separately (snapshot + --llm-briefing
# declared), so this run only ADDS a fair-口径 counterpart.
$ErrorActionPreference = 'Continue'
$eval = 'C:\Code\source-code\openmd\code\eval'
$py   = 'C:\Code\source-code\source_codes\.venv\Scripts\python.exe'
$JOBS = 6
$THETA = '_w1_runs/rl/theta_arm5_llm_reward_v9.npz'
$SC = 'IE-11-DECOY-SCREEN'

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:OPENMDBENCH_ROOT = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:MPLCONFIGDIR = 'C:\Code\source-code\.mplcache'
Set-Location $eval

$steps = @(
  @{ n='llm-rule'; p='llm';      tag='fair';  seed=7;  rl=$false },
  @{ n='llm-rule'; p='llm';      tag='fair';  seed=11; rl=$false },
  @{ n='llm-rule'; p='llm';      tag='fair';  seed=13; rl=$false },
  @{ n='pure-llm'; p='pure-llm'; tag='fairp'; seed=7;  rl=$false },
  @{ n='pure-llm'; p='pure-llm'; tag='fairp'; seed=11; rl=$false },
  @{ n='pure-llm'; p='pure-llm'; tag='fairp'; seed=13; rl=$false },
  @{ n='llm-rl';   p='llm-rl';   tag='fairr'; seed=7;  rl=$true  },
  @{ n='llm-rl';   p='llm-rl';   tag='fairr'; seed=11; rl=$true  },
  @{ n='llm-rl';   p='llm-rl';   tag='fairr'; seed=13; rl=$true  }
)

$sw = [Diagnostics.Stopwatch]::StartNew()
$i = 0
foreach ($st in $steps) {
    $i++
    $seedSuffix = if ($st.seed -eq 7) { '' } else { '_s' + $st.seed }
    $stem = 'ie_' + ($st.p -replace '-','') + '_' + $SC.ToLower()
    $out  = Join-Path $eval ("_w1_runs\" + $stem + "_" + $st.tag + $seedSuffix + ".json")
    if (Test-Path -LiteralPath $out) {
        Write-Output ("[{0}/9] {1} seed={2}  [skip] already exists" -f $i, $st.n, $st.seed)
        continue
    }
    Write-Output ""
    Write-Output ("[{0}/9] {1}  seed={2}  (briefing=withheld)" -f $i, $st.n, $st.seed)

    $argv = @('_w1_ie_sweep.py', '--planner', $st.p, '--scenarios', $SC,
              '--jobs', '1', '--tag', $st.tag, '--seed', $st.seed,
              '--step-timeout', '180', '--wall-limit', '7200', '--episode-timeout', '7800',
              '--llm-briefing', 'withheld')
    if ($st.p -eq 'pure-llm') { $argv += @('--pure-llm-envelope', 'executor') }
    if ($st.rl) {
        $argv += @('--rl-theta', $THETA, '--decision-interval', '5',
                   '--rl-stochastic', '--rl-speed-source', 'legacy_tags')
    }
    & $py @argv 2>&1 | Select-Object -Last 6
    Write-Output ("    elapsed {0:n1} min" -f $sw.Elapsed.TotalMinutes)
}

$sw.Stop()
Write-Output ""
Write-Output ("IE-11 FAIR PILOT DONE: {0:n1} min total" -f $sw.Elapsed.TotalMinutes)
