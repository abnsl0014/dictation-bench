# timeout=300   Blip AI after install (attempt 2): still running? every binary signed? Windows errors? app windows and logs
$ErrorActionPreference = 'Continue'
Start-Sleep 30
$dir = "$env:LOCALAPPDATA\Programs\blip-ai"
"install dir exists: $(Test-Path $dir)"
Get-ChildItem $dir -ErrorAction SilentlyContinue | Format-Table Name, Length -AutoSize | Out-String -Width 200
"== Blip processes (about 1 minute after launch)"
Get-Process | Where-Object { $_.ProcessName -match 'Blip' } | Format-Table Id, ProcessName, StartTime, @{n='MB';e={[int]($_.WorkingSet64/1MB)}}, MainWindowTitle -AutoSize | Out-String -Width 200
"== signatures of every .exe/.dll/.node"
$files = Get-ChildItem $dir -Recurse -Include *.exe, *.dll, *.node -ErrorAction SilentlyContinue
$bad = foreach ($f in $files) { $s = Get-AuthenticodeSignature $f.FullName; if ($s.Status -ne 'Valid') { "$($f.FullName.Replace($dir, '')) : $($s.Status)" } }
"checked $($files.Count) files; not validly signed: $(@($bad).Count)"
$bad
"== shortcuts"
"desktop: $(Test-Path "$env:USERPROFILE\Desktop\Blip AI.lnk")   start menu: $(Test-Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Blip AI.lnk")"
"== Windows Application log errors mentioning Blip (last 30 min)"
Get-WinEvent -FilterHashtable @{ LogName = 'Application'; StartTime = (Get-Date).AddMinutes(-30) } -ErrorAction SilentlyContinue |
  Where-Object { $_.Message -match 'Blip' -and $_.Level -le 2 } | Format-List TimeCreated, Id, ProviderName, Message | Out-String -Width 300
"== app log files (last 80 lines each)"
foreach ($d in "$env:APPDATA\blip-ai", "$env:APPDATA\Blip-AI", "$env:APPDATA\Blip AI") {
  if (Test-Path $d) { Get-ChildItem $d -Recurse -Filter *.log -ErrorAction SilentlyContinue | ForEach-Object { "--- $($_.FullName)"; Get-Content $_.FullName -Tail 80 } }
}
"== top-level windows"
Get-Process | Where-Object { $_.MainWindowTitle } | Format-Table ProcessName, MainWindowTitle -AutoSize | Out-String -Width 200
