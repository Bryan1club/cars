# gen_pitart.py -- the racing game's pit scene art: the mechanic, the driver
# and the car, smooth full-size drawings (no pixel blocks).
#
# Each is drawn here at 4x with PIL and reduced to 1x by taking the most
# common colour in each 4x4 block, so every pixel is one of the game's
# palette slots (no blended colours the board can't show). Written into
# racing.bas between its ART BEGIN / ART END markers as run-length DATA:
# per row, pairs of (a colour code, the run length as CHR$(34 + n)).
# Colour codes: 0-F a palette slot, "." see-through, T / U the player's
# team colour and its shade, C / D the car's colour and its shade.
#
# Talking and blinking: for each person there are also small patches of the
# face -- mouth open / shut, eyes open / shut -- that the game swaps over
# the face while the words type out.
#
# Also saves assets/pit_scene_preview.png: the whole scene the way the game
# lays it out.
# Run: python mmbasic/games/gen_pitart.py   (then python mmbasic/build.py)
import os
from collections import Counter
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
NL = chr(10)

PAL = {0: (0, 0, 0), 1: (67, 160, 71), 2: (46, 125, 50), 3: (226, 75, 74),
       4: (168, 40, 40), 5: (255, 176, 0), 6: (17, 18, 19), 7: (30, 74, 30),
       8: (96, 96, 96), 9: (204, 102, 255), 10: (30, 32, 35), 11: (210, 180, 140),
       12: (51, 136, 255), 13: (66, 70, 74), 14: (117, 121, 125), 15: (232, 234, 237)}
K, RED, DRED, AMB, SKIN, DG, MG, LG, WH, DK = 0, 3, 4, 5, 11, 13, 8, 14, 15, 10
TM, TS, CM, CS = 100, 101, 102, 103       # team colour + shade, car colour + shade
SEE = 255
S = 4


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.im = Image.new("P", (w * S, h * S), SEE)
        self.d = ImageDraw.Draw(self.im)

    def P(self, pts):
        return [(x * S, y * S) for x, y in pts]

    def poly(self, pts, c, ol=True):
        self.d.polygon(self.P(pts), fill=c)
        if ol:
            self.d.line(self.P(pts + pts[:1]), fill=K, width=2 * S, joint="curve")

    def ell(self, cx, cy, rx, ry, c, ol=True):
        self.d.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=c,
                       outline=K if ol else None, width=2 * S if ol else 0)

    def rrect(self, x0, y0, x1, y1, r, c, ol=True):
        self.d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], r * S, fill=c,
                                 outline=K if ol else None, width=2 * S if ol else 0)

    def ln(self, pts, c, w=1):
        self.d.line(self.P(pts), fill=c, width=max(1, int(w * S)), joint="curve")

    def arc(self, cx, cy, rx, ry, a0, a1, c, w=1):
        self.d.arc([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], a0, a1, fill=c,
                   width=max(1, int(w * S)))

    def chord(self, box, a0, a1, c, ol=True):
        self.d.chord([v * S for v in box], a0, a1, fill=c, outline=K if ol else None,
                     width=2 * S if ol else 0)

    def reduce(self):
        src = self.im.load()
        out = []
        for y in range(self.h):
            row = []
            for x in range(self.w):
                cnt = Counter(src[x * S + i, y * S + j] for i in range(S) for j in range(S))
                row.append(cnt.most_common(1)[0][0])
            out.append(row)
        return out


