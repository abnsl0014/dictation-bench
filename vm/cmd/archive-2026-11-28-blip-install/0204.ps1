# timeout=180   diagnose: where is the Blip installer? processes, windows, install dir, recent events
$ErrorActionPreference = 'Continue'
"== processes started in the last 20 min"
Get-CimInstance Win32_Process | Where-Object { $_.CreationDate -gt (Get-Date).AddMinutes(-20) } | Sort-Object CreationDate |
  Format-Table ProcessId, ParentProcessId, Name, CreationDate, @{n='cmd';e={ if ($_.CommandLine) { $_.CommandLine.Substring(0, [Math]::Min(150, $_.CommandLine.Length)) } }} -AutoSize | Out-String -Width 400
"== all visible windows (incl. no-title owners)"
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices; using System.Collections.Generic;
public class EW {
  public delegate bool P(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(P p, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  public static List<string> All() { var r = new List<string>(); EnumWindows((h, l) => { if (IsWindowVisible(h)) { var t = new StringBuilder(256); var c = new StringBuilder(256); GetWindowText(h, t, 256); GetClassName(h, c, 256); uint pid; GetWindowThreadProcessId(h, out pid); r.Add(pid + " | " + c + " | " + t); } return true; }, IntPtr.Zero); return r; }
}
"@
[EW]::All() | ForEach-Object { $p = ($_ -split ' \| ')[0]; $n = (Get-Process -Id $p -ErrorAction SilentlyContinue).ProcessName; "$n | $_" }
"== install dir"
Test-Path "$env:LOCALAPPDATA\Programs\blip-ai"; Get-ChildItem "$env:LOCALAPPDATA\Programs" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
"== Zone.Identifier still on installer?"
Get-Content "$env:USERPROFILE\Downloads\Blip-AI-Setup-0.5.11.exe" -Stream Zone.Identifier -ErrorAction SilentlyContinue
"== Application + SmartScreen events, last 20 min"
Get-WinEvent -FilterHashtable @{ LogName = 'Application'; StartTime = (Get-Date).AddMinutes(-20) } -ErrorAction SilentlyContinue | Select-Object -First 25 | Format-List TimeCreated, ProviderName, Id, LevelDisplayName, Message | Out-String -Width 300
Get-WinEvent -LogName 'Microsoft-Windows-SmartScreen/Debug' -MaxEvents 10 -ErrorAction SilentlyContinue | Format-List TimeCreated, Message | Out-String -Width 300
