param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$ArgsList
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$entry = Join-Path $scriptDir "money-machine.py"

if (Get-Command py -ErrorAction SilentlyContinue) {
  & py $entry @ArgsList
  exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
  & python $entry @ArgsList
  exit $LASTEXITCODE
}

Write-Error "No Python launcher found. Install Python or run with available interpreter."
exit 1
