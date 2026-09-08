param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$env:TEMP="$PSScriptRoot\tmp"
$env:TMP=$env:TEMP
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$python=Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe'
try { $ready=Invoke-RestMethod 'http://127.0.0.1:8765/api/status' -TimeoutSec 2 } catch { $ready=$null }
if (-not $ready) {
    Start-Process -FilePath $python -ArgumentList @('-B',('"'+$PSScriptRoot+'\app.py"')) -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput "$PSScriptRoot\data\ui.stdout.log" -RedirectStandardError "$PSScriptRoot\data\ui.stderr.log"
    for ($attempt=0;$attempt -lt 30;$attempt++) {
        Start-Sleep -Milliseconds 500
        try { $ready=Invoke-RestMethod 'http://127.0.0.1:8765/api/status' -TimeoutSec 1; break } catch {}
    }
}
if ($ready) {
    if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:8765' }
    Write-Host '知识库网页服务已就绪。'
} else { throw '启动失败，请查看 data\ui.stderr.log' }