# ============================================================ the mechanic
# pose 0: thumbs up, spanner in hand (the default/talking pose -- the only
# one with mouth/eye variants, since it's the only one used for dialogue).
# pose 1: arms crossed. pose 2: hand on hip, other arm relaxed. 1 and 2
# are for the idle GARAGE screen only, so he's not always shown mid-job.
def mechanic(mouth=True, eyes=True, pose=0):
    c = Canvas(150, 200)
    poly, ell, rrect, ln, arc = c.poly, c.ell, c.rrect, c.ln, c.arc
    # legs, boots
    poly([(46, 142), (72, 142), (71, 184), (48, 184)], TM)
    poly([(78, 142), (104, 142), (102, 184), (79, 184)], TM)
    poly([(62, 146), (71, 146), (71, 183), (64, 183)], TS, ol=False)
    poly([(93, 146), (103, 146), (101, 183), (94, 183)], TS, ol=False)
    ln([(52, 163), (66, 161)], TS, 1.5)
    ln([(84, 161), (98, 163)], TS, 1.5)
    poly([(48, 174), (71, 174), (71, 179), (48, 179)], AMB, ol=False)
    poly([(79, 174), (102, 174), (102, 179), (79, 179)], AMB, ol=False)
    ln([(48, 174), (71, 174)], K, 1)
    ln([(79, 174), (102, 174)], K, 1)
    poly([(47, 184), (72, 184), (73, 196), (34, 196), (35, 190), (42, 186)], K)
    poly([(78, 184), (103, 184), (108, 186), (115, 190), (116, 196), (78, 196)], K)
    ell(41, 190, 5, 2.5, DG, ol=False)
    ell(109, 190, 5, 2.5, DG, ol=False)
    if pose == 0:
        # spanner (behind the arm) -- only pose 0 is holding it
        ln([(128, 136), (135, 76)], LG, 7)
        ln([(126, 135), (133, 78)], WH, 2)
        ell(136, 68, 11, 11, LG)
        poly([(131, 54), (141, 54), (139, 66), (133, 66)], SEE, ol=False)
        ln([(131, 55), (133, 66), (139, 66), (141, 55)], K, 2)
        arc(136, 68, 8, 8, 120, 200, WH, 2)
        ell(127, 142, 8, 8, LG)
        ell(127, 142, 3.5, 3.5, SEE, ol=False)
        arc(127, 142, 3.5, 3.5, 0, 360, K, 1.5)
    # body
    poly([(38, 92), (112, 92), (118, 112), (114, 146), (36, 146), (32, 112)], TM)
    poly([(90, 94), (112, 92), (118, 112), (114, 145), (98, 145)], TS, ol=False)
    ln([(75, 100), (75, 138)], TS, 1.5)
    ln([(73, 100), (73, 138)], K, 0.8)
    rrect(44, 108, 66, 121, 3, WH)
    ln([(48, 114), (54, 112), (58, 116), (62, 113)], DRED, 1.5)
    rrect(84, 106, 98, 118, 2, TS)
    ln([(84, 108), (98, 108)], AMB, 1.5)
    ln([(88, 104), (88, 113)], LG, 2)
    poly([(35, 136), (115, 136), (115, 145), (35, 145)], DK)
    rrect(68, 134, 82, 147, 2, AMB)
    rrect(72, 138, 78, 143, 1, DK, ol=False)
    poly([(36, 142), (48, 141), (50, 152), (46, 166), (41, 158), (35, 168), (33, 153)], LG)
    ln([(40, 146), (42, 160)], DG, 1.5)
    ln([(45, 147), (46, 158)], MG, 1.5)
    ell(39, 150, 2, 3, DG, ol=False)
    poly([(62, 86), (88, 86), (82, 100), (68, 100)], WH)
    poly([(50, 88), (64, 86), (70, 101)], TM)
    poly([(86, 86), (100, 88), (80, 101)], TS)
    if pose == 0:
        # arms: thumbs up, and the hand holding the spanner
        poly([(38, 92), (48, 104), (32, 122), (20, 112)], TM)
        ln([(40, 96), (26, 114)], AMB, 2.5)
        poly([(20, 112), (32, 122), (29, 127), (16, 117)], WH)
        poly([(17, 117), (29, 126), (27, 100), (16, 100)], SKIN)
        rrect(10, 76, 30, 102, 6, SKIN)
        rrect(14, 58, 22, 80, 4, SKIN)
        ln([(15, 62), (21, 62)], LG, 1)
        for y in (84, 90, 96):
            ln([(12, y), (27, y)], K, 1)
        ell(22, 110, 3, 2, LG, ol=False)
        poly([(112, 92), (124, 104), (131, 128), (120, 130), (112, 110)], TS)
        ln([(114, 96), (126, 122)], AMB, 2.5)
        poly([(119, 129), (132, 127), (133, 133), (120, 135)], WH)
        rrect(117, 131, 137, 147, 5, SKIN)
        ln([(119, 137), (135, 137)], K, 1)
        ln([(119, 142), (135, 142)], K, 1)
    elif pose == 1:
        # arms folded across the chest
        poly([(38, 92), (52, 100), (72, 116), (66, 128), (48, 114), (28, 100)], TM)
        poly([(112, 92), (98, 100), (78, 122), (86, 132), (104, 116), (122, 100)], TS)
        rrect(56, 118, 76, 134, 6, SKIN)
        ln([(60, 122), (72, 122)], K, 1)
        rrect(50, 122, 68, 136, 6, SKIN)
        ln([(54, 126), (64, 126)], K, 1)
    else:
        # one hand on the hip, the other relaxed at his side
        poly([(38, 92), (26, 106), (30, 124), (44, 122), (42, 104)], TM)
        rrect(24, 120, 44, 134, 6, SKIN)
        ln([(28, 124), (40, 124)], K, 1)
        poly([(112, 92), (124, 102), (122, 136), (108, 138), (108, 100)], TS)
        rrect(102, 134, 122, 150, 6, SKIN)
        ln([(106, 140), (118, 140)], K, 1)
    # head
    rrect(64, 74, 86, 92, 4, SKIN)
    ell(49, 56, 5, 8, SKIN)
    ell(101, 56, 5, 8, SKIN)
    arc(49, 56, 2.5, 4.5, 250, 110, LG, 1.2)
    arc(101, 56, 2.5, 4.5, 70, 290, LG, 1.2)
    ell(75, 52, 26, 29, SKIN)
    poly([(51, 38), (57, 38), (56, 60), (51, 58)], K, ol=False)
    poly([(93, 38), (99, 38), (99, 58), (94, 60)], K, ol=False)
    arc(75, 54, 21, 25, 30, 150, LG, 2)
    for x, y in ((62, 72), (68, 76), (75, 77), (82, 76), (88, 72), (65, 69), (85, 69)):
        ell(x, y, 0.8, 0.8, LG, ol=False)
    poly([(58, 38), (70, 36), (71, 40), (59, 42)], K, ol=False)
    poly([(80, 36), (92, 38), (91, 42), (79, 40)], K, ol=False)
    if eyes:
        # looking left, at whoever he's talking to -- same trick as the
        # driver's own eyes (which look right, at him)
        ell(64, 48, 5.5, 5, WH)
        ell(86, 48, 5.5, 5, WH)
        ell(60.5, 48.5, 2.8, 3, K, ol=False)
        ell(82.5, 48.5, 2.8, 3, K, ol=False)
        ell(59.5, 47, 0.9, 0.9, WH, ol=False)
        ell(81.5, 47, 0.9, 0.9, WH, ol=False)
    else:
        ln([(58.5, 49), (69.5, 49)], K, 2)
        ln([(80.5, 49), (91.5, 49)], K, 2)
    poly([(74, 50), (79, 58), (73, 60)], SKIN, ol=False)
    ln([(75, 50), (79, 58), (72, 60)], LG, 1.5)
    if mouth:
        poly([(62, 64), (88, 64), (84, 73), (66, 73)], DRED)
        poly([(64, 64), (86, 64), (84, 67), (66, 67)], WH, ol=False)
        ln([(75, 64), (75, 67)], LG, 0.8)
    else:
        arc(75, 62, 10, 6, 20, 160, K, 2)
    poly([(56, 64), (66, 58), (75, 61), (84, 58), (94, 64), (88, 66), (75, 63), (62, 66)], K, ol=False)
    ell(92, 60, 3, 2, LG, ol=False)
    ell(95, 62, 1.5, 1.2, LG, ol=False)
    # cap
    c.chord([48, 16, 102, 60], 180, 360, RED)
    c.chord([80, 16, 102, 60], 270, 360, DRED, ol=False)
    ln([(48, 38), (102, 38)], K, 2)
    poly([(28, 34), (62, 34), (64, 40), (32, 42)], DRED)
    ln([(32, 36), (60, 36)], RED, 1.5)
    rrect(68, 22, 82, 32, 3, AMB)
    ell(75, 27, 2.5, 2.5, RED, ol=False)
    ell(75, 16.5, 2.5, 1.5, DRED)
    return c


