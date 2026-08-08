# club.py -- car club system
# Pico Computer 3, MicroPython.  One program, several pages.
# Data lives in SQLite at /sd/club.db.
#
# VERSION 0.50

CLUB_VERSION = "0.50"

import os
import time
import gc
import math
import hdmi
import pcgui
import usqlite
import network
import socket
try:
    import ssl
except ImportError:
    import ussl as ssl
import struct
import pcimage
import ubinascii as binascii
from pcconfig import screen
from pcconsole import console
from pcgfx import WHITE, RED

DB_PATH = "/sd/club.db"
ROLES_FILE = "/sd/roles.txt"
STATUS_FILE = "/sd/status.txt"
WIFI_FILE = "/sd/wifi.txt"
WIFI_KEY = "clubkey"   # single word used to obfuscate the saved wifi password
FORWARD_FILE = "/sd/forward.txt"   # IP of another board to relay new uploads to

DEFAULT_ROLES = ["", "President", "Secretary", "Treasurer", "Committee"]
DEFAULT_STATUS = ["Active", "Not Active"]

UPLOAD_LOG = "/sd/upload_log.txt"
EXPORT_DIR = "/sd/exports"
IMPORT_DIR = "/sd/imported"   # non-photo files copied in via Import from SD
MODELS_DIR = "/sd/models"     # saved 3D models from the Model Editor

# ---------- Email settings: fill in SMTP_PASSWORD before using EMAIL ----------
SMTP_SERVER = "smtp.telstra.com"
SMTP_PORT = 587
SMTP_USER = "your.email@example.com"
SMTP_PASSWORD = "PUT_YOUR_PASSWORD_HERE"
EMAIL_TO = "your.email@example.com"
# ------------------------------------------------------------------------------


def pad_right(s, width):
    # like str.ljust() -- pad spaces on the right so the text is
    # left-aligned. Written by hand because this board's MicroPython
    # build doesn't provide str.ljust()/str.rjust() and calling them
    # raises AttributeError.
    s = str(s)
    if len(s) >= width:
        return s
    return s + (" " * (width - len(s)))


def pad_left(s, width):
    # like str.rjust() -- pad spaces on the left so the text is
    # right-aligned. See pad_right() above for why this exists.
    s = str(s)
    if len(s) >= width:
        return s
    return (" " * (width - len(s))) + s


def csv_escape(val):
    s = "" if val is None else str(val)
    if "," in s or "\"" in s or "\n" in s:
        s = "\"" + s.replace("\"", "\"\"") + "\""
    return s


def write_csv(path, headers, data_rows):
    f = open(path, "w")
    try:
        f.write(",".join(csv_escape(h) for h in headers) + "\n")
        for r in data_rows:
            f.write(",".join(csv_escape(v) for v in r) + "\n")
    finally:
        f.close()


def csv_parse_line(line):
    # minimal CSV line parser, matching csv_escape's quoting rules
    fields = []
    i = 0
    n = len(line)
    while i <= n:
        if i < n and line[i] == '"':
            i += 1
            buf = []
            while i < n:
                if line[i] == '"':
                    if i + 1 < n and line[i + 1] == '"':
                        buf.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                buf.append(line[i])
                i += 1
            fields.append("".join(buf))
            if i < n and line[i] == ",":
                i += 1
            else:
                i += 1
        else:
            start = i
            while i < n and line[i] != ",":
                i += 1
            fields.append(line[start:i])
            i += 1
    return fields


def import_members_csv(path):
    f = open(path)
    try:
        text = f.read()
    finally:
        f.close()
    lines = [l for l in text.split("\n") if l.strip()]
    if len(lines) < 2:
        return 0
    count = 0
    for line in lines[1:]:
        fields = csv_parse_line(line)
        if len(fields) < 11:
            continue
        while len(fields) < 12:
            fields.append("")
        number, name, email, phone, status, financial, role, notes, visited, logbook, address, photo = fields[:12]
        try:
            num = int(number)
        except ValueError:
            continue
        db.execute(
            "INSERT OR REPLACE INTO members(number,name,email,phone,status,financial,role,notes,visited,logbook,address,photo) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (num, name, email, phone, status, financial, role, notes, visited, logbook, address, photo))
        count += 1
    return count


def import_cars_csv(path):
    f = open(path)
    try:
        text = f.read()
    finally:
        f.close()
    lines = [l for l in text.split("\n") if l.strip()]
    if len(lines) < 2:
        return 0
    count = 0
    for line in lines[1:]:
        fields = csv_parse_line(line)
        if len(fields) < 5:
            continue
        while len(fields) < 6:
            fields.append("")
        cid, member, descr, rego, logbook, photo = fields[:6]
        try:
            member_num = int(member)
        except ValueError:
            continue
        try:
            cid_int = int(cid)
        except ValueError:
            cid_int = None
        if cid_int is not None and one("SELECT id FROM cars WHERE id=?", (cid_int,)):
            db.execute("UPDATE cars SET member=?, descr=?, rego=?, logbook=?, photo=? WHERE id=?",
                       (member_num, descr, rego, logbook, photo, cid_int))
        else:
            db.execute("INSERT INTO cars(member,descr,rego,logbook,photo) VALUES(?,?,?,?,?)",
                       (member_num, descr, rego, logbook, photo))
        count += 1
    return count


def import_events_csv(path):
    f = open(path)
    try:
        text = f.read()
    finally:
        f.close()
    lines = [l for l in text.split("\n") if l.strip()]
    if len(lines) < 2:
        return 0
    count = 0
    for line in lines[1:]:
        fields = csv_parse_line(line)
        if len(fields) < 6:
            continue
        while len(fields) < 9:
            fields.append("")
        key, name, date, tim, place, notes, photo, lat, lon = fields[:9]
        if not key:
            continue
        if get_event(key):
            db.execute("UPDATE events SET name=?, date=?, time=?, place=?, notes=?, photo=?, lat=?, lon=? WHERE key=?",
                       (name, date, tim, place, notes, photo, lat, lon, key))
        else:
            db.execute("INSERT INTO events(key,name,date,time,place,notes,photo,lat,lon) VALUES(?,?,?,?,?,?,?,?,?)",
                       (key, name, date, tim, place, notes, photo, lat, lon))
        count += 1
    return count



def ulog(text):
    try:
        f = open(UPLOAD_LOG, "a")
        t = time.localtime()
        s = "%04d-%02d-%02d %02d:%02d:%02d  " % (t[0], t[1], t[2], t[3], t[4], t[5])
        f.write(s + text + "\n")
        f.close()
    except Exception:
        pass


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


def wifi_scramble(text, key):
    # simple XOR obfuscation -- NOT real security, just avoids
    # the password sitting in plain readable text in the file.
    out = []
    for i in range(len(text)):
        c = ord(text[i]) ^ ord(key[i % len(key)])
        out.append(c)
    return out


def wifi_encode(password):
    vals = wifi_scramble(password, WIFI_KEY)
    return ",".join(str(v) for v in vals)


def wifi_decode(blob):
    if not blob:
        return ""
    vals = [int(v) for v in blob.split(",") if v != ""]
    chars = []
    for i in range(len(vals)):
        c = vals[i] ^ ord(WIFI_KEY[i % len(WIFI_KEY)])
        chars.append(chr(c))
    return "".join(chars)


def load_wifi_list():
    # file format: pairs of lines, SSID then encoded password, repeated
    # for each saved network. A file saved by the old single-network
    # code (one SSID + one password line) still loads fine as a
    # one-entry list.
    try:
        f = open(WIFI_FILE)
        text = f.read()
        f.close()
    except OSError:
        return []
    lines = text.split("\n")
    nets = []
    i = 0
    while i + 1 < len(lines) or (i < len(lines) and lines[i].strip()):
        ssid = lines[i].strip() if i < len(lines) else ""
        pwd_blob = lines[i + 1] if i + 1 < len(lines) else ""
        if ssid:
            nets.append((ssid, wifi_decode(pwd_blob)))
        i += 2
    return nets


def save_wifi_list(nets):
    f = open(WIFI_FILE, "w")
    for ssid, password in nets:
        f.write(ssid + "\n")
        f.write(wifi_encode(password) + "\n")
    f.close()


def upsert_wifi(ssid, password):
    # adds a new saved network, or updates the password if that SSID
    # is already saved
    nets = load_wifi_list()
    for i, (s, p) in enumerate(nets):
        if s == ssid:
            nets[i] = (ssid, password)
            save_wifi_list(nets)
            return nets
    nets.append((ssid, password))
    save_wifi_list(nets)
    return nets


def remove_wifi(ssid):
    nets = [(s, p) for s, p in load_wifi_list() if s != ssid]
    save_wifi_list(nets)
    return nets


def load_wifi():
    # back-compat helper: just the most recently saved network
    nets = load_wifi_list()
    return nets[-1] if nets else ("", "")


def save_wifi(ssid, password):
    upsert_wifi(ssid, password)


def synctime():
    # syncs the RTC via NTP (needs a working internet route -- plain
    # STA connect to a real router, not just AP mode with no upstream)
    # and adjusts for +9:30 (Adelaide/Central Australia, matching
    # Tailem Bend) since NTP itself is always UTC.
    try:
        import ntptime
        import machine
        ntptime.settime()
        t = time.localtime(time.time() + 9 * 3600 + 30 * 60)
        rtc = machine.RTC()
        rtc.datetime((t[0], t[1], t[2], t[6], t[3], t[4], t[5], 0))
        return True
    except Exception as e:
        ulog("synctime failed: " + str(e))
        return False


def load_forward_ips():
    try:
        f = open(FORWARD_FILE)
        text = f.read()
        f.close()
    except OSError:
        return []
    return [l.strip() for l in text.split("\n") if l.strip()]


def save_forward_ips(ips):
    f = open(FORWARD_FILE, "w")
    for ip in ips:
        f.write(ip + "\n")
    f.close()


def add_forward_ip(ip):
    ips = load_forward_ips()
    if ip not in ips:
        ips.append(ip)
        save_forward_ips(ips)
    return ips


def remove_forward_ip(ip):
    ips = [i for i in load_forward_ips() if i != ip]
    save_forward_ips(ips)
    return ips


def load_forward_ip():
    # back-compat helper: first saved board, used by places that still
    # want a single target (e.g. Export/Import's manual send box)
    ips = load_forward_ips()
    return ips[0] if ips else ""


def save_forward_ip(ip):
    if ip:
        add_forward_ip(ip)
    else:
        save_forward_ips([])


def url_quote(s):
    safe = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
    out = []
    for ch in s:
        if ch in safe:
            out.append(ch)
        else:
            out.append("%%%02X" % ord(ch))
    return "".join(out)


def forward_upload(ip, path, filename, max_seconds=45):
    # re-POSTs an already-saved file to another board's /upload/
    # endpoint -- used so a "relay" board can pass new photos on to
    # the main board automatically.
    #
    # NOTE: this runs synchronously in the single GUI thread -- for a
    # small CSV that's a sub-second blip, but for a photo it can
    # freeze the screen for several seconds with no feedback while it
    # runs. max_seconds bounds the WHOLE transfer so a stalled/slow
    # connection fails outright instead of hanging indefinitely.
    ulog("forward_upload: starting, ip=" + ip + " file=" + filename)
    start = time.ticks_ms()
    try:
        size = os.stat(path)[6]
        ulog("forward_upload: size=" + str(size) + " connecting...")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((ip, 8080))
        ulog("forward_upload: connected, sending headers")
        try:
            header = ("POST /upload/" + url_quote(filename) + " HTTP/1.1\r\n" +
                       "Host: " + ip + "\r\n" +
                       "Content-Length: " + str(size) + "\r\n" +
                       "Connection: close\r\n\r\n")
            s.send(header.encode())
            ulog("forward_upload: headers sent, streaming body")
            f = open(path, "rb")
            sent = 0
            try:
                while True:
                    if time.ticks_diff(time.ticks_ms(), start) > max_seconds * 1000:
                        raise RuntimeError("transfer exceeded " + str(max_seconds) + "s, aborting")
                    chunk = f.read(2048)
                    if not chunk:
                        break
                    s.send(chunk)
                    sent += len(chunk)
            finally:
                f.close()
            elapsed = time.ticks_diff(time.ticks_ms(), start) / 1000
            ulog("forward_upload: body sent, " + str(sent) + " of " + str(size) +
                 " bytes in " + str(elapsed) + "s")
            try:
                resp = s.recv(200)
                ulog("forward_upload: response=" + str(resp))
            except Exception as e:
                ulog("forward_upload: no response read: " + str(e))
        finally:
            s.close()
        ulog("forward_upload: done, closed socket")
        return True
    except Exception as e:
        ulog("forward_upload: EXCEPTION " + type(e).__name__ + " " + str(e))
        return False


def _smtp_read_line(sock):
    line = b""
    while not line.endswith(b"\r\n"):
        chunk = sock.read(1)
        if not chunk:
            break
        line += chunk
    return line


def _smtp_command(sock, command, expect_code=None):
    if command is not None:
        sock.write(command + b"\r\n")
    response = b""
    while True:
        line = _smtp_read_line(sock)
        response += line
        if len(line) < 4 or line[3:4] != b"-":
            break
    code = int(response[:3])
    if expect_code and code != expect_code:
        raise RuntimeError("SMTP error: %s" % response)
    return code, response


def _build_mime_message(sender, to, subject, body_text, attach_filename, attach_bytes):
    boundary = "club_py_boundary_123456"
    b64 = binascii.b2a_base64(attach_bytes).decode().strip()
    b64_lines = [b64[i:i + 76] for i in range(0, len(b64), 76)]
    b64_wrapped = "\r\n".join(b64_lines)
    return (
        "From: {sender}\r\n"
        "To: {to}\r\n"
        "Subject: {subject}\r\n"
        "MIME-Version: 1.0\r\n"
        "Content-Type: multipart/mixed; boundary=\"{boundary}\"\r\n"
        "\r\n"
        "--{boundary}\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "{body}\r\n"
        "\r\n"
        "--{boundary}\r\n"
        "Content-Type: text/csv; name=\"{filename}\"\r\n"
        "Content-Transfer-Encoding: base64\r\n"
        "Content-Disposition: attachment; filename=\"{filename}\"\r\n"
        "\r\n"
        "{data}\r\n"
        "\r\n"
        "--{boundary}--\r\n"
    ).format(sender=sender, to=to, subject=subject, boundary=boundary,
             body=body_text, filename=attach_filename, data=b64_wrapped)


def _plain_message(sender, to, subject, body_text):
    return (
        "From: {sender}\r\n"
        "To: {to}\r\n"
        "Subject: {subject}\r\n"
        "MIME-Version: 1.0\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "{body}\r\n"
    ).format(sender=sender, to=to, subject=subject, body=body_text)


def _smtp_connect_and_auth():
    # shared connect+STARTTLS+login sequence used by both email senders
    addr = socket.getaddrinfo(SMTP_SERVER, SMTP_PORT)[0][-1]
    raw_sock = socket.socket()
    raw_sock.settimeout(15)
    raw_sock.connect(addr)
    _smtp_command(raw_sock, None)
    _smtp_command(raw_sock, b"EHLO club-py", expect_code=250)
    _smtp_command(raw_sock, b"STARTTLS", expect_code=220)

    sock = ssl.wrap_socket(raw_sock)
    _smtp_command(sock, b"EHLO club-py", expect_code=250)

    _smtp_command(sock, b"AUTH LOGIN", expect_code=334)
    _smtp_command(sock, binascii.b2a_base64(SMTP_USER.encode()).strip(), expect_code=334)
    _smtp_command(sock, binascii.b2a_base64(SMTP_PASSWORD.encode()).strip(), expect_code=235)
    return sock


def _send_plain_email(to_addr, subject, body_text):
    # Sends a simple text email with no attachment -- used by the
    # "EMAIL" button on the Members page to message an individual member.
    sock = _smtp_connect_and_auth()
    _smtp_command(sock, ("MAIL FROM:<%s>" % SMTP_USER).encode(), expect_code=250)
    _smtp_command(sock, ("RCPT TO:<%s>" % to_addr).encode(), expect_code=250)
    _smtp_command(sock, b"DATA", expect_code=354)
    message = _plain_message(SMTP_USER, to_addr, subject, body_text)
    sock.write(message.encode())
    _smtp_command(sock, b".", expect_code=250)
    _smtp_command(sock, b"QUIT")
    sock.close()


def send_csv_email(csv_path, subject=None, to_addr=None):
    # Emails a CSV file already saved on the SD card. Assumes Wi-Fi is
    # already connected (this board connects at boot / via the WIFI page).
    to_addr = to_addr or EMAIL_TO
    with open(csv_path, "rb") as f:
        data = f.read()
    filename = csv_path.split("/")[-1]

    addr = socket.getaddrinfo(SMTP_SERVER, SMTP_PORT)[0][-1]
    raw_sock = socket.socket()
    raw_sock.settimeout(15)
    raw_sock.connect(addr)
    _smtp_command(raw_sock, None)
    _smtp_command(raw_sock, b"EHLO club-py", expect_code=250)
    _smtp_command(raw_sock, b"STARTTLS", expect_code=220)

    sock = ssl.wrap_socket(raw_sock)
    _smtp_command(sock, b"EHLO club-py", expect_code=250)

    _smtp_command(sock, b"AUTH LOGIN", expect_code=334)
    _smtp_command(sock, binascii.b2a_base64(SMTP_USER.encode()).strip(), expect_code=334)
    _smtp_command(sock, binascii.b2a_base64(SMTP_PASSWORD.encode()).strip(), expect_code=235)

    _smtp_command(sock, ("MAIL FROM:<%s>" % SMTP_USER).encode(), expect_code=250)
    _smtp_command(sock, ("RCPT TO:<%s>" % to_addr).encode(), expect_code=250)
    _smtp_command(sock, b"DATA", expect_code=354)

    message = _build_mime_message(
        sender=SMTP_USER, to=to_addr,
        subject=subject or ("CSV file: %s" % filename),
        body_text="Attached: %s" % filename,
        attach_filename=filename, attach_bytes=data,
    )
    sock.write(message.encode())
    _smtp_command(sock, b".", expect_code=250)
    _smtp_command(sock, b"QUIT")
    sock.close()

    return "Emailed %s to %s" % (filename, to_addr)


def stamp():
    t = time.localtime()
    return "%04d-%02d-%02d %02d:%02d" % (t[0], t[1], t[2], t[3], t[4])


def display_stamp():
    # day-month-year format for the on-screen ticker, e.g. "4-8-2026 16:44:01"
    t = time.localtime()
    return "%d-%d-%d %02d:%02d:%02d" % (t[2], t[1], t[0], t[3], t[4], t[5])


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
    try:
        db.execute("ALTER TABLE members ADD COLUMN photo TEXT")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE cars ADD COLUMN photo TEXT")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE events ADD COLUMN photo TEXT")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE events ADD COLUMN lat TEXT")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE events ADD COLUMN lon TEXT")
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
    return one("SELECT number, name, email, phone, status, financial, role, notes, visited, logbook, address, photo FROM members WHERE number=?", (num,))


def put_member(num, name, email, phone, status, financial, role, notes, logbook, address):
    if get_member(num):
        db.execute("UPDATE members SET name=?, email=?, phone=?, status=?, financial=?, role=?, notes=?, logbook=?, address=?, visited=? WHERE number=?",
                   (name, email, phone, status, financial, role, notes, logbook, address, stamp(), num))
    else:
        db.execute("INSERT INTO members(number,name,email,phone,status,financial,role,notes,logbook,address,visited) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                   (num, name, email, phone, status, financial, role, notes, logbook, address, stamp()))


def set_photo(num, filename):
    db.execute("UPDATE members SET photo=? WHERE number=?", (filename, num))


def delete_member(num):
    db.execute("DELETE FROM cars WHERE member=?", (num,))
    db.execute("DELETE FROM members WHERE number=?", (num,))


def member_cars(num):
    return rows("SELECT id, descr, rego, logbook, photo FROM cars WHERE member=? ORDER BY id", (num,))


def add_car(num, descr, rego, logbook):
    db.execute("INSERT INTO cars(member,descr,rego,logbook) VALUES(?,?,?,?)", (num, descr, rego, logbook))


def update_car(cid, descr, rego, logbook):
    db.execute("UPDATE cars SET descr=?, rego=?, logbook=? WHERE id=?", (descr, rego, logbook, cid))


def get_car_photo(cid):
    r = one("SELECT photo FROM cars WHERE id=?", (cid,))
    return (r[0] if r else "") or ""


def set_car_photo(cid, filename):
    db.execute("UPDATE cars SET photo=? WHERE id=?", (filename, cid))


def drop_car(cid):
    db.execute("DELETE FROM cars WHERE id=?", (cid,))


def event_list():
    return rows("SELECT key, name, date FROM events ORDER BY key DESC LIMIT 100")


def get_event(key):
    return one("SELECT key, name, date, time, place, notes, photo, lat, lon FROM events WHERE key=?", (key,))


def put_event(key, name, date, tim, place, notes):
    if get_event(key):
        db.execute("UPDATE events SET name=?, date=?, time=?, place=?, notes=? WHERE key=?", (name, date, tim, place, notes, key))
    else:
        db.execute("INSERT INTO events(key,name,date,time,place,notes) VALUES(?,?,?,?,?,?)", (key, name, date, tim, place, notes))


def set_event_photo(key, filename):
    db.execute("UPDATE events SET photo=? WHERE key=?", (filename, key))


def set_event_location(key, lat, lon):
    db.execute("UPDATE events SET lat=?, lon=? WHERE key=?", (str(lat), str(lon), key))


def delete_event(key):
    db.execute("DELETE FROM attend WHERE evkey=?", (key,))
    db.execute("DELETE FROM events WHERE key=?", (key,))


# --- GPS ---------------------------------------------------------
# Assumes a standard NMEA-output GPS module (e.g. NEO-6M) wired to
# UART0 at the default Pico pins (TX=GP0, RX=GP1), 9600 baud -- the
# usual out-of-the-box wiring/settings for these modules. If your
# module is wired to different pins or a different UART, change
# GPS_UART_ID / GPS_TX_PIN / GPS_RX_PIN / GPS_BAUD below to match.
GPS_UART_ID = 0
GPS_TX_PIN = 0
GPS_RX_PIN = 1
GPS_BAUD = 9600


def nmea_to_decimal(raw, direction):
    # NMEA lat/lon are in ddmm.mmmm / dddmm.mmmm format, not plain
    # decimal degrees -- convert to decimal degrees here.
    if not raw:
        return None
    dot = raw.find(".")
    if dot < 2:
        return None
    deg_digits = dot - 2
    deg = float(raw[:deg_digits])
    minutes = float(raw[deg_digits:])
    val = deg + minutes / 60.0
    if direction in ("S", "W"):
        val = -val
    return val


def parse_gprmc(line):
    # $GPRMC,time,status,lat,N/S,lon,E/W,speed,course,date,...
    if not line.startswith("$GPRMC") and not line.startswith("$GNRMC"):
        return None
    parts = line.split(",")
    # only lat/lon/status (fields 0-6) are actually required for a
    # usable fix -- date/speed/course are read opportunistically
    # below if present, since some modules omit the trailing optional
    # fields (magnetic variation etc.) entirely. Requiring 10 fields
    # here (as an earlier version of this did) rejected perfectly
    # good fixes from modules that send a shorter sentence.
    if len(parts) < 7 or parts[2] != "A":
        return None  # 'A' = active/valid fix, 'V' = void/no fix
    lat = nmea_to_decimal(parts[3], parts[4])
    lon = nmea_to_decimal(parts[5], parts[6])
    if lat is None or lon is None:
        return None
    utc = None
    try:
        t = parts[1]  # hhmmss.ss
        d = parts[9] if len(parts) > 9 else ""  # ddmmyy
        if len(t) >= 6 and len(d) == 6:
            hh, mi, ss = int(t[0:2]), int(t[2:4]), int(t[4:6])
            dd, mo, yy = int(d[0:2]), int(d[2:4]), int(d[4:6]) + 2000
            utc = (yy, mo, dd, hh, mi, ss)
    except Exception:
        utc = None  # fix is still good even if the date/time didn't parse
    speed_kn = None
    try:
        if len(parts) > 7 and parts[7]:
            speed_kn = float(parts[7])
    except Exception:
        speed_kn = None
    course_deg = None
    try:
        if len(parts) > 8 and parts[8]:
            course_deg = float(parts[8])
    except Exception:
        course_deg = None
    return (lat, lon, utc, speed_kn, course_deg)


def read_gps_fix_full(timeout_ms=4000):
    # returns ((lat, lon, utc_or_None, speed_knots_or_None,
    # course_deg_or_None), None) on success, or (None, error_message)
    # on failure -- wrapped in broad try/except since we can't confirm
    # the module/wiring is actually present on any given board.
    # utc_or_None is (year, month, day, hour, min, sec) straight from
    # the GPS's own UTC clock, when the sentence included it -- this
    # is what STAR uses for "current time" since it's far more
    # trustworthy than an onboard RTC that may not be battery-backed
    # or synced. speed/course come from the same GPRMC sentence.
    try:
        import machine
        uart = machine.UART(GPS_UART_ID, baudrate=GPS_BAUD,
                              tx=machine.Pin(GPS_TX_PIN), rx=machine.Pin(GPS_RX_PIN))
    except Exception as e:
        return None, "GPS UART error: " + str(e)
    start = time.ticks_ms()
    buf = b""
    try:
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            n = uart.any()
            if n:
                chunk = uart.read(n)
                if chunk:
                    buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        text = line.decode().strip()
                    except Exception:
                        continue
                    parsed = parse_gprmc(text)
                    if parsed:
                        return parsed, None
            time.sleep_ms(50)
    except Exception as e:
        return None, "GPS read error: " + str(e)
    return None, "No GPS fix (timed out -- check antenna/sky view/wiring)"


def read_gps_fix(timeout_ms=4000):
    # backward-compatible wrapper used by the Events "GET GPS" feature,
    # which only ever needed the (lat, lon) pair
    result, err = read_gps_fix_full(timeout_ms)
    if result is None:
        return None, err
    lat, lon, _utc, _speed, _course = result
    return (lat, lon), None


# --- GPS AND ASTRONOMICAL COMMANDS: STAR, LOCATION, ASTRO, SLEW -----
# Python port of the board's "GPS and Astronomical Commands Reference"
# (a BASIC-language manual) -- this board's MicroPython environment
# has no BASIC interpreter, so these are plain functions instead of
# language keywords. Where the manual describes an output variable,
# these return a tuple instead.
#
# ACCURACY NOTE: planetary/lunar positions use reduced/low-precision
# series appropriate for telescope pointing and visual finding
# (roughly arc-minute level for planets, a few arc-minutes for the
# Moon), not full VSOP87/ELP2000-82 to observatory precision. Star
# catalog coordinates were compiled from memory of standard J2000.0
# catalogs and have NOT been cross-checked against a live database --
# double check before relying on this for anything beyond
# eyepiece-field pointing. Proper motion is only filled in for a
# handful of high-motion showcase stars; everything else uses 0,0
# (fine for human timescales on most stars, but not catalog-grade).

_D2R = math.pi / 180.0
_R2D = 180.0 / math.pi


def _jd_from_datetime(y, mo, d, h, mi, s):
    # Meeus ch.7 -- Julian Day from a Gregorian calendar date/time
    if mo <= 2:
        y -= 1
        mo += 12
    a = y // 100
    b = 2 - a + a // 4
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (mo + 1)) + d + b - 1524.5
    jd += (h + mi / 60.0 + s / 3600.0) / 24.0
    return jd


