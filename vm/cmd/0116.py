# timeout=120   onboarding clicks [(110,325),(255,648)]
import time, lib
for x,y in [(110,325),(255,648)]:
    lib.click(x,y); time.sleep(2.5)
time.sleep(2)
