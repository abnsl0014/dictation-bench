# timeout=120   select German once, screenshot, Save and close
import time, lib
lib.click(389, 293); time.sleep(2)
lib.shot('lang_selected')
lib.click(850, 602); time.sleep(3)
