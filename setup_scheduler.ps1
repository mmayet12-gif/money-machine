# setup_scheduler.ps1 — Register the Money Machine upload scheduler
# Run this in an elevated (admin) PowerShell, or as your normal user if you
# don't need "run whether logged in or not" (we don't).
#
# Usage:  powershell -ExecutionPolicy Bypass -File C:\money-machine\setup_scheduler.ps1

$TaskName = "MoneyMachineUploader"
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) { $PythonExe = "python" }

$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "C:\money-machine\scheduler.py" `
    -WorkingDirectory "C:\money-machine"

$Trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).Date.AddHours(9) `
    -RepetitionInterval (New-TimeSpan -Minutes 15) `
    -RepetitionDuration (New-TimeSpan -Days 9999)

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -RestartCount 1 `
    -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Uploads scheduled YouTube videos from the Money Machine queue every 15 minutes."

Write-Host ""
Write-Host "Task '$TaskName' registered successfully." -ForegroundColor Green
Write-Host ""
Write-Host "Verify:   Get-ScheduledTask -TaskName $TaskName"
Write-Host "Disable:  Disable-ScheduledTask -TaskName $TaskName"
Write-Host "Enable:   Enable-ScheduledTask -TaskName $TaskName"
Write-Host "Remove:   Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
Write-Host "Run now:  Start-ScheduledTask -TaskName $TaskName"
