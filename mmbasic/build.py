# build.py -- builds the MMBasic files that go on the boards (MMBasic on
# the Pico has no include). Run with: python mmbasic/build.py
#
# Each page in PAGES becomes ../<page>.bas as:
#   the page's lines up to and including "Option DEFAULT NONE"
#   core.inc's declarations (every line before its first Sub/Function)
#   the rest of the page
#   generated.inc (font widths and MapGreys, from gen_club_bas_assets.py)
#   only the core.inc Subs/Functions the page uses, directly or through
#     another one it uses (board 2's firmware has 24K of program space,
#     too little for the whole of core.inc on every page)
# Games in GAMES are built the same way from games/ into ../games/ (they
# go in the SD card's Games folder). GAME_LIBS maps a game to the standalone
# library file(s) its own first line LIBRARY LOADs (RAM), concatenated in
# that order into one library -- built and deployed the same way, no
# core.inc/generated.inc merge (self-contained).
#
# Nothing goes in the board's flash-saved LIBRARY except the fonts (the owner:
# leave that alone until the code is well established) -- a game's own
# LIBRARY LOAD ..., RAM is a separate PSRAM slot, never the flash one.
#
# Output keeps every comment and indent: RUN in board 2's firmware crunches
# the program as it loads, so comments cost no program space.

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..")
PAGES = ["club", "gps", "members", "events", "financial", "photos", "music", "games", "admin", "files", "edit", "export", "users", "mailsetup", "unitname", "wifi", "settings", "message", "cars", "help"]
GAMES = ["snake", "clicker", "racing"]
GAME_LIBS = {"racing": ["racing_quotes", "racing_ui"]}
WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\$?")


def read(name):
    with open(os.path.join(HERE, name)) as f:
        return f.read().split("\n")


def crunch(lines):
    out = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("'"):
            continue
        out.append(s)
    return out


def split_core(core):
    """(declarations, {lower-case sub name: its lines})"""
    first = next(i for i, l in enumerate(core) if l.startswith(("Sub ", "Function ")))
    decl, subs, block = core[:first], {}, []
    for line in core[first:]:
        block.append(line)
        if line.startswith(("End Sub", "End Function")):
            head = next(l for l in block if l.startswith(("Sub ", "Function ")))
            subs[WORD.match(head.split()[1]).group(0).lower()] = block
            block = []
    return decl, subs


def used_names(code, subs):
    """the core sub names code uses, and the ones those use"""
    want, todo = set(), [code]
    while todo:
        for w in WORD.findall("\n".join(todo.pop())):
            w = w.lower()
            if w in subs and w not in want:
                want.add(w)
                todo.append(subs[w])
    return want


def needed(code, subs, exclude=frozenset()):
    """the core subs code uses, and the ones those use, in core order --
    skipping any already in exclude (e.g. already in the game's library)"""
    want = used_names(code, subs) - exclude
    return [l for name, block in subs.items() if name in want for l in block]


STRING = re.compile(r'"[^"]*"')
TYPES = {"integer", "string", "float", "as", "length"}
# MMBasic keywords that also turn up as command arguments (GUI CURSOR OFF,
# PLAY STOP, OPEN ... FOR INPUT, DIR$(p, FILE) ...): a declared name that
# matches one of these is never renamed, or the keyword would be renamed too
KEYWORDS = {"off", "on", "hide", "show", "load", "link", "unlink", "mouse", "file",
            "dir", "input", "output", "append", "random", "client", "tcp", "open",
            "close", "stop", "pause", "resume", "volume", "set", "reset", "next",
            "previous", "all", "address", "colour", "color", "mode", "font", "text",
            "box", "line", "circle", "pixel", "time", "date", "timer", "left", "right",
            "top", "bottom", "up", "down", "step", "to", "then", "else", "and", "or",
            "not", "mod", "xor", "for", "print", "run", "end", "exit", "sub", "function",
            "local", "dim", "const", "read", "data", "restore", "select", "case", "loop",
            "while", "until", "do", "if", "call", "gosub", "return", "sort", "copy",
            "kill", "rename", "mkdir", "chdir", "play", "mp3", "wav", "flac", "tone",
            "jpg", "bmp", "blit", "write", "gui", "cursor", "touch", "device", "map",
            "web", "request", "sound", "info", "errno", "errmsg", "cls", "list", "files"}


