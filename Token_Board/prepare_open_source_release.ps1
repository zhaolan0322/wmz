param(
    [string]$OutputRoot = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $OutputRoot) {
    $OutputRoot = Join-Path $ProjectRoot "open-source-dist"
}

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ExportRoot = Join-Path $OutputRoot "Token_Board-open-source-$Stamp"
$ZipPath = "$ExportRoot.zip"

New-Item -ItemType Directory -Path $ExportRoot -Force | Out-Null

$ExcludeTop = @(
    ".venv",
    "__pycache__",
    "logs",
    "data",
    "open-source-dist",
    "start_star_office_mishu.cmd",
    "PROGRESS.md",
    "开发计划.md",
    "启动说明.md",
    "同步容器数据说明.md"
)

Get-ChildItem -Force $ProjectRoot | ForEach-Object {
    if ($ExcludeTop -contains $_.Name) {
        return
    }
    Copy-Item $_.FullName -Destination (Join-Path $ExportRoot $_.Name) -Recurse -Force
}

New-Item -ItemType Directory -Path (Join-Path $ExportRoot "data") -Force | Out-Null
Copy-Item (Join-Path $ProjectRoot "data\sample_sessions.json") (Join-Path $ExportRoot "data\sample_sessions.json") -Force
Copy-Item (Join-Path $ProjectRoot "data\README.md") (Join-Path $ExportRoot "data\README.md") -Force

if (Test-Path (Join-Path $ExportRoot "start_star_office_mishu.cmd")) {
    Remove-Item (Join-Path $ExportRoot "start_star_office_mishu.cmd") -Force
}
Copy-Item (Join-Path $ProjectRoot "start_star_office.example.cmd") (Join-Path $ExportRoot "start_star_office.example.cmd") -Force

Get-ChildItem -Path $ExportRoot -File -Filter "*.md" |
    Where-Object { $_.Name -notin @("README.md", "OPEN_SOURCE_RELEASE.md") } |
    ForEach-Object { Remove-Item $_.FullName -Force }

$VendorRoot = Join-Path $ExportRoot "vendor\Star-Office-UI"
$VendorRemove = @(
    ".git",
    ".venv",
    "agents-state.json",
    "asset-defaults.json",
    "asset-positions.json",
    "join-keys.json",
    "runtime-config.json",
    "state.json",
    "assets\bg-history",
    "assets\home-favorites",
    "backend\__pycache__"
)
foreach ($Item in $VendorRemove) {
    $Path = Join-Path $VendorRoot $Item
    if (Test-Path $Path) {
        Remove-Item $Path -Recurse -Force
    }
}

Get-ChildItem -Path $ExportRoot -Recurse -Force -Directory |
    Where-Object { $_.Name -in @("__pycache__") } |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force }

Get-ChildItem -Path $ExportRoot -Recurse -Force -File |
    Where-Object { $_.Extension -in @(".pyc", ".pyo", ".log", ".out", ".err") } |
    ForEach-Object { Remove-Item $_.FullName -Force }

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
Compress-Archive -Path (Join-Path $ExportRoot "*") -DestinationPath $ZipPath -Force

Write-Host "Open-source export ready:"
Write-Host "  Folder: $ExportRoot"
Write-Host "  Zip:    $ZipPath"
