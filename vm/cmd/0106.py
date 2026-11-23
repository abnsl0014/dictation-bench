# timeout=200   dismiss calendar prompt + skip onboarding, then list Wispr UI text
import time, lib
from pywinauto import Desktop
def click_text(label):
    for w in Desktop(backend='uia').windows():
        try:
            for c in w.descendants():
                if (c.window_text() or '').strip() == label:
                    try: c.click_input()
                    except Exception:
                        r=c.rectangle(); lib.click((r.left+r.right)//2,(r.top+r.bottom)//2)
                    return True
        except Exception: pass
    return False
print('Not now:', click_text('Not now')); time.sleep(3)
print('Skip onboarding:', click_text('Skip onboarding')); time.sleep(6)
for lab in ('Not now','Skip','Continue','Done','Finish','Get started'):
    if click_text(lab): print('also clicked', lab); time.sleep(4)
for w in Desktop(backend='uia').windows():
    if w.window_text() in ('Wispr Flow','Status','Hub') or 'Wispr' in (w.window_text() or ''):
        print('UI', w.window_text(), '=>', [c.window_text() for c in w.descendants() if c.window_text()][:60])