def code_part(line):
    """the line with any trailing ' comment removed (quotes respected)"""
    q = False
    for i, ch in enumerate(line):
        if ch == '"':
            q = not q
        elif ch == "'" and not q:
            return line[:i].rstrip()
    return line


def declared(lines):
    """every name this program declares: Const/Dim/Local, Sub/Function
    names and parameters, and labels -- 3+ characters only, so one- and
    two-letter names like X, W, L that are also keyword arguments
    (Touch(X), Device(MOUSE c, W)) are never touched"""
    names = set()
    for line in lines:
        s = STRING.sub('""', line)
        m = re.match(r"(Const|Dim|Local)\s+(.*)", s, re.I)
        if m:
            depth, part, parts = 0, "", []
            for ch in m.group(2):
                depth += ch == "("
                depth -= ch == ")"
                if ch == "," and depth == 0:
                    parts.append(part)
                    part = ""
                else:
                    part += ch
            parts.append(part)
            for p in parts:
                for w in WORD.findall(p.split("=")[0].split("(")[0]):
                    if w.lower() not in TYPES:
                        names.add(w)
                        break
        m = re.match(r"(Sub|Function)\s+(\w+\$?)\s*(\((.*)\))?", s, re.I)
        if m:
            names.add(m.group(2))
            for p in (m.group(4) or "").split(","):
                w = WORD.findall(p)
                if w:
                    names.add(w[0])
        m = re.match(r"^(\w+):$", s)
        if m:
            names.add(m.group(1))
    return {n for n in names if len(n.rstrip("$")) >= 3 and n.rstrip("$").lower() not in KEYWORDS}


def minify(lines):
    """rename declared names to short ones, outside string literals"""
    lines = [code_part(l) for l in lines]
    names = sorted(declared(lines), key=lambda n: n.lower())
    used = {w.lower() for l in lines for w in WORD.findall(STRING.sub('""', l))}
    short, n = {}, 0
    for name in names:
        while True:
            n += 1
            new, k = "", n
            while k:
                k, r = divmod(k - 1, 26)
                new = chr(97 + r) + new
            new = "q" + new
            if new not in used:
                break
        short[name.lower()] = new + ("$" if name.endswith("$") else "")

    def swap(m):
        return short.get(m.group(0).lower(), m.group(0))

    out = []
    for line in lines:
        pieces, last = [], 0
        for m in STRING.finditer(line):
            pieces.append(WORD.sub(swap, line[last:m.start()]))
            pieces.append(m.group(0))
            last = m.end()
        pieces.append(WORD.sub(swap, line[last:]))
        out.append("".join(pieces))
    return out


SPACES = re.compile(r"\s*([=+\-*/\\,()<>:;^])\s*")


def squeeze(lines):
    """drop the spaces next to operators, commas and brackets (outside
    string literals) -- MMBasic doesn't need them, the 24K does"""
    out = []
    for line in lines:
        pieces, last = [], 0
        for m in STRING.finditer(line):
            pieces.append(SPACES.sub(r"\1", line[last:m.start()]))
            pieces.append(m.group(0))
            last = m.end()
        pieces.append(SPACES.sub(r"\1", line[last:]))
        out.append("".join(pieces))
    return out


def build(src, decl, subs, gen, exclude=frozenset()):
    cut = next(i for i, l in enumerate(src) if l.strip().upper() == "OPTION DEFAULT NONE") + 1
    body = src[:cut] + decl + src[cut:] + gen
    # no crunching or squeezing: board 2's firmware crunches as RUN loads
    # (2026-09-24), so the board keeps the full commented source -- and
    # squeezing "MAP 1 = x" to "MAP 1=x" broke MAP (the slot came out wrong)
    return body + needed(body, subs, exclude)


