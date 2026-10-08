# P2 relay: once the P1 grid driver has no episodes left in flight, extend the
# grid to seeds 11 and 13 so every (arm, scenario) cell reaches n >= 3.
#
# Why a relay instead of a single 126-cell run: the user's mandated order is
# "every arm produces data first, then multiple seeds". Splitting it means P1
# results exist and can be inspected while P2 is still running, and it caps the
# blast radius if a systemic problem shows up mid-batch.
#
# The skip logic in the driver is idempotent, so re-running either phase is safe.
# Concurrency stays at the measured-safe 6.
$ErrorActionPreference = 'Continue'
$eval = 'C:\Code\source-code\openmd\code\eval'
$py   = 'C:\Code\source-code\source_codes\.venv\Scripts\python.exe'
$MAX_WAIT_MIN = 420      # give up after 7h of waiting
$POLL_SEC = 180

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:OPENMDBENCH_ROOT = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:MPLCONFIGDIR = 'C:\Code\source-code\.mplcache'
Set-Location $eval

function Get-DriverCount {
    $procs = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
               Where-Object { $_.CommandLine -like '*_w1_grid_driver*' })
    return $procs.Count
}

$start = Get-Date
Write-Output ("P2 relay armed at {0}" -f $start.ToString('yyyy-MM-dd HH:mm:ss'))
Write-Output ("waiting for P1 driver to finish (poll {0}s, cap {1} min)" -f $POLL_SEC, $MAX_WAIT_MIN)

$zeroStreak = 0
while ($true) {
    $n = Get-DriverCount
    $mins = [math]::Round(((Get-Date) - $start).TotalMinutes, 1)
    if ($n -eq 0) {
        $zeroStreak++
        Write-Output ("  [{0}] no driver in flight ({1}/2 confirmations)" -f $mins, $zeroStreak)
        if ($zeroStreak -ge 2) { break }
    } else {
        if ($zeroStreak -ne 0) { Write-Output ("  [{0}] driver back ({1} procs)" -f $mins, $n) }
        $zeroStreak = 0
    }
    if (((Get-Date) - $start).TotalMinutes -gt $MAX_WAIT_MIN) {
        Write-Output "P2 relay: wait cap reached without P1 finishing; aborting relay"
        exit 2
    }
    Start-Sleep -Seconds $POLL_SEC
}

Write-Output ""
Write-Output ("=" * 78)
Write-Output "P1 driver gone - starting P2 (seeds 11 and 13)"
Write-Output ("=" * 78)

& $py -u _w1_grid_driver.py --tag n3 --seeds 11 13 --jobs 6 `
    --wall-limit 7200 --episode-timeout 7800 --step-timeout 180 2>&1

Write-Output ""
Write-Output "P2 relay finished"