# ============================================================ the driver
def driver(mouth=True, eyes=True, female=False):
    c = Canvas(130, 200)
    poly, ell, rrect, ln, arc = c.poly, c.ell, c.rrect, c.ln, c.arc
    # boots
    poly([(34, 184), (58, 184), (60, 196), (30, 196)], K)
    poly([(66, 184), (90, 184), (100, 192), (100, 196), (66, 196)], K)
    ell(94, 192, 4, 2, DG, ol=False)
    # legs: race suit, white stripe down the outside
    poly([(36, 132), (60, 132), (58, 185), (36, 185)], TM)
    poly([(64, 132), (88, 132), (90, 185), (66, 185)], TM)
    poly([(52, 136), (60, 136), (58, 184), (53, 184)], TS, ol=False)
    poly([(80, 136), (88, 136), (90, 184), (84, 184)], TS, ol=False)
    ln([(38, 136), (38, 182)], WH, 2.5)
    ln([(86, 136), (88, 182)], WH, 2.5)
    # body
    poly([(30, 84), (94, 84), (98, 108), (92, 136), (32, 136), (26, 108)], TM)
    poly([(74, 86), (94, 84), (98, 108), (92, 135), (78, 135)], TS, ol=False)
    ln([(62, 90), (62, 132)], K, 1)                      # zip
    ln([(30, 88), (46, 132)], WH, 3)                     # racing stripe
    rrect(66, 98, 86, 108, 2, AMB)                       # sponsor patch
    ln([(70, 103), (82, 103)], DRED, 1.5)
    rrect(38, 118, 52, 126, 2, WH)                       # small badge
    # collar
    rrect(50, 78, 74, 90, 4, TM)
    ln([(52, 84), (72, 84)], WH, 1.5)
    # our left arm: down, black glove
    poly([(30, 86), (40, 92), (30, 128), (20, 124)], TM)
    ln([(28, 92), (22, 122)], WH, 2)
    rrect(16, 122, 32, 140, 5, K)
    ln([(18, 128), (30, 128)], DG, 1)
    # the helmet under his other arm
    ell(104, 118, 20, 18, TM)
    c.chord([84, 100, 124, 136], 200, 340, TS, ol=False)
    ln([(86, 112), (124, 112)], WH, 3)                   # helmet stripe
    rrect(96, 118, 124, 130, 5, DK)                      # visor
    ln([(100, 121), (114, 121)], LG, 1.5)
    arc(104, 118, 20, 18, 0, 360, K, 2)
    # our right arm, over the helmet, glove on top
    poly([(90, 86), (100, 94), (104, 112), (94, 116), (88, 104)], TM)
    ln([(92, 90), (98, 110)], WH, 2)
    rrect(88, 108, 108, 122, 5, K)
    ln([(92, 114), (104, 114)], DG, 1)
    # head
    rrect(52, 70, 72, 82, 4, SKIN)
    ell(40, 48, 4.5, 7, SKIN)
    ell(84, 48, 4.5, 7, SKIN)
    ell(62, 46, 22, 26, SKIN)
    # hair: the same short, swept crown either way, but long hair also
    # flows down past the shoulders on both sides instead of stopping at
    # the ears -- drawn after the body/collar (above), so it falls over
    # them, not under
    c.chord([38, 16, 86, 56], 180, 360, K)
    poly([(40, 36), (52, 24), (70, 22), (84, 30), (86, 40), (76, 32), (60, 30), (46, 38)], K, ol=False)
    if female:
        poly([(38, 40), (46, 36), (48, 96), (34, 100), (32, 60)], K)
        poly([(86, 40), (78, 36), (76, 96), (90, 100), (92, 60)], K)
    else:
        poly([(40, 36), (44, 30), (46, 44), (41, 46)], K, ol=False)
        poly([(84, 36), (86, 44), (82, 46), (80, 34)], K, ol=False)
    # eyebrows
    ln([(48, 38), (57, 36)], K, 2)
    ln([(67, 36), (76, 38)], K, 2)
    if eyes:
        # looking right, at the mechanic
        ell(53, 44, 4.5, 4, WH)
        ell(71, 44, 4.5, 4, WH)
        ell(55, 44.5, 2.3, 2.6, K, ol=False)
        ell(73, 44.5, 2.3, 2.6, K, ol=False)
        ell(56, 43, 0.8, 0.8, WH, ol=False)
        ell(74, 43, 0.8, 0.8, WH, ol=False)
    else:
        ln([(48.5, 45), (57.5, 45)], K, 2)
        ln([(66.5, 45), (75.5, 45)], K, 2)
    # nose
    ln([(63, 46), (66, 53), (61, 54)], LG, 1.5)
    if mouth:
        poly([(52, 58), (72, 58), (68, 66), (56, 66)], DRED)
        poly([(54, 58), (70, 58), (68, 61), (56, 61)], WH, ol=False)
    else:
        arc(62, 57, 9, 5, 20, 160, K, 2)
    # cheeks
    ell(47, 55, 2.5, 1.5, LG, ol=False)
    return c


