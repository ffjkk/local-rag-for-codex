param([ValidateSet('ingest','search','status','serve')][string]$Action='serve', [string]$Query='')
$env:TEMP="$PSScriptRoot\tmp"
$env:TMP=$env:TEMP
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
& "$PSScriptRoot\.venv\Scripts\python.exe" -B "$PSScriptRoot\rag.py" $Action $Query
exit $LASTEXITCODE
