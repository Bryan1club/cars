# club.py -- car club system
# Pico Computer 3, MicroPython.  One program, several pages.
# Data lives in SQLite at /sd/club.db.

import os
import time
import gc
import hdmi
import pcgui
import usqlite
from pcconfig import screen
from pcconsole import console
from pcgfx import WHITE, RED

DB_PATH = "/sd/club.db"
ROLES_FILE = "/sd/roles.txt"
STATUS_FILE = "/sd/status.txt"

DEFAULT_ROLES = ["", "President", "Secretary", "Treasurer", "Committee"]
DEFAULT_STATUS = ["Active", "Not Active"]

PAGE = 0x66B2FF
INK = 0x103018
BTN = 0x2E7D32

db = None


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


def stamp():
    t = time.localtime()
    return "%04d-%02d-%02d %02d:%02d" % (t[0], t[1], t[2], t[3], t[4])


def today():
    t = time.localtime()
    return "%04d-%02d-%02d" % (t[0], t[1], t[2])


def clock():
    t = time.localtime()
    return "%02d:%02d" % (t[3], t[4])


def one(sql, args=()):
    for row in db.execute(sql, args):
        return row
    return None


def rows(sql, args=()):
    return list(db.execute(sql, args))


def scalar(sql, args=()):
    r = one(sql, args)
    return r[0] if r else 0


def open_db():
    global db
    db = usqlite.connect(DB_PATH)
    db.execute("CREATE TABLE IF NOT EXISTS members(number INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT, status TEXT, financial TEXT, role TEXT, notes TEXT, visited TEXT, logbook TEXT, address TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS cars(id INTEGER PRIMARY KEY, member INTEGER, descr TEXT, rego TEXT, logbook TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS events(key TEXT PRIMARY KEY, name TEXT, date TEXT, time TEXT, place TEXT, notes TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS attend(evkey TEXT, member INTEGER, time TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS setting(k TEXT PRIMARY KEY, v TEXT)")
    db.execute("CREATE INDEX IF NOT EXISTS ix_name ON members(name)")
    db.execute("CREATE INDEX IF NOT EXISTS ix_car ON cars(member)")
    db.execute("CREATE INDEX IF NOT EXISTS ix_att ON attend(evkey)")
    # migration for an existing club.db that predates these columns
    try:
        db.execute("ALTER TABLE members ADD COLUMN logbook TEXT")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE members ADD COLUMN address TEXT")
    except Exception:
        pass


def setting(k, v=None):
    if v is None:
        r = one("SELECT v FROM setting WHERE k=?", (k,))
        return r[0] if r else ""
    db.execute("INSERT OR REPLACE INTO setting(k,v) VALUES(?,?)", (k, v))
    return v


def member_count():
    return scalar("SELECT COUNT(*) FROM members")


def find_members(text):
    text = text.strip()
    if not text:
        return rows("SELECT number, name, status FROM members ORDER BY number LIMIT 200")
    if text.isdigit():
        return rows("SELECT number, name, status FROM members WHERE number=?", (int(text),))
    p = "%" + text + "%"
    return rows("SELECT number, name, status FROM members WHERE name LIKE ? OR number IN (SELECT member FROM cars WHERE rego LIKE ?) ORDER BY name LIMIT 200", (p, p))


def get_member(num):
    return one("SELECT number, name, email, phone, status, financial, role, notes, visited, logbook, address FROM members WHERE number=?", (num,))


