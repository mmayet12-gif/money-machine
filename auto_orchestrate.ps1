# Money Machine Auto-Orchestrator
# ================================
# Runs the orchestrator to produce the next batch of videos.
# Designed to be called by Windows Task Scheduler weekly.
#
# Install: Run setup_auto_orchestrate.ps1 (below) as admin
# Manual:  powershell -File C:\money-machine\auto_orchestrate.ps1

$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = "utf-8"

$root = "C:\money-machine"
$logFile = "$root\output\logs\orchestrator_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Kill switch
if (Test-Path "$root\PAUSE") {
    "$(Get-Date -Format 'HH:mm:ss') PAUSED - remove C:\money-machine\PAUSE to resume" | Out-File -FilePath $logFile -Encoding utf8
    exit 0
}

# Run orchestrator
"$(Get-Date -Format 'HH:mm:ss') Starting orchestrator..." | Out-File -FilePath $logFile -Encoding utf8
$process = Start-Process -FilePath "python" -ArgumentList "$root\orchestrator.py --batch 20" -WorkingDirectory $root -NoNewWindow -Wait -PassThru -RedirectStandardOutput "$logFile.stdout" -RedirectStandardError "$logFile.stderr"

# Combine logs
if (Test-Path "$logFile.stdout") { Get-Content "$logFile.stdout" | Add-Content $logFile }
if (Test-Path "$logFile.stderr") { Get-Content "$logFile.stderr" | Add-Content $logFile }
Remove-Item "$logFile.stdout","$logFile.stderr" -ErrorAction SilentlyContinue

"$(Get-Date -Format 'HH:mm:ss') Done. Exit code: $($process.ExitCode)" | Add-Content $logFile
