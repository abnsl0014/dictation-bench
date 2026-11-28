# timeout=120   screenshot + visible window titles + Wispr UI text
import time, lib
time.sleep(4)
import win32gui
t=[]; win32gui.EnumWindows(lambda h,_: t.append(win32gui.GetWindowText(h)) if win32gui.IsWindowVisible(h) and win32gui.GetWindowText(h) else None, None)
print('windows:', t)
try:
    from pywinauto import Desktop
    for w in Desktop(backend='uia').windows():
        if 'Wispr' in (w.window_text() or '') or w.window_text() in ('Status','Hub'):
            txt=[c.window_text() for c in w.descendants() if c.window_text()][:80]
            print('UI', w.window_text(), '=>', txt)
except Exception as e: print('uia err', e)