def put_member(num, name, email, phone, status, financial, role, notes, logbook, address):
    if get_member(num):
        db.execute("UPDATE members SET name=?, email=?, phone=?, status=?, financial=?, role=?, notes=?, logbook=?, address=?, visited=? WHERE number=?",
                   (name, email, phone, status, financial, role, notes, logbook, address, stamp(), num))
    else:
        db.execute("INSERT INTO members(number,name,email,phone,status,financial,role,notes,logbook,address,visited) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                   (num, name, email, phone, status, financial, role, notes, logbook, address, stamp()))


def member_cars(num):
    return rows("SELECT id, descr, rego, logbook FROM cars WHERE member=? ORDER BY id", (num,))


def add_car(num, descr, rego, logbook):
    db.execute("INSERT INTO cars(member,descr,rego,logbook) VALUES(?,?,?,?)", (num, descr, rego, logbook))


def update_car(cid, descr, rego, logbook):
    db.execute("UPDATE cars SET descr=?, rego=?, logbook=? WHERE id=?", (descr, rego, logbook, cid))


def drop_car(cid):
    db.execute("DELETE FROM cars WHERE id=?", (cid,))


def event_list():
    return rows("SELECT key, name, date FROM events ORDER BY key DESC LIMIT 100")


def get_event(key):
    return one("SELECT key, name, date, time, place, notes FROM events WHERE key=?", (key,))


def put_event(key, name, date, tim, place, notes):
    if get_event(key):
        db.execute("UPDATE events SET name=?, date=?, time=?, place=?, notes=? WHERE key=?", (name, date, tim, place, notes, key))
    else:
        db.execute("INSERT INTO events(key,name,date,time,place,notes) VALUES(?,?,?,?,?,?)", (key, name, date, tim, place, notes))


def attend_count(key):
    return scalar("SELECT COUNT(*) FROM attend WHERE evkey=?", (key,))


def check_in(num):
    key = setting("active")
    if not key:
        return "No event is running"
    r = one("SELECT time FROM attend WHERE evkey=? AND member=?", (key, num))
    if r:
        return "Member " + str(num) + " already in at " + r[0]
    t = clock()
    db.execute("INSERT INTO attend(evkey,member,time) VALUES(?,?,?)", (key, num, t))
    return "Checked in " + str(num) + " at " + t + "   (" + str(attend_count(key)) + " here)"


def drain():
    try:
        import sys
        import select
        p = select.poll()
        p.register(sys.stdin, select.POLLIN)
        while p.poll(0):
            sys.stdin.read(1)
    except Exception:
        pass


STATUS = read_list(STATUS_FILE, DEFAULT_STATUS)
ROLES = read_list(ROLES_FILE, DEFAULT_ROLES)
FINANCIAL = ["Yes", "No"]


class Page:
    def __init__(self):
        self.next = None

    def go(self, where):
        self.next = where

    def show(self):
        hdmi.fill(hdmi.fb().colour(PAGE))
        g = pcgui.GUI()
        self.g = g
        g.start()
        self.build(g)
        self.enter()
        while self.next is None:
            g.poll()
            time.sleep_ms(10)
        g.stop()
        gc.collect()
        return self.next

    def enter(self):
        pass

    def say(self, text):
        self.msg.value = text

    def footer(self, g):
        self.msg = g.displaybox(8, 450, 624, 26, "", fg=INK, bg=PAGE, font=2)


class Menu(Page):
    def build(self, g):
        g.caption(320, 10, "Car Club System", fg=INK, bg=PAGE, font=3, just="CT")
        g.button(60, 90, 200, 50, "MEMBERS", fg=WHITE, bg=BTN, font=3, callback=self.on_members)
        g.caption(288, 106, "Look up and edit records", fg=INK, bg=PAGE, font=2)
        g.button(60, 160, 200, 50, "EVENTS", fg=WHITE, bg=BTN, font=3, callback=self.on_events)
        g.caption(288, 176, "Run and record an event", fg=INK, bg=PAGE, font=2)
        g.button(60, 380, 200, 50, "QUIT", fg=WHITE, bg=RED, font=3, callback=self.on_quit)
        g.caption(288, 396, "Back to the prompt", fg=INK, bg=PAGE, font=2)
        self.info = g.displaybox(60, 250, 500, 26, "", fg=INK, bg=PAGE, font=2)
        self.ev = g.displaybox(60, 286, 500, 26, "", fg=INK, bg=PAGE, font=2)
        self.footer(g)

    def enter(self):
        self.info.value = str(member_count()) + " members on file"
        key = setting("active")
        if key:
            e = get_event(key)
            if e:
                self.ev.value = "Running: " + (e[1] or key) + "    " + str(attend_count(key)) + " checked in"
            else:
                self.ev.value = "Active event " + key + " is missing"
        else:
            self.ev.value = "No event running"
        self.say(stamp())

    def on_members(self, b):
        self.go("members")

    def on_events(self, b):
        self.go("events")

    def on_quit(self, b):
        self.go("exit")


class Members(Page):
    def build(self, g):
        self.num = 0
        self.found = []
        self.cars = []
        self.boxes = {}
        g.caption(320, 4, "Members", fg=INK, bg=PAGE, font=3, just="CT")
        g.caption(14, 40, "Find", fg=INK, bg=PAGE, font=2)
        self.search = g.textbox(70, 34, 240, 28, "", font=2, callback=self.on_search)
        g.button(320, 34, 90, 28, "SEARCH", fg=WHITE, bg=BTN, font=2, callback=self.on_search_btn)
        g.button(416, 34, 90, 28, "NEW", fg=WHITE, bg=BTN, font=2, callback=self.on_new)
        g.button(512, 34, 120, 28, "CHECK IN", fg=WHITE, bg=BTN, font=2, callback=self.on_checkin)
        self.list = None
        g.frame(262, 68, 370, 336, "Member", fg=INK, font=2)
        self.who = g.displaybox(274, 74, 346, 20, "nobody loaded", font=1)
        g.caption(274, 102, "No", fg=INK, bg=PAGE, font=2)
        self.mno = g.numberbox(330, 96, 80, 26, font=2)
        g.caption(274, 130, "Name", fg=INK, bg=PAGE, font=2)
        self.boxes["name"] = g.textbox(348, 124, 272, 26, font=2)
        g.caption(274, 158, "Email", fg=INK, bg=PAGE, font=2)
        self.boxes["email"] = g.textbox(348, 152, 272, 26, font=2)
        g.caption(274, 186, "Phone", fg=INK, bg=PAGE, font=2)
        self.boxes["phone"] = g.textbox(348, 180, 272, 26, font=2)
        g.caption(274, 214, "Logbook No", fg=INK, bg=PAGE, font=2)
        self.boxes["logbook"] = g.textbox(388, 208, 172, 26, font=2)
        g.caption(274, 242, "Address", fg=INK, bg=PAGE, font=2)
        self.boxes["address"] = g.textbox(348, 236, 272, 26, font=2)
        g.caption(274, 270, "Notes", fg=INK, bg=PAGE, font=2)
        self.boxes["notes"] = g.textbox(348, 264, 272, 26, font=2)
        g.caption(274, 298, "Status", fg=INK, bg=PAGE, font=1)
        self.status = g.listbox(274, 316, 130, 46, STATUS, 0, font=1)
        g.caption(414, 298, "Paid", fg=INK, bg=PAGE, font=1)
        self.fin = g.listbox(414, 316, 90, 46, FINANCIAL, 0, font=1)
        g.caption(514, 298, "Role", fg=INK, bg=PAGE, font=1)
        self.role = g.listbox(514, 316, 106, 46, ROLES, 0, font=1)
        self.seen = g.displaybox(274, 372, 346, 20, "", font=1)
        g.button(14, 400, 110, 32, "SAVE", fg=WHITE, bg=BTN, font=2, callback=self.on_save)
        g.button(132, 400, 110, 32, "CLEAR", fg=WHITE, bg=BTN, font=2, callback=self.on_clear)
        g.button(262, 400, 150, 32, "CARS", fg=WHITE, bg=BTN, font=2, callback=self.on_cars)
        g.button(522, 400, 110, 32, "MENU", fg=WHITE, bg=RED, font=2, callback=self.on_menu)
        self.footer(g)

    def enter(self):
        self.refresh("")
        self.say(str(member_count()) + " members -- type a name, number or rego")

    def refresh(self, text):
        self.found = find_members(text)
        items = []
        for num, name, status in self.found:
            tag = " " if status == "Active" else "-"
            items.append(tag + str(num) + "  " + (name or ""))
        if not items:
            items = ["(nothing found)"]
        if self.list is not None:
            self.g.remove(self.list)
        self.list = self.g.listbox(14, 72, 240, 300, items, 0, font=2, callback=self.on_pick)

    def on_search(self, c):
        self.refresh(c.value)
        self.say(str(len(self.found)) + " found")

    def on_search_btn(self, b):
        self.refresh(self.search.value)
        self.say(str(len(self.found)) + " found")

    def on_pick(self, c):
        i = c.value
        if i < 0 or i >= len(self.found):
            return
        self.load(self.found[i][0])

    def wipe(self):
        self.num = 0
        self.who.value = "nobody loaded"
        self.seen.value = ""
        for k in self.boxes:
            self.boxes[k].value = ""
        self.status.value = 0
        self.fin.value = 0
        self.role.value = 0

    def load(self, num):
        r = get_member(num)
        if r is None:
            self.wipe()
            self.say("No record for " + str(num))
            return
        self.num = num
        self.mno.value = num
        self.who.value = "MEMBER " + str(num) + "   " + (r[1] or "")
        self.boxes["name"].value = r[1] or ""
        self.boxes["email"].value = r[2] or ""
        self.boxes["phone"].value = r[3] or ""
        self.boxes["notes"].value = r[7] or ""
        self.boxes["logbook"].value = r[9] or ""
        self.boxes["address"].value = r[10] or ""
        s = r[4] or STATUS[0]
        self.status.value = STATUS.index(s) if s in STATUS else 0
        f = r[5] or "Yes"
        self.fin.value = FINANCIAL.index(f) if f in FINANCIAL else 0
        ro = r[6] or ""
        self.role.value = ROLES.index(ro) if ro in ROLES else 0
        cars = member_cars(num)
        extra = "" if len(cars) < 2 else "   (" + str(len(cars)) + " cars)"
        self.seen.value = "Last seen: " + (r[8] or "never") + extra
        self.say("Loaded member " + str(num))

    def number(self):
        try:
            return int(self.mno.number)
        except (ValueError, TypeError):
            return 0

    def on_new(self, b):
        self.wipe()
        n = scalar("SELECT COALESCE(MAX(number),0)+1 FROM members")
        self.mno.value = n
        self.who.value = "NEW MEMBER " + str(n)
        self.say("New member " + str(n) + " -- edit the number if you want, then SAVE")

    def on_save(self, b):
        n = self.number()
        if n <= 0:
            self.say("Enter a member number")
            return
        put_member(n, self.boxes["name"].value, self.boxes["email"].value,
                   self.boxes["phone"].value, STATUS[self.status.value],
                   FINANCIAL[self.fin.value], ROLES[self.role.value],
                   self.boxes["notes"].value, self.boxes["logbook"].value,
                   self.boxes["address"].value)
        self.num = n
        self.who.value = "MEMBER " + str(n) + "   " + self.boxes["name"].value
        self.seen.value = "Last seen: " + stamp()
        self.refresh(self.search.value)
        self.say("Saved member " + str(n))

    def on_checkin(self, b):
        n = self.number()
        if n <= 0:
            self.say("Load a member first")
            return
        if get_member(n) is None:
            self.say("No record for " + str(n) + " -- save it first")
            return
        self.say(check_in(n))

    def on_cars(self, b):
        n = self.number()
        if n <= 0 or get_member(n) is None:
            self.say("Load a member first")
            return
        self.pick_member = n
        self.go("cars")

    def on_clear(self, b):
        self.wipe()
        self.say("Cleared")

    def on_menu(self, b):
        self.go("menu")


class Cars(Page):
    def __init__(self, num):
        Page.__init__(self)
        self.num = num
        self.cid = None

    def build(self, g):
        r = get_member(self.num)
        who = r[1] if r else ""
        g.caption(320, 6, "Cars", fg=INK, bg=PAGE, font=3, just="CT")
        g.caption(14, 44, "Member " + str(self.num) + "   " + (who or ""), fg=INK, bg=PAGE, font=2)
        self.list = None
        g.frame(324, 68, 308, 200, "Car", fg=INK, font=2)
        g.caption(336, 104, "Car", fg=INK, bg=PAGE, font=2)
        self.descr = g.textbox(410, 98, 210, 26, font=2)
        g.caption(336, 140, "Rego", fg=INK, bg=PAGE, font=2)
        self.rego = g.textbox(410, 134, 210, 26, font=2)
        g.caption(336, 176, "Logbook", fg=INK, bg=PAGE, font=2)
        self.logbook = g.textbox(410, 170, 210, 26, font=2)
        g.caption(336, 210, "Logbook is for historic rego", fg=INK, bg=PAGE, font=1)
        g.button(324, 282, 96, 32, "ADD", fg=WHITE, bg=BTN, font=2, callback=self.on_add)
        g.button(428, 282, 96, 32, "SAVE", fg=WHITE, bg=BTN, font=2, callback=self.on_save)
        g.button(532, 282, 100, 32, "DELETE", fg=WHITE, bg=RED, font=2, callback=self.on_del)
        g.button(14, 382, 150, 32, "BACK", fg=WHITE, bg=RED, font=2, callback=self.on_back)
        self.footer(g)

    def enter(self):
        self.refresh()

    def refresh(self):
        self.cars = member_cars(self.num)
        items = []
        for cid, descr, rego, logbook in self.cars:
            line = (descr or "?")
            if rego:
                line = line + "  " + rego
            if logbook:
                line = line + "  LB" + logbook
            items.append(line)
        if not items:
            items = ["(none yet)"]
        if self.list is not None:
            self.g.remove(self.list)
        self.list = self.g.listbox(14, 76, 300, 260, items, 0, font=2, callback=self.on_pick)
        self.say(str(len(self.cars)) + " cars on file")

    def on_pick(self, c):
        i = c.value
        if i < 0 or i >= len(self.cars):
            return
        cid, descr, rego, logbook = self.cars[i]
        self.cid = cid
        self.descr.value = descr or ""
        self.rego.value = rego or ""
        self.logbook.value = logbook or ""
        self.say("Editing car " + str(cid))

    def on_add(self, b):
        if not self.descr.value.strip():
            self.say("Type the car in the box first")
            return
        add_car(self.num, self.descr.value, self.rego.value, self.logbook.value)
        self.descr.value = ""
        self.rego.value = ""
        self.logbook.value = ""
        self.cid = None
        self.refresh()
        self.say("Car added")

    def on_save(self, b):
        if self.cid is None:
            self.say("Pick a car from the list, or press ADD")
            return
        update_car(self.cid, self.descr.value, self.rego.value, self.logbook.value)
        self.refresh()
        self.say("Car saved")

    def on_del(self, b):
        if self.cid is None:
            self.say("Pick a car from the list first")
            return
        drop_car(self.cid)
        self.cid = None
        self.descr.value = ""
        self.rego.value = ""
        self.logbook.value = ""
        self.refresh()
        self.say("Car deleted")

    def on_back(self, b):
        self.go("members")


class Events(Page):
    def build(self, g):
        self.key = None
        g.caption(320, 6, "Events", fg=INK, bg=PAGE, font=3, just="CT")
        g.frame(8, 40, 300, 300, "On file", fg=INK, font=2)
        self.list = None
        g.frame(316, 40, 316, 300, "Details", fg=INK, font=2)
        g.caption(330, 76, "Name", fg=INK, bg=PAGE, font=2)
        self.name = g.textbox(420, 70, 200, 26, font=2)
        g.caption(330, 112, "Date", fg=INK, bg=PAGE, font=2)
        self.date = g.textbox(420, 106, 200, 26, font=2)
        g.caption(330, 148, "Time", fg=INK, bg=PAGE, font=2)
        self.tim = g.textbox(420, 142, 200, 26, font=2)
        g.caption(330, 184, "Place", fg=INK, bg=PAGE, font=2)
        self.place = g.textbox(420, 178, 200, 26, font=2)
        g.caption(330, 220, "Notes", fg=INK, bg=PAGE, font=2)
        self.notes = g.textbox(420, 214, 200, 26, font=2)
        self.count = g.displaybox(330, 250, 290, 20, "", font=1)
        self.act = g.displaybox(330, 276, 290, 20, "", font=1)
        g.button(8, 352, 100, 32, "NEW", fg=WHITE, bg=BTN, font=2, callback=self.on_new)
        g.button(116, 352, 100, 32, "SAVE", fg=WHITE, bg=BTN, font=2, callback=self.on_save)
        g.button(224, 352, 110, 32, "START", fg=WHITE, bg=BTN, font=2, callback=self.on_start)
        g.button(342, 352, 100, 32, "STOP", fg=WHITE, bg=BTN, font=2, callback=self.on_stop)
        g.button(8, 400, 180, 32, "WHO CAME", fg=WHITE, bg=BTN, font=2, callback=self.on_who)
        g.button(522, 400, 110, 32, "MENU", fg=WHITE, bg=RED, font=2, callback=self.on_menu)
        self.footer(g)

    def enter(self):
        self.refresh()
        if self.evs:
            self.load(0)
        else:
            self.say("No events yet -- press NEW")

    def refresh(self):
        self.evs = event_list()
        items = []
        for key, name, date in self.evs:
            items.append(key + "  " + (name or ""))
        if not items:
            items = ["(none yet)"]
        if self.list is not None:
            self.g.remove(self.list)
        self.list = self.g.listbox(20, 66, 276, 260, items, 0, font=2, callback=self.on_pick)

    def load(self, i):
        if i < 0 or i >= len(self.evs):
            return
        key = self.evs[i][0]
        e = get_event(key)
        if e is None:
            self.say("Cannot read that event")
            return
        self.key = key
        self.name.value = e[1] or ""
        self.date.value = e[2] or ""
        self.tim.value = e[3] or ""
        self.place.value = e[4] or ""
        self.notes.value = e[5] or ""
        self.count.value = str(attend_count(key)) + " checked in"
        self.act.value = "RUNNING NOW" if setting("active") == key else ""
        self.say("Loaded " + key)

    def on_pick(self, c):
        self.load(c.value)

    def on_new(self, b):
        key = today()
        n = 1
        while get_event(key) is not None:
            n = n + 1
            key = today() + "-" + str(n)
        put_event(key, "", today(), clock(), "", "")
        self.key = key
        self.refresh()
        self.name.value = ""
        self.date.value = today()
        self.tim.value = clock()
        self.place.value = ""
        self.notes.value = ""
        self.count.value = "0 checked in"
        self.act.value = ""
        self.say("New event " + key + " -- fill in and SAVE")

    def on_save(self, b):
        if self.key is None:
            self.say("Nothing to save -- press NEW")
            return
        put_event(self.key, self.name.value, self.date.value, self.tim.value,
                  self.place.value, self.notes.value)
        self.refresh()
        self.say("Saved " + self.key)

    def on_start(self, b):
        if self.key is None:
            self.say("Pick an event first")
            return
        setting("active", self.key)
        self.act.value = "RUNNING NOW"
        self.say(self.key + " is running -- check-ins go to it")

    def on_stop(self, b):
        setting("active", "")
        self.act.value = ""
        self.say("No event running now")

    def on_who(self, b):
        if self.key is None:
            self.say("Pick an event first")
            return
        rs = rows("SELECT a.member, m.name, a.time FROM attend a LEFT JOIN members m ON m.number=a.member WHERE a.evkey=? ORDER BY a.time", (self.key,))
        if not rs:
            self.say("Nobody checked in yet")
            return
        line = ""
        for num, name, t in rs:
            bit = str(num) + " " + (name.split(" ")[0] if name else "") + "  "
            if len(line) + len(bit) > 58:
                break
            line = line + bit
        self.say(str(len(rs)) + " here: " + line)

    def on_menu(self, b):
        self.go("menu")


def main():
    open_db()
    screen(hdmi.RGB640)
    time.sleep(3)
    console("serial")
    where = "menu"
    who = 0
    try:
        while where != "exit":
            if where == "menu":
                where = Menu().show()
            elif where == "members":
                p = Members()
                where = p.show()
                if where == "cars":
                    who = p.pick_member
            elif where == "cars":
                where = Cars(who).show()
            elif where == "events":
                where = Events().show()
            else:
                where = "menu"
    finally:
        console("both")
        hdmi.fill(0)
        try:
            db.close()
        except Exception:
            pass
        drain()


main()