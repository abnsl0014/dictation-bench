# timeout=150   Continue through the last onboarding screens, screenshot each, dump visible-ish text
import time, lib
for i in range(3):
    lib.click(512, 664); time.sleep(3.5); lib.shot(f'cont_{i}')
