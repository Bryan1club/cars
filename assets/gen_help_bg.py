# gen_help_bg.py -- generates help_bg.bmp, HelpPage's own background.
# Same shared brushed-panel + console trapezoid frame as login_bg.bmp/
# dash_bg.bmp, but the inner content trapezoid is filled a light "page"
# colour instead of PANEL_LITE -- the owner: "now in help a white single
# page tapered to suit the dashboard can be used" / "the help txt can
# be also done to suit this tapered white page". Same taper (same
# CONSOLE_CX/trapezoid_panel call, same x/y numbers) as every other
# page's console -- only the inner face colour changes, so HelpPage's
# text column still lines up with the standard x=170..470 content
# column exactly like before. Run with: python gen_help_bg.py (needs
# Pillow). Not deployed to the board itself -- only its BMP output is.
#
# Deliberately a near-duplicate of gen_login_bg.py/gen_dash_bg.py's
# background-panel and trapezoid_panel()/rounded_polygon_points()/
# band_rivets() code rather than a shared import -- see gen_page_bg.py's
# own header for why (small standalone Pillow generators, not part of
# the runtime app).

from PIL import Image, ImageDraw
import random
import math

W, H = 640, 480
img = Image.new("RGB", (W, H), (0, 0, 0))
d = ImageDraw.Draw(img)

PANEL_MID = (44, 47, 50)
PANEL_LITE = (66, 70, 74)
# 2026-09-20: PANEL_LITE's replacement for this variant only -- a light
# "page" colour instead of the usual medium-grey inner face. Chosen on
# the display's own native RGB332 dither grid (R/G steps of 0/36/73/
# 109/146/182/219/255) the same way SEAM_SAFE was, so it dithers to
# itself with no per-row rounding error instead of banding. help_page.py
# uses this exact value (0xDBDBDB) as both fg background-match colour
# and the fallback plain fill, so captions blend into it seamlessly
# instead of each showing its own highlighted box -- the owner: "all the
# text is highlighted which I dont want as it looks cheap".
PAGE_PANEL = (219, 219, 219)
CHROME_HI = (196, 200, 204)
CHROME_MID = (140, 144, 148)
CHROME_LO = (70, 73, 76)
STITCH = (12, 13, 14)
SILVER = (176, 180, 184)
SEAM_SAFE = (73, 73, 85)

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


def cross_brushed_texture(draw, box, base, streaks=500, angle_deg=18):
    # 2026-09-20: same as gen_login_bg.py's identical function -- the owner:
    # "do the same treatment to the boiler plate background so lets made
    # new better one with alot more detial".
    x0, y0, x1, y1 = box
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    for _ in range(streaks):
        x = random.randint(x0, x1)
        y = random.randint(y0, y1)
        length = random.randint(15, 45)
        shade = random.randint(-8, 8)
        c = tuple(max(0, min(255, base[i] + shade)) for i in range(3))
        ex, ey = x + dx * length, y + dy * length
        draw.line((x, y, ex, ey), fill=c)


def corner_bolt_cluster(draw, cx, cy, spread=14):
    for ang in (90, 210, 330):
        a = math.radians(ang)
        bolt(draw, cx + spread * math.cos(a), cy + spread * math.sin(a), r=2)


def rounded_polygon_points(points, radius, arc_steps=6):
    n = len(points)
    out = []
    for i in range(n):
        px, py = points[i]
        ax, ay = points[(i - 1) % n]
        bx, by = points[(i + 1) % n]
        v1x, v1y = ax - px, ay - py
        v2x, v2y = bx - px, by - py
        len1 = (v1x * v1x + v1y * v1y) ** 0.5
        len2 = (v2x * v2x + v2y * v2y) ** 0.5
        u1x, u1y = v1x / len1, v1y / len1
        u2x, u2y = v2x / len2, v2y / len2
        r = min(radius, len1 / 2, len2 / 2)
        t1 = (px + u1x * r, py + u1y * r)
        t2 = (px + u2x * r, py + u2y * r)
        dot = max(-1.0, min(1.0, u1x * u2x + u1y * u2y))
        angle = math.acos(dot)
        half = angle / 2
        if half < 1e-6:
            out.append((px, py))
            continue
        dist = r / math.sin(half)
        bx2, by2 = u1x + u2x, u1y + u2y
        blen = (bx2 * bx2 + by2 * by2) ** 0.5
        cx, cy = px + (bx2 / blen) * dist, py + (by2 / blen) * dist
        a1 = math.atan2(t1[1] - cy, t1[0] - cx)
        a2 = math.atan2(t2[1] - cy, t2[0] - cx)
        diff = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        out.append(t1)
        for step in range(1, arc_steps):
            a = a1 + diff * step / arc_steps
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        out.append(t2)
    return out


