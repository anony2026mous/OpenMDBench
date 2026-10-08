param([Parameter(ValueFromRemainingArguments = $true)][string[]]$CliArgs)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$candidates = @(
    $env:HUAIROU_LOCAL_PYTHON,
    (Join-Path $root 'source_codes/.venv/Scripts/python.exe'),
    (Join-Path $env:USERPROFILE '.conda/envs/llamafactory/python.exe')
)
$python = $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if (!$python) { throw 'Set HUAIROU_LOCAL_PYTHON to a local Python 3.10+ executable.' }
& $python (Join-Path $PSScriptRoot 'remote.py') @CliArgs
exit $LASTEXITCODE
