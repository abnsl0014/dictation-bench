# timeout=1500   Root-cause check with full page heap: public 0.5.11 (page heap x3 + Run anyway x4) and 0.5.10 (page heap x3). Both are expected to crash under page heap.
$ErrorActionPreference = 'Continue'
$dl = "$env:USERPROFILE\Downloads"; New-Item -ItemType Directory -Force $dl | Out-Null
foreach ($v in '0.5.11', '0.5.10') {
  $f = Join-Path $dl "Blip-AI-Setup-$v.exe"
  if (-not (Test-Path $f)) { Invoke-WebRequest "https://github.com/abnsl0014/blipai-releases/releases/download/v$v/Blip-AI-Setup-$v.exe" -OutFile $f -UseBasicParsing }
}
"===== 0.5.11 (current public build)"
pwsh -NoProfile -File vm/windowsInstallTest.ps1 -Installer "$dl\Blip-AI-Setup-0.5.11.exe" -PageHeapRuns 3 -RunAnywayRuns 4 -SkipInstall -OutDir "$env:WISPR_VM_OUT\t0511"
"exit $LASTEXITCODE"
"===== 0.5.10 (previous public build)"
pwsh -NoProfile -File vm/windowsInstallTest.ps1 -Installer "$dl\Blip-AI-Setup-0.5.10.exe" -PageHeapRuns 3 -RunAnywayRuns 0 -SkipInstall -OutDir "$env:WISPR_VM_OUT\t0510"
"exit $LASTEXITCODE"
