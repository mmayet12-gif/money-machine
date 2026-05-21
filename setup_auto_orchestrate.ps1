# Setup Auto-Orchestrator Scheduled Task
# ========================================
# Run this script AS ADMIN to register the weekly orchestrator task.
#
# Schedule: Every Sunday at 02:00 (renders overnight for Mon/Wed/Fri uploads)

$taskName = "MoneyMachine_Orchestrator"
$scriptPath = "C:\money-machine\auto_orchestrate.ps1"

# Remove existing task if present
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# Create trigger: Weekly on Sunday at 2:00 AM
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "02:00"

# Action: Run PowerShell with the orchestrator script
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$scriptPath`"" -WorkingDirectory "C:\money-machine"

# Settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 6)

# Register
Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action -Settings $settings -Description "Money Machine: weekly batch video generation across top niches" -RunLevel Highest

Write-Host ""
Write-Host "Task '$taskName' registered successfully!" -ForegroundColor Green
Write-Host "  Schedule: Every Sunday at 02:00"
Write-Host "  Action:   Generates 20 videos in the top-scoring niche"
Write-Host "  Timeout:  6 hours max"
Write-Host "  Kill:     Create C:\money-machine\PAUSE to stop"
Write-Host ""
Write-Host "To run manually: powershell -File $scriptPath"
Write-Host "To check status: Get-ScheduledTask -TaskName '$taskName'"
