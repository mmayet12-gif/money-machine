# Money Machine — Daily Workflow

## Rendering Videos

```
cd C:\money-machine

# Check environment
python run_pipeline.py --check

# Generate scripts (if starting fresh)
python generate_scripts.py --template

# Render all videos
python run_pipeline.py

# Render just one
python run_pipeline.py --only 5

# Re-render a failed one
python run_pipeline.py --redo 3
```

## Uploading & Scheduling

### One-time setup

1. Complete the OAuth setup: read `OAUTH_SETUP.md` and follow every step.
2. Verify: `python youtube_uploader.py --whoami`
3. Install the scheduler: run `setup_scheduler.ps1` in PowerShell.

### Daily workflow

1. **Render videos** as above.
2. **Add to queue**:
   ```
   python queue_manager.py auto-fill output\videos
   ```
3. **Review** the schedule it prints. Type `y` to confirm.
4. **Wait.** The scheduler runs every 15 minutes and uploads due videos.
5. **Get notified.** A Windows toast pops up: "Uploaded: \<title\>". Click it.
6. **Review in YouTube Studio:**
   - Confirm the video plays correctly
   - Check title, description, tags
   - Upload a custom thumbnail
   - Change visibility from Private to **Public**

### Managing the queue

```
# See what's scheduled
python queue_manager.py list

# See everything including uploaded/failed
python queue_manager.py list --all

# Cancel a queued video
python queue_manager.py remove <id>

# Reschedule one
python queue_manager.py reschedule <id> --at "2026-05-15 09:00"

# Check next available slot
python queue_manager.py next-slot --kind long_form
python queue_manager.py next-slot --kind short

# Upload one video manually (bypasses the scheduler)
python youtube_uploader.py --upload output\videos\01_xxx.mp4
python youtube_uploader.py --upload output\videos\01_xxx.mp4 --dry-run
```

### Upload cadence

| Kind | Days | Window | Limit |
|------|------|--------|-------|
| Long-form | Mon / Wed / Fri | 09:00–18:00 | Min 24h between uploads |
| Shorts | Any day | 09:00–21:00 | Max 1 per calendar day |

The queue manager auto-picks slots respecting these rules.

## Panic Button

Create the file `C:\money-machine\PAUSE` to stop all uploads:

```
echo. > C:\money-machine\PAUSE
```

The scheduler checks for this file before doing anything. Uploads stop
within 15 minutes.

To resume, delete the file:

```
del C:\money-machine\PAUSE
```

## Scheduler Management

```powershell
# Check status
Get-ScheduledTask -TaskName MoneyMachineUploader

# Temporarily disable
Disable-ScheduledTask -TaskName MoneyMachineUploader

# Re-enable
Enable-ScheduledTask -TaskName MoneyMachineUploader

# Run immediately (for testing)
Start-ScheduledTask -TaskName MoneyMachineUploader

# Remove entirely
Unregister-ScheduledTask -TaskName MoneyMachineUploader -Confirm:$false
```
