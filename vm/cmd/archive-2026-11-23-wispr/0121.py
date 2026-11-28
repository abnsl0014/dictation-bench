# timeout=150   play a clip into the virtual mic during Wispr's mic test, screenshot the bars, click Yes
import threading, time, lib
t = threading.Thread(target=lambda: lib.play('vm/audio/dep21.flac')); t.start()
time.sleep(3.5); lib.shot('mic_bars')
time.sleep(1.5); lib.click(723, 473); time.sleep(4)
print('clicked Yes')
