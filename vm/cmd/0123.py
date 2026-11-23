# timeout=120   Wispr languages: search German, select it, remove English, screenshot (no save yet)
import time, lib
lib.click(300, 230); time.sleep(0.8)
lib.type_text('German'); time.sleep(2)
lib.click(207, 292); time.sleep(1.5)
lib.shot('lang_after_select')
lib.click(897, 256); time.sleep(1.5)
