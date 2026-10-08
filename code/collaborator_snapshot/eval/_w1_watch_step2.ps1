# Watch for step 2 of the top-up batch (planner=llm, seed=17) to start, then exit.
# Purpose: as soon as step 1 releases its 4 slots, we can stop the batch and
# relaunch at jobs=6 without ever running 4+6=10 concurrently.
$deadline = (Get-Date).AddHours(2)
$seen = $false
while ((Get-Date) -lt $deadline) {
    $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
             Where-Object { $_.CommandLine -like '*run_episode.py*' -and $_.CommandLine -like '*--output*' }
    $step2 = @($procs | Where-Object { $_.CommandLine -match '--seed 17' })
    if ($step2.Count -gt 0) {
        Write-Output ("STEP2_STARTED at {0}: {1} subprocess(es) with --seed 17" -f (Get-Date).ToString('HH:mm:ss'), $step2.Count)
        foreach ($p in $step2) {
            $sc = if ($p.CommandLine -match '--scenario\s+(\S+)') { $matches[1] } else { '?' }
            Write-Output ("   PID {0}  {1}" -f $p.ProcessId, $sc)
        }
        $seen = $true
        break
    }
    Start-Sleep -Seconds 30
}
if (-not $seen) { Write-Output "TIMEOUT: step2 not seen within 2h" }
