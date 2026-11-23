# timeout=120   onboarding clicks [(389,293),(897,256)]
import time, lib
for x,y in [(389,293),(897,256)]:
    lib.click(x,y); time.sleep(2)
time.sleep(1.5)
