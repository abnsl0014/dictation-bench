<#
  Installer smoke test for the Blip AI Windows NSIS installer, run on a GitHub-hosted
  Windows runner (it needs the interactive desktop those runners have).

  Why it exists: electron-builder <= 26.11's multiUser.nsh over-reads a heap buffer on a
  fresh per-user install (System.dll+0x1581, 0xc0000005). The crash depends on heap
  layout, so it came and went: ~50% of launches from SmartScreen's "Run anyway" on the
  first signed 0.5.11 build. scripts/patchNsisMultiUser.js fixes the template; this
  test makes sure no installer with that kind of bug ships again.

  Tests (each from a clean state: app uninstalled, no InstallLocation in HKCU)
    1. Page heap  - Windows full page heap is turned on for the installer, so any heap
                    over-read faults every time instead of by luck. The installer must
                    reach its first window on every run.
    2. Run anyway - the real customer path: the file carries Mark-of-the-Web, is opened
                    through Explorer, and SmartScreen's More info -> Run anyway is clicked.
    3. Install    - silent per-user install, the app starts and is still running 30 s
                    later, every installed .exe/.dll/.node is signed (if -ExpectSigned),
                    then a silent uninstall.
  Any crash, missing window or failed install fails the script (exit 1).
#>
param(
  [Parameter(Mandatory = $true)][string]$Installer,
  [int]$PageHeapRuns = 3,
  [int]$RunAnywayRuns = 6,
  [switch]$SkipInstall,
  [switch]$ExpectSigned,
  [string]$OutDir = "$env:RUNNER_TEMP\install-test"
)
$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Force $OutDir | Out-Null
$Installer = (Resolve-Path $Installer).Path
$exeName = Split-Path $Installer -Leaf
$procName = [IO.Path]::GetFileNameWithoutExtension($exeName)
$appDir = "$env:LOCALAPPDATA\Programs\blip-ai"
$summary = New-Object System.Collections.Generic.List[string]
$failures = 0

Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public static class BlipW {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, IntPtr e);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  public static void Click(int x, int y) { SetCursorPos(x, y); System.Threading.Thread.Sleep(150); mouse_event(2, 0, 0, 0, IntPtr.Zero); mouse_event(4, 0, 0, 0, IntPtr.Zero); }
}
'@
# Keep the runner's own console window out of the way.
Get-Process | Where-Object { $_.MainWindowTitle -match 'GitHub|Hosted|hosted-compute' } | ForEach-Object { [BlipW]::ShowWindow($_.MainWindowHandle, 6) | Out-Null }

function Log([string]$m) { Write-Host $m; $summary.Add($m) }
function Shot([string]$name) {
  $b = [System.Windows.Forms.SystemInformation]::VirtualScreen
  $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size)
  $bmp.Save((Join-Path $OutDir "$name.png"), [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
}
function Pixel([int]$x, [int]$y) {
  $bmp = New-Object System.Drawing.Bitmap 1, 1
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($x, $y, 0, 0, $bmp.Size)
  $c = $bmp.GetPixel(0, 0); $g.Dispose(); $bmp.Dispose(); return $c
}
function Crashes([datetime]$since) {
  @(Get-WinEvent -FilterHashtable @{ LogName = 'Application'; Id = 1000; StartTime = $since } -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match [regex]::Escape($procName) } |
    ForEach-Object { (($_.Message -split "`n") | Select-Object -First 5 | ForEach-Object { $_.Trim() }) -join ' / ' })
}
function SetupWindowUp {
  [bool](Get-Process -Name $procName -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -match 'Setup' })
}
function CleanSlate {
  foreach ($n in @($procName, 'Blip-AI')) { Get-Process -Name $n -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue }
  Start-Sleep 1
  $un = Join-Path $appDir 'Uninstall Blip-AI.exe'
  if (Test-Path $un) { Start-Process $un -ArgumentList '/S' -Wait; Start-Sleep 4 }
  Remove-Item $appDir -Recurse -Force -ErrorAction SilentlyContinue
  # The bug path only runs when HKCU has no InstallLocation for the app.
  Get-ChildItem HKCU:\Software -ErrorAction SilentlyContinue | ForEach-Object {
    $loc = (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).InstallLocation
    if ($loc -and $loc -match 'blip') { Remove-Item $_.PSPath -Recurse -Force -ErrorAction SilentlyContinue }
  }
}
function WaitForOutcome([datetime]$since, [int]$seconds) {
  for ($i = 0; $i -lt $seconds; $i++) {
    Start-Sleep 1
    if (SetupWindowUp) { return 'window' }
    if ((Crashes $since).Count) { return 'crash' }
  }
  if ((Crashes $since).Count) { return 'crash' }
  return 'nothing'
}
$ifeoRoots = @('HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options',
               'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows NT\CurrentVersion\Image File Execution Options')
function PageHeap([bool]$on) {
  foreach ($r in $ifeoRoots) {
    $k = Join-Path $r $exeName
    if ($on) {
      New-Item $k -Force | Out-Null
      Set-ItemProperty $k GlobalFlag 0x02000000 -Type DWord   # FLG_HEAP_PAGE_ALLOCS
      Set-ItemProperty $k PageHeapFlags 0x3 -Type DWord       # full page heap
    } else { Remove-Item $k -Recurse -Force -ErrorAction SilentlyContinue }
  }
}