def _parse_datetime(date_str):
    # accepts "dd/mm/yyyy hh:mm:ss" with separators -, /, :, or space
    # (and a missing time defaults to midnight)
    nums = []
    cur = ""
    for c in date_str:
        if c in "-/: ":
            if cur:
                nums.append(int(cur))
                cur = ""
        else:
            cur += c
    if cur:
        nums.append(int(cur))
    if len(nums) < 3:
        raise ValueError("bad date string: " + date_str)
    d, mo, y = nums[0], nums[1], nums[2]
    h = nums[3] if len(nums) > 3 else 0
    mi = nums[4] if len(nums) > 4 else 0
    s = nums[5] if len(nums) > 5 else 0
    return y, mo, d, h, mi, s


def _julian_centuries(jd):
    return (jd - 2451545.0) / 36525.0


def _gmst_hours(jd):
    T = _julian_centuries(jd)
    gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0) +
            0.000387933 * T * T - (T ** 3) / 38710000.0)
    gmst %= 360.0
    if gmst < 0:
        gmst += 360.0
    return gmst / 15.0


def _lst_hours(jd, lon_deg):
    lst = _gmst_hours(jd) + lon_deg / 15.0
    lst %= 24.0
    if lst < 0:
        lst += 24.0
    return lst


def _precess(ra_h, dec_deg, T):
    # IAU 1976 precession, J2000.0 -> epoch of date (Meeus ch.21)
    zeta = (2306.2181 * T + 0.30188 * T * T + 0.017998 * T ** 3) * _D2R / 3600.0
    z = (2306.2181 * T + 1.09468 * T * T + 0.018203 * T ** 3) * _D2R / 3600.0
    theta = (2004.3109 * T - 0.42665 * T * T - 0.041833 * T ** 3) * _D2R / 3600.0
    ra = ra_h * 15.0 * _D2R
    dec = dec_deg * _D2R
    A = math.cos(dec) * math.sin(ra + zeta)
    B = (math.cos(theta) * math.cos(dec) * math.cos(ra + zeta) -
         math.sin(theta) * math.sin(dec))
    C = (math.sin(theta) * math.cos(dec) * math.cos(ra + zeta) +
         math.cos(theta) * math.sin(dec))
    ra2 = math.atan2(A, B) + z
    ra2 %= (2 * math.pi)
    if ra2 < 0:
        ra2 += 2 * math.pi
    dec2 = math.asin(max(-1.0, min(1.0, C)))
    return (ra2 * _R2D / 15.0) % 24.0, dec2 * _R2D


def _apply_proper_motion(ra_h, dec_deg, pm_ra_arcsec, pm_dec_arcsec, years):
    ra_arcsec = ra_h * 15.0 * 3600.0 + pm_ra_arcsec * years
    dec_arcsec = dec_deg * 3600.0 + pm_dec_arcsec * years
    ra_h2 = (ra_arcsec / 3600.0 / 15.0) % 24.0
    if ra_h2 < 0:
        ra_h2 += 24.0
    return ra_h2, dec_arcsec / 3600.0


def _refraction_deg(alt_deg):
    # Bennett's formula (Meeus ch.16), standard atmosphere -- the
    # correction in degrees to ADD to true altitude for apparent
    # altitude. Near/below the horizon it's not meaningful, so it's
    # clamped off there.
    if alt_deg < -1.0:
        return 0.0
    R_arcmin = 1.0 / math.tan(_D2R * (alt_deg + 7.31 / (alt_deg + 4.4)))
    return R_arcmin / 60.0


def _eq_to_horiz(ra_h, dec_deg, lat_deg, lst_h):
    ha_h = (lst_h - ra_h) % 24.0
    if ha_h > 12.0:
        ha_h -= 24.0
    ha = ha_h * 15.0 * _D2R
    dec = dec_deg * _D2R
    lat = lat_deg * _D2R
    sin_alt = math.sin(dec) * math.sin(lat) + math.cos(dec) * math.cos(lat) * math.cos(ha)
    sin_alt = max(-1.0, min(1.0, sin_alt))
    alt = math.asin(sin_alt)
    denom = math.cos(alt) * math.cos(lat)
    cos_az = (math.sin(dec) - math.sin(alt) * math.sin(lat)) / denom if abs(denom) > 1e-9 else 0.0
    cos_az = max(-1.0, min(1.0, cos_az))
    az = math.acos(cos_az)
    if math.sin(ha) > 0:
        az = 2 * math.pi - az
    alt_deg = alt * _R2D
    alt_deg += _refraction_deg(alt_deg)
    return alt_deg, az * _R2D


def _topocentric_correction(ra_h, dec_deg, lat_deg, lst_h, parallax_rad):
    # Meeus ch.40 -- approximate parallax-in-RA/Dec correction.
    # Dominant for the Moon; negligible (but harmless) for anything
    # farther away.
    if parallax_rad <= 0:
        return ra_h, dec_deg
    ha_h = (lst_h - ra_h) % 24.0
    if ha_h > 12.0:
        ha_h -= 24.0
    H = ha_h * 15.0 * _D2R
    dec = dec_deg * _D2R
    lat = lat_deg * _D2R
    d_ra = -parallax_rad * math.cos(lat) * math.sin(H) / max(math.cos(dec), 1e-6)
    d_dec = -parallax_rad * (math.sin(lat) * math.cos(dec) - math.cos(lat) * math.sin(dec) * math.cos(H))
    ra_h2 = (ra_h + d_ra * _R2D / 15.0) % 24.0
    dec_deg2 = dec_deg + d_dec * _R2D
    return ra_h2, dec_deg2


# --- planetary elements (J2000.0 mean elements + rate per Julian
# century) -- L=mean longitude, a=semi-major axis (AU), e=eccentricity,
# i=inclination, node=longitude of ascending node, peri=longitude of
# perihelion. Degrees except a, e. This is the standard "low precision
# formulae for planetary positions" table (good to roughly an
# arcminute for inner planets over a couple of centuries either side
# of J2000) -- not full VSOP87.
_PLANET_ELEMENTS = {
    "mercury": ((252.250906, 149472.6746358), (0.387098310, 0.0),
                (0.20563175, 0.000020407), (7.004986, -0.0059516),
                (48.330893, -0.1254229), (77.456119, 0.1588643)),
    "venus":   ((181.979801, 58517.8156760), (0.72332982, 0.0),
                (0.00677188, -0.000047766), (3.394662, -0.0008568),
                (76.679920, -0.2780134), (131.563707, 0.0048646)),
    "earth":   ((100.466449, 35999.3728519), (1.000001018, 0.0),
                (0.01670862, -0.000042037), (0.0, 0.0130546),
                (174.873174, -0.2410908), (102.937348, 0.3225654)),
    "mars":    ((355.433275, 19140.2993313), (1.523679342, 0.0),
                (0.09340062, 0.000090483), (1.849726, -0.0081479),
                (49.558093, -0.2949846), (336.060234, 0.4438898)),
    "jupiter": ((34.351484, 3034.9056746), (5.202603191, 0.0),
                (0.04849485, 0.000163244), (1.303270, -0.0019872),
                (100.464441, 0.1766828), (14.331309, 0.2155525)),
    "saturn":  ((50.077471, 1222.1137943), (9.554909596, 0.0),
                (0.05550862, -0.000346818), (2.488878, 0.0025515),
                (113.665524, -0.2566649), (93.056787, 0.5665496)),
    "uranus":  ((314.055005, 428.4669983), (19.218446062, 0.0),
                (0.04629590, -0.000027337), (0.773196, -0.0016869),
                (74.005947, 0.0741461), (173.005159, 0.0893212)),
    "neptune": ((304.348665, 218.4862002), (30.110386869, 0.0),
                (0.00898809, 0.000006408), (1.769952, 0.0002257),
                (131.784057, -0.0061651), (48.123691, 0.0291587)),
}


def _kepler_E(M_rad, e):
    E = M_rad
    for _ in range(8):
        dE = (E - e * math.sin(E) - M_rad) / (1 - e * math.cos(E))
        E -= dE
        if abs(dE) < 1e-9:
            break
    return E


def _planet_heliocentric(name, T):
    (L0, Ld), (a0, ad), (e0, ed), (i0, idd), (n0, nd), (p0, pd) = _PLANET_ELEMENTS[name]
    L = (L0 + Ld * T) % 360.0
    a = a0 + ad * T
    e = e0 + ed * T
    i = (i0 + idd * T) * _D2R
    node = (n0 + nd * T) * _D2R
    peri = (p0 + pd * T) * _D2R
    M = (L - (p0 + pd * T)) % 360.0
    if M > 180.0:
        M -= 360.0
    M_rad = M * _D2R
    E = _kepler_E(M_rad, e)
    xv = a * (math.cos(E) - e)
    yv = a * math.sqrt(max(0.0, 1 - e * e)) * math.sin(E)
    w = peri - node
    cw, sw = math.cos(w), math.sin(w)
    cn, sn = math.cos(node), math.sin(node)
    ci, si = math.cos(i), math.sin(i)
    x = (cn * cw - sn * sw * ci) * xv + (-cn * sw - sn * cw * ci) * yv
    y = (sn * cw + cn * sw * ci) * xv + (-sn * sw + cn * cw * ci) * yv
    z = (sw * si) * xv + (cw * si) * yv
    return x, y, z


def _obliquity_deg(T):
    return 23.439291 - 0.0130042 * T


def _ecl_to_eq(x, y, z, T):
    eps = _obliquity_deg(T) * _D2R
    xeq = x
    yeq = y * math.cos(eps) - z * math.sin(eps)
    zeq = y * math.sin(eps) + z * math.cos(eps)
    r = math.sqrt(xeq * xeq + yeq * yeq + zeq * zeq)
    ra = math.atan2(yeq, xeq) * _R2D / 15.0
    ra %= 24.0
    if ra < 0:
        ra += 24.0
    dec = math.asin(max(-1.0, min(1.0, zeq / r))) * _R2D
    return ra, dec, r


def _sun_geocentric_equatorial(T):
    xe, ye, ze = _planet_heliocentric("earth", T)
    return _ecl_to_eq(-xe, -ye, -ze, T)


def _planet_geocentric_equatorial(name, T):
    xp, yp, zp = _planet_heliocentric(name, T)
    xe, ye, ze = _planet_heliocentric("earth", T)
    return _ecl_to_eq(xp - xe, yp - ye, zp - ze, T)


def _moon_geocentric_equatorial(T):
    # Low-precision truncated lunar theory (the well-known ~10-term
    # Astronomical Almanac formula, good to a few arcminutes in
    # position and used here as the "truncated ELP2000-82" series) --
    # returns (ra_h, dec_deg, horizontal_parallax_deg)
    d = lambda deg: deg * _D2R
    Lp = (218.32 + 481267.881 * T
          + 6.29 * math.sin(d(134.9 + 477198.85 * T))
          - 1.27 * math.sin(d(259.2 - 413335.38 * T))
          + 0.66 * math.sin(d(235.7 + 890534.23 * T))
          + 0.21 * math.sin(d(269.9 + 954397.70 * T))
          - 0.19 * math.sin(d(357.5 + 35999.05 * T))
          - 0.11 * math.sin(d(186.6 + 966404.05 * T))) % 360.0
    B = (5.13 * math.sin(d(93.3 + 483202.03 * T))
         + 0.28 * math.sin(d(228.2 + 960400.87 * T))
         - 0.28 * math.sin(d(318.3 + 6003.18 * T))
         - 0.17 * math.sin(d(217.6 - 407332.20 * T)))
    P = (0.9508 + 0.0518 * math.cos(d(134.9 + 477198.85 * T))
         + 0.0095 * math.cos(d(259.2 - 413335.38 * T))
         + 0.0078 * math.cos(d(235.7 + 890534.23 * T))
         + 0.0028 * math.cos(d(269.9 + 954397.70 * T)))
    eps = _obliquity_deg(T) * _D2R
    Lp_r, B_r = Lp * _D2R, B * _D2R
    ra = math.atan2(math.sin(Lp_r) * math.cos(eps) - math.tan(B_r) * math.sin(eps),
                     math.cos(Lp_r)) * _R2D / 15.0
    ra %= 24.0
    if ra < 0:
        ra += 24.0
    dec = math.asin(math.sin(B_r) * math.cos(eps) + math.cos(B_r) * math.sin(eps) * math.sin(Lp_r)) * _R2D
    return ra, dec, P


# --- star / deep-sky catalog: name -> (ra_h, dec_deg, pm_ra_arcsec_per_yr,
# pm_dec_arcsec_per_yr), all J2000.0. See the accuracy note above.
_STAR_CATALOG = {
    "achernar": (1.6283, -57.2333, 0.0, 0.0), "acrux": (12.4433, -63.0999, 0.0, 0.0),
    "alcyone": (3.7917, 24.10, 0.0, 0.0), "aldebaran": (4.5983, 16.50, 0.0, 0.0),
    "algenib": (0.22, 15.18, 0.0, 0.0), "algieba": (10.333, 19.83, 0.0, 0.0),
    "algol": (3.1367, 40.95, 0.0, 0.0), "alhajoth": (5.2783, 46.00, 0.0, 0.0),
    "alhena": (6.6283, 16.40, 0.0, 0.0), "almaak": (2.065, 42.33, 0.0, 0.0),
    "alnair": (22.1367, -46.97, 0.0, 0.0), "alnilam": (5.6033, -1.20, 0.0, 0.0),
    "alnitak": (5.680, -1.95, 0.0, 0.0), "alphard": (9.460, -8.667, 0.0, 0.0),
    "alpheratz": (0.140, 29.083, 0.0, 0.0), "alpherg": (1.525, 15.35, 0.0, 0.0),
    "alrescha": (2.0333, 2.767, 0.0, 0.0), "alsephina": (8.745, -54.717, 0.0, 0.0),
    "alshain": (19.9217, 6.40, 0.0, 0.0), "altair": (19.8467, 8.867, 0.0, 0.0),
    "aludra": (7.4017, -29.30, 0.0, 0.0),
    "andromeda galaxy": (0.7117, 41.267, 0.0, 0.0), "antares": (16.490, -26.433, 0.0, 0.0),
    "arcturus": (14.2617, 19.183, -1.09, -2.00),
    "aspidiske": (9.285, -59.267, 0.0, 0.0), "bellatrix": (5.4183, 6.35, 0.0, 0.0),
    "betelgeuse": (5.920, 7.40, 0.0, 0.0),
    "bodes galaxy": (9.9267, 69.067, 0.0, 0.0), "canopus": (6.400, -52.70, 0.0, 0.0),
    "capella": (5.2783, 46.00, 0.0, 0.0), "caph": (0.1533, 59.15, 0.0, 0.0),
    "castor": (7.5767, 31.883, 0.0, 0.0),
    "cigar galaxy": (9.9317, 69.683, 0.0, 0.0), "deneb": (20.690, 45.283, 0.0, 0.0),
    "denebola": (11.8183, 14.567, 0.0, 0.0), "dubhe": (11.0617, 61.75, 0.0, 0.0),
    "elnath": (5.4383, 28.60, 0.0, 0.0), "eltanin": (17.9433, 51.483, 0.0, 0.0),
    "enif": (21.7367, 9.867, 0.0, 0.0), "fomalhaut": (22.960, -29.617, 0.0, 0.0),
    "gacrux": (12.520, -57.117, 0.0, 0.0), "hadar": (14.0633, -60.367, 0.0, 0.0),
    "homam": (22.6917, 10.833, 0.0, 0.0), "kaus australis": (18.4033, -34.383, 0.0, 0.0),
    "kochab": (14.845, 74.15, 0.0, 0.0), "kornephoros": (16.5017, 21.483, 0.0, 0.0),
    "large magellanic cloud": (5.3933, -69.75, 0.0, 0.0), "lesath": (17.5133, -37.30, 0.0, 0.0),
    "markab": (23.080, 15.20, 0.0, 0.0), "menkalinan": (5.9917, 44.95, 0.0, 0.0),
    "mimosa": (12.795, -59.683, 0.0, 0.0), "mintaka": (5.5333, -0.30, 0.0, 0.0),
    "mirfak": (3.405, 49.867, 0.0, 0.0), "nunki": (18.9217, -26.30, 0.0, 0.0),
    "peacock": (20.4267, -56.733, 0.0, 0.0), "polaris": (2.530, 89.267, 0.0, 0.0),
    "pollux": (7.755, 28.033, 0.0, 0.0), "procyon": (7.655, 5.217, -0.7, -1.0),
    "rasalgethi": (17.2433, 14.383, 0.0, 0.0), "rasalhague": (17.5817, 12.55, 0.0, 0.0),
    "regulus": (10.140, 11.967, 0.0, 0.0), "rigel": (5.2417, -8.20, 0.0, 0.0),
    "rigil kent": (14.660, -60.833, -3.68, 0.48),
    "ruchbah": (1.4283, 60.233, 0.0, 0.0), "sabik": (17.1733, -15.733, 0.0, 0.0),
    "sadalmelik": (22.0967, -0.333, 0.0, 0.0), "sadalsuud": (21.5267, -5.567, 0.0, 0.0),
    "sadr": (20.370, 40.25, 0.0, 0.0), "saiph": (5.7967, -9.667, 0.0, 0.0),
    "scheat": (23.0633, 28.083, 0.0, 0.0), "shaula": (17.560, -37.10, 0.0, 0.0),
    "shedir": (0.675, 56.533, 0.0, 0.0), "sirius": (6.7517, -16.717, -0.55, -1.21),
    "small magellanic cloud": (0.8783, -72.833, 0.0, 0.0),
    "sombrero galaxy": (12.667, -11.617, 0.0, 0.0), "spica": (13.420, -11.167, 0.0, 0.0),
    "suhail": (9.1333, -43.433, 0.0, 0.0), "tarazed": (19.7717, 10.617, 0.0, 0.0),
    "triangulum galaxy": (1.565, 30.65, 0.0, 0.0), "vega": (18.615, 38.783, 0.0, 0.0),
    "whirlpool galaxy": (13.4983, 47.20, 0.0, 0.0),
    "zubenelgenubi": (14.845, -16.033, 0.0, 0.0), "zubeneschamali": (15.2833, -9.383, 0.0, 0.0),
}

_SOLAR_SYSTEM = ("sun", "mercury", "venus", "moon", "mars", "jupiter",
                  "saturn", "uranus", "neptune")


def _resolve_target(jd, lat_deg, lon_deg, name=None, ra=None, dec=None,
                     pm_ra=0.0, pm_dec=0.0):
    # Shared logic for STAR/ASTRO. Returns (alt, az, ra_now, dec_now)
    # or None if a named object isn't recognised.
    T = _julian_centuries(jd)
    lst = _lst_hours(jd, lon_deg)
    if name is not None:
        key = name.strip().lower()
        if key == "sun":
            ra_now, dec_now, dist_au = _sun_geocentric_equatorial(T)
            plx = math.asin(min(1.0, 4.26352e-5 / max(dist_au, 1e-6)))
            ra_now, dec_now = _topocentric_correction(ra_now, dec_now, lat_deg, lst, plx)
        elif key == "moon":
            ra_now, dec_now, plx_deg = _moon_geocentric_equatorial(T)
            ra_now, dec_now = _topocentric_correction(ra_now, dec_now, lat_deg, lst, plx_deg * _D2R)
        elif key in _PLANET_ELEMENTS and key != "earth":
            ra_now, dec_now, dist_au = _planet_geocentric_equatorial(key, T)
            plx = math.asin(min(1.0, 4.26352e-5 / max(dist_au, 1e-6)))
            ra_now, dec_now = _topocentric_correction(ra_now, dec_now, lat_deg, lst, plx)
        else:
            cat = _STAR_CATALOG.get(key)
            if cat is None:
                return None
            ra0, dec0, pmra0, pmdec0 = cat
            years = T * 100.0
            ra_pm, dec_pm = _apply_proper_motion(ra0, dec0, pmra0, pmdec0, years)
            ra_now, dec_now = _precess(ra_pm, dec_pm, T)
    else:
        years = T * 100.0
        ra_pm, dec_pm = _apply_proper_motion(ra, dec, pm_ra, pm_dec, years)
        ra_now, dec_now = _precess(ra_pm, dec_pm, T)
    alt, az = _eq_to_horiz(ra_now, dec_now, lat_deg, lst)
    return alt, az, ra_now, dec_now


# --- 3D MODEL VIEWER (ported from the PicoMite MMBasic 3D graphics
# manual) -- a from-scratch software 3D pipeline: quaternion rotation,
# simple perspective projection, centroid depth sorting, normal-based
# backface culling, and wireframe/solid rendering. This board's
# MicroPython has no built-in "3D CREATE"/"3D SHOW" the way MMBasic
# does, so this is a plain-Python reimplementation of the same ideas,
# not a wrapper around real 3D commands.
#
# TWO CAVEATS, both explained in more detail in chat:
#  1. Drawing primitives (fb.line()/fb.poly()) are a best guess at
#     what this board's hdmi module exposes, matching the standard
#     MicroPython framebuf.FrameBuffer API -- there's a software
#     fallback (Bresenham line, scanline fill) if those aren't
#     present, but if there's truly no pixel-level primitive at all,
#     this can't draw anything.
#  2. This display turned out to only support a handful of
#     simultaneous colours in its normal video mode (that's why
#     photos looked posterized) -- so WIREFRAME is the recommended/
#     default render mode here, since flat-coloured lines match what
#     the UI already draws fine. SOLID (filled faces) is included but
#     likely to look poor for the same reason photos did. There's no
#     shading/lighting gradient implemented, since scaling an unknown
#     colour encoding could easily produce garbage colours on a
#     limited-palette display -- lit faces just pick between the
#     face's normal colour and a separate "shadow" colour you supply,
#     rather than any continuous blend.

import array


def _fb_pixel(fb, x, y, color):
    try:
        fb.pixel(int(x), int(y), color)
    except Exception:
        pass


