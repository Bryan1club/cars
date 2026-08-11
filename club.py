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
UPLOAD_LOG_MAX_BYTES = 100000  # truncated (not deleted) once exceeded, so a chatty
                                # diagnostic caller can't quietly fill the SD card
EXPORT_DIR = "/sd/exports"
IMPORT_DIR = "/sd/imported"   # non-photo files copied in via Import from SD
MODELS_DIR = "/sd/models"     # saved 3D models from the Model Editor
ICONS_DIR = "/sd/icons"       # command button icons for the Model Editor
GAMES_DIR = "/sd/Games"       # .py games, browsed and run from the GAMES page

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
        try:
            if os.stat(UPLOAD_LOG)[6] > UPLOAD_LOG_MAX_BYTES:
                # truncate rather than remove -- keeps the path present
                # so anything else opening it for read doesn't hit a
                # missing-file error, just starts it fresh instead of
                # ever growing past the cap
                f = open(UPLOAD_LOG, "w")
                f.write("--- log truncated: exceeded %d bytes ---\n" % UPLOAD_LOG_MAX_BYTES)
                f.close()
        except OSError:
            pass  # file doesn't exist yet -- nothing to truncate
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


# command name -> icon file under ICONS_DIR (see assets/icons/*.svg in
# the repo -- rendered to 26x26 BMP) -- module level so both
# Model3DPage's own buttons and HelpPage's icon-illustrated entries for
# the "model3d" topic can use the same mapping
ICON_NAMES = {
    "NEW FILE": "new_file", "OPEN": "open", "SAVE AS": "save_as", "DELETE": "delete",
    "SELECT": "select", "LINE": "line", "CTR LINE": "centerline", "BOX": "box",
    "CIRCLE": "circle", "ARC": "arc", "GRID": "grid",
}

# topic -> (page title, [(button/field label, what it does), ...])
HELP_TEXT = {
    "menu": ("Main Menu", [
        ("MEMBERS", "Look up, add, edit, or email club members."),
        ("EVENTS", "Create events, start/stop check-in, see who came."),
        ("WIFI", "Connect to a network, name this board, manage saved networks and board-to-board forwarding."),
        ("PHOTOS", "Browse, upload, rename, or delete general photos."),
        ("IMPORT SD", "Copy pictures in from the SD card."),
        ("3D MODEL EDITOR", "Build a 3D model (boxes, lines, circles, arcs) and view it as a wireframe."),
        ("CALCULATOR", "A basic four-function calculator."),
        ("GAMES", "Browse and run .py games from /sd/Games."),
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
    "games": ("Games", [
        ("List", "Every .py file in /sd/Games -- tap to pick one."),
        ("REFRESH", "Rescans /sd/Games for new files."),
        ("RUN", "Runs the picked game. Returns here automatically when the game exits or crashes."),
        ("MENU", "Return to the main menu."),
    ]),
    "model3d": ("3D Model Editor", [
        ("NEW FILE", "Type X/Y/Z size in mm and CREATE a box -- clears everything else currently modelled."),
        ("OPEN", "Pick a saved model from the list and load it into the viewer."),
        ("SAVE AS", "Type a name and save everything currently modelled to the SD card."),
        ("DELETE", "If something is SELECTED (highlighted red), removes just that item (undoable). Otherwise, pick a saved model from the list and remove that file."),
        ("SELECT", "Click near an item's outline in the VIEW panel to select it (highlighted red) -- press DELETE to remove it, or pick another command to cancel."),
        ("LAYER button", "Shows the active layer -- new items go on it. Opens LAYERS: pick one then SET ACTIVE, TOGGLE SHOW (hide/unhide), or NEW LAYER."),
        ("LINE", "Choose CLICK ON GRID (tap start then end point in the VIEW panel, snaps to the grid if one's set) or TYPE VALUES (enter X/Y/Z numbers)."),
        ("CTR LINE", "Pick an axis (tap to cycle X/Y/Z) and a length -- adds a line through the origin along that axis. Snaps the length to the nearest GRID spacing if a grid is set."),
        ("BOX", "Choose CLICK ON GRID (tap one corner then the opposite corner in the VIEW panel) or TYPE VALUES (enter X/Y/Z numbers)."),
        ("CIRCLE", "Enter a centre point and radius; tap the plane button to cycle XY/XZ/YZ. Adds a selectable centre-mark crosshair through the middle too."),
        ("ARC", "Same as CIRCLE plus a start/end angle in degrees, swept counter-clockwise."),
        ("GRID", "Set a spacing, extent, plane (tap to cycle XY/XZ/YZ), and position along that plane's normal axis (e.g. Y for an XZ 'vertical' grid, to line it up with a wall). Replaces any existing grid. Once set, every typed X/Y/Z/radius/angle value in every dialog rounds to this spacing."),
        ("VIEW panel", "Rotatable view of everything modelled -- X is red, Y is green, Z is blue, all from the origin marked 0,0."),
        ("+ / - / RST", "Zoom in, zoom out, or reset the view back to its default position, zoom, and rotation."),
        ("U / D / L / R", "Pan the view up/down/left/right in fixed steps."),
        ("AZ - / AZ +", "Spin the viewpoint left/right around the model."),
        ("EL - / EL +", "Tilt the viewpoint down/up, from edge-on towards looking straight down."),
        ("WIRE", "Show or hide LINE/CIRCLE/ARC entries -- BOX, the grid, and the axis arrows stay visible either way."),
        ("GRID button", "Below the mouse position readout -- shows or hides the GRID dots on their own, independent of WIRE."),
        ("SNAP", "Master on/off for grid snapping -- when off, every typed value and click position is used exactly as entered even if a GRID is set."),
        ("EXTRUDE", "SELECT anything first, then give a height in mm: LINE becomes a wall, BOX grows taller, CIRCLE becomes a cylinder, ARC becomes a curved wall."),
        ("EDIT", "SELECT anything first -- opens its points/radius/angles pre-filled so you can fix a mistake without deleting and redrawing it. Also has its own DELETE THIS ITEM button."),
        ("UNDO / REDO", "Step back or forward through NEW FILE/OPEN/LINE/BOX/CIRCLE/ARC/GRID/EXTRUDE/EDIT changes."),
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
    # content rows run from just under the title/BACK row down to
    # ROW_BOTTOM, leaving room below that for PREV/NEXT (above the
    # scrolling footer ticker, which build() still adds via footer())
    # when a topic doesn't fit on one screen
    ROW_TOP = 34
    ROW_BOTTOM = 404
    ICON_SIZE = 26
    ICON_GAP = 8

    def __init__(self, topic, return_to):
        Page.__init__(self)
        self.topic = topic
        self.return_to = return_to
        self.page = 0

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

    def _row_height(self, label, desc):
        text_h = 18 + 14 * len(self.wrap(desc, self._desc_width(label)))
        icon_h = self.ICON_SIZE if label in ICON_NAMES else 0
        return max(text_h, icon_h) + 8

    def _desc_width(self, label):
        # narrower wrap for rows with an icon -- their text starts
        # further right, so fewer characters fit per line
        return 66 if label in ICON_NAMES else 76

    def _paginate(self, entries):
        pages = []
        current = []
        y = self.ROW_TOP
        for entry in entries:
            h = self._row_height(entry[0], entry[1])
            if current and y + h > self.ROW_BOTTOM:
                pages.append(current)
                current = []
                y = self.ROW_TOP
            current.append(entry)
            y += h
        pages.append(current)
        return pages

    def _redraw(self):
        try:
            self.g.stop()
        except Exception:
            pass
        g = pcgui.GUI()
        self.g = g
        g.start()
        self.build(g)

    def build(self, g):
        title, entries = HELP_TEXT.get(self.topic, ("Help", []))
        pages = self._paginate(entries)
        self.page = max(0, min(self.page, len(pages) - 1))
        page_entries = pages[self.page]

        header = "Help -- " + title
        if len(pages) > 1:
            header += "  (%d/%d)" % (self.page + 1, len(pages))
        g.caption(320, 6, header, fg=INK, bg=PAGE, font=3, just="CT")
        g.button(486, 4, 140, 28, "BACK", fg=WHITE, bg=RED, font=2, callback=self.on_back)

        y = self.ROW_TOP
        for label, desc in page_entries:
            icon_name = ICON_NAMES.get(label)
            text_x = 20
            if icon_name:
                path = ICONS_DIR + "/" + icon_name + ".bmp"
                try:
                    pcimage.draw_bmp(path, 20, y, dither=True)
                except Exception as e:
                    ulog("HelpPage: icon load failed for " + label + ": " + type(e).__name__ + " " + str(e))
                text_x = 20 + self.ICON_SIZE + self.ICON_GAP
            g.caption(text_x, y, label, fg=INK, bg=PAGE, font=2)
            ty = y + 18
            for line in self.wrap(desc, self._desc_width(label)):
                g.caption(text_x + 10, ty, line, fg=INK, bg=PAGE, font=1)
                ty += 14
            y += self._row_height(label, desc)

        if len(pages) > 1:
            # sits between the content and the scrolling footer ticker
            # footer() adds below, not the same lower spot the
            # standalone editor's HelpPage uses (it has no footer)
            if self.page > 0:
                g.button(20, 412, 90, 28, "PREV", fg=WHITE, bg=BTN, font=2, callback=self.on_prev_page)
            if self.page < len(pages) - 1:
                g.button(530, 412, 90, 28, "NEXT", fg=WHITE, bg=BTN, font=2, callback=self.on_next_page)

        self.footer(g)

    def enter(self):
        self.say("Help for " + HELP_TEXT.get(self.topic, ("this page", []))[0])

    def on_prev_page(self, b):
        self.page -= 1
        self._redraw()
        self.enter()

    def on_next_page(self, b):
        self.page += 1
        self._redraw()
        self.enter()

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
        g.button(172, 420, 296, 26, "GAMES", fg=WHITE, bg=BTN, font=1, callback=self.on_games)

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

    def on_games(self, b):
        self.go("games")

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


# --- 3D model file format: a plain text file under MODELS_DIR, one
# line per element -- plain numbers, not the earlier version's
# vertex/face-index format:
#   BOX x0 y0 z0 x1 y1 z1 layer        -- opposite corners
#   LINE x0 y0 z0 x1 y1 z1 layer       -- endpoints
#   CIRCLE cx cy cz radius plane layer -- plane is XY/XZ/YZ
#   ARC cx cy cz radius plane start end layer  -- start/end in degrees
#   GRID plane spacing extent_i extent_j [position]  -- at most one per
#     file, no layer (it's a reference, not something you select);
#     extent_i/extent_j are along the plane's two axes in AXIS_NAMES
#     order (e.g. X then Y for an XY grid), independent so a grid can
#     exactly cover a non-square face; position is where the grid sits
#     along its plane's normal axis (Z for XY, Y for XZ, X for YZ) --
#     omitted/missing means 0, for files saved before that field
#     existed. Files saved before extent_i/extent_j existed have just
#     one extent value, applied to both axes (a square grid).
#   LAYER name visible           -- visible is 1 or 0, one per layer
# v1 only had a single origin-anchored "BOX x y z"; v2 added multiple
# boxes/circles/arcs/grid; v3 added the trailing layer field. Each
# breaks the previous format on purpose -- still early enough that old
# .model files aren't worth carrying forward -- but BOX/LINE/CIRCLE/ARC
# still parse without their newest field(s), defaulting to "Layer1", so
# v2 files still open rather than silently losing content.
def serialize_model(boxes, lines, circles, arcs, grid, layers, layer_visible):
    out = []
    for (c0, c1, layer) in boxes:
        out.append("BOX %g %g %g %g %g %g %s" % (c0[0], c0[1], c0[2], c1[0], c1[1], c1[2], layer))
    for (p0, p1, layer) in lines:
        out.append("LINE %g %g %g %g %g %g %s" % (p0[0], p0[1], p0[2], p1[0], p1[1], p1[2], layer))
    for (c, r, plane, layer) in circles:
        out.append("CIRCLE %g %g %g %g %s %s" % (c[0], c[1], c[2], r, plane, layer))
    for (c, r, plane, a0, a1, layer) in arcs:
        out.append("ARC %g %g %g %g %s %g %g %s" % (c[0], c[1], c[2], r, plane, a0, a1, layer))
    if grid:
        plane, spacing, extent_i, extent_j, position = grid
        out.append("GRID %s %g %g %g %g" % (plane, spacing, extent_i, extent_j, position))
    for name in layers:
        out.append("LAYER %s %d" % (name, 1 if layer_visible.get(name, True) else 0))
    return "\n".join(out) + "\n"


def parse_model(text):
    boxes, lines, circles, arcs = [], [], [], []
    grid = None
    layers = []
    layer_visible = {}
    for line in text.split("\n"):
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "BOX" and len(parts) >= 8:
            boxes.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                          (float(parts[4]), float(parts[5]), float(parts[6])), parts[7]))
        elif parts[0] == "BOX" and len(parts) >= 7:
            boxes.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                          (float(parts[4]), float(parts[5]), float(parts[6])), "Layer1"))
        elif parts[0] == "BOX" and len(parts) >= 4:
            # v1 format ("BOX x y z") -- one corner was always the
            # origin. Kept readable so files saved before the
            # multi-box refactor still open instead of silently
            # losing their box.
            boxes.append(((0.0, 0.0, 0.0), (float(parts[1]), float(parts[2]), float(parts[3])), "Layer1"))
        elif parts[0] == "LINE" and len(parts) >= 8:
            lines.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                          (float(parts[4]), float(parts[5]), float(parts[6])), parts[7]))
        elif parts[0] == "LINE" and len(parts) >= 7:
            lines.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                          (float(parts[4]), float(parts[5]), float(parts[6])), "Layer1"))
        elif parts[0] == "CIRCLE" and len(parts) >= 7:
            circles.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                            float(parts[4]), parts[5], parts[6]))
        elif parts[0] == "CIRCLE" and len(parts) >= 6:
            circles.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                            float(parts[4]), parts[5], "Layer1"))
        elif parts[0] == "ARC" and len(parts) >= 9:
            arcs.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                         float(parts[4]), parts[5], float(parts[6]), float(parts[7]), parts[8]))
        elif parts[0] == "ARC" and len(parts) >= 8:
            arcs.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                         float(parts[4]), parts[5], float(parts[6]), float(parts[7]), "Layer1"))
        elif parts[0] == "GRID" and len(parts) >= 6:
            grid = (parts[1], float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5]))
        elif parts[0] == "GRID" and len(parts) >= 5:
            # pre-independent-extents save: one extent, applied to both axes
            grid = (parts[1], float(parts[2]), float(parts[3]), float(parts[3]), float(parts[4]))
        elif parts[0] == "GRID" and len(parts) >= 4:
            grid = (parts[1], float(parts[2]), float(parts[3]), float(parts[3]), 0.0)
        elif parts[0] == "LAYER" and len(parts) >= 3:
            layers.append(parts[1])
            layer_visible[parts[1]] = parts[2] != "0"
    if not layers:
        layers = ["Layer1"]
        layer_visible = {"Layer1": True}
    return boxes, lines, circles, arcs, grid, layers, layer_visible


def save_model_file(name, boxes, lines, circles, arcs, grid, layers, layer_visible):
    try:
        os.mkdir(MODELS_DIR)
    except OSError:
        pass  # already exists
    path = MODELS_DIR + "/" + name + ".model"
    f = open(path, "w")
    try:
        f.write(serialize_model(boxes, lines, circles, arcs, grid, layers, layer_visible))
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


def delete_model_file(name):
    try:
        os.remove(MODELS_DIR + "/" + name + ".model")
        return True
    except OSError:
        return False


# --- template wireframes: a reference cube (dots on its XY/XZ/YZ faces
# through the origin, plus optional centre lines) that's independent of
# whatever model is currently open -- unaffected by NEW FILE/OPEN, not
# saved into any .model file. Named and saved like models are, so you
# can build up a small library (e.g. a big reference cube and a small
# one for detail work) and pick up to two of them -- MAIN and LOCAL --
# to show at once. Each saved as one line:
#   size spacing scale centerlines show_xy show_xz show_yz
# size/spacing are the base values; scale multiplies both together, so
# the same saved template can be reused at any real-world size.
WIREFRAMES_DIR = "/sd/wireframes"
TEMPLATE_ACTIVE_FILE = "/sd/template_active.txt"


def serialize_wireframe(cfg):
    size, spacing, scale, centerlines, show_xy, show_xz, show_yz = cfg
    return "%g %g %g %d %d %d %d\n" % (
        size, spacing, scale, 1 if centerlines else 0,
        1 if show_xy else 0, 1 if show_xz else 0, 1 if show_yz else 0)


def parse_wireframe(text):
    parts = text.split()
    if len(parts) < 7:
        return None
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]), parts[3] != "0",
                parts[4] != "0", parts[5] != "0", parts[6] != "0")
    except ValueError:
        return None


def save_wireframe_file(name, cfg):
    try:
        os.mkdir(WIREFRAMES_DIR)
    except OSError:
        pass  # already exists
    path = WIREFRAMES_DIR + "/" + name + ".wf"
    f = open(path, "w")
    try:
        f.write(serialize_wireframe(cfg))
    finally:
        f.close()
    return path


def load_wireframe_file(name):
    path = WIREFRAMES_DIR + "/" + name + ".wf"
    f = open(path)
    try:
        text = f.read()
    finally:
        f.close()
    return parse_wireframe(text)


def list_saved_wireframes():
    try:
        names = [f[:-3] for f in os.listdir(WIREFRAMES_DIR) if f.endswith(".wf")]
        names.sort()
        return names
    except OSError:
        return []


def delete_wireframe_file(name):
    try:
        os.remove(WIREFRAMES_DIR + "/" + name + ".wf")
        return True
    except OSError:
        return False


def load_template_active():
    # returns (main_name, local_name), either/both None if unset
    try:
        f = open(TEMPLATE_ACTIVE_FILE)
        try:
            text = f.read()
        finally:
            f.close()
    except OSError:
        return None, None
    main_name = None
    local_name = None
    for line in text.split("\n"):
        parts = line.split(None, 1)
        if len(parts) == 2:
            if parts[0] == "MAIN":
                main_name = parts[1]
            elif parts[0] == "LOCAL":
                local_name = parts[1]
    return main_name, local_name


def save_template_active(main_name, local_name):
    lines = []
    if main_name:
        lines.append("MAIN " + main_name)
    if local_name:
        lines.append("LOCAL " + local_name)
    try:
        f = open(TEMPLATE_ACTIVE_FILE, "w")
        try:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        finally:
            f.close()
    except OSError as e:
        ulog("save_template_active failed: " + str(e))