def write(name, lines):
    # the board copy has no comments or blank lines: the commented source
    # stays here in mmbasic/, the board would drop them anyway as it RUNs,
    # and this way a board error like [71] is line 71 of the file
    lines = [code_part(l).rstrip() for l in lines if l.strip() and not l.strip().startswith("'")]
    lines = [l for l in lines if l.strip()]
    text = "\r\n".join(lines) + "\r\n"
    with open(os.path.join(OUT, name), "w", newline="") as f:
        f.write(text)
    print("%-18s %6d bytes, %4d lines" % (name, len(text), len(lines)))


def main():
    decl, subs = split_core(read("core.inc"))
    # net.inc: email/SMS Subs, added (like core's) only to pages that use them
    subs.update(split_core(read("net.inc"))[1])
    gen = read("generated.inc")
    for page in PAGES:
        write(page + ".bas", build(read(page + ".bas"), decl, subs, gen))
    os.makedirs(os.path.join(OUT, "games"), exist_ok=True)
    for game in GAMES:
        libs = GAME_LIBS.get(game, [])
        libcode = []
        for lib in libs:
            libcode += read(os.path.join("games", lib + ".bas"))
        # any core.inc sub the library itself needs is excluded from the
        # game's own needed() pass (below) -- it's already going to be in
        # the deployed program via the library, and MMBasic errors on a
        # Sub declared twice, since the two share one namespace once
        # LIBRARY LOAD runs
        libwant = used_names(libcode, subs)
        write(os.path.join("games", game + ".bas"),
              build(read(os.path.join("games", game + ".bas")), decl, subs, gen, libwant))
        for i, lib in enumerate(libs):
            libsrc = read(os.path.join("games", lib + ".bas"))
            # the core.inc code itself goes on the end of the LAST library
            # file only -- LIBRARY LOAD concatenates every file it's given
            # into one library, so it doesn't matter which one physically
            # holds it, only that it's not duplicated across more than one
            extra = [l for name, block in subs.items() if name in libwant for l in block] if i == len(libs) - 1 else []
            write(os.path.join("games", lib + ".bas"), libsrc + extra)


# club.pak: every page, game and picture in one file, for unpack.bas on a
# board (see its header for the format). Data files are left out on
# purpose -- a pack must never overwrite a board's live members/events.
PACK_ART = ["menu_bg.bmp", "page_bg_640.bmp"]


def write_pack(name, entries):
    import datetime
    out = bytearray(b"@@PACK %s %s %d\n" % (name[:-4].encode(), datetime.date.today().isoformat().encode(), len(entries)))
    for dest, src in entries:
        data = open(src, "rb").read()
        out += b"@@FILE %s %d\n" % (dest.encode(), len(data)) + data
    out += b"@@END\n"
    with open(os.path.join(OUT, name), "wb") as f:
        f.write(out)
    print("%-18s %7d bytes, %d files" % (name, len(out), len(entries)))


def pack():
    # club.pak: the pages and games (the everyday update); clubart.pak:
    # the background pictures and pointer (only when the art changes)
    entries = [("B:/club/%s.bas" % p, os.path.join(OUT, p + ".bas")) for p in PAGES]
    entries += [("B:/Games/%s.bas" % g, os.path.join(OUT, "games", g + ".bas")) for g in GAMES]
    entries += [("B:/Games/%s.bas" % lib, os.path.join(OUT, "games", lib + ".bas")) for libs in GAME_LIBS.values() for lib in libs]
    entries += [("B:/club/help.txt", os.path.join(HERE, "help.txt")),
                ("B:/club/unpack.bas", os.path.join(HERE, "unpack.bas")),
                ("B:/club/draw.bas", os.path.join(OUT, "draw.bas"))]
    write_pack("club.pak", entries)
    art = [("B:/club/" + a, os.path.join(OUT, "assets", a)) for a in PACK_ART]
    art += [("B:/club/arrow.spr", os.path.join(OUT, "arrow.spr"))]
    write_pack("clubart.pak", art)


if __name__ == "__main__":
    main()
    pack()
    # every page checked for undeclared / twice-declared names before it
    # can reach a board (see check.py)
    import subprocess, sys
    subprocess.call([sys.executable, os.path.join(HERE, "check.py")])
