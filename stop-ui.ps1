$ErrorActionPreference = 'Stop'
$appPath = Join-Path $PSScriptRoot 'app.py'
$appPattern = '(?i)(?:^|[\s"])(?:' + [regex]::Escape($appPath) + ')(?=[\s"]|$)'
function Get-UiProcesses {
    @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" |
        Where-Object { $_.CommandLine -match $appPattern })
}
$targets = @(Get-UiProcesses)
if ($targets.Count -eq 0) {
    Write-Host '网页服务已经关闭。'
    return
}
foreach ($target in $targets) {
    $current = Get-CimInstance Win32_Process -Filter "ProcessId = $($target.ProcessId)"
    if ($current -and $current.CommandLine -match $appPattern) {
        Stop-Process -Id $current.ProcessId -ErrorAction SilentlyContinue
    }
}
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    if (@(Get-UiProcesses).Count -eq 0) {
        Write-Host '知识库网页服务已关闭。'
        return
    }
    Start-Sleep -Milliseconds 250
}
throw '网页服务未能完全关闭，请检查进程权限。'