def _fb_line(fb, x0, y0, x1, y1, color):
    try:
        fb.line(int(x0), int(y0), int(x1), int(y1), color)
        return
    except Exception:
        pass
    # Bresenham fallback, pixel by pixel
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        _fb_pixel(fb, x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _fb_fill_poly(fb, points, color):
    if len(points) < 3:
        return
    try:
        ox, oy = points[0]
        coords = []
        for (px, py) in points:
            coords.append(int(px - ox))
            coords.append(int(py - oy))
        fb.poly(int(ox), int(oy), array.array("h", coords), color, True)
        return
    except Exception:
        pass
    _scanline_fill(fb, points, color)


def _scanline_fill(fb, points, color):
    # basic even-odd scanline polygon fill -- only used if fb has no
    # native poly()/fill primitive
    ys = [p[1] for p in points]
    y_min, y_max = int(min(ys)), int(max(ys))
    n = len(points)
    for y in range(y_min, y_max + 1):
        xs = []
        for i in range(n):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % n]
            if y1 == y2:
                continue
            if min(y1, y2) <= y < max(y1, y2):
                t = (y - y1) / (y2 - y1)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            xa, xb = int(xs[i]), int(xs[i + 1])
            try:
                fb.hline(xa, y, max(1, xb - xa), color)
            except Exception:
                for x in range(xa, xb + 1):
                    _fb_pixel(fb, x, y, color)


