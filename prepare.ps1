$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Get-Command python -ErrorAction Stop

if (-not (Test-Path (Join-Path $root '.venv'))) {
    & $python.Source -m venv (Join-Path $root '.venv')
}

$venvPython = Join-Path $root '.venv\Scripts\python.exe'
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $root 'requirements.lock.txt')
& $venvPython -B (Join-Path $root 'prepare_model.py')

Write-Host 'Environment and embedding model are ready.'
