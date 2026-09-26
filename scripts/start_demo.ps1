param([switch]$RestartTrueForge, [switch]$RestartResolver)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$runtimeDir = Join-Path $projectRoot '.runtime'
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

function Start-DemoProcess {
    param([string]$Name, [string]$Executable, [string[]]$ProcessArguments, [int]$Port)
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        if (($Name -eq 'trueforge' -and $RestartTrueForge) -or ($Name -eq 'resolver' -and $RestartResolver)) {
            $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener[0].OwningProcess)"
            $expectedCommand = if ($Name -eq 'trueforge') {
                '(@truefoundry[/\\]trueforge[/\\]dist[/\\]cli\.js|scripts[/\\]run_trueforge\.mjs)'
            } else { '-m app\.cli serve' }
            if ($owner.CommandLine -notmatch $expectedCommand) {
                throw "Port $Port is owned by a different application; it was not stopped."
            }
            $ownedProcess = [System.Diagnostics.Process]::GetProcessById([int]$owner.ProcessId)
            $ownedProcess.Kill()
            $ownedProcess.WaitForExit(5000) | Out-Null
            Start-Sleep -Milliseconds 600
        } else {
            Write-Output "$Name already listening on port $Port."
            return
        }
    }
    $process = Start-Process -FilePath $Executable -ArgumentList $ProcessArguments `
        -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runtimeDir "$Name.stdout.log") `
        -RedirectStandardError (Join-Path $runtimeDir "$Name.stderr.log")
    Set-Content -LiteralPath (Join-Path $runtimeDir "$Name.pid") -Value $process.Id
    Write-Output "$Name started on localhost port $Port (PID $($process.Id))."
}

Start-DemoProcess -Name 'trueforge' -Executable 'node' `
    -ProcessArguments @('scripts/run_trueforge.mjs', '--port', '8790') -Port 8790
Start-DemoProcess -Name 'resolver' -Executable (Join-Path $projectRoot '.venv\Scripts\python.exe') `
    -ProcessArguments @('-m', 'app.cli', 'serve') -Port 8000
