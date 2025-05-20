# deploy-all.ps1
# Usage: Right-click and run with PowerShell

# ---------- Enhanced Configuration Section ----------
$DEPLOY_DIR = Join-Path $PSScriptRoot "deploy"  # Use absolute path
$KUBECTL_CMD = "kubectl"
$MAX_RETRIES = 2  # Retry mechanism
# ----------------------------------------------------

# Enhanced initialization check
function Initialize-Check {
    if (-not (Test-Path $DEPLOY_DIR)) {
        Write-Host "Error: Deployment directory not found: $DEPLOY_DIR" -ForegroundColor Red
        Write-Host "Hint: Ensure deployment directory is at the same level as script" -ForegroundColor Yellow
        Read-Host "Press Enter to exit..."
        exit 1
    }

    # Verify kubectl availability
    try {
        & $KUBECTL_CMD version --client 2>&1 | Out-Null
    } catch {
        Write-Host "Error: kubectl executable not found" -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
}

# Enhanced deployment function
function Deploy-Component {
    param(
        [string]$Type,
        [string]$Name,
        [string]$DirPath
    )

    $retryCount = 0
    while ($retryCount -lt $MAX_RETRIES) {
        try {
            Write-Host "Deploying $Type`: $Name" -ForegroundColor Cyan
            & $KUBECTL_CMD apply -f $DirPath 2>&1 | Tee-Object -Variable output
            if ($LASTEXITCODE -ne 0) {
                throw "kubectl apply failed"
            }
            return
        } catch {
            $retryCount++
            Write-Host "[Retry $retryCount/$MAX_RETRIES] $Type $Name deployment error: $_" -ForegroundColor Yellow
            Write-Host "Error details: $output" -ForegroundColor DarkYellow
            Start-Sleep -Seconds 3
        }
    }

    Write-Host "$Type $Name deployment failed!" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 2
}

# ---------- Main Execution Flow ----------
Initialize-Check

# Deploy middleware
$middlewares = @("mysql", "nats", "redis")
foreach ($mw in $middlewares) {
    $dir = Join-Path $DEPLOY_DIR "middlewares\$mw"
    if (-not (Test-Path $dir)) {
        Write-Host "Skipping non-existent middleware: $mw" -ForegroundColor Yellow
        continue
    }
    
    Deploy-Component -Type "Middleware" -Name $mw -DirPath $dir
}

# Deploy microservices
$services = @("cart", "checkout", "email", "frontend", "order", "payment", "product", "user")
$serviceJobs = @()

foreach ($svc in $services) {
    $dir = Join-Path $DEPLOY_DIR "services\$svc"
    if (-not (Test-Path $dir)) {
        Write-Host "Skipping non-existent service: $svc" -ForegroundColor Yellow
        continue
    }
    
    $jobScript = {
        param($dir, $retries)
        $attempt = 0
        do {
            $output = & kubectl apply -f $dir 2>&1
            if ($LASTEXITCODE -eq 0) { return 0 }
            $attempt++
            Start-Sleep -Seconds 2
        } while ($attempt -lt $retries)
        Write-Host "Final failure: $dir" -ForegroundColor Red
        return 1
    }
    
    $job = Start-Job -ScriptBlock $jobScript -ArgumentList $dir, $MAX_RETRIES
    $serviceJobs += @{ Name=$svc; Job=$job }
}

# Monitor deployment progress
while ($serviceJobs.Count -gt 0) {
    $completed = @()
    foreach ($item in $serviceJobs) {
        if ($item.Job.State -eq "Completed") {
            $result = Receive-Job $item.Job
            if ($result -eq 0) {
                Write-Host "Service $($item.Name) deployed successfully" -ForegroundColor Green
            } else {
                Write-Host "Service $($item.Name) deployment failed!" -ForegroundColor Red
                $failed += $item.Name
            }
            Remove-Job $item.Job
            $completed += $item
        }
    }
    $serviceJobs = $serviceJobs | Where-Object { $_ -notin $completed }
    Start-Sleep -Seconds 1
}

# Final status report
if ($failed.Count -gt 0) {
    Write-Host "Failed services: $($failed -join ', ')" -ForegroundColor Red
    Write-Host "Troubleshooting steps:"
    Write-Host "1. Check YAML syntax for failed services"
    Write-Host "2. Run kubectl describe pod/<pod-name> for details"
    Write-Host "3. Verify cluster resource availability (CPU/Memory)"
} else {
    Write-Host "All components deployed successfully!" -ForegroundColor Green
    Write-Host "Monitoring commands:"
    Write-Host "kubectl get pods -w" -ForegroundColor Cyan
    Write-Host "kubectl get svc" -ForegroundColor Cyan
}

Read-Host "Press Enter to exit..."