$sig = Get-AuthenticodeSignature $Installer
Log "Installer: $exeName  ($([math]::Round((Get-Item $Installer).Length / 1MB, 1)) MB)  signature: $($sig.Status)  $($sig.SignerCertificate.Subject)"
if ($ExpectSigned -and $sig.Status -ne 'Valid') { Log "FAIL installer signature is $($sig.Status)"; $failures++ }

# 1. Page heap
if ($PageHeapRuns -gt 0) {
  PageHeap $true
  for ($i = 1; $i -le $PageHeapRuns; $i++) {
    CleanSlate
    Unblock-File $Installer
    $t = Get-Date
    Start-Process $Installer
    $o = WaitForOutcome $t 60
    Shot "pageheap-$i-$o"
    $c = Crashes $t
    if ($o -ne 'window' -or $c.Count) { $failures++; Log "FAIL page heap run $i`: $o $($c -join ' | ')" } else { Log "ok   page heap run $i`: installer window opened" }
  }
  PageHeap $false
}

# 2. SmartScreen "Run anyway" (dialog is centred; offsets measured at 100% scaling)
if ($RunAnywayRuns -gt 0) {
  $s = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $cx = [int]($s.Width / 2); $cy = [int]($s.Height / 2)
  $url = "https://www.blipai.app/download/windows"
  for ($i = 1; $i -le $RunAnywayRuns; $i++) {
    CleanSlate
    for ($k = 0; $k -lt 3; $k++) { [BlipW]::Click($cx + 190, $cy + 167); Start-Sleep -Milliseconds 800 }  # "Don't run" on a leftover dialog
    Set-Content -Path $Installer -Stream Zone.Identifier -Value "[ZoneTransfer]`r`nZoneId=3`r`nHostUrl=$url"
    $t = Get-Date
    Start-Process explorer.exe -ArgumentList "`"$Installer`""
    $shown = $false
    for ($w = 0; $w -lt 30 -and -not $shown; $w++) {
      Start-Sleep 1
      $p = Pixel $cx ($cy - 150)
      $shown = ($p.B -gt 140 -and $p.R -lt 60)   # SmartScreen's blue
      if (SetupWindowUp) { break }
    }
    if ($shown) {
      Shot "runanyway-$i-1-smartscreen"
      [BlipW]::Click($cx - 214, $cy - 161)   # More info
      Start-Sleep 2
      Shot "runanyway-$i-2-more-info"
      [BlipW]::Click($cx + 69, $cy + 167)    # Run anyway
    }
    $o = WaitForOutcome $t 45
    Shot "runanyway-$i-3-$o"
    $c = Crashes $t
    if ($o -ne 'window' -or $c.Count) { $failures++; Log "FAIL Run-anyway run $i (SmartScreen shown: $shown): $o $($c -join ' | ')" }
    else { Log "ok   Run-anyway run $i (SmartScreen shown: $shown): installer window opened" }
  }
  Remove-Item -Path $Installer -Stream Zone.Identifier -ErrorAction SilentlyContinue
}

# 3. Full silent install, app start, signatures, uninstall
if (-not $SkipInstall) {
  CleanSlate
  Unblock-File $Installer
  $t = Get-Date
  $p = Start-Process $Installer -ArgumentList '/S' -PassThru
  if (-not $p.WaitForExit(300000)) { $failures++; Log "FAIL silent install did not finish in 5 min" }
  $exe = Join-Path $appDir 'Blip-AI.exe'
  if (-not (Test-Path $exe)) { $failures++; Log "FAIL silent install: $exe missing (exit $($p.ExitCode)) $((Crashes $t) -join ' | ')" }
  else {
    Log "ok   silent install (exit $($p.ExitCode))"
    Start-Process $exe
    Start-Sleep 30
    Shot "app-30s"
    $alive = @(Get-Process -Name 'Blip-AI' -ErrorAction SilentlyContinue)
    if (-not $alive.Count) { $failures++; Log "FAIL app not running 30 s after start" } else { Log "ok   app running 30 s after start ($($alive.Count) processes)" }
    $appCrash = @(Get-WinEvent -FilterHashtable @{ LogName = 'Application'; Id = 1000; StartTime = $t } -ErrorAction SilentlyContinue | Where-Object { $_.Message -match 'Blip-AI\.exe' })
    if ($appCrash.Count) { $failures++; Log "FAIL app crash events: $($appCrash.Count)" }
    if ($ExpectSigned) {
      $files = Get-ChildItem $appDir -Recurse -File -Include *.exe, *.dll, *.node
      $bad = @($files | Where-Object { (Get-AuthenticodeSignature $_.FullName).Status -ne 'Valid' })
      if ($bad.Count) { $failures++; Log "FAIL $($bad.Count) of $($files.Count) installed binaries not validly signed: $(($bad | Select-Object -First 5 | ForEach-Object Name) -join ', ')" }
      else { Log "ok   all $($files.Count) installed .exe/.dll/.node files validly signed" }
    }
  }
  CleanSlate
  if (Test-Path $exe) { $failures++; Log "FAIL uninstall left $exe behind" } else { Log "ok   silent uninstall" }
}

Log "RESULT: $(if ($failures) { "FAILED ($failures)" } else { 'PASSED' })"
$summary | Set-Content (Join-Path $OutDir 'summary.txt')
if ($env:GITHUB_STEP_SUMMARY) { "### Installer test: $exeName`n" + (($summary | ForEach-Object { "- $_" }) -join "`n") | Add-Content $env:GITHUB_STEP_SUMMARY }
exit [int]($failures -gt 0)
