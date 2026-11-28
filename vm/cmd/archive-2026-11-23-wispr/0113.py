# timeout=200   onboarding: click the first visible button from a preference list, report visible UI
import time, lib, sys
from pywinauto import Desktop
PREF = ['Skip onboarding', 'Not now', 'Skip', 'Other', 'Continue', 'Next', 'Done', 'Finish', 'Get started', 'Yes', 'Allow']
def vis():
    out=[]
    for w in Desktop(backend='uia').windows():
        if w.window_text() in ('Wispr Flow','Status','Hub'):
            for c in w.descendants():
                try:
                    t=(c.window_text() or '').strip()
                    if t and c.is_visible(): out.append((t,c))
                except Exception: pass
    return out
for step in range(6):
    v = vis(); names=[t for t,_ in v]
    hit = next((p for p in PREF if p in names), None)
    print(f'step {step}:', names[:28])
    if not hit: break
    c = dict(v)[hit]
    try: c.click_input()
    except Exception:
        r=c.rectangle(); lib.click((r.left+r.right)//2,(r.top+r.bottom)//2)
    print('  clicked', hit); time.sleep(4)
print('final:', [t for t,_ in vis()][:40])