# --- STL export: the model is a wireframe (edges only), but STL needs
# a solid triangle mesh -- BOX converts directly (it's already a solid
# box), LINE/CIRCLE/ARC don't have any volume of their own, so each
# gets "solidified" into a thin rectangular strut/tube of a chosen
# thickness (a circle/arc becomes a ring of straight struts, reusing
# the same chord approximation _draw_arc already uses on screen, so
# what you see is what gets printed). Adjacent struts around a circle/
# arc don't perfectly weld at their shared joints (each is its own
# independent oblique box) -- fine for FDM printing, where slicers
# routinely repair much worse, but worth knowing if a strict mesh
# checker complains. Written as binary STL (compact, simple format).
def _v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _v_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _v_scale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _v_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _v_length(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _v_normalize(a):
    length = _v_length(a)
    if length < 1e-9:
        return (0.0, 0.0, 1.0)
    return (a[0] / length, a[1] / length, a[2] / length)


def _perp_basis(d):
    # d must already be a unit vector -- returns (u, v) such that
    # u, v, d form a right-handed orthonormal basis (cross(u, v) == d),
    # the same convention as cross(X_AXIS, Y_AXIS) == Z_AXIS
    ref = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 1.0, 0.0)
    u = _v_normalize(_v_cross(ref, d))
    v = _v_cross(d, u)
    return u, v


def _box_corner_triangles(b0, b1, b2, b3, t0, t1, t2, t3):
    # 12 triangles (2 per face) for a box given its 4 bottom corners
    # (in order, forming a right-handed ring when viewed from "outside
    # the top") and the matching 4 top corners directly above them.
    # Winding is chosen so every face's normal points outward.
    tris = []

    def quad(p0, p1, p2, p3):
        tris.append((p0, p1, p2))
        tris.append((p0, p2, p3))
    quad(b3, b2, b1, b0)
    quad(t0, t1, t2, t3)
    quad(b0, b1, t1, t0)
    quad(b1, b2, t2, t1)
    quad(b2, b3, t3, t2)
    quad(b3, b0, t0, t3)
    return tris


def _box_triangles(c0, c1):
    x0, y0, z0 = c0
    x1, y1, z1 = c1
    b0, b1, b2, b3 = (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)
    t0, t1, t2, t3 = (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)
    return _box_corner_triangles(b0, b1, b2, b3, t0, t1, t2, t3)


def _strut_triangles(p0, p1, half_width):
    # a thin rectangular beam (square cross-section) running from p0
    # to p1 -- how LINE/CIRCLE/ARC edges get turned into something
    # with actual volume for printing (see the module comment above)
    d = _v_sub(p1, p0)
    if _v_length(d) < 1e-6:
        return []
    d = _v_normalize(d)
    u, v = _perp_basis(d)
    hu, hv = _v_scale(u, half_width), _v_scale(v, half_width)
    b0 = _v_sub(_v_sub(p0, hu), hv)
    b1 = _v_sub(_v_add(p0, hu), hv)
    b2 = _v_add(_v_add(p0, hu), hv)
    b3 = _v_add(_v_sub(p0, hu), hv)
    offset = _v_sub(p1, p0)
    t0, t1, t2, t3 = _v_add(b0, offset), _v_add(b1, offset), _v_add(b2, offset), _v_add(b3, offset)
    return _box_corner_triangles(b0, b1, b2, b3, t0, t1, t2, t3)


def _triangle_normal(p0, p1, p2):
    return _v_normalize(_v_cross(_v_sub(p1, p0), _v_sub(p2, p0)))


STL_DIR = "/sd/stl"


def write_stl_file(path, triangles):
    f = open(path, "wb")
    try:
        header = b"model3d_editor STL export"
        f.write(header + b"\x00" * (80 - len(header)))
        f.write(struct.pack("<I", len(triangles)))
        for (p0, p1, p2) in triangles:
            n = _triangle_normal(p0, p1, p2)
            f.write(struct.pack("<3f", n[0], n[1], n[2]))
            f.write(struct.pack("<3f", p0[0], p0[1], p0[2]))
            f.write(struct.pack("<3f", p1[0], p1[1], p1[2]))
            f.write(struct.pack("<3f", p2[0], p2[1], p2[2]))
            f.write(struct.pack("<H", 0))
    finally:
        f.close()


def save_stl_file(name, triangles):
    try:
        os.mkdir(STL_DIR)
    except OSError:
        pass  # already exists
    path = STL_DIR + "/" + name + ".stl"
    write_stl_file(path, triangles)
    return path


