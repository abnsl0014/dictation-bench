# timeout=120   use Ctrl+Win as the dictation shortcut, press it once, confirm Yes
import time, lib
lib.click(349, 477); time.sleep(2)
lib.keys_down('LCTRL', 'LWIN'); time.sleep(1.2); lib.shot('hotkey_pressed'); time.sleep(0.5); lib.keys_up('LCTRL', 'LWIN')
time.sleep(1.5); lib.click(744, 477); time.sleep(3)
