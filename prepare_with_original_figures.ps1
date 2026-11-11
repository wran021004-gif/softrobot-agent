# One-step Windows workflow: download exact GitHub-exported figures and package a ready-to-import Overleaf ZIP.
# Run from the extracted source project root:
#   powershell -ExecutionPolicy Bypass -File .\prepare_with_original_figures.ps1
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'figures\download_original_figures.ps1')
$output = Join-Path (Split-Path $PSScriptRoot -Parent) 'softrobot_agent_overleaf_v0_4_original_figures.zip'
if (Test-Path $output) { Remove-Item -LiteralPath $output -Force }
Push-Location $PSScriptRoot
try {
  $paths=@('main.tex','references.bib','sections','appendices','figures','tables')
  foreach ($path in $paths) { if (!(Test-Path $path)) { throw "Missing required project entry $path" } }
  Compress-Archive -Path $paths -DestinationPath $output -CompressionLevel Optimal -Force
} finally { Pop-Location }
Write-Host "Ready for Overleaf: $output"
