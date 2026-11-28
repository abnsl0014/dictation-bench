# timeout=600   download + silent-install Wispr Flow MSI, launch, screenshot, list sign-in UI + protocols
$ErrorActionPreference = 'Continue'
$msi = "$env:RUNNER_TEMP\WisprFlow.msi"
Invoke-WebRequest "https://dl.wisprflow.ai/windows/msi/latest" -OutFile $msi -UseBasicParsing -MaximumRedirection 5
"msi size: $((Get-Item $msi).Length)"
$p = Start-Process msiexec.exe -ArgumentList '/i', "`"$msi`"", '/qn', '/l*v', "$env:RUNNER_TEMP\wispr-install.log" -PassThru -Wait
"msiexec exit: $($p.ExitCode)"
$exe = Get-ChildItem 'C:\Program Files (x86)\Wispr Flow','C:\Program Files\Wispr Flow',"$env:LOCALAPPDATA\Programs" -Recurse -Filter '*.exe' -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'Wispr' -and $_.Name -notmatch 'Uninstall|crash|setup' } | Select-Object -First 1
"exe: $($exe.FullName)"
"== registered URL protocols that mention wispr/flow"
Get-ChildItem 'Registry::HKEY_CLASSES_ROOT' -ErrorAction SilentlyContinue | Where-Object { $_.PSChildName -match 'wispr|flow' } | ForEach-Object {
  $u = (Get-ItemProperty "Registry::$($_.Name)" -ErrorAction SilentlyContinue).'URL Protocol'
  "$($_.PSChildName)  (URL Protocol: $([bool]($u -ne $null)))"
}
if ($exe) { Start-Process $exe.FullName; Start-Sleep 30 }
Add-Type -AssemblyName System.Windows.Forms
Get-Process | Where-Object { $_.MainWindowTitle } | Format-Table ProcessName, MainWindowTitle -AutoSize | Out-String -Width 200
python vm/shot.py wispr_app_launch 2>&1
