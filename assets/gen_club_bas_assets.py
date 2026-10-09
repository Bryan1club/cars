# gen_club_bas_assets.py -- builds the assets club.bas (MMBasic) needs at
# 640x480 in MODE 3 (16 colours). Run with: python gen_club_bas_assets.py
# (needs Pillow, runs on Windows for the Comic Sans font).
#
# 1. page_bg_640.bmp -- page_bg.bmp reduced to 7 greys. MODE 3 turns every
#    pixel into a 4-bit slot from its top bits (R bit 7, G bits 7-6,
#    B bit 7), then MAP decides what colour each slot shows. So each pixel
#    is written as the "code" colour for slot 8..14, and the real grey for
#    that slot is written into club.bas as a MAP line.
# 2. Two DefineFont blocks from Comic Sans MS Italic (#9 for buttons/ticker/clock,
#    #10 for the title) plus each character's advance width, so club.bas
#    can space letters proportionally instead of in fixed-width cells.
#
# The MAP lines and the width tables go into mmbasic/generated.inc,
# which mmbasic/build.py joins onto every page. The DefineFont
# blocks go into clubfont9.bas and clubfont10.bas instead: this board
# only has 24K of program space, so the fonts live in the MMBasic
# library, where every program can use them. Install once per board,
# one file at a time (one file with both fonts is too big to LOAD):
#   LIBRARY DELETE, LOAD "clubfont9.bas", LIBRARY SAVE,
#   LOAD "clubfont10.bas", LIBRARY SAVE

from PIL import Image, ImageDraw, ImageFont
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GEN_INC = os.path.join(HERE, "..", "mmbasic", "generated.inc")
FONT_BAS = os.path.join(HERE, "..", "clubfont%d.bas")

FONT_FILE = "C:/Windows/Fonts/comici.ttf"
# (MMBasic font number, pixel size, last character). The title font
# stops at "Z": it only shows the club name, the time and the date, and
# the full set is too big to LOAD on this board.
FONTS = [(9, 12, 126), (10, 18, 90)]
FIRST, LAST = 32, 126
# The 16 colour slots (MAP n = colour), shared by every page:
#   0 black, 15 near-white -- the mouse pointer's own black and white
#   1/2 green top/base, 3/4 red top/base, 5 amber (the selected button)
#   6..14 nine panel greys, chosen from the backgrounds themselves
UI_SLOTS = {0: (0, 0, 0), 1: (67, 160, 71), 2: (46, 125, 50), 3: (226, 75, 74),
            4: (168, 40, 40), 5: (255, 176, 0), 15: (232, 234, 237)}
GREY_SLOTS = list(range(6, 15))
# (source art, board file): the dash for the menu, the plain boiler-plate
# panel for every other page
BACKGROUNDS = [("dash_bg.bmp", "menu_bg.bmp"), ("page_bg.bmp", "page_bg_640.bmp")]


def slot_code(i):
    """An RGB colour that MODE 3 turns into slot i."""
    return (0x80 if i & 8 else 0, ((i >> 1) & 3) << 6, 0x80 if i & 1 else 0)


