<#
PowerShell helper to run SonarQube locally (docker-compose) and run SonarScanner via Docker.
Usage:
  1. Start SonarQube: .\run_sonar_local.ps1 -Action up
  2. Open http://localhost:9000, login admin/admin, create a token named e.g. 'local-scan'
  3. Run scanner: $env:SONAR_TOKEN = '<TOKEN>'; .\run_sonar_local.ps1 -Action scan
  4. Tear down: .\run_sonar_local.ps1 -Action down

Notes:
 - Requires Docker Desktop installed and running.
 - Uses host.docker.internal so the scanner container can reach Sonar running on host.
 - Adjust paths in sonar-project.properties if needed.
#>

param(
    [ValidateSet('up','scan','down')]
    [string]$Action = 'up'
)

$root = Get-Location
$composeFile = Join-Path $root 'docker-compose.sonar.yml'

function Wait-For-Sonar {
    Param(
        [int]$timeoutSeconds = 300
    )
    $url = 'http://localhost:9000'
    $start = Get-Date
    Write-Host "Waiting for SonarQube to become available at $url..."
    while ((Get-Date) -lt $start.AddSeconds($timeoutSeconds)) {
        try {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            if ($resp.StatusCode -eq 200) {
                Write-Host "SonarQube is up."
                return $true
            }
        } catch {
            Start-Sleep -Seconds 3
        }
    }
    Write-Error "Timed out waiting for SonarQube after $timeoutSeconds seconds. Check docker logs."
    return $false
}

if ($Action -eq 'up') {
    if (-not (Test-Path $composeFile)) {
        Write-Error "Compose file not found: $composeFile"
        exit 1
    }
    Write-Host "Starting SonarQube stack using $composeFile..."
    docker compose -f $composeFile up -d
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to start docker-compose"; exit $LASTEXITCODE }
    if (-not (Wait-For-Sonar -timeoutSeconds 420)) { exit 1 }
    Write-Host "Open http://localhost:9000 in your browser. Default admin/admin. Create a token and then run this script with -Action scan.";
    exit 0
}

if ($Action -eq 'down') {
    if (-not (Test-Path $composeFile)) {
        Write-Error "Compose file not found: $composeFile"
        exit 1
    }
    Write-Host "Stopping SonarQube stack..."
    docker compose -f $composeFile down
    exit 0
}

if ($Action -eq 'scan') {
    if (-not $env:SONAR_TOKEN) {
        Write-Host "SONAR_TOKEN not set. You can set it like: $env:SONAR_TOKEN = '<TOKEN>'";
        $token = Read-Host -AsSecureString "Enter your Sonar token (input hidden)"
        if (-not $token) { Write-Error "No token provided"; exit 1 }
        $ptr = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($token))
        $env:SONAR_TOKEN = $ptr
    }

    # Optional: Generate Python coverage (requires pytest + coverage). Adjust if you use other test runners.
    Write-Host "Generating Python coverage report (if pytest available)..."
    try {
        python -m pip install --user pytest coverage > $null 2>&1
        coverage run -m pytest || Write-Host "pytest returned non-zero or no tests found; continuing"
        coverage xml -o backend/coverage.xml || Write-Host "coverage xml generation failed or coverage not present"
        if (Test-Path backend/coverage.xml) { Write-Host "Python coverage written to backend/coverage.xml" }
    } catch {
        Write-Host "Skipping Python coverage generation: $_"
    }

    # Optional: JS coverage generation -- many projects need custom commands. User should generate lcov manually if available.
    Write-Host "If you have JS coverage (lcov.info), make sure it's at the paths listed in sonar-project.properties (e.g., app/coverage/lcov.info)"

    Write-Host "Running SonarScanner (Docker image). This will mount the current folder into /usr/src in the container."

    $pwdPath = (Get-Location).ProviderPath -replace '\\','/'
    # Use host.docker.internal so scanner can reach Sonar on Windows host
    $dockerCmd = @(
        'run', '--rm',
        '-e', "SONAR_HOST_URL=http://host.docker.internal:9000",
        '-e', "SONAR_LOGIN=$($env:SONAR_TOKEN)",
        '-v', "${pwdPath}:/usr/src",
        '-w', '/usr/src',
        'sonarsource/sonar-scanner-cli',
        '-Dsonar.projectKey=Gustavo-Eduardo_checkers'
    ) -join ' '

    Write-Host "Executing: docker $dockerCmd"
    iex "docker $dockerCmd"
    if ($LASTEXITCODE -ne 0) { Write-Error "SonarScanner failed (exit $LASTEXITCODE)"; exit $LASTEXITCODE }
    Write-Host "Scan complete. Open http://localhost:9000 and search for project 'checkers' (or key Gustavo-Eduardo_checkers)."
    exit 0
}
