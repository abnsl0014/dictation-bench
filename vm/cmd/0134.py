# timeout=2400   run the German small-word scenarios through Wispr Flow into Notepad, retry on empty
import json, time, subprocess, lib
import win32gui, win32con
lib._key(lib.VK['ESC'], False); lib._key(lib.VK['ESC'], True); time.sleep(1.5)
S={s['id']:s for s in json.load(open('vm/scenarios.json',encoding='utf-8'))}
def hwnds(s):
    r=[]; win32gui.EnumWindows(lambda h,_: r.append(h) if win32gui.IsWindowVisible(h) and s.lower() in win32gui.GetWindowText(h).lower() else None, None); return r
for h in hwnds('Wispr Flow'):
    try: win32gui.ShowWindow(h, win32con.SW_MINIMIZE)
    except Exception: pass
time.sleep(1)
if not hwnds('Notepad'): subprocess.Popen(['notepad.exe']); time.sleep(3)
NP=hwnds('Notepad')[0]
from pywinauto import Desktop
def edit():
    w=Desktop(backend='uia').window(handle=NP)
    for ct in ('Document','Edit'):
        for c in w.descendants(control_type=ct): return c
def read():
    c=edit()
    if not c: return ''
    try: v=c.iface_value.CurrentValue
    except Exception:
        try: v=c.iface_text.DocumentRange.GetText(-1)
        except Exception: v=c.window_text()
    return (v or '').replace('\r\n','\n').replace('\r','\n')
def focus():
    try: win32gui.ShowWindow(NP,win32con.SW_RESTORE); win32gui.SetForegroundWindow(NP)
    except Exception: pass
    r=win32gui.GetWindowRect(NP); lib.click((r[0]+r[2])//2,(r[1]+r[3])//2); time.sleep(0.4)
def clear(): focus(); lib.chord('LCTRL','A'); time.sleep(0.2); lib._key(lib.VK['DELETE'],False); lib._key(lib.VK['DELETE'],True); time.sleep(0.4)
def one(sid):
    clear(); lib.keys_down('LCTRL','LWIN'); time.sleep(0.7)
    dur=lib.play(f'vm/audio/{sid}.flac'); time.sleep(1.0); lib.keys_up('LCTRL','LWIN')
    t0=time.time(); first=None; last=''; stable=None
    while time.time()-t0<42:
        txt=read(); now=time.time()
        if txt.strip() and first is None: first=now
        if txt!=last: last=txt; stable=now
        elif txt.strip() and stable and now-stable>2.5: break
        time.sleep(0.25)
    return last, dur, (int((first-t0)*1000) if first else None)
ids=[s for s in S if s.startswith('dep')]
outp=lib.OUT/'app_wispr_de_particles.jsonl'
for sid in ids:
    out='';dur=0;ms=None
    for a in range(3):
        out,dur,ms=one(sid)
        if out.strip(): break
        time.sleep(3)
    r={'id':sid,'lang':S[sid]['lang'],'out':out,'dur':round(dur,2),'ms_first':ms,'label':'wispr_de_particles'}
    open(outp,'a',encoding='utf-8').write(json.dumps(r,ensure_ascii=False)+'\n')
    print(json.dumps(r,ensure_ascii=False)[:200])
    time.sleep(3)
