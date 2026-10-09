# gen_menu_art.py -- an interactive menu picture (a race timing tower:
# the menu items are its rows, P1 to P11; gauges and the red car on the right) for club.bas: menu.bmp (the
# art) + menu.lay (where its buttons and areas are), the same pair draw.bas
# saves. club.bas uses them when they're in B:/draw (see its header).
#
# Colours: MODE 3 turns each BMP pixel into one of 16 slots from its top
# bits, and club.bas's MAP decides what each slot shows (core.inc
# SetPalette + generated.inc MapGreys). So the art is drawn in slot
# numbers and each pixel written as that slot's "code" colour; the preview
# PNG shows the real colours.
#
# Run: python assets/gen_menu_art.py  -> assets/menu.bmp, menu.lay,
#      menu_preview.png. They go on the board in B:/draw.
import os
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, S = 640, 480, 4

SHOW = {0: (0, 0, 0), 1: (67, 160, 71), 2: (46, 125, 50), 3: (226, 75, 74), 4: (168, 40, 40),
        5: (255, 176, 0), 6: (17, 18, 19), 7: (20, 22, 24), 8: (23, 25, 27), 9: (26, 28, 31),
        10: (30, 32, 35), 11: (33, 36, 39), 12: (42, 44, 47), 13: (66, 70, 74),
        14: (117, 121, 125), 15: (232, 234, 237)}
BLACK, GRN, DGRN, RED, DRED, AMB, WHITE = 0, 1, 2, 3, 4, 5, 15
G6, G7, G8, G9, G10, G11, G12, G13, G14 = range(6, 15)


def code(i):
    """the RGB colour MODE 3 turns into slot i"""
    return (0x80 if i & 8 else 0, ((i >> 1) & 3) << 6, 0x80 if i & 1 else 0)


big = Image.new("P", (W * S, H * S), G7)
d = ImageDraw.Draw(big)


def B(v):
    return [x * S for x in v]


def rr(x0, y0, x1, y1, r, fill, outline=None, w=0):
    d.rounded_rectangle(B([x0, y0, x1, y1]), r * S, fill=fill, outline=outline, width=w * S)


def el(cx, cy, r, fill, outline=None, w=0):
    d.ellipse(B([cx - r, cy - r, cx + r, cy + r]), fill=fill, outline=outline, width=w * S)


def poly(pts, fill):
    d.polygon([(x * S, y * S) for x, y in pts], fill=fill)


