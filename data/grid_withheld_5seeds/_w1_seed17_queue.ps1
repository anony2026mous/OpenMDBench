# Queue seed 17 as a FOURTH seed, without touching the run that is already going.
#
# This waits for the current grid driver to exit, then starts the same grid with
# one extra seed.  Nothing about the in-flight job is modified: it keeps its own
# process, its own cap of 6 concurrent episodes, and its own output files.  The two
# phases are strictly sequential, so the LLM endpoint never sees more than 6
# concurrent episodes at a time (9 previously tripped `step_timeout` and produced
# an aborted, worthless episode).
#
# The skip logic in the driver is idempotent and keyed on the seed-suffixed
# filename, so re-running this is safe and it resumes after an interruption.
$ErrorActionPreference = 'Continue'
$eval = 'C:\Code\source-code\openmd\code\eval'
$py   = 'C:\Code\source-code\source_codes\.venv\Scripts\python.exe'
$SEED = 17
$MAX_WAIT_MIN = 900      # 15 h: the current phase is projected at ~6 h, so this
                         # must not expire the way the 7 h generic relay would
$POLL_SEC = 180

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:OPENMDBENCH_ROOT = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:MPLCONFIGDIR = 'C:\Code\source-code\.mplcache'
Set-Location $eval

function Get-GridDrivers {
    return @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
             Where-Object { $_.CommandLine -like '*_w1_grid_driver*' }).Count
}

$start = Get-Date
Write-Output ("seed {0} queue armed at {1}" -f $SEED, $start.ToString('yyyy-MM-dd HH:mm:ss'))
Write-Output ("waiting for the current grid driver to exit (poll {0}s, cap {1} min)" -f $POLL_SEC, $MAX_WAIT_MIN)

$zero = 0
while ($true) {
    $n = Get-GridDrivers
    $mins = [math]::Round(((Get-Date) - $start).TotalMinutes, 1)
    if ($n -eq 0) {
        $zero++
        Write-Output ("  [{0} min] no grid driver ({1}/3 confirmations)" -f $mins, $zero)
        if ($zero -ge 3) { break }
    } else {
        if ($zero -ne 0) { Write-Output ("  [{0} min] driver back ({1})" -f $mins, $n) }
        $zero = 0
    }
    if (((Get-Date) - $start).TotalMinutes -gt $MAX_WAIT_MIN) {
        Write-Output "seed queue: wait cap reached; NOT starting (the earlier phase is still running)"
        exit 2
    }
    Start-Sleep -Seconds $POLL_SEC
}

Write-Output ""
Write-Output ("=" * 78)
Write-Output ("current phase finished after {0} min - starting seed {1}" -f `
              [math]::Round(((Get-Date) - $start).TotalMinutes, 1), $SEED)
Write-Output ("=" * 78)

& $py -u _w1_grid_driver.py --tag n3 --seeds $SEED --jobs 6 `
    --wall-limit 7200 --episode-timeout 7800 --step-timeout 180 2>&1

Write-Output ""
Write-Output ("seed {0} done" -f $SEED)
