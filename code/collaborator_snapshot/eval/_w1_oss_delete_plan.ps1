# Open-source cleanup: exact deletion inventory (dry-run, deletes nothing)
$root  = 'C:\Code\source-code\openmd'
$sub   = "$root\source-code\source_codes"
$eval  = "$root\code\eval"
$runs  = "$eval\_w1_runs"

function Sz($items) {
    $s = ($items | Where-Object { $_ } | ForEach-Object { (Get-Item $_) } | Measure-Object Length -Sum)
    if (-not $s) { return @(0,0) }
    return @($s.Count, $s.Sum)
}
function Show($label, $items) {
    $a = Sz $items
    '{0,-46} {1,5} files  {2,12:n2} MB' -f $label, $a[0], ($a[1]/1MB)
}

Write-Output "=== KEEP (must not be deleted) ==="
$keep = @()
$keep += Get-ChildItem $sub -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '\\(\.git|__pycache__|\.pytest_cache|\.venv|\.mypy_cache|reports)\\' } |
    Select-Object -ExpandProperty FullName
Show "engine+runtime+scenarios (submodule)" $keep
$keep2 = Get-ChildItem $runs -Recurse -File -Force |
    Where-Object { $_.FullName -notmatch '\\checkpoints\\' } |
    Select-Object -ExpandProperty FullName
Show "eval results/logs/weights (non-ckpt)" $keep2

Write-Output ""
Write-Output "=== DELETE CANDIDATES ==="
$A = Get-ChildItem $sub -Recurse -Directory -Force -ErrorAction SilentlyContinue |
     Where-Object { $_.Name -in @('__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.ipynb_checkpoints') }
$A = $A | ForEach-Object { Get-ChildItem $_.FullName -Recurse -File -Force } | Select-Object -ExpandProperty FullName
Show "A1 __pycache__/.pytest_cache (engine)" $A

$B = Get-ChildItem $eval -Recurse -Directory -Force -ErrorAction SilentlyContinue |
     Where-Object { $_.Name -in @('__pycache__','.pytest_cache') } |
     ForEach-Object { Get-ChildItem $_.FullName -Recurse -File -Force } | Select-Object -ExpandProperty FullName
Show "A2 __pycache__ (code/eval)" $B

$C = Get-ChildItem $eval -File -Filter '*.bak' | Select-Object -ExpandProperty FullName
$C += Get-ChildItem $runs -File -Filter '*.bak' | Select-Object -ExpandProperty FullName
Show "B1 *.bak backup files" $C

$D = Get-ChildItem $eval -File | Where-Object { $_.Name -like '_tmp_*' } | Select-Object -ExpandProperty FullName
Show "C1 _tmp_* scratch scripts" $D

$CK = Get-ChildItem "$runs\checkpoints" -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
Show "D1 _w1_runs/checkpoints (69 full-episode blobs)" $CK

$keepw = @('theta_arm5_llm_reward_v9.npz','theta_rl_legacy2.npz')
$W = Get-ChildItem "$runs\rl" -File -Filter '*.npz' | Where-Object { $_.Name -notin $keepw } | Select-Object -ExpandProperty FullName
Show "D2 superseded theta weights (keep v9 + rlb2)" $W

Write-Output ""
Write-Output "=== SUPERSEDED WEIGHTS KEPT-OR-DELETED DETAIL ==="
Get-ChildItem "$runs\rl" -File -Filter '*.npz' | Sort-Object Name | ForEach-Object {
    $mark = if ($_.Name -in $keepw) { 'KEEP  ' } else { 'delete' }
    '  {0} {1,8:n2} MB  {2}' -f $mark, ($_.Length/1MB), $_.Name
}

Write-Output ""
Write-Output "=== TOTALS ==="
Show "TOTAL to delete" ($A + $B + $C + $D + $CK + $W)
Show "KEEP engine" $keep
Show "KEEP eval results" $keep2

Write-Output ""
Write-Output "=== estimated size after cleanup ==="
$all = Get-ChildItem $root -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum
$del = ($A + $B + $C + $D + $CK + $W) | Where-Object { $_ } | ForEach-Object { Get-Item $_ } | Measure-Object Length -Sum
'{0,-46} {1,5} files  {2,12:n2} MB' -f 'repo now', $all.Count, ($all.Sum/1MB)
'{0,-46} {1,5} files  {2,12:n2} MB' -f 'repo after cleanup', ($all.Count - $del.Count), (($all.Sum - $del.Sum)/1MB)