# ---- carbon-fibre background: a woven checker of two dark greys ----
for y in range(0, H, 8):
    for x in range(0, W, 8):
        a = ((x // 8) + (y // 8)) % 2
        d.rectangle(B([x, y, x + 7, y + 3]), fill=G8 if a else G10)
        d.rectangle(B([x, y + 4, x + 7, y + 7]), fill=G10 if a else G8)
# ---- racing stripes down the whole picture ----
poly([(0, 60), (640, 60), (640, 66), (0, 66)], RED)
poly([(0, 68), (640, 68), (640, 71), (0, 71)], AMB)
poly([(0, 410), (640, 410), (640, 413), (0, 413)], AMB)
poly([(0, 414), (640, 414), (640, 418), (0, 418)], RED)

# ---- chequered flags top left and right ----
for fx, flip in ((14, 1), (626, -1)):
    d.line(B([fx, 8, fx, 56]), fill=G13, width=3 * S)
    for r in range(4):
        for c in range(5):
            x0 = fx + flip * (2 + c * 9)
            y0 = 8 + r * 9 + (c * 1)
            col = WHITE if (r + c) % 2 == 0 else BLACK
            xa, xb = sorted([x0, x0 + flip * 9])
            d.polygon([(xa * S, y0 * S), (xb * S, (y0 + 1) * S), (xb * S, (y0 + 10) * S), (xa * S, (y0 + 9) * S)], fill=col)

# ---- title plate ----
rr(150, 8, 490, 54, 12, G12, BLACK, 2)
rr(154, 12, 486, 50, 10, G11)
d.line(B([160, 13, 480, 13]), fill=G14, width=S)
for x in (162, 478):
    el(x, 31, 3, G14, BLACK, 1)
TITLE = (170, 14, 300, 34)          # the club name goes here

# ---- the two gauges, top right ----
GAUGES = {"CLOCK": (360, 158), "DATE": (540, 158)}
GR = 56
import math
for cx, cy in GAUGES.values():
    el(cx + 3, cy + 4, GR + 12, G6)                      # shadow
    el(cx, cy, GR + 12, G13, BLACK, 2)                   # chrome bezel
    el(cx, cy, GR + 8, G14)
    el(cx, cy, GR + 5, G12, BLACK, 1)
    d.arc(B([cx - GR - 10, cy - GR - 10, cx + GR + 10, cy + GR + 10]), 200, 290, fill=WHITE, width=2 * S)
    el(cx, cy, GR + 1, BLACK)
    for a in range(0, 360, 15):
        t = math.radians(a)
        r1, r2 = GR + 1, GR + 5
        d.line([((cx + r1 * math.cos(t)) * S, (cy + r1 * math.sin(t)) * S),
                ((cx + r2 * math.cos(t)) * S, (cy + r2 * math.sin(t)) * S)],
               fill=RED if 300 <= a or a < 30 else G14, width=S)

# ---- the timing tower down the left: the menu, P1 to P11 ----
LABELS = ["MEMBERS", "EVENTS", "PHOTOS", "EXPORT/IMPORT", "EMAIL/TXT", "FINANCIAL",
          "GAMES", "GPS", "ADMIN", "MUSIC", "QUIT"]
TX, TY, TW, RH, GAP = 22, 84, 226, 26, 4
rr(TX - 6, TY - 30, TX + TW + 6, TY + len(LABELS) * (RH + GAP) + 2, 8, G6, BLACK, 1)   # the tower
rr(TX - 2, TY - 26, TX + TW + 2, TY - 6, 5, RED)                                      # its header
buttons = []
for i, t in enumerate(LABELS):
    y = TY + i * (RH + GAP)
    rr(TX, y, TX + TW, y + RH, 4, G11 if i % 2 else G12)          # the row
    rr(TX + 2, y + 2, TX + 36, y + RH - 2, 3, RED if t == "QUIT" else AMB)  # position badge
    poly([(TX + TW - 18, y + 8), (TX + TW - 10, y + RH // 2), (TX + TW - 18, y + RH - 8)], G14)  # chevron
    d.line(B([TX + 40, y + RH - 1, TX + TW - 4, y + RH - 1]), fill=G6, width=S)
    buttons.append((t, TX, y, TW, RH))

# ---- the car, under the gauges ----
import sys
sys.path.insert(0, os.path.join(HERE, "..", "mmbasic", "games"))
import gen_pitart
car_rows = gen_pitart.car().reduce()
CAR = {gen_pitart.CM: RED, gen_pitart.CS: DRED}
CARX, CARY = 300, 262

# ---- the ticker strip ----
TICK = (40, 426, 560, 38)
rr(TICK[0] - 4, TICK[1] - 4, TICK[0] + TICK[2] + 4, TICK[1] + TICK[3] + 4, 8, AMB, BLACK, 1)
rr(TICK[0], TICK[1], TICK[0] + TICK[2], TICK[1] + TICK[3], 6, BLACK)

# ---- reduce to 1x: the most common slot in each 4x4 block ----
src = big.load()
img = Image.new("P", (W, H))
px = img.load()
for y in range(H):
    for x in range(W):
        px[x, y] = Counter(src[x * S + i, y * S + j] for i in range(S) for j in range(S)).most_common(1)[0][0]

for y, r in enumerate(car_rows):
    for x, c in enumerate(r):
        if c != gen_pitart.SEE and 0 <= CARX + x < W and 0 <= CARY + y < H:
            px[CARX + x, CARY + y] = CAR.get(c, c)

# ---- button labels, crisp at 1x (black shadow, white text) ----
dd = ImageDraw.Draw(img)
dd.fontmode = "1"
font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 14)
for n, (t, x, y, bw, bh) in enumerate(buttons):
    dd.text((x + 8, y + bh / 2 - 8), "P%d" % (n + 1), font=font, fill=BLACK)
    dd.text((x + 45, y + bh / 2 - 8), t, font=font, fill=WHITE)
dd.text((TX + 6, TY - 25), "CLUB MENU", font=font, fill=WHITE)
tw = dd.textlength("1", font=font)
dd.text((CARX + 204 - tw / 2, CARY + 66 - 8), "1", font=font, fill=BLACK)
small = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 11)
for n, (cx, cy) in GAUGES.items():
    tw = dd.textlength(n, font=small)
    dd.text((cx - tw / 2 + 1, cy + GR + 15 + 1), n, font=small, fill=BLACK)
    dd.text((cx - tw / 2, cy + GR + 15), n, font=small, fill=G14)

# ---- out ----
bmp = Image.new("RGB", (W, H))
prev = Image.new("RGB", (W, H))
bp, pp = bmp.load(), prev.load()
for y in range(H):
    for x in range(W):
        s = px[x, y]
        bp[x, y] = code(s)
        pp[x, y] = SHOW[s]
bmp.save(os.path.join(HERE, "menu.bmp"))
prev.save(os.path.join(HERE, "menu_preview.png"))

lay = ["BUTTON,%s,%d,%d,%d,%d" % b for b in buttons]
for n, (cx, cy) in GAUGES.items():
    lay.append("AREA,%s,%d,%d,%d,%d" % (n, cx - GR, cy - GR, 2 * GR, 2 * GR))
lay.append("AREA,TICKER,%d,%d,%d,%d" % TICK)
lay.append("AREA,TITLE,%d,%d,%d,%d" % TITLE)
with open(os.path.join(HERE, "menu.lay"), "w", newline="\r\n") as f:
    f.write("\n".join(lay) + "\n")
print("menu.bmp, menu.lay:", len(buttons), "buttons,", len(lay) - len(buttons), "areas")