def _draw_calc_icon(fb, cx, cy, size, symbol, color):
    # simple hand-drawn ("turtle graphics" style) vector icons for
    # calculator operator buttons, using the same _fb_line/_fb_pixel
    # helpers (and their software fallback) as the 3D engine -- drawn
    # instead of a text label, centred at (cx, cy)
    r = max(4, size // 2 - 6)
    if symbol == "+":
        _fb_line(fb, cx - r, cy, cx + r, cy, color)
        _fb_line(fb, cx, cy - r, cx, cy + r, color)
    elif symbol == "-":
        _fb_line(fb, cx - r, cy, cx + r, cy, color)
    elif symbol == "*":
        _fb_line(fb, cx - r, cy - r, cx + r, cy + r, color)
        _fb_line(fb, cx - r, cy + r, cx + r, cy - r, color)
    elif symbol == "/":
        _fb_line(fb, cx - r, cy + r, cx + r, cy - r, color)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                _fb_pixel(fb, cx - r // 2 + dx, cy + r // 2 + dy, color)
                _fb_pixel(fb, cx + r // 2 + dx, cy - r // 2 + dy, color)
    elif symbol == "=":
        _fb_line(fb, cx - r, cy - r // 2, cx + r, cy - r // 2, color)
        _fb_line(fb, cx - r, cy + r // 2, cx + r, cy + r // 2, color)
    elif symbol == "<-":
        _fb_line(fb, cx - r, cy, cx + r, cy, color)
        _fb_line(fb, cx - r, cy, cx - r + r, cy - r, color)
        _fb_line(fb, cx - r, cy, cx - r + r, cy + r, color)


def _quat_from_axis_angle(axis, angle_rad):
    ax, ay, az = axis
    n = math.sqrt(ax * ax + ay * ay + az * az) or 1.0
    ax, ay, az = ax / n, ay / n, az / n
    s = math.sin(angle_rad / 2.0)
    return (math.cos(angle_rad / 2.0), ax * s, ay * s, az * s)


def _quat_multiply(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return (
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    )


def _quat_rotate_vector(q, v):
    w, x, y, z = q
    vx, vy, vz = v
    qv = (0.0, vx, vy, vz)
    qc = (w, -x, -y, -z)
    _, rx, ry, rz = _quat_multiply(_quat_multiply(q, qv), qc)
    return (rx, ry, rz)


class Model3D:
    """A single 3D object: vertices, faces (lists of vertex indices,
    each >=3), and a colour per face -- the same shape as MMBasic's
    3D CREATE, minus the fixed 8-object slot limit (this board's
    Python has no such cap, so just make as many Model3D instances as
    you need)."""

    def __init__(self, vertices, faces, face_colours, shadow_colour=None):
        self.base_vertices = list(vertices)
        self.faces = faces
        self.face_colours = face_colours
        self.shadow_colour = shadow_colour  # used instead of blending, see caveat above
        self.rotation = (1.0, 0.0, 0.0, 0.0)  # identity quaternion
        self.light = None    # (x, y, z) direction, or None
        self.ambient = 100   # percent 0-100 -- see caveat, this only picks lit/shadow, not a blend
        self.flags = [0] * len(faces)
        self._compute_normals()

    def _compute_normals(self):
        self.normals = []
        self.centroids = []
        for face in self.faces:
            pts = [self.base_vertices[i] for i in face]
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            cz = sum(p[2] for p in pts) / len(pts)
            self.centroids.append((cx, cy, cz))
            (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = pts[0], pts[1], pts[2]
            ux, uy, uz = x1 - x0, y1 - y0, z1 - z0
            vx, vy, vz = x2 - x0, y2 - y0, z2 - z0
            # v (x) u, not u (x) v -- verified against a known cube:
            # u x v gave INWARD normals for this (and the manual's
            # own) counter-clockwise-from-outside winding order
            nx = vy * uz - vz * uy
            ny = vz * ux - vx * uz
            nz = vx * uy - vy * ux
            n = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            self.normals.append((nx / n, ny / n, nz / n))

    def reset(self):
        self.rotation = (1.0, 0.0, 0.0, 0.0)

    def rotate(self, axis, angle_rad):
        q = _quat_from_axis_angle(axis, angle_rad)
        self.rotation = _quat_multiply(q, self.rotation)

    def set_light(self, x, y, z, ambient=40):
        self.light = (x, y, z)
        self.ambient = max(0, min(100, ambient))

    def set_flag(self, flag, face_start, count):
        for i in range(face_start, min(face_start + count, len(self.faces))):
            self.flags[i] = flag


class Camera3D:
    def __init__(self, viewplane, x=0, y=0, panx=0, pany=0):
        self.viewplane = viewplane
        self.x = x
        self.y = y
        self.panx = panx
        self.pany = pany


def render_model(fb, model, camera, ox, oy, oz, screen_w, screen_h,
                  mode="wireframe", nonormals=False, wire_colour=WHITE):
    """Draws `model` at object-space position (ox, oy, oz) using
    `camera`, onto framebuffer `fb`. mode is "wireframe" (recommended
    -- see the module caveat above) or "solid". Returns the on-screen
    bounding box (xmin, xmax, ymin, ymax) drawn, or None if nothing
    was visible, so the caller can clear it before the next frame."""
    rotated = [_quat_rotate_vector(model.rotation, v) for v in model.base_vertices]
    rotated_normals = [_quat_rotate_vector(model.rotation, n) for n in model.normals]
    rotated_centroids = [_quat_rotate_vector(model.rotation, c) for c in model.centroids]

    visible_faces = []
    for idx, face in enumerate(model.faces):
        if model.flags[idx] & 1:  # bit 0: hidden
            continue
        nx, ny, nz = rotated_normals[idx]
        facing_camera = nz > 0
        if model.flags[idx] & 4:  # bit 2: invert normal
            facing_camera = not facing_camera
        if not nonormals and not facing_camera:
            continue
        cx, cy, cz = rotated_centroids[idx]
        dist = oz + cz
        visible_faces.append((dist, idx, face, (nx, ny, nz)))

    if not visible_faces:
        return None

    # centroid depth sort -- furthest first, so nearer faces/edges end
    # up drawn on top
    visible_faces.sort(key=lambda t: -t[0])

    all_x, all_y = [], []

    for dist, idx, face, normal in visible_faces:
        colour = model.face_colours[idx] if idx < len(model.face_colours) else wire_colour
        if (model.flags[idx] & 8) and model.light and model.shadow_colour is not None:
            lx, ly, lz = model.light
            ln = math.sqrt(lx * lx + ly * ly + lz * lz) or 1.0
            lx, ly, lz = lx / ln, ly / ln, lz / ln
            nx, ny, nz = normal
            lit = (-(nx * lx + ny * ly + nz * lz)) > (1.0 - model.ambient / 100.0)
            if not lit:
                colour = model.shadow_colour

        pts2d = []
        skip = False
        for vi in face:
            vx, vy, vz = rotated[vi]
            wx, wy, wz = ox + vx, oy + vy, oz + vz
            if wz <= 1:
                skip = True
                break
            scale = camera.viewplane / wz
            sx = screen_w / 2 + camera.panx + (wx - camera.x) * scale
            sy = screen_h / 2 + camera.pany - (wy - camera.y) * scale
            pts2d.append((sx, sy))
            all_x.append(sx)
            all_y.append(sy)
        if skip or len(pts2d) < 3:
            continue

        if mode == "solid":
            _fb_fill_poly(fb, pts2d, colour)
        else:
            for i in range(len(pts2d)):
                x0, y0 = pts2d[i]
                x1, y1 = pts2d[(i + 1) % len(pts2d)]
                _fb_line(fb, x0, y0, x1, y1, colour)

    if not all_x:
        return None
    return (min(all_x), max(all_x), min(all_y), max(all_y))


def make_box(cx, cy, cz, hx, hy, hz, colour):
    """Builds a Model3D box centred at (cx,cy,cz) with half-extents
    (hx,hy,hz) -- one flat colour per face."""
    vertices = [
        (cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
        (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz),
    ]
    faces = [
        [0, 1, 2, 3], [5, 4, 7, 6], [0, 4, 5, 1],
        [2, 6, 7, 3], [0, 3, 7, 4], [1, 5, 6, 2],
    ]
    colours = [colour] * 6
    return Model3D(vertices, faces, colours)


def make_demo_car():
    """A simple placeholder 'car' -- a body box plus a smaller cabin
    box on top -- since no real vehicle mesh was supplied. Swap in
    real vertex/face data here once you have some (e.g. exported from
    a modelling tool as vertex/face lists)."""
    body = make_box(0, -10, 0, 60, 18, 25, WHITE)
    cabin = make_box(-5, 14, 0, 30, 14, 20, WHITE)
    vertices = body.base_vertices + cabin.base_vertices
    offset = len(body.base_vertices)
    faces = list(body.faces) + [[i + offset for i in f] for f in cabin.faces]
    colours = list(body.face_colours) + list(cabin.face_colours)
    return Model3D(vertices, faces, colours, shadow_colour=RED)


# --- 3D model editor file format: a plain text file under MODELS_DIR,
# one line per vertex ("V x y z") and one line per face
# ("F i,i,i,... COLOURNAME"). Colours are stored by name (not the raw
# value) so a saved file stays meaningful even if colour constants
# ever change.
_MODEL_COLOUR_NAMES = {"WHITE": WHITE, "RED": RED}


def serialize_model(vertices, faces):
    # faces: list of (index_list, colour_name) tuples
    lines = []
    for (x, y, z) in vertices:
        lines.append("V %g %g %g" % (x, y, z))
    for (idxs, colour_name) in faces:
        lines.append("F " + ",".join(str(i) for i in idxs) + " " + colour_name)
    return "\n".join(lines) + "\n"


def parse_model(text):
    vertices, faces = [], []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        if parts[0] == "V":
            xs = parts[1].split()
            if len(xs) < 3:
                continue
            vertices.append((float(xs[0]), float(xs[1]), float(xs[2])))
        elif parts[0] == "F":
            rest = parts[1].rsplit(" ", 1)
            idxs = [int(i) for i in rest[0].split(",") if i.strip() != ""]
            colour_name = rest[1] if len(rest) > 1 else "WHITE"
            faces.append((idxs, colour_name))
    return vertices, faces


def save_model_file(name, vertices, faces):
    try:
        os.mkdir(MODELS_DIR)
    except OSError:
        pass
    path = MODELS_DIR + "/" + name + ".model"
    f = open(path, "w")
    try:
        f.write(serialize_model(vertices, faces))
    finally:
        f.close()
    return path


def load_model_file(name):
    path = MODELS_DIR + "/" + name + ".model"
    f = open(path)
    try:
        text = f.read()
    finally:
        f.close()
    return parse_model(text)


def list_saved_models():
    try:
        names = [f[:-6] for f in os.listdir(MODELS_DIR) if f.endswith(".model")]
        names.sort()
        return names
    except OSError:
        return []


def validate_face_indices(idxs, num_vertices):
    if len(idxs) < 3:
        return "A face needs at least 3 vertex indices"
    for i in idxs:
        if i < 0 or i >= num_vertices:
            return "Vertex index %d doesn't exist (have %d vertices)" % (i, num_vertices)
    return None


def delete_vertex_safe(vertices, faces, idx):
    # returns (new_vertices, new_faces, error_or_None) -- refuses to
    # delete a vertex still referenced by a face (rather than silently
    # corrupting that face), and re-indexes remaining faces so
    # everything above the deleted index shifts down by one
    for fidxs, colour_name in faces:
        if idx in fidxs:
            return vertices, faces, "Vertex %d is used by a face -- delete that face first" % idx
    new_vertices = vertices[:idx] + vertices[idx + 1:]
    new_faces = [([i - 1 if i > idx else i for i in fidxs], colour_name) for fidxs, colour_name in faces]
    return new_vertices, new_faces, None


def snap_to_grid(value, grid_size):
    if not grid_size:
        return value
    return round(value / grid_size) * grid_size


def extrude_polygon(points2d, z_base, thickness):
    # points2d must be a simple (non-self-intersecting) polygon
    # outline, counter-clockwise as seen from above (+Z looking down)
    # -- e.g. for a rectangle: [(0,0), (w,0), (w,h), (0,h)].
    # Returns (vertices, faces) -- faces is a list of plain index
    # lists (not yet paired with a colour name), ready to append onto
    # a Model3DPage's vertex/face lists at the right offset.
    # Winding verified against a known box and an L-shape: bottom cap
    # points -Z, top cap points +Z, and every side wall points
    # straight outward -- see chat history for the standalone tests.
    n = len(points2d)
    vertices = [(x, y, z_base) for (x, y) in points2d] + [(x, y, z_base + thickness) for (x, y) in points2d]
    bottom_face = list(range(n))
    top_face = list(range(2 * n - 1, n - 1, -1))
    faces = [bottom_face, top_face]
    for i in range(n):
        i2 = (i + 1) % n
        faces.append([i2, i, n + i, n + i2])
    return vertices, faces


def name_face_by_normal(normal):
    # classifies a face's outward normal into a CAD-style face name --
    # verified against all 6 axis directions in chat history
    nx, ny, nz = normal
    ax, ay, az = abs(nx), abs(ny), abs(nz)
    if az >= ax and az >= ay:
        return "TOP" if nz > 0 else "BOTTOM"
    elif ay >= ax:
        return "BACK" if ny > 0 else "FRONT"
    else:
        return "RIGHT" if nx > 0 else "LEFT"



def attend_count(key):
    return scalar("SELECT COUNT(*) FROM attend WHERE evkey=?", (key,))


# last GPS fix seen, cached so the menu ticker can show something
# current without blocking on a fresh read every cycle
last_gps_fix = None
last_gps_check = 0

# last file received via the background upload server (SEND TO BOARD /
# UPDATE), so the menu ticker can show that something just arrived
last_received_file = ""
last_received_time = ""


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


def ensure_lists():
    # make sure roles.txt / status.txt actually exist on disk with the
    # defaults, so there's something there to edit later -- mirrors the
    # ensure_dir() behaviour from the old members.py
    try:
        os.stat(ROLES_FILE)
    except OSError:
        write_list(ROLES_FILE, DEFAULT_ROLES)
    try:
        os.stat(STATUS_FILE)
    except OSError:
        write_list(STATUS_FILE, DEFAULT_STATUS)


ensure_lists()
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
            self.g.poll()
            self.ticker_update()
            self.page_tick()
            background_tick()
            discovery_tick()
            time.sleep_ms(10)
        try:
            self.g.stop()
        except Exception:
            pass
        gc.collect()
        return self.next

    def enter(self):
        pass

    def page_tick(self):
        pass

    def say(self, text):
        # if this page has a static status box (status_box), show
        # messages there plainly instead of scrolling them in the
        # footer ticker -- a scrolling confirmation is easy to miss
        # or misread, so pages that have upgraded to a status box
        # get a clear, static one instead of both at once
        if hasattr(self, "status_box") and self.status_box is not None:
            self.status_box.value = text
        else:
            self.ticker_base = text

    def status_bar(self, g, y=24):
        # reusable static, non-scrolling status line -- call this in
        # build() to opt a page into clear confirmations instead of
        # the scrolling ticker
        self.status_box = g.displaybox(14, y, 612, 24, "Ready", fg=WHITE, bg=BTN, font=2)
        return self.status_box

    def footer(self, g):
        self.msg = g.displaybox(8, 450, 624, 26, "", fg=INK, bg=PAGE, font=2)
        self.ticker_base = ""
        self.ticker_pos = 0
        self.ticker_last = time.ticks_ms()

    def help_button(self, g, topic, return_to):
        # small '?' button, consistent top-right spot on every page,
        # opens HelpPage for this page's topic and returns here after
        g.button(602, 4, 32, 26, "?", fg=WHITE, bg=BTN, font=2,
                 callback=lambda b: self.go("help|" + topic + "|" + return_to))

    def ticker_update(self):
        if not hasattr(self, "ticker_last"):
            return
        now = time.ticks_ms()
        if time.ticks_diff(now, self.ticker_last) < 200:
            return
        self.ticker_last = now
        full = display_stamp() + "     |     " + self.ticker_base + "          "
        L = len(full)
        if L == 0:
            self.msg.value = ""
            return
        window = 70
        doubled = full + full
        self.msg.value = doubled[self.ticker_pos:self.ticker_pos + window]
        self.ticker_pos = (self.ticker_pos + 1) % L


# topic -> (page title, [(button/field label, what it does), ...])
HELP_TEXT = {
    "menu": ("Main Menu", [
        ("MEMBERS", "Look up, add, edit, or email club members."),
        ("EVENTS", "Create events, start/stop check-in, see who came."),
        ("WIFI", "Connect to a network, name this board, manage saved networks and board-to-board forwarding."),
        ("PHOTOS", "Browse, upload, rename, or delete general photos."),
        ("IMPORT SD", "Copy pictures in from the SD card."),
        ("3D MODEL EDITOR", "Build a 3D model by typing vertex coordinates and face vertex-lists, save/load it, then rotate and inspect it in wireframe or solid mode."),
        ("CALCULATOR", "A basic four-function calculator."),
        ("EXPORT / IMPORT", "Write CSV files, send them to other boards, email them, or import a CSV back in."),
        ("EMAIL", "Shortcut straight to Export/Import, where EMAIL LAST sends the most recent export."),
        ("QUIT", "Exit back to the MicroPython prompt."),
        ("Status panel", "Shows member count, current event status, and wifi/IP status at a glance."),
    ]),
    "members": ("Members", [
        ("Find box", "Type a name, member number, or rego to filter the list."),
        ("SEARCH", "Re-runs the search using what's typed in Find."),
        ("NEW", "Clears the form and assigns the next free member number."),
        ("CHECK IN", "Marks the loaded member as attending the currently running event."),
        ("List (left)", "Tap a name to load that member's details on the right."),
        ("Detail fields", "No, Name, Email, Phone, Logbook No, Address, Notes -- edit then SAVE."),
        ("Status / Paid switches", "Active vs Not Active, and financial (paid) status."),
        ("SAVE", "Writes the current form to the database."),
        ("CLEAR", "Wipes the form without deleting anything saved."),
        ("CARS", "Go to this member's car records."),
        ("PHOTO", "Attach or view a photo for this member."),
        ("DELETE", "Removes this member -- press twice to confirm."),
        ("EMAIL", "Send a one-off email to this member."),
        ("UPDATE", "Sends this member's record to every board saved on the Wifi page."),
        ("REFRESH", "Re-runs the current search -- use after an import lands."),
        ("SHOW ALL / RELOAD LIST", "Fully reloads this page -- use if the list stops responding to taps."),
        ("MENU", "Back to the main menu."),
    ]),
    "cars": ("Cars", [
        ("List (left)", "Every car on file for this member -- tap to edit."),
        ("Car / Rego / Logbook fields", "Details for the selected or new car."),
        ("ADD", "Adds a new car with the fields above."),
        ("SAVE", "Saves changes to the selected car."),
        ("PHOTO", "Attach or view a photo of this car."),
        ("DELETE", "Removes the selected car."),
        ("BACK", "Return to this member's record."),
    ]),
    "events": ("Events", [
        ("List (left)", "Events on file -- tap to load."),
        ("Name / Date / Time / Place / Notes", "Details for the selected or new event."),
        ("NEW", "Starts a fresh event using today's date."),
        ("SAVE", "Saves the event details."),
        ("START", "Marks this event as the currently running one -- CHECK IN on Members applies to it."),
        ("STOP", "Stops any event from being 'currently running'."),
        ("IMPORT", "Toggle to import attendance from a photo (see on-screen prompt)."),
        ("SHOW PHOTO", "Displays a photo linked to this event."),
        ("WHO CAME", "Lists everyone checked in to this event."),
        ("DELETE", "Removes this event."),
        ("GET GPS", "Records the current GPS fix against this event."),
        ("MENU", "Back to the main menu."),
    ]),
    "wifi": ("Wifi Setup", [
        ("Status bar (top)", "Shows the result of your last action here, clearly, without scrolling."),
        ("SSID / Password", "Type these to connect to a new network."),
        ("SAVE", "Adds this network to your saved list (doesn't connect)."),
        ("CONNECT", "Connects using whatever's in the SSID/Password fields."),
        ("DISCONN.", "Disconnects from wifi and clears the fields."),
        ("Saved networks", "Tap a name to load it into the fields -- press CONNECT to actually switch."),
        ("DELETE (saved)", "Removes the selected saved network."),
        ("This board's name", "A fixed label this board announces itself as, so other boards can find it even if its IP changes."),
        ("SAVE NAME", "Stores this board's name."),
        ("Discovered boards", "Other boards seen on the network recently -- tap to add to forwarding."),
        ("Forwarding to", "Boards that receive new photos/CSVs automatically."),
        ("ADD / DEL", "Manually add or remove a board name from forwarding."),
        ("MENU", "Return to the main menu."),
    ]),
    "photos": ("Photos", [
        ("List", "Every picture in this photo set -- tap to pick one."),
        ("REFRESH", "Rescans the folder for new files."),
        ("USE PHOTO", "Attaches the picked photo to whatever you came here from."),
        ("CLEAR PHOTO", "Removes the current attachment (doesn't delete the file)."),
        ("SHOW PIC", "Displays the picked photo full-screen."),
        ("DELETE", "Deletes the picked photo file -- press twice to confirm."),
        ("UPLOAD STATUS", "Shows the URL to browse to for uploading photos from a phone."),
        ("SEND TO BOARD", "Sends the picked photo to every board saved on the Wifi page."),
        ("RENAME", "Renames the picked photo."),
        ("BACK", "Return to where you came from."),
    ]),
    "sdimport": ("Import from SD", [
        ("List", "Every file and folder at this location on the SD card -- tap a folder to open it, tap a file to pick it."),
        ("REFRESH", "Rescans the current folder for new files."),
        ("IMPORT", "Copies the picked file in. Photos (.jpg/.bmp) go to the photo library; anything else goes to a general imported-files folder."),
        ("MENU", "Return to the main menu."),
    ]),
    "model3d": ("3D Model Editor", [
        ("Vertices list", "Every vertex you've added so far -- tap one to select it (for deleting)."),
        ("X / Y / Z / Grid + ADD VERTEX", "Type coordinates and add a new vertex -- snapped to the grid size if it's non-zero."),
        ("DEL SELECTED (vertex)", "Deletes the selected vertex -- blocked if a face still uses it (delete that face first)."),
        ("Faces list", "Every face you've added so far -- tap one to select it (for deleting)."),
        ("Vertex indices + ADD FACE", "Type the vertex numbers for a face, comma-separated (e.g. 0,1,2,3), then add it in the current colour."),
        ("COLOR", "Cycles the colour used for the next face you add."),
        ("DEL SELECTED (face)", "Deletes the selected face."),
        ("Name / SAVE / LOAD", "Saves or loads the model to/from the SD card under that name."),
        ("Saved models list", "Every model you've saved -- tap one to load it directly, no need to type the name."),
        ("UNDO", "Reverts the last add/delete/load/extrude -- up to 20 steps back."),
        ("CLEAR ALL", "Empties the current model completely -- doesn't touch any saved files."),
        ("2D SKETCH", "Draw a flat outline (snapped to a grid) and extrude it into a solid -- see below."),
        ("LOAD DEMO CAR", "Loads a simple placeholder box-car as a starting example you can edit."),
        ("VIEW / ROTATE", "Switches to the viewer: rotate the model and toggle wireframe/solid."),
        ("EDIT", "From the viewer, switches back to editing."),
        ("MENU", "Return to the main menu."),
    ]),
    "calculator": ("Calculator", [
        ("Digits/operators", "Tap to build up an expression, same as any basic calculator."),
        ("=", "Evaluates the expression typed so far."),
        ("<-", "Backspace -- removes the last character typed."),
        ("C", "Clears the expression completely."),
        ("MENU", "Return to the main menu."),
    ]),
    "export": ("Export / Import", [
        ("Option list (left)", "Choose what to export: all members, cars, events, or today's changed members."),
        ("Send last export to IP", "Type another board's address here to send it directly by IP."),
        ("SEND TO BOARD", "Sends the most recent export to that IP."),
        ("EMAIL LAST", "Emails the most recent export as a CSV attachment."),
        ("EXPORT", "Writes the selected option out to a CSV file on the SD card."),
        ("Import list (right)", "CSV files found that match the selected type -- tap to pick."),
        ("REFRESH LIST", "Rescans for CSV files."),
        ("IMPORT", "Loads the picked CSV into the database -- press twice to confirm."),
        ("DELETE", "Deletes the picked CSV file -- press twice to confirm."),
        ("MENU", "Back to the main menu."),
    ]),
    "email_member": ("Email Member", [
        ("To", "The recipient's email address, pre-filled from this member's record if they have one."),
        ("Subject / Message", "What to send. Message is a single line on this screen."),
        ("SEND", "Sends the email using the club's configured email account."),
        ("BACK", "Return to the Members page."),
    ]),
}


class HelpPage(Page):
    def __init__(self, topic, return_to):
        Page.__init__(self)
        self.topic = topic
        self.return_to = return_to

    def wrap(self, text, width=76):
        words = text.split(" ")
        lines = []
        cur = ""
        for word in words:
            candidate = (cur + " " + word).strip()
            if len(candidate) <= width:
                cur = candidate
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        if len(lines) > 2:
            lines = lines[:2]
            lines[1] = lines[1][:width - 3] + "..."
        return lines

    def build(self, g):
        title, entries = HELP_TEXT.get(self.topic, ("Help", []))
        g.caption(320, 6, "Help -- " + title, fg=INK, bg=PAGE, font=3, just="CT")
        g.button(486, 4, 140, 28, "BACK", fg=WHITE, bg=RED, font=2, callback=self.on_back)
        y = 34
        for label, desc in entries:
            if y > 404:
                break  # keep it on one screen -- longer topics get trimmed
            g.caption(20, y, label, fg=INK, bg=PAGE, font=2)
            y += 18
            for line in self.wrap(desc):
                g.caption(30, y, line, fg=INK, bg=PAGE, font=1)
                y += 14
            y += 8
        self.footer(g)

    def enter(self):
        self.say("Help for " + HELP_TEXT.get(self.topic, ("this page", []))[0])

    def on_back(self, b):
        self.go(self.return_to)


class Menu(Page):
    def build(self, g):
        g.caption(320, 8, "Tailem-Bend Car Club", fg=INK, bg=PAGE, font=3, just="CT")
        g.caption(556, 10, "v" + CLUB_VERSION, fg=INK, bg=PAGE, font=1)

        # -- status panel --------------------------------------------
        g.frame(20, 36, 600, 54, "Status", fg=INK, font=1)
        self.info = g.displaybox(30, 52, 280, 18, "", fg=INK, bg=PAGE, font=1)
        self.ev = g.displaybox(320, 52, 290, 18, "", fg=INK, bg=PAGE, font=1)
        self.net = g.displaybox(30, 72, 580, 14, "", fg=INK, bg=PAGE, font=1)

        # -- main action grid (2 columns, uniform buttons) -------------
        col1, col2 = 20, 320
        w, h, gap = 280, 56, 14
        row1, row2, row3, row4 = 104, 104 + (h + gap), 104 + 2 * (h + gap), 104 + 3 * (h + gap)

        g.button(col1, row1, w, h, "MEMBERS", fg=WHITE, bg=BTN, font=3, callback=self.on_members)
        g.button(col2, row1, w, h, "EVENTS", fg=WHITE, bg=BTN, font=3, callback=self.on_events)

        g.button(col1, row2, w, h, "WIFI", fg=WHITE, bg=BTN, font=3, callback=self.on_wifi)
        g.button(col2, row2, w, h, "PHOTOS", fg=WHITE, bg=BTN, font=3, callback=self.on_photos)

        g.button(col1, row3, w, h, "IMPORT SD", fg=WHITE, bg=BTN, font=3, callback=self.on_import)
        g.button(col2, row3, w, h, "EXPORT / IMPORT", fg=WHITE, bg=BTN, font=2, callback=self.on_export)

        g.button(col1, row4, w, h, "EMAIL", fg=WHITE, bg=BTN, font=3, callback=self.on_email_shortcut)
        g.button(col2, row4, w, h, "QUIT", fg=WHITE, bg=RED, font=3, callback=self.on_quit)

        g.button(20, 386, 296, 30, "3D MODEL EDITOR", fg=WHITE, bg=BTN, font=1, callback=self.on_model3d)
        g.button(324, 386, 296, 30, "CALCULATOR", fg=WHITE, bg=BTN, font=1, callback=self.on_calculator)

        self.footer(g)
        self.help_button(g, "menu", "menu")

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
        sta = network.WLAN(network.STA_IF)
        n = 0
        try:
            n = len(os.listdir(PHOTO_DIR))
        except OSError:
            pass
        if sta.active() and sta.isconnected():
            self.net.value = "Wifi: " + sta.ifconfig()[0] + ":8080   " + str(n) + " picture(s) in " + PHOTO_DIR
        else:
            self.net.value = "Wifi: not connected   " + str(n) + " picture(s) in " + PHOTO_DIR
        self.update_ticker_text()
        self.last_gps_attempt = 0
        self._seen_received_file = last_received_file
        self._seen_gps_fix = last_gps_fix

    def update_ticker_text(self):
        global last_gps_fix, last_received_file, last_received_time
        text = "Welcome to Tailem-Bend Car Club"
        if last_gps_fix:
            text += "   |   GPS: %.5f, %.5f" % last_gps_fix
        else:
            text += "   |   GPS: (no fix yet)"
        if last_received_file:
            text += "   |   Received: " + last_received_file + " at " + last_received_time
        self.say(text)

    def page_tick(self):
        global last_gps_fix, last_gps_check, last_received_file
        # cheap checks every tick -- no I/O, just variable compares --
        # so a file arriving, or a phone GPS fix landing, shows up
        # immediately rather than waiting on the next 20s cycle
        if last_received_file != self._seen_received_file:
            self._seen_received_file = last_received_file
            self.update_ticker_text()
        if last_gps_fix != self._seen_gps_fix:
            self._seen_gps_fix = last_gps_fix
            self.update_ticker_text()
        now = time.ticks_ms()
        # only attempt a GPS read every 20s, and only a quick one --
        # a full-length read would freeze the whole menu each time
        if time.ticks_diff(now, last_gps_check) < 20000:
            return
        last_gps_check = now
        fix, err = read_gps_fix(timeout_ms=300)
        if fix:
            last_gps_fix = fix
            self.update_ticker_text()

    def on_members(self, b):
        self.go("members")

    def on_events(self, b):
        self.go("events")

    def on_wifi(self, b):
        self.go("wifi")

    def on_photos(self, b):
        self.go("genphotos")

    def on_import(self, b):
        self.go("sdimport")

    def on_model3d(self, b):
        self.go("model3d")

    def on_calculator(self, b):
        self.go("calculator")

    def on_export(self, b):
        self.go("export")

    def on_email_shortcut(self, b):
        self.go("export")

    def on_quit(self, b):
        self.go("exit")


class WifiPage(Page):
    def build(self, g):
        g.caption(320, 6, "Wifi Setup", fg=INK, bg=PAGE, font=3, just="CT")

        # static status bar -- separate from the scrolling footer ticker,
        # so button confirmations are clearly visible and don't scroll
        # away or get missed
        self.status_box = g.displaybox(14, 24, 612, 24, "Ready", fg=WHITE, bg=BTN, font=2)

        # -- Connect to Wi-Fi --------------------------------------
        g.frame(14, 56, 300, 168, "Connect to Wi-Fi", fg=INK, font=2)
        g.caption(24, 82, "Network name (SSID)", fg=INK, bg=PAGE, font=1)
        self.ssid = g.textbox(24, 98, 270, 28, font=2)
        g.caption(24, 134, "Password", fg=INK, bg=PAGE, font=1)
        # pcgui.textbox has no built-in masking option, so we fake it:
        # every poll cycle (via tick), any newly typed characters are
        # captured into self.real_password and the visible box is
        # overwritten with *s.
        self.password = g.textbox(24, 150, 270, 28, font=2)
        self.real_password = ""
        self._masked_len = 0
        g.button(24, 186, 84, 30, "SAVE", fg=WHITE, bg=BTN, font=2, callback=self.on_save)
        g.button(114, 186, 96, 30, "CONNECT", fg=WHITE, bg=BTN, font=2, callback=self.on_connect)
        g.button(216, 186, 88, 30, "DISCONN.", fg=WHITE, bg=RED, font=1, callback=self.on_disconnect)

        # -- Saved networks ------------------------------------------
        g.frame(324, 56, 302, 168, "Saved networks -- tap to select", fg=INK, font=1)
        self.saved_nets = []
        self.saved_list = None
        self.picked_saved_idx = -1
        g.button(332, 194, 90, 24, "DELETE", fg=WHITE, bg=RED, font=1, callback=self.on_delete_saved)

        # -- This board's identity ------------------------------------
        g.frame(14, 232, 300, 66, "This board's name (for discovery)", fg=INK, font=1)
        self.board_name_box = g.textbox(24, 262, 170, 26, font=2)
        g.button(200, 262, 100, 26, "SAVE NAME", fg=WHITE, bg=BTN, font=1, callback=self.on_save_board_name)

        # -- Discovery & forwarding ------------------------------------
        g.frame(324, 232, 302, 168, "Discovered boards / forwarding", fg=INK, font=1)
        g.caption(332, 250, "Tap to add to forwarding:", fg=INK, bg=PAGE, font=1)
        self.discovered_names = []
        self.discovered_list = None
        g.caption(332, 322, "Forwarding to:", fg=INK, bg=PAGE, font=1)
        self.forward_nets = []
        self.forward_list = None
        self.picked_forward_idx = -1
        self.forward_box = g.textbox(332, 372, 160, 24, font=1)
        g.button(496, 372, 54, 24, "ADD", fg=WHITE, bg=BTN, font=1, callback=self.on_add_forward)
        g.button(554, 372, 62, 24, "DEL", fg=WHITE, bg=RED, font=1, callback=self.on_delete_forward)

        g.button(14, 410, 100, 30, "MENU", fg=WHITE, bg=RED, font=2, callback=self.on_back)

        self.footer(g)
        self.help_button(g, "wifi", "wifi")

    def status(self, text):
        # base Page.say() now handles the static status box directly
        self.say(text)

    def enter(self):
        self.ssid.value = ""
        self.real_password = ""
        self._masked_len = 0
        self.password.value = ""
        self.picked_saved_idx = -1
        sta = network.WLAN(network.STA_IF)
        if sta.active() and sta.isconnected():
            self.status("Connected: " + sta.ifconfig()[0] + " -- pick a saved network or type a new one")
        else:
            self.status("Not connected -- pick a saved network or type a new one")
        self.board_name_box.value = get_board_name()
        self.refresh_saved_list()
        self.refresh_forward_list()
        self.refresh_discovered_list()
        self._discovered_check = 0

    def on_save_board_name(self, b):
        name = self.board_name_box.value.strip()
        if not name:
            self.status("Type a name for this board first")
            return
        set_board_name(name)
        self.status("This board is now named '" + name + "' -- other boards will see it once they're on wifi too")

    def refresh_discovered_list(self):
        self.discovered_names = sorted(known_boards.keys())
        items = []
        for name in self.discovered_names:
            ip, last_seen = known_boards[name]
            age_s = time.ticks_diff(time.ticks_ms(), last_seen) // 1000
            items.append(name + "  (" + ip + ", " + str(age_s) + "s ago)")
        if not items:
            items = ["(none seen yet)"]
        if self.discovered_list is not None:
            self.g.remove(self.discovered_list)
        self.discovered_list = self.g.listbox(332, 266, 286, 50, items, 0, font=1, callback=self.on_pick_discovered)

    def on_pick_discovered(self, c):
        i = c.value
        if i < 0 or i >= len(self.discovered_names):
            return
        name = self.discovered_names[i]
        add_forward_ip(name)
        self.refresh_forward_list()
        self.status("Added '" + name + "' to forwarding list")

    def refresh_saved_list(self):
        self.saved_nets = load_wifi_list()
        items = [ssid for ssid, pw in self.saved_nets]
        if not items:
            items = ["(none saved yet)"]
        if self.saved_list is not None:
            self.g.remove(self.saved_list)
        self.saved_list = self.g.listbox(332, 78, 286, 110, items, 0, font=1, callback=self.on_pick_saved)

    def on_pick_saved(self, c):
        i = c.value
        if i < 0 or i >= len(self.saved_nets):
            return
        self.picked_saved_idx = i
        ssid, password = self.saved_nets[i]
        self.ssid.value = ssid
        self.real_password = password
        self._masked_len = len(password)
        self.password.value = "*" * len(password)
        self.status("Selected " + ssid + " -- press CONNECT to switch to it")

    def on_delete_saved(self, b):
        i = getattr(self, "picked_saved_idx", -1)
        if i < 0 or i >= len(self.saved_nets):
            self.status("Tap a saved network in the list first, then DELETE")
            return
        ssid = self.saved_nets[i][0]
        remove_wifi(ssid)
        self.picked_saved_idx = -1
        self.refresh_saved_list()
        self.status("Removed saved network " + ssid)

    def refresh_forward_list(self):
        self.forward_nets = load_forward_ips()
        items = list(self.forward_nets)
        if not items:
            items = ["(none saved -- forwarding off)"]
        if self.forward_list is not None:
            self.g.remove(self.forward_list)
        self.forward_list = self.g.listbox(332, 338, 286, 30, items, 0, font=1, callback=self.on_pick_forward)

    def on_pick_forward(self, c):
        i = c.value
        if 0 <= i < len(self.forward_nets):
            self.picked_forward_idx = i

    def on_add_forward(self, b):
        name = self.forward_box.value.strip()
        if not name:
            self.status("Type a board name first (or tap one in Discovered)")
            return
        add_forward_ip(name)
        self.forward_box.value = ""
        self.refresh_forward_list()
        self.status("Added '" + name + "' -- uploads now broadcast to " + str(len(self.forward_nets)) + " board(s)")

    def on_delete_forward(self, b):
        i = getattr(self, "picked_forward_idx", -1)
        if i < 0 or i >= len(self.forward_nets):
            self.status("Tap a board in the forward list first, then DELETE")
            return
        name = self.forward_nets[i]
        remove_forward_ip(name)
        self.picked_forward_idx = -1
        self.refresh_forward_list()
        self.status("Removed '" + name + "' from forwarding")

    def page_tick(self):
        self.mask_password()
        now = time.ticks_ms()
        if time.ticks_diff(now, getattr(self, "_discovered_check", 0)) >= 5000:
            self._discovered_check = now
            self.refresh_discovered_list()

    def mask_password(self):
        val = self.password.value
        cur_len = len(val)
        if cur_len > self._masked_len:
            self.real_password += val[self._masked_len:cur_len]
        elif cur_len < self._masked_len:
            self.real_password = self.real_password[:cur_len]
        self._masked_len = cur_len
        stars = "*" * cur_len
        if val != stars:
            self.password.value = stars

    def on_save(self, b):
        ssid = self.ssid.value.strip()
        password = self.real_password
        if not ssid:
            self.status("Enter a network name first")
            return
        save_wifi(ssid, password)
        self.refresh_saved_list()
        self.status("Saved " + ssid + " for future use")

    def on_connect(self, b):
        ssid = self.ssid.value.strip()
        password = self.real_password
        if not ssid:
            self.status("Enter a network name first")
            return
        self.do_connect(ssid, password)

    def do_connect(self, ssid, password):
        sta = network.WLAN(network.STA_IF)

        # if we're already connected (e.g. pressing CONNECT again on
        # the same network), don't disturb a working connection at all
        if sta.active() and sta.isconnected():
            self.status("Already connected: " + sta.ifconfig()[0])
            return

        for attempt in (1, 2):
            self.status("Connecting to " + ssid + " (try " + str(attempt) + ") ...")
            try:
                sta.disconnect()
            except Exception:
                pass
            sta.active(False)
            time.sleep_ms(500)
            sta.active(True)
            time.sleep_ms(200)
            sta.connect(ssid, password)
            ok = False
            for i in range(15):
                if sta.isconnected():
                    ok = True
                    break
                time.sleep(1)
            if ok:
                self.status("Connected: " + sta.ifconfig()[0] + " -- syncing time...")
                if synctime():
                    self.status("Connected: " + sta.ifconfig()[0] + "  (time synced)")
                else:
                    self.status("Connected: " + sta.ifconfig()[0] + "  (time sync failed)")
                return
        self.status("Failed to connect to " + ssid + " after 2 tries")

    def on_disconnect(self, b):
        sta = network.WLAN(network.STA_IF)
        was_connected = sta.active() and sta.isconnected()
        if was_connected:
            sta.disconnect()
        self.ssid.value = ""
        self.real_password = ""
        self._masked_len = 0
        self.password.value = ""
        self.picked_saved_idx = -1
        if was_connected:
            self.status("Disconnected")
        else:
            self.status("Not connected")

    def on_back(self, b):
        self.go("menu")


PHOTO_DIR = "/sd/cars"


def jpeg_size(path):
    # reads just the SOF marker to get width/height, without
    # decoding any pixel data
    f = open(path, "rb")
    try:
        if f.read(2) != b"\xff\xd8":
            return None
        while True:
            marker = f.read(2)
            if len(marker) < 2 or marker[0] != 0xFF:
                return None
            code = marker[1]
            if code in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                        0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                f.read(2)  # segment length, not needed here
                seg = f.read(5)
                if len(seg) < 5:
                    return None
                height = (seg[1] << 8) | seg[2]
                width = (seg[3] << 8) | seg[4]
                return width, height
            elif code == 0xD8 or code == 0xD9 or (0xD0 <= code <= 0xD7):
                continue
            else:
                seglen_bytes = f.read(2)
                if len(seglen_bytes) < 2:
                    return None
                seglen = (seglen_bytes[0] << 8) | seglen_bytes[1]
                f.seek(seglen - 2, 1)
    except Exception:
        return None
    finally:
        f.close()


def bmp_size(path):
    f = open(path, "rb")
    try:
        header = f.read(26)
        if len(header) < 26 or header[0:2] != b"BM":
            return None
        width = struct.unpack("<i", header[18:22])[0]
        height = struct.unpack("<i", header[22:26])[0]
        return width, abs(height)
    except Exception:
        return None
    finally:
        f.close()


def url_unquote(s):
    # minimal percent-decoding, e.g. "%20" -> " " -- avoids needing
    # a urllib module that may not exist on this board
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "%" and i + 2 < n:
            try:
                out.append(chr(int(s[i + 1:i + 3], 16)))
                i += 3
                continue
            except ValueError:
                pass
        out.append(c)
        i += 1
    return "".join(out)


def render_picture_fullscreen(path, filename):
    # switches to RGB1024 for the duration of the preview -- RGB640
    # turned out to be a low color-depth mode (fine for the app's flat
    # UI colors, not enough for real photos), so we need the higher
    # mode for decent quality. To give the switch the best chance of
    # being stable: free memory with gc.collect() before touching the
    # display, and give the monitor extra time to re-lock before we
    # draw or switch back.
    # Caller is responsible for stopping its own GUI before calling
    # this and rebuilding its widgets afterward -- this function never
    # touches any GUI object, just the raw display. Returns an error
    # message string on failure, or None on success.
    low = filename.lower()
    is_bmp = low.endswith(".bmp")
    error = None
    gc.collect()
    try:
        hdmi.deinit()
        hdmi.init(hdmi.RGB1024)
        time.sleep(4)  # let the monitor re-lock before drawing
    except Exception as e:
        ulog("render_picture: RGB1024 switch failed: " + str(e))
        return "Could not switch display mode: " + str(e)
    try:
        hdmi.fill(0)
        size = bmp_size(path) if is_bmp else jpeg_size(path)
        CANVAS_W, CANVAS_H = 1024, 600
        draw_y = 30
        scale = 8
        if size:
            # pick the sharpest scale whose WIDTH fits -- height is
            # allowed to run off the bottom of the screen (naturally
            # clipped) rather than always falling back to the most
            # aggressive scale just to guarantee the whole photo fits
            for s in (2, 4, 8):
                w = max(1, size[0] // (1 if is_bmp else s))
                if w <= CANVAS_W:
                    scale = s
                    break
            decoded_w = max(1, size[0] // (1 if is_bmp else scale))
            decoded_h = max(1, size[1] // (1 if is_bmp else scale))
        else:
            decoded_w = decoded_h = 300
        draw_x = max(0, (CANVAS_W - decoded_w) // 2)
        if decoded_h > CANVAS_H - draw_y:
            ulog("render_picture: " + filename + " decoded " + str(decoded_w) + "x" +
                 str(decoded_h) + " -- taller than 1024x600 even at max scale")
        try:
            fb = hdmi.fb()
            hdmi.text(filename, 10, 4, fb.colour(WHITE), -1, 1, 1)
        except Exception as e:
            ulog("render_picture: filename text failed: " + str(e))
        if is_bmp:
            pcimage.draw_bmp(path, draw_x, draw_y, dither=True)
        else:
            pcimage.draw_jpg(path, draw_x, draw_y, scale, dither=True)
        time.sleep(2)
    except Exception as e:
        error = str(e)
    finally:
        try:
            hdmi.deinit()
            hdmi.init(hdmi.RGB640)
            time.sleep(4)
        except Exception as e:
            ulog("render_picture: RGB640 switch-back failed: " + str(e))
    return error


def preview_picture(page, path, filename):
    page.say("Rendering " + filename + " ... please wait")
    try:
        page.g.stop()
    except Exception:
        pass
    err = render_picture_fullscreen(path, filename)
    hdmi.fill(hdmi.fb().colour(PAGE))
    g = pcgui.GUI()
    page.g = g
    g.start()
    page.build(g)
    page.enter()
    if err:
        page.say("Could not show picture: " + err)


def receive_file_to(conn, already, length, filename, dest_dir, max_seconds=45):
    try:
        os.mkdir(dest_dir)
    except OSError:
        pass
    path = dest_dir + "/" + filename
    start = time.ticks_ms()
    f = open(path, "wb")
    try:
        written = 0
        if already:
            take = already[:length]
            f.write(take)
            written += len(take)
        while written < length:
            if time.ticks_diff(time.ticks_ms(), start) > max_seconds * 1000:
                ulog("receive_file_to: " + filename + " exceeded " + str(max_seconds) +
                     "s, aborting with " + str(written) + " of " + str(length) + " bytes")
                break
            chunk = conn.recv(min(2048, length - written))
            if not chunk:
                break
            f.write(chunk)
            written += len(chunk)
    finally:
        f.close()


def send_upload_page_html(conn):
    html = (
        "<html><head>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<style>"
        "body{font-family:sans-serif;font-size:28px;padding:20px;}"
        "h1{font-size:38px;font-weight:bold;margin:0 0 4px 0;}"
        "h2{font-size:32px;font-weight:bold;margin-top:0;}"
        "label{font-size:26px;display:block;margin-top:10px;}"
        "input[type=text]{font-size:28px;padding:12px;width:100%;box-sizing:border-box;"
        "margin-bottom:14px;}"
        "input[type=file]{font-size:24px;display:block;margin:20px 0;}"
        "button{font-size:30px;padding:18px 36px;background:#2E7D32;color:white;"
        "border:none;border-radius:8px;}"
        "#msg{font-size:26px;margin-top:20px;}"
        "</style>"
        "</head><body>"
        "<h1>Tailem-Bend Car Club</h1>"
        "<h2>Upload File</h2>"
        "<input type='file' id='f' accept='image/*' onchange='picked()'>"
        "<label>Save as:</label>"
        "<input type='text' id='name' placeholder='name for this photo'>"
        "<button onclick='go()'>Upload</button>"
        "<p id='msg'></p>"
        "<script>"
        "function picked(){"
        "var file=document.getElementById('f').files[0];"
        "if(!file){return;}"
        "var nameBox=document.getElementById('name');"
        "if(!nameBox.value.trim()){"
        "var n=file.name||'photo.jpg';"
        "nameBox.value=n;"
        "}"
        "}"
        "async function go(){"
        "var file=document.getElementById('f').files[0];"
        "if(!file){document.getElementById('msg').innerText='Pick a file first';return;}"
        "var wanted=document.getElementById('name').value.trim();"
        "var name=file.name;"
        "if(wanted){"
        "if(!/\\.[a-zA-Z0-9]+$/.test(wanted)){wanted=wanted+'.jpg';}"
        "name=wanted;"
        "}"
        "document.getElementById('msg').innerText='Preparing...';"
        "var blob=file;"
        "try{"
        "if(window.createImageBitmap){"
        "var bmp=await createImageBitmap(file,{imageOrientation:'from-image'});"
        "var canvas=document.createElement('canvas');"
        "canvas.width=bmp.width;"
        "canvas.height=bmp.height;"
        "var ctx=canvas.getContext('2d');"
        "ctx.drawImage(bmp,0,0);"
        "var made=await new Promise(function(res){canvas.toBlob(res,'image/jpeg',0.9);});"
        "if(made){blob=made;}"
        "}"
        "}catch(e){blob=file;}"
        "document.getElementById('msg').innerText='Uploading...';"
        "fetch('/upload/'+encodeURIComponent(name),{method:'POST',body:blob})"
        ".then(function(r){return r.text();})"
        ".then(function(t){document.getElementById('msg').innerText=t;})"
        ".catch(function(e){document.getElementById('msg').innerText='Failed: '+e;});"
        "}"
        "</script>"
        "</body></html>"
    )
    body = html.encode()
    conn.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: " +
               str(len(body)).encode() + b"\r\nConnection: close\r\n\r\n" + body)


def send_gps_page_html(conn):
    html = (
        "<html><head>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<style>"
        "body{font-family:sans-serif;font-size:28px;padding:20px;}"
        "h1{font-size:38px;font-weight:bold;margin:0 0 4px 0;}"
        "h2{font-size:32px;font-weight:bold;margin-top:0;}"
        "button{font-size:30px;padding:18px 36px;background:#2E7D32;color:white;"
        "border:none;border-radius:8px;}"
        "#msg{font-size:26px;margin-top:20px;}"
        "#note{font-size:20px;margin-top:30px;color:#555;}"
        "</style>"
        "</head><body>"
        "<h1>Tailem-Bend Car Club</h1>"
        "<h2>Send Phone GPS to Board</h2>"
        "<button onclick='send()'>SEND MY LOCATION NOW</button>"
        "<div id='msg'>Starting automatic updates...</div>"
        "<div id='note'>This page auto-sends your location every 5 minutes "
        "while it stays open. Leave this tab open (don't lock the phone) "
        "for continuous updates.</div>"
        "<script>"
        "function send(){"
        "document.getElementById('msg').innerText='Getting location...';"
        "if(!navigator.geolocation){"
        "document.getElementById('msg').innerText='This browser has no GPS support';"
        "return;}"
        "navigator.geolocation.getCurrentPosition(function(pos){"
        "var lat=pos.coords.latitude;var lon=pos.coords.longitude;"
        "fetch('/gpslocation?lat='+lat+'&lon='+lon)"
        ".then(function(r){return r.text();})"
        ".then(function(t){var now=new Date().toLocaleTimeString();"
        "document.getElementById('msg').innerText='Last sent '+now+': '+lat.toFixed(5)+', '+lon.toFixed(5);})"
        ".catch(function(e){document.getElementById('msg').innerText='Send failed: '+e;});"
        "}, function(err){"
        "document.getElementById('msg').innerText='Location error: '+err.message;"
        "}, {enableHighAccuracy:true, timeout:15000});"
        "}"
        "send();"
        "setInterval(send, 5*60*1000);"
        "</script>"
        "</body></html>"
    )
    body = html.encode()
    conn.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: " +
               str(len(body)).encode() + b"\r\nConnection: close\r\n\r\n" + body)


def handle_upload_connection(conn):
    # shared GET/POST handling used by both the background service and
    # any page's own on-demand server
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = conn.recv(512)
        if not chunk:
            ulog("handle_upload: connection closed before headers finished")
            return
        buf += chunk
    head, rest = buf.split(b"\r\n\r\n", 1)
    lines = head.split(b"\r\n")
    request_line = lines[0].decode()
    parts = request_line.split(" ")
    method = parts[0] if len(parts) > 0 else ""
    path = parts[1] if len(parts) > 1 else "/"
    ulog("handle_upload: " + method + " " + path)

    headers = {}
    for line in lines[1:]:
        if b":" in line:
            k, v = line.split(b":", 1)
            headers[k.strip().lower().decode()] = v.strip().decode()

    if method == "GET" and path == "/":
        send_upload_page_html(conn)
        return

    if method == "GET" and path == "/gps":
        send_gps_page_html(conn)
        return

    if method == "GET" and path.startswith("/gpslocation"):
        global last_gps_fix
        try:
            qs = path.split("?", 1)[1] if "?" in path else ""
            params = {}
            for pair in qs.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = v
            lat = float(params["lat"])
            lon = float(params["lon"])
            last_gps_fix = (lat, lon)
            ulog("gpslocation: received phone fix " + str(lat) + "," + str(lon))
            body = b"OK"
        except Exception as e:
            ulog("gpslocation: bad request: " + str(e))
            body = b"ERROR " + str(e).encode()
        conn.send(b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body)).encode() +
                   b"\r\nConnection: close\r\n\r\n" + body)
        return

    if method == "POST" and path.startswith("/upload/"):
        filename = path[len("/upload/"):]
        filename = url_unquote(filename)
        filename = filename.replace("/", "_").replace("..", "_")
        if not filename:
            filename = "upload_" + stamp().replace(" ", "_").replace(":", "") + ".jpg"
        length = int(headers.get("content-length", "0"))
        dest_dir = EXPORT_DIR if filename.lower().endswith(".csv") else PHOTO_DIR
        ulog("handle_upload: receiving " + filename + " length=" + str(length) + " -> " + dest_dir)
        receive_file_to(conn, rest, length, filename, dest_dir)
        actual = 0
        try:
            actual = os.stat(dest_dir + "/" + filename)[6]
        except OSError:
            pass
        ulog("handle_upload: wrote " + filename + " actual_size=" + str(actual))
        if dest_dir == EXPORT_DIR:
            global last_received_file, last_received_time
            imported_note = ""
            if filename.lower().startswith("member") and filename.lower().endswith(".csv"):
                try:
                    n = import_members_csv(dest_dir + "/" + filename)
                    imported_note = " (auto-imported " + str(n) + " member row(s))"
                    ulog("handle_upload: auto-imported " + str(n) + " from " + filename)
                except Exception as e:
                    imported_note = " (auto-import FAILED: " + str(e) + ")"
                    ulog("handle_upload: auto-import failed: " + str(e))
            last_received_file = filename + imported_note
            last_received_time = stamp()
        body = b"OK saved " + filename.encode()
        conn.send(b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body)).encode() +
                   b"\r\nConnection: close\r\n\r\n" + body)
        if dest_dir == PHOTO_DIR:
            for fwd_name in load_forward_ips():
                fwd_ip = resolve_board_ip(fwd_name)
                if not fwd_ip:
                    ulog("handle_upload: skip forward to " + fwd_name + " -- not seen on network recently")
                    continue
                ulog("handle_upload: forwarding " + filename + " to " + fwd_name + " (" + fwd_ip + ")")
                ok = forward_upload(fwd_ip, dest_dir + "/" + filename, filename)
                ulog("handle_upload: forward to " + fwd_name + " " + ("OK" if ok else "FAILED"))
        return

    conn.send(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")


# --- background upload service ------------------------------------
# runs independent of whatever page is currently showing, started
# automatically once wifi is connected, so nobody has to manually
# navigate to a Photos page and press WIFI UPLOAD before a send/
# forward/phone-upload will work.
background_server = None
background_last_attempt = 0


def start_background_server():
    global background_server
    if background_server is not None:
        return True
    sta = network.WLAN(network.STA_IF)
    if not (sta.active() and sta.isconnected()):
        return False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", 8080))
        s.listen(1)
        s.setblocking(False)
        background_server = s
        ulog("background: listening on 0.0.0.0:8080, ip=" + sta.ifconfig()[0])
        return True
    except Exception as e:
        ulog("background: failed to start: " + str(e))
        return False


def background_tick():
    global background_server, background_last_attempt
    if background_server is None:
        now = time.ticks_ms()
        if time.ticks_diff(now, background_last_attempt) < 10000:
            return
        background_last_attempt = now
        start_background_server()
        return
    try:
        conn, addr = background_server.accept()
    except Exception:
        return
    try:
        conn.settimeout(10)
        handle_upload_connection(conn)
    except Exception as e:
        ulog("background: EXCEPTION " + type(e).__name__ + " " + str(e))
    finally:
        try:
            conn.close()
        except Exception:
            pass


# --- board discovery (name -> current IP) --------------------------
# IPs change when a board reconnects to wifi (DHCP), so boards are
# identified by a fixed name instead. Each board broadcasts its own
# name+IP over UDP every 15s; every board also listens for these
# broadcasts and keeps a live name->(ip, last_seen) map. Forwarding
# (photo relay, UPDATE, etc.) looks a saved NAME up in this map to
# get a current IP, instead of trusting a possibly-stale saved IP.
DISCOVERY_PORT = 8091
known_boards = {}          # name -> (ip, last_seen_ticks_ms)
discovery_socket = None
discovery_last_broadcast = 0


def get_board_name():
    name = setting("board_name")
    return name if name else ""


def set_board_name(name):
    setting("board_name", name)


def start_discovery_socket():
    global discovery_socket
    if discovery_socket is not None:
        return True
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", DISCOVERY_PORT))
        s.setblocking(False)
        discovery_socket = s
        ulog("discovery: listening on UDP " + str(DISCOVERY_PORT))
        return True
    except Exception as e:
        ulog("discovery: failed to start: " + str(e))
        return False


def discovery_tick():
    global discovery_socket, discovery_last_broadcast
    sta = network.WLAN(network.STA_IF)
    if not (sta.active() and sta.isconnected()):
        return
    if discovery_socket is None:
        start_discovery_socket()
        if discovery_socket is None:
            return

    # broadcast our own name+IP every 15s
    now = time.ticks_ms()
    if time.ticks_diff(now, discovery_last_broadcast) >= 15000:
        discovery_last_broadcast = now
        name = get_board_name()
        if name:
            try:
                msg = ("CLUBBOARD|" + name + "|" + sta.ifconfig()[0]).encode()
                bsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                bsock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                bsock.sendto(msg, ("255.255.255.255", DISCOVERY_PORT))
                bsock.close()
            except Exception as e:
                ulog("discovery: broadcast failed: " + str(e))

    # drain any incoming broadcasts from other boards (non-blocking)
    for _ in range(5):
        try:
            data, addr = discovery_socket.recvfrom(200)
        except Exception:
            break
        try:
            text = data.decode()
            parts = text.split("|")
            if len(parts) == 3 and parts[0] == "CLUBBOARD":
                other_name, other_ip = parts[1], parts[2]
                if other_name and other_name != get_board_name():
                    known_boards[other_name] = (other_ip, time.ticks_ms())
        except Exception:
            pass

    # forget boards we haven't heard from in a while, so a decommissioned
    # or renamed board doesn't linger forever in the Discovered list
    stale = [n for n, (ip, last_seen) in known_boards.items()
             if time.ticks_diff(time.ticks_ms(), last_seen) > 300000]
    for n in stale:
        del known_boards[n]


def resolve_board_ip(name, max_age_ms=120000):
    # returns a current IP for a saved board name, or None if we
    # haven't heard from it recently. Matching ignores case and extra
    # spacing, since a name typed by hand (forward list) and a name
    # broadcast by the other board (SAVE NAME) can easily differ only
    # in case/whitespace otherwise.
    #
    # If more than one differently-cased entry exists for the same
    # logical name (e.g. leftover "Board 2" alongside current
    # "board2"), check ALL of them for a fresh one rather than
    # stopping at whichever matches first -- a stale duplicate
    # shouldn't be able to block a fresher one from being found.
    target = name.strip().lower()
    best_ip = None
    best_age = None
    for known_name, (ip, last_seen) in known_boards.items():
        if known_name.strip().lower() != target:
            continue
        age = time.ticks_diff(time.ticks_ms(), last_seen)
        if age <= max_age_ms and (best_age is None or age < best_age):
            best_ip = ip
            best_age = age
    return best_ip


class PhotosPage(Page):
    # generic photo browser/picker/uploader -- subclasses provide the
    # hooks below to say what this page is attached to (a member or a
    # specific car) without duplicating all the browsing/upload logic.
    ROUTE_NAME = "genphotos"

    def __init__(self):
        Page.__init__(self)
        self.picked = ""

    def get_label(self):
        return ""

    def get_current_photo(self):
        return ""

    def set_current_photo(self, name):
        pass

    def get_back_route(self):
        return "menu"

    def sync_rename(self, old_name, new_name):
        pass

    def sync_delete(self, name):
        pass

    def build(self, g):
        self.build_header(g)
        self.list = None
        self.build_controls(g)
        self.footer(g)
        self.help_button(g, "photos", self.ROUTE_NAME)
        self.delete_armed = False

    def build_header(self, g):
        # title/label -- pulled into its own method so it can be
        # recreated if needed (e.g. after a full refresh restart)
        old = getattr(self, "header_widgets", None)
        if old:
            for w in old:
                try:
                    g.remove(w)
                except Exception:
                    pass
        widgets = []
        widgets.append(g.caption(320, 6, "Photos", fg=INK, bg=PAGE, font=3, just="CT"))
        widgets.append(g.caption(14, 44, self.get_label(), fg=INK, bg=PAGE, font=2))
        self.header_widgets = widgets

    def build_controls(self, g):
        # all interactive controls live in a column on the right
        # (x >= 330), physically separate from the image/list area on
        # the left -- so a picture being previewed can never overlap
        # any of these, no masking/overlap tracking needed
        old = getattr(self, "control_widgets", None)
        if old:
            for w in old:
                try:
                    g.remove(w)
                except Exception:
                    pass
        rx, rw = 480, 150
        widgets = []
        widgets.append(g.button(rx, 100, rw, 28, "REFRESH", fg=WHITE, bg=BTN, font=1, callback=self.on_refresh))
        widgets.append(g.button(rx, 132, rw, 28, "USE PHOTO", fg=WHITE, bg=BTN, font=1, callback=self.on_use))
        widgets.append(g.button(rx, 164, rw, 28, "CLEAR PHOTO", fg=WHITE, bg=BTN, font=1, callback=self.on_clear))
        widgets.append(g.button(rx, 196, rw, 28, "SHOW PIC", fg=WHITE, bg=BTN, font=1, callback=self.on_show))
        widgets.append(g.button(rx, 228, rw, 28, "DELETE", fg=WHITE, bg=RED, font=1, callback=self.on_delete))
        widgets.append(g.button(rx, 260, rw, 28, "UPLOAD STATUS", fg=WHITE, bg=BTN, font=1, callback=self.on_wifi_upload))
        widgets.append(g.button(rx, 292, rw, 28, "SEND TO BOARD", fg=WHITE, bg=BTN, font=1, callback=self.on_send_to_board))
        widgets.append(g.caption(rx, 326, "Rename to", fg=INK, bg=PAGE, font=1))
        self.rename_box = g.textbox(rx, 344, rw, 24, font=1)
        widgets.append(self.rename_box)
        widgets.append(g.button(rx, 374, rw, 24, "RENAME", fg=WHITE, bg=BTN, font=1, callback=self.on_rename))
        widgets.append(g.button(rx, 406, rw, 28, "BACK", fg=WHITE, bg=RED, font=1, callback=self.on_back))
        self.control_widgets = widgets


    def enter(self):
        self.refresh()

    def refresh(self):
        names = []
        try:
            for f in os.listdir(PHOTO_DIR):
                if f.lower().endswith(".jpg") or f.lower().endswith(".jpeg") or f.lower().endswith(".bmp"):
                    names.append(f)
        except OSError:
            pass
        names.sort()
        self.names = names
        if names:
            max_len = max(len(f) for f in names)
            items = []
            for f in names:
                try:
                    size = os.stat(PHOTO_DIR + "/" + f)[6]
                    if size >= 1024:
                        size_txt = str(size // 1024) + "KB"
                    else:
                        size_txt = str(size) + "B"
                except OSError:
                    size_txt = "?"
                items.append(pad_right(f, max_len + 2) + pad_left(size_txt, 7))
        else:
            items = ["(no pictures found in " + PHOTO_DIR + ")"]
        # fully stop and restart the GUI object (same pattern the
        # full-screen preview uses reliably) -- a plain pixel clear
        # while the GUI was still running/polling wasn't reliably
        # sticking, so do a proper GUI restart instead
        try:
            self.g.stop()
        except Exception:
            pass
        hdmi.fill(hdmi.fb().colour(PAGE))
        g = pcgui.GUI()
        self.g = g
        g.start()
        self.list = None
        self.build_header(g)
        self.build_controls(g)
        self.footer(g)
        self.help_button(g, "photos", self.ROUTE_NAME)
        self.list = self.g.listbox(14, 100, 300, 330, items, 0, font=2, callback=self.on_pick)
        self.say(str(len(names)) + " picture(s) found in " + PHOTO_DIR)

    def on_refresh(self, b):
        self.refresh()

    def on_pick(self, c):
        i = c.value
        self.delete_armed = False
        if i < 0 or i >= len(self.names):
            self.picked = ""
            return
        self.picked = self.names[i]
        self.say("Picked " + self.picked + " -- press USE THIS PHOTO to attach it")

    def on_use(self, b):
        if not self.picked:
            self.say("Pick a picture from the list first")
            return
        self.set_current_photo(self.picked)
        self.build_header(self.g)
        self.say("Attached " + self.picked)

    def on_show(self, b):
        if not self.picked:
            self.say("Pick a picture from the list first")
            return
        path = PHOTO_DIR + "/" + self.picked
        try:
            self.g.stop()
        except Exception:
            pass
        err = render_picture_fullscreen(path, self.picked)
        self.refresh()
        self.say("Could not show picture: " + err if err else "Back from preview")

    def on_delete(self, b):
        if not self.picked:
            self.say("Pick a picture from the list first")
            return
        if not self.delete_armed:
            self.delete_armed = True
            self.say("Press DELETE again to permanently remove " + self.picked)
            return
        name = self.picked
        try:
            os.remove(PHOTO_DIR + "/" + name)
        except OSError as e:
            self.say("Delete failed: " + str(e))
            self.delete_armed = False
            return
        self.sync_delete(name)
        db.execute("UPDATE events SET photo='' WHERE photo=?", (name,))
        if self.get_current_photo() == name:
            self.set_current_photo("")
        self.picked = ""
        self.delete_armed = False
        self.refresh()
        self.say("Deleted " + name)

    def on_rename(self, b):
        if not self.picked:
            self.say("Pick a picture from the list first")
            return
        newname = self.rename_box.value.strip()
        if not newname:
            self.say("Type a new name first")
            return
        newname = newname.replace("/", "_")
        if "." not in newname:
            # keep the original extension if the user didn't type one
            if "." in self.picked:
                newname = newname + self.picked[self.picked.rindex("."):]
            else:
                newname = newname + ".jpg"
        old_path = PHOTO_DIR + "/" + self.picked
        new_path = PHOTO_DIR + "/" + newname
        try:
            os.rename(old_path, new_path)
        except OSError as e:
            self.say("Rename failed: " + str(e))
            return
        # keep anything already pointing at the old name pointing at
        # the file under its new name -- events can reference a photo
        # too, independent of the member/car/general context
        old_name = self.picked
        self.sync_rename(old_name, newname)
        db.execute("UPDATE events SET photo=? WHERE photo=?", (newname, old_name))
        self.picked = newname
        self.rename_box.value = ""
        self.refresh()
        self.say("Renamed " + old_name + " to " + newname)

    def on_wifi_upload(self, b):
        sta = network.WLAN(network.STA_IF)
        if not (sta.active() and sta.isconnected()):
            self.say("Connect to wifi first (Menu -> WIFI)")
            return
        if background_server is not None:
            self.say("Upload server running -- browse to http://" + sta.ifconfig()[0] + ":8080")
        else:
            if start_background_server():
                self.say("Upload server started -- browse to http://" + sta.ifconfig()[0] + ":8080")
            else:
                self.say("Upload server not running yet -- try again shortly")

    def on_send_to_board(self, b):
        if not self.picked:
            self.say("Pick a picture from the list first")
            return
        names = load_forward_ips()
        if not names:
            self.say("No boards saved yet -- add some on the WIFI page first")
            return
        path = PHOTO_DIR + "/" + self.picked
        try:
            size_kb = os.stat(path)[6] // 1024
        except OSError:
            size_kb = 0
        self.say("Sending " + self.picked + " (" + str(size_kb) + "KB) -- "
                  "screen will freeze until done, this is normal for photos")
        start = time.ticks_ms()
        sent = []
        failed = []
        for board_name in names:
            ip = resolve_board_ip(board_name)
            if not ip:
                failed.append(board_name + " (not seen on network)")
                continue
            if forward_upload(ip, path, self.picked):
                sent.append(board_name)
            else:
                failed.append(board_name)
        elapsed = time.ticks_diff(time.ticks_ms(), start) // 1000
        if failed:
            self.say("Sent to " + str(len(sent)) + " board(s) in " + str(elapsed) +
                      "s, FAILED: " + ", ".join(failed))
        else:
            self.say("Sent " + self.picked + " to " + str(len(sent)) + " board(s) in " + str(elapsed) + "s")

    def on_clear(self, b):
        self.set_current_photo("")
        self.build_header(self.g)
        self.picked = ""
        self.say("Photo cleared")

    def on_back(self, b):
        self.go(self.get_back_route())


class MemberPhotosPage(PhotosPage):
    ROUTE_NAME = "photos"

    def __init__(self, num):
        PhotosPage.__init__(self)
        self.num = num

    def get_label(self):
        r = get_member(self.num)
        who = r[1] if r else ""
        return "Member " + str(self.num) + "   " + (who or "")

    def get_current_photo(self):
        r = get_member(self.num)
        return (r[11] if r else "") or ""

    def set_current_photo(self, name):
        set_photo(self.num, name)

    def get_back_route(self):
        return "members"

    def sync_rename(self, old_name, new_name):
        db.execute("UPDATE members SET photo=? WHERE photo=?", (new_name, old_name))

    def sync_delete(self, name):
        db.execute("UPDATE members SET photo='' WHERE photo=?", (name,))


class CarPhotosPage(PhotosPage):
    ROUTE_NAME = "carphoto"

    def __init__(self, cid):
        PhotosPage.__init__(self)
        self.cid = cid

    def get_label(self):
        car = one("SELECT descr, rego FROM cars WHERE id=?", (self.cid,))
        descr = (car[0] if car else "") or ""
        rego = (car[1] if car else "") or ""
        extra = ("  " + rego) if rego else ""
        return "Car: " + descr + extra

    def get_current_photo(self):
        return get_car_photo(self.cid)

    def set_current_photo(self, name):
        set_car_photo(self.cid, name)

    def get_back_route(self):
        return "cars"

    def sync_rename(self, old_name, new_name):
        db.execute("UPDATE cars SET photo=? WHERE photo=?", (new_name, old_name))

    def sync_delete(self, name):
        db.execute("UPDATE cars SET photo='' WHERE photo=?", (name,))


class GeneralPhotosPage(PhotosPage):
    ROUTE_NAME = "genphotos"

    # reached straight from the main menu -- browse, upload, rename,
    # and preview pictures without attaching one to a member or car.
    def get_label(self):
        return "General browser -- open a member or car's PHOTO button to attach a picture"

    def get_current_photo(self):
        return ""

    def set_current_photo(self, name):
        pass

    def on_use(self, b):
        self.say("Nothing to attach to here -- open this from a member or car's PHOTO button instead")

    def get_back_route(self):
        return "menu"


class CalculatorPage(Page):
    # Basic four-function calculator, plus an optional scientific
    # mode (sin/cos/tan and inverses, log/ln, sqrt, powers, 1/x, pi,
    # e, and a DEG/RAD toggle). Same safety approach as before: the
    # expression is checked against a strict character whitelist
    # (digits, the arithmetic operators, and only the specific
    # letters needed to spell the function/constant names below)
    # before being handed to eval(), which itself only ever sees a
    # namespace containing those exact functions/constants -- nothing
    # else is reachable from it. Every character in the expression
    # comes from this page's own fixed set of buttons; there is no
    # free-text entry into this field at all.
    ALLOWED_CHARS = set("0123456789+-*/(). ") | set("acegilnopqrst")
    SCI_FUNCS = ("sin(", "cos(", "tan(", "asin(", "acos(", "atan(",
                 "log(", "ln(", "sqrt(")

    def __init__(self):
        Page.__init__(self)
        # build() (called before enter() by Page.show()) needs these
        # to already exist, since it branches on self.mode -- setting
        # them in enter() instead left the very first visit crashing
        # with an AttributeError before enter() ever ran
        self.mode = "std"
        self.angle_mode = "deg"
        self.expr = ""
        self.just_evaluated = False

    def build(self, g):
        g.caption(320, 6, "Calculator", fg=INK, bg=PAGE, font=3, just="CT")
        self.display = g.displaybox(20, 40, 600, 50, "0", fg=INK, bg=WHITE, font=3)
        self._icon_rects = {}  # symbol -> (x, y, w, h), filled in by _build_std/_build_sci
        if self.mode == "sci":
            self._build_sci(g)
        else:
            self._build_std(g)
        g.button(522, 410, 110, 32, "MENU", fg=WHITE, bg=RED, font=2, callback=self.on_back)
        self.footer(g)
        self.help_button(g, "calculator", "menu")
        self._draw_icons()

    def _icon_button(self, g, x, y, s, symbol, bg, callback):
        # a square button with no text label -- the symbol is instead
        # drawn as a small vector icon on top, after all widgets exist
        # (see _draw_icons()), same "draw last" pattern used by the 3D
        # viewer so it isn't clobbered by widget creation
        g.button(x, y, s, s, "", fg=WHITE, bg=bg, font=1, callback=callback)
        self._icon_rects[symbol] = (x, y, s, s)

    def _draw_icons(self):
        # draws the operator icons for whichever buttons were
        # registered in self._icon_rects during _build_std/_build_sci
        try:
            fb = hdmi.fb()
        except Exception as e:
            ulog("CalculatorPage icon draw: no framebuffer: " + str(e))
            return
        for symbol, (x, y, w, h) in self._icon_rects.items():
            try:
                _draw_calc_icon(fb, x + w // 2, y + h // 2, min(w, h), symbol, WHITE)
            except Exception as e:
                ulog("CalculatorPage icon draw failed for " + symbol + ": " + str(e))

    ICON_SYMBOLS = ("+", "-", "*", "/", "=", "<-")

    def _build_std(self, g):
        s, gap = 50, 8
        cols = 5
        grid_w = cols * s + (cols - 1) * gap
        x0 = 20 + (600 - grid_w) // 2
        y0 = 110
        grid = [
            ["7", "8", "9", "/", "C"],
            ["4", "5", "6", "*", "<-"],
            ["1", "2", "3", "-", "("],
            ["0", ".", "=", "+", ")"],
            ["", "", "SCI", "", ""],
        ]
        for r, row in enumerate(grid):
            for c, label in enumerate(row):
                if not label:
                    continue
                x = x0 + c * (s + gap)
                y = y0 + r * (s + gap)
                if label in self.ICON_SYMBOLS:
                    bg = RED if label == "=" else BTN
                    cb = self.on_backspace if label == "<-" else self._make_key_handler(label)
                    self._icon_button(g, x, y, s, label, bg, cb)
                elif label == "C":
                    g.button(x, y, s, s, "C", fg=WHITE, bg=RED, font=2, callback=self.on_clear)
                elif label == "SCI":
                    g.button(x, y, s, s, "SCI", fg=WHITE, bg=BTN, font=1, callback=self.on_toggle_mode)
                elif label in ("(", ")"):
                    g.button(x, y, s, s, label, fg=WHITE, bg=BTN, font=3, callback=self._make_key_handler(label))
                else:  # digits and '.'
                    g.button(x, y, s, s, label, fg=WHITE, bg=BTN, font=2, callback=self._make_key_handler(label))

    def _build_sci(self, g):
        s, gap = 40, 8
        cols = 6
        grid_w = cols * s + (cols - 1) * gap
        x0 = 20 + (600 - grid_w) // 2
        y0 = 110
        grid = [
            ["sin", "cos", "tan", "asin", "acos", "atan"],
            ["log", "ln", "sqrt", "x^2", "x^y", "1/x"],
            ["pi", "e", self._deg_rad_label(), "(", ")", "C"],
            ["7", "8", "9", "/", "<-", ""],
            ["4", "5", "6", "*", "0", "."],
            ["1", "2", "3", "-", "=", "STD"],
        ]
        for r, row in enumerate(grid):
            for c, label in enumerate(row):
                if not label:
                    continue
                x = x0 + c * (s + gap)
                y = y0 + r * (s + gap)
                if label in self.ICON_SYMBOLS:
                    bg = RED if label == "=" else BTN
                    self._icon_button(g, x, y, s, label, bg, self._sci_handler(label))
                else:
                    bg = RED if label == "C" else BTN
                    g.button(x, y, s, s, label, fg=WHITE, bg=bg, font=1,
                             callback=self._sci_handler(label))

    def _deg_rad_label(self):
        return "DEG" if self.angle_mode == "deg" else "RAD"

    def _sci_handler(self, label):
        if label == "C":
            return self.on_clear
        if label == "<-":
            return self.on_backspace
        if label == "=":
            return lambda b: self.on_equals()
        if label == "STD":
            return self.on_toggle_mode
        if label == self._deg_rad_label():
            return self.on_toggle_angle
        if label == "x^2":
            return self._make_key_handler("**2")
        if label == "x^y":
            return self._make_key_handler("**")
        if label == "1/x":
            return self.on_reciprocal
        if label in ("sin", "cos", "tan", "asin", "acos", "atan", "log", "ln", "sqrt"):
            return self._make_key_handler(label + "(")
        return self._make_key_handler(label)  # digits, operators, pi, e, ( )

    def enter(self):
        self.expr = ""
        self.just_evaluated = False
        self.display.value = "0"
        self.say("Tap digits and operators, = to evaluate")

    def _rebuild(self, message=None):
        # same "fully stop and restart the GUI object" pattern used
        # elsewhere in club.py -- needed here because switching
        # STD/SCI mode or DEG/RAD changes which buttons exist, not
        # just a label on one of them
        try:
            self.g.stop()
        except Exception:
            pass
        hdmi.fill(hdmi.fb().colour(PAGE))
        g = pcgui.GUI()
        self.g = g
        g.start()
        self.build(g)
        self.display.value = self.expr[-22:] if self.expr else "0"
        if message:
            self.say(message)

    def on_toggle_mode(self, b):
        self.mode = "sci" if self.mode == "std" else "std"
        self._rebuild("Scientific mode" if self.mode == "sci" else "Standard mode")

    def on_toggle_angle(self, b):
        self.angle_mode = "rad" if self.angle_mode == "deg" else "deg"
        self._rebuild("Angles now in " + self.angle_mode.upper())

    def on_reciprocal(self, b):
        if not self.expr:
            return
        self.expr = "1/(" + self.expr + ")"
        self.just_evaluated = False
        self.display.value = self.expr[-22:]

    def _make_key_handler(self, ch):
        def handler(b):
            self.on_key(ch)
        return handler

    def on_key(self, ch):
        if ch == "=":
            self.on_equals()
            return
        if self.just_evaluated:
            self.just_evaluated = False
            if ch[0] in "0123456789.(" or ch in self.SCI_FUNCS or ch in ("pi", "e"):
                self.expr = ""  # start fresh after a result
            # else (an operator): leave the previous result in place
            # so the new operator chains from it
        self.expr += ch
        self.display.value = self.expr[-22:] if self.expr else "0"

    def _eval_namespace(self):
        deg = self.angle_mode == "deg"

        def sin(x):
            return math.sin(math.radians(x)) if deg else math.sin(x)

        def cos(x):
            return math.cos(math.radians(x)) if deg else math.cos(x)

        def tan(x):
            return math.tan(math.radians(x)) if deg else math.tan(x)

        def asin(x):
            r = math.asin(x)
            return math.degrees(r) if deg else r

        def acos(x):
            r = math.acos(x)
            return math.degrees(r) if deg else r

        def atan(x):
            r = math.atan(x)
            return math.degrees(r) if deg else r

        return {
            "sin": sin, "cos": cos, "tan": tan,
            "asin": asin, "acos": acos, "atan": atan,
            "sqrt": math.sqrt, "log": math.log10, "ln": math.log,
            "pi": math.pi, "e": math.e,
        }

    def on_equals(self):
        if not self.expr:
            return
        if not all(c in self.ALLOWED_CHARS for c in self.expr):
            self.display.value = "Error"
            self.expr = ""
            self.just_evaluated = False
            return
        try:
            result = eval(self.expr, {"__builtins__": {}}, self._eval_namespace())
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            self.display.value = str(result)
            self.expr = str(result)
            self.just_evaluated = True
        except ZeroDivisionError:
            self.display.value = "Error: div by 0"
            self.expr = ""
            self.just_evaluated = False
        except Exception:
            self.display.value = "Error"
            self.expr = ""
            self.just_evaluated = False

    def on_clear(self, b):
        self.expr = ""
        self.just_evaluated = False
        self.display.value = "0"

    def on_backspace(self, b):
        self.just_evaluated = False
        self.expr = self.expr[:-1]
        self.display.value = self.expr if self.expr else "0"

    def on_back(self, b):
        self.go("menu")


class Model3DPage(Page):
    # See club.py's history: this is a from-scratch software 3D
    # pipeline (ported from the PicoMite MMBasic 3D graphics manual),
    # not a wrapper around real "3D CREATE"/"3D SHOW" commands, which
    # don't exist in this MicroPython environment.
    #
    # Three screens sharing one page:
    #  EDIT   -- build a model directly (vertex coordinates, face
    #            vertex-lists), with SAVE/LOAD (from a browsable list
    #            of saved models)/UNDO
    #  SKETCH -- a drawing canvas: click on it to place a point
    #            (snapped to a grid), or type exact X/Y for precision.
    #            Set a layer Z and thickness, EXTRUDE to generate a
    #            solid and drop it into the model automatically.
    #  VIEW   -- rotate/inspect what you built, wireframe or solid,
    #            with each face's CAD-style name (TOP/BOTTOM/FRONT/
    #            BACK/LEFT/RIGHT) shown for the current orientation
    #
    # MOUSE SUPPORT: g.on_touch(callback) is a confirmed, tested API
    # (verified live against a real USB mouse click -- see chat
    # history) that fires with integer (x, y) screen coordinates on
    # click/tap. on_move/on_down/on_up exist but are plain attributes
    # defaulting to None, not registration methods.
    #
    # RESOLUTION: this page previously switched to RGB1024 while
    # active. That switch caused a confirmed hard reset on real
    # hardware -- the same failure class as the photo-preview reset
    # earlier in this project's history -- so it's been removed. This
    # page now stays in the app's normal RGB640 the whole time.
    VIEWPLANE = 400
    SCALE = 1.5  # canvas pixels per model unit (mm) -- 612x190px canvas
    # gives ~408 x ~127mm of visible working area, enough for a
    # 95x100mm enclosure sketch with margin to spare

    def __init__(self):
        Page.__init__(self)
        # build() (called before enter() by Page.show()) branches on
        # self.page_mode, so it must exist before the first build()
        # call -- setting it only in enter() left the first visit
        # crashing with an AttributeError before enter() ever ran
        # (the same class of bug fixed in CalculatorPage)
        self.vertices = []
        self.faces = []            # list of (index_list, colour_name)
        self.page_mode = "edit"    # "edit", "sketch", or "view"
        self.render_mode = "wireframe"
        self.current_color_name = "WHITE"
        self.model_name = "mycar"
        self.model = None
        self.camera = Camera3D(self.VIEWPLANE)
        self.selected_vertex = -1
        self.selected_face = -1
        self.grid_size = 5.0
        self.history = []          # undo stack: (vertices_copy, faces_copy)
        self.sketch_points = []    # list of (x, y) -- the 2D outline being built
        self.sketch_z = 0.0        # layer height the sketch sits at
        self.sketch_thickness = 3.0
        self.canvas_x0, self.canvas_y0, self.canvas_w, self.canvas_h = 14, 56, 612, 190

    def build(self, g):
        if self.page_mode == "view":
            self._build_view(g)
        elif self.page_mode == "sketch":
            self._build_sketch(g)
        else:
            self._build_edit(g)

    def _build_edit(self, g):
        g.caption(320, 6, "3D Model Editor", fg=INK, bg=PAGE, font=3, just="CT")
        self.status_box = g.displaybox(14, 40, 612, 20, "Ready", fg=WHITE, bg=BTN, font=1)

        g.caption(14, 64, "Vertices (" + str(len(self.vertices)) + ")", fg=INK, bg=PAGE, font=1)
        vert_items = ["%d: (%.1f, %.1f, %.1f)" % (i, v[0], v[1], v[2]) for i, v in enumerate(self.vertices)]
        self.vertex_list = g.listbox(14, 80, 290, 92, vert_items if vert_items else ["(no vertices yet)"],
                                      0, font=1, callback=self.on_pick_vertex)

        g.caption(14, 178, "X", fg=INK, bg=PAGE, font=1)
        self.x_box = g.numberbox(30, 176, 56, 22, font=1)
        g.caption(96, 178, "Y", fg=INK, bg=PAGE, font=1)
        self.y_box = g.numberbox(112, 176, 56, 22, font=1)
        g.caption(178, 178, "Z", fg=INK, bg=PAGE, font=1)
        self.z_box = g.numberbox(194, 176, 56, 22, font=1)
        g.caption(260, 178, "Grid", fg=INK, bg=PAGE, font=1)
        self.grid_box = g.numberbox(292, 176, 56, 22, str(self.grid_size), font=1)
        g.button(14, 204, 140, 24, "ADD VERTEX", fg=WHITE, bg=BTN, font=1, callback=self.on_add_vertex)
        g.button(160, 204, 144, 24, "DEL SELECTED", fg=WHITE, bg=RED, font=1, callback=self.on_del_vertex)

        g.caption(328, 64, "Faces (" + str(len(self.faces)) + ")", fg=INK, bg=PAGE, font=1)
        face_items = ["%d: [%s] %s" % (i, ",".join(str(x) for x in idxs), cname)
                      for i, (idxs, cname) in enumerate(self.faces)]
        self.face_list = g.listbox(328, 80, 290, 92, face_items if face_items else ["(no faces yet)"],
                                    0, font=1, callback=self.on_pick_face)

        g.caption(328, 178, "Vertex indices, e.g. 0,1,2,3", fg=INK, bg=PAGE, font=1)
        self.face_idx_box = g.textbox(328, 194, 180, 22, font=1)
        g.button(514, 194, 104, 22, "COLOR: " + self.current_color_name, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_cycle_color)
        g.button(328, 220, 180, 24, "ADD FACE", fg=WHITE, bg=BTN, font=1, callback=self.on_add_face)
        g.button(514, 220, 104, 24, "DEL SELECTED", fg=WHITE, bg=RED, font=1, callback=self.on_del_face)

        g.caption(14, 254, "Name", fg=INK, bg=PAGE, font=1)
        self.name_box = g.textbox(56, 252, 130, 22, self.model_name, font=1)
        g.button(194, 250, 70, 26, "SAVE", fg=WHITE, bg=BTN, font=1, callback=self.on_save)
        g.button(268, 250, 70, 26, "LOAD", fg=WHITE, bg=BTN, font=1, callback=self.on_load)
        g.button(342, 250, 90, 26, "UNDO", fg=WHITE, bg=BTN, font=1, callback=self.on_undo)
        g.button(436, 250, 90, 26, "CLEAR ALL", fg=WHITE, bg=RED, font=1, callback=self.on_clear_all)

        g.button(14, 284, 160, 30, "VIEW / ROTATE", fg=WHITE, bg=BTN, font=1, callback=self.on_switch_view)
        g.button(178, 284, 130, 30, "2D SKETCH", fg=WHITE, bg=BTN, font=1, callback=self.on_switch_sketch)
        g.button(312, 284, 130, 30, "LOAD DEMO CAR", fg=WHITE, bg=BTN, font=1, callback=self.on_load_demo)

        g.caption(14, 322, "Saved models -- tap to load", fg=INK, bg=PAGE, font=1)
        saved = list_saved_models()
        self.saved_list = g.listbox(14, 338, 400, 60, saved if saved else ["(none saved yet)"],
                                     0, font=1, callback=self.on_pick_saved_model)

        g.button(522, 410, 110, 32, "MENU", fg=WHITE, bg=RED, font=2, callback=self.on_back)
        self.footer(g)
        self.help_button(g, "model3d", "menu")

    def _build_sketch(self, g):
        g.caption(320, 6, "2D Sketch -> Extrude", fg=INK, bg=PAGE, font=3, just="CT")
        self.status_box = g.displaybox(14, 36, 612, 20,
                                        "%d points placed -- click the canvas, or type X/Y" % len(self.sketch_points),
                                        fg=WHITE, bg=BTN, font=1)

        g.frame(self.canvas_x0 - 2, self.canvas_y0 - 2, self.canvas_w + 4, self.canvas_h + 4,
                "Canvas", fg=INK, font=1)

        g.caption(14, 250, "X", fg=INK, bg=PAGE, font=1)
        self.sx_box = g.numberbox(30, 248, 46, 22, font=1)
        g.caption(90, 250, "Y", fg=INK, bg=PAGE, font=1)
        self.sy_box = g.numberbox(106, 248, 46, 22, font=1)
        g.button(166, 246, 110, 26, "ADD TYPED", fg=WHITE, bg=BTN, font=1, callback=self.on_add_sketch_point)
        g.button(296, 246, 160, 26, "DEL LAST POINT", fg=WHITE, bg=RED, font=1, callback=self.on_del_sketch_point)

        g.caption(14, 278, "Grid", fg=INK, bg=PAGE, font=1)
        self.sgrid_box = g.numberbox(52, 276, 46, 22, str(self.grid_size), font=1)
        g.caption(112, 278, "Z", fg=INK, bg=PAGE, font=1)
        self.sz_box = g.numberbox(128, 276, 46, 22, str(self.sketch_z), font=1)
        g.caption(188, 278, "Thick", fg=INK, bg=PAGE, font=1)
        self.thick_box = g.numberbox(234, 276, 46, 22, str(self.sketch_thickness), font=1)

        g.button(14, 306, 150, 28, "EXTRUDE", fg=WHITE, bg=RED, font=2, callback=self.on_extrude)
        g.button(174, 306, 150, 26, "CLEAR SKETCH", fg=WHITE, bg=BTN, font=1, callback=self.on_clear_sketch)
        g.button(334, 306, 150, 26, "BACK TO EDIT", fg=WHITE, bg=BTN, font=1, callback=self.on_switch_edit)

        g.button(522, 410, 110, 32, "MENU", fg=WHITE, bg=RED, font=2, callback=self.on_back)
        self.footer(g)
        self.help_button(g, "model3d", "menu")

    def _build_view(self, g):
        g.caption(320, 6, "3D Model Viewer", fg=INK, bg=PAGE, font=3, just="CT")
        self.status_box = g.displaybox(14, 40, 612, 20, "Ready", fg=WHITE, bg=BTN, font=1)
        self.faces_box = g.displaybox(14, 62, 612, 18, "", fg=INK, bg=PAGE, font=1)

        g.button(20, 340, 145, 32, "ROTATE Y-", fg=WHITE, bg=BTN, font=1, callback=self.on_rot_y_minus)
        g.button(172, 340, 145, 32, "ROTATE Y+", fg=WHITE, bg=BTN, font=1, callback=self.on_rot_y_plus)
        g.button(324, 340, 145, 32, "ROTATE X-", fg=WHITE, bg=BTN, font=1, callback=self.on_rot_x_minus)
        g.button(476, 340, 145, 32, "ROTATE X+", fg=WHITE, bg=BTN, font=1, callback=self.on_rot_x_plus)

        g.button(20, 378, 220, 32, "TOGGLE WIREFRAME/SOLID", fg=WHITE, bg=BTN, font=1, callback=self.on_toggle_render)
        g.button(250, 378, 130, 32, "RESET", fg=WHITE, bg=BTN, font=1, callback=self.on_reset)
        g.button(390, 378, 120, 32, "EDIT", fg=WHITE, bg=BTN, font=1, callback=self.on_switch_edit)

        g.button(522, 410, 110, 32, "MENU", fg=WHITE, bg=RED, font=2, callback=self.on_back)
        self.footer(g)
        self.help_button(g, "model3d", "menu")

    def enter(self):
        self.say("Build a model: add vertices, then faces -- or try 2D SKETCH for a print-ready solid")
        self._redraw()

    def _redraw(self, message=None):
        # same "fully stop and restart the GUI object" pattern used
        # elsewhere in club.py -- any raw drawing (3D render, sketch
        # canvas) happens LAST, strictly after the widget rebuild, so
        # it can't be clobbered by anything the GUI restart does
        try:
            self.g.stop()
        except Exception:
            pass
        hdmi.fill(hdmi.fb().colour(PAGE))
        g = pcgui.GUI()
        self.g = g
        g.start()
        self.build(g)
        if self.page_mode == "view":
            self.status_box.value = "Mode: " + self.render_mode.upper()
            try:
                render_model(hdmi.fb(), self.model, self.camera, 0, 30, 220, 640, 480, mode=self.render_mode)
                self._show_face_names()
            except Exception as e:
                ulog("Model3DPage render error: " + type(e).__name__ + " " + str(e))
                self.status_box.value = "Render error: " + str(e)
        elif self.page_mode == "sketch":
            try:
                self.g.on_touch(self.on_canvas_touch)
            except Exception as e:
                ulog("Model3DPage: on_touch registration failed: " + str(e))
            try:
                self._draw_sketch_canvas()
            except Exception as e:
                ulog("Model3DPage: sketch canvas draw failed: " + str(e))
        if message:
            self.say(message)

    def _show_face_names(self):
        # names every currently-visible (not backface-culled) face
        # using its rotated normal, CAD style -- verified against all
        # six axis directions before shipping
        try:
            names = []
            for idx in range(len(self.model.faces)):
                if self.model.flags[idx] & 1:
                    continue
                nx, ny, nz = _quat_rotate_vector(self.model.rotation, self.model.normals[idx])
                facing = nz > 0
                if self.model.flags[idx] & 4:
                    facing = not facing
                if facing:
                    names.append(name_face_by_normal((nx, ny, nz)))
            text = "Visible faces: " + (", ".join(names) if names else "(none facing camera)")
            self.faces_box.value = text[:100]
        except Exception as e:
            ulog("Model3DPage face naming error: " + str(e))

    # --- 2D sketch canvas (mouse-driven) ------------------------------

    def _model_to_screen(self, mx, my):
        sx = self.canvas_x0 + mx * self.SCALE
        sy = self.canvas_y0 + self.canvas_h - my * self.SCALE
        return int(sx), int(sy)

    def _screen_to_model(self, sx, sy):
        mx = (sx - self.canvas_x0) / self.SCALE
        my = (self.canvas_y0 + self.canvas_h - sy) / self.SCALE
        return mx, my

    def _in_canvas(self, sx, sy):
        return (self.canvas_x0 <= sx <= self.canvas_x0 + self.canvas_w and
                self.canvas_y0 <= sy <= self.canvas_y0 + self.canvas_h)

    def _read_grid_value(self, box):
        try:
            v = float(box.value)
            self.grid_size = v if v > 0 else 0.0
        except (ValueError, TypeError):
            pass
        return self.grid_size

    def on_canvas_touch(self, x, y):
        # registered via g.on_touch() only while page_mode == "sketch"
        # (a fresh GUI object every redraw means this never lingers
        # into edit/view mode); ignores clicks outside the canvas
        # rectangle so button presses in this same mode aren't
        # mistaken for point placement
        if not self._in_canvas(x, y):
            return
        mx, my = self._screen_to_model(x, y)
        grid_size = self._read_grid_value(self.sgrid_box)
        if grid_size:
            mx, my = snap_to_grid(mx, grid_size), snap_to_grid(my, grid_size)
        self.sketch_points.append((mx, my))
        self._redraw("Placed point at (%.1f, %.1f)" % (mx, my))

    def _draw_sketch_canvas(self):
        try:
            fb = hdmi.fb()
        except Exception as e:
            ulog("sketch canvas: no framebuffer: " + str(e))
            return
        x0, y0, w, h = self.canvas_x0, self.canvas_y0, self.canvas_w, self.canvas_h
        grid_size = self.grid_size
        if grid_size:
            step_px = max(4, int(grid_size * self.SCALE))
            x = x0
            while x <= x0 + w:
                _fb_line(fb, x, y0, x, y0 + h, INK)
                x += step_px
            y = y0
            while y <= y0 + h:
                _fb_line(fb, x0, y, x0 + w, y, INK)
                y += step_px
        pts_screen = [self._model_to_screen(mx, my) for (mx, my) in self.sketch_points]
        for i in range(len(pts_screen) - 1):
            _fb_line(fb, pts_screen[i][0], pts_screen[i][1], pts_screen[i + 1][0], pts_screen[i + 1][1], WHITE)
        if len(pts_screen) >= 3:
            _fb_line(fb, pts_screen[-1][0], pts_screen[-1][1], pts_screen[0][0], pts_screen[0][1], WHITE)
        for (sx, sy) in pts_screen:
            for dx in range(-3, 4):
                _fb_pixel(fb, sx + dx, sy, WHITE)
            for dy in range(-3, 4):
                _fb_pixel(fb, sx, sy + dy, WHITE)

    def on_switch_sketch(self, b):
        self.page_mode = "sketch"
        self._redraw("Click the canvas to place a point, or type exact X/Y and press ADD TYPED")

    def on_add_sketch_point(self, b):
        try:
            x = float(self.sx_box.value)
            y = float(self.sy_box.value)
        except (ValueError, TypeError):
            self.say("X/Y must be numbers")
            return
        grid_size = self._read_grid_value(self.sgrid_box)
        if grid_size:
            x, y = snap_to_grid(x, grid_size), snap_to_grid(y, grid_size)
        self.sketch_points.append((x, y))
        self._redraw("Added point %d at (%.2f, %.2f)" % (len(self.sketch_points) - 1, x, y))

    def on_del_sketch_point(self, b):
        if not self.sketch_points:
            self.say("No points to remove")
            return
        self.sketch_points.pop()
        self._redraw("Removed last point")

    def on_clear_sketch(self, b):
        self.sketch_points = []
        self._redraw("Sketch cleared")

    def on_extrude(self, b):
        if len(self.sketch_points) < 3:
            self.say("Need at least 3 outline points to extrude")
            return
        try:
            z_base = float(self.sz_box.value)
            thickness = float(self.thick_box.value)
        except (ValueError, TypeError):
            self.say("Layer Z and Thickness must be numbers")
            return
        if thickness <= 0:
            self.say("Thickness must be greater than 0")
            return
        self.sketch_z = z_base
        self.sketch_thickness = thickness
        new_verts, new_faces_raw = extrude_polygon(self.sketch_points, z_base, thickness)
        self._push_history()
        offset = len(self.vertices)
        self.vertices = self.vertices + new_verts
        new_faces = [([i + offset for i in f], self.current_color_name) for f in new_faces_raw]
        self.faces = self.faces + new_faces
        self.sketch_points = []
        self.page_mode = "edit"
        self._redraw("Extruded a %d-point outline, %.2f thick -- added %d vertices, %d faces" %
                      (len(new_verts) // 2, thickness, len(new_verts), len(new_faces)))

    # --- vertex/face editing ------------------------------------------

    def _push_history(self):
        self.history.append((list(self.vertices), [(list(i), c) for i, c in self.faces]))
        if len(self.history) > 20:
            self.history.pop(0)

    def on_undo(self, b):
        if not self.history:
            self.say("Nothing to undo")
            return
        self.vertices, self.faces = self.history.pop()
        self.selected_vertex = -1
        self.selected_face = -1
        self._redraw("Undid last change")

    def on_pick_vertex(self, c):
        self.selected_vertex = c.value

    def on_pick_face(self, c):
        self.selected_face = c.value

    def on_add_vertex(self, b):
        try:
            x = float(self.x_box.value)
            y = float(self.y_box.value)
            z = float(self.z_box.value)
        except (ValueError, TypeError):
            self.say("X/Y/Z must be numbers")
            return
        self.grid_size = self._read_grid_value(self.grid_box)
        if self.grid_size:
            x, y, z = snap_to_grid(x, self.grid_size), snap_to_grid(y, self.grid_size), snap_to_grid(z, self.grid_size)
        self._push_history()
        self.vertices.append((x, y, z))
        self._redraw("Added vertex %d at (%.2f, %.2f, %.2f)" % (len(self.vertices) - 1, x, y, z))

    def on_del_vertex(self, b):
        if self.selected_vertex < 0 or self.selected_vertex >= len(self.vertices):
            self.say("Pick a vertex from the list first")
            return
        nv, nf, err = delete_vertex_safe(self.vertices, self.faces, self.selected_vertex)
        if err:
            self.say(err)
            return
        self._push_history()
        self.vertices, self.faces = nv, nf
        self.selected_vertex = -1
        self._redraw("Deleted vertex")

    def on_cycle_color(self, b):
        names = list(_MODEL_COLOUR_NAMES.keys())
        i = names.index(self.current_color_name) if self.current_color_name in names else 0
        self.current_color_name = names[(i + 1) % len(names)]
        self._redraw()

    def on_add_face(self, b):
        text = self.face_idx_box.value.strip()
        if not text:
            self.say("Type vertex indices first, e.g. 0,1,2,3")
            return
        try:
            idxs = [int(t) for t in text.split(",") if t.strip() != ""]
        except ValueError:
            self.say("Vertex indices must be whole numbers, comma-separated")
            return
        err = validate_face_indices(idxs, len(self.vertices))
        if err:
            self.say(err)
            return
        self._push_history()
        self.faces.append((idxs, self.current_color_name))
        self._redraw("Added face %d" % (len(self.faces) - 1))

    def on_del_face(self, b):
        if self.selected_face < 0 or self.selected_face >= len(self.faces):
            self.say("Pick a face from the list first")
            return
        self._push_history()
        del self.faces[self.selected_face]
        self.selected_face = -1
        self._redraw("Deleted face")

    def on_clear_all(self, b):
        self._push_history()
        self.vertices = []
        self.faces = []
        self.selected_vertex = -1
        self.selected_face = -1
        self._redraw("Cleared")

    def on_save(self, b):
        name = self.name_box.value.strip()
        if not name:
            self.say("Type a name first")
            return
        if not self.vertices:
            self.say("Nothing to save yet -- add some vertices/faces first")
            return
        try:
            path = save_model_file(name, self.vertices, self.faces)
            self.model_name = name
            self.say("Saved " + path)
        except OSError as e:
            self.say("Save failed: " + str(e))

    def on_load(self, b):
        name = self.name_box.value.strip()
        if not name:
            self.say("Type a name first")
            return
        self._load_named_model(name)

    def on_pick_saved_model(self, c):
        saved = list_saved_models()
        if not saved or c.value < 0 or c.value >= len(saved):
            return
        self._load_named_model(saved[c.value])

    def _load_named_model(self, name):
        try:
            vertices, faces = load_model_file(name)
        except OSError:
            self.say("No saved model called '" + name + "'")
            return
        except Exception as e:
            self.say("Load failed: " + str(e))
            return
        self._push_history()
        self.vertices, self.faces = vertices, faces
        self.model_name = name
        self.selected_vertex = -1
        self.selected_face = -1
        self._redraw("Loaded " + name + " (" + str(len(vertices)) + " vertices, " + str(len(faces)) + " faces)")

    def on_load_demo(self, b):
        demo = make_demo_car()
        reverse = {}
        for k, v in _MODEL_COLOUR_NAMES.items():
            reverse[v] = k
        self._push_history()
        self.vertices = list(demo.base_vertices)
        self.faces = [(list(f), reverse.get(demo.face_colours[i], "WHITE")) for i, f in enumerate(demo.faces)]
        self.model_name = "democar"
        self.selected_vertex = -1
        self.selected_face = -1
        self._redraw("Loaded the demo car -- edit it or press VIEW/ROTATE")

    # --- view / rotate -------------------------------------------------

    def on_switch_view(self, b):
        if not self.vertices or not self.faces:
            self.say("Add at least one face before viewing (or LOAD DEMO CAR)")
            return
        colours = [_MODEL_COLOUR_NAMES.get(cname, WHITE) for idxs, cname in self.faces]
        face_lists = [idxs for idxs, cname in self.faces]
        self.model = Model3D(self.vertices, face_lists, colours)
        self.page_mode = "view"
        self._redraw()

    def on_switch_edit(self, b):
        self.page_mode = "edit"
        self._redraw()

    def on_rot_y_minus(self, b):
        self.model.rotate((0, 1, 0), -math.radians(15))
        self._redraw()

    def on_rot_y_plus(self, b):
        self.model.rotate((0, 1, 0), math.radians(15))
        self._redraw()

    def on_rot_x_minus(self, b):
        self.model.rotate((1, 0, 0), -math.radians(15))
        self._redraw()

    def on_rot_x_plus(self, b):
        self.model.rotate((1, 0, 0), math.radians(15))
        self._redraw()

    def on_toggle_render(self, b):
        self.render_mode = "solid" if self.render_mode == "wireframe" else "wireframe"
        self._redraw()

    def on_reset(self, b):
        self.model.reset()
        self._redraw()

    def on_back(self, b):
        self.go("menu")


class SDImportPage(Page):
    # a navigable file browser -- start at /sd, click into folders,
    # click ".." to go up, pick ANY file anywhere on the card. Photos
    # (.jpg/.jpeg/.bmp) copy into PHOTO_DIR ready to attach to a
    # member/car; everything else copies into IMPORT_DIR as a general
    # holding folder.
    ROOT = "/sd"

    # extensions that are safe to open as plain text in the on-screen editor
    TEXT_EXTS = (".txt", ".csv", ".log", ".ini", ".md")
    # cap how big a file we'll pull into RAM to edit (bytes)
    MAX_EDIT_SIZE = 10000
    # fixed width for the name column in the file list -- using a
    # FIXED width (rather than sizing to the longest name in the
    # current folder) is what keeps the size column lined up and
    # actually on-screen; a dynamic width means one long filename
    # pushes every row's size off the right edge of the list box
    NAME_COL = 46

    def build(self, g):
        g.caption(320, 6, "Import from SD", fg=INK, bg=PAGE, font=3, just="CT")
        self.path_line = g.displaybox(14, 40, 600, 22, "", fg=INK, bg=PAGE, font=2)
        self.list = None
        self.refresh_btn = g.button(14, 410, 150, 32, "REFRESH", fg=WHITE, bg=BTN, font=2, callback=self.on_refresh)
        self.import_btn = g.button(180, 410, 150, 32, "IMPORT", fg=WHITE, bg=BTN, font=2, callback=self.on_import)
        self.edit_btn = g.button(340, 410, 170, 32, "VIEW / EDIT", fg=WHITE, bg=BTN, font=2, callback=self.on_edit_toggle)
        g.button(522, 410, 110, 32, "MENU", fg=WHITE, bg=RED, font=2, callback=self.on_back)
        self.footer(g)
        self.help_button(g, "sdimport", "sdimport")
        self.picked_path = ""
        self.current_dir = self.ROOT
        self.editing = False
        self.edit_path = None
        self.edit_box = None
        self.save_btn = None
        self.cancel_btn = None
        self.back_armed = False

    def enter(self):
        self.current_dir = self.ROOT
        self.refresh()

    def is_textish(self, path):
        low = path.lower()
        for ext in self.TEXT_EXTS:
            if low.endswith(ext):
                return True
        return False

    def _exists(self, path):
        try:
            os.stat(path)
            return True
        except OSError:
            return False

    def _is_dir(self, path):
        try:
            os.listdir(path)
            return True
        except Exception:
            return False

    def _size_text(self, path):
        # never let a size lookup crash the whole page load -- fall
        # back to "?" for anything unexpected the SD driver throws
        try:
            size = os.stat(path)[6]
        except Exception:
            return "?"
        try:
            if size >= 1024 * 1024:
                return str(size // (1024 * 1024)) + "MB"
            elif size >= 1024:
                return str(size // 1024) + "KB"
            else:
                return str(size) + "B"
        except Exception:
            return "?"

    def _format_row(self, label, size_txt):
        col = self.NAME_COL
        if len(label) > col:
            label = label[:col - 2] + ".."
        return pad_right(label, col + 2) + pad_left(size_txt, 7)

    def refresh(self):
        dirs = []
        files = []
        try:
            for f in os.listdir(self.current_dir):
                if f.lower() == "system volume information":
                    continue  # hidden Windows system folder, often has
                    # unusual filenames inside that break listing
                try:
                    full = self.current_dir.rstrip("/") + "/" + f
                    if self._is_dir(full):
                        dirs.append(f)
                    else:
                        files.append(f)
                except Exception:
                    continue  # skip any entry we can't safely handle
        except Exception as e:
            self.say("Could not read " + self.current_dir + ": " + str(e))
            dirs, files = [], []
        dirs.sort()
        files.sort()

        try:
            # rows: (label, size_txt, kind, name) -- size_txt is "" for ".." and folders
            rows = []
            if self.current_dir != self.ROOT:
                rows.append(("..  (up one level)", "", "up", ".."))
            for d in dirs:
                rows.append(("[DIR]  " + d, "", "dir", d))
            for f in files:
                full = self.current_dir.rstrip("/") + "/" + f
                rows.append((f, self._size_text(full), "file", f))

            if rows:
                items = [self._format_row(r[0], r[1]) for r in rows]
                entries = [(items[i], rows[i][2], rows[i][3]) for i in range(len(rows))]
            else:
                items = ["(nothing here)"]
                entries = []
        except Exception as ex:
            # if the size column itself blows up for any reason, fall
            # back to a plain unaligned list rather than losing the page
            ulog("sdimport size column error: " + type(ex).__name__ + " " + str(ex))
            entries = []
            if self.current_dir != self.ROOT:
                entries.append(("..  (up one level)", "up", ".."))
            for d in dirs:
                entries.append(("[DIR]  " + d, "dir", d))
            for f in files:
                entries.append((f, "file", f))
            items = [en[0] for en in entries] if entries else ["(nothing here)"]

        self.entries = entries

        if self.list is not None:
            self.g.remove(self.list)
        self.list = self.g.listbox(14, 66, 600, 334, items, 0, font=2, callback=self.on_pick)
        self.path_line.value = self.current_dir
        self.picked_path = ""
        self.say(str(len(dirs)) + " folder(s), " + str(len(files)) + " file(s) here")

    def on_refresh(self, b):
        self.refresh()

    def on_pick(self, c):
        i = c.value
        if i < 0 or i >= len(self.entries):
            self.picked_path = ""
            return
        text, kind, name = self.entries[i]
        if kind == "up":
            parent = self.current_dir.rstrip("/").rsplit("/", 1)[0]
            self.current_dir = parent if parent else "/"
            self.refresh()
        elif kind == "dir":
            self.current_dir = self.current_dir.rstrip("/") + "/" + name
            self.refresh()
        else:
            self.picked_path = self.current_dir.rstrip("/") + "/" + name
            if self.is_textish(self.picked_path):
                self.say("Picked " + self.picked_path + " -- IMPORT to copy, or VIEW/EDIT to open it here")
            else:
                self.say("Picked " + self.picked_path + " -- press IMPORT to copy it into " + PHOTO_DIR)

    def on_edit_toggle(self, b):
        if self.editing:
            self.on_cancel(b)
        else:
            self.open_editor()

    def open_editor(self):
        if not self.picked_path:
            self.say("Pick a file from the list first")
            return
        if not self.is_textish(self.picked_path):
            self.say("Only text files (" + ", ".join(self.TEXT_EXTS) + ") can be opened here")
            return
        try:
            size = os.stat(self.picked_path)[6]
        except Exception as e:
            self.say("Could not read " + self.picked_path + ": " + str(e))
            return
        if size > self.MAX_EDIT_SIZE:
            self.say("File too big to edit here (" + str(size) + " bytes, limit " + str(self.MAX_EDIT_SIZE) + ")")
            return
        gc.collect()  # free up RAM before pulling the whole file into memory
        try:
            f = open(self.picked_path)
            try:
                content = f.read()
            finally:
                f.close()
        except OSError as e:
            self.say("Could not open " + self.picked_path + ": " + str(e))
            return

        self.edit_path = self.picked_path
        if self.list is not None:
            self.g.remove(self.list)
            self.list = None
        self.g.remove(self.refresh_btn)
        self.g.remove(self.import_btn)
        self.g.remove(self.edit_btn)
        self.edit_box = self.g.textbox(14, 66, 600, 334, content, font=1)
        self.save_btn = self.g.button(14, 410, 150, 32, "SAVE", fg=WHITE, bg=BTN, font=2, callback=self.on_save)
        self.cancel_btn = self.g.button(180, 410, 150, 32, "CANCEL", fg=WHITE, bg=RED, font=2, callback=self.on_cancel)
        self.editing = True
        self.back_armed = False
        self.path_line.value = self.edit_path
        self.say("Editing " + self.edit_path + " -- SAVE to write changes back to the card")

    def close_editor(self):
        if self.edit_box is not None:
            self.g.remove(self.edit_box)
            self.edit_box = None
        if self.save_btn is not None:
            self.g.remove(self.save_btn)
            self.save_btn = None
        if self.cancel_btn is not None:
            self.g.remove(self.cancel_btn)
            self.cancel_btn = None
        self.editing = False
        self.edit_path = None
        self.back_armed = False
        self.refresh_btn = self.g.button(14, 410, 150, 32, "REFRESH", fg=WHITE, bg=BTN, font=2, callback=self.on_refresh)
        self.import_btn = self.g.button(180, 410, 150, 32, "IMPORT", fg=WHITE, bg=BTN, font=2, callback=self.on_import)
        self.edit_btn = self.g.button(340, 410, 170, 32, "VIEW / EDIT", fg=WHITE, bg=BTN, font=2, callback=self.on_edit_toggle)
        self.refresh()

    def on_save(self, b):
        if self.edit_path is None or self.edit_box is None:
            return
        try:
            f = open(self.edit_path, "w")
            try:
                f.write(self.edit_box.value)
            finally:
                f.close()
        except OSError as e:
            self.say("Save failed: " + str(e))
            return
        saved = self.edit_path
        self.close_editor()
        self.say("Saved " + saved)

    def on_cancel(self, b):
        self.close_editor()
        self.say("Closed without saving")

    def on_import(self, b):
        if not self.picked_path:
            self.say("Pick a file from the list first")
            return
        name = self.picked_path.split("/")[-1]
        low = name.lower()
        is_photo = low.endswith(".jpg") or low.endswith(".jpeg") or low.endswith(".bmp")
        target_dir = PHOTO_DIR if is_photo else IMPORT_DIR
        try:
            os.mkdir(target_dir)
        except OSError:
            pass
        dest = target_dir + "/" + name
        if self._exists(dest):
            if "." in name:
                stem = name[:name.rindex(".")]
                ext = name[name.rindex("."):]
            else:
                stem, ext = name, ""
            n = 1
            while self._exists(target_dir + "/" + stem + "_" + str(n) + ext):
                n += 1
            name = stem + "_" + str(n) + ext
            dest = target_dir + "/" + name
        try:
            src = open(self.picked_path, "rb")
            try:
                dst = open(dest, "wb")
                try:
                    while True:
                        chunk = src.read(2048)
                        if not chunk:
                            break
                        dst.write(chunk)
                finally:
                    dst.close()
            finally:
                src.close()
            self.say("Imported as " + name + " into " + target_dir)
        except OSError as e:
            self.say("Import failed: " + str(e))

    def on_back(self, b):
        if self.editing:
            if not self.back_armed:
                self.back_armed = True
                self.say("You have unsaved changes -- press BACK again to leave without saving, or SAVE first")
                return
            self.back_armed = False
        self.go("menu")


class ExportPage(Page):
    OPTIONS = [
        "All members",
        "All cars",
        "All events",
        "Today's changes (members saved today)",
    ]
    LABELS = ["members", "cars", "events", "members"]

    def build(self, g):
        g.caption(320, 6, "Export / Import", fg=INK, bg=PAGE, font=3, just="CT")
        g.caption(14, 40, "Writes CSV files to " + EXPORT_DIR + " on the SD card", fg=INK, bg=PAGE, font=2)
        g.caption(14, 58, "(this board has no USB storage support -- pull the SD card to collect files)", fg=INK, bg=PAGE, font=1)
        self.picked_idx = 0
        self.list = g.listbox(14, 84, 400, 200, self.OPTIONS, 0, font=2, callback=self.on_pick)
        g.caption(14, 292, "Send last export to IP", fg=INK, bg=PAGE, font=2)
        self.send_ip = g.textbox(14, 316, 260, 28, font=2)
        g.button(282, 316, 132, 28, "SEND TO BOARD", fg=WHITE, bg=BTN, font=1, callback=self.on_send)
        self.send_ip.value = load_forward_ip()
        self.result = g.displaybox(14, 364, 400, 44, "", fg=INK, bg=PAGE, font=1)
        g.button(14, 410, 150, 32, "EXPORT", fg=WHITE, bg=BTN, font=2, callback=self.on_export)
        g.button(170, 410, 150, 32, "EMAIL LAST", fg=WHITE, bg=BTN, font=2, callback=self.on_email)
        g.button(522, 410, 110, 32, "MENU", fg=WHITE, bg=RED, font=2, callback=self.on_menu)

        self.import_label = g.caption(430, 84, "Import " + self.LABELS[0] + " from CSV", fg=INK, bg=PAGE, font=2)
        self.csv_list = None
        self.refresh_csv_list(g)
        g.button(430, 296, 184, 28, "REFRESH LIST", fg=WHITE, bg=BTN, font=1, callback=self.on_refresh_csv)
        g.button(430, 328, 184, 28, "IMPORT", fg=WHITE, bg=BTN, font=1, callback=self.on_import)
        g.button(430, 360, 184, 28, "DELETE", fg=WHITE, bg=RED, font=1, callback=self.on_delete_csv)
        self.delete_armed = False

        self.footer(g)
        self.help_button(g, "export", "export")

    def refresh_csv_list(self, g):
        keyword = self.LABELS[self.picked_idx].rstrip("s")  # "members" -> "member", etc
        names = []
        for d in (EXPORT_DIR, "/sd"):
            try:
                for f in os.listdir(d):
                    fl = f.lower()
                    if fl.endswith(".csv") and keyword in fl:
                        names.append(d + "/" + f)
            except OSError:
                pass
        names.sort()
        self.csv_names = names
        items = names if names else ["(no " + self.LABELS[self.picked_idx] + " CSV files found)"]
        if self.csv_list is not None:
            g.remove(self.csv_list)
        self.csv_list = g.listbox(430, 108, 184, 184, items, 0, font=1, callback=self.on_pick_csv)
        self.picked_csv = names[0] if names else ""

    def on_refresh_csv(self, b):
        self.refresh_csv_list(self.g)
        self.say(str(len(self.csv_names)) + " " + self.LABELS[self.picked_idx] + " CSV file(s) found")

    def on_pick_csv(self, c):
        i = c.value
        if 0 <= i < len(self.csv_names):
            self.picked_csv = self.csv_names[i]
        self.import_armed = False
        self.delete_armed = False

    def on_import(self, b):
        if not getattr(self, "picked_csv", ""):
            self.say("Pick a CSV file first")
            return
        if not getattr(self, "import_armed", False):
            self.import_armed = True
            self.result.value = "Selected: " + self.picked_csv + " -- press IMPORT again to confirm"
            self.say("Press IMPORT again to confirm")
            return
        self.import_armed = False
        kind = self.LABELS[self.picked_idx]
        try:
            if kind == "cars":
                n = import_cars_csv(self.picked_csv)
            elif kind == "events":
                n = import_events_csv(self.picked_csv)
            else:
                n = import_members_csv(self.picked_csv)
            self.result.value = "Imported " + str(n) + " " + kind + " from " + self.picked_csv
            self.say("Import complete")
        except Exception as e:
            self.result.value = "Import failed: " + str(e)
            self.say("Import failed")

    def on_delete_csv(self, b):
        if not getattr(self, "picked_csv", ""):
            self.say("Pick a CSV file first")
            return
        if not self.delete_armed:
            self.delete_armed = True
            self.result.value = "Selected: " + self.picked_csv + " -- press DELETE again to remove"
            self.say("Press DELETE again to confirm")
            return
        self.delete_armed = False
        path = self.picked_csv
        try:
            os.remove(path)
            self.result.value = "Deleted " + path
            self.say("Deleted " + path)
        except OSError as e:
            self.result.value = "Delete failed: " + str(e)
            self.say("Delete failed")
        self.refresh_csv_list(self.g)

    def on_pick(self, c):
        self.picked_idx = c.value
        self.import_armed = False
        self.import_label.value = "Import " + self.LABELS[self.picked_idx] + " from CSV"
        self.refresh_csv_list(self.g)

    def ensure_dir(self):
        try:
            os.mkdir(EXPORT_DIR)
        except OSError:
            pass

    def on_export(self, b):
        self.ensure_dir()
        choice = self.OPTIONS[self.picked_idx]
        ts = stamp().replace(" ", "_").replace(":", "")
        self.last_export_path = ""
        try:
            if choice == "All members":
                data = rows("SELECT number,name,email,phone,status,financial,role,notes,visited,logbook,address,photo FROM members ORDER BY number")
                headers = ["number", "name", "email", "phone", "status", "financial", "role", "notes", "visited", "logbook", "address", "photo"]
                path = EXPORT_DIR + "/members_" + ts + ".csv"
                write_csv(path, headers, data)
                self.result.value = "Wrote " + str(len(data)) + " member(s) to " + path
            elif choice == "All cars":
                data = rows("SELECT id,member,descr,rego,logbook,photo FROM cars ORDER BY id")
                headers = ["id", "member", "descr", "rego", "logbook", "photo"]
                path = EXPORT_DIR + "/cars_" + ts + ".csv"
                write_csv(path, headers, data)
                self.result.value = "Wrote " + str(len(data)) + " car(s) to " + path
            elif choice == "All events":
                data = rows("SELECT key,name,date,time,place,notes,photo FROM events ORDER BY key")
                headers = ["key", "name", "date", "time", "place", "notes", "photo"]
                path = EXPORT_DIR + "/events_" + ts + ".csv"
                write_csv(path, headers, data)
                self.result.value = "Wrote " + str(len(data)) + " event(s) to " + path
            else:
                d = today()
                data = rows("SELECT number,name,email,phone,status,financial,role,notes,visited,logbook,address,photo FROM members WHERE visited LIKE ? ORDER BY number", (d + "%",))
                headers = ["number", "name", "email", "phone", "status", "financial", "role", "notes", "visited", "logbook", "address", "photo"]
                path = EXPORT_DIR + "/changes_" + ts + ".csv"
                write_csv(path, headers, data)
                self.result.value = "Wrote " + str(len(data)) + " changed member(s) to " + path
            self.last_export_path = path
            self.say("Export complete -- safe to remove the SD card when done")
        except Exception as e:
            self.result.value = "Export failed: " + str(e)
            self.say("Export failed")

    def on_send(self, b):
        if not getattr(self, "last_export_path", ""):
            self.say("Export something first, then send it")
            return
        ip = self.send_ip.value.strip()
        if not ip:
            self.say("Type the other board's IP first")
            return
        if ":" in ip:
            ip = ip.split(":")[0]  # accept "1.2.3.4" or "1.2.3.4:8080" -- port is always 8080
        filename = self.last_export_path.split("/")[-1]
        self.say("Sending " + filename + " to " + ip + " ...")
        ok = forward_upload(ip, self.last_export_path, filename)
        if ok:
            self.result.value = "Sent " + filename + " to " + ip
            self.say("Sent -- go to Export/Import on that board and REFRESH LIST")
        else:
            self.result.value = "Send to " + ip + " FAILED"
            self.say("Send failed -- is that board's WIFI UPLOAD running?")

    def on_email(self, b):
        if not getattr(self, "last_export_path", ""):
            self.say("Export something first, then email it")
            return
        self.say("Emailing " + self.last_export_path.split("/")[-1] + " ...")
        try:
            status = send_csv_email(self.last_export_path)
        except Exception as e:
            self.result.value = "Email failed: " + str(e)
            self.say("Email failed")
            return
        self.result.value = status
        self.say(status)

    def on_menu(self, b):
        self.go("menu")


class Members(Page):
    def build(self, g):
        self.num = 0
        self.found = []
        self.cars = []
        self.delete_armed = False
        self.boxes = {}
        g.caption(320, 4, "Members", fg=INK, bg=PAGE, font=3, just="CT")
        self.status_box = g.displaybox(14, 18, 612, 16, "Ready", fg=WHITE, bg=BTN, font=1)
        g.caption(14, 46, "Find", fg=INK, bg=PAGE, font=2)
        self.search = g.textbox(70, 40, 240, 28, "", font=2, callback=self.on_search)
        g.button(320, 40, 90, 28, "SEARCH", fg=WHITE, bg=BTN, font=2, callback=self.on_search_btn)
        g.button(416, 40, 90, 28, "NEW", fg=WHITE, bg=BTN, font=2, callback=self.on_new)
        g.button(512, 40, 120, 28, "CHECK IN", fg=WHITE, bg=BTN, font=2, callback=self.on_checkin)
        self.list = None
        g.button(14, 318, 108, 28, "DELETE", fg=WHITE, bg=RED, font=2, callback=self.on_delete)
        g.button(132, 318, 108, 28, "EMAIL", fg=WHITE, bg=BTN, font=2, callback=self.on_email)
        g.button(14, 350, 108, 28, "UPDATE", fg=WHITE, bg=BTN, font=2, callback=self.on_update_boards)
        g.button(132, 350, 108, 28, "REFRESH", fg=WHITE, bg=BTN, font=2, callback=self.on_refresh)
        g.button(14, 382, 226, 24, "SHOW ALL / RELOAD LIST", fg=WHITE, bg=BTN, font=1, callback=self.on_show_all)
        g.frame(262, 68, 370, 336, "", fg=INK, font=2)
        self.who = g.displaybox(270, 72, 354, 18, "nobody loaded", font=1)
        g.caption(270, 96, "No", fg=INK, bg=PAGE, font=1)
        self.mno = g.numberbox(300, 92, 60, 22, font=1)
        g.caption(270, 122, "Name", fg=INK, bg=PAGE, font=1)
        self.boxes["name"] = g.textbox(320, 118, 302, 22, font=1)
        g.caption(270, 148, "Email", fg=INK, bg=PAGE, font=1)
        self.boxes["email"] = g.textbox(320, 144, 302, 22, font=1)
        g.caption(270, 174, "Phone", fg=INK, bg=PAGE, font=1)
        self.boxes["phone"] = g.textbox(320, 170, 302, 22, font=1)
        g.caption(270, 200, "Logbook No", fg=INK, bg=PAGE, font=1)
        self.boxes["logbook"] = g.textbox(320, 196, 302, 22, font=1)
        g.caption(270, 226, "Address", fg=INK, bg=PAGE, font=1)
        self.boxes["address"] = g.textbox(320, 222, 302, 22, font=1)
        g.caption(270, 252, "Notes", fg=INK, bg=PAGE, font=1)
        self.boxes["notes"] = g.textbox(320, 248, 302, 60, font=1)
        g.caption(270, 320, "Status", fg=INK, bg=PAGE, font=1)
        self.status_sw = g.switch(330, 316, 130, 22, "Active|Not Active", value=1)
        g.caption(474, 320, "Paid", fg=INK, bg=PAGE, font=1)
        self.fin_sw = g.switch(510, 316, 70, 22, "Yes|No", value=1)
        self.seen = g.displaybox(270, 344, 354, 18, "", font=1)
        g.button(14, 410, 110, 32, "SAVE", fg=WHITE, bg=BTN, font=2, callback=self.on_save)
        g.button(132, 410, 110, 32, "CLEAR", fg=WHITE, bg=BTN, font=2, callback=self.on_clear)
        g.button(262, 410, 150, 32, "CARS", fg=WHITE, bg=BTN, font=2, callback=self.on_cars)
        g.button(412, 410, 100, 32, "PHOTO", fg=WHITE, bg=BTN, font=2, callback=self.on_photo)
        g.button(522, 410, 110, 32, "MENU", fg=WHITE, bg=RED, font=2, callback=self.on_menu)
        self.footer(g)
        self.help_button(g, "members", "members")

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
        self.list = self.g.listbox(14, 72, 230, 240, items, 0, font=2, callback=self.on_pick)

    def on_search(self, c):
        self.refresh(c.value)
        self.say(str(len(self.found)) + " found")

    def on_search_btn(self, b):
        self.refresh(self.search.value)
        self.say(str(len(self.found)) + " found")

    def on_refresh(self, b):
        self.refresh(self.search.value)
        self.say(str(len(self.found)) + " found -- list refreshed (" + str(member_count()) + " total on file)")

    def on_show_all(self, b):
        # Workaround for a click-stops-working bug after the list is
        # rebuilt in place (refresh()) -- reloading the whole page fresh
        # (like when you first open Members) reliably keeps the list
        # clickable. Until the root cause in pcgui is found, this is
        # the safe way back to seeing everyone / clicking again.
        self.go("members")

    def on_pick(self, c):
        i = c.value
        if i < 0 or i >= len(self.found):
            return
        self.load(self.found[i][0])

    def wipe(self):
        self.num = 0
        self.photo_name = ""
        self.delete_armed = False
        self.who.value = "nobody loaded"
        self.seen.value = ""
        for k in self.boxes:
            self.boxes[k].value = ""
        self.status_sw.value = 1
        self.fin_sw.value = 1
        self._current_role = ""

    def load(self, num):
        r = get_member(num)
        if r is None:
            self.wipe()
            self.say("No record for " + str(num))
            return
        self.num = num
        self.delete_armed = False
        self.mno.value = num
        self.who.value = "MEMBER " + str(num) + "   " + (r[1] or "")
        self.boxes["name"].value = r[1] or ""
        self.boxes["email"].value = r[2] or ""
        self.boxes["phone"].value = r[3] or ""
        self.boxes["notes"].value = r[7] or ""
        self.boxes["logbook"].value = r[9] or ""
        self.boxes["address"].value = r[10] or ""
        self.status_sw.value = 1 if (r[4] or STATUS[0]) == "Active" else 0
        self.fin_sw.value = 1 if (r[5] or "Yes") == "Yes" else 0
        self._current_role = r[6] or ""
        self.photo_name = r[11] or ""
        cars = member_cars(num)
        extra = "" if len(cars) < 2 else "   (" + str(len(cars)) + " cars)"
        photo_note = "   photo: " + self.photo_name if self.photo_name else "   no photo"
        self.seen.value = "Last saved: " + (r[8] or "never") + extra + photo_note
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
        status_str = "Active" if self.status_sw.value else "Not Active"
        fin_str = "Yes" if self.fin_sw.value else "No"
        role_str = getattr(self, "_current_role", "")
        put_member(n, self.boxes["name"].value, self.boxes["email"].value,
                   self.boxes["phone"].value, status_str,
                   fin_str, role_str,
                   self.boxes["notes"].value, self.boxes["logbook"].value,
                   self.boxes["address"].value)
        self.num = n
        self.who.value = "MEMBER " + str(n) + "   " + self.boxes["name"].value
        self.seen.value = "Last saved: " + stamp()
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

    def on_photo(self, b):
        n = self.number()
        if n <= 0 or get_member(n) is None:
            self.say("Load a member first -- save the record before adding a photo")
            return
        self.pick_member = n
        self.go("photos")

    def on_email(self, b):
        n = self.number()
        if n <= 0 or get_member(n) is None:
            self.say("Load a member first")
            return
        self.pick_member = n
        self.go("email_member")

    def on_update_boards(self, b):
        names = load_forward_ips()
        if not names:
            self.say("No boards saved yet -- add some on the WIFI page first")
            return
        n = self.number()
        if n <= 0 or get_member(n) is None:
            self.say("Load (and save) a member first")
            return
        self.say("Exporting member " + str(n) + "...")
        try:
            try:
                os.mkdir(EXPORT_DIR)
            except OSError:
                pass
            ts = stamp().replace(" ", "_").replace(":", "")
            data = rows("SELECT number,name,email,phone,status,financial,role,notes,visited,logbook,address,photo FROM members WHERE number=?", (n,))
            headers = ["number", "name", "email", "phone", "status", "financial", "role", "notes", "visited", "logbook", "address", "photo"]
            path = EXPORT_DIR + "/member_" + str(n) + "_" + ts + ".csv"
            write_csv(path, headers, data)
        except Exception as e:
            self.say("Export failed: " + str(e))
            return
        filename = path.split("/")[-1]
        sent = []
        failed = []
        for board_name in names:
            ip = resolve_board_ip(board_name)
            if not ip:
                failed.append(board_name + " (not seen on network)")
                continue
            self.say("Sending " + filename + " to " + board_name + " ...")
            if forward_upload(ip, path, filename):
                sent.append(board_name)
            else:
                failed.append(board_name)
        if failed:
            self.say("Sent to " + str(len(sent)) + " board(s), FAILED: " + ", ".join(failed))
        else:
            self.say("Sent member " + str(n) + " to " + str(len(sent)) + " board(s) -- REFRESH LIST there")

    def on_delete(self, b):
        n = self.number()
        if n <= 0 or get_member(n) is None:
            self.say("Load a member first")
            return
        if not self.delete_armed:
            self.delete_armed = True
            self.say("Press DELETE again to permanently remove member " + str(n))
            return
        delete_member(n)
        self.delete_armed = False
        self.wipe()
        self.refresh("")
        self.say("Deleted member " + str(n))

    def on_clear(self, b):
        self.wipe()
        self.say("Cleared")

    def on_menu(self, b):
        self.go("menu")


class EmailMemberPage(Page):
    def __init__(self, num):
        Page.__init__(self)
        self.num = num

    def build(self, g):
        r = get_member(self.num)
        self.member_email = (r[2] if r else "") or ""
        who = r[1] if r else ""
        g.caption(320, 6, "Email Member", fg=INK, bg=PAGE, font=3, just="CT")
        g.caption(14, 44, "Member " + str(self.num) + "   " + (who or ""), fg=INK, bg=PAGE, font=2)
        g.caption(14, 84, "To", fg=INK, bg=PAGE, font=2)
        self.to = g.textbox(70, 78, 400, 28, self.member_email, font=2)
        g.caption(14, 122, "Subject", fg=INK, bg=PAGE, font=2)
        self.subject = g.textbox(100, 116, 500, 28, "", font=2)
        g.caption(14, 160, "Message", fg=INK, bg=PAGE, font=2)
        # note: this GUI's textbox is single-line -- for a longer message,
        # edit the body_text default below and re-flash, or extend pcgui
        # with a real multi-line widget later.
        self.body = g.textbox(100, 154, 500, 28, "", font=2)
        self.result = g.displaybox(14, 210, 600, 80, "", fg=INK, bg=PAGE, font=2)
        g.button(14, 410, 150, 32, "SEND", fg=WHITE, bg=BTN, font=2, callback=self.on_send)
        g.button(522, 410, 110, 32, "BACK", fg=WHITE, bg=RED, font=2, callback=self.on_back)
        self.footer(g)
        self.help_button(g, "email_member", "email_member")

    def enter(self):
        if not self.member_email:
            self.say("This member has no email on file -- type one in To, or add it under Members")
        else:
            self.say("Ready to send")

    def on_send(self, b):
        to_addr = self.to.value.strip()
        if not to_addr or "@" not in to_addr:
            self.say("Enter a valid email address in To")
            return
        subject = self.subject.value.strip() or "Message from the club"
        body = self.body.value.strip() or "(no message)"
        self.say("Sending...")
        try:
            _send_plain_email(to_addr, subject, body)
        except Exception as e:
            self.result.value = "Send failed: " + str(e)
            self.say("Send failed")
            return
        self.result.value = "Sent to " + to_addr
        self.say("Sent")

    def on_back(self, b):
        self.go("members")


class Cars(Page):
    def __init__(self, num):
        Page.__init__(self)
        self.num = num
        self.cid = None

    def build(self, g):
        r = get_member(self.num)
        who = r[1] if r else ""
        g.caption(320, 6, "Cars", fg=INK, bg=PAGE, font=3, just="CT")
        self.status_box = g.displaybox(14, 24, 612, 16, "Ready", fg=WHITE, bg=BTN, font=1)
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
        g.button(324, 322, 90, 28, "PHOTO", fg=WHITE, bg=BTN, font=1, callback=self.on_photo)
        self.photo_preview = g.displaybox(420, 322, 212, 28, "no photo", fg=INK, bg=PAGE, font=1)
        g.button(14, 382, 150, 32, "BACK", fg=WHITE, bg=RED, font=2, callback=self.on_back)
        self.footer(g)
        self.help_button(g, "cars", "cars")
        self.car_photo = ""

    def enter(self):
        self.refresh()

    def update_preview(self):
        if self.car_photo:
            self.photo_preview.value = self.car_photo + " (view via PHOTO -> SHOW PIC)"
        else:
            self.photo_preview.value = "no photo"

    def refresh(self):
        self.cars = member_cars(self.num)
        items = []
        for cid, descr, rego, logbook, photo in self.cars:
            line = (descr or "?")
            if rego:
                line = line + "  " + rego
            if logbook:
                line = line + "  LB" + logbook
            if photo:
                line = line + "  [photo]"
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
        cid, descr, rego, logbook, photo = self.cars[i]
        self.cid = cid
        self.descr.value = descr or ""
        self.rego.value = rego or ""
        self.logbook.value = logbook or ""
        self.car_photo = photo or ""
        self.update_preview()
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
        self.car_photo = ""
        self.update_preview()
        self.refresh()
        self.say("Car added")

    def on_photo(self, b):
        if self.cid is None:
            self.say("Pick a car from the list first, or ADD one")
            return
        self.pick_car = self.cid
        self.go("carphoto")

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
        self.picking_photo = False
        self.delete_armed = False
        self.photo_names = []
        g.caption(320, 6, "Events", fg=INK, bg=PAGE, font=3, just="CT")
        self.status_box = g.displaybox(14, 24, 612, 14, "Ready", fg=WHITE, bg=BTN, font=1)
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
        self.photo_line = g.displaybox(330, 300, 290, 20, "", font=1)
        self.gps_line = g.displaybox(330, 322, 290, 20, "", font=1)
        g.button(8, 352, 80, 32, "NEW", fg=WHITE, bg=BTN, font=1, callback=self.on_new)
        g.button(96, 352, 80, 32, "SAVE", fg=WHITE, bg=BTN, font=1, callback=self.on_save)
        g.button(184, 352, 90, 32, "START", fg=WHITE, bg=BTN, font=1, callback=self.on_start)
        g.button(282, 352, 80, 32, "STOP", fg=WHITE, bg=BTN, font=1, callback=self.on_stop)
        self.import_btn = g.button(370, 352, 110, 32, "IMPORT", fg=WHITE, bg=BTN, font=1, callback=self.on_import_toggle)
        g.button(488, 352, 144, 32, "SHOW PHOTO", fg=WHITE, bg=BTN, font=1, callback=self.on_show_photo)
        g.button(8, 400, 150, 32, "WHO CAME", fg=WHITE, bg=BTN, font=1, callback=self.on_who)
        g.button(170, 400, 120, 32, "DELETE", fg=WHITE, bg=RED, font=1, callback=self.on_delete)
        g.button(300, 400, 130, 32, "GET GPS", fg=WHITE, bg=BTN, font=1, callback=self.on_get_gps)
        g.button(522, 400, 110, 32, "MENU", fg=WHITE, bg=RED, font=1, callback=self.on_menu)
        self.footer(g)
        self.help_button(g, "events", "events")

    def enter(self):
        self.picking_photo = False
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
        self.delete_armed = False
        self.name.value = e[1] or ""
        self.date.value = e[2] or ""
        self.tim.value = e[3] or ""
        self.place.value = e[4] or ""
        self.notes.value = e[5] or ""
        self.count.value = str(attend_count(key)) + " checked in"
        self.act.value = "RUNNING NOW" if setting("active") == key else ""
        photo = (e[6] if len(e) > 6 else "") or ""
        self.photo_line.value = "Photo: " + photo if photo else "Photo: (none)"
        lat = (e[7] if len(e) > 7 else "") or ""
        lon = (e[8] if len(e) > 8 else "") or ""
        if lat and lon:
            self.gps_line.value = "GPS: " + lat + ", " + lon
        else:
            self.gps_line.value = "GPS: (not set)"
        self.say("Loaded " + key)

    def load_by_key(self, key):
        for i in range(len(self.evs)):
            if self.evs[i][0] == key:
                self.load(i)
                return

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
        self.delete_armed = False
        self.refresh()
        self.name.value = ""
        self.date.value = today()
        self.tim.value = clock()
        self.place.value = ""
        self.notes.value = ""
        self.count.value = "0 checked in"
        self.act.value = ""
        self.photo_line.value = "Photo: (none)"
        self.gps_line.value = "GPS: (not set)"
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

    def on_get_gps(self, b):
        global last_gps_fix
        if self.key is None:
            self.say("Pick or create an event first")
            return
        self.say("Reading GPS ... please wait")
        fix, err = read_gps_fix()
        if fix is None:
            self.gps_line.value = "GPS: (not set)"
            self.say(err)
            return
        lat, lon = fix
        set_event_location(self.key, lat, lon)
        last_gps_fix = fix
        self.gps_line.value = "GPS: %.5f, %.5f" % (lat, lon)
        self.say("Got GPS fix for " + self.key)

    def on_delete(self, b):
        if self.key is None:
            self.say("Pick an event first")
            return
        if not self.delete_armed:
            self.delete_armed = True
            self.say("Press DELETE again to permanently remove event " + self.key)
            return
        deleted = self.key
        delete_event(deleted)
        self.key = None
        self.delete_armed = False
        self.refresh()
        if self.evs:
            self.load(0)
        else:
            self.name.value = ""
            self.date.value = ""
            self.tim.value = ""
            self.place.value = ""
            self.notes.value = ""
            self.count.value = ""
            self.act.value = ""
            self.photo_line.value = "Photo: (none)"
        self.say("Deleted event " + deleted)

    def on_import_toggle(self, b):
        self.picking_photo = not self.picking_photo
        self.g.remove(self.import_btn)
        if self.picking_photo:
            self.show_photo_list()
            label = "BACK TO LIST"
        else:
            self.refresh()
            if self.key:
                self.load_by_key(self.key)
            label = "IMPORT"
        self.import_btn = self.g.button(370, 352, 110, 32, label, fg=WHITE, bg=BTN, font=1, callback=self.on_import_toggle)

    def show_photo_list(self):
        names = []
        try:
            for f in os.listdir(PHOTO_DIR):
                lf = f.lower()
                if lf.endswith(".jpg") or lf.endswith(".jpeg") or lf.endswith(".bmp"):
                    names.append(f)
        except OSError:
            pass
        names.sort()
        self.photo_names = names
        items = names if names else ["(no pictures found)"]
        if self.list is not None:
            self.g.remove(self.list)
        self.list = self.g.listbox(20, 66, 276, 260, items, 0, font=2, callback=self.on_pick_photo)
        self.say(str(len(names)) + " picture(s) -- pick one to attach")

    def on_pick_photo(self, c):
        i = c.value
        if i < 0 or i >= len(self.photo_names):
            return
        if self.key is None:
            self.say("Pick or create an event first, then IMPORT")
            return
        name = self.photo_names[i]
        set_event_photo(self.key, name)
        self.photo_line.value = "Photo: " + name
        self.say("Attached " + name + " to " + self.key)
        self.picking_photo = False
        self.g.remove(self.import_btn)
        self.refresh()
        self.load_by_key(self.key)
        self.import_btn = self.g.button(370, 352, 110, 32, "IMPORT", fg=WHITE, bg=BTN, font=1, callback=self.on_import_toggle)

    def on_show_photo(self, b):
        if self.key is None:
            self.say("Pick an event first")
            return
        e = get_event(self.key)
        photo = (e[6] if e and len(e) > 6 else "") or ""
        if not photo:
            self.say("No photo attached to this event -- press IMPORT")
            return
        preview_picture(self, PHOTO_DIR + "/" + photo, photo)

    def on_menu(self, b):
        self.go("menu")


def main():
    open_db()
    screen(hdmi.RGB640)
    time.sleep(3)
    console("serial")
    where = "menu"
    who = 0
    picked_car = 0
    try:
        while where != "exit":
            try:
                if where == "menu":
                    where = Menu().show()
                elif where == "members":
                    p = Members()
                    where = p.show()
                    if where == "cars" or where == "photos" or where == "email_member":
                        who = p.pick_member
                elif where == "cars":
                    p = Cars(who)
                    where = p.show()
                    if where == "carphoto":
                        picked_car = p.pick_car
                elif where == "carphoto":
                    where = CarPhotosPage(picked_car).show()
                elif where == "photos":
                    where = MemberPhotosPage(who).show()
                elif where == "email_member":
                    where = EmailMemberPage(who).show()
                elif where == "events":
                    where = Events().show()
                elif where == "wifi":
                    where = WifiPage().show()
                elif where == "genphotos":
                    where = GeneralPhotosPage().show()
                elif where == "sdimport":
                    where = SDImportPage().show()
                elif where == "model3d":
                    where = Model3DPage().show()
                elif where == "calculator":
                    where = CalculatorPage().show()
                elif where == "export":
                    where = ExportPage().show()
                elif isinstance(where, str) and where.startswith("help|"):
                    _, topic, return_to = where.split("|", 2)
                    where = HelpPage(topic, return_to).show()
                else:
                    where = "menu"
            except Exception as e:
                msg = "PAGE ERROR at " + str(where) + " : " + type(e).__name__ + " " + str(e)
                print(msg)
                try:
                    ulog(msg)
                except Exception:
                    pass
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