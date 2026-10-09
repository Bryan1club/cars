# gen_login_bg.py -- generates login_bg.bmp, LoginPage's own background:
# the shared brushed panel PLUS the empty console trapezoid frame (same
# shape/silver rivet band as Menu's), with LoginPage's own fields drawn
# live on top inside it -- the first real page built against the owner's
# "the whole app is going to be in this dash board" / "so the login will
# have the empty dash and the button inside it". Run with:
# python gen_login_bg.py (needs Pillow). Not deployed to the board itself
# -- only its BMP output is.
#
# Deliberately a near-duplicate of gen_dash_bg.py's background-panel and
# trapezoid_panel()/rounded_polygon_points()/band_rivets() code rather
# than a shared import -- see gen_page_bg.py's own header for why (small
# standalone Pillow generators, not part of the runtime app).

from PIL import Image, ImageDraw
import random
import math

W, H = 640, 480
img = Image.new("RGB", (W, H), (0, 0, 0))
d = ImageDraw.Draw(img)

PANEL_MID = (44, 47, 50)
PANEL_LITE = (66, 70, 74)
CHROME_HI = (196, 200, 204)
CHROME_MID = (140, 144, 148)
CHROME_LO = (70, 73, 76)
STITCH = (12, 13, 14)
SILVER = (176, 180, 184)
# 2026-09-18: the owner, on real hardware, repeatedly: "the vertical lines are
# not lines they are small segments" / "still not a straight line" --
# widening the bar and boosting contrast (both tried first) didn't fix it,
# because neither was the actual cause. Read the board's own firmware
# source (dither.c) to find the real one: the on-device decode is
# row-by-row Floyd-Steinberg error diffusion, quantizing to the display's
# native RGB332 grid (R/G in 8 steps of 0/36/73/109/146/182/219/255, B in
# 4 steps of 0/85/170/255). CHROME_LO (70,73,76) doesn't land exactly on
# that grid, so every row carries a small rounding error down to the next
# -- fine for a 2D fill (the error scatters sideways too, and the noisy
# brushed_texture masks it), fatal for a solid vertical run: the error
# accumulates for ~400 rows straight down ONE column with nothing to
# break the periodicity, and periodically resets, reading as a break.
# Horizontal lines never showed this because they only span a single row,
# so there's no vertical accumulation. SEAM_SAFE is CHROME_LO rounded to
# the nearest EXACT grid point (73,73,85) -- visually identical, but
# dithers to itself with zero error on every row, so nothing accumulates
# no matter how long the run is.
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
    # 2026-09-20: the owner: "do the same treatment to the boiler plate
    # background so lets made new better one with alot more detial" --
    # brushed_texture() alone is pure horizontal streaks, reading a
    # little flat/uniform. A second pass of short streaks at a shallow
    # angle crossing the first gives the panel actual cross-grain depth
    # (like brushed metal caught at a different light angle) instead of
    # just one uniform direction.
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
    # small 3-bolt triangular cluster for the boilerplate's own dark
    # corners (outside the console entirely) -- the owner wanted "alot more
    # detail" generally; the console/rivet band already reads as the
    # focal point, these are a quiet accent so the corners aren't bare.
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


def chrome_band(draw, cx, top_y, bottom_y, top_half_w, bottom_half_w, radius=16, border=9):
    # 2026-09-18: the owner, on real hardware: "its the outside white band
    # going around" -- the console's outer edge (trapezoid_panel's old
    # flat 3px SILVER fill) read as plain flat white/grey on the actual
    # display, not chrome. Three concentric rounded-polygon rings instead
    # of one flat fill -- bright rim, silver mid, dark rim -- fakes a
    # rounded/polished bevel without true per-pixel gradient math. Wider
    # than the old 3px band (each ring needs enough real width to survive
    # dither=True decode on the actual screen, same lesson as the
    # vertical seam lines fragmenting when they were too thin/low
    # contrast) but still leaves the original 12px PANEL_MID groove
    # before the console's own inner sub-frame starts, so nothing else
    # needs to move.
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


def draw_aa_trapezoid(base_img, cx, top_y, bottom_y, top_half_w, bottom_half_w, face, hi, lo, radius=16, border=1, scale=4):
    # 2026-09-20: plain trapezoid_panel()'s polygon edges are hard/aliased
    # (PIL's draw.polygon has no anti-aliasing), and the rounded-corner
    # approximation (rounded_polygon_points' short straight arc_steps
    # segments) reads as faceted little triangles rather than a real
    # curve at any real contrast -- confirmed real on an actual zoomed
    # hardware photo: "smooth edges too on the angle parts" / "the
    # rivets go into the zagged line" / "a cheaply done first version
    # that has never been fixed". Draw on a blank RGBA canvas at
    # `scale`x resolution, downsample with LANCZOS (genuine
    # anti-aliasing), then paste back using its own alpha as the mask.
    # First proven on gen_help_bg.py, this is that fix propagated back
    # into the shared template every other page's background uses.
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
    small = hi_img.resize((w, h), Image.LANCZOS)
    base_img.paste(small, (x0, y0), small)