def make_backgrounds():
    """both backgrounds in the 16 slots; returns [(slot, grey)] for 6..14"""
    srcs = [Image.open(os.path.join(HERE, a)).convert("RGB") for a, _ in BACKGROUNDS]
    # one set of greys that suits both images, darkest in the lowest slot
    both = Image.new("RGB", (srcs[0].width, srcs[0].height * len(srcs)))
    for n, im in enumerate(srcs):
        both.paste(im, (0, n * im.height))
    q = both.quantize(colors=len(GREY_SLOTS), method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = q.getpalette()[:3 * len(GREY_SLOTS)]
    greys = sorted((tuple(pal[i * 3:i * 3 + 3]) for i in range(len(GREY_SLOTS))), key=sum)
    slots = dict(UI_SLOTS)
    slots.update({GREY_SLOTS[n]: g for n, g in enumerate(greys)})
    flat = [c for s in range(16) for c in slots[s]]
    palimg = Image.new("P", (1, 1))
    palimg.putpalette(flat + [0] * (768 - len(flat)))
    for (art, board), src in zip(BACKGROUNDS, srcs):
        # nearest of the panel greys only -- the UI colours are for buttons
        greypal = Image.new("P", (1, 1))
        gflat = [c for s in GREY_SLOTS for c in slots[s]]
        greypal.putpalette(gflat + [0] * (768 - len(gflat)))
        idx = src.quantize(palette=greypal, dither=Image.Dither.NONE).load()
        out = Image.new("RGB", src.size)
        prev = Image.new("RGB", src.size)
        op, pp = out.load(), prev.load()
        for y in range(src.size[1]):
            for x in range(src.size[0]):
                s = GREY_SLOTS[idx[x, y]]
                op[x, y] = slot_code(s)
                pp[x, y] = slots[s]
        out.save(os.path.join(HERE, board))
        prev.save(os.path.join(HERE, board.replace(".bmp", "_preview.png")))
    return [(s, slots[s]) for s in GREY_SLOTS]


def make_font(num, size, last):
    font = ImageFont.truetype(FONT_FILE, size)
    ascent, descent = font.getmetrics()
    chars = [chr(c) for c in range(FIRST, LAST + 1)]
    adv = [max(1, round(font.getlength(ch))) for ch in chars]
    chars = chars[:last - FIRST + 1]
    w = max(adv[:len(chars)])
    h = ascent + descent
    while (w * h) % 8:
        h += 1
    bits = []
    for ch in chars:
        img = Image.new("1", (w, h), 0)
        d = ImageDraw.Draw(img)
        d.fontmode = "1"
        d.text((0, 0), ch, font=font, fill=1)
        px = img.load()
        for y in range(h):
            for x in range(w):
                bits.append(1 if px[x, y] else 0)
    data = bytearray([w, h, FIRST, len(chars)])
    for i in range(0, len(bits), 8):
        b = 0
        for bit in bits[i:i + 8]:
            b = (b << 1) | bit
        data.append(b)
    while len(data) % 4:
        data.append(0)
    words = ["%08X" % int.from_bytes(data[i:i + 4], "little") for i in range(0, len(data), 4)]
    lines = ["DefineFont #%d" % num]
    for i in range(0, len(words), 8):
        lines.append("  " + " ".join(words[i:i + 8]))
    lines.append("End DefineFont")
    return lines, adv, h


def main():
    greys = make_backgrounds()
    out = ["' --- generated.inc: written by assets/gen_club_bas_assets.py, don't edit", ""]
    out.append("' the nine panel greys (slots 6-14) the backgrounds use")
    out.append("Sub MapGreys")
    for slot, (r, g, b) in greys:
        out.append("  MAP %d = RGB(%d,%d,%d)" % (slot, r, g, b))
    out.append("End Sub")
    out.append("")
    out.append("FontWidths:")
    for n, (num, size, last) in enumerate(FONTS):
        lines, adv, h = make_font(num, size, last)
        out.append("' font #%d: Comic Sans MS Italic %dpx, cell height %d, then the" % (num, size, h))
        out.append("' advance width of each character from CHR$(32) to CHR$(126)")
        out.append("Data %d" % h)
        for i in range(0, len(adv), 24):
            out.append("Data " + ",".join(str(a) for a in adv[i:i + 24]))
        fonts = ["' clubfont%d.bas -- font #%d for club.bas, generated by" % (num, num),
                 "' assets/gen_club_bas_assets.py. Goes in the library, see there.", ""]
        fonts.extend(lines)
        with open(FONT_BAS % num, "w", newline="\r\n") as f:
            f.write("\n".join(fonts) + "\n")
    with open(GEN_INC, "w", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print("greys:", greys)


if __name__ == "__main__":
    main()
