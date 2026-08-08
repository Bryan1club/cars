# menu.py -- car club system, main menu.
# Launches the other tools.  Put this in /main.py to run at boot.

import os
import time
import hdmi
import pcgui
from pcconfig import screen
from pcconsole import console
from pcshell import run
from pcgfx import WHITE, RED, BLACK
PAGE = 0xCCE8CC
INK = 0x103018
BTN = 0x2E7D32
DIM = 0x9AB49A

HERE = "/"

ITEMS = [
    ("Club", "club.py", "Members, cars and events, all in one"),
    ("Members", "members.py", "Look up, add and edit records"),
    ("Import", "import.py", "Load a CSV into records"),
    ("Export", "export.py", "Write records out as CSV"),
    ("Upload", "upload.py", "Send data to the main board"),
    ("Settings", "settings.py", "Roles, statuses, desk number"),
]


def exists(name):
    try:
        os.stat(HERE + name)
        return True
    except OSError:
        return False


class Menu:
    def __init__(self):
        self.done = False
        self.build()

    def build(self):
        hdmi.fill(hdmi.fb().colour(PAGE))
        g = pcgui.GUI()
        self.g = g
        g.start()
        g.caption(320, 10, "Car Club System", fg=INK, bg=PAGE, font=3, just="CT")
        g.caption(320, 44, "Choose an option", fg=INK, bg=PAGE, font=2, just="CT")
        y = 86
        for i in range(len(ITEMS)):
            name, script, blurb = ITEMS[i]
            ok = exists(script)
            fg = WHITE
            bg = BTN if ok else DIM
            g.button(40, y, 160, 40, name, fg=fg, bg=bg, font=3, callback=self.make_cb(i))
            note = blurb if ok else "not installed"
            g.caption(216, y + 12, note, fg=INK if ok else DIM, bg=PAGE, font=2)
            y = y + 52
        g.button(40, 400, 160, 40, "QUIT", fg=WHITE, bg=RED, font=3, callback=self.on_quit)
        g.caption(216, 412, "Back to the prompt", fg=INK, bg=PAGE, font=2)
        self.msg = g.displaybox(8, 450, 624, 26, "", fg=INK, bg=PAGE, font=2)

    def make_cb(self, i):
        def cb(b):
            self.launch(i)
        return cb

    def say(self, text):
        self.msg.value = text

    def launch(self, i):
        name, script, blurb = ITEMS[i]
        if not exists(script):
            self.say(script + " is not on this board yet")
            return
        self.g.stop()
        try:
            run(HERE + script)
        except Exception as e:
            print("error in", script, ":", e)
        screen(hdmi.RGB640)
        time.sleep(3)
        self.build()
        self.say("Back from " + name)

    def on_quit(self, b):
        self.done = True

    def run(self):
        self.say("Ready")
        while not self.done:
            self.g.poll()
            time.sleep_ms(10)
        self.g.stop()


def main():
    screen(hdmi.RGB640)
    time.sleep(3)
    console("serial")
    try:
        Menu().run()
    finally:
        console("both")
        hdmi.fill(0)


main()