def draw_aa_console_frame(base_img, cx, top_y, bottom_y, top_half_w, bottom_half_w, face, radius=16, band_border=9, scale=4):
    # same technique as draw_aa_trapezoid, bundling trapezoid_panel's
    # outer rim + chrome_band's 3 concentric rings into one supersampled
    # canvas so all 4 nested layers get smoothed together.
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

    b1 = max(1, band_border // 3)
    b2 = (band_border * 2) // 3
    hd.polygon(rounded_polygon_points(quad(0), radius * scale, arc_steps=16), fill=CHROME_HI + (255,))
    hd.polygon(rounded_polygon_points(quad(b1), max(1, radius - b1) * scale, arc_steps=16), fill=SILVER + (255,))
    hd.polygon(rounded_polygon_points(quad(b2), max(1, radius - b2) * scale, arc_steps=16), fill=CHROME_LO + (255,))
    hd.polygon(rounded_polygon_points(quad(band_border), max(1, radius - band_border) * scale, arc_steps=16), fill=face + (255,))
    small = hi_img.resize((w, h), Image.LANCZOS)
    base_img.paste(small, (x0, y0), small)


def bolt(draw, cx, cy, r=3):
    # 2026-09-18: the owner: "make the back ground like a boiler plate" --
    # a flat single-colour dot read as a printed circle, not a fastener.
    # A real countersunk rivet/bolt head is a small dome: dark socket
    # shadow first, then the head itself with a highlight offset toward
    # the (fixed, upper-left) light source, same convention as the
    # switch-plate bezels' own HI/LO layering elsewhere in the app.
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
# soft overhead highlight, off-centre toward the top -- a second, smaller
# and brighter glow than the main vignette below, suggesting a light
# source rather than a flat radial falloff
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

# 2026-09-20: boiler-plate perimeter (side seams at x=13-15/W-16-14)
# removed -- the owner: "that large box frame needs to be deleted on every
# page" / confirmed it's this thin white full-height bar, not the
# console itself. Left the top/bottom seam above untouched.

# --- console frame -- same shape/position as Menu's, empty (LoginPage
# draws its own fields/buttons live on top, inside CONTENT_BOX below)
# 2026-09-18: the owner: "the dash board is too high so it impedes into the
# boiler plate" -- top edge was 54, nearly touching the new top rivet
# band (bolts at y=53). Dropped ~5mm (~16px at this screen's scale) to
# clear it -- was 54/66, now 70/82. Bottom edge (436/424) left alone,
# only the top narrowed further.
# 2026-09-18, second pass: briefly dropped a further ~16px (86/98) on a
# misreading of "reduce it down 5mm" as a second, additional 5mm on top
# of the first -- the owner: "that not 5 its 10 move it up to 5". Reverted
# back to 70/82 -- the total drop from the original 54/66 is one 5mm
# step, not two.
CONSOLE_CX = 320
CONSOLE_TOP_Y = 70
CONSOLE_INNER_TOP_Y = 82
# outer face still needs filling behind the chrome band (chrome_band only
# draws the rim itself, same as trapezoid_panel's old "lo" ring) -- plain
# trapezoid_panel() first for the PANEL_MID face/interior, chrome_band()
# on top for just the rim, same footprint.
# 2026-09-20: both trapezoid_panel()+chrome_band() (outer rim) and the
# inner trapezoid_panel() below switched to the anti-aliased versions --
# confirmed real on a zoomed hardware photo: "a cheaply done first
# version that has never been fixed" / "the rivets go into the zagged
# line". Same fix already proven on help_bg.bmp, now the shared template
# every other page's background (this file) uses.
draw_aa_console_frame(img, CONSOLE_CX, CONSOLE_TOP_Y, 436, 175, 233, face=PANEL_MID, radius=16, band_border=9)
d = ImageDraw.Draw(img)
_console_corners = [(CONSOLE_CX - 233, 436), (CONSOLE_CX + 233, 436),
                     (CONSOLE_CX + 175, CONSOLE_TOP_Y), (CONSOLE_CX - 175, CONSOLE_TOP_Y)]
# 2026-09-18: the owner, on real hardware: "the inner band where we have
# small circles not rivets" -- r=2 was too small for the dome
# highlight/shadow layering in bolt() to survive dither=True decode on
# the actual screen, same fragmentation lesson as the seam lines and the
# outer band above. Bumped to r=4, inset out to 9 to clear the now-wider
# chrome_band() rim instead of sitting on top of it.
band_rivets(d, _console_corners, spacing=30, inset=8, color=CHROME_LO, r=4)
draw_aa_trapezoid(img, CONSOLE_CX, CONSOLE_INNER_TOP_Y, 424, 155, 213, face=PANEL_LITE, hi=CHROME_MID, lo=CHROME_LO, border=1)
d = ImageDraw.Draw(img)

out_path = __file__.rsplit("\\", 1)[0] + "\\login_bg.bmp" if "\\" in __file__ else "login_bg.bmp"
img.save(out_path, "BMP")
print("wrote", out_path, img.size)
# content area (inner face): narrowest at top (y=82): x 157..483 (326 wide)
# widening to (y=424): x 99..541 (442 wide)
