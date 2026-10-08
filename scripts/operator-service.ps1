param([ValidateSet('Start','Stop','Status')][string]$Action = 'Status')
$ErrorActionPreference = 'Stop'
$operatorRoot = Split-Path -Parent $PSScriptRoot
$operatorFolder = Join-Path $operatorRoot 'local/operator-lab'
$operatorStop = Join-Path $operatorFolder 'stop-service'
$operatorStatus = Join-Path $operatorFolder 'service-status.json'
if ($Action -eq 'Status') {
    if (Test-Path -LiteralPath $operatorStatus) {
        $operatorState = Get-Content -LiteralPath $operatorStatus -Raw | ConvertFrom-Json
        [pscustomobject]@{ SupervisorRunning = [bool](Get-Process -Id $operatorState.supervisor_pid -ErrorAction SilentlyContinue); UpdatedAt = $operatorState.checked_at }
    } else { Write-Output 'Operator service has not started.' }
    exit
}
if ($Action -eq 'Stop') {
    Set-Content -LiteralPath $operatorStop -Value 'operator requested stop'
    if (Test-Path -LiteralPath $operatorStatus) {
        $operatorState = Get-Content -LiteralPath $operatorStatus -Raw | ConvertFrom-Json
        for ($operatorAttempt = 0; $operatorAttempt -lt 15; $operatorAttempt++) {
            if (-not (Get-Process -Id $operatorState.supervisor_pid -ErrorAction SilentlyContinue)) { break }
            Start-Sleep -Seconds 1
        }
        if (Get-Process -Id $operatorState.supervisor_pid -ErrorAction SilentlyContinue) { throw 'Supervisor did not stop; no other process was terminated.' }
    }
    Write-Output 'Owned service stop completed.'
    exit
}
if (Get-NetTCPConnection -State Listen -LocalPort 5681 -ErrorAction SilentlyContinue) { throw 'Port 5681 is occupied; no process was changed.' }
if (Test-Path -LiteralPath $operatorStop) { Remove-Item -LiteralPath $operatorStop }
Start-Process -FilePath (Join-Path $operatorRoot '.venv/Scripts/python.exe') `
    -ArgumentList '-B','scripts/operator_service.py' -WorkingDirectory $operatorRoot -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $operatorFolder 'supervisor.out.log') `
    -RedirectStandardError (Join-Path $operatorFolder 'supervisor.err.log')
Write-Output 'Operator supervisor launch requested; check /readyz and service status.'