# ============================================================ the car
def car():
    c = Canvas(300, 112)
    poly, ell, rrect, ln, arc = c.poly, c.ell, c.rrect, c.ln, c.arc
    ell(150, 104, 140, 6, DK, ol=False)                             # shadow
    # rear wing on its struts
    ln([(30, 46), (34, 62)], K, 3)
    ln([(52, 46), (54, 60)], K, 3)
    rrect(10, 36, 72, 48, 3, CS)
    ln([(14, 40), (68, 40)], WH, 1.5)
    # body: long and low, nose to the right
    poly([(8, 88), (14, 60), (70, 56), (118, 54), (150, 36), (190, 34), (204, 52),
          (262, 62), (296, 76), (296, 86), (240, 92), (60, 92)], CM)
    # lower side shade and the white stripe
    poly([(12, 80), (296, 80), (296, 86), (240, 92), (60, 92), (8, 88)], CS, ol=False)
    ln([(20, 70), (292, 74)], WH, 3)
    # air intake, side pod vent
    rrect(100, 60, 132, 72, 3, DK)
    for x in (106, 114, 122):
        ln([(x, 62), (x, 70)], DG, 1.5)
    # cockpit: opening, driver's helmet, screen, roll hoop
    poly([(150, 38), (188, 36), (196, 52), (146, 54)], DK)
    ell(166, 40, 11, 10, WH)
    rrect(162, 36, 178, 44, 3, DK)
    ln([(190, 36), (202, 52)], LG, 3)
    ln([(138, 30), (140, 54)], DK, 4)
    ln([(132, 30), (146, 30)], DK, 4)
    # exhaust
    rrect(2, 72, 16, 78, 2, LG)
    ell(3, 75, 2, 3, K, ol=False)
    # nose wing
    poly([(262, 86), (298, 84), (298, 92), (264, 94)], CS)
    # wheels
    for x in (72, 236):
        ell(x, 86, 22, 22, K)
        ell(x, 86, 13, 13, LG)
        ell(x, 86, 5, 5, DG)
        arc(x, 86, 18, 18, 200, 250, DG, 2)
        for a in range(0, 360, 60):
            import math
            ln([(x + 6 * math.cos(math.radians(a)), 86 + 6 * math.sin(math.radians(a))),
                (x + 12 * math.cos(math.radians(a)), 86 + 12 * math.sin(math.radians(a)))], DG, 1.5)
    # number roundel (the game prints the number on it)
    ell(204, 66, 11, 10, WH)
    return c


