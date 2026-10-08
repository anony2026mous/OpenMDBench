# Wait for P1 to finish, then run the full P3 analysis stack and log it.
# Kept as a separate watcher so the analysis is produced with zero manual steps and
# is reproducible from the log alone.
$ErrorActionPreference = 'Continue'
$eval = 'C:\Code\source-code\openmd\code\eval'
$py   = 'C:\Code\source-code\source_codes\.venv\Scripts\python.exe'
$log  = Join-Path $eval '_w1_runs\P1_ANALYSIS_20260927.txt'
$MAX_WAIT_MIN = 400
$POLL_SEC = 240

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:OPENMDBENCH_ROOT = 'C:\Code\source-code\openmd\source-code\source_codes'
$env:MPLCONFIGDIR = 'C:\Code\source-code\.mplcache'
Set-Location $eval

function Get-P1Driver {
    return @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
             Where-Object { $_.CommandLine -like '*_w1_grid_driver*' }).Count
}

$start = Get-Date
Write-Output ("P1 analysis watcher armed at {0}" -f $start.ToString('yyyy-MM-dd HH:mm:ss'))
$zero = 0
while ($true) {
    $n = Get-P1Driver
    $mins = [math]::Round(((Get-Date) - $start).TotalMinutes, 1)
    if ($n -eq 0) {
        $zero++
        Write-Output ("  [{0} min] P1 driver absent ({1}/2)" -f $mins, $zero)
        if ($zero -ge 2) { break }
    } else {
        if ($zero -ne 0) { Write-Output ("  [{0} min] P1 driver back ({1} procs)" -f $mins, $n) }
        $zero = 0
    }
    if (((Get-Date) - $start).TotalMinutes -gt $MAX_WAIT_MIN) {
        Write-Output "P1 analysis watcher: wait cap reached; running analysis on partial data"
        break
    }
    Start-Sleep -Seconds $POLL_SEC
}

Write-Output ""
Write-Output "P1 driver finished after $([math]::Round(((Get-Date) - $start).TotalMinutes,1)) min; running analysis"
"" | Set-Content $log -Encoding UTF8

$steps = @(
    @{ n = 'cell inspection'; a = @('_w1_cell_inspect.py') },
    @{ n = 'P3 verdict';     a = @('_w1_p3_analysis.py') },
    @{ n = 'withheld table'; a = @('_w1_withheld_table.py') },
    @{ n = 'behavior signal'; a = @('_w1_behavior_signal.py') },
    @{ n = 'length audit';    a = @('_w1_length_audit.py') },
    @{ n = 'baseline partition'; a = @('_w1_baseline_partition.py') }
)
foreach ($s in $steps) {
    ("`n`n" + ("#" * 96)) | Add-Content $log -Encoding UTF8
    ("### " + $s.n) | Add-Content $log -Encoding UTF8
    ("#" * 96) | Add-Content $log -Encoding UTF8
    & $py -u @($s.a) 2>&1 | Add-Content $log -Encoding UTF8
    Write-Output ("  ran: {0}" -f $s.n)
}
Write-Output ("analysis written to {0}" -f $log)
