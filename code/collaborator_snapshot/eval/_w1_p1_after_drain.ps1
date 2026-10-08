# Wait for the in-flight 5-episode job to finish, then launch the P1 batch.
# Keeps total endpoint concurrency at <= 6 (5 in flight + 6 would breach the
# 9-concurrent region that previously caused a step_timeout abort).
$eval = 'C:\Code\source-code\openmd\code\eval'
$deadline = (Get-Date).AddHours(4)
Write-Output "waiting for in-flight episodes to drain before starting P1..."

while ((Get-Date) -lt $deadline) {
    $n = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
           Where-Object { $_.CommandLine -like '*run_episode.py*' -and $_.CommandLine -like '*--output*' }).Count
    if ($n -eq 0) {
        Write-Output ("drained at {0}; launching P1" -f (Get-Date).ToString('HH:mm:ss'))
        & "$eval\_w1_p1_every_arm.ps1"
        exit 0
    }
    Start-Sleep -Seconds 60
}
Write-Output "TIMEOUT waiting for drain; not launching"
