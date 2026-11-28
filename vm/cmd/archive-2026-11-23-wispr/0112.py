# timeout=330   watch up to ~290s for Wispr to leave the sign-in screen
import time, lib
from pywinauto import Desktop
def visible_texts():
    out=[]
    for w in Desktop(backend='uia').windows():
        if w.window_text()=='Wispr Flow':
            for c in w.descendants():
                try:
                    if c.window_text() and c.is_visible(): out.append(c.window_text())
                except Exception: pass
    return out
t0=time.time()
while time.time()-t0<290:
    t=visible_texts()
    if 'Copy sign-in link' not in t:
        print(f'left sign-in screen after {int(time.time()-t0)}s'); print(t[:40]); break
    time.sleep(10)
else:
    print('still on sign-in screen after 290s'); print(t[:30])