def trapezoid_panel(draw, cx, top_y, bottom_y, top_half_w, bottom_half_w, face, hi, lo, radius=16, border=3):
    outer = [(cx - bottom_half_w, bottom_y), (cx + bottom_half_w, bottom_y),
              (cx + top_half_w, top_y), (cx - top_half_w, top_y)]
    draw.polygon(rounded_polygon_points(outer, radius), fill=lo, outline=hi)
    inset = border
    inner = [(cx - bottom_half_w + inset, bottom_y - inset), (cx + bottom_half_w - inset, bottom_y - inset),
              (cx + top_half_w - inset, top_y + inset), (cx - top_half_w + inset, top_y + inset)]
    draw.polygon(rounded_polygon_points(inner, max(1, radius - border)), fill=face)


def draw_aa_trapezoid(base_img, cx, top_y, bottom_y, top_half_w, bottom_half_w, face, hi, lo, radius=16, border=1, scale=4,
                       paper_grain=False):
    # 2026-09-20: plain trapezoid_panel()'s polygon edges are hard/aliased
    # (PIL's draw.polygon has no anti-aliasing), and the rounded-corner
    # approximation (rounded_polygon_points' short straight arc_steps
    # segments) reads as faceted little triangles rather than a real
    # curve at any real contrast -- confirmed real: "smooth edges too on
    # the angle parts" / "as small triangles too". Standard fix: draw the
    # same two polygons on a blank RGBA canvas at `scale`x resolution
    # (so the faceted/jagged edges are far finer), downsample with a
    # high-quality resampling filter (LANCZOS averages many high-res
    # pixels into one, producing genuine anti-aliasing), then paste back
    # using its own alpha as the mask. Only used for the two inner
    # panels below (grey face + white page) -- the outer console frame
    # elsewhere is untouched, unrelated to this specific complaint.
    pad = 6
    x0, y0 = int(cx - bottom_half_w - pad), int(top_y - pad)
    x1, y1 = int(cx + bottom_half_w + pad), int(bottom_y + pad)
    w, h = x1 - x0, y1 - y0
    hi_img = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hi_img)

    def shift(pts):
        return [((px - x0) * scale, (py - y0) * scale) for px, py in pts]

    outer = shift([(cx - bottom_half_w, bottom_y), (cx + bottom_half_w, bottom_y),
                   (cx + top_half_w, top_y), (cx - top_half_w, top_y)])
    hd.polygon(rounded_polygon_points(outer, radius * scale, arc_steps=16), fill=lo + (255,), outline=hi + (255,))
    inset = border
    inner = shift([(cx - bottom_half_w + inset, bottom_y - inset), (cx + bottom_half_w - inset, bottom_y - inset),
                   (cx + top_half_w - inset, top_y + inset), (cx - top_half_w + inset, top_y + inset)])
    hd.polygon(rounded_polygon_points(inner, max(1, radius - border) * scale, arc_steps=16), fill=face + (255,))
    if paper_grain:
        # 2026-09-20: the owner: "I want to look like a peice of paper was
        # put in so get some graphics done" -- a flat solid fill read as
        # plastic, not paper. Faint speckle (barely-there +-4 shade
        # variation, low density), but must be CLIPPED to the actual
        # (tapered, not rectangular) inner polygon -- a first attempt
        # just scattered across its bounding box leaked speckle dots
        # onto the dark metal outside the taper at the corners, each one
        # opaque against full transparency there. inner (pre-rounding)
        # is a simple convex quadrilateral -- a per-point inside test
        # against its 4 edges (cross-product sign, same winding for
        # all four) is enough, the rounded corners it approximates only
        # shave a couple of px off each corner.
        def _inside(px, py):
            n = len(inner)
            sign = None
            for i in range(n):
                ax, ay = inner[i]
                bx, by = inner[(i + 1) % n]
                cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
                if sign is None:
                    sign = cross >= 0
                elif (cross >= 0) != sign:
                    return False
            return True

        ix0, iy0 = min(p[0] for p in inner), min(p[1] for p in inner)
        ix1, iy1 = max(p[0] for p in inner), max(p[1] for p in inner)
        tries = int((ix1 - ix0) * (iy1 - iy0) / (60 * scale * scale))
        placed = 0
        attempts = 0
        while placed < tries and attempts < tries * 4:
            attempts += 1
            px = random.uniform(ix0, ix1)
            py = random.uniform(iy0, iy1)
            r = scale * random.uniform(0.5, 1.5)
            if not _inside(px, py) or not _inside(px, py - r) or not _inside(px, py + r):
                continue
            shade = random.randint(-4, 4)
            c = tuple(max(0, min(255, face[i] + shade)) for i in range(3)) + (255,)
            hd.ellipse((px - r, py - r, px + r, py + r), fill=c)
            placed += 1
    small = hi_img.resize((w, h), Image.LANCZOS)
    base_img.paste(small, (x0, y0), small)


