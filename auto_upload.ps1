# Money Machine Auto-Uploader
# ============================
# Runs the batch uploader to push rendered videos to YouTube as PRIVATE.
# Designed for Windows Task Scheduler — runs every 4 hours.
# Handles: daily upload limits, token refresh, logging.
#
# Kill switch: Create C:\money-machine\PAUSE to stop all automation.

$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = "utf-8"

$root = "C:\money-machine"
$logDir = "$root\logs"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "$logDir\upload_$timestamp.log"

# Ensure log directory exists
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

# Kill switch check
if (Test-Path "$root\PAUSE") {
    "$(Get-Date -Format 'HH:mm:ss') PAUSED - remove C:\money-machine\PAUSE to resume" | Out-File -FilePath $logFile -Encoding utf8
    exit 0
}

# Run the uploader
"$(Get-Date -Format 'HH:mm:ss') Starting auto-upload..." | Out-File -FilePath $logFile -Encoding utf8

$process = Start-Process -FilePath "python" `
    -ArgumentList "$root\render_and_upload.py --once" `
    -WorkingDirectory $root `
    -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput "$logFile.stdout" `
    -RedirectStandardError "$logFile.stderr"

# Combine logs
if (Test-Path "$logFile.stdout") { Get-Content "$logFile.stdout" | Add-Content $logFile }
if (Test-Path "$logFile.stderr") { Get-Content "$logFile.stderr" | Add-Content $logFile }
Remove-Item "$logFile.stdout","$logFile.stderr" -ErrorAction SilentlyContinue

"$(Get-Date -Format 'HH:mm:ss') Done. Exit code: $($process.ExitCode)" | Add-Content $logFile
