# Downloads the GitHub branch's exact exported PDF files, never regenerates graphs.
# Requires PowerShell 5.1+ and an Internet connection; no Python packages needed.
$ErrorActionPreference = 'Stop'
$repo='wran021004-gif/softrobot-demo-showcase'
$branch='codex/paper-figures-spring-button-20261111'
$assets = Get-Content (Join-Path $PSScriptRoot 'original_assets_manifest.json') -Raw | ConvertFrom-Json
foreach ($item in $assets.assets) {
  $name=$item.file_name
  $url="https://raw.githubusercontent.com/$repo/$branch/$($item.source_path)"
  $path=Join-Path $PSScriptRoot $name
  Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $path
  # Git blob SHA-1 is SHA1("blob <size>\0" + raw file bytes), not ordinary file SHA-1.
  $bytes=[System.IO.File]::ReadAllBytes($path)
  $prefix=[System.Text.Encoding]::ASCII.GetBytes("blob $($bytes.Length)`0")
  $payload=New-Object byte[] ($prefix.Length+$bytes.Length)
  [Array]::Copy($prefix,0,$payload,0,$prefix.Length)
  [Array]::Copy($bytes,0,$payload,$prefix.Length,$bytes.Length)
  $hasher=[System.Security.Cryptography.SHA1]::Create()
  $hash=[System.BitConverter]::ToString($hasher.ComputeHash($payload)).Replace('-','').ToLowerInvariant()
  if ($hash -ne $item.git_blob_sha1) { throw "BLOB_HASH_MISMATCH for $name ($hash vs $($item.git_blob_sha1))" }
  Write-Host "Verified $name ($($bytes.Length) bytes)"
}
Write-Host 'All original exported PDFs verified. Upload them in the Overleaf figures/ folder.'
