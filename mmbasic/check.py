# check.py -- catches "X is not declared" and "X already declared" before a
# page reaches a board. Run: python mmbasic/check.py  (after build.py)
#
# Every word in a built page (outside strings and comments) must be an
# MMBasic command/function/keyword (read from the firmware's own tables in
# C:\build\picomite), or declared in that page (Dim/Const/Local/Static,
# Sub/Function names and parameters, labels). Also flags a name declared
# twice at the top level (MMBasic ignores case, and x$ and x are the same).
import os, re, sys, glob

FW = r"C:\build\picomite"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..")
WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*[$%!]?")
STRING = re.compile(r'"[^"]*"')

kw = set()
fwkw = set()   # the firmware's one-word commands (PUSH, POP, ...)
for h in glob.glob(os.path.join(FW, "**", "*.h"), recursive=True) + glob.glob(os.path.join(FW, "*.h")):
    try:
        t = open(h, errors="ignore").read()
    except OSError:
        continue
    for m in re.finditer(r'\{\s*\(unsigned char \*\)"([^"]+)"\s*,\s*(T_\w+)', t):
        for w in re.findall(r"[A-Za-z_][A-Za-z0-9_.]*", m.group(1)):
            kw.add(w.lower())
        # whole-word commands only ("Push", not "Blit Framebuffer")
        if m.group(2) == "T_CMD" and re.fullmatch(r"[A-Za-z_]\w*", m.group(1)):
            fwkw.add(m.group(1).lower())
# keywords used as command arguments that aren't in the tables, and the
# MM.xxx readings (checked loosely: anything starting mm.)
kw |= {"then", "else", "elseif", "endif", "to", "step", "as", "integer", "string", "float",
       "length", "input", "output", "append", "random", "for", "next", "do", "loop", "while",
       "until", "and", "or", "not", "xor", "mod", "inv", "case", "select", "end", "sub",
       "function", "exit", "gosub", "return", "local", "static", "dim", "const", "data",
       "read", "restore", "on", "off", "error", "skip", "clear", "abort", "file", "dir",
       "all", "rgb", "map", "set", "reset", "show", "hide", "load", "link", "cursor",
       "mouse", "keyboard", "tcp", "client", "request", "stream", "tls", "udp", "web",
       "scan", "open", "close", "write", "messages", "framebuffer", "f", "n", "l", "t",
       "copy", "merge", "create", "left", "right", "top", "bottom", "now", "gps", "sound",
       "flac", "wav", "mp3", "stop", "pause", "resume", "volume", "tone", "jpg", "bmp",
       "image", "save", "cls", "at", "true", "false", "pi", "base", "explicit", "default",
       "none", "option", "device", "touch", "x", "y", "w", "r", "m", "b", "d", "lcase", "vga", "path",
       "info", "filesize", "ip", "address", "status", "wifi", "usb", "com1", "com2",
       "black", "white", "red", "green", "blue", "yellow", "cyan", "magenta", "gray",
       "grey", "brown", "lilac", "rust", "fuchsia", "myrtle", "cobalt", "midgreen",
       "cerulean", "orange", "pink", "gold", "salmon", "beige", "lightgrey", "darkgrey",
       "chr", "hres", "vres", "errno", "errmsg", "fontwidth", "fontheight", "psram",
       "blit", "arc", "polygon", "rbox", "circle", "line", "pixel", "box", "text", "font",
       "mode", "gui", "library", "drive", "chdir", "mkdir", "kill", "rename", "files",
       "run", "execute", "print", "longstring", "sort", "field", "epoch", "day", "time",
       "date", "timer", "inkey", "val", "str", "hex", "len", "mid", "instr", "ucase",
       "trim", "choice", "max", "min", "abs", "int", "sqr", "sin", "cos", "atn", "rad",
       "rnd", "asc", "space", "eof", "loc", "lof", "llen", "linstr", "lgetstr", "setpin",
       "interrupt", "range", "e", "h", "c", "p", "s"}