def chrome_band(draw, cx, top_y, bottom_y, top_half_w, bottom_half_w, radius=16, border=9):
    outer = [(cx - bottom_half_w, bottom_y), (cx + bottom_half_w, bottom_y),
              (cx + top_half_w, top_y), (cx - top_half_w, top_y)]
    draw.polygon(rounded_polygon_points(outer, radius), fill=CHROME_HI)
    b1 = max(1, border // 3)
    mid = [(cx - bottom_half_w + b1, bottom_y - b1), (cx + bottom_half_w - b1, bottom_y - b1),
            (cx + top_half_w - b1, top_y + b1), (cx - top_half_w + b1, top_y + b1)]
    draw.polygon(rounded_polygon_points(mid, max(1, radius - b1)), fill=SILVER)
    b2 = (border * 2) // 3
    dark = [(cx - bottom_half_w + b2, bottom_y - b2), (cx + bottom_half_w - b2, bottom_y - b2),
             (cx + top_half_w - b2, top_y + b2), (cx - top_half_w + b2, top_y + b2)]
    draw.polygon(rounded_polygon_points(dark, max(1, radius - b2)), fill=CHROME_LO)


def draw_aa_console_frame(base_img, cx, top_y, bottom_y, top_half_w, bottom_half_w, face, radius=16, band_border=9, scale=4):
    # 2026-09-20: the OUTER console rim (trapezoid_panel + chrome_band's
    # 3 concentric rings) has never been anti-aliased since the very
    # first version of this generator -- confirmed real, zoomed in on an
    # actual photo: "a cheaply done first version that has never been
    # fixed" / "the rivets go into the zagged line". Same supersample +
    # LANCZOS-downsample fix as draw_aa_trapezoid, just bundling all 4
    # concentric layers (PANEL_MID face, CHROME_HI/SILVER/CHROME_LO
    # rings) into one canvas so they all get smoothed together, not
    # each ring re-jaggedizing the one under it.
    pad = 6
    x0, y0 = int(cx - bottom_half_w - pad), int(top_y - pad)
    x1, y1 = int(cx + bottom_half_w + pad), int(bottom_y + pad)
    w, h = x1 - x0, y1 - y0
    hi_img = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hi_img)

    def shift(pts):
        return [((px - x0) * scale, (py - y0) * scale) for px, py in pts]

    def quad(inset):
        return shift([(cx - bottom_half_w + inset, bottom_y - inset), (cx + bottom_half_w - inset, bottom_y - inset),
                      (cx + top_half_w - inset, top_y + inset), (cx - top_half_w + inset, top_y + inset)])

    # 4 nested filled polygons, outermost to innermost -- matches the
    # original trapezoid_panel()+chrome_band() combination's actual
    # visible result exactly (chrome_band's 3 rings are drawn ON TOP of
    # trapezoid_panel's own outer rim, so only its face fill beyond
    # band_border ever shows through underneath).
    b1 = max(1, band_border // 3)
    b2 = (band_border * 2) // 3
    hd.polygon(rounded_polygon_points(quad(0), radius * scale, arc_steps=16), fill=CHROME_HI + (255,))
    hd.polygon(rounded_polygon_points(quad(b1), max(1, radius - b1) * scale, arc_steps=16), fill=SILVER + (255,))
    hd.polygon(rounded_polygon_points(quad(b2), max(1, radius - b2) * scale, arc_steps=16), fill=CHROME_LO + (255,))
    hd.polygon(rounded_polygon_points(quad(band_border), max(1, radius - band_border) * scale, arc_steps=16), fill=face + (255,))
    small = hi_img.resize((w, h), Image.LANCZOS)
    base_img.paste(small, (x0, y0), small)


def bolt(draw, cx, cy, r=3):
    draw.ellipse((cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1), fill=(20, 21, 23))
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=CHROME_LO)
    draw.ellipse((cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1), fill=CHROME_MID)
    hr = max(1, r - 2)
    draw.ellipse((cx - hr - 1, cy - hr - 1, cx - 1, cy - 1), fill=CHROME_HI)


