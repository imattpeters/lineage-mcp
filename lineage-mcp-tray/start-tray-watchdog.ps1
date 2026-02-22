# Lineage MCP Tray Watchdog
# Restarts the tray application if it crashes unexpectedly.
# Exits cleanly only when the tray exits with code 0 (user-initiated close).

$trayPath = Join-Path $PSScriptRoot "lineage_tray"
$scriptName = "Lineage MCP Tray Watchdog"

# Color output
function Write-Info {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $args" -ForegroundColor Cyan
}

function Write-Error {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ERROR: $args" -ForegroundColor Red
}

function Write-Success {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $args" -ForegroundColor Green
}

Write-Info "Starting $scriptName"
Write-Info "Tray module: $trayPath"

$crashCount = 0
$maxConsecutiveCrashes = 10
$crashResetTime = 60  # Reset crash counter after 60 seconds without crashes

while ($true) {
    $lastStartTime = Get-Date
    
    Write-Info "Starting tray application..."
    
    try {
        # Run the tray application and wait for it to exit
        & python -m lineage_tray
        $exitCode = $LASTEXITCODE
        
        $exitTime = Get-Date
        $uptime = ($exitTime - $lastStartTime).TotalSeconds
        
        if ($exitCode -eq 0) {
            Write-Success "Tray exited cleanly (uptime: ${uptime}s)"
            Write-Info "Shutting down watchdog."
            exit 0
        }
        else {
            $crashCount++
            Write-Error "Tray crashed with exit code $exitCode (crashes: $crashCount, uptime: ${uptime}s)"
            
            if ($crashCount -ge $maxConsecutiveCrashes) {
                Write-Error "Too many consecutive crashes ($maxConsecutiveCrashes). Giving up."
                exit 1
            }
            
            Write-Info "Restarting tray in 3 seconds..."
            Start-Sleep -Seconds 3
        }
    }
    catch {
        $crashCount++
        Write-Error "Exception: $_"
        
        if ($crashCount -ge $maxConsecutiveCrashes) {
            Write-Error "Too many consecutive crashes ($maxConsecutiveCrashes). Giving up."
            exit 1
        }
        
        Write-Info "Restarting tray in 3 seconds..."
        Start-Sleep -Seconds 3
    }
    
    # Reset crash counter if enough time has passed since last start
    $nowTime = Get-Date
    if (($nowTime - $lastStartTime).TotalSeconds -gt $crashResetTime) {
        if ($crashCount -gt 0) {
            Write-Info "Resetting crash counter after ${crashResetTime}s without issues"
            $crashCount = 0
        }
    }
}