def declared(lines):
    names = []
    for line in lines:
        s = STRING.sub('""', line)
        s = s.split("'")[0]
        m = re.match(r"\s*(Const|Dim|Local|Static)\s+(.*)", s, re.I)
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
                w = [x for x in WORD.findall(p.split("=")[0].split("(")[0]) if x.lower() not in ("integer", "string", "float", "length")]
                if w:
                    names.append((w[0], m.group(1).lower()))
        m = re.match(r"\s*(Sub|Function)\s+(\w+[$%!]?)\s*(\((.*)\))?", s, re.I)
        if m:
            names.append((m.group(2), "sub"))
            for p in (m.group(4) or "").split(","):
                w = WORD.findall(p)
                if w:
                    names.append((w[0], "param"))
        m = re.match(r"^(\w+):\s*$", s)
        if m:
            names.append((m.group(1), "label"))
    return names


def base(w):
    return w.rstrip("$%!").lower()


bad = 0
sys.path.insert(0, HERE)
import build
files = [os.path.join(OUT, p + ".bas") for p in build.PAGES]
files += [os.path.join(OUT, "games", g + ".bas") for g in build.GAMES]
lib_files = {os.path.join(OUT, "games", lib + ".bas") for libs in build.GAME_LIBS.values() for lib in libs}
files += list(lib_files)
# which game(s) LIBRARY LOAD a given library file -- it can rely on
# whichever game(s) load it having already declared their own top-level
# Dims/Consts (LIBRARY LOAD is always that game's first statement, but a
# library Sub only actually runs later, once its caller's own program has
# already declared everything -- same guarantee as core.inc's own globals)
lib_owners = {}
lib_siblings = {}
for game, libs in build.GAME_LIBS.items():
    for lib in libs:
        libpath = os.path.join(OUT, "games", lib + ".bas")
        lib_owners.setdefault(libpath, []).append(os.path.join(OUT, "games", game + ".bas"))
        # every LIBRARY LOAD file for a game is concatenated into ONE
        # library image, so each can see what its siblings declare too
        lib_siblings.setdefault(libpath, []).extend(
            os.path.join(OUT, "games", other + ".bas") for other in libs if other != lib)
files += [os.path.join(OUT, "draw.bas"), os.path.join(OUT, "unpack.bas")]
for path in sorted(files):
    name = os.path.relpath(path, OUT)
    lines = open(path, errors="ignore").read().replace("\r\n", "\n").split("\n")
    decl = declared(lines)
    if path in lib_files:
        # a library's owner(s) already carry core.inc's own top-level
        # Dims/Consts (tkSeg$, C_BAR, ...) in their OWN built output --
        # build() inserts core.inc's whole decl block into every page/
        # game unconditionally -- so merging the owner below is enough;
        # merging core.inc's decl separately too would just double-count
        # every one of those names as "declared twice"
        for ownerpath in lib_owners.get(path, []):
            if os.path.exists(ownerpath):
                ownerlines = open(ownerpath, errors="ignore").read().replace("\r\n", "\n").split("\n")
                decl = declared(ownerlines) + decl
        for sibpath in lib_siblings.get(path, []):
            if os.path.exists(sibpath):
                siblines = open(sibpath, errors="ignore").read().replace("\r\n", "\n").split("\n")
                decl = declared(siblines) + decl
    # a LIBRARY LOAD "B:/Games/x.bas"[, "B:/Games/y.bas" ...] line pulls
    # every file's own top-level Dims, Subs and labels into this program
    # before its first line runs (see racing.bas's header) -- so they
    # count as declared here too, and a clash between any of them is
    # exactly as real as one inside a single file. Every quoted path on
    # the line, not just the one straight after LIBRARY LOAD -- a naive
    # "LIBRARY LOAD\s+"..."" match only ever caught the first of several
    for ln in "\n".join(lines).split("\n"):
        if not re.match(r"\s*LIBRARY\s+LOAD\b", ln, re.I):
            continue
        for m in re.finditer(r'"B:/Games/(\w+)\.bas"', ln):
            libpath = os.path.join(OUT, "games", m.group(1) + ".bas")
            if not os.path.exists(libpath):
                continue
            liblines = open(libpath, errors="ignore").read().replace("\r\n", "\n").split("\n")
            decl = declared(liblines) + decl
    known = {base(n) for n, _ in decl}
    # declared twice at the top level (Dim/Const, not Local/params)
    seen = {}
    for n, how in decl:
        if how in ("dim", "const", "sub", "label"):
            k = base(n)
            if k in seen and not (how == "label" or seen[k] == "label"):
                print("%s: %s declared twice" % (name, n))
                bad += 1
            seen[k] = how
    # a variable named like a firmware command (PUSH, POP...): declaring it
    # works, but "push = 1" runs the command instead -- only when that line
    # is reached
    for n, how in decl:
        # (a Function too: inside it "Fill$ = x" starts with FILL, the
        # command). Only an assignment at the start of a statement is read
        # as the command -- using the name anywhere else is fine.
        if how in ("dim", "local", "static", "param", "const", "sub") and base(n) in fwkw:
            pat = re.compile(r"^\s*" + re.escape(n) + r"\s*(\(.*?\))?\s*=", re.I)
            for i, line in enumerate(lines, 1):
                if pat.match(STRING.sub('""', line).split("'")[0]):
                    print("%s line %d: %s = ... runs the MMBasic command %s instead" % (name, i, n, base(n).upper()))
                    bad += 1
    # a local or parameter with a Sub/Function's name (q vs Q$ -- MMBasic
    # ignores the $): "already declared" when that routine runs
    subnames = {base(n) for n, how in decl if how == "sub"}
    for n, how in decl:
        if how in ("local", "static", "param") and base(n) in subnames:
            print("%s: %s has the same name as a Sub/Function" % (name, n))
            bad += 1
    for i, line in enumerate(lines, 1):
        if len(line) > 250:
            print("%s line %d: %d characters, longer than MMBasic allows (255)" % (name, i, len(line)))
            bad += 1
    unknown = {}
    for i, line in enumerate(lines, 1):
        s = STRING.sub('""', line).split("'")[0]
        s = re.sub(r"&[Hh][0-9A-Fa-f]+", "0", s)
        if re.match(r"\s*(Data)\b", s, re.I):
            continue
        for w in WORD.findall(s):
            b = base(w)
            if b.startswith("mm.") or re.match(r"^gp\d+$", b):
                continue
            if b in kw or b in known or re.match(r"^\d", w):
                continue
            unknown.setdefault(w, i)
    for w, i in sorted(unknown.items(), key=lambda x: x[1]):
        print("%s line %d: %s is not declared" % (name, i, w))
        bad += 1
