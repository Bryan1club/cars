# gen_page_bg.py -- generates page_bg.bmp, the shared "brushed gunmetal
# panel" background every non-Menu page uses now (the owner: "I do like the
# menu river background so that can be used on every page" / "just the
# empty dash I mean" / "yes just the river edge and blank state"). Run
# with: python gen_page_bg.py (needs Pillow). Not deployed to the board
# itself -- only its BMP output is.
#
# Same base-panel look as gen_dash_bg.py's Menu background (brushed
# texture, vignette, top/bottom rivet seam) but WITHOUT the console,
# gauges, or switch plates -- those are Menu-specific content that would
# visually clash with every other page's own buttons/lists/forms drawn on
# top. This is deliberately a near-duplicate of gen_dash_bg.py's own
# "background panel" section rather than a shared import -- both scripts
# are standalone Pillow generators, not part of the runtime MicroPython
# app, so a little duplication here keeps each one simple to read on its
# own instead of introducing a shared-module dependency between two
# one-off asset scripts.

from PIL import Image, ImageDraw
import random

W, H = 640, 480
img = Image.new("RGB", (W, H), (0, 0, 0))
d = ImageDraw.Draw(img)

STITCH = (12, 13, 14)
CHROME_LO = (70, 73, 76)

random.seed(7)


def vgradient(draw, box, top, bottom):
    x0, y0, x1, y1 = box
    h = y1 - y0
    if h <= 0:
        return
    for i in range(h):
        t = i / h
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line((x0, y0 + i, x1, y0 + i), fill=(r, g, b))


def brushed_texture(draw, box, base, streaks=900):
    x0, y0, x1, y1 = box
    for _ in range(streaks):
        y = random.randint(y0, y1 - 1)
        x = random.randint(x0, x1 - 40)
        length = random.randint(10, 60)
        shade = random.randint(-10, 10)
        c = tuple(max(0, min(255, base[i] + shade)) for i in range(3))
        draw.line((x, y, min(x1, x + length), y), fill=c)


# --- background panel: brushed gunmetal with a soft vignette ---------------
vgradient(d, (0, 0, W, H), (36, 39, 42), (18, 19, 21))
brushed_texture(d, (0, 0, W, H), (30, 32, 35), streaks=1400)
vig = Image.new("L", (W, H), 0)
vd = ImageDraw.Draw(vig)
vd.ellipse((-160, -160, W + 160, H + 160), fill=60)
vd.ellipse((-40, -40, W + 40, H + 40), fill=0)
img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, vig)
d = ImageDraw.Draw(img)

# --- riveted seam lines top/bottom, like a dash panel edge -----------------
d.line((0, 56, W, 56), fill=STITCH)
d.line((0, 58, W, 58), fill=(52, 55, 58))
d.line((0, 444, W, 444), fill=(52, 55, 58))
d.line((0, 446, W, 446), fill=STITCH)
for rx in range(20, W, 40):
    d.ellipse((rx - 2, 51, rx + 2, 55), fill=CHROME_LO)
    d.ellipse((rx - 2, 447, rx + 2, 451), fill=CHROME_LO)

out_path = __file__.rsplit("\\", 1)[0] + "\\page_bg.bmp" if "\\" in __file__ else "page_bg.bmp"
img.save(out_path, "BMP")
print("wrote", out_path, img.size)
