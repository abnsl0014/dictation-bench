# timeout=1800   Final check of what customers download now: the public v0.5.11 Windows installer (fixed build), page heap x6, SmartScreen Run anyway x8, full install + signature check.
$ErrorActionPreference = 'Continue'
$dl = "$env:USERPROFILE\Downloads"; New-Item -ItemType Directory -Force $dl | Out-Null
$f = Join-Path $dl 'Blip-AI-Setup-0.5.11.exe'
Invoke-WebRequest 'https://github.com/abnsl0014/blipai-releases/releases/download/v0.5.11/Blip-AI-Setup-0.5.11.exe' -OutFile $f -UseBasicParsing
"sha256: $((Get-FileHash $f).Hash)   size: $((Get-Item $f).Length)"
pwsh -NoProfile -File vm/windowsInstallTest.ps1 -Installer $f -PageHeapRuns 6 -RunAnywayRuns 8 -ExpectSigned -OutDir "$env:WISPR_VM_OUT\public"
"exit $LASTEXITCODE"
