# timeout=600   Blip AI: install from scratch like a customer (double-click, click through every screen), screenshot each step
import json, os, time
import lib
import win32api, win32con, win32gui, win32process
from pywinauto import Desktop

VER = '0.5.11'
EXE = os.path.join(os.environ['USERPROFILE'], 'Downloads', f'Blip-AI-Setup-{VER}.exe')
APP = os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'blip-ai', 'Blip-AI.exe')
steps = []
n = [0]


def shot(label):
    n[0] += 1
    name = f'0202-{n[0]:02d}-' + ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in label)[:60]
    lib.shot(name)
    print('screenshot', name)
    return name


def procname(pid):
    try:
        h = win32api.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        return os.path.basename(win32process.GetModuleFileNameEx(h, 0)).lower()
    except Exception:
        return '?'


def wins():
    out = []
    def cb(h, _):
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if t:
                pid = win32process.GetWindowThreadProcessId(h)[1]
                out.append((h, t, procname(pid)))
    win32gui.EnumWindows(cb, None)
    return out


def texts(h):
    try:
        w = Desktop(backend='uia').window(handle=h)
        seen = []
        for c in w.descendants():
            t = c.window_text().strip()
            if t:
                item = f'{c.element_info.control_type}: {t}'
                if item not in seen:
                    seen.append(item)
        return seen
    except Exception as e:
        return [f'(could not read window: {e})']


def front(h):
    try:
        win32gui.ShowWindow(h, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(h)
    except Exception as e:
        print('foreground failed:', e)
    time.sleep(0.8)


def click(h, labels):
    """Click the first enabled control whose name matches one of labels (case-insensitive)."""
    try:
        w = Desktop(backend='uia').window(handle=h)
        for c in w.descendants():
            name = c.window_text().strip().lower().replace('&', '')
            if name in labels and c.element_info.control_type in ('Button', 'Hyperlink', 'Text', 'CheckBox'):
                if c.is_enabled():
                    c.click_input()
                    return c.window_text()
    except Exception as e:
        print('click failed:', e)
    return None


def record(kind, h, title, clicked=None):
    label = shot(f'{kind}-{title}')
    steps.append({'t': round(time.time() - t0, 1), 'kind': kind, 'title': title, 'screenshot': label,
                  'text': texts(h), 'clicked': clicked})


shot('desktop-before-install')
t0 = time.time()
os.startfile(EXE)  # ShellExecute, the same as double-clicking the file in Downloads
last_page = None
done = False
while time.time() - t0 < 480:
    time.sleep(2.5)
    ws = wins()
    ss = [w for w in ws if 'smartscreen' in w[2] or 'protected your pc' in w[1].lower() or 'smartscreen' in w[1].lower()]
    if ss:
        ss_tries = globals().get('ss_tries', 0) + 1
        globals()['ss_tries'] = ss_tries
        if ss_tries > 2:
            print('SmartScreen still blocking after 2 tries; stopping here')
            shot('smartscreen-still-blocking')
            break
        h, title, _ = ss[0]
        front(h)
        record('smartscreen', h, title)
        c = click(h, {'more info'})
        time.sleep(1.5)
        record('smartscreen-more-info', h, title, c)
        c = click(h, {'run anyway'})
        time.sleep(2)
        steps[-1]['then_clicked'] = c
        if not c:
            print('SmartScreen offered no Run anyway button')
        continue
    warn = [w for w in ws if 'security warning' in w[1].lower()]
    if warn:
        h, title, _ = warn[0]
        front(h)
        record('open-file-security-warning', h, title)
        click(h, {'run'})
        continue
    setup = [w for w in ws if 'setup' in w[1].lower() and 'blip' in (w[1].lower() + w[2])]
    if not setup:
        setup = [w for w in ws if w[2].startswith('blip-ai-setup') or ('setup' in w[1].lower() and w[2] not in ('explorer.exe',))]
    if setup:
        h, title, _ = setup[0]
        page = '|'.join(texts(h)[:12])
        if page != last_page:
            front(h)
            record('installer', h, title)
            last_page = page
        c = click(h, {'next >', 'next', 'i agree', 'install', 'finish'})
        if c:
            steps.append({'t': round(time.time() - t0, 1), 'kind': 'clicked', 'title': title, 'clicked': c})
            print('clicked', c)
            time.sleep(2)
        continue
    running = [w for w in ws if w[2] == 'blip-ai.exe']
    if os.path.exists(APP) and running:
        done = True
        break

print('installed:', os.path.exists(APP), ' app window seen:', done, ' after', round(time.time() - t0), 's')
time.sleep(20)
for h, title, proc in wins():
    if proc == 'blip-ai.exe':
        front(h)
        record('app-window', h, title)
shot('screen-20s-after-install')
print('== all windows now')
for h, title, proc in wins():
    print(proc, '|', title)
(lib.OUT / 'install_steps.json').write_text(json.dumps(steps, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(steps, indent=1, ensure_ascii=False)[:20000])
