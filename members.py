# members.py -- car club member records
# Pico Computer 3, MicroPython.  Single board, no networking yet.

import os
import json
import time
import hdmi
import pcgui
from pcconfig import screen
from pcconsole import console
from pcgfx import WHITE, YELLOW, GREEN, RED, CYAN

DIR = "/sd/members"
ROLES_FILE = "/sd/roles.txt"
STATUS_FILE = "/sd/status.txt"

DEFAULT_ROLES = ["", "President", "Secretary", "Treasurer", "Committee"]
DEFAULT_STATUS = ["Active", "Not Active"]


def read_list(path, fallback):
    try:
        f = open(path)
        lines = f.read().split("\n")
        f.close()
    except OSError:
        return list(fallback)
    out = []
    for line in lines:
        line = line.strip()
        if line == "-":
            out.append("")
        elif line:
            out.append(line)
    return out if out else list(fallback)


def write_list(path, items):
    f = open(path, "w")
    for it in items:
        f.write((it if it else "-") + "\n")
    f.close()


STATUS = read_list(STATUS_FILE, DEFAULT_STATUS)
ROLES = read_list(ROLES_FILE, DEFAULT_ROLES)

FIELDS = ["name", "email", "phone", "car", "rego"]
LABELS = ["Name", "Email", "Phone", "Car", "Rego"]


def ensure_dir():
    try:
        os.mkdir(DIR)
    except OSError:
        pass
    try:
        os.stat(ROLES_FILE)
    except OSError:
        write_list(ROLES_FILE, ROLES)
    try:
        os.stat(STATUS_FILE)
    except OSError:
        write_list(STATUS_FILE, STATUS)


def path_for(num):
    return DIR + "/" + str(num) + ".json"


def load_member(num):
    try:
        f = open(path_for(num))
        rec = json.load(f)
        f.close()
        return rec
    except OSError:
        return None


def save_member(rec):
    f = open(path_for(rec["number"]), "w")
    json.dump(rec, f)
    f.close()


def blank(num):
    rec = {"number": num, "status": "Active", "role": ""}
    for k in FIELDS:
        rec[k] = ""
    return rec


class App:
    def __init__(self):
        self.rec = None
        self.boxes = {}
        self.build()

    def build(self):
        hdmi.fill(0)
        g = pcgui.GUI()
        self.g = g
        g.start()

        g.caption(320, 6, "Car Club Members", fg=YELLOW, font=3, just="CT")

        g.caption(20, 44, "Member No", fg=WHITE, font=2)
        self.num = g.numberbox(140, 38, 90, 28, font=2)
        g.button(244, 38, 80, 28, "FIND", font=2, callback=self.on_find)
        g.button(332, 38, 80, 28, "NEW", font=2, callback=self.on_new)

        g.frame(8, 78, 624, 296, "Details", font=2)

        y = 104
        for i in range(len(FIELDS)):
            g.caption(22, y + 4, LABELS[i], fg=WHITE, font=2)
            self.boxes[FIELDS[i]] = g.textbox(112, y, 286, 28, font=2)
            y = y + 38

        g.caption(424, 100, "Status", fg=WHITE, font=2)
        self.status = g.listbox(424, 122, 190, 54, STATUS, 0, font=2)

        g.caption(424, 190, "Role", fg=WHITE, font=2)
        self.role = g.listbox(424, 212, 190, 130, ROLES, 0, font=2)

        g.button(8, 392, 120, 34, "SAVE", fg=WHITE, bg=GREEN, font=2, callback=self.on_save)
        g.button(140, 392, 120, 34, "CLEAR", font=2, callback=self.on_clear)
        g.button(512, 392, 120, 34, "QUIT", fg=YELLOW, bg=RED, font=2, callback=self.on_quit)

        self.msg = g.displaybox(8, 438, 624, 28, "", fg=CYAN, font=2)
        self.done = False

    def say(self, text):
        self.msg.value = text

    def show(self, rec):
        self.rec = rec
        for k in FIELDS:
            self.boxes[k].value = rec.get(k, "")
        s = rec.get("status", STATUS[0])
        self.status.value = STATUS.index(s) if s in STATUS else 0
        r = rec.get("role", "")
        self.role.value = ROLES.index(r) if r in ROLES else 0

    def collect(self):
        rec = self.rec
        for k in FIELDS:
            rec[k] = self.boxes[k].value
        rec["status"] = STATUS[self.status.value]
        rec["role"] = ROLES[self.role.value]
        return rec

    def on_find(self, b):
        n = int(self.num.number)
        if n <= 0:
            self.say("Enter a member number")
            return
        rec = load_member(n)
        if rec is None:
            self.say("No record for " + str(n) + " -- press NEW to create")
        else:
            self.show(rec)
            self.say("Loaded member " + str(n))

    def on_new(self, b):
        n = int(self.num.number)
        if n <= 0:
            self.say("Enter a member number first")
            return
        if load_member(n) is not None:
            self.say("Member " + str(n) + " already exists")
            return
        for k in FIELDS:
            self.boxes[k].value = ""
        self.show(blank(n))
        self.say("New member " + str(n) + " -- fill in and SAVE")

    def on_save(self, b):
        if self.rec is None:
            n = int(self.num.number)
            if n <= 0:
                self.say("Enter a member number before saving")
                return
            self.rec = blank(n)
        rec = self.collect()
        try:
            save_member(rec)
            self.say("Saved member " + str(rec["number"]))
        except OSError as e:
            self.say("Save failed: " + str(e))

    def on_clear(self, b):
        self.rec = None
        for k in FIELDS:
            self.boxes[k].value = ""
        self.status.value = 0
        self.role.value = 0
        self.say("Cleared")

    def on_quit(self, b):
        self.done = True

    def run(self):
        n = 0
        try:
            n = len(os.listdir(DIR))
        except OSError:
            pass
        self.say(str(n) + " records on file -- enter a number and press FIND")
        while not self.done:
            self.g.poll()
            time.sleep_ms(10)
        self.g.stop()


def main():
    ensure_dir()
    screen(hdmi.RGB640)
    time.sleep(3)
    console("serial")
    try:
        App().run()
    finally:
        console("both")


main()