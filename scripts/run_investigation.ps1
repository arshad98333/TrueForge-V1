$ErrorActionPreference = 'Stop'
& "$PSScriptRoot\start_demo.ps1" -RestartResolver
Start-Sleep -Seconds 2
& '.venv\Scripts\python.exe' -m app.cli configure-runtime
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& '.venv\Scripts\python.exe' -m app.cli start
exit $LASTEXITCODE
