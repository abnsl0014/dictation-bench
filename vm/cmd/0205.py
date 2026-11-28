# timeout=840   Blip AI install, attempt 2: open via Explorer (a real double-click), click through every screen, screenshot each step
import concurrent.futures as cf
import json, os, subprocess, time
import lib
import win32api, win32con, win32gui, win32process
from pywinauto import Desktop

VER = '0.5.11'
EXE = os.path.join(os.environ['USERPROFILE'], 'Downloads', f'Blip-AI-Setup-{VER}.exe')
APP = os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'blip-ai', 'Blip-AI.exe')
LOG = lib.OUT / '0205-log.txt'
POOL = cf.ThreadPoolExecutor(max_workers=4)
steps, n = [], [0]


def log(*a):
    line = ' '.join(str(x) for x in a)
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(f'[{time.strftime("%H:%M:%S")}] {line}\n')


def timed(fn, *a, t=20, default=None):
    try:
        return POOL.submit(fn, *a).result(timeout=t)
    except Exception as e:
        log(f'{getattr(fn, "__name__", fn)} failed/timed out: {e!r}')
        return default


def shot(label):
    n[0] += 1
    name = f'0205-{n[0]:02d}-' + ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in label)[:60]
    timed(lib.shot, name)
    log('screenshot', name)
    return name


def procname(pid):
    try:
        h = win32api.OpenProcess(0x1000, False, pid)
        return os.path.basename(win32process.GetModuleFileNameEx(h, 0)).lower()
    except Exception:
        return '?'


def wins():
    out = []
    def cb(h, _):
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if t:
                out.append((h, t, procname(win32process.GetWindowThreadProcessId(h)[1])))
    win32gui.EnumWindows(cb, None)
    return out


def _texts(h):
    w = Desktop(backend='uia').window(handle=h)
    seen = []
    for c in w.descendants():
        t = c.window_text().strip()
        if t:
            item = f'{c.element_info.control_type}: {t}'
            if item not in seen:
                seen.append(item)
    return seen


def texts(h):
    return timed(_texts, h, default=[])


def front(h):
    try:
        win32gui.ShowWindow(h, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(h)
    except Exception as e:
        log('foreground failed:', e)
    time.sleep(0.8)


def _click(h, labels):
    w = Desktop(backend='uia').window(handle=h)
    for c in w.descendants():
        name = c.window_text().strip().lower().replace('&', '')
        if name in labels and c.element_info.control_type in ('Button', 'Hyperlink', 'Text', 'CheckBox') and c.is_enabled():
            c.click_input()
            return c.window_text()
    return None


def click(h, labels):
    return timed(_click, h, labels)


def record(kind, h, title, **extra):
    label = shot(f'{kind}-{title}')
    tx = texts(h)
    steps.append({'t': round(time.time() - t0, 1), 'kind': kind, 'title': title, 'screenshot': label, 'text': tx, **extra})
    log(kind, '|', title, '|', ' / '.join(tx[:15]))


def setup_running():
    out = subprocess.run(['tasklist', '/fo', 'csv', '/nh'], capture_output=True, text=True).stdout.lower()
    return 'blip-ai-setup' in out


# close the Windows Server paging-file notice so screenshots are clean
for h, title, proc in wins():
    if proc == 'systempropertiesperformance.exe':
        win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
time.sleep(1)

shot('desktop-before-install')
t0 = time.time()
log('opening installer through Explorer (same as double-clicking it in Downloads)')
subprocess.Popen(['explorer.exe', EXE])
last_page, ss_tries, fallback, done = None, 0, False, False
while time.time() - t0 < 600:
    time.sleep(2.5)
    ws = wins()
    ss = [w for w in ws if 'smartscreen' in w[2] or 'protected your pc' in w[1].lower() or 'smartscreen' in w[1].lower()]
    if ss:
        ss_tries += 1
        h, title, _ = ss[0]
        if ss_tries > 3:
            shot('smartscreen-still-blocking')
            log('SmartScreen still blocking after 3 tries')
            break
        front(h)
        record('smartscreen', h, title)
        c = click(h, {'more info'})
        time.sleep(1.5)
        record('smartscreen-after-more-info', h, title, clicked=c)
        c = click(h, {'run anyway'})
        log('Run anyway clicked:', c)
        time.sleep(3)
        continue
    warn = [w for w in ws if 'security warning' in w[1].lower()]
    if warn:
        h, title, _ = warn[0]
        front(h)
        record('open-file-security-warning', h, title)
        log('clicked', click(h, {'run'}))
        time.sleep(2)
        continue
    setup = [w for w in ws if 'setup' in w[1].lower() and w[2] not in ('systempropertiesperformance.exe', 'explorer.exe')]
    if setup:
        h, title, proc = setup[0]
        tx = texts(h)
        page = '|'.join(tx[:12])
        if page != last_page:
            front(h)
            record('installer', h, title, process=proc)
            last_page = page
        c = click(h, {'next >', 'next', 'i agree', 'install', 'finish'})
        if c:
            log('clicked', c)
            time.sleep(2)
        continue
    if os.path.exists(APP) and any(w[2] == 'blip-ai.exe' for w in ws):
        done = True
        log('installer finished and Blip AI window is up')
        break
    el = time.time() - t0
    if not fallback and el > 60 and not setup_running() and not os.path.exists(APP):
        shot('nothing-appeared-after-60s')
        log('no installer, SmartScreen or warning window after 60 s; windows now:', [(t, p) for _, t, p in ws])
        log('fallback: Unblock-File and start the installer directly (no Mark-of-the-Web)')
        subprocess.run(['pwsh', '-NoProfile', '-Command', f'Unblock-File -Path "{EXE}"'])
        subprocess.Popen([EXE])
        fallback = True
    if int(el) % 30 < 3:
        shot(f'waiting-{int(el)}s')

log('installed:', os.path.exists(APP), '| app window seen:', done, '| fallback used:', fallback, '| after', round(time.time() - t0), 's')
time.sleep(20)
for h, title, proc in wins():
    if proc == 'blip-ai.exe':
        front(h)
        record('app-window', h, title)
shot('screen-20s-after-install')
log('windows now:', [(t, p) for _, t, p in wins()])
(lib.OUT / '0205-steps.json').write_text(json.dumps(steps, indent=1, ensure_ascii=False), encoding='utf-8')
os._exit(0)
