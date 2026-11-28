# timeout=120   click "Copy sign-in link" at its on-screen position, read the clipboard
import time, lib, pyperclip
pyperclip.copy('')
lib.click(255, 456); time.sleep(2.5)
link = pyperclip.paste()
if not link.strip():
    lib.click(255, 456); time.sleep(3); link = pyperclip.paste()
print('CLIPBOARD_START'); print(link); print('CLIPBOARD_END')
