# Queue seeds 19 and 23 as the fifth and sixth seeds, without touching what runs now.
#
# Both are appended to the SAME tag (`n3`), so every existing seed keeps its own
# files (`..._n3.json`, `..._n3_s11.json`, `..._n3_s13.json`, `..._n3_s17.json`) and the
# new ones land beside them as `..._n3_s19.json` / `..._n3_s23.json`.  Nothing is
# overwritten and the four completed seeds stay intact - the analysis reads all six.
#
# The two seeds run SEQUENTIALLY (one driver call each) so the shared LLM endpoint
# never sees more than 6 concurrent episodes; 9 previously tripped `step_timeout`
# and produced an aborted, worthless episode.
$ErrorActionPreference = 'Continue'
$eval = 'C:\Code\source-code\openmd\code\eval'
$py   = 'C:\Code\source-code\source_codes\.venv\Scripts\python.exe'
$SEEDS = @(19, 23)
$MAX_WAIT_MIN = 120     # nothing else should be running; fail fast if something is
$POLL_SEC = 60

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:OPENMDBENCH_ROOT = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:MPLCONFIGDIR = 'C:\Code\source-code\.mplcache'

# The LLM endpoint is on a LAN address.  If a proxy is configured, requests to it are
# routed through that proxy instead of going direct, and the whole batch dies at
# tick 0 with ProxyError.  That is exactly what happened on 2026-09-28 15:27: the
# environment carried ALL_PROXY/HTTP_PROXY/HTTPS_PROXY pointing at 127.0.0.1:7897
# where nothing was listening, while the endpoint itself answered fine (HTTP 200).
#
# So: drop the proxy variables for the child processes.  This affects only this run
# and grants no wider access - it makes the client connect directly, which is how
# every successful batch so far has reached the model.
foreach ($v in 'ALL_PROXY','HTTP_PROXY','HTTPS_PROXY','all_proxy','http_proxy','https_proxy') {
    Remove-Item "env:$v" -ErrorAction SilentlyContinue
}
Write-Output ("proxy env cleared: ALL_PROXY='{0}' HTTP_PROXY='{1}'" -f `
              $env:ALL_PROXY, $env:HTTP_PROXY)

Set-Location $eval

function Get-GridDrivers {
    return @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
             Where-Object { $_.CommandLine -like '*_w1_grid_driver*' }).Count
}

$start = Get-Date
Write-Output ("seeds {0} queue armed at {1}" -f ($SEEDS -join ','), $start.ToString('yyyy-MM-dd HH:mm:ss'))
Write-Output "waiting until no grid driver is running before taking the endpoint"

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
        Write-Output "seed queue: wait cap reached while another driver is running; NOT starting"
        exit 2
    }
    Start-Sleep -Seconds $POLL_SEC
}

foreach ($s in $SEEDS) {
    Write-Output ""
    Write-Output ("=" * 78)
    Write-Output ("starting seed {0} at {1}" -f $s, (Get-Date).ToString('HH:mm:ss'))
    Write-Output ("=" * 78)
    & $py -u _w1_grid_driver.py --tag n3 --seeds $s --jobs 6 `
        --wall-limit 7200 --episode-timeout 7800 --step-timeout 180 2>&1
    Write-Output ("seed {0} driver returned" -f $s)
}

Write-Output ""
Write-Output ("all queued seeds done: {0}" -f ($SEEDS -join ','))
