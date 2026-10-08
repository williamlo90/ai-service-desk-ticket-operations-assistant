param(
    [ValidateSet('prepare','start-db','start-n8n','status','stop-db','stop-n8n','restart-db')]
    [string]$Action = 'status'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
# Outside the synced project; never load the Jira .env.
$secretDir = Join-Path $env:LOCALAPPDATA 'ServiceDeskLab/secrets'
$env:SERVICE_DESK_SECRET_DIR = $secretDir.Replace('\','/')
$composeArgs = @('compose','--env-file',(Join-Path $projectRoot 'deploy/compose.empty.env'),'-f',(Join-Path $projectRoot 'deploy/compose.yaml'),'-p','service-desk-lab')
if ($Action -eq 'prepare') {
    $existingVolumes = @(docker volume ls --format '{{.Name}}')
    if ($LASTEXITCODE -ne 0) { throw 'Docker engine unavailable.' }
    $requiredExisting = @()
    if ($existingVolumes -contains 'service-desk-lab_postgres_data') { $requiredExisting += @('db_admin','db_app','db_n8n') }
    if ($existingVolumes -contains 'service-desk-lab_n8n_data') { $requiredExisting += 'n8n_key' }
    foreach ($name in $requiredExisting) {
        if (-not (Test-Path -LiteralPath (Join-Path $secretDir $name) -PathType Leaf)) {
            throw 'Existing data volume found but original local secrets are missing. Restore secrets; do not regenerate.'
        }
    }
    New-Item -ItemType Directory -Force -Path $secretDir | Out-Null
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    & icacls $secretDir /inheritance:r /grant:r "${identity}:(OI)(CI)F" 'SYSTEM:(OI)(CI)F' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Cannot restrict secret directory permissions.' }
    foreach ($name in @('db_admin','db_app','db_n8n','n8n_key')) {
        $target = Join-Path $secretDir $name
        if (-not (Test-Path -LiteralPath $target)) {
            $bytes = New-Object byte[] 32
            $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
            try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
            $password = [Convert]::ToBase64String($bytes)
            [IO.File]::WriteAllText($target, $password, (New-Object Text.UTF8Encoding($false)))
            $password = $null
        }
    }
    & python -B (Join-Path $PSScriptRoot 'prepare_database_secrets.py')
    if ($LASTEXITCODE -ne 0) { throw 'Cannot prepare database secret volume.' }
    & docker @composeArgs config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Compose validation failed.' }
    Write-Output 'Prepared isolated database secrets and validated Compose. No secret values printed.'
    exit 0
}
if ($Action -eq 'start-db') {
    foreach ($name in @('db_admin','db_app','db_n8n')) {
        if (-not (Test-Path -LiteralPath (Join-Path $secretDir $name))) { throw 'Run prepare first.' }
    }
    $running = & docker @composeArgs ps --status running --services db
    if ($running -ne 'db') {
        & $PSScriptRoot/check_docker_readiness.ps1 -Mode database
        if ($LASTEXITCODE -ne 0) { throw 'Database startup readiness check failed.' }
    }
    & docker @composeArgs up -d --wait --wait-timeout 60 db
} elseif ($Action -eq 'start-n8n') {
    $healthy = docker inspect --format '{{.State.Health.Status}}' service-desk-lab-db-1 2>$null
    if ($LASTEXITCODE -ne 0 -or $healthy -ne 'healthy') { throw 'Start and verify the database first.' }
    $running = & docker @composeArgs ps --status running --services n8n
    if ($running -ne 'n8n') {
        & $PSScriptRoot/check_docker_readiness.ps1 -Mode n8n
        if ($LASTEXITCODE -ne 0) { throw 'n8n startup readiness check failed.' }
    }
    & docker @composeArgs up -d --no-deps --wait --wait-timeout 120 n8n
} elseif ($Action -eq 'stop-n8n') {
    & docker @composeArgs stop n8n
} elseif ($Action -eq 'stop-db') {
    & docker @composeArgs stop db
} elseif ($Action -eq 'restart-db') {
    & docker @composeArgs restart db
} else {
    & docker @composeArgs ps
}
if ($LASTEXITCODE -ne 0) { throw 'Runtime operation failed.' }