def band_rivets(draw, corners, spacing=26, inset=6, color=CHROME_LO, r=2):
    n = len(corners)
    ccx = sum(p[0] for p in corners) / n
    ccy = sum(p[1] for p in corners) / n
    for i in range(n):
        ax, ay = corners[i]
        bx, by = corners[(i + 1) % n]
        edge_len = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        steps = max(1, int(edge_len // spacing))
        ex, ey = (bx - ax) / edge_len, (by - ay) / edge_len
        nx, ny = -ey, ex
        midx, midy = (ax + bx) / 2, (ay + by) / 2
        if (ccx - midx) * nx + (ccy - midy) * ny < 0:
            nx, ny = -nx, -ny
        for s in range(1, steps):
            t = s / steps
            px = ax + (bx - ax) * t + nx * inset
            py = ay + (by - ay) * t + ny * inset
            bolt(draw, px, py, r=r)


# --- background panel: brushed gunmetal with a soft vignette ---------------
vgradient(d, (0, 0, W, H), (36, 39, 42), (18, 19, 21))
brushed_texture(d, (0, 0, W, H), (30, 32, 35), streaks=1400)
cross_brushed_texture(d, (0, 0, W, H), (33, 35, 38), streaks=700)
glow = Image.new("L", (W, H), 0)
gd = ImageDraw.Draw(glow)
gd.ellipse((W // 2 - 260, -180, W // 2 + 260, 160), fill=26)
img = Image.composite(img, Image.new("RGB", (W, H), (52, 56, 60)), glow.point(lambda v: 255 - v))
d = ImageDraw.Draw(img)
vig = Image.new("L", (W, H), 0)
vd = ImageDraw.Draw(vig)
vd.ellipse((-160, -160, W + 160, H + 160), fill=60)
vd.ellipse((-40, -40, W + 40, H + 40), fill=0)
img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, vig)
d = ImageDraw.Draw(img)
for cx, cy in ((28, 26), (W - 28, 26), (28, H - 26), (W - 28, H - 26)):
    corner_bolt_cluster(d, cx, cy)

# --- riveted seam lines top/bottom, like a dash panel edge -----------------
d.line((0, 56, W, 56), fill=STITCH)
d.line((0, 58, W, 58), fill=(52, 55, 58))
d.line((0, 444, W, 444), fill=(52, 55, 58))
d.line((0, 446, W, 446), fill=STITCH)
for rx in range(20, W, 40):
    bolt(d, rx, 53, r=3)
    bolt(d, rx, 449, r=3)

# --- console frame -- same shape/position as every other page's --------
CONSOLE_CX = 320
CONSOLE_TOP_Y = 70
CONSOLE_INNER_TOP_Y = 82
draw_aa_console_frame(img, CONSOLE_CX, CONSOLE_TOP_Y, 436, 175, 233, face=PANEL_MID, radius=16, band_border=9)
d = ImageDraw.Draw(img)
_console_corners = [(CONSOLE_CX - 233, 436), (CONSOLE_CX + 233, 436),
                     (CONSOLE_CX + 175, CONSOLE_TOP_Y), (CONSOLE_CX - 175, CONSOLE_TOP_Y)]
band_rivets(d, _console_corners, spacing=30, inset=8, color=CHROME_LO, r=4)
# 2026-09-20: the white page used to run the console's FULL inner
# trapezoid (82..424), overlapping the MENU_Y=92 switch-plate row --
# confirmed real: "white board too big as the top menu system has to
# be above it". Standard grey inner panel drawn first (82..424, same as
# every other page, so the menu tiles at y=92 sit on the normal metal
# console face), THEN a smaller white "page" on top of it for just the
# content area below the menu row (124..424 -- ROW_TOP down to the
# console's own bottom). Its top half-width (170) is interpolated along
# the SAME taper line as the outer trapezoid (163 at y=82, 221 at
# y=424), not a separately-guessed number, so it's still one continuous
# cone shape, just a shorter slice of it.
draw_aa_trapezoid(img, CONSOLE_CX, CONSOLE_INNER_TOP_Y, 424, 155, 213, face=PANEL_LITE, hi=CHROME_MID, lo=CHROME_LO, border=1)
d = ImageDraw.Draw(img)
# border 1 -> 4: a slightly thicker dark rim reads as the paper sitting
# recessed into the console with a soft shadow at its own edge, not
# just a flat colour change -- the owner: "look like a peice of paper was
# put in". paper_grain=True adds the speckle texture (see
# draw_aa_trapezoid's own comment).
draw_aa_trapezoid(img, CONSOLE_CX, 124, 424, 162, 213, face=PAGE_PANEL, hi=CHROME_MID, lo=CHROME_LO, border=4, paper_grain=True)
d = ImageDraw.Draw(img)

out_path = __file__.rsplit("\\", 1)[0] + "\\help_bg.bmp" if "\\" in __file__ else "help_bg.bmp"
img.save(out_path, "BMP")
print("wrote", out_path, img.size)
