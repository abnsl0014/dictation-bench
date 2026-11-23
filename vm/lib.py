"""Helpers for VM command scripts (test-only)."""
import ctypes, json, os, sys, time
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace"); sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from pathlib import Path

OUT = Path(os.environ.get('WISPR_VM_OUT', '.'))


def secrets():
    p = os.environ.get('WISPR_VM_SECRETS')
    return json.load(open(p)) if p and Path(p).exists() else {}


def shot(name):
    from PIL import ImageGrab
    img = ImageGrab.grab(all_screens=True)
    img.save(OUT / f'{name}.png', optimize=True)
    return str(OUT / f'{name}.png')


def device(name_part, kind):
    """Index of the first sounddevice whose name contains name_part (kind: 'input'/'output')."""
    import sounddevice as sd
    for i, d in enumerate(sd.query_devices()):
        if name_part.lower() in d['name'].lower() and d[f'max_{kind}_channels'] > 0:
            return i
    raise RuntimeError(f'no {kind} device like {name_part!r}')


def play(wav, block=True):
    """Play a WAV into the virtual cable (the apps hear it as the microphone)."""
    import sounddevice as sd, soundfile as sf
    data, sr = sf.read(wav, dtype='float32')
    sd.play(data, sr, device=device('CABLE In', 'output'))
    if block:
        sd.wait()
    return len(data) / sr


# ── keyboard (SendInput) ───────────────────────────────────────────────────────
VK = {'CTRL': 0x11, 'LCTRL': 0xA2, 'LWIN': 0x5B, 'SHIFT': 0x10, 'ALT': 0x12, 'SPACE': 0x20, 'ENTER': 0x0D,
      'A': 0x41, 'C': 0x43, 'V': 0x56, 'Z': 0x5A, 'ESC': 0x1B, 'TAB': 0x09, 'DELETE': 0x2E}
EXTENDED = {0x5B}


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', ctypes.c_ushort), ('wScan', ctypes.c_ushort), ('dwFlags', ctypes.c_ulong), ('time', ctypes.c_ulong), ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong))]


class INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = [('ki', KEYBDINPUT), ('pad', ctypes.c_byte * 32)]
    _anonymous_ = ('i',)
    _fields_ = [('type', ctypes.c_ulong), ('i', _I)]


def _key(vk, up):
    scan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
    flags = (0x0002 if up else 0) | (0x0001 if vk in EXTENDED else 0)
    inp = INPUT(type=1)
    inp.ki = KEYBDINPUT(vk, scan, flags, 0, None)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def keys_down(*names):
    for n in names:
        _key(VK[n], False); time.sleep(0.03)


def keys_up(*names):
    for n in reversed(names):
        _key(VK[n], True); time.sleep(0.03)


def chord(*names):
    keys_down(*names); time.sleep(0.05); keys_up(*names)


def hold_and_play(wav, hotkey=('LCTRL', 'LWIN'), lead=0.6, tail=0.8):
    """Hold the push-to-talk chord, play the recording into the mic, release."""
    keys_down(*hotkey)
    time.sleep(lead)
    dur = play(wav)
    time.sleep(tail)
    keys_up(*hotkey)
    return dur


def clipboard_text():
    import pyperclip
    return pyperclip.paste()


def windows():
    from pywinauto import Desktop
    return [(w.window_text(), w.class_name(), w.rectangle()) for w in Desktop(backend='uia').windows() if w.window_text()]


def click(x, y, double=False):
    import pyautogui
    pyautogui.FAILSAFE = False
    (pyautogui.doubleClick if double else pyautogui.click)(x, y)


def type_text(s, interval=0.01):
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.write(s, interval=interval)