class Model3DPage(Page):
    # window chrome: an 8px grey border framing the whole 640x480
    # screen, drawn as concentric 1px g.frame() outlines (this app's
    # only bordered-box primitive) since there's no filled-rect call
    # available at the g level. INNER_* marks the usable area inside
    # the border for whatever gets built next.
    BORDER = 8
    GREY = 0x808080
    BLACK = 0x000000
    INNER_X0 = BORDER
    INNER_Y0 = BORDER
    INNER_X1 = 640 - BORDER
    INNER_Y1 = 480 - BORDER

    # left-hand commands panel geometry -- narrow now that the buttons
    # are icon-only (no text label to fit), which hands the reclaimed
    # width to the VIEW canvas below
    PANEL_X = 16
    PANEL_Y = 44
    PANEL_W = 56
    PANEL_H = 400

    # CMD_BTN_H has shrunk twice now (40->34->30, icons 32->26->22px)
    # to keep fitting more buttons in the same panel height as they've
    # been added.
    COMMANDS = ("NEW FILE", "OPEN", "SAVE AS", "DELETE", "SELECT", "LINE", "CTR LINE",
                "BOX", "CIRCLE", "ARC", "GRID", "TEMPLATE")
    CMD_BTN_H = 26  # shrunk again (30->26, icons 22->18px) to fit SELECT as an 11th button
    CMD_BTN_GAP = 5

    # centred modal dialog box used by NEW FILE / SAVE AS / DELETE --
    # width/x are shared, height/y vary per dialog since NEW FILE needs
    # three input rows and the others don't
    DLG_W = 320
    DLG_X = (640 - DLG_W) // 2

    # wireframe viewport -- the empty area right of the commands panel,
    # below the status readout and above the MENU button
    CANVAS_X0 = PANEL_X + PANEL_W + 20
    CANVAS_Y0 = 76
    CANVAS_X1 = INNER_X1 - 8
    CANVAS_Y1 = 396
    CANVAS_W = CANVAS_X1 - CANVAS_X0
    CANVAS_H = CANVAS_Y1 - CANVAS_Y0
    CANVAS_CX = CANVAS_X0 + CANVAS_W // 2
    CANVAS_CY = CANVAS_Y0 + CANVAS_H // 2

    # zoom/reset buttons, top-right corner of the VIEW canvas
    ZOOM_BTN_Y = CANVAS_Y0 + 4
    ZOOM_BTN_W = 30
    ZOOM_BTN_H = 24
    RESET_BTN_W = 44
    RESET_VIEW_X = CANVAS_X1 - 4 - RESET_BTN_W
    ZOOM_IN_X = RESET_VIEW_X - 4 - ZOOM_BTN_W
    ZOOM_OUT_X = ZOOM_IN_X - 4 - ZOOM_BTN_W
    ZOOM_STEP = 1.2
    MIN_ZOOM = 0.2
    MAX_ZOOM = 20.0  # raised from 5.0 -- 5x wasn't enough to work on a small part of a larger model

    # undo/redo, directly below the zoom row -- edit controls, not
    # drawing tools, so (like zoom) no CONFIRM popup for these
    UNDO_REDO_Y = ZOOM_BTN_Y + ZOOM_BTN_H + 4
    UNDO_REDO_W = 55
    UNDO_REDO_H = 24
    UNDO_MAX = 20  # capped so this doesn't grow without bound on an embedded board

    # hard cap on GRID dot count -- a 1mm spacing over the default
    # 100mm extent is 40,401 points (161,604 _fb_pixel calls in one
    # synchronous loop), which is what actually caused the "red
    # plane"/frozen-looking screen: not a rendering bug, a board
    # hang/reset from far too much blocking pixel-pushing at once
    GRID_MAX_DOTS = 500
    REDO_X = CANVAS_X1 - 4 - UNDO_REDO_W
    UNDO_X = REDO_X - 4 - UNDO_REDO_W

    # LAYERS button, directly below the undo/redo row, spanning the
    # same combined width
    LAYERS_BTN_Y = UNDO_REDO_Y + UNDO_REDO_H + 4
    LAYERS_BTN_X = UNDO_X
    LAYERS_BTN_W = (REDO_X + UNDO_REDO_W) - UNDO_X
    LAYERS_BTN_H = 24

    # pan nudge buttons -- a guaranteed-reliable fallback for the
    # sliders (real button clicks, same proven mechanism as everything
    # else in this app) stacked in the narrow gap between the commands
    # panel and the canvas, since that's the one strip with enough
    # free room for four of them without touching either slider
    PAN_NUDGE = 20
    DPAD_W = 18
    DPAD_H = 18
    DPAD_GAP = 4
    DPAD_X = CANVAS_X0 - DPAD_W - 1
    DPAD_Y0 = CANVAS_CY - (4 * DPAD_H + 3 * DPAD_GAP) // 2

    # two on_touch calls inside the VIEW canvas within this many ms of
    # each other count as one drag -- see the caveat on on_touch
    DRAG_TIMEOUT_MS = 500

    # rotate/wireframe row, directly under the VIEW canvas -- azimuth
    # (spin) and elevation (tilt) step buttons plus the wireframe
    # show/hide toggle, all left-aligned under the canvas so they never
    # reach as far right as MENU
    ROT_BTN_Y = CANVAS_Y1 + 6
    ROT_BTN_H = 26
    ROT_STEP_BTN_W = 56
    ROT_GAP = 6
    AZ_MINUS_X = CANVAS_X0
    AZ_PLUS_X = AZ_MINUS_X + ROT_STEP_BTN_W + ROT_GAP
    EL_MINUS_X = AZ_PLUS_X + ROT_STEP_BTN_W + ROT_GAP
    EL_PLUS_X = EL_MINUS_X + ROT_STEP_BTN_W + ROT_GAP
    WIRE_BTN_X = EL_PLUS_X + ROT_STEP_BTN_W + ROT_GAP + 10
    WIRE_BTN_W = 130

    # mouse position readout -- narrowed from its original 260 to make
    # room for GRID/EXTRUDE/SNAP/EDIT sharing the rest of this row
    MOUSE_BOX_W = 220

    # GRID show/hide toggle, SNAP master on/off, EXTRUDE, and EDIT all
    # share this row beside the mouse position readout, since the row
    # under the canvas is already full
    GRID_BTN_Y = PANEL_Y + PANEL_H + 4
    GRID_BTN_H = 20
    GRID_BTN_X = PANEL_X + MOUSE_BOX_W + 14
    GRID_BTN_W = 90
    EXTRUDE_BTN_X = GRID_BTN_X + GRID_BTN_W + 6
    EXTRUDE_BTN_W = 100
    SNAP_BTN_X = EXTRUDE_BTN_X + EXTRUDE_BTN_W + 6
    SNAP_BTN_W = 90
    EDIT_BTN_X = SNAP_BTN_X + SNAP_BTN_W + 6
    EDIT_BTN_W = 60

    # orbit-camera projection: an azimuth (spin around the vertical Z
    # axis) and an elevation (tilt between edge-on and looking straight
    # down) drive a plain rotation, then dropped straight to screen X/Y
    # -- orthographic, no perspective, no depth foreshortening, still
    # no quaternion/camera machinery. Z always renders straight up on
    # screen regardless of azimuth. The defaults below (45/30) reproduce
    # the project's original fixed isometric look -- X down-right,
    # Y down-left, Z up -- as just one point in the now-rotatable range.
    AZIMUTH_DEFAULT = 45.0
    ELEVATION_DEFAULT = 30.0
    AZIMUTH_STEP = 15.0
    ELEVATION_STEP = 10.0
    ELEVATION_MIN = -80.0
    ELEVATION_MAX = 80.0

    # world-space unit basis vectors spanning each GRID/click plane,
    # used to turn a screen click back into a 3D point on that plane
    # (see _screen_to_plane_point) -- generic across any azimuth/
    # elevation rather than a per-plane formula tied to one fixed view
    PLANE_BASIS = {"XY": ((1, 0, 0), (0, 1, 0)),
                   "XZ": ((1, 0, 0), (0, 0, 1)),
                   "YZ": ((0, 1, 0), (0, 0, 1))}

    # (0,0,0) is pinned to a fixed spot in the lower-right area of the
    # canvas rather than auto-centring the whole model -- as fractions
    # of the canvas, not a fixed margin from the corner, since a small
    # margin from the actual corner left almost no room on the
    # down-right side for a model that (with only positive X/Y/Z
    # modelled so far) always grows down and to both sides from here
    ORIGIN_X = CANVAS_X0 + CANVAS_W * 0.62
    ORIGIN_Y = CANVAS_Y0 + CANVAS_H * 0.75

    # axis gizmo -- direction + a perpendicular (for the arrowhead
    # wings) + colour per axis, always drawn from the origin so the
    # X/Y/Z planes stay readable regardless of what's been modelled.
    # Each arrow starts past wherever the model itself already reaches
    # along that axis (see _axis_extent) instead of at literal (0,0,0),
    # so it doesn't trace back over -- and cancel out -- a wireframe
    # edge running the same direction.
    AXIS_DIRS = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}
    AXIS_PERP = {"X": (0, 1, 0), "Y": (1, 0, 0), "Z": (1, 0, 0)}
    AXIS_COLORS = {"X": RED, "Y": 0x00CC00, "Z": 0x3399FF}

    # SELECT -- click near an element's projected outline to select it.
    # RED, not a raw hex literal like the original yellow (0xFFFF00) --
    # confirmed on real hardware that a "selected" item hit-tested fine
    # (status bar showed "SELECTED: ...") but rendered as nothing at
    # all, which a raw untested colour value silently failing in
    # _fb_line/_fb_pixel's own try/except would explain. RED is
    # imported from pcgfx (like WHITE) rather than being a raw literal,
    # and is already proven to draw via this exact framebuffer path
    # (the dashed active-command frame, the LINE start-point marker).
    SELECT_COLOR = RED
    CIRCLE_PREVIEW_COLOR = 0xFFFF00  # yellow -- distinct from SELECT_COLOR/grid grey/geometry white
    SELECT_THRESHOLD = 15    # px -- closest hit within this radius wins

    def __init__(self):
        Page.__init__(self)
        # build() runs before enter() (Page.show()), so anything build()
        # reads must exist before the first build() call -- same
        # AttributeError trap CalculatorPage and the old Model3DPage
        # both had to work around
        self.dialog = None        # None, "newfile", "open", "saveas", "delete", "line",
                                   # "box", "circle", or "arc"
        self.model_name = "mycar"
        self.stl_strut_thickness = 4.0  # mm -- default cross-section for solidified LINE/CIRCLE/ARC edges
        self.boxes = []             # list of ((x0,y0,z0), (x1,y1,z1)) opposite corners
        self.lines = []             # list of ((x0,y0,z0), (x1,y1,z1)) segments
        self.circles = []           # list of ((cx,cy,cz), radius, plane)
        self.arcs = []               # list of ((cx,cy,cz), radius, plane, start_deg, end_deg)

        self.line_start_point = None
        self.line_stage = "start"  # "start" or "end", within the LINE dialog
        self.box_start_point = None
        self.box_stage = "start"   # "start" or "end", within the BOX dialog
        self.circle_plane = "XY"   # cycles XY -> XZ -> YZ, within the CIRCLE dialog
        self._circle_radius_pending = None  # typed radius, preserved across a same-dialog redraw
        self._circle_pick_radius = 20.0     # confirmed radius, used once CIRCLE switches to click-to-place
        self._axis_label_widgets = []  # g.caption() widgets from the last _draw_axes call -- removed
                                        # before creating new ones so repeated lightweight _draw_scene()
                                        # calls (e.g. live mouse polling) don't pile up stale duplicates
        self.arc_plane = "XY"      # same, within the ARC dialog
        self.grid_plane = "XY"     # same, within the GRID dialog
        self.grid = None          # (plane, spacing, extent_i, extent_j, position) or None -- one
                                   # grid at a time, a fresh GRID replaces whatever grid was there
        self.snap_enabled = True  # master switch -- grid snapping only actually applies
                                   # when this is True AND self.grid is set
        self.centerline_axis = "X"  # cycles X -> Y -> Z, within the CTR LINE dialog

        # layers -- every box/line/circle/arc is tagged with the name
        # of whichever layer was "active" (current_layer) when it was
        # created. Hidden layers are skipped entirely by drawing, the
        # auto-fit scale, and SELECT's hit-testing.
        self.layers = ["Layer1"]
        self.current_layer = "Layer1"
        self.layer_visible = {"Layer1": True}
        self._dialog_selected_layer = None
        self._layers_dialog_message = ""  # feedback shown inside the LAYERS dialog, e.g. why a delete was blocked

        self._dialog_file_names = []     # filled in by _build_file_list_dialog
        self._dialog_selected_name = None  # read by on_confirm_open / on_confirm_delete

        # view pan/zoom -- pan is a screen-pixel offset added on top of
        # the fixed ORIGIN_X/ORIGIN_Y anchor, zoom multiplies the
        # auto-fit scale. Dragging is reconstructed from on_touch
        # (confirmed working) rather than on_move (confirmed NOT
        # working) -- see on_touch for the caveat about what that means
        # in practice.
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 1.0
        self.azimuth_deg = self.AZIMUTH_DEFAULT
        self.elevation_deg = self.ELEVATION_DEFAULT
        self._update_rotation_trig()
        self.wireframe_visible = True  # hides boxes/lines/circles/arcs when off; grid/axes stay
        self.grid_visible = True       # independent of wireframe_visible -- hides just the grid dots
        self._last_touch = None
        self._last_touch_time = 0
        self._last_scale = 1.0            # set for real by _draw_scene each redraw --
        self._last_origin = (0.0, 0.0)    # used by on_touch to report a model-space position

        self.box_pick_start = None  # BOX's "CLICK ON GRID" mode -- first corner, or None

        # diagnostic only -- counts every on_touch call regardless of
        # dialog state, logged via ulog() so a hardware test can tell
        # "on_touch never fired" apart from "on_touch fired but the
        # pick logic did nothing"
        self.touch_count = 0

        self.active_command = None  # last command clicked, gets the red dashed frame
        self.selected = None  # (kind, index) e.g. ("box", 0), or None -- highlighted red

        self.undo_stack = []  # snapshots of (boxes, lines, circles, arcs, grid)
        self.redo_stack = []  # cleared whenever a new action is taken, not just undone

        # live mouse tracking -- pcgui.GUI itself only ever fires
        # on_touch (a discrete click), but pcgui.pccursor.mouse.query()
        # is a separate, lower-level HID poll that returns the mouse's
        # current screen position at any moment, click or not. Confirmed
        # on real hardware: query('present') is 1 with a mouse attached,
        # query('x')/query('y') read back live screen coordinates.
        # _last_live_mouse_xy avoids redundant readout updates (and the
        # position-readout math) on every 10ms tick when the mouse
        # hasn't actually moved since the last poll.
        self._last_live_mouse_xy = None

        # template wireframes -- see save_wireframe_file/load_template_active
        # near the top of this file. Independent of the open model:
        # loaded once here, not touched by NEW FILE/OPEN, not part of
        # undo/redo. template_main/template_local are the actual
        # (size, spacing, scale, centerlines, show_xy, show_xz, show_yz)
        # configs currently active, or None if that slot is unset or its
        # saved file has gone missing.
        self.template_main_name, self.template_local_name = load_template_active()
        self.template_main = self._safe_load_wireframe(self.template_main_name)
        self.template_local = self._safe_load_wireframe(self.template_local_name)
        self._template_dialog_message = ""
        # NEW TEMPLATE dialog's own working fields, separate from the
        # active MAIN/LOCAL config above -- only written into a saved
        # .wf file (and possibly promoted to a slot) on SAVE
        self._template_new_pending = None  # (name, size, spacing, scale) strings, preserved across a same-dialog redraw
        self._template_new_centerlines = True
        self._template_new_xy = True
        self._template_new_xz = True
        self._template_new_yz = True

    def _safe_load_wireframe(self, name):
        if not name:
            return None
        try:
            return load_wireframe_file(name)
        except OSError as e:
            ulog("Model3DPage: template '%s' missing: %s" % (name, e))
            return None

    def show(self):
        # overrides Page.show() to add a live mouse-position poll into
        # the same 10ms tick loop -- everything else here matches
        # Page.show() exactly, including the ticker/background/
        # discovery ticks every other page also relies on
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
            self._poll_live_mouse()
            time.sleep_ms(10)
        try:
            self.g.stop()
        except Exception:
            pass
        gc.collect()
        return self.next

    def _poll_live_mouse(self):
        if self.dialog not in (None, "line_pick", "select_pick", "box_pick", "circle_pick"):
            # no mouse_box on any other (modal) dialog -- see _build_main
            return
        try:
            if not pcgui.pccursor.mouse.query("present"):
                return
            x = pcgui.pccursor.mouse.query("x")
            y = pcgui.pccursor.mouse.query("y")
        except Exception as e:
            ulog("Model3DPage: live mouse query failed: " + str(e))
            return
        if (x, y) == self._last_live_mouse_xy:
            return
        self._last_live_mouse_xy = (x, y)
        try:
            self.mouse_box.value = self._safe_position_readout(x, y)
        except Exception as e:
            ulog("Model3DPage: live mouse readout failed: " + str(e))
        if self.dialog == "circle_pick":
            # lightweight repaint (just the framebuffer scene, not a
            # full widget rebuild) so the snap-preview marker follows
            # the mouse smoothly -- safe to call every tick now that
            # _draw_axes cleans up its own widgets first
            try:
                self._draw_scene(self.g)
            except Exception as e:
                ulog("Model3DPage: circle preview redraw failed: " + str(e))

    def build(self, g):
        hdmi.fill(hdmi.fb().colour(self.BLACK))
        for i in range(self.BORDER):
            g.frame(i, i, 640 - 2 * i, 480 - 2 * i, "", fg=self.GREY, font=1)
        g.caption(320, self.INNER_Y0 + 6, "3D Model Editor", fg=WHITE, bg=self.BLACK, font=3, just="CT")
        self.help_button(g, "model3d", "model3d")

        if self.dialog == "newfile":
            self._build_newfile_dialog(g)
        elif self.dialog == "open":
            self._build_open_dialog(g)
        elif self.dialog == "saveas":
            self._build_saveas_dialog(g)
        elif self.dialog == "delete":
            self._build_delete_dialog(g)
        elif self.dialog == "line_choice":
            self._build_line_choice_dialog(g)
        elif self.dialog == "line":
            self._build_line_dialog(g)
        elif self.dialog == "centerline":
            self._build_centerline_dialog(g)
        elif self.dialog == "box_choice":
            self._build_box_choice_dialog(g)
        elif self.dialog == "box":
            self._build_box_dialog(g)
        elif self.dialog == "circle":
            self._build_circle_dialog(g)
        elif self.dialog == "arc":
            self._build_arc_dialog(g)
        elif self.dialog == "grid":
            self._build_grid_dialog(g)
        elif self.dialog == "extrude":
            self._build_extrude_dialog(g)
        elif self.dialog == "edit":
            self._build_edit_dialog(g)
        elif self.dialog == "layers":
            self._build_layers_dialog(g)
        elif self.dialog == "template":
            self._build_template_dialog(g)
        elif self.dialog == "template_pick_main":
            self._build_wireframe_list_dialog(g, "PICK MAIN", "SELECT", self.on_confirm_pick_main)
        elif self.dialog == "template_pick_local":
            self._build_wireframe_list_dialog(g, "PICK LOCAL", "SELECT", self.on_confirm_pick_local)
        elif self.dialog == "template_delete":
            self._build_wireframe_list_dialog(g, "DELETE TEMPLATE", "DELETE", self.on_confirm_delete_template)
        elif self.dialog == "template_new":
            self._build_template_new_dialog(g)
        elif (self.dialog == "line_pick" or self.dialog == "select_pick" or self.dialog == "box_pick"
              or self.dialog == "circle_pick"):
            # reuses the normal main layout (canvas, zoom, D-pad, all
            # of it) rather than a modal -- picking points/elements
            # needs the wireframe/grid actually visible and clickable,
            # which no modal dialog in this app currently shows
            self._build_main(g)
        else:
            self._build_main(g)

    # command name -> its real dialog key, used once the CONFIRM popup
    # (see on_command / on_confirm_command) is accepted
    COMMAND_DIALOG = {
        "NEW FILE": "newfile", "OPEN": "open", "SAVE AS": "saveas", "DELETE": "delete",
        "SELECT": "select_pick", "LINE": "line_choice", "CTR LINE": "centerline", "BOX": "box_choice",
        "CIRCLE": "circle", "ARC": "arc", "GRID": "grid", "TEMPLATE": "template",
    }

    def _build_main(self, g):
        g.frame(self.PANEL_X, self.PANEL_Y, self.PANEL_W, self.PANEL_H, "COMMANDS", fg=WHITE, font=1)

        btn_x = self.PANEL_X + 6
        btn_w = self.PANEL_W - 12  # fit the panel, wide enough for "NEW FILE" / "SAVE AS" at font=1
        y = self.PANEL_Y + 26
        icon_slots = []
        button_rects = []
        for name in self.COMMANDS:
            # blank label, background matches the page so only the icon
            # shows -- real click handling still goes through this
            # button's own callback (proven, used everywhere else in
            # this app), the icon is just drawn on top afterwards, same
            # trick CalculatorPage uses for its operator icons
            g.button(btn_x, y, btn_w, self.CMD_BTN_H, "", fg=WHITE, bg=self.BLACK, font=1,
                     callback=self._make_command_handler(name))
            icon_slots.append((name, btn_x + 4, y + 4))
            button_rects.append((name, btn_x, y, btn_w, self.CMD_BTN_H))
            y += self.CMD_BTN_H + self.CMD_BTN_GAP

        # status readout for whichever command was last pressed, in the
        # (currently empty) area to the right of the panel
        self.status_box = g.displaybox(self.PANEL_X + self.PANEL_W + 20, self.PANEL_Y,
                                        640 - self.BORDER - (self.PANEL_X + self.PANEL_W + 20) - 8, 24,
                                        "Ready", fg=WHITE, bg=self.BLACK, font=2)
        snap_status = "grid snap ON" if (self.grid and self.snap_enabled) else "not snapped"
        if self.dialog == "line_pick":
            verb = "START" if self.line_stage == "start" else "END"
            self.status_box.value = "LINE: click %s point in VIEW (%s) -- pick another command to cancel" % (verb, snap_status)
        elif self.dialog == "select_pick":
            self.status_box.value = "SELECT: click near an item in VIEW -- pick another command to cancel"
        elif self.dialog == "box_pick":
            verb = "FIRST" if self.box_pick_start is None else "OPPOSITE"
            self.status_box.value = "BOX: click %s corner in VIEW (%s) -- pick another command to cancel" % (verb, snap_status)
        elif self.dialog == "circle_pick":
            self.status_box.value = "CIRCLE: click centre in VIEW (%s) -- pick another command to cancel" % snap_status

        # temporary readout so mouse/touch input can be confirmed working
        # on real hardware independently of the command buttons above --
        # sits below the panel now that the taller buttons fill it
        # width is fixed, not tied to the now-narrow PANEL_W -- "Mouse:
        # (640, 480)" doesn't fit in 56px
        self.mouse_box = g.displaybox(self.PANEL_X, self.PANEL_Y + self.PANEL_H + 4,
                                       self.MOUSE_BOX_W, 20, "X:--  Y:--  Z:--", fg=WHITE, bg=self.BLACK, font=1)
        grid_label = "GRID: ON" if self.grid_visible else "GRID: OFF"
        g.button(self.GRID_BTN_X, self.GRID_BTN_Y, self.GRID_BTN_W, self.GRID_BTN_H, grid_label,
                 fg=WHITE, bg=BTN, font=1, callback=self.on_toggle_grid_visible)
        snap_label = "SNAP: ON" if self.snap_enabled else "SNAP: OFF"
        g.button(self.SNAP_BTN_X, self.GRID_BTN_Y, self.SNAP_BTN_W, self.GRID_BTN_H, snap_label,
                 fg=WHITE, bg=BTN, font=1, callback=self.on_toggle_snap)
        g.button(self.EXTRUDE_BTN_X, self.GRID_BTN_Y, self.EXTRUDE_BTN_W, self.GRID_BTN_H, "EXTRUDE",
                 fg=WHITE, bg=BTN, font=1, callback=self.on_extrude_pressed)
        g.button(self.EDIT_BTN_X, self.GRID_BTN_Y, self.EDIT_BTN_W, self.GRID_BTN_H, "EDIT",
                 fg=WHITE, bg=BTN, font=1, callback=self.on_edit_pressed)
        # re-enabled -- the slider experiment that disabled this is
        # over (sliders got dropped entirely in favour of the D-pad),
        # and the mouse coordinate readout is genuinely useful again
        # for eyeballing where to place a LINE/BOX/CIRCLE/ARC point
        try:
            g.on_touch(self.on_touch)
        except Exception as e:
            ulog("Model3DPage: on_touch registration failed: " + str(e))
        # on_move (continuous hover) and mouse-wheel zoom were both
        # tried and dropped again: dir(pcgui.GUI) on real hardware
        # shows on_touch as the only interactive input method this
        # class defines at all. on_move is a plain instance attribute
        # rather than a registration method (assigning it didn't
        # error), but assigning it made no observable difference on
        # real hardware -- the mouse position readout stayed silent
        # between clicks, confirming poll() never actually reads it.
        # It's still updated on every click via on_touch below.

        g.button(522, 410, 110, 32, "MENU", fg=WHITE, bg=RED, font=2, callback=self.on_back)

        g.frame(self.CANVAS_X0, self.CANVAS_Y0, self.CANVAS_W, self.CANVAS_H, "VIEW", fg=WHITE, font=1)
        g.button(self.ZOOM_OUT_X, self.ZOOM_BTN_Y, self.ZOOM_BTN_W, self.ZOOM_BTN_H, "-",
                 fg=WHITE, bg=BTN, font=2, callback=self.on_zoom_out)
        g.button(self.ZOOM_IN_X, self.ZOOM_BTN_Y, self.ZOOM_BTN_W, self.ZOOM_BTN_H, "+",
                 fg=WHITE, bg=BTN, font=2, callback=self.on_zoom_in)
        g.button(self.RESET_VIEW_X, self.ZOOM_BTN_Y, self.RESET_BTN_W, self.ZOOM_BTN_H, "RST",
                 fg=WHITE, bg=RED, font=1, callback=self.on_reset_view)
        g.button(self.UNDO_X, self.UNDO_REDO_Y, self.UNDO_REDO_W, self.UNDO_REDO_H, "UNDO",
                 fg=WHITE, bg=BTN, font=1, callback=self.on_undo)
        g.button(self.REDO_X, self.UNDO_REDO_Y, self.UNDO_REDO_W, self.UNDO_REDO_H, "REDO",
                 fg=WHITE, bg=BTN, font=1, callback=self.on_redo)
        g.button(self.LAYERS_BTN_X, self.LAYERS_BTN_Y, self.LAYERS_BTN_W, self.LAYERS_BTN_H,
                 "LAYER: " + self.current_layer, fg=WHITE, bg=BTN, font=1, callback=self.on_open_layers)

        # pan nudge buttons -- click-based, proven reliable (sliders
        # were tried and dropped; these are the only pan control now)
        dpad = (("U", self.on_pan_up), ("D", self.on_pan_down),
                ("L", self.on_pan_left), ("R", self.on_pan_right))
        for i, (label, callback) in enumerate(dpad):
            by = self.DPAD_Y0 + i * (self.DPAD_H + self.DPAD_GAP)
            g.button(self.DPAD_X, by, self.DPAD_W, self.DPAD_H, label,
                     fg=WHITE, bg=0x3399FF, font=1, callback=callback)

        g.button(self.AZ_MINUS_X, self.ROT_BTN_Y, self.ROT_STEP_BTN_W, self.ROT_BTN_H, "AZ -",
                 fg=WHITE, bg=0x3399FF, font=1, callback=self.on_rotate_az_minus)
        g.button(self.AZ_PLUS_X, self.ROT_BTN_Y, self.ROT_STEP_BTN_W, self.ROT_BTN_H, "AZ +",
                 fg=WHITE, bg=0x3399FF, font=1, callback=self.on_rotate_az_plus)
        g.button(self.EL_MINUS_X, self.ROT_BTN_Y, self.ROT_STEP_BTN_W, self.ROT_BTN_H, "EL -",
                 fg=WHITE, bg=0x3399FF, font=1, callback=self.on_rotate_el_minus)
        g.button(self.EL_PLUS_X, self.ROT_BTN_Y, self.ROT_STEP_BTN_W, self.ROT_BTN_H, "EL +",
                 fg=WHITE, bg=0x3399FF, font=1, callback=self.on_rotate_el_plus)
        wire_label = "WIRE: ON" if self.wireframe_visible else "WIRE: OFF"
        g.button(self.WIRE_BTN_X, self.ROT_BTN_Y, self.WIRE_BTN_W, self.ROT_BTN_H, wire_label,
                 fg=WHITE, bg=BTN, font=1, callback=self.on_toggle_wireframe)

        # raw framebuffer drawing happens LAST, strictly after every
        # widget above -- same ordering the earlier version of this
        # page used, so it can't be clobbered by the widget rebuild.
        # the X/Y/Z axis labels are still plain g.caption() widgets
        # though, so _draw_scene needs g to add those.
        self._draw_scene(g)
        self._draw_command_icons(icon_slots)

        if self.active_command:
            for name, bx, by, bw, bh in button_rects:
                if name == self.active_command:
                    self._draw_dashed_rect(hdmi.fb(), bx - 2, by - 2, bw + 4, bh + 4, RED)
                    break

        if self.dialog == "line_pick" and self.line_stage == "end" and self.line_start_point:
            # marks where the start point landed -- the only feedback
            # available between the two clicks, since there's no live
            # preview line following the mouse (needs on_move)
            try:
                fb = hdmi.fb()
                sx, sy = self._project(self.line_start_point[0], self.line_start_point[1],
                                        self.line_start_point[2], self._last_scale,
                                        self._last_origin[0], self._last_origin[1])
                r = 5
                self._clipped_line(fb, sx - r, sy, sx + r, sy, RED)
                self._clipped_line(fb, sx, sy - r, sx, sy + r, RED)
            except Exception as e:
                ulog("Model3DPage: start marker draw error: " + type(e).__name__ + " " + str(e))

        if self.dialog == "box_pick" and self.box_pick_start:
            # marks where the first corner landed -- the only feedback
            # available between the two clicks (no live outline: that
            # needs on_move, confirmed not to fire on this hardware)
            try:
                fb = hdmi.fb()
                sx, sy = self._project(self.box_pick_start[0], self.box_pick_start[1],
                                        self.box_pick_start[2], self._last_scale,
                                        self._last_origin[0], self._last_origin[1])
                r = 5
                self._clipped_line(fb, sx - r, sy, sx + r, sy, RED)
                self._clipped_line(fb, sx, sy - r, sx, sy + r, RED)
            except Exception as e:
                ulog("Model3DPage: box start marker draw error: " + type(e).__name__ + " " + str(e))

    def _draw_command_icons(self, icon_slots):
        # rendered to 26x26 BMP via Inkscape + Pillow, not yet confirmed
        # against real hardware: bmp colour depth/dithering on this
        # display is unverified, same caveat the old 3D viewer code
        # flagged about this board's limited palette
        for name, ix, iy in icon_slots:
            icon_name = ICON_NAMES.get(name)
            if not icon_name:
                continue
            path = ICONS_DIR + "/" + icon_name + ".bmp"
            try:
                pcimage.draw_bmp(path, ix, iy, dither=True)
            except Exception as e:
                ulog("Model3DPage: icon load failed for " + name + ": " + type(e).__name__ + " " + str(e))

    # --- scene projection -------------------------------------------

    def _update_rotation_trig(self):
        # cached once per azimuth/elevation change rather than
        # recomputed per point -- _raw_project runs for every vertex of
        # every box/line/circle/arc/grid-dot in a redraw
        az = math.radians(self.azimuth_deg)
        el = math.radians(self.elevation_deg)
        self._rot_ct = math.cos(az)
        self._rot_st = math.sin(az)
        self._rot_cp = math.cos(el)
        self._rot_sp = math.sin(el)

    def _raw_project(self, x, y, z):
        # projects at scale=1, origin=(0,0) -- just used to measure
        # extents before the real scale/origin are known. Z is "up" on
        # screen at any azimuth; elevation 0 is edge-on (only Z moves
        # vertically), elevation 90 is straight down (only X/Y move
        # vertically, Z is invisible).
        ct, st, cp, sp = self._rot_ct, self._rot_st, self._rot_cp, self._rot_sp
        x1 = x * ct - y * st
        y1 = x * st + y * ct
        sx = x1
        sy = y1 * sp - z * cp
        return sx, sy

    # which two coordinate indices sweep around a circle/arc in each
    # plane -- the third index stays fixed at the centre's value
    PLANE_AXES = {"XY": (0, 1), "XZ": (0, 2), "YZ": (1, 2)}
    AXIS_NAMES = {0: "X", 1: "Y", 2: "Z"}

    def _plane_normal_axis(self, plane):
        # the one coordinate index NOT in PLANE_AXES[plane] -- 0/1/2
        # sum to 3, so subtracting the two in-plane indices leaves it
        i, j = self.PLANE_AXES[plane]
        return 3 - i - j

    def _box_corners(self, box):
        c0, c1 = box[0], box[1]
        xs, ys, zs = (c0[0], c1[0]), (c0[1], c1[1]), (c0[2], c1[2])
        return [(x, y, z) for x in xs for y in ys for z in zs]

    def _box_edges(self, box):
        c0, c1 = box[0], box[1]
        (x0, y0, z0), (x1, y1, z1) = c0, c1
        corners = {
            (0, 0, 0): (x0, y0, z0), (1, 0, 0): (x1, y0, z0),
            (0, 1, 0): (x0, y1, z0), (0, 0, 1): (x0, y0, z1),
            (1, 1, 0): (x1, y1, z0), (1, 0, 1): (x1, y0, z1),
            (0, 1, 1): (x0, y1, z1), (1, 1, 1): (x1, y1, z1),
        }
        edge_keys = [
            ((0, 0, 0), (1, 0, 0)), ((1, 0, 0), (1, 1, 0)), ((1, 1, 0), (0, 1, 0)), ((0, 1, 0), (0, 0, 0)),
            ((0, 0, 1), (1, 0, 1)), ((1, 0, 1), (1, 1, 1)), ((1, 1, 1), (0, 1, 1)), ((0, 1, 1), (0, 0, 1)),
            ((0, 0, 0), (0, 0, 1)), ((1, 0, 0), (1, 0, 1)), ((1, 1, 0), (1, 1, 1)), ((0, 1, 0), (0, 1, 1)),
        ]
        return [(corners[a], corners[b]) for a, b in edge_keys]

    def _circle_point(self, center, radius, plane, angle_deg):
        i, j = self.PLANE_AXES[plane]
        p = [center[0], center[1], center[2]]
        rad = math.radians(angle_deg)
        p[i] = center[i] + radius * math.cos(rad)
        p[j] = center[j] + radius * math.sin(rad)
        return (p[0], p[1], p[2])

    def _circle_bounds_points(self, center, radius, plane):
        # cardinal points -- enough to bound a full circle; used as a
        # (slightly generous, but simple and safe) stand-in for arcs too
        return [self._circle_point(center, radius, plane, a) for a in (0, 90, 180, 270)]

    def _model_points(self):
        # everything actually modelled -- NOT the axis arrows
        # themselves (their length is derived from this) and NOT the
        # grid (deliberately -- the grid's extent is usually much
        # bigger than the actual model, and letting it into the
        # auto-fit scale calculation shrank the real model down to fit
        # the grid instead of the other way round). The grid just
        # renders at whatever scale the real model already uses, with
        # anything outside the canvas clipped rather than shrunk to fit.
        pts = []
        for box in self.boxes:
            if self.layer_visible.get(box[2], True):
                pts.extend(self._box_corners(box))
        for (p0, p1, layer) in self.lines:
            if self.layer_visible.get(layer, True):
                pts.append(p0)
                pts.append(p1)
        for (c, r, plane, layer) in self.circles:
            if self.layer_visible.get(layer, True):
                pts.extend(self._circle_bounds_points(c, r, plane))
        for (c, r, plane, a0, a1, layer) in self.arcs:
            if self.layer_visible.get(layer, True):
                pts.extend(self._circle_bounds_points(c, r, plane))
        return pts

    def _axis_length(self):
        pts = self._model_points()
        if not pts:
            return 50.0
        m = 0.0
        for (x, y, z) in pts:
            m = max(m, abs(x), abs(y), abs(z))
        # 30% past the model's largest dimension, so every axis arrow
        # still has a visible stretch beyond wherever _axis_extent says
        # the model itself already reaches
        return max(m * 1.3, 30.0)

    def _axis_extent(self, axis_index):
        # how far the model already reaches along one axis (0=x,1=y,
        # 2=z) -- the arrow for that axis starts here instead of at
        # (0,0,0), so it doesn't overlap a wireframe edge running the
        # same direction
        pts = self._model_points()
        m = 0.0
        for p in pts:
            m = max(m, abs(p[axis_index]))
        return m

    def _scene_points(self):
        # everything that needs to fit on screen, including the axis
        # tips, so the gizmo is never clipped by the auto-fit
        pts = self._model_points()
        length = self._axis_length()
        pts.append((0, 0, 0))
        for axis, d in self.AXIS_DIRS.items():
            pts.append((d[0] * length, d[1] * length, d[2] * length))
        return pts

    def _compute_transform(self, pts):
        # (0,0,0) is pinned at (ORIGIN_X, ORIGIN_Y) -- scale is
        # whatever fits the furthest point in each of the four
        # directions (left/right/up/down) into the space actually
        # available on that side of the fixed anchor, since it's no
        # longer centred in the canvas
        raws = [self._raw_project(p[0], p[1], p[2]) for p in pts]
        xs = [r[0] for r in raws] or [0.0]
        ys = [r[1] for r in raws] or [0.0]
        max_right = max(max(xs), 0.0)
        max_left = -min(min(xs), 0.0)
        max_down = max(max(ys), 0.0)
        max_up = -min(min(ys), 0.0)

        space_right = self.CANVAS_X1 - self.ORIGIN_X
        space_left = self.ORIGIN_X - self.CANVAS_X0
        space_down = self.CANVAS_Y1 - self.ORIGIN_Y
        space_up = self.ORIGIN_Y - self.CANVAS_Y0

        candidates = []
        for extent, space in ((max_right, space_right), (max_left, space_left),
                               (max_down, space_down), (max_up, space_up)):
            if extent > 0:
                candidates.append((space * 0.9) / extent)
        scale = min(candidates) if candidates else 1.0
        # zoom multiplies the auto-fit scale; pan is a plain screen-pixel
        # offset from the fixed anchor -- both are user-driven, on top
        # of the auto-fit that's still computed against the anchor
        # itself, so panned/zoomed views can end up looser or tighter
        # than the 90%-of-available-space fit implies
        return scale * self.zoom, self.ORIGIN_X + self.pan_x, self.ORIGIN_Y + self.pan_y

    def _project(self, x, y, z, scale, origin_x, origin_y):
        sx, sy = self._raw_project(x, y, z)
        return origin_x + sx * scale, origin_y + sy * scale

    def _clip_to_canvas(self, x0, y0, x1, y1):
        # Cohen-Sutherland clip against the VIEW canvas rectangle --
        # without this, zooming in (which just multiplies the scale
        # with no limit on the result) sends wireframe lines straight
        # past the canvas edge and off the bottom of the screen.
        # Returns a clipped (x0,y0,x1,y1) or None if fully outside.
        xmin, ymin, xmax, ymax = self.CANVAS_X0, self.CANVAS_Y0, self.CANVAS_X1, self.CANVAS_Y1

        def out_code(x, y):
            c = 0
            if x < xmin: c |= 1
            elif x > xmax: c |= 2
            if y < ymin: c |= 4
            elif y > ymax: c |= 8
            return c

        c0, c1 = out_code(x0, y0), out_code(x1, y1)
        for _ in range(8):  # bounded loop -- 4 clip edges is always enough, this is just a safety cap
            if not (c0 | c1):
                return x0, y0, x1, y1
            if c0 & c1:
                return None
            c_out = c0 or c1
            if c_out & 8:
                x = x0 + (x1 - x0) * (ymax - y0) / (y1 - y0)
                y = ymax
            elif c_out & 4:
                x = x0 + (x1 - x0) * (ymin - y0) / (y1 - y0)
                y = ymin
            elif c_out & 2:
                y = y0 + (y1 - y0) * (xmax - x0) / (x1 - x0)
                x = xmax
            else:
                y = y0 + (y1 - y0) * (xmin - x0) / (x1 - x0)
                x = xmin
            if c_out == c0:
                x0, y0 = x, y
                c0 = out_code(x0, y0)
            else:
                x1, y1 = x, y
                c1 = out_code(x1, y1)
        return None

    def _clipped_line(self, fb, x0, y0, x1, y1, colour):
        clipped = self._clip_to_canvas(x0, y0, x1, y1)
        if clipped:
            _fb_line(fb, clipped[0], clipped[1], clipped[2], clipped[3], colour)

    def _draw_scene(self, g):
        pts = self._scene_points()
        if not pts:
            return
        try:
            scale, ox, oy = self._compute_transform(pts)
            self._last_scale, self._last_origin = scale, (ox, oy)
            fb = hdmi.fb()
            # geometry always draws in plain WHITE, selected or not --
            # confirmed on real hardware that swapping in SELECT_COLOR
            # here (even RED, otherwise proven to render fine
            # elsewhere) made the selected item vanish entirely rather
            # than highlight, and undoing then redoing (which both just
            # clear self.selected back to None) brought it straight
            # back. Whatever's actually wrong with that colour swap
            # isn't worth the risk of ever hiding real geometry again
            # -- selection now gets a separate, additive marker instead
            # (_draw_selection_marker)
            #
            # BOX is not "the wireframe" -- it stays visible regardless
            # of WIRE, which only toggles LINE/CIRCLE/ARC
            for bi, box in enumerate(self.boxes):
                if not self.layer_visible.get(box[2], True):
                    continue
                for p1, p2 in self._box_edges(box):
                    s1 = self._project(p1[0], p1[1], p1[2], scale, ox, oy)
                    s2 = self._project(p2[0], p2[1], p2[2], scale, ox, oy)
                    self._clipped_line(fb, s1[0], s1[1], s2[0], s2[1], WHITE)
            if self.wireframe_visible:
                for li, (p0, p1, layer) in enumerate(self.lines):
                    if not self.layer_visible.get(layer, True):
                        continue
                    s0 = self._project(p0[0], p0[1], p0[2], scale, ox, oy)
                    s1 = self._project(p1[0], p1[1], p1[2], scale, ox, oy)
                    self._clipped_line(fb, s0[0], s0[1], s1[0], s1[1], WHITE)
                for ci, (c, r, plane, layer) in enumerate(self.circles):
                    if not self.layer_visible.get(layer, True):
                        continue
                    self._draw_arc(fb, c, r, plane, 0, 360, scale, ox, oy, colour=WHITE)
                for ai, (c, r, plane, a0, a1, layer) in enumerate(self.arcs):
                    if not self.layer_visible.get(layer, True):
                        continue
                    self._draw_arc(fb, c, r, plane, a0, a1, scale, ox, oy, colour=WHITE)
            self._draw_selection_marker(fb, scale, ox, oy)
            if self.grid and self.grid_visible:
                self._draw_grid_dots(fb, scale, ox, oy)
            if self.template_main:
                self._draw_template_wireframe(fb, scale, ox, oy, self.template_main)
            if self.template_local:
                self._draw_template_wireframe(fb, scale, ox, oy, self.template_local)
            if self.dialog == "circle_pick":
                self._draw_circle_snap_preview(fb, scale, ox, oy)

            self._draw_axes(g, fb, scale, ox, oy)
        except Exception as e:
            ulog("Model3DPage: scene draw error: " + type(e).__name__ + " " + str(e))

    def _selected_center_point(self):
        # 3D point to mark for whatever's currently selected -- a
        # midpoint for box/line, the centre itself for circle/arc
        if not self.selected:
            return None
        kind, idx = self.selected
        try:
            if kind == "box":
                c0, c1 = self.boxes[idx][0], self.boxes[idx][1]
                return tuple((c0[i] + c1[i]) / 2.0 for i in range(3))
            if kind == "line":
                p0, p1 = self.lines[idx][0], self.lines[idx][1]
                return tuple((p0[i] + p1[i]) / 2.0 for i in range(3))
            if kind == "circle":
                return self.circles[idx][0]
            if kind == "arc":
                return self.arcs[idx][0]
        except IndexError:
            return None
        return None

    def _draw_selection_marker(self, fb, scale, ox, oy):
        # additive-only feedback for SELECT -- a crosshair drawn ON TOP
        # of the (always-WHITE) selected geometry rather than replacing
        # its colour, so a marker that fails to render for whatever
        # reason still leaves the geometry itself visible
        center = self._selected_center_point()
        if center is None:
            return
        mx, my = self._project(center[0], center[1], center[2], scale, ox, oy)
        r = 8
        self._clipped_line(fb, mx - r, my, mx + r, my, self.SELECT_COLOR)
        self._clipped_line(fb, mx, my - r, mx, my + r, self.SELECT_COLOR)

    def _draw_circle_snap_preview(self, fb, scale, ox, oy):
        # live preview for CIRCLE's click-to-place centre step -- a
        # crosshair at wherever a click would land right now (grid-
        # snapped if SNAP TO GRID is on), so you can see the target
        # before committing. Uses the last live-polled mouse position
        # (see _poll_live_mouse); does nothing if the mouse hasn't been
        # seen yet or is currently outside the canvas.
        if self._last_live_mouse_xy is None:
            return
        x, y = self._last_live_mouse_xy
        if not self._in_canvas(x, y):
            return
        try:
            plane, point = self._plane_point_at(x, y)
        except Exception:
            return
        mx, my = self._project(point[0], point[1], point[2], scale, ox, oy)
        r = 6
        self._clipped_line(fb, mx - r, my, mx + r, my, self.CIRCLE_PREVIEW_COLOR)
        self._clipped_line(fb, mx, my - r, mx, my + r, self.CIRCLE_PREVIEW_COLOR)

    def _draw_grid_dots(self, fb, scale, ox, oy):
        # a dot at every grid intersection in its plane -- a visible
        # reference to eyeball/eventually snap to, not full grid lines
        # (much cheaper to draw and less visually busy against the
        # wireframe). Grey, not white, so it reads as background
        # reference rather than part of the actual model. Spans 0 to
        # extent (not -extent to +extent) in both plane axes, matching
        # every box/line/circle/arc's own 0-based convention -- an
        # extent equal to a box's size sits exactly under that box,
        # instead of straddling it centred on the origin.
        # `position` places the whole plane along its normal axis (e.g.
        # a "vertical" XZ grid's Y), so it can line up with an actual
        # wall instead of sitting at 0. extent_i/extent_j are
        # independent, so a grid can exactly cover a non-square face.
        plane, spacing, extent_i, extent_j, position = self.grid
        i, j = self.PLANE_AXES[plane]
        k = self._plane_normal_axis(plane)
        ni = int(extent_i / spacing)
        nj = int(extent_j / spacing)
        for gi in range(0, ni + 1):
            for gj in range(0, nj + 1):
                p = [0.0, 0.0, 0.0]
                p[i] = gi * spacing
                p[j] = gj * spacing
                p[k] = position
                sx, sy = self._project(p[0], p[1], p[2], scale, ox, oy)
                if self.CANVAS_X0 <= sx <= self.CANVAS_X1 and self.CANVAS_Y0 <= sy <= self.CANVAS_Y1:
                    ix, iy = int(sx), int(sy)
                    _fb_pixel(fb, ix, iy, self.GREY)
                    _fb_pixel(fb, ix + 1, iy, self.GREY)
                    _fb_pixel(fb, ix, iy + 1, self.GREY)
                    _fb_pixel(fb, ix + 1, iy + 1, self.GREY)

    def _draw_template_wireframe(self, fb, scale, ox, oy, cfg):
        # a reference cube through the origin -- unlike the per-file
        # GRID (0 to extent, matching the model's own convention), this
        # spans -size/2 to +size/2 in each axis so it's actually
        # centred on the origin, which is what makes "centre lines"
        # (the two lines through 0,0 on each shown plane) meaningful.
        size, spacing, template_scale, centerlines, show_xy, show_xz, show_yz = cfg
        eff_size = size * template_scale
        eff_spacing = spacing * template_scale
        if eff_spacing <= 0:
            return
        half = eff_size / 2.0
        show = {"XY": show_xy, "XZ": show_xz, "YZ": show_yz}
        for plane in ("XY", "XZ", "YZ"):
            if not show[plane]:
                continue
            i, j = self.PLANE_AXES[plane]
            k = self._plane_normal_axis(plane)
            n = int(eff_size / eff_spacing)
            for gi in range(0, n + 1):
                for gj in range(0, n + 1):
                    p = [0.0, 0.0, 0.0]
                    p[i] = -half + gi * eff_spacing
                    p[j] = -half + gj * eff_spacing
                    p[k] = 0.0
                    sx, sy = self._project(p[0], p[1], p[2], scale, ox, oy)
                    if self.CANVAS_X0 <= sx <= self.CANVAS_X1 and self.CANVAS_Y0 <= sy <= self.CANVAS_Y1:
                        ix, iy = int(sx), int(sy)
                        _fb_pixel(fb, ix, iy, self.GREY)
                        _fb_pixel(fb, ix + 1, iy, self.GREY)
                        _fb_pixel(fb, ix, iy + 1, self.GREY)
                        _fb_pixel(fb, ix + 1, iy + 1, self.GREY)
            if centerlines:
                p0 = [0.0, 0.0, 0.0]
                p0[i] = -half
                p1 = [0.0, 0.0, 0.0]
                p1[i] = half
                s0 = self._project(p0[0], p0[1], p0[2], scale, ox, oy)
                s1 = self._project(p1[0], p1[1], p1[2], scale, ox, oy)
                self._clipped_line(fb, s0[0], s0[1], s1[0], s1[1], self.GREY)
                p2 = [0.0, 0.0, 0.0]
                p2[j] = -half
                p3 = [0.0, 0.0, 0.0]
                p3[j] = half
                s2 = self._project(p2[0], p2[1], p2[2], scale, ox, oy)
                s3 = self._project(p3[0], p3[1], p3[2], scale, ox, oy)
                self._clipped_line(fb, s2[0], s2[1], s3[0], s3[1], self.GREY)

    def _draw_arc(self, fb, center, radius, plane, a0, a1, scale, ox, oy, segments=32, colour=WHITE):
        # approximates a circle (a0=0, a1=360) or arc as a polyline of
        # short chords -- fewer chords for a short arc, always at
        # least 3 so nothing degenerates to a single dot
        sweep = a1 - a0
        n = max(3, int(round(segments * abs(sweep) / 360.0)))
        prev = None
        for i in range(n + 1):
            angle = a0 + sweep * i / n
            p3d = self._circle_point(center, radius, plane, angle)
            s = self._project(p3d[0], p3d[1], p3d[2], scale, ox, oy)
            if prev is not None:
                self._clipped_line(fb, prev[0], prev[1], s[0], s[1], colour)
            prev = s

    def _draw_axes(self, g, fb, scale, ox, oy):
        # X/Y/Z reference arrows, one colour each, so the planes stay
        # readable no matter what's been modelled. When the wireframe
        # is showing, each starts past wherever the model already
        # reaches along that axis (not at literal (0,0,0)) so it
        # doesn't trace back over -- and cancel out -- a wireframe edge
        # running the same direction. With WIRE off there's no edge to
        # avoid, so they run the full length from the origin instead --
        # otherwise, with the model hidden, all that's left on screen is
        # a short sliver near the tip (or nothing at all, if that
        # sliver falls outside the canvas).
        # Arrowhead is just two short "wing" lines back from the tip.
        #
        # the axis/origin labels are real g.caption() widgets (not raw
        # framebuffer pixels), so calling this repeatedly without
        # removing the previous batch first would pile up stale
        # duplicates -- matters now that _draw_scene (which calls this)
        # can be invoked directly on every live mouse-move tick, not
        # just from a full build()
        for w in self._axis_label_widgets:
            try:
                g.remove(w)
            except Exception:
                pass
        self._axis_label_widgets = []

        length = self._axis_length()
        wing = length * 0.15
        axis_index = {"X": 0, "Y": 1, "Z": 2}
        for axis, d in self.AXIS_DIRS.items():
            perp = self.AXIS_PERP[axis]
            colour = self.AXIS_COLORS[axis]
            start_at = self._axis_extent(axis_index[axis]) if self.wireframe_visible else 0.0
            start3d = (d[0] * start_at, d[1] * start_at, d[2] * start_at)
            tip3d = (d[0] * length, d[1] * length, d[2] * length)
            start = self._project(start3d[0], start3d[1], start3d[2], scale, ox, oy)
            tip = self._project(tip3d[0], tip3d[1], tip3d[2], scale, ox, oy)
            self._clipped_line(fb, start[0], start[1], tip[0], tip[1], colour)

            w1 = tuple(tip3d[i] - wing * d[i] + wing * 0.5 * perp[i] for i in range(3))
            w2 = tuple(tip3d[i] - wing * d[i] - wing * 0.5 * perp[i] for i in range(3))
            w1s = self._project(w1[0], w1[1], w1[2], scale, ox, oy)
            w2s = self._project(w2[0], w2[1], w2[2], scale, ox, oy)
            self._clipped_line(fb, tip[0], tip[1], w1s[0], w1s[1], colour)
            self._clipped_line(fb, tip[0], tip[1], w2s[0], w2s[1], colour)

            # only label the tip if it's actually still on screen --
            # otherwise this would place a caption widget off-canvas
            if self.CANVAS_X0 <= tip[0] <= self.CANVAS_X1 and self.CANVAS_Y0 <= tip[1] <= self.CANVAS_Y1:
                w = g.caption(int(tip[0]) + 6, int(tip[1]) - 8, axis, fg=colour, bg=self.BLACK, font=1)
                self._axis_label_widgets.append(w)

        origin = self._project(0, 0, 0, scale, ox, oy)
        w = g.caption(int(origin[0]) + 6, int(origin[1]) + 4, "0,0", fg=WHITE, bg=self.BLACK, font=1)
        self._axis_label_widgets.append(w)

    # --- modal dialogs --------------------------------------------------
    # NEW FILE / SAVE AS / DELETE each fully replace the screen with a
    # smaller centred window instead of the normal commands panel --
    # simplest way to avoid a click landing on a now-hidden button
    # underneath, and reuses the same "stop the GUI, refill the screen,
    # rebuild" redraw the earlier version of this page proved out.

    def _redraw(self):
        try:
            self.g.stop()
        except Exception:
            pass
        g = pcgui.GUI()
        self.g = g
        g.start()
        self.build(g)

    def _build_newfile_dialog(self, g):
        h = 240
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "NEW FILE", fg=WHITE, font=2)

        defaults = (100.0, 60.0, 40.0)
        labels = ("X (mm):", "Y (mm):", "Z (mm):")
        boxes = []
        for i, label in enumerate(labels):
            ly = y0 + 40 + i * 44
            g.caption(self.DLG_X + 20, ly + 6, label, fg=WHITE, bg=self.BLACK, font=1)
            boxes.append(g.textbox(self.DLG_X + 130, ly, 100, 26, str(defaults[i]), font=1))
        self.newfile_x_box, self.newfile_y_box, self.newfile_z_box = boxes

        g.button(self.DLG_X + 20, y0 + 180, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_newfile)
        g.button(self.DLG_X + 180, y0 + 180, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_saveas_dialog(self, g):
        h = 280
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "SAVE AS", fg=WHITE, font=2)
        g.caption(self.DLG_X + 20, y0 + 40, "Name:", fg=WHITE, bg=self.BLACK, font=1)
        self.saveas_box = g.textbox(self.DLG_X + 20, y0 + 58, self.DLG_W - 40, 26,
                                     self.model_name, font=1)

        # EXPORT STL below reuses this same name field -- solidifies
        # LINE/CIRCLE/ARC edges into struts of this thickness (BOX
        # elements are already solid, unaffected). See the STL export
        # module comment near write_stl_file for what this can't do
        # (it's not a slicer -- load the .stl into one for G-code).
        g.caption(self.DLG_X + 20, y0 + 100, "STL strut thickness (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.stl_thickness_box = g.textbox(self.DLG_X + 20, y0 + 118, self.DLG_W - 40, 26,
                                            str(self.stl_strut_thickness), font=1)

        g.button(self.DLG_X + 20, y0 + h - 110, 120, 40, "SAVE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_saveas)
        g.button(self.DLG_X + 180, y0 + h - 110, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)
        g.button(self.DLG_X + 20, y0 + h - 60, self.DLG_W - 40, 40, "EXPORT STL", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_export_stl)

    def _build_line_choice_dialog(self, g):
        h = 180
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "LINE", fg=WHITE, font=2)
        g.caption(self.DLG_X + self.DLG_W // 2, y0 + 40, "How do you want to place the points?",
                  fg=WHITE, bg=self.BLACK, font=1, just="CT")
        g.button(self.DLG_X + 20, y0 + 70, 120, 44, "CLICK ON GRID", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_line_choice_click)
        g.button(self.DLG_X + 180, y0 + 70, 120, 44, "TYPE VALUES", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_line_choice_type)
        g.button(self.DLG_X + 100, y0 + 126, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_box_choice_dialog(self, g):
        h = 180
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "BOX", fg=WHITE, font=2)
        g.caption(self.DLG_X + self.DLG_W // 2, y0 + 40, "How do you want to place the corners?",
                  fg=WHITE, bg=self.BLACK, font=1, just="CT")
        g.button(self.DLG_X + 20, y0 + 70, 120, 44, "CLICK ON GRID", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_box_choice_click)
        g.button(self.DLG_X + 180, y0 + 70, 120, 44, "TYPE VALUES", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_box_choice_type)
        g.button(self.DLG_X + 100, y0 + 126, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _grid_snap_title_suffix(self):
        # every typed X/Y/Z/radius/angle value across every dialog
        # snaps to this once a GRID is set (see _snap_to_grid) -- shown
        # in each dialog's own title bar since there's no spare row for
        # a separate caption in most of them
        if not self.grid:
            return " (no grid snap)"
        return " (snap: %gmm)" % self.grid[1]

    def _build_line_dialog(self, g):
        # two-step: START POINT then END POINT, using the same three
        # boxes -- they come up blank each step (this is manual entry
        # for now; once the canvas takes clicks directly, LINE can
        # place points with the mouse instead, see on_touch)
        h = 240
        y0 = (480 - h) // 2
        title = "LINE -- START POINT" if self.line_stage == "start" else "LINE -- END POINT"
        title += self._grid_snap_title_suffix()
        g.frame(self.DLG_X, y0, self.DLG_W, h, title, fg=WHITE, font=2)

        labels = ("X (mm):", "Y (mm):", "Z (mm):")
        boxes = []
        for i, label in enumerate(labels):
            ly = y0 + 40 + i * 44
            g.caption(self.DLG_X + 20, ly + 6, label, fg=WHITE, bg=self.BLACK, font=1)
            boxes.append(g.textbox(self.DLG_X + 130, ly, 100, 26, "", font=1))
        self.line_x_box, self.line_y_box, self.line_z_box = boxes

        if self.line_stage == "start":
            g.button(self.DLG_X + 20, y0 + 180, 120, 40, "NEXT", fg=WHITE, bg=BTN, font=2,
                     callback=self.on_line_next)
        else:
            g.button(self.DLG_X + 20, y0 + 180, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                     callback=self.on_line_create)
        g.button(self.DLG_X + 180, y0 + 180, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_box_dialog(self, g):
        # two-step: CORNER 1 then CORNER 2 -- any two opposite corners,
        # not necessarily min/max order (on_box_create sorts that out)
        h = 240
        y0 = (480 - h) // 2
        title = "BOX -- CORNER 1" if self.box_stage == "start" else "BOX -- CORNER 2"
        title += self._grid_snap_title_suffix()
        g.frame(self.DLG_X, y0, self.DLG_W, h, title, fg=WHITE, font=2)

        labels = ("X (mm):", "Y (mm):", "Z (mm):")
        boxes = []
        for i, label in enumerate(labels):
            ly = y0 + 40 + i * 44
            g.caption(self.DLG_X + 20, ly + 6, label, fg=WHITE, bg=self.BLACK, font=1)
            boxes.append(g.textbox(self.DLG_X + 130, ly, 100, 26, "", font=1))
        self.box_x_box, self.box_y_box, self.box_z_box = boxes

        if self.box_stage == "start":
            g.button(self.DLG_X + 20, y0 + 180, 120, 40, "NEXT", fg=WHITE, bg=BTN, font=2,
                     callback=self.on_box_next)
        else:
            g.button(self.DLG_X + 20, y0 + 180, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                     callback=self.on_box_create)
        g.button(self.DLG_X + 180, y0 + 180, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_circle_dialog(self, g):
        # radius (+ plane, + snap) only -- the centre is placed by
        # clicking in VIEW afterward (see on_confirm_circle/circle_pick)
        # rather than typed, with a live snap-preview marker following
        # the mouse (_draw_circle_snap_preview)
        h = 280
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "CIRCLE" + self._grid_snap_title_suffix(), fg=WHITE, font=2)

        if self._circle_radius_pending is not None:
            radius_str = self._circle_radius_pending
            self._circle_radius_pending = None
        else:
            radius_str = ""

        ly = y0 + 40
        g.caption(self.DLG_X + 20, ly + 6, "Radius:", fg=WHITE, bg=self.BLACK, font=1)
        self.circle_r_box = g.textbox(self.DLG_X + 160, ly, 100, 26, radius_str, font=1)

        ly += 44
        g.caption(self.DLG_X + 20, ly + 6, "Plane:", fg=WHITE, bg=self.BLACK, font=1)
        g.button(self.DLG_X + 160, ly, 100, 26, self.circle_plane, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_cycle_circle_plane)

        ly += 44
        snap_label = "SNAP TO GRID: ON" if self.snap_enabled else "SNAP TO GRID: OFF"
        g.button(self.DLG_X + 20, ly, self.DLG_W - 40, 32, snap_label, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_toggle_circle_snap)

        g.button(self.DLG_X + 20, y0 + h - 60, 120, 40, "NEXT", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_circle)
        g.button(self.DLG_X + 180, y0 + h - 60, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_arc_dialog(self, g):
        h = 360
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "ARC" + self._grid_snap_title_suffix(), fg=WHITE, font=2)

        labels = ("Center X:", "Center Y:", "Center Z:", "Radius:", "Start (deg):", "End (deg):")
        boxes = []
        for i, label in enumerate(labels):
            ly = y0 + 36 + i * 38
            g.caption(self.DLG_X + 20, ly + 6, label, fg=WHITE, bg=self.BLACK, font=1)
            boxes.append(g.textbox(self.DLG_X + 130, ly, 100, 24, "", font=1))
        (self.arc_cx_box, self.arc_cy_box, self.arc_cz_box, self.arc_r_box,
         self.arc_start_box, self.arc_end_box) = boxes

        ly = y0 + 36 + 6 * 38
        g.caption(self.DLG_X + 20, ly + 6, "Plane:", fg=WHITE, bg=self.BLACK, font=1)
        g.button(self.DLG_X + 130, ly, 100, 24, self.arc_plane, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_cycle_arc_plane)

        g.button(self.DLG_X + 20, y0 + h - 50, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_arc)
        g.button(self.DLG_X + 180, y0 + h - 50, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_centerline_dialog(self, g):
        h = 200
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "CTR LINE", fg=WHITE, font=2)

        ly = y0 + 40
        g.caption(self.DLG_X + 20, ly + 6, "Axis:", fg=WHITE, bg=self.BLACK, font=1)
        g.button(self.DLG_X + 160, ly, 100, 26, self.centerline_axis, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_cycle_centerline_axis)

        ly += 44
        g.caption(self.DLG_X + 20, ly + 6, "Length (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.centerline_len_box = g.textbox(self.DLG_X + 160, ly, 100, 26, "100", font=1)

        g.button(self.DLG_X + 20, y0 + h - 60, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_centerline)
        g.button(self.DLG_X + 180, y0 + h - 60, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_grid_dialog(self, g):
        h = 348
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "GRID", fg=WHITE, font=2)

        # pre-fill from the current grid (if any) so re-opening this
        # dialog to tweak an existing grid doesn't mean retyping every
        # field from scratch
        if self.grid:
            _, cur_spacing, cur_extent_i, cur_extent_j, cur_position = self.grid
        else:
            cur_spacing, cur_extent_i, cur_extent_j, cur_position = 10, 100, 100, 0

        # independent per-axis extents, so a grid can exactly cover a
        # non-square face instead of being forced into a square region
        axis_i, axis_j = self.PLANE_AXES[self.grid_plane]
        axis_i_name = self.AXIS_NAMES[axis_i]
        axis_j_name = self.AXIS_NAMES[axis_j]

        ly = y0 + 40
        g.caption(self.DLG_X + 20, ly + 6, "Spacing (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.grid_spacing_box = g.textbox(self.DLG_X + 160, ly, 100, 26, str(cur_spacing), font=1)

        ly += 44
        g.caption(self.DLG_X + 20, ly + 6, "Extent " + axis_i_name + " (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.grid_extent_i_box = g.textbox(self.DLG_X + 160, ly, 100, 26, str(cur_extent_i), font=1)

        ly += 44
        g.caption(self.DLG_X + 20, ly + 6, "Extent " + axis_j_name + " (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.grid_extent_j_box = g.textbox(self.DLG_X + 160, ly, 100, 26, str(cur_extent_j), font=1)

        ly += 44
        g.caption(self.DLG_X + 20, ly + 6, "Plane:", fg=WHITE, bg=self.BLACK, font=1)
        g.button(self.DLG_X + 160, ly, 100, 26, self.grid_plane, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_cycle_grid_plane)

        ly += 44
        # where the grid sits along its plane's normal axis -- e.g. for
        # an XZ ("vertical") grid, this is its Y position, so it can
        # line up with an actual wall instead of always sitting at 0
        axis_name = self.AXIS_NAMES[self._plane_normal_axis(self.grid_plane)]
        g.caption(self.DLG_X + 20, ly + 6, axis_name + " position (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.grid_position_box = g.textbox(self.DLG_X + 160, ly, 100, 26, str(cur_position), font=1)

        g.button(self.DLG_X + 20, y0 + h - 60, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_grid)
        g.button(self.DLG_X + 180, y0 + h - 60, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_extrude_dialog(self, g):
        # only reachable with something already selected -- see
        # on_extrude_pressed
        h = 200
        y0 = (480 - h) // 2
        kind = self.selected[0] if self.selected else "?"
        g.frame(self.DLG_X, y0, self.DLG_W, h, "EXTRUDE " + kind.upper() + self._grid_snap_title_suffix(),
                fg=WHITE, font=2)

        if kind == "line":
            label = "Wall height (mm):"
        elif kind == "box":
            label = "Add to height (mm):"
        else:
            label = "Extrude height (mm):"
        g.caption(self.DLG_X + 20, y0 + 44, label, fg=WHITE, bg=self.BLACK, font=1)
        self.extrude_amount_box = g.textbox(self.DLG_X + 20, y0 + 66, 200, 26, "50", font=1)

        g.button(self.DLG_X + 20, y0 + h - 60, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_extrude)
        g.button(self.DLG_X + 180, y0 + h - 60, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _edit_fields(self):
        # (label, current value) pairs for whatever's selected -- the
        # shared source for both building the dialog's textboxes and
        # (via defaults, re-derived the same way in on_confirm_edit)
        # knowing what each typed value means once SAVE is pressed
        kind, idx = self.selected if self.selected else (None, -1)
        if kind == "line":
            p0, p1, layer = self.lines[idx]
            return [("P1 X:", p0[0]), ("P1 Y:", p0[1]), ("P1 Z:", p0[2]),
                    ("P2 X:", p1[0]), ("P2 Y:", p1[1]), ("P2 Z:", p1[2])]
        if kind == "box":
            c0, c1, layer = self.boxes[idx]
            return [("Corner1 X:", c0[0]), ("Corner1 Y:", c0[1]), ("Corner1 Z:", c0[2]),
                    ("Corner2 X:", c1[0]), ("Corner2 Y:", c1[1]), ("Corner2 Z:", c1[2])]
        if kind == "circle":
            c, r, plane, layer = self.circles[idx]
            return [("Center X:", c[0]), ("Center Y:", c[1]), ("Center Z:", c[2]), ("Radius:", r)]
        if kind == "arc":
            c, r, plane, a0, a1, layer = self.arcs[idx]
            return [("Center X:", c[0]), ("Center Y:", c[1]), ("Center Z:", c[2]),
                    ("Radius:", r), ("Start deg:", a0), ("End deg:", a1)]
        raise ValueError("unsupported kind")

    def _build_edit_dialog(self, g):
        # only reachable with something already selected -- see
        # on_edit_pressed. Fields come pre-filled with the item's
        # current values so a small mistake (like a bad SELECT/DELETE-
        # and-redraw, or a mis-snapped point) can be nudged straight
        # rather than deleted and re-entered from scratch.
        h = 360
        y0 = (480 - h) // 2
        kind = self.selected[0] if self.selected else "?"
        try:
            fields = self._edit_fields()
        except (IndexError, ValueError):
            g.frame(self.DLG_X, y0, self.DLG_W, h, "EDIT", fg=WHITE, font=2)
            g.caption(self.DLG_X + self.DLG_W // 2, y0 + 100, "Nothing valid selected",
                      fg=WHITE, bg=self.BLACK, font=1, just="CT")
            g.button(self.DLG_X + 100, y0 + h - 60, 120, 40, "CLOSE", fg=WHITE, bg=RED, font=2,
                     callback=self.on_cancel_dialog)
            return

        g.frame(self.DLG_X, y0, self.DLG_W, h, "EDIT " + kind.upper() + self._grid_snap_title_suffix(),
                fg=WHITE, font=2)
        self.edit_boxes = []
        for i, (label, default) in enumerate(fields):
            ly = y0 + 36 + i * 38
            g.caption(self.DLG_X + 20, ly + 6, label, fg=WHITE, bg=self.BLACK, font=1)
            self.edit_boxes.append(g.textbox(self.DLG_X + 130, ly, 100, 24, "%g" % default, font=1))

        g.button(self.DLG_X + 20, y0 + h - 96, self.DLG_W - 40, 36, "DELETE THIS ITEM",
                 fg=WHITE, bg=RED, font=1, callback=self.on_edit_delete)
        g.button(self.DLG_X + 20, y0 + h - 50, 120, 40, "SAVE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_edit)
        g.button(self.DLG_X + 180, y0 + h - 50, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_layers_dialog(self, g):
        h = 340
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "LAYERS", fg=WHITE, font=2)

        items = []
        for name in self.layers:
            mark = "* " if name == self.current_layer else "  "
            vis = "" if self.layer_visible.get(name, True) else "  (hidden)"
            items.append(mark + name + vis)
        if self._dialog_selected_layer not in self.layers:
            self._dialog_selected_layer = self.layers[0]
        start_index = self.layers.index(self._dialog_selected_layer)
        self.layers_list = g.listbox(self.DLG_X + 20, y0 + 40, self.DLG_W - 40, 120, items,
                                      start_index, font=1, callback=self.on_pick_layer)

        g.button(self.DLG_X + 20, y0 + 170, 130, 36, "SET ACTIVE", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_set_active_layer)
        g.button(self.DLG_X + 170, y0 + 170, 130, 36, "TOGGLE SHOW", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_toggle_layer_visible)
        g.button(self.DLG_X + 20, y0 + 212, self.DLG_W - 40, 36, "DELETE LAYER", fg=WHITE, bg=RED, font=1,
                 callback=self.on_delete_layer)
        if self._layers_dialog_message:
            g.caption(self.DLG_X + self.DLG_W // 2, y0 + 258, self._layers_dialog_message,
                       fg=WHITE, bg=self.BLACK, font=1, just="CT")
        g.button(self.DLG_X + 20, y0 + h - 60, 130, 40, "NEW LAYER", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_new_layer)
        g.button(self.DLG_X + 170, y0 + h - 60, 130, 40, "CLOSE", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_file_list_dialog(self, g, title, action_label, action_callback):
        # shared by OPEN and DELETE -- a listbox of everything under
        # MODELS_DIR plus one action button, or a plain "none yet"
        # message with just CLOSE if there's nothing saved
        h = 240
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, title, fg=WHITE, font=2)
        saved = list_saved_models()
        self._dialog_file_names = saved
        if not saved:
            g.caption(self.DLG_X + self.DLG_W // 2, y0 + 60, "No saved files yet",
                      fg=WHITE, bg=self.BLACK, font=1, just="CT")
            g.button(self.DLG_X + 100, y0 + 180, 120, 40, "CLOSE", fg=WHITE, bg=BTN, font=2,
                     callback=self.on_cancel_dialog)
            return
        self._dialog_selected_name = saved[0]
        self.dialog_list = g.listbox(self.DLG_X + 20, y0 + 40, self.DLG_W - 40, 120, saved, 0,
                                      font=1, callback=self.on_pick_dialog_file)
        g.button(self.DLG_X + 20, y0 + 180, 120, 40, action_label, fg=WHITE, bg=BTN, font=2,
                 callback=action_callback)
        g.button(self.DLG_X + 180, y0 + 180, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_open_dialog(self, g):
        self._build_file_list_dialog(g, "OPEN", "OPEN", self.on_confirm_open)

    def _build_delete_dialog(self, g):
        self._build_file_list_dialog(g, "DELETE", "DELETE", self.on_confirm_delete)

    def on_pick_dialog_file(self, c):
        i = c.value
        if 0 <= i < len(self._dialog_file_names):
            self._dialog_selected_name = self._dialog_file_names[i]

    # --- template wireframes -----------------------------------------

    def _build_template_dialog(self, g):
        h = 300
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "TEMPLATE", fg=WHITE, font=2)

        ly = y0 + 44
        main_label = self.template_main_name if self.template_main_name else "(none)"
        g.caption(self.DLG_X + 20, ly, "MAIN: " + main_label, fg=WHITE, bg=self.BLACK, font=1)
        ly += 24
        local_label = self.template_local_name if self.template_local_name else "(none)"
        g.caption(self.DLG_X + 20, ly, "LOCAL: " + local_label, fg=WHITE, bg=self.BLACK, font=1)

        ly += 36
        g.button(self.DLG_X + 20, ly, 130, 36, "PICK MAIN", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_open_template_pick_main)
        g.button(self.DLG_X + 170, ly, 130, 36, "PICK LOCAL", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_open_template_pick_local)

        ly += 46
        g.button(self.DLG_X + 20, ly, 130, 36, "NEW", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_open_template_new)
        g.button(self.DLG_X + 170, ly, 130, 36, "DELETE", fg=WHITE, bg=RED, font=1,
                 callback=self.on_open_template_delete)

        if self._template_dialog_message:
            g.caption(self.DLG_X + self.DLG_W // 2, ly + 46, self._template_dialog_message,
                       fg=WHITE, bg=self.BLACK, font=1, just="CT")

        g.button(self.DLG_X + 20, y0 + h - 50, self.DLG_W - 40, 36, "CLOSE", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_wireframe_list_dialog(self, g, title, action_label, action_callback):
        # mirrors _build_file_list_dialog, but lists saved templates
        # (list_saved_wireframes) instead of models, and CANCEL returns
        # to the TEMPLATE manager dialog rather than the main panel
        h = 240
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, title, fg=WHITE, font=2)
        saved = list_saved_wireframes()
        self._dialog_file_names = saved
        if not saved:
            g.caption(self.DLG_X + self.DLG_W // 2, y0 + 60, "No saved templates yet",
                      fg=WHITE, bg=self.BLACK, font=1, just="CT")
            g.button(self.DLG_X + 100, y0 + 180, 120, 40, "CLOSE", fg=WHITE, bg=BTN, font=2,
                     callback=self.on_cancel_to_template)
            return
        self._dialog_selected_name = saved[0]
        self.dialog_list = g.listbox(self.DLG_X + 20, y0 + 40, self.DLG_W - 40, 120, saved, 0,
                                      font=1, callback=self.on_pick_dialog_file)
        g.button(self.DLG_X + 20, y0 + 180, 120, 40, action_label, fg=WHITE, bg=BTN, font=2,
                 callback=action_callback)
        g.button(self.DLG_X + 180, y0 + 180, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_to_template)

    def _build_template_new_dialog(self, g):
        h = 400
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "NEW TEMPLATE", fg=WHITE, font=2)

        if self._template_new_pending:
            name_str, size_str, spacing_str, scale_str = self._template_new_pending
            self._template_new_pending = None
        else:
            name_str, size_str, spacing_str, scale_str = "", "1000", "100", "1"

        ly = y0 + 36
        g.caption(self.DLG_X + 20, ly + 6, "Name:", fg=WHITE, bg=self.BLACK, font=1)
        self.template_new_name_box = g.textbox(self.DLG_X + 130, ly, 160, 26, name_str, font=1)

        ly += 38
        g.caption(self.DLG_X + 20, ly + 6, "Size (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.template_new_size_box = g.textbox(self.DLG_X + 130, ly, 100, 26, size_str, font=1)

        ly += 38
        g.caption(self.DLG_X + 20, ly + 6, "Spacing (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.template_new_spacing_box = g.textbox(self.DLG_X + 130, ly, 100, 26, spacing_str, font=1)

        ly += 38
        g.caption(self.DLG_X + 20, ly + 6, "Scale factor:", fg=WHITE, bg=self.BLACK, font=1)
        self.template_new_scale_box = g.textbox(self.DLG_X + 130, ly, 100, 26, scale_str, font=1)

        ly += 44
        centerlines_label = "CTR LINES: ON" if self._template_new_centerlines else "CTR LINES: OFF"
        g.button(self.DLG_X + 20, ly, 140, 32, centerlines_label, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_toggle_new_centerlines)

        ly += 40
        xy_label = "XY: ON" if self._template_new_xy else "XY: OFF"
        g.button(self.DLG_X + 20, ly, 90, 32, xy_label, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_toggle_new_xy)
        xz_label = "XZ: ON" if self._template_new_xz else "XZ: OFF"
        g.button(self.DLG_X + 115, ly, 90, 32, xz_label, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_toggle_new_xz)
        yz_label = "YZ: ON" if self._template_new_yz else "YZ: OFF"
        g.button(self.DLG_X + 210, ly, 90, 32, yz_label, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_toggle_new_yz)

        if self._template_dialog_message:
            g.caption(self.DLG_X + self.DLG_W // 2, ly + 38, self._template_dialog_message,
                       fg=WHITE, bg=self.BLACK, font=1, just="CT")

        g.button(self.DLG_X + 20, y0 + h - 50, 120, 40, "SAVE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_template_new)
        g.button(self.DLG_X + 180, y0 + h - 50, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_to_template)

    def on_cancel_to_template(self, b):
        self.dialog = "template"
        self._template_dialog_message = ""
        self._redraw()

    def on_open_template_pick_main(self, b):
        self.dialog = "template_pick_main"
        self._redraw()

    def on_open_template_pick_local(self, b):
        self.dialog = "template_pick_local"
        self._redraw()

    def on_open_template_delete(self, b):
        self.dialog = "template_delete"
        self._redraw()

    def on_open_template_new(self, b):
        self._template_new_pending = None
        self._template_new_centerlines = True
        self._template_new_xy = True
        self._template_new_xz = True
        self._template_new_yz = True
        self._template_dialog_message = ""
        self.dialog = "template_new"
        self._redraw()

    def on_confirm_pick_main(self, b):
        name = getattr(self, "_dialog_selected_name", None)
        self.dialog = "template"
        if not name:
            self._redraw()
            return
        self.template_main_name = name
        self.template_main = self._safe_load_wireframe(name)
        save_template_active(self.template_main_name, self.template_local_name)
        self._redraw()

    def on_confirm_pick_local(self, b):
        name = getattr(self, "_dialog_selected_name", None)
        self.dialog = "template"
        if not name:
            self._redraw()
            return
        self.template_local_name = name
        self.template_local = self._safe_load_wireframe(name)
        save_template_active(self.template_main_name, self.template_local_name)
        self._redraw()

    def on_confirm_delete_template(self, b):
        name = getattr(self, "_dialog_selected_name", None)
        self.dialog = "template"
        if not name:
            self._redraw()
            return
        delete_wireframe_file(name)
        # if the deleted template was active in either slot, clear that
        # slot too rather than leaving a dangling name pointing nowhere
        if self.template_main_name == name:
            self.template_main_name = None
            self.template_main = None
        if self.template_local_name == name:
            self.template_local_name = None
            self.template_local = None
        save_template_active(self.template_main_name, self.template_local_name)
        self._template_dialog_message = "Deleted " + name
        self._redraw()

    def on_toggle_new_centerlines(self, b):
        self._stash_template_new_fields()
        self._template_new_centerlines = not self._template_new_centerlines
        self._redraw_dialog_in_place()

    def on_toggle_new_xy(self, b):
        self._stash_template_new_fields()
        self._template_new_xy = not self._template_new_xy
        self._redraw_dialog_in_place()

    def on_toggle_new_xz(self, b):
        self._stash_template_new_fields()
        self._template_new_xz = not self._template_new_xz
        self._redraw_dialog_in_place()

    def on_toggle_new_yz(self, b):
        self._stash_template_new_fields()
        self._template_new_yz = not self._template_new_yz
        self._redraw_dialog_in_place()

    def _stash_template_new_fields(self):
        # preserves whatever's currently typed across the redraw a
        # toggle button triggers -- same problem/fix as GRID's own
        # plane-cycle button (see on_cycle_grid_plane)
        self._template_new_pending = (
            self.template_new_name_box.value, self.template_new_size_box.value,
            self.template_new_spacing_box.value, self.template_new_scale_box.value)

    def on_confirm_template_new(self, b):
        name = self.template_new_name_box.value.strip()
        if not name:
            self._template_dialog_message = "Name can't be empty"
            self._redraw_dialog_in_place()
            return

        def parse(box, fallback):
            try:
                v = float(box.value)
                return v if v > 0 else fallback
            except (ValueError, TypeError):
                return fallback
        size = parse(self.template_new_size_box, 1000.0)
        spacing = parse(self.template_new_spacing_box, 100.0)
        scale = parse(self.template_new_scale_box, 1.0)
        # spacing/size scale together, so the dot-count check only
        # needs the unscaled ratio -- scale can't push it over the cap
        n = int(size / spacing)
        dot_count = (n + 1) ** 2
        if n < 1:
            self._template_dialog_message = "size must be at least as large as spacing"
            self._redraw_dialog_in_place()
            return
        if dot_count > self.GRID_MAX_DOTS:
            self._template_dialog_message = "%d points is too many (max %d)" % (dot_count, self.GRID_MAX_DOTS)
            self._redraw_dialog_in_place()
            return
        cfg = (size, spacing, scale, self._template_new_centerlines,
               self._template_new_xy, self._template_new_xz, self._template_new_yz)
        save_wireframe_file(name, cfg)
        self.dialog = "template"
        self._template_dialog_message = "Saved " + name
        self._redraw()

    def on_confirm_newfile(self, b):
        def parse(box, fallback):
            try:
                v = float(box.value)
                return v if v > 0 else fallback
            except (ValueError, TypeError):
                return fallback
        x = parse(self.newfile_x_box, 100.0)
        y = parse(self.newfile_y_box, 60.0)
        z = parse(self.newfile_z_box, 40.0)
        self._push_undo()
        # NEW FILE starts completely fresh, not just a new box on top
        # of whatever else was already there
        # NEW FILE also resets layers back to a single default one --
        # the new box always lands on it
        self.boxes = [((0.0, 0.0, 0.0), (x, y, z), "Layer1")]
        self.lines = []
        self.circles = []
        self.arcs = []
        self.grid = None
        self.layers = ["Layer1"]
        self.current_layer = "Layer1"
        self.layer_visible = {"Layer1": True}
        self.selected = None
        self.dialog = None
        self._redraw()
        self.status_box.value = "NEW FILE: %g x %g x %g mm box" % (x, y, z)

    def on_confirm_saveas(self, b):
        name = (self.saveas_box.value or "").strip()
        self.dialog = None
        self._redraw()
        if not name:
            self.status_box.value = "SAVE AS cancelled -- no name entered"
            return
        self.model_name = name
        try:
            path = save_model_file(name, self.boxes, self.lines, self.circles, self.arcs, self.grid,
                                    self.layers, self.layer_visible)
            self.status_box.value = "Saved to " + path
        except Exception as e:
            self.status_box.value = "SAVE AS failed: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage SAVE AS error: " + type(e).__name__ + " " + str(e))

    def _model_to_stl_triangles(self, strut_half_width):
        # only what's actually modelled, and only from visible layers
        # (matching the on-screen view) -- never GRID or the template
        # wireframes, both explicitly not part of the real model
        triangles = []
        for c0, c1, layer in self.boxes:
            if not self.layer_visible.get(layer, True):
                continue
            triangles.extend(_box_triangles(c0, c1))
        for p0, p1, layer in self.lines:
            if not self.layer_visible.get(layer, True):
                continue
            triangles.extend(_strut_triangles(p0, p1, strut_half_width))
        for center, radius, plane, layer in self.circles:
            if not self.layer_visible.get(layer, True):
                continue
            segments = 32
            pts = [self._circle_point(center, radius, plane, 360.0 * i / segments) for i in range(segments)]
            for i in range(segments):
                triangles.extend(_strut_triangles(pts[i], pts[(i + 1) % segments], strut_half_width))
        for center, radius, plane, a0, a1, layer in self.arcs:
            if not self.layer_visible.get(layer, True):
                continue
            sweep = a1 - a0
            segments = max(3, int(round(32 * abs(sweep) / 360.0)))
            pts = [self._circle_point(center, radius, plane, a0 + sweep * i / segments)
                   for i in range(segments + 1)]
            for i in range(segments):
                triangles.extend(_strut_triangles(pts[i], pts[i + 1], strut_half_width))
        return triangles

    def on_confirm_export_stl(self, b):
        name = (self.saveas_box.value or "").strip()
        try:
            thickness = float(self.stl_thickness_box.value)
            if thickness <= 0:
                thickness = 4.0
        except (ValueError, TypeError):
            thickness = 4.0
        self.stl_strut_thickness = thickness
        self.dialog = None
        self._redraw()
        if not name:
            self.status_box.value = "EXPORT STL cancelled -- no name entered"
            return
        try:
            triangles = self._model_to_stl_triangles(thickness / 2.0)
            if not triangles:
                self.status_box.value = "EXPORT STL: nothing visible to export"
                return
            path = save_stl_file(name, triangles)
            self.status_box.value = "Exported %d triangles to %s" % (len(triangles), name + ".stl")
        except Exception as e:
            self.status_box.value = "EXPORT STL failed: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage EXPORT STL error: " + type(e).__name__ + " " + str(e))

    def on_confirm_open(self, b):
        # load THEN redraw, not the other way round -- redrawing first
        # (like the other dialog confirms do) would rebuild the scene
        # from the OLD model, before the load below ever runs, so the
        # file would load into memory but never actually appear
        name = getattr(self, "_dialog_selected_name", None)
        self.dialog = None
        if not name:
            self._redraw()
            self.status_box.value = "OPEN: nothing selected"
            return
        try:
            boxes, lines, circles, arcs, grid, layers, layer_visible = load_model_file(name)
            self._push_undo()
            self.boxes = boxes
            self.lines = lines
            self.circles = circles
            self.arcs = arcs
            self.grid = grid
            self.layers = layers
            self.layer_visible = layer_visible
            self.current_layer = layers[0]
            self.selected = None
            self.model_name = name
            self._redraw()
            self.status_box.value = "Opened " + name
        except Exception as e:
            self._redraw()
            self.status_box.value = "OPEN failed: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage OPEN error: " + type(e).__name__ + " " + str(e))

    def on_confirm_delete(self, b):
        name = getattr(self, "_dialog_selected_name", None)
        self.dialog = None
        self._redraw()
        if not name:
            self.status_box.value = "DELETE: nothing selected"
            return
        if delete_model_file(name):
            self.status_box.value = "Deleted " + name
        else:
            self.status_box.value = "DELETE failed for " + name

    def _read_line_point(self):
        def parse(box):
            try:
                v = float(box.value)
            except (ValueError, TypeError):
                v = 0.0
            return self._snap_to_grid(v)
        return (parse(self.line_x_box), parse(self.line_y_box), parse(self.line_z_box))

    def on_line_choice_click(self, b):
        self.line_stage = "start"
        self.dialog = "line_pick"
        self._redraw()

    def on_line_choice_type(self, b):
        self.line_stage = "start"
        self.dialog = "line"
        self._redraw()

    def on_box_choice_click(self, b):
        self.box_pick_start = None
        self.dialog = "box_pick"
        self._redraw()

    def on_box_choice_type(self, b):
        self.box_stage = "start"
        self.dialog = "box"
        self._redraw()

    def on_line_next(self, b):
        self.line_start_point = self._read_line_point()
        self.line_stage = "end"
        self._redraw()

    def on_line_create(self, b):
        end_point = self._read_line_point()
        self._push_undo()
        self.lines.append((self.line_start_point, end_point, self.current_layer))
        self.dialog = None
        self.line_stage = "start"
        self._redraw()
        self.status_box.value = "LINE: %s to %s" % (self.line_start_point, end_point)

    def _read_box_point(self):
        def parse(box):
            try:
                v = float(box.value)
            except (ValueError, TypeError):
                v = 0.0
            return self._snap_to_grid(v)
        return (parse(self.box_x_box), parse(self.box_y_box), parse(self.box_z_box))

    def on_box_next(self, b):
        self.box_start_point = self._read_box_point()
        self.box_stage = "end"
        self._redraw()

    def on_box_create(self, b):
        p1 = self.box_start_point
        p2 = self._read_box_point()
        # sorted into (min corner, max corner) so it doesn't matter
        # which of the two opposite corners was entered first
        corner_min = (min(p1[0], p2[0]), min(p1[1], p2[1]), min(p1[2], p2[2]))
        corner_max = (max(p1[0], p2[0]), max(p1[1], p2[1]), max(p1[2], p2[2]))
        self._push_undo()
        self.boxes.append((corner_min, corner_max, self.current_layer))
        self.dialog = None
        self.box_stage = "start"
        self._redraw()
        self.status_box.value = "BOX: %s to %s" % (corner_min, corner_max)

    def on_cycle_circle_plane(self, b):
        self._circle_radius_pending = self.circle_r_box.value
        order = ("XY", "XZ", "YZ")
        self.circle_plane = order[(order.index(self.circle_plane) + 1) % 3]
        self._redraw()

    def on_toggle_circle_snap(self, b):
        self._circle_radius_pending = self.circle_r_box.value
        self.snap_enabled = not self.snap_enabled
        self._redraw()

    def on_confirm_circle(self, b):
        # only the radius is typed -- confirming this hands off to
        # circle_pick, where the centre is placed by clicking in VIEW
        # (with a live snap preview), not typed
        def parse(box, fallback):
            try:
                v = float(box.value)
            except (ValueError, TypeError):
                v = fallback
            return self._snap_to_grid(v)
        r = parse(self.circle_r_box, 20.0)
        if r <= 0:
            r = 20.0
        r = self._snap_length_to_grid(r)
        self._circle_pick_radius = r
        self.dialog = "circle_pick"
        self._redraw()

    def _circle_centerline_segments(self, center, radius, plane):
        # a technical-drawing-style center mark -- two short reference
        # lines through the circle's centre, along the plane's two
        # axes, extending a little past the circle's own edge so they
        # read as a crosshair rather than getting lost inside the
        # circle outline. Added as ordinary lines (own layer tag, own
        # SELECT/DELETE entry) rather than a special element kind.
        i, j = self.PLANE_AXES[plane]
        arm = radius * 1.3
        p0, p1 = list(center), list(center)
        p0[i] -= arm
        p1[i] += arm
        p2, p3 = list(center), list(center)
        p2[j] -= arm
        p3[j] += arm
        return ((tuple(p0), tuple(p1)), (tuple(p2), tuple(p3)))

    def on_cycle_arc_plane(self, b):
        order = ("XY", "XZ", "YZ")
        self.arc_plane = order[(order.index(self.arc_plane) + 1) % 3]
        self._redraw()

    def on_confirm_arc(self, b):
        def parse(box, fallback):
            try:
                v = float(box.value)
            except (ValueError, TypeError):
                v = fallback
            return self._snap_to_grid(v)
        cx = parse(self.arc_cx_box, 0.0)
        cy = parse(self.arc_cy_box, 0.0)
        cz = parse(self.arc_cz_box, 0.0)
        r = parse(self.arc_r_box, 20.0)
        if r <= 0:
            r = 20.0
        r = self._snap_length_to_grid(r)
        a0 = parse(self.arc_start_box, 0.0)
        a1 = parse(self.arc_end_box, 90.0)
        self._push_undo()
        self.arcs.append(((cx, cy, cz), r, self.arc_plane, a0, a1, self.current_layer))
        self.dialog = None
        self._redraw()
        self.status_box.value = "ARC: centre (%g,%g,%g) r=%g %s %g to %g deg" % (cx, cy, cz, r, self.arc_plane, a0, a1)

    def on_cycle_grid_plane(self, b):
        order = ("XY", "XZ", "YZ")
        self.grid_plane = order[(order.index(self.grid_plane) + 1) % 3]
        self._redraw()

    def on_cycle_centerline_axis(self, b):
        order = ("X", "Y", "Z")
        self.centerline_axis = order[(order.index(self.centerline_axis) + 1) % 3]
        self._redraw()

    def _snap_to_grid(self, value):
        # rounds any typed number (not a click position -- see
        # _snap_to_grid_point for that) to the nearest multiple of the
        # current GRID's spacing, if any -- applied to every numeric
        # field across every typed-entry dialog (BOX/LINE points,
        # CIRCLE/ARC centres and radius, ARC's angles, CTR LINE's
        # length), not just positions
        if not self.grid or not self.snap_enabled:
            return value
        spacing = self.grid[1]
        if spacing <= 0:
            return value
        return round(value / spacing) * spacing

    def _snap_length_to_grid(self, length):
        # like _snap_to_grid, but guarantees a positive result -- for
        # lengths/radii, which can't be zero or negative, so it falls
        # back to one full spacing unit rather than 0 if rounding would
        # otherwise collapse a short length to nothing
        snapped = self._snap_to_grid(length)
        return snapped if snapped > 0 else (self.grid[1] if self.grid else length)

    def on_confirm_centerline(self, b):
        try:
            length = float(self.centerline_len_box.value)
            if length <= 0:
                length = 100.0
        except (ValueError, TypeError):
            length = 100.0
        length = self._snap_length_to_grid(length)
        d = self.AXIS_DIRS[self.centerline_axis]
        half = length / 2.0
        p0 = (-half * d[0], -half * d[1], -half * d[2])
        p1 = (half * d[0], half * d[1], half * d[2])
        self._push_undo()
        self.lines.append((p0, p1, self.current_layer))
        self.dialog = None
        self._redraw()
        self.status_box.value = "CTR LINE: %s axis, %g mm" % (self.centerline_axis, length)

    def on_confirm_grid(self, b):
        def parse(box, fallback):
            try:
                v = float(box.value)
                return v if v > 0 else fallback
            except (ValueError, TypeError):
                return fallback
        spacing = parse(self.grid_spacing_box, 10.0)
        extent_i = parse(self.grid_extent_i_box, 100.0)
        extent_j = parse(self.grid_extent_j_box, 100.0)
        try:
            position = float(self.grid_position_box.value)
        except (ValueError, TypeError):
            position = 0.0
        if self.snap_enabled and spacing > 0:
            # snap to the spacing just typed in this dialog, not
            # self.grid's (old) spacing -- self.grid isn't updated
            # until below, so _snap_to_grid would use stale spacing
            position = round(position / spacing) * spacing
        ni = int(extent_i / spacing)
        nj = int(extent_j / spacing)
        self.dialog = None
        if ni < 1 or nj < 1:
            # either extent smaller than spacing -- collapses that axis
            # to a single dot at the origin, which is exactly the
            # "always points at zero" bug this guards
            self._redraw()
            self.status_box.value = "GRID: both extents must be at least as large as spacing"
            return
        dot_count = (ni + 1) * (nj + 1)
        if dot_count > self.GRID_MAX_DOTS:
            self._redraw()
            self.status_box.value = ("GRID: %d points is too many (max %d) -- "
                                      "use a bigger spacing or smaller extent" % (dot_count, self.GRID_MAX_DOTS))
            return
        self._push_undo()
        self.grid = (self.grid_plane, spacing, extent_i, extent_j, position)
        self._redraw()
        axis_name = self.AXIS_NAMES[self._plane_normal_axis(self.grid_plane)]
        self.status_box.value = "GRID: %s, %g mm spacing, %gx%g mm extent, %s=%g" % (
            self.grid_plane, spacing, extent_i, extent_j, axis_name, position)

    def on_open_layers(self, b):
        self._dialog_selected_layer = self.current_layer
        self._layers_dialog_message = ""
        self.dialog = "layers"
        self._redraw()

    def on_pick_layer(self, c):
        i = c.value
        if 0 <= i < len(self.layers):
            self._dialog_selected_layer = self.layers[i]
            self._layers_dialog_message = ""

    def on_set_active_layer(self, b):
        self.current_layer = self._dialog_selected_layer
        self._redraw_dialog_in_place()

    def on_toggle_layer_visible(self, b):
        name = self._dialog_selected_layer
        self.layer_visible[name] = not self.layer_visible.get(name, True)
        self._redraw_dialog_in_place()

    def on_new_layer(self, b):
        i = 2
        while ("Layer%d" % i) in self.layers:
            i += 1
        name = "Layer%d" % i
        self._push_undo()
        self.layers.append(name)
        self.layer_visible[name] = True
        self._dialog_selected_layer = name
        self._layers_dialog_message = ""
        self._redraw_dialog_in_place()

    def _layer_item_count(self, name):
        # how many boxes/lines/circles/arcs are tagged with this layer
        # -- used to block deleting a layer out from under real items
        # rather than silently orphaning their layer tag
        count = 0
        for box in self.boxes:
            if box[2] == name:
                count += 1
        for line in self.lines:
            if line[2] == name:
                count += 1
        for circle in self.circles:
            if circle[3] == name:
                count += 1
        for arc in self.arcs:
            if arc[5] == name:
                count += 1
        return count

    def on_delete_layer(self, b):
        name = self._dialog_selected_layer
        if len(self.layers) <= 1:
            self._layers_dialog_message = "Can't delete the only layer"
            self._redraw_dialog_in_place()
            return
        count = self._layer_item_count(name)
        if count > 0:
            self._layers_dialog_message = "%d item%s still on this layer" % (
                count, "" if count == 1 else "s")
            self._redraw_dialog_in_place()
            return
        self._push_undo()
        self.layers.remove(name)
        self.layer_visible.pop(name, None)
        if self.current_layer == name:
            self.current_layer = self.layers[0]
        self._dialog_selected_layer = self.current_layer
        self._layers_dialog_message = ""
        self._redraw_dialog_in_place()

    def _redraw_dialog_in_place(self):
        # LAYERS' own buttons stay on this dialog after acting (unlike
        # every other dialog's confirm, which closes back to the main
        # panel) -- SET ACTIVE/TOGGLE SHOW/NEW LAYER are all things
        # you'd plausibly do several of in a row
        self._redraw()

    def on_cancel_dialog(self, b):
        self.dialog = None
        self.line_stage = "start"
        self.box_stage = "start"
        self.box_pick_start = None
        self._redraw()

    def _make_command_handler(self, name):
        # closure factory, same pattern CalculatorPage uses for its key
        # grid -- one handler per command without writing out a
        # separate on_xxx method for each of these
        def handler(b):
            self.on_command(name)
        return handler

    def on_command(self, name):
        self.active_command = name
        if name == "LINE":
            self.line_stage = "start"
        elif name == "BOX":
            self.box_stage = "start"
            self.box_pick_start = None
        elif name == "DELETE" and self.selected is not None:
            # DELETE means "delete the selected item" whenever SELECT
            # has one highlighted -- only falls back to the saved-file
            # list below once nothing's currently selected
            self._delete_selected()
            return
        elif name == "GRID" and self.grid:
            # pre-fill the plane toggle from the actual current grid,
            # not whatever was last left over from a previous (possibly
            # cancelled) visit to this dialog
            self.grid_plane = self.grid[0]
        elif name == "TEMPLATE":
            self._template_dialog_message = ""
        target = self.COMMAND_DIALOG.get(name)
        if target is None:
            # shouldn't happen -- every current COMMANDS entry has a
            # COMMAND_DIALOG entry -- but fail safely rather than
            # silently if a future command gets added and forgotten
            self._redraw()
            self.status_box.value = "Pressed: " + name
            ulog("Model3DPage: command pressed: " + name)
            return
        self.dialog = target
        self._redraw()

    def _delete_selected(self):
        kind, idx = self.selected
        collection = {"box": self.boxes, "line": self.lines,
                      "circle": self.circles, "arc": self.arcs}[kind]
        self._push_undo()
        del collection[idx]
        self.selected = None
        self.dialog = None
        self._redraw()
        self.status_box.value = "DELETE: removed %s #%d (undoable)" % (kind.upper(), idx + 1)

    def _in_canvas(self, x, y):
        return self.CANVAS_X0 <= x <= self.CANVAS_X1 and self.CANVAS_Y0 <= y <= self.CANVAS_Y1

    def _screen_to_plane_point(self, sx, sy, plane):
        # inverts _project(), assuming the point actually lies on
        # `plane` -- a single 2D screen point can't otherwise be turned
        # back into a 3D one. Uses whatever scale/origin the VIEW panel
        # was last drawn with. The third axis is 0 by default, unless
        # the active GRID is on this same plane and has a non-zero
        # position, in which case the point lands on the grid instead
        # (matching what's actually drawn -- see _draw_grid_dots).
        #
        # Solved generically rather than with a per-plane formula, so
        # it keeps working at any azimuth/elevation: `plane`'s two
        # world-space basis vectors are themselves projected (giving
        # the 2x2 Jacobian from plane-space (a,b) to screen pixels),
        # then that's inverted to recover (a,b) for this click.
        scale = self._last_scale or 1.0
        ox, oy = self._last_origin
        normal_offset = 0.0
        if self.grid and self.grid[0] == plane:
            normal_offset = self.grid[4]  # (plane, spacing, extent_i, extent_j, position)
        offset_x = offset_y = 0.0
        if normal_offset:
            k = self._plane_normal_axis(plane)
            off_vec = [0.0, 0.0, 0.0]
            off_vec[k] = normal_offset
            offset_x, offset_y = self._raw_project(off_vec[0], off_vec[1], off_vec[2])
        rsx = (sx - ox) / scale - offset_x
        rsy = (sy - oy) / scale - offset_y
        u, v = self.PLANE_BASIS[plane]
        ux, uy = self._raw_project(u[0], u[1], u[2])
        vx, vy = self._raw_project(v[0], v[1], v[2])
        det = ux * vy - vx * uy
        if -1e-9 < det < 1e-9:
            # near edge-on view of this plane at the current rotation --
            # nudge off zero rather than divide by it; the result will
            # be a poor (likely large) estimate, but GRID snapping
            # clamps it back into range rather than blowing up
            det = 1e-9 if det >= 0 else -1e-9
        a = (rsx * vy - vx * rsy) / det
        b = (ux * rsy - rsx * uy) / det
        p = [0.0, 0.0, 0.0]
        for coeff, vec in ((a, u), (b, v)):
            for i in range(3):
                p[i] += coeff * vec[i]
        if normal_offset:
            p[self._plane_normal_axis(plane)] = normal_offset
        return (p[0], p[1], p[2])

    def _snap_to_grid_point(self, point):
        if not self.grid or not self.snap_enabled:
            return point
        plane, spacing, extent_i, extent_j, position = self.grid
        i, j = self.PLANE_AXES[plane]
        k = self._plane_normal_axis(plane)
        p = list(point)
        extents = {i: extent_i, j: extent_j}
        for idx in (i, j):
            v = round(p[idx] / spacing) * spacing
            p[idx] = max(0.0, min(extents[idx], v))
        p[k] = position
        return (p[0], p[1], p[2])

    def _point_to_segment_dist(self, px, py, x0, y0, x1, y1):
        # math.sqrt, not math.hypot -- confirmed on real hardware that
        # this board's MicroPython math module doesn't implement hypot
        dx, dy = x1 - x0, y1 - y0
        if dx == 0 and dy == 0:
            ex, ey = px - x0, py - y0
            return math.sqrt(ex * ex + ey * ey)
        t = ((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        cx, cy = x0 + t * dx, y0 + t * dy
        ex, ey = px - cx, py - cy
        return math.sqrt(ex * ex + ey * ey)

    def _arc_hit_dist(self, x, y, center, radius, plane, a0, a1, scale, ox, oy, segments=32):
        # same chord approximation _draw_arc uses -- distance from
        # (x,y) to the nearest chord, so hit-testing matches what's
        # actually drawn on screen
        sweep = a1 - a0
        n = max(3, int(round(segments * abs(sweep) / 360.0)))
        prev = None
        best = None
        for i in range(n + 1):
            angle = a0 + sweep * i / n
            p3d = self._circle_point(center, radius, plane, angle)
            s = self._project(p3d[0], p3d[1], p3d[2], scale, ox, oy)
            if prev is not None:
                d = self._point_to_segment_dist(x, y, prev[0], prev[1], s[0], s[1])
                if best is None or d < best:
                    best = d
            prev = s
        return best if best is not None else 1.0e9

    def _hit_test(self, x, y):
        # nearest element (by screen-space distance to its projected
        # outline) within SELECT_THRESHOLD px of the click, or None
        scale, (ox, oy) = self._last_scale, self._last_origin
        best_dist = None
        best = None

        for bi, box in enumerate(self.boxes):
            if not self.layer_visible.get(box[2], True):
                continue
            for p1, p2 in self._box_edges(box):
                s1 = self._project(p1[0], p1[1], p1[2], scale, ox, oy)
                s2 = self._project(p2[0], p2[1], p2[2], scale, ox, oy)
                d = self._point_to_segment_dist(x, y, s1[0], s1[1], s2[0], s2[1])
                if best_dist is None or d < best_dist:
                    best_dist, best = d, ("box", bi)

        for li, (p0, p1, layer) in enumerate(self.lines):
            if not self.layer_visible.get(layer, True):
                continue
            s0 = self._project(p0[0], p0[1], p0[2], scale, ox, oy)
            s1 = self._project(p1[0], p1[1], p1[2], scale, ox, oy)
            d = self._point_to_segment_dist(x, y, s0[0], s0[1], s1[0], s1[1])
            if best_dist is None or d < best_dist:
                best_dist, best = d, ("line", li)

        for ci, (c, r, plane, layer) in enumerate(self.circles):
            if not self.layer_visible.get(layer, True):
                continue
            d = self._arc_hit_dist(x, y, c, r, plane, 0, 360, scale, ox, oy)
            if best_dist is None or d < best_dist:
                best_dist, best = d, ("circle", ci)

        for ai, (c, r, plane, a0, a1, layer) in enumerate(self.arcs):
            if not self.layer_visible.get(layer, True):
                continue
            d = self._arc_hit_dist(x, y, c, r, plane, a0, a1, scale, ox, oy)
            if best_dist is None or d < best_dist:
                best_dist, best = d, ("arc", ai)

        if best_dist is not None and best_dist <= self.SELECT_THRESHOLD:
            return best
        return None

    def _plane_point_at(self, x, y):
        # model-space position under the cursor, assuming it lies on
        # the active GRID's plane (or XY if there's no grid) and
        # snapped to that grid if one exists -- shared by the readout
        # and by actual point-picking (LINE's "CLICK ON GRID" mode)
        plane = self.grid[0] if self.grid else "XY"
        point = self._screen_to_plane_point(x, y, plane)
        point = self._snap_to_grid_point(point)
        return plane, point

    def _position_readout(self, x, y):
        if not self._in_canvas(x, y):
            return "X:--  Y:--  Z:--"
        plane, point = self._plane_point_at(x, y)
        # always show all three, not just the two the active plane
        # varies -- the third (always 0, whichever axis is fixed by
        # the plane) was implicit before and not obvious at a glance.
        # Rounded to 1dp -- without an active grid to snap to, the raw
        # inverse-projected position is a long, jittery decimal
        # (floating-point noise from the screen->model math, not
        # anything meaningful past ~1mm on a screen this size).
        return "X:%.1f  Y:%.1f  Z:%.1f" % (point[0], point[1], point[2])

    def on_touch(self, x, y):
        # g.on_touch(callback) fires with integer (x, y) screen
        # coordinates on any click/tap -- confirmed working against a
        # real USB mouse. Only registered while the main panel (not a
        # dialog) is showing -- see _build_main.
        self.touch_count += 1
        ulog("on_touch fired #%d at (%d,%d) dialog=%s" % (self.touch_count, x, y, self.dialog))
        if self.dialog == "line_pick":
            self._on_line_pick_touch(x, y)
            return
        if self.dialog == "select_pick":
            self._on_select_pick_touch(x, y)
            return
        if self.dialog == "box_pick":
            self._on_box_pick_touch(x, y)
            return
        if self.dialog == "circle_pick":
            self._on_circle_pick_touch(x, y)
            return
        #
        # DRAG CAVEAT: panning is reconstructed from on_touch rather
        # than a continuous drag hook: two on_touch calls inside the
        # VIEW canvas within DRAG_TIMEOUT_MS of each other are treated
        # as a drag, and the view pans by the difference between them.
        # Whether this actually feels like a smooth drag depends on
        # whether on_touch itself fires repeatedly while a mouse button
        # is held and moved, or only once per discrete click -- that
        # part is UNVERIFIED. If it only fires once per click, this
        # will still work, just as "click, click again elsewhere" =
        # jump the view by that offset, not a fluid drag.
        if self._in_canvas(x, y):
            now = time.ticks_ms()
            dragged = False
            if self._last_touch is not None and time.ticks_diff(now, self._last_touch_time) < self.DRAG_TIMEOUT_MS:
                dx = x - self._last_touch[0]
                dy = y - self._last_touch[1]
                if dx or dy:
                    self.pan_x += dx
                    self.pan_y += dy
                    dragged = True
            self._last_touch = (x, y)
            self._last_touch_time = now
            if dragged:
                self._redraw()
                self.mouse_box.value = self._safe_position_readout(x, y)
                return
        else:
            self._last_touch = None
        self.mouse_box.value = self._safe_position_readout(x, y)

    def _safe_position_readout(self, x, y):
        # falls back to raw pixel coords on any error instead of
        # leaving the box silently frozen -- if it shows "Mouse: (x,
        # y)" that proves on_touch IS firing and the new plane/grid
        # math is what's broken; if it shows nothing at all, on_touch
        # itself isn't firing
        try:
            text = self._position_readout(x, y)
        except Exception as e:
            ulog("Model3DPage: position readout error: " + type(e).__name__ + " " + str(e))
            text = "Mouse: (%d, %d)" % (x, y)
        return text

    def _on_line_pick_touch(self, x, y):
        # LINE's "CLICK ON GRID" mode -- two clicks in the canvas set
        # start then end; no live "follows the mouse" preview (that
        # needs on_move, which doesn't work on this hardware), so this
        # is click-click rather than click-drag-release.
        # Every branch here updates status_box directly (not just
        # ulog) so a click's outcome is visible on screen immediately,
        # not just in a log file nobody's reading live off the board.
        if not self._in_canvas(x, y):
            self.status_box.value = "LINE: click (%d,%d) was outside the VIEW panel" % (x, y)
            return
        try:
            plane, point = self._plane_point_at(x, y)
        except Exception as e:
            self.status_box.value = "LINE pick error: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage: line pick error: " + type(e).__name__ + " " + str(e))
            return
        if self.line_stage == "start":
            self.line_start_point = point
            self.line_stage = "end"
            self._redraw()
            self.status_box.value = "LINE: start point set, click END point"
        else:
            self._push_undo()
            self.lines.append((self.line_start_point, point, self.current_layer))
            end_point = point
            start_point = self.line_start_point
            self.dialog = None
            self.line_stage = "start"
            self._redraw()
            self.status_box.value = "LINE: %s to %s" % (start_point, end_point)

    def _on_box_pick_touch(self, x, y):
        # BOX's "CLICK ON GRID" mode -- mirrors _on_line_pick_touch:
        # first click sets one corner, second click sets the opposite
        # corner and creates the box (on_box_create already sorts
        # whichever two corners come in into min/max order)
        if not self._in_canvas(x, y):
            self.status_box.value = "BOX: click (%d,%d) was outside the VIEW panel" % (x, y)
            return
        try:
            plane, point = self._plane_point_at(x, y)
        except Exception as e:
            self.status_box.value = "BOX pick error: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage: box pick error: " + type(e).__name__ + " " + str(e))
            return
        if self.box_pick_start is None:
            self.box_pick_start = point
            self._redraw()
            self.status_box.value = "BOX: first corner set, click the OPPOSITE corner"
        else:
            p1, p2 = self.box_pick_start, point
            corner_min = (min(p1[0], p2[0]), min(p1[1], p2[1]), min(p1[2], p2[2]))
            corner_max = (max(p1[0], p2[0]), max(p1[1], p2[1]), max(p1[2], p2[2]))
            self._push_undo()
            self.boxes.append((corner_min, corner_max, self.current_layer))
            self.dialog = None
            self.box_pick_start = None
            self._redraw()
            self.status_box.value = "BOX: %s to %s" % (corner_min, corner_max)

    def _on_circle_pick_touch(self, x, y):
        # CIRCLE's centre-placement step -- radius/plane/snap were
        # already confirmed back in the CIRCLE dialog (see
        # on_confirm_circle), so a single click here places the centre
        # and creates the circle. _plane_point_at already applies grid
        # snapping (or not) according to SNAP TO GRID/self.snap_enabled,
        # same as every other click-to-place tool.
        if not self._in_canvas(x, y):
            self.status_box.value = "CIRCLE: click (%d,%d) was outside the VIEW panel" % (x, y)
            return
        try:
            plane, point = self._plane_point_at(x, y)
        except Exception as e:
            self.status_box.value = "CIRCLE pick error: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage: circle pick error: " + type(e).__name__ + " " + str(e))
            return
        r = self._circle_pick_radius
        self._push_undo()
        self.circles.append((point, r, self.circle_plane, self.current_layer))
        for p0, p1 in self._circle_centerline_segments(point, r, self.circle_plane):
            self.lines.append((p0, p1, self.current_layer))
        self.dialog = None
        self._redraw()
        self.status_box.value = "CIRCLE: centre %s r=%g %s" % (point, r, self.circle_plane)

    def _on_select_pick_touch(self, x, y):
        if not self._in_canvas(x, y):
            self.status_box.value = "SELECT: click (%d,%d) was outside the VIEW panel" % (x, y)
            return
        try:
            hit = self._hit_test(x, y)
        except Exception as e:
            self.status_box.value = "SELECT error: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage: select error: " + type(e).__name__ + " " + str(e))
            return
        self.selected = hit
        ulog("Model3DPage: SELECT hit=%s at click (%d,%d)" % (str(hit), x, y))
        self.dialog = None
        self._redraw()
        if hit:
            kind, idx = hit
            self.status_box.value = "SELECTED: %s #%d" % (kind.upper(), idx + 1)
        else:
            self.status_box.value = "SELECT: nothing close enough -- try clicking nearer an item"

    def on_zoom_in(self, b):
        self.zoom = min(self.zoom * self.ZOOM_STEP, self.MAX_ZOOM)
        self._redraw()

    def on_zoom_out(self, b):
        self.zoom = max(self.zoom / self.ZOOM_STEP, self.MIN_ZOOM)
        self._redraw()

    def on_reset_view(self, b):
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.azimuth_deg = self.AZIMUTH_DEFAULT
        self.elevation_deg = self.ELEVATION_DEFAULT
        self._update_rotation_trig()
        self._redraw()

    def on_rotate_az_minus(self, b):
        self.azimuth_deg = (self.azimuth_deg - self.AZIMUTH_STEP) % 360.0
        self._update_rotation_trig()
        self._redraw()

    def on_rotate_az_plus(self, b):
        self.azimuth_deg = (self.azimuth_deg + self.AZIMUTH_STEP) % 360.0
        self._update_rotation_trig()
        self._redraw()

    def on_rotate_el_minus(self, b):
        self.elevation_deg = max(self.ELEVATION_MIN, self.elevation_deg - self.ELEVATION_STEP)
        self._update_rotation_trig()
        self._redraw()

    def on_rotate_el_plus(self, b):
        self.elevation_deg = min(self.ELEVATION_MAX, self.elevation_deg + self.ELEVATION_STEP)
        self._update_rotation_trig()
        self._redraw()

    def on_toggle_wireframe(self, b):
        self.wireframe_visible = not self.wireframe_visible
        self._redraw()

    def on_toggle_grid_visible(self, b):
        self.grid_visible = not self.grid_visible
        self._redraw()

    def on_toggle_snap(self, b):
        self.snap_enabled = not self.snap_enabled
        self._redraw()

    def on_extrude_pressed(self, b):
        if self.selected is None:
            self.status_box.value = "EXTRUDE: SELECT an item first"
            return
        self.active_command = "EXTRUDE"
        self.dialog = "extrude"
        self._redraw()

    def on_confirm_extrude(self, b):
        self.dialog = None
        if self.selected is None:
            self._redraw()
            self.status_box.value = "EXTRUDE: nothing selected"
            return
        kind, idx = self.selected
        try:
            amount = float(self.extrude_amount_box.value)
        except (ValueError, TypeError):
            amount = 0.0
        if amount <= 0:
            amount = 50.0
        amount = self._snap_length_to_grid(amount)
        try:
            if kind == "line":
                p0, p1, layer = self.lines[idx]
            elif kind == "box":
                c0, c1, layer = self.boxes[idx]
            elif kind == "circle":
                center, radius, plane, layer = self.circles[idx]
            else:
                center, radius, plane, a0, a1, layer = self.arcs[idx]
        except IndexError:
            self._redraw()
            self.status_box.value = "EXTRUDE: that item no longer exists"
            return
        self._push_undo()
        if kind == "line":
            # turns a line into a rectangular wall outline: the
            # original line stays as the bottom edge, a copy raised by
            # `amount` in Z becomes the top edge, plus two verticals
            # closing the ends -- all ordinary LINE entries, no new
            # element kind needed
            top0 = (p0[0], p0[1], p0[2] + amount)
            top1 = (p1[0], p1[1], p1[2] + amount)
            self.lines.append((top0, top1, layer))
            self.lines.append((p0, top0, layer))
            self.lines.append((p1, top1, layer))
            self.status_box.value = "EXTRUDE: line raised into a %gmm wall" % amount
        elif kind == "box":
            self.boxes[idx] = (c0, (c1[0], c1[1], c1[2] + amount), layer)
            self.status_box.value = "EXTRUDE: box height increased by %gmm" % amount
        elif kind == "circle":
            # sweeps the circle along its plane's normal axis into a
            # cylinder outline: the original stays as the bottom
            # circle, a copy offset by `amount` becomes the top circle,
            # with a few verticals connecting them -- all ordinary
            # CIRCLE/LINE entries, no new element kind needed
            axis = self._plane_normal_axis(plane)
            top_center = list(center)
            top_center[axis] += amount
            top_center = tuple(top_center)
            self.circles.append((top_center, radius, plane, layer))
            for angle in (0, 90, 180, 270):
                pb = self._circle_point(center, radius, plane, angle)
                pt = self._circle_point(top_center, radius, plane, angle)
                self.lines.append((pb, pt, layer))
            self.status_box.value = "EXTRUDE: circle swept into a %gmm cylinder" % amount
        else:
            # same idea as circle, but only the two ends of the arc get
            # a connecting vertical, matching a LINE's wall ends
            axis = self._plane_normal_axis(plane)
            top_center = list(center)
            top_center[axis] += amount
            top_center = tuple(top_center)
            self.arcs.append((top_center, radius, plane, a0, a1, layer))
            for angle in (a0, a1):
                pb = self._circle_point(center, radius, plane, angle)
                pt = self._circle_point(top_center, radius, plane, angle)
                self.lines.append((pb, pt, layer))
            self.status_box.value = "EXTRUDE: arc swept into a %gmm curved wall" % amount
        self.selected = None
        self._redraw()

    def on_edit_pressed(self, b):
        if self.selected is None:
            self.status_box.value = "EDIT: SELECT an item first"
            return
        self.active_command = "EDIT"
        self.dialog = "edit"
        self._redraw()

    def on_edit_delete(self, b):
        if self.selected is None:
            self.dialog = None
            self._redraw()
            self.status_box.value = "EDIT: nothing selected"
            return
        self._delete_selected()

    def on_confirm_edit(self, b):
        self.dialog = None
        if self.selected is None:
            self._redraw()
            self.status_box.value = "EDIT: nothing selected"
            return
        kind, idx = self.selected

        def parse(box, fallback):
            try:
                v = float(box.value)
            except (ValueError, TypeError):
                v = fallback
            return self._snap_to_grid(v)

        try:
            fields = self._edit_fields()
        except (IndexError, ValueError):
            self._redraw()
            self.status_box.value = "EDIT: that item no longer exists"
            return
        values = [parse(box, default) for box, (label, default) in zip(self.edit_boxes, fields)]

        self._push_undo()
        if kind == "line":
            layer = self.lines[idx][2]
            self.lines[idx] = ((values[0], values[1], values[2]), (values[3], values[4], values[5]), layer)
            self.status_box.value = "EDIT: LINE #%d updated" % (idx + 1)
        elif kind == "box":
            layer = self.boxes[idx][2]
            p0 = (values[0], values[1], values[2])
            p1 = (values[3], values[4], values[5])
            corner_min = (min(p0[0], p1[0]), min(p0[1], p1[1]), min(p0[2], p1[2]))
            corner_max = (max(p0[0], p1[0]), max(p0[1], p1[1]), max(p0[2], p1[2]))
            self.boxes[idx] = (corner_min, corner_max, layer)
            self.status_box.value = "EDIT: BOX #%d updated" % (idx + 1)
        elif kind == "circle":
            _, old_r, plane, layer = self.circles[idx]
            r = self._snap_length_to_grid(values[3] if values[3] > 0 else old_r)
            self.circles[idx] = ((values[0], values[1], values[2]), r, plane, layer)
            self.status_box.value = "EDIT: CIRCLE #%d updated" % (idx + 1)
        else:  # arc
            _, old_r, plane, old_a0, old_a1, layer = self.arcs[idx]
            r = self._snap_length_to_grid(values[3] if values[3] > 0 else old_r)
            self.arcs[idx] = ((values[0], values[1], values[2]), r, plane, values[4], values[5], layer)
            self.status_box.value = "EDIT: ARC #%d updated" % (idx + 1)
        self._redraw()

    def _model_snapshot(self):
        return (list(self.boxes), list(self.lines), list(self.circles), list(self.arcs), self.grid,
                list(self.layers), dict(self.layer_visible), self.current_layer)

    def _restore_snapshot(self, snapshot):
        (self.boxes, self.lines, self.circles, self.arcs, self.grid,
         self.layers, self.layer_visible, self.current_layer) = snapshot

    def _push_undo(self):
        # call BEFORE mutating the model -- captures the state to go
        # back to, and a fresh action means any old redo history no
        # longer makes sense
        self.undo_stack.append(self._model_snapshot())
        if len(self.undo_stack) > self.UNDO_MAX:
            self.undo_stack.pop(0)
        self.redo_stack = []

    def on_undo(self, b):
        if not self.undo_stack:
            self.status_box.value = "UNDO: nothing to undo"
            return
        self.redo_stack.append(self._model_snapshot())
        self._restore_snapshot(self.undo_stack.pop())
        # self.selected is a (kind, index) pair into boxes/lines/
        # circles/arcs -- snapshots don't carry selection, so that
        # index can easily point at a different item (or nothing) once
        # the lists it indexes into have just changed underneath it
        self.selected = None
        self._redraw()
        self.status_box.value = "Undone"

    def on_redo(self, b):
        if not self.redo_stack:
            self.status_box.value = "REDO: nothing to redo"
            return
        self.undo_stack.append(self._model_snapshot())
        self._restore_snapshot(self.redo_stack.pop())
        self.selected = None
        self._redraw()
        self.status_box.value = "Redone"

    def on_pan_left(self, b):
        self.pan_x -= self.PAN_NUDGE
        self._redraw()

    def on_pan_right(self, b):
        self.pan_x += self.PAN_NUDGE
        self._redraw()

    def on_pan_up(self, b):
        self.pan_y -= self.PAN_NUDGE
        self._redraw()

    def on_pan_down(self, b):
        self.pan_y += self.PAN_NUDGE
        self._redraw()

    def _draw_dashed_rect(self, fb, x, y, w, h, color, dash=4, gap=3):
        step = dash + gap
        for edge_y in (y, y + h):
            xi = x
            while xi < x + w:
                xe = min(xi + dash, x + w)
                _fb_line(fb, xi, edge_y, xe, edge_y, color)
                xi += step
        for edge_x in (x, x + w):
            yi = y
            while yi < y + h:
                ye = min(yi + dash, y + h)
                _fb_line(fb, edge_x, yi, edge_x, ye, color)
                yi += step

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


class GamesPage(Page):
    # a small launcher: list .py files in GAMES_DIR, RUN executes the
    # picked one in-process (MicroPython has no subprocess/os.system --
    # exec() in a fresh namespace is the only way to "run another
    # program and come back"). This is genuinely risky: a game that
    # changes hdmi mode or leaves hardware in a strange state could
    # destabilise the board (see the RGB1024-causes-a-hard-reset note
    # elsewhere in this file) -- on_run tries to force the display back
    # to a known-good state afterward regardless of how the game exits,
    # but that's a best-effort safety net, not a guarantee.
    def build(self, g):
        g.caption(320, 6, "Games", fg=INK, bg=PAGE, font=3, just="CT")
        self.list = None
        self.game_names = []
        self.picked = ""
        self.refresh()
        g.button(14, 410, 150, 32, "REFRESH", fg=WHITE, bg=BTN, font=2, callback=self.on_refresh)
        g.button(180, 410, 150, 32, "RUN", fg=WHITE, bg=BTN, font=2, callback=self.on_run)
        g.button(522, 410, 110, 32, "MENU", fg=WHITE, bg=RED, font=2, callback=self.on_back)
        self.status_bar(g)
        self.help_button(g, "games", "games")

    def enter(self):
        self.say("Pick a game and press RUN")

    def _ensure_dir(self):
        try:
            os.mkdir(GAMES_DIR)
        except OSError:
            pass  # already exists

    def list_games(self):
        try:
            return sorted(f for f in os.listdir(GAMES_DIR) if f.endswith(".py"))
        except OSError:
            return []

    def refresh(self):
        self._ensure_dir()
        names = self.list_games()
        self.game_names = names
        items = names if names else ["(no .py files in /sd/Games)"]
        if self.list is not None:
            self.g.remove(self.list)
        self.list = self.g.listbox(20, 60, 600, 330, items, 0, font=2, callback=self.on_pick)
        self.picked = names[0] if names else ""
        self.say(str(len(names)) + " game(s) found" if names else "No games found in /sd/Games")

    def on_refresh(self, b):
        self.refresh()

    def on_pick(self, c):
        i = c.value
        if 0 <= i < len(self.game_names):
            self.picked = self.game_names[i]

    def on_run(self, b):
        if not self.picked:
            self.say("Nothing picked -- add a .py file to /sd/Games and REFRESH")
            return
        path = GAMES_DIR + "/" + self.picked
        ulog("GamesPage: launching " + path)
        try:
            self.g.stop()
        except Exception:
            pass
        try:
            hdmi.fill(0)
        except Exception:
            pass
        try:
            console("serial")
        except Exception:
            pass
        try:
            f = open(path)
            try:
                source = f.read()
            finally:
                f.close()
            exec(compile(source, path, "exec"), {"__name__": "__main__"})
        except Exception as e:
            ulog("GamesPage: " + self.picked + " crashed: " + type(e).__name__ + " " + str(e))
        finally:
            # best-effort: force the display/console back to what the
            # rest of this app expects, regardless of what the game did
            try:
                hdmi.deinit()
            except Exception:
                pass
            try:
                hdmi.init(hdmi.RGB640)
                time.sleep(1)
            except Exception as e:
                ulog("GamesPage: display recovery failed: " + type(e).__name__ + " " + str(e))
            try:
                console("both")
            except Exception:
                pass
        self.go("menu")

    def on_back(self, b):
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
                elif where == "games":
                    where = GamesPage().show()
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