param([ValidateSet('full','database','n8n')][string]$Mode = 'full')
$ErrorActionPreference = 'Stop'
# Read-only checks. Does not read .env, start/stop containers or change WSL.
$projectRoot = Split-Path $PSScriptRoot -Parent
try {
    $dockerData = docker info --format '{{json .}}' 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Engine unavailable' }
    $engine = $dockerData | ConvertFrom-Json
    $compose = docker compose version --short 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Compose unavailable' }
    $os = Get-CimInstance Win32_OperatingSystem
    $freeGiB = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
    $ports = if ($Mode -eq 'database') { @(5433) } elseif ($Mode -eq 'n8n') { @(5678) } else { @(5678,5433) }
    $minimumFree = if ($Mode -in @('database','n8n')) { 1 } else { 4 }
    $guestAvailable = $null
    if ($Mode -eq 'n8n') {
        # Read the Linux VM's global memory through our already-running database.
        # This is not the database container's cgroup allowance, nor additive to host RAM.
        $memoryLines = docker exec service-desk-lab-db-1 cat /proc/meminfo 2>$null
        if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect Linux memory.' }
        $availableLine = $memoryLines | Where-Object { $_ -match '^MemAvailable:\s+(\d+)\s+kB' }
        if (-not $availableLine) { throw 'Linux memory data missing.' }
        $guestAvailable = [math]::Round([double]([regex]::Match($availableLine, '\d+').Value) / 1MB, 2)
    }
    $portConflicts = @(Get-NetTCPConnection -State Listen -LocalPort $ports -ErrorAction SilentlyContinue | Select-Object -ExpandProperty LocalPort -Unique)
    $ready = $engine.OSType -eq 'linux' -and $freeGiB -ge $minimumFree -and $portConflicts.Count -eq 0
    if ($Mode -eq 'n8n') { $ready = $ready -and $guestAvailable -ge 2 }
    $report = [ordered]@{
        checked_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
        docker_engine = $engine.ServerVersion
        compose = $compose
        platform = $engine.OSType
        engine_memory_gib = [math]::Round($engine.MemTotal / 1GB, 2)
        host_free_memory_gib = $freeGiB
        linux_available_memory_gib = $guestAvailable
        running_containers_at_sample = $engine.ContainersRunning
        mode = $Mode
        required_host_free_memory_gib = $minimumFree
        port_conflicts = $portConflicts
        ready_to_start_prototype = $ready
        note = 'Project guards, not vendor minima: full stack 4 GiB host; staged DB 1 GiB host / 512 MiB cap; staged n8n 1 GiB host AND 2 GiB Linux available / 1 GiB cap. Host and guest values overlap; never add them. No services changed by this check.'
    }
    $report | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $projectRoot 'docs/phase-0/docker-readiness.json') -Encoding utf8
    $report | ConvertTo-Json -Depth 3
    if (-not $ready) { exit 2 }
}
catch {
    Write-Output 'Docker readiness check failed; engine or local inspection unavailable.'
    exit 1
}
