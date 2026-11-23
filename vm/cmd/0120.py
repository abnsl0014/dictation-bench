# timeout=120   onboarding clicks [(255,398),(255,648)]
import time, lib
for x,y in [(255,398),(255,648)]:
    lib.click(x,y); time.sleep(2.5)
time.sleep(3)
