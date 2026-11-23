"""Dictate scenarios into Notepad through a desktop dictation app (test-only).

run(label, ids, hotkey) → appends one JSON line per scenario to out/app_<label>.jsonl:
  {id, lang, out, ms_first, ms_stable, dur}
ms_first: key release → first text in Notepad; ms_stable: → text stopped changing.
"""
import json, os, subprocess, time
import lib

S = {s['id']: s for s in json.load(open('vm/scenarios.json', encoding='utf-8'))}


def notepad():
    from pywinauto import Desktop
    d = Desktop(backend='uia')
    for w in d.windows():
        if 'Notepad' in w.window_text() or w.class_name() == 'Notepad':
            return w
    subprocess.Popen(['notepad.exe']); time.sleep(4)
    for w in d.windows():
        if 'Notepad' in w.window_text() or w.class_name() == 'Notepad':
            return w
    raise RuntimeError('no Notepad')


def read_text(w):
    for ct in ('Document', 'Edit'):
        try:
            for c in w.descendants(control_type=ct):
                try:
                    v = c.iface_value.CurrentValue
                except Exception:
                    try:
                        v = c.iface_text.DocumentRange.GetText(-1)
                    except Exception:
                        v = c.window_text()
                if v is not None:
                    return v.replace('\r\n', '\n').replace('\r', '\n')
        except Exception:
            pass
    return None


def focus(w):
    try:
        w.set_focus()
    except Exception:
        pass
    r = w.rectangle()
    lib.click((r.left + r.right) // 2, (r.top + r.bottom) // 2)
    time.sleep(0.3)


def clear(w):
    focus(w)
    lib.chord('LCTRL', 'A'); time.sleep(0.1)
    lib._key(lib.VK['DELETE'], False); lib._key(lib.VK['DELETE'], True); time.sleep(0.3)


def dictate(w, sid, hotkey, wait_max=40):
    s = S[sid]
    clear(w)
    path = f"vm/audio/{sid}.flac"
    lib.keys_down(*hotkey); time.sleep(0.6)
    dur = lib.play(path)
    time.sleep(0.8)
    lib.keys_up(*hotkey)
    t0 = time.time(); first = None; last = ''; stable_since = None
    limit = wait_max if s['text'] else 12
    while time.time() - t0 < limit:
        txt = read_text(w) or ''
        now = time.time()
        if txt.strip() and first is None:
            first = now
        if txt != last:
            last = txt; stable_since = now
        elif txt.strip() and stable_since and now - stable_since > 2.5:
            break
        time.sleep(0.25)
    return {'id': sid, 'lang': s['lang'], 'out': last, 'dur': round(dur, 2),
            'ms_first': int((first - t0) * 1000) if first else None,
            'ms_stable': int((stable_since - t0) * 1000) if (stable_since and last.strip()) else None}


def run(label, ids, hotkey=('LCTRL', 'LWIN')):
    w = notepad()
    outp = lib.OUT / f'app_{label}.jsonl'
    res = []
    for sid in ids:
        try:
            r = dictate(w, sid, hotkey)
        except Exception as e:
            r = {'id': sid, 'error': repr(e)}
        r['label'] = label
        res.append(r)
        with open(outp, 'a', encoding='utf-8') as f:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
        print(json.dumps(r, ensure_ascii=False)[:300])
        time.sleep(1.5)
    return res


def blip_config_path():
    for name in ('Blip-AI', 'blip-ai', 'Blip AI'):
        p = os.path.expandvars(f'%APPDATA%\\{name}\\config.json')
        if os.path.exists(p):
            return p
    return None


def restart_blip(lang=None):
    subprocess.run(['taskkill', '/F', '/IM', 'Blip-AI.exe'], capture_output=True); time.sleep(3)
    if lang:
        p = blip_config_path()
        cfg = json.load(open(p, encoding='utf-8')) if p else {}
        cfg['dictationLanguage'] = lang
        json.dump(cfg, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    subprocess.Popen([os.path.expandvars(r'%LOCALAPPDATA%\Programs\Blip-AI\Blip-AI.exe')]); time.sleep(15)
