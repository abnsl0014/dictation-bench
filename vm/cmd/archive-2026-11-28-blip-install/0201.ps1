# timeout=600   Blip AI: download the public installer like a browser, check signature, SmartScreen/SAC state, Defender scan
$ErrorActionPreference = 'Continue'
Add-Type @'
using System; using System.Runtime.InteropServices;
public class W { [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c); }
'@
Get-Process | Where-Object { $_.MainWindowTitle -like '*GitHub*' -or $_.MainWindowTitle -like '*Hosted*' } | ForEach-Object { [W]::ShowWindow($_.MainWindowHandle, 6) | Out-Null }
$os = Get-CimInstance Win32_OperatingSystem
"OS: $($os.Caption)  version $($os.Version)  build $($os.BuildNumber)"
$ver = '0.5.11'
$url = "https://github.com/abnsl0014/blipai-releases/releases/download/v$ver/Blip-AI-Setup-$ver.exe"
$dl = "$env:USERPROFILE\Downloads"; New-Item -ItemType Directory -Force $dl | Out-Null
$exe = Join-Path $dl "Blip-AI-Setup-$ver.exe"
Invoke-WebRequest $url -OutFile $exe -UseBasicParsing
# Mark-of-the-Web, exactly what Edge/Chrome attach to a download from blipai.app
Set-Content -Path $exe -Stream Zone.Identifier -Value "[ZoneTransfer]`r`nZoneId=3`r`nReferrerUrl=https://www.blipai.app/download`r`nHostUrl=$url"
"installer: $exe"
"size: $((Get-Item $exe).Length) bytes   sha256: $((Get-FileHash $exe).Hash)"
"== Zone.Identifier"; Get-Content $exe -Stream Zone.Identifier
$sig = Get-AuthenticodeSignature $exe
"== signature: $($sig.Status)  $($sig.StatusMessage)"
"signer:  $($sig.SignerCertificate.Subject)"
"issuer:  $($sig.SignerCertificate.Issuer)"
"valid:   $($sig.SignerCertificate.NotBefore) -> $($sig.SignerCertificate.NotAfter)"
"timestamp: $([bool]$sig.TimeStamperCertificate)  $($sig.TimeStamperCertificate.Subject)"
"== SmartScreen settings"
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer' -Name SmartScreenEnabled -ErrorAction SilentlyContinue | Format-List SmartScreenEnabled
Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' -ErrorAction SilentlyContinue | Format-List EnableSmartScreen, ShellSmartScreenLevel
"== Smart App Control (VerifiedAndReputablePolicyState: 0 off, 1 on, 2 evaluation)"
Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy' -Name VerifiedAndReputablePolicyState -ErrorAction SilentlyContinue | Format-List VerifiedAndReputablePolicyState
"== Defender"
Get-MpComputerStatus -ErrorAction SilentlyContinue | Format-List AMServiceEnabled, AntivirusEnabled, RealTimeProtectionEnabled
$mp = "$env:ProgramFiles\Windows Defender\MpCmdRun.exe"
if (Test-Path $mp) { & $mp -Scan -ScanType 3 -File $exe -DisableRemediation 2>&1 | Out-String } else { 'MpCmdRun not found' }
