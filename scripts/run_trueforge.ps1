$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
New-Item -ItemType Directory -Force -Path '.runtime' | Out-Null
$env:SQLITE_PATH = Join-Path $projectRoot '.runtime\trueforge.sqlite'
$env:HOST = '127.0.0.1'
$env:ACCESS_LOGS = 'false'
$env:OUTBOUND_URL_ALLOWED_HOSTS = '["127.0.0.1"]'
& node 'scripts/run_trueforge.mjs' --port 8790
exit $LASTEXITCODE
