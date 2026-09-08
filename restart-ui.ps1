param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'stop-ui.ps1')
& (Join-Path $PSScriptRoot 'start-ui.ps1') -NoBrowser:$NoBrowser
Write-Host '知识库网页服务已重启，请刷新已有页面（Ctrl+F5）。'
