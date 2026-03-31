param(
  [string]$Time = "08:30",
  [string]$Enabled = "true"
)

$ErrorActionPreference = "Stop"

$taskName = "ContentFactoryDailyReport"
$workspace = "D:\wangmz\Content_Factory"
$scriptPath = Join-Path $workspace "scripts\run-daily-report.mjs"
$nodePath = (Get-Command node).Source

$isEnabled = "$Enabled".ToLower() -in @("1", "true", "$true")

if (-not $isEnabled) {
  $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
  if ($existingTask) {
    Disable-ScheduledTask -TaskName $taskName | Out-Null
  }
  Write-Output "disabled"
  exit 0
}

$runAt = [datetime]::ParseExact($Time, "HH:mm", $null)
$actionCommand = "Set-Location '$workspace'; & '$nodePath' '$scriptPath'"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -Command `$ErrorActionPreference='Stop'; $actionCommand"
$trigger = New-ScheduledTaskTrigger -Daily -At $runAt
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
} else {
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings | Out-Null
}

Enable-ScheduledTask -TaskName $taskName | Out-Null
Write-Output "registered"
