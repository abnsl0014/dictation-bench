# timeout=150   click Skip on the remaining practice screens, screenshot each
import time, lib
for i in range(3):
    lib.click(931, 94); time.sleep(3.5); lib.shot(f'skip_{i}')
