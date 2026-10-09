# make_buttons_pic.py -- writes buttons.pic, a draw.bas picture holding every
# button club.bas uses (main menu + the page bar), as real BTN shapes that
# can be picked, resized (EDIT > Shrink / grow), recoloured and moved in
# draw.bas. Also writes buttons_preview.png, a rough look at it on the PC.
# Run: python mmbasic/make_buttons_pic.py
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "buttons.pic")

# draw.bas colour slots (DefaultColours)
BLACK, BLUE, MYRTLE, COBALT, MIDGREEN, CERULEAN, GREEN, CYAN = range(8)
RED, MAGENTA, RUST, FUCHSIA, BROWN, LILAC, YELLOW, WHITE = range(8, 16)

MAIN = ["MEMBERS", "EVENTS", "PHOTOS", "EXPORT/IMPORT", "EMAIL/TXT", "FINANCIAL",
        "GAMES", "GPS", "ADMIN", "MUSIC", "QUIT"]
BAR = ["MENU", "BACK", "HELP", "SAVE", "NEW", "CLEAR", "DELETE"]

shapes = []   # (kind, a, b, c, d, e, f, colour, size, text)


def btn(x, y, w, h, t, c):
    shapes.append(("BTN", x, y, w, h, 0, 0, c, 1, t))


def text(x, y, t, c, s=1):
    shapes.append(("TEXT", x, y, 0, 0, 0, 0, c, s, t))


# the picture area on a 640x480 draw screen: right of the icon panel
# (40 px), under the menu bar, above the status bar
text(60, 36, "MAIN MENU", YELLOW)
for i, t in enumerate(MAIN):
    col = RED if t == "QUIT" else MIDGREEN
    btn(60 + (i % 3) * 190, 56 + (i // 3) * 56, 170, 44, t, col)
text(60, 290, "PAGE BAR", YELLOW)
for i, t in enumerate(BAR):
    col = RUST if t == "HELP" else (RED if t == "DELETE" else COBALT)
    btn(60 + i * 78, 310, 72, 32, t, col)
text(60, 370, "Pick one with SEL: drag to move, STYLE to recolour,", CYAN)
text(60, 386, "EDIT > Shrink / grow to size it.", CYAN)

with open(OUT, "w", newline="\r\n") as f:
    for s in shapes:
        f.write(",".join(str(v) for v in s) + "\n")
print("wrote", os.path.normpath(OUT), len(shapes), "shapes")

# ---- a rough preview (colours approximate) ----
try:
    from PIL import Image, ImageDraw
except ImportError:
    raise SystemExit
PAL = [(0, 0, 0), (0, 0, 255), (0, 64, 0), (0, 64, 255), (0, 160, 0), (0, 160, 255),
       (0, 255, 0), (0, 255, 255), (255, 0, 0), (255, 0, 255), (255, 64, 0), (255, 64, 255),
       (160, 96, 0), (160, 128, 255), (255, 255, 0), (255, 255, 255)]


def lighter(c):
    return tuple(min(255, v + 90) for v in c)


im = Image.new("RGB", (640, 480), (0, 0, 0))
d = ImageDraw.Draw(im)
for k, x, y, w, h, _, _, c, sz, t in shapes:
    if k == "BTN":
        r = max(2, h // 4)
        d.rounded_rectangle([x, y, x + w - 1, y + h - 1], r, fill=PAL[c], outline=(0, 0, 0))
        d.rounded_rectangle([x + 3, y + 3, x + w - 4, y + 3 + h // 2 - 3], max(1, r - 2), fill=lighter(PAL[c]))
        tw = len(t) * 6
        d.text((x + w // 2 - tw // 2 + 1, y + h // 2 - 4), t, fill=(0, 0, 0))
        d.text((x + w // 2 - tw // 2, y + h // 2 - 5), t, fill=(255, 255, 255))
    else:
        d.text((x, y), t, fill=PAL[c])
im.save(os.path.join(HERE, "..", "assets", "buttons_preview.png"))
