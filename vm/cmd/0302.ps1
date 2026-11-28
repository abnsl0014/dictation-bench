# timeout=2700   A/B: build a minimal Electron app with electron-builder 24.13.3 and Blip's NSIS settings twice (stock template vs scripts/patchNsisMultiUser.js), then test both installers (page heap, Run anyway, full install).
$ErrorActionPreference = 'Continue'
$repo = (Get-Location).Path
$w = "$env:RUNNER_TEMP\nsisab"; New-Item -ItemType Directory -Force $w | Out-Null; Set-Location $w
@'
{
  "name": "blip-ai",
  "productName": "Blip-AI",
  "version": "1.0.0",
  "description": "NSIS multiUser.nsh A/B test app",
  "author": "Blip test",
  "main": "main.js",
  "devDependencies": { "electron": "37.10.2", "electron-builder": "24.13.3" },
  "build": {
    "appId": "com.blipai.nsisab",
    "directories": { "output": "dist" },
    "win": { "target": [{ "target": "nsis", "arch": ["x64"] }] },
    "nsis": { "oneClick": false, "allowToChangeInstallationDirectory": true, "perMachine": false,
              "createDesktopShortcut": true, "createStartMenuShortcut": true, "shortcutName": "Blip AI",
              "runAfterFinish": true, "deleteAppDataOnUninstall": false,
              "artifactName": "${productName}-Setup-${version}.${ext}" }
  }
}
'@ | Set-Content package.json
"const { app, BrowserWindow } = require('electron'); app.whenReady().then(() => { new BrowserWindow({ width: 420, height: 200 }).loadURL('data:text/html,<h3>A/B test app running</h3>'); });" | Set-Content main.js
"node $(node -v)  npm $(npm -v)"
npm install --no-audit --no-fund 2>&1 | Select-Object -Last 3
"app-builder-lib $(node -p "require('app-builder-lib/package.json').version")"
New-Item -ItemType Directory -Force scripts | Out-Null
Copy-Item "$repo\vm\patchNsisMultiUser.js" scripts\

"===== build A: stock electron-builder template"
npx electron-builder --win --x64 --publish=never 2>&1 | Select-String -Pattern 'building|error|⨯' | ForEach-Object { $_.Line }
Copy-Item dist\Blip-AI-Setup-1.0.0.exe "$w\Blip-AI-Setup-stock.exe" -Force
"===== build B: template patched by scripts/patchNsisMultiUser.js"
node scripts\patchNsisMultiUser.js
Select-String -Path node_modules\app-builder-lib\templates\nsis\multiUser.nsh -Pattern 'lstrcpynW|NSIS_MAX_STRLEN} .s' | ForEach-Object { "  template: $($_.Line.Trim())" }
Remove-Item dist -Recurse -Force
npx electron-builder --win --x64 --publish=never 2>&1 | Select-String -Pattern 'building|error|⨯' | ForEach-Object { $_.Line }
Copy-Item dist\Blip-AI-Setup-1.0.0.exe "$w\Blip-AI-Setup-patched.exe" -Force
Get-Item "$w\Blip-AI-Setup-*.exe" | Format-Table Name, Length -AutoSize | Out-String

Set-Location $repo
"===== test A (stock): expected to crash under page heap"
pwsh -NoProfile -File vm/windowsInstallTest.ps1 -Installer "$w\Blip-AI-Setup-stock.exe" -PageHeapRuns 3 -RunAnywayRuns 0 -SkipInstall -OutDir "$env:WISPR_VM_OUT\abstock"
"exit $LASTEXITCODE"
"===== test B (patched): expected to pass everything"
pwsh -NoProfile -File vm/windowsInstallTest.ps1 -Installer "$w\Blip-AI-Setup-patched.exe" -PageHeapRuns 5 -RunAnywayRuns 4 -OutDir "$env:WISPR_VM_OUT\abpatched"
"exit $LASTEXITCODE"
