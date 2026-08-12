# clicker.py -- a minimal sample game for the GAMES launcher in club.py
# Drop this into /sd/Games and it'll show up in the GAMES list.
#
# Deliberately simple: it exists to prove the launcher works (runs,
# takes input, exits cleanly back to club.py's menu) and to be a
# starting template for a real game. Uses only the same pcgui/hdmi
# calls already used throughout club.py -- nothing new or unproven.

import hdmi
import pcgui
import time

PAGE = 0x202040
INK = 0xFFFFFF
BTN = 0x2E7D32
RED = 0xCC3333

hdmi.fill(hdmi.fb().colour(PAGE))
g = pcgui.GUI()
g.start()

g.caption(320, 40, "CLICKER", fg=INK, bg=PAGE, font=3, just="CT")
count_box = g.displaybox(220, 120, 200, 60, "0", fg=INK, bg=PAGE, font=3)

state = {"count": 0, "done": False}


def on_click(b):
    state["count"] += 1
    count_box.value = str(state["count"])


def on_quit(b):
    state["done"] = True


g.button(220, 220, 200, 60, "CLICK ME", fg=INK, bg=BTN, font=3, callback=on_click)
g.button(220, 300, 200, 50, "QUIT", fg=INK, bg=RED, font=2, callback=on_quit)

while not state["done"]:
    g.poll()
    time.sleep_ms(10)

try:
    g.stop()
except Exception:
    pass
