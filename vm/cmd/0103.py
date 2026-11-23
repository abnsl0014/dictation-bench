# timeout=120   click "Copy sign-in link" via UIA (robust to layout), read clipboard
import time, lib, pyperclip
from pywinauto import Desktop
pyperclip.copy('')
clicked = False
try:
    w = Desktop(backend='uia').window(title='Wispr Flow')
    for c in w.descendants():
        if 'Copy sign-in link' in (c.window_text() or ''):
            try:
                c.click_input(); clicked = True; break
            except Exception:
                r = c.rectangle(); lib.click((r.left+r.right)//2, (r.top+r.bottom)//2); clicked = True; break
except Exception as e:
    print('uia err', e)
time.sleep(2.5)
print('clicked:', clicked)
print('CLIPBOARD_START'); print(pyperclip.paste()); print('CLIPBOARD_END')
lib.shot('wispr_signin_link')
