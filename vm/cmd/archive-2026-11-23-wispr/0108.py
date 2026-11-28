# timeout=120   fresh sign-in link: click "Copy sign-in link" (current layout), read clipboard
import time, lib, pyperclip
from pywinauto import Desktop
still = False
for w in Desktop(backend='uia').windows():
    if w.window_text()=='Wispr Flow':
        for c in w.descendants():
            try:
                if c.window_text()=='Copy sign-in link' and c.is_visible():
                    still = True; r = c.rectangle(); x, y = (r.left+r.right)//2, (r.top+r.bottom)//2
            except Exception: pass
if not still:
    print('NOT ON SIGN-IN SCREEN (already signed in?)')
else:
    pyperclip.copy(''); lib.click(x, y); time.sleep(2.5)
    print('clicked at', x, y)
    print('CLIPBOARD_START'); print(pyperclip.paste()); print('CLIPBOARD_END')
