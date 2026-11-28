# timeout=1500   Blip AI: SmartScreen Run anyway -> does the installer crash? 3 tries, robust SmartScreen detection, fresh uninstall before each
import concurrent.futures as cf
import os, subprocess, time
import lib
import win32api, win32con, win32gui, win32process
from pywinauto import Desktop

VER = '0.5.11'
EXE = os.path.join(os.environ['USERPROFILE'], 'Downloads', f'Blip-AI-Setup-{VER}.exe')
DIR = os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'blip-ai')
URL = f'https://github.com/abnsl0014/blipai-releases/releases/download/v{VER}/Blip-AI-Setup-{VER}.exe'
LOG = lib.OUT / '0208-log.txt'
POOL = cf.ThreadPoolExecutor(max_workers=4)


def log(*a):
    line = ' '.join(str(x) for x in a)
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(f'[{time.strftime("%H:%M:%S")}] {line}\n')


def timed(fn, *a, t=20, default=None):
    try:
        return POOL.submit(fn, *a).result(timeout=t)
    except Exception as e:
        log(f'{getattr(fn, "__name__", fn)} failed: {e!r}')
        return default


def ps(cmd, t=120):
    return subprocess.run(['pwsh', '-NoProfile', '-Command', cmd], capture_output=True, text=True, timeout=t).stdout.strip()


def procname(pid):
    try:
        return os.path.basename(win32process.GetModuleFileNameEx(win32api.OpenProcess(0x1000, False, pid), 0)).lower()
    except Exception:
        return '?'


def wins():
    out = []
    def cb(h, _):
        if win32gui.IsWindowVisible(h) and win32gui.GetWindowText(h):
            out.append((h, win32gui.GetWindowText(h), procname(win32process.GetWindowThreadProcessId(h)[1])))
    win32gui.EnumWindows(cb, None)
    return out


def _click(h, label):
    w = Desktop(backend='uia').window(handle=h)
    for c in w.descendants():
        if c.window_text().strip().lower() == label and c.is_enabled():
            c.click_input()
            return True
    return False


def _ssw():
    return [w.handle for w in Desktop(backend='uia').windows() if 'smartscreen' in (w.window_text() or '').lower()]


def smartscreen_windows():
    return timed(_ssw, default=[]) or []


def close_leftover_smartscreen():
    for h in smartscreen_windows():
        timed(_click, h, "don\u2019t run") or timed(_click, h, "don't run")
        time.sleep(1)


def crashes_since(ts):
    return ps(f"""Get-WinEvent -FilterHashtable @{{LogName='Application'; Id=1000; StartTime=[datetime]'{ts}'}} -ErrorAction SilentlyContinue |
      Where-Object {{ $_.Message -match 'Blip' }} | ForEach-Object {{ ($_.Message -split "`n")[0..4] -join ' / ' }}""")


def clean_slate():
    subprocess.run(['taskkill', '/F', '/T', '/IM', 'Blip-AI.exe'], capture_output=True)
    subprocess.run(['taskkill', '/F', '/T', '/IM', f'Blip-AI-Setup-{VER}.exe'], capture_output=True)
    un = os.path.join(DIR, 'Uninstall Blip-AI.exe')
    if os.path.exists(un):
        subprocess.run([un, '/S'], timeout=120)
        time.sleep(8)
    subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', DIR], capture_output=True)
    time.sleep(2)


def attempt(i, mode):
    close_leftover_smartscreen()
    clean_slate()
    ts = ps("(Get-Date).ToString('yyyy-MM-ddTHH:mm:ss')")
    if mode == 'run-anyway':
        ps(f'Set-Content -Path "{EXE}" -Stream Zone.Identifier -Value "[ZoneTransfer]`r`nZoneId=3`r`nHostUrl={URL}"')
        subprocess.Popen(['explorer.exe', EXE])
        clicked = False
        ss = []
        for _ in range(60):
            time.sleep(1.5)
            ss = smartscreen_windows()
            if ss:
                h = ss[0]
                lib.shot(f'0208-{i}-{mode}-smartscreen-first')
                timed(_click, h, 'more info')
                time.sleep(1.5)
                lib.shot(f'0208-{i}-{mode}-smartscreen')
                clicked = timed(_click, h, 'run anyway', default=False)
                break
        log(f'#{i} {mode}: SmartScreen shown={bool(ss)} run-anyway clicked={clicked}')
    else:
        ps(f'Unblock-File -Path "{EXE}"')
        subprocess.Popen([EXE])
    appeared = False
    for _ in range(20):
        time.sleep(2)
        if any('setup' in t.lower() and p.startswith('blip-ai-setup') for _, t, p in wins()):
            appeared = True
            break
    lib.shot(f'0208-{i}-{mode}-after')
    time.sleep(3)
    cr = crashes_since(ts)
    log(f'#{i} {mode}: installer window appeared={appeared} | crash events: {cr or "none"}')
    subprocess.run(['taskkill', '/F', '/T', '/IM', f'Blip-AI-Setup-{VER}.exe'], capture_output=True)
    return appeared, bool(cr)


results = []
for i, mode in enumerate(['run-anyway', 'run-anyway', 'run-anyway'], 1):
    try:
        results.append((mode,) + attempt(i, mode))
    except Exception as e:
        log(f'#{i} {mode}: error {e!r}')
log('SUMMARY (mode, installer window appeared, crashed):', results)
log('== WER crash reports for the installer')
log(ps(r"""Get-ChildItem 'C:\ProgramData\Microsoft\Windows\WER\ReportArchive','C:\ProgramData\Microsoft\Windows\WER\ReportQueue' -Recurse -Filter Report.wer -ErrorAction SilentlyContinue |
  Where-Object { (Get-Content $_.FullName -Raw) -match 'Blip-AI-Setup' } | Select-Object -First 1 | ForEach-Object { Get-Content $_.FullName | Select-String 'Sig\[|AppPath|Exception|ModuleName|OsInfo' }"""))
os._exit(0)
