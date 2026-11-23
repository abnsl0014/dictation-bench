# timeout=900   recon + audio service + VB-Cable virtual mic + default devices + loopback
$ErrorActionPreference = 'Continue'
Add-Type @'
using System; using System.Runtime.InteropServices;
public class W { [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c); }
'@
Get-Process | Where-Object { $_.MainWindowTitle -like '*GitHub*' -or $_.MainWindowTitle -like '*Hosted*' } | ForEach-Object { [W]::ShowWindow($_.MainWindowHandle, 6) | Out-Null }
(Get-CimInstance Win32_OperatingSystem).Caption
foreach ($s in 'AudioEndpointBuilder','Audiosrv') { Set-Service $s -StartupType Automatic; Start-Service $s }
$dir = "$env:RUNNER_TEMP\vbcable"; $zip = "$env:RUNNER_TEMP\vbcable.zip"
Invoke-WebRequest "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip" -OutFile $zip -UseBasicParsing
Expand-Archive $zip $dir -Force
$cat = Get-ChildItem $dir -Filter *.cat | Select-Object -First 1
$cert = (Get-AuthenticodeSignature $cat.FullName).SignerCertificate
if ($cert) { Export-Certificate -Cert $cert -FilePath "$env:RUNNER_TEMP\vb.cer" | Out-Null; certutil -addstore -f TrustedPublisher "$env:RUNNER_TEMP\vb.cer" | Out-Null }
$p = Start-Process (Join-Path $dir 'VBCABLE_Setup_x64.exe') -ArgumentList '-i','-h' -PassThru; $p.WaitForExit(240000) | Out-Null
Start-Sleep 8
foreach ($root in 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone') {
  New-Item $root -Force | Out-Null; Set-ItemProperty $root Value Allow
  New-Item "$root\NonPackaged" -Force | Out-Null; Set-ItemProperty "$root\NonPackaged" Value Allow
}
New-Item 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\AppPrivacy' -Force | Out-Null
Set-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\AppPrivacy' LetAppsAccessMicrophone 1 -Type DWord
Install-Module AudioDeviceCmdlets -Force -Scope CurrentUser -AllowClobber
Import-Module AudioDeviceCmdlets
$rec = Get-AudioDevice -List | Where-Object { $_.Type -eq 'Recording' -and $_.Name -like '*CABLE Output*' } | Select-Object -First 1
$play = Get-AudioDevice -List | Where-Object { $_.Type -eq 'Playback' -and $_.Name -like '*CABLE In*' } | Select-Object -First 1
if ($rec) { Set-AudioDevice -ID $rec.ID | Out-Null; Set-AudioDevice -ID $rec.ID -CommunicationOnly | Out-Null }
if ($play) { Set-AudioDevice -ID $play.ID | Out-Null }
Get-AudioDevice -Recording | Format-List Name
python -m pip install --quiet sounddevice soundfile numpy pillow pyautogui pywinauto pyperclip playwright
python -c "import sounddevice as sd,numpy as np,lib; o=lib.device('CABLE In','output'); i=lib.device('CABLE Output','input'); sr=48000; import numpy; t=numpy.arange(sr)/sr; tone=(0.3*numpy.sin(2*numpy.pi*440*t)).astype('float32'); rec=sd.playrec(tone,sr,channels=1,device=(i,o)); sd.wait(); print('loopback rms', float(numpy.sqrt((rec**2).mean())))"