# ============================================================ encoding
CODE = {TM: "T", TS: "U", CM: "C", CS: "D"}
DIG = "0123456789ABCDEF"


def rle(rows):
    out = []
    for r in rows:
        s, i = "", 0
        while i < len(r):
            j = i
            while j < len(r) and r[j] == r[i] and j - i < 90:
                j += 1
            s += ("." if r[i] == SEE else CODE.get(r[i]) or DIG[r[i]]) + chr(34 + (j - i))
            i = j
        assert len(s) < 240, "row too busy: %d" % len(s)
        out.append(s)
    return out


def trim(rows):
    """crop to what's drawn: rows, left, top"""
    used = [y for y, r in enumerate(rows) if any(c != SEE for c in r)]
    top, bot = used[0], used[-1]
    rows = rows[top:bot + 1]
    left = min(next(i for i, c in enumerate(r) if c != SEE) for r in rows if any(c != SEE for c in r))
    right = max(max(i for i, c in enumerate(r) if c != SEE) for r in rows if any(c != SEE for c in r))
    return [r[left:right + 1] for r in rows], left, top


def patch(full, other, left, top):
    """the box round where two drawings differ: (x, y, rows of full, rows of other)"""
    ys = [y for y in range(len(full)) if full[y] != other[y]]
    xs = [x for y in ys for x in range(len(full[y])) if full[y][x] != other[y][x]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    a = [full[y][x0:x1 + 1] for y in range(y0, y1 + 1)]
    b = [other[y][x0:x1 + 1] for y in range(y0, y1 + 1)]
    return x0 - left, y0 - top, a, b


def main():
    blocks = []   # (label, w, h, dx, dy, rows)


    def add(label, rows, dx=0, dy=0):
        blocks.append((label, len(rows[0]), len(rows), dx, dy, rows))


    info = []
    for name, fn, mouthxy in (("Mech", mechanic, (64, 68)), ("Drv", driver, (66, 62))):
        full = fn().reduce()
        shut = fn(mouth=False).reduce()
        blink = fn(eyes=False).reduce()
        rows, left, top = trim(full)
        add(name + "Art", rows)
        x, y, a, b = patch(full, shut, left, top)
        add(name + "MouthOpen", a, x, y)
        add(name + "MouthShut", b, x, y)
        x, y, a, b = patch(full, blink, left, top)
        add(name + "EyesOpen", a, x, y)
        add(name + "EyesShut", b, x, y)
        info += [len(rows[0]), len(rows), mouthxy[0] - left, mouthxy[1] - top]
    # the long-hair driver (ArtAt 13-17, +8 on the usual 5-9): same head
    # position and bounding box as the usual driver (hair falls inside the
    # arms' own silhouette, doesn't widen or heighten the trim), so it
    # shares DrvArt's own info entry rather than needing a second one
    full = driver(female=True).reduce()
    shut = driver(mouth=False, female=True).reduce()
    blink = driver(eyes=False, female=True).reduce()
    rows, left, top = trim(full)
    add("DrvArtF", rows)
    x, y, a, b = patch(full, shut, left, top)
    add("DrvMouthOpenF", a, x, y)
    add("DrvMouthShutF", b, x, y)
    x, y, a, b = patch(full, blink, left, top)
    add("DrvEyesOpenF", a, x, y)
    add("DrvEyesShutF", b, x, y)
    # two more mechanic poses for the idle GARAGE screen (arms crossed,
    # hand on hip) -- no mouth/eye variants, they're never used for talking
    for i, pose in ((2, 1), (3, 2)):
        rows, left, top = trim(mechanic(pose=pose).reduce())
        add("MechArt%d" % i, rows)
    rows, left, top = trim(car().reduce())
    add("CarArt", rows)
    info += [len(rows[0]), len(rows), 204 - left, 66 - top]

    lines = ["' sizes: mechanic w, h, mouth x, y; driver the same; car w, h, roundel x, y",
             "ArtInfo:", "Data " + ", ".join(str(v) for v in info)]
    for label, w, h, dx, dy, rows in blocks:
        lines.append(label + ":")
        lines.append("Data %d, %d, %d, %d" % (w, h, dx, dy))
        lines += ['Data "%s"' % s for s in rle(rows)]
    rb = os.path.join(HERE, "racing.bas")
    text = open(rb).read()
    a = text.index("' ART BEGIN")
    a = text.index(NL, a) + 1
    b = text.index("' ART END")
    open(rb, "w", newline=NL).write(text[:a] + NL.join(lines) + NL + text[b:])

    # ---- a preview of the scene as the game lays it out ----
    W, H, fh = 640, 480, 12
    CT, CB = 2 * fh + 40, H - fh - 14 - 12
    team = (12, 13)
    carc = (5, 4)
    im = Image.new("RGB", (W, H), (30, 32, 35))


    def put(label, x, y):
        for lb, w, h, dx, dy, rows in blocks:
            if lb == label:
                for yy, r in enumerate(rows):
                    for xx, cc in enumerate(r):
                        if cc != SEE:
                            col = {TM: team[0], TS: team[1], CM: carc[0], CS: carc[1]}.get(cc, cc)
                            im.putpixel((x + dx + xx, y + dy + yy), PAL[col])


    dd = ImageDraw.Draw(im)
    wall = CT + (CB - CT) * 55 // 100
    dd.rectangle([0, CT, W, wall], fill=PAL[13])
    for x in range(0, W, 80):
        dd.line([x, CT, x, wall], fill=PAL[10], width=2)
    dd.rectangle([0, wall - 14, W, wall - 8], fill=PAL[5])
    dd.rectangle([0, wall, W, CB], fill=PAL[10])
    dd.line([0, wall, W, wall], fill=PAL[14], width=2)
    mw, mh, _, _, dw, dh, _, _, cw, chh, _, _ = info
    put("CarArt", (W - cw) // 2, CB - chh - 16)
    put("DrvArt", 14, CB - dh - 6)
    put("DrvArtF", 160, CB - dh - 6)
    put("MechArt", W - mw - 10, CB - mh - 6)
    im.save(os.path.join(ROOT, "assets", "pit_scene_preview.png"))
    print("art blocks:", ", ".join("%s %dx%d" % (b[0], b[1], b[2]) for b in blocks))
    print("runs:", sum(len(s) // 2 for b in blocks for s in rle(b[5])))


if __name__ == "__main__":
    main()