# the shared files: a routine named twice there silently replaces the other
seen = {}
for f in ("core.inc", "net.inc"):
    for m in re.finditer(r"^(Sub|Function)\s+(\w+[$%!]?)", open(os.path.join(HERE, f)).read(), re.M):
        k = base(m.group(2))
        if k in seen:
            print("shared routines named twice: %s (%s and %s)" % (m.group(2), seen[k], f))
            bad += 1
        seen[k] = f
for n, line in enumerate(open(os.path.join(HERE, "help.txt")).read().splitlines(), 1):
    if len(line) > 250:
        print("help.txt line %d: %d characters, longer than MMBasic can read" % (n, len(line)))
        bad += 1
print("problems:", bad)


# a Local (or parameter) with the same name as a global hides it inside that
# routine -- MMBasic ignores case, so a local w hides the screen's W. Flag
# every such routine that also uses the name the global way (upper case W/H)
# or any local that shadows another global the routine might mean.
def shadow_report():
    import re as _re
    n = 0
    for path in sorted(files):
        name = os.path.relpath(path, OUT)
        text = open(path, errors="ignore").read().replace("\r\n", "\n")
        glob_names = {base(x) for x, how in declared(text.split("\n")) if how in ("dim", "const")}
        for m in _re.finditer(r"^(Sub|Function)\s+(\w+[$%!]?)\s*(\([^)]*\))?(.*?)^End (Sub|Function)", text, _re.M | _re.S):
            body = m.group(0)
            locs = set()
            for lm in _re.finditer(r"^\s*(Local|Static)\s+(.*)$", body, _re.M):
                for p in _re.split(r",(?![^(]*\))", lm.group(2)):
                    w = [x for x in WORD.findall(p.split("(")[0]) if x.lower() not in ("integer", "string", "float", "length")]
                    if w:
                        locs.add(base(w[0]))
            for p in (m.group(3) or "").strip("()").split(","):
                w = WORD.findall(p)
                if w:
                    locs.add(base(w[0]))
            code = "\n".join(STRING.sub('""', l).split("'")[0] for l in body.split("\n")[1:])
            for g in sorted(locs & glob_names):
                if g in ("w", "h") and _re.search(r"\b" + g.upper() + r"\b", code):
                    print("%s %s: local %s hides the global %s, which it also uses" % (name, m.group(2), g, g.upper()))
                    n += 1
    return n


extra = shadow_report()
print("shadowing problems:", extra)
sys.exit(1 if (bad or extra) else 0)
