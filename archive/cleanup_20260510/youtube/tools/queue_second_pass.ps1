param(
  [string]$RunId = "full_run_01",
  [string]$WorkDir = "C:\money-machine\youtube"
)

$log1 = Join-Path $WorkDir "runs\$RunId\videos\render_all.log"
$err1 = Join-Path $WorkDir "runs\$RunId\videos\render_all.err.log"
$log2 = Join-Path $WorkDir "runs\$RunId\videos\render_s4plus.log"
$err2 = Join-Path $WorkDir "runs\$RunId\videos\render_s4plus.err.log"

New-Item -ItemType Directory -Force (Join-Path $WorkDir "runs\$RunId\videos") | Out-Null

# Wait for first-pass marker. If no log appears, continue after timeout.
$deadline = (Get-Date).AddHours(6)
while ((Get-Date) -lt $deadline) {
  if (Test-Path $log1) {
    $tail = Get-Content $log1 -Tail 10 -ErrorAction SilentlyContinue
    if ($tail -match "Done\. Rendered") {
      break
    }
  }
  Start-Sleep -Seconds 30
}

Push-Location $WorkDir
try {
  python .\tools\render_mp4_from_scripts.py --run-id $RunId --streams S4,S5,S6,S7,S8 *> $log2 2> $err2
}
finally {
  Pop-Location
}
