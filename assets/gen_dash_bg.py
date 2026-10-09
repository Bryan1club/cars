# gen_dash_bg.py -- generates dash_bg.bmp, the illustrated "car dash"
# background for club.py's Menu page. Run with: python gen_dash_bg.py
# (needs Pillow). Not deployed to the board itself -- only its BMP
# output is.
#
# Deliberately flat/illustrated, not a photo: the board's display only
# renders 256 colors (RGB640 mode) via a dither pass in firmware
# (bmp.c/dither.c), and flat panel art with a handful of tones dithers
# far cleaner than a photograph would. Switch plates are drawn WITHOUT
# their text labels -- club.py draws those live on top at the same grid
# positions (see Menu.build()), so the art stays reusable regardless of
# label text/length.
#
# Grid must match Menu's LEFT_BUTTONS/RIGHT_BUTTONS layout exactly
# (col_w=130, col_h=40, col_gap=6, col_y0=64, left_x=16, right_x=494)
# or the tap zones won't line up with what's drawn.

from PIL import Image, ImageDraw
import random
import math

W, H = 640, 480
img = Image.new("RGB", (W, H), (0, 0, 0))
d = ImageDraw.Draw(img)

# --- palette (kept close to club.py's existing DASH_BG/DASH_TEXT/BTN/RED) ---
PANEL_DARK = (28, 30, 32)
PANEL_MID = (44, 47, 50)
PANEL_LITE = (66, 70, 74)
CHROME_HI = (196, 200, 204)
CHROME_MID = (140, 144, 148)
CHROME_LO = (70, 73, 76)
SWITCH_FACE = (18, 19, 20)
SWITCH_FACE_LIT = (30, 32, 34)
ACCENT_ORANGE = (216, 90, 48)   # DASH_CLOCK_ACCENT
STITCH = (12, 13, 14)
# 2026-09-18: same fix as gen_login_bg.py's identical constant -- the owner,
# on real hardware, repeatedly: "the vertical lines are not lines they
# are small segments" / "still not a straight line". Root cause, found by
# reading the firmware's actual dither.c: row-by-row Floyd-Steinberg
# error diffusion to the display's native RGB332 grid (R/G in steps of
# 0/36/73/109/146/182/219/255, B in steps of 0/85/170/255). CHROME_LO
# (70,73,76) isn't on that grid, so a tiny rounding error carries down
# every row -- invisible in a 2D fill, but a ~400-row-tall single-column
# vertical bar accumulates it with nothing to break the periodicity,
# reading as a break. SEAM_SAFE is CHROME_LO rounded to the nearest EXACT
# grid point -- dithers to itself with zero error every row.
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
    # new better one with alot more detial". A second pass of short
    # streaks at a shallow angle crossing the horizontal ones gives the
    # panel actual cross-grain depth instead of one uniform direction.
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


def rrect_bevel(draw, box, radius, face, hi, lo, border=2):
    x0, y0, x1, y1 = box
    # outer chrome bezel (bright top-left -> dark bottom-right bevel)
    draw.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=lo)
    draw.rounded_rectangle((x0, y0, x1 - border, y1 - border), radius=radius, fill=hi)
    # inset face
    ix0, iy0, ix1, iy1 = x0 + border, y0 + border, x1 - border, y1 - border
    draw.rounded_rectangle((ix0, iy0, ix1, iy1), radius=max(1, radius - border), fill=face)
    return ix0, iy0, ix1, iy1


def rounded_polygon_points(points, radius, arc_steps=6):
    # generic rounded-corner outline for an arbitrary (convex) polygon --
    # PIL has rounded_rectangle but nothing for a rounded trapezoid, so
    # this builds one: at each vertex, replace the sharp corner with an
    # arc tangent to both adjacent edges. Standard construction -- the
    # arc's centre sits on the interior angle bisector, at distance
    # radius/sin(half-angle) from the vertex; the two tangent points sit
    # at distance `radius` from the vertex along each edge.
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
        # walk from a1 to a2 the short way around
        diff = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        out.append(t1)
        for step in range(1, arc_steps):
            a = a1 + diff * step / arc_steps
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        out.append(t2)
    return out


def switch_plate(draw, x, y, w, h, nub_side="left"):
    # chrome bezel + dark inset face + a small raised toggle nub, no text
    # (club.py draws the label on top of the face at runtime). Bezel
    # radius/border and nub size all scale off h (2026-09-18, when the
    # buttons themselves were halved) rather than staying fixed, so this
    # keeps looking like a switch instead of a rounded blob at the
    # smaller size.
    #
    # nub_side (2026-09-18): the owner -- "the one on the right need the
    # silver button moved to the other side so its more like a dash
    # theme". Mirrored per-column below (right_x's own switch_plate()
    # calls pass "right"), so the upper 4+4 grid reads as a symmetric
    # dash panel -- left-bank toggles on the left, right-bank on the
    # right -- instead of every plate having its nub on the same side
    # regardless of which half of the console it sits in.
    bezel_radius = max(3, h // 6)
    border = 2 if h >= 30 else 1
    ix0, iy0, ix1, iy1 = rrect_bevel(draw, (x, y, x + w, y + h), radius=bezel_radius,
                                      face=SWITCH_FACE, hi=CHROME_HI, lo=CHROME_LO, border=border)
    # subtle top-lit sheen across the inset face
    vgradient(draw, (ix0 + 1, iy0 + 1, ix1 - 1, iy0 + (iy1 - iy0) // 3),
              SWITCH_FACE_LIT, SWITCH_FACE)
    # toggle nub -- small vertical pill at the chosen edge, suggesting a
    # flip switch, chrome-rimmed
    nub_w = max(4, w // 16)
    nub_h = max(4, h - h // 3)
    if nub_side == "right":
        nx0 = ix1 - max(2, w // 22) - nub_w
    else:
        nx0 = ix0 + max(2, w // 22)
    ny0 = y + (h - nub_h) // 2
    nub_radius = max(1, nub_w // 2)
    draw.rounded_rectangle((nx0, ny0, nx0 + nub_w, ny0 + nub_h), radius=nub_radius, fill=CHROME_MID)
    draw.rounded_rectangle((nx0 + 1, ny0 + 1, nx0 + nub_w - 1, ny0 + nub_h // 2), radius=max(1, nub_radius - 1), fill=CHROME_HI)
    # thin engraved divider between the nub and where the label sits
    if nub_side == "right":
        draw.line((nx0 - 5, y + 6, nx0 - 5, y + h - 6), fill=CHROME_LO)
    else:
        draw.line((nx0 + nub_w + 5, y + 6, nx0 + nub_w + 5, y + h - 6), fill=CHROME_LO)


def draw_aa_trapezoid(base_img, cx, top_y, bottom_y, top_half_w, bottom_half_w, face, hi, lo, radius=16, border=1, scale=4):
    # 2026-09-20: same fix as gen_login_bg.py's identical function --
    # confirmed real on a zoomed hardware photo: "a cheaply done first
    # version that has never been fixed" / "the rivets go into the
    # zagged line". Supersample + LANCZOS-downsample for genuine
    # anti-aliasing instead of plain aliased polygon edges.
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
    # 2026-09-18: same fix as gen_login_bg.py's identical function -- a
    # flat single-colour dot read as a printed circle, not a fastener.
    # Dark socket shadow, then the head, then a highlight offset toward
    # the fixed upper-left light source, same HI/LO layering convention
    # as the switch-plate bezels.
    draw.ellipse((cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1), fill=(20, 21, 23))
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=CHROME_LO)
    draw.ellipse((cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1), fill=CHROME_MID)
    hr = max(1, r - 2)
    draw.ellipse((cx - hr - 1, cy - hr - 1, cx - 1, cy - 1), fill=CHROME_HI)


def chrome_band(draw, cx, top_y, bottom_y, top_half_w, bottom_half_w, radius=16, border=9):
    # 2026-09-18: same fix as gen_login_bg.py's identical function -- the
    # console's outer edge read as flat white/grey, not chrome. Three
    # concentric rounded-polygon rings (bright rim / silver mid / dark
    # rim) fake a rounded bevel without true per-pixel gradient math.
    # SILVER is defined later, at the console section below -- fine, only
    # resolved when this function actually runs, well after that point.
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


# --- background panel: brushed gunmetal with a soft vignette ---------------
vgradient(d, (0, 0, W, H), (36, 39, 42), (18, 19, 21))
brushed_texture(d, (0, 0, W, H), (30, 32, 35), streaks=1400)
cross_brushed_texture(d, (0, 0, W, H), (33, 35, 38), streaks=700)
glow = Image.new("L", (W, H), 0)
gd = ImageDraw.Draw(glow)
gd.ellipse((W // 2 - 260, -180, W // 2 + 260, 160), fill=26)
img = Image.composite(img, Image.new("RGB", (W, H), (52, 56, 60)), glow.point(lambda v: 255 - v))
d = ImageDraw.Draw(img)
# corner vignette (cheap: four dark radial-ish rects blended via ellipses)
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

# (the small title plaque at (200,26)-(240,46) that club.py drew text on
# was removed 2026-09-25 -- nothing in the MMBasic menu uses it and it
# showed as an empty box -- the owner)

# --- centre console: one housing shared by the clock and the RAM gauge
# (2026-09-18, from the owner's hand-drawn concept sketch -- a single rounded
# console box between the two switch columns, both gauges inset into it,
# with the footer ticker relocated into a bar underneath them, inside the
# same housing). Menu draws rim/numerals/hands/needle/ticks live on top
# every tick (see club.py) -- everything here is just the static housing.

def trapezoid_panel(draw, cx, top_y, bottom_y, top_half_w, bottom_half_w, face, hi, lo, radius=16, border=3):
    # rounded trapezoid panel, tapering narrower at the top to match
    # the owner's hand-drawn concept sketch (base width : top width roughly
    # 200 : 150, i.e. top_half_w should be about 0.75x bottom_half_w).
    # Same "bordered face inset from an outer shape" idea as rrect_bevel(),
    # just polygon-based (via rounded_polygon_points) instead of
    # rounded_rectangle-based.
    outer = [(cx - bottom_half_w, bottom_y), (cx + bottom_half_w, bottom_y),
              (cx + top_half_w, top_y), (cx - top_half_w, top_y)]
    draw.polygon(rounded_polygon_points(outer, radius), fill=lo, outline=hi)
    inset = border
    inner = [(cx - bottom_half_w + inset, bottom_y - inset), (cx + bottom_half_w - inset, bottom_y - inset),
              (cx + top_half_w - inset, top_y + inset), (cx - top_half_w + inset, top_y + inset)]
    draw.polygon(rounded_polygon_points(inner, max(1, radius - border)), fill=face)


def band_rivets(draw, corners, spacing=26, inset=6, color=CHROME_LO, r=2):
    # evenly spaced rivet dots walking each straight edge of a polygon,
    # inset toward its centroid -- used to populate the silver bezel band
    # below with rivets, same look as the top/bottom screen-edge seam's
    # own rivet dots, just running around the console instead
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
            draw.ellipse((px - r, py - r, px + r, py + r), fill=color)


# 2026-09-18: widened to fill most of the screen -- the old 154..486 span
# was sized to fit between the two outer switch columns, but those moved
# INTO the console itself the same day (see the switch grid below), so
# that width constraint no longer applies. Went too wide on the first
# attempt (300/225 half-widths) -- pulled back halfway to the original
# 166/125.
CONSOLE_CX = 320
# bottom extended 2026-09-18 (390 -> 436) for more room now the side
# buttons are much shorter -- 8px clear of the bottom rivet seam at 444
#
# 2026-09-18: outer bezel recoloured to a proper bright SILVER (was
# CHROME_LO, a dark grey meant as a bevel shadow, not a band colour) --
# the owner: "a nice thin band with rivets inside and a silver colour". The
# existing 12px gap between this outer trapezoid and the inner one below
# it (166/125 vs 154/113) IS the band; rivets are added into that same
# gap, not a new layer.
SILVER = (176, 180, 184)
# 2026-09-18: top edge dropped 54 -> 70, one 5mm/16px pass, same as the
# identical fix on gen_login_bg.py's console -- the owner: "the dash board is
# too high so it impedes into the boiler plate". (A second drop to 86 was
# briefly applied on a misreading of a follow-up "reduce it down 5mm" as
# an additional step rather than a correction of the first -- the owner:
# "that not 5 its 10 move it up to 5" -- reverted back to 70.) Inner
# trapezoid follows the same 12px offset it always had (66 -> 82). Bottom
# edge (436/424) untouched. Gauges at CY=150/r=48 (below) still clear this
# comfortably (top edge now 70, gauge top ~102).
CONSOLE_TOP_Y = 70
CONSOLE_INNER_TOP_Y = 82
# 2026-09-20: anti-aliased versions -- same fix as gen_login_bg.py/
# gen_help_bg.py, confirmed real on a zoomed hardware photo: "a cheaply
# done first version that has never been fixed".
draw_aa_console_frame(img, CONSOLE_CX, CONSOLE_TOP_Y, 436, 175, 233, face=PANEL_MID, radius=16, band_border=9)
d = ImageDraw.Draw(img)
_console_corners = [(CONSOLE_CX - 233, 436), (CONSOLE_CX + 233, 436),
                     (CONSOLE_CX + 175, CONSOLE_TOP_Y), (CONSOLE_CX - 175, CONSOLE_TOP_Y)]
band_rivets(d, _console_corners, spacing=30, inset=8, color=CHROME_LO, r=4)
draw_aa_trapezoid(img, CONSOLE_CX, CONSOLE_INNER_TOP_Y, 424, 155, 213, face=PANEL_LITE, hi=CHROME_MID, lo=CHROME_LO, border=1)
d = ImageDraw.Draw(img)


def gauge_housing(draw, cx, cy, cr):
    # chrome ring bezel for one circular gauge -- same ring style the
    # clock alone used to get, now shared by both the clock and the new
    # RAM gauge so they read as a matched pair
    draw.ellipse((cx - cr - 10, cy - cr - 10, cx + cr + 10, cy + cr + 10), fill=CHROME_HI)
    draw.ellipse((cx - cr - 6, cy - cr - 6, cx + cr + 6, cy + cr + 6), fill=CHROME_LO)
    # 2026-09-18: two failed attempts at a near-black fill here already
    # ((10,11,12), then SWITCH_FACE) both confirmed real hardware to still
    # read brown -- likely this display's RGB640 dither/palette biasing
    # warm on large areas of near-equal-RGB near-black, not a specific bad
    # value. Switched to PAGE (0x5C6268 -> (92,98,104)), the one grey
    # that's been neutral everywhere else in this app for months, rather
    # than guessing a fourth dark tone.
    draw.ellipse((cx - cr - 2, cy - cr - 2, cx + cr + 2, cy + cr + 2), fill=(92, 98, 104))
    for a in range(0, 360, 30):
        rx = cx + (cr + 8) * math.cos(math.radians(a))
        ry = cy + (cr + 8) * math.sin(math.radians(a))
        d.ellipse((rx - 2, ry - 2, rx + 2, ry + 2), fill=CHROME_MID)


# must match club.py Menu.CLOCK_CX/CY/FACE_R and RAM_GAUGE_CX/CY/FACE_R --
# moved up 2026-09-18 to match the owner's sketch, which sat both gauges close
# under the console's top edge with a big open gap above the ticker below.
# CX pulled in and radius trimmed the same day when the console became a
# trapezoid (narrower at the top, see trapezoid_panel() above) -- the
# original 250/390 centres at r=52 overhung the now-narrower top edge at
# y=150 (available half-width there is ~124px, the old pair needed ~132).
# Pushed further apart again the same day -- the owner: "move the 2 gauges
# further apart as they are too close" -- 260/380 (120 apart) widened to
# 230/410 (180 apart); at y=150 the inner console edge is ~176px each
# side of centre, comfortably clearing a 48-radius gauge centred at
# either new spot (~38px to spare on each outer edge).
gauge_housing(d, 230, 150, 48)
gauge_housing(d, 410, 150, 48)

# --- switch grid: MUST match Menu.LEFT_BUTTONS/RIGHT_BUTTONS exactly ------
# 2026-09-18: moved off the side columns entirely, into the console itself
# (the owner: "let's put each button in the dash") -- two 4-row sub-columns
# side by side directly under the gauges, above the ticker. ADMIN/QUIT/
# MUSIC split out into their own BOTTOM_BUTTONS row below the ticker
# instead (the owner: "I only want admin quit and for now music put under the
# ticker then the rest go above it").
col_w, col_h, col_gap = 110, 20, 3
col_y0 = 216
left_x = 190
right_x = 340
for i in range(4):
    switch_plate(d, left_x, col_y0 + i * (col_h + col_gap), col_w, col_h, nub_side="left")
    switch_plate(d, right_x, col_y0 + i * (col_h + col_gap), col_w, col_h, nub_side="right")

# ticker bar housing -- between the upper 4-row grid and BOTTOM_BUTTONS
# moved down again 2026-09-18 to centre it in the gap between the upper
# grid (ends y=305) and BOTTOM_BUTTONS (starts y=398, moved down the same
# day)
TICKER_BOX = (182, 334, 458, 368)
rrect_bevel(d, TICKER_BOX, radius=4, face=SWITCH_FACE, hi=CHROME_MID, lo=CHROME_LO, border=1)

# BOTTOM_BUTTONS row: ADMIN, QUIT, MUSIC -- MUST match Menu.BOTTOM_BUTTONS
# and its bot_w/bot_h/bot_gap/bot_x0/bot_y0 exactly
bot_w, bot_h, bot_gap = 90, 20, 10
bot_x0, bot_y0 = 175, 398
for i in range(3):
    switch_plate(d, bot_x0 + i * (bot_w + bot_gap), bot_y0, bot_w, bot_h)

# orange accent pinstripe REMOVED 2026-09-18 -- sat at y=50, in the
# console's old un-dropped top area. Once the top rivet seam (y=53/56/58)
# and the console itself (now dropped to top_y=86) moved into that same
# band, this stray line cut straight across the new boiler-plate rivet
# seam -- the owner: "now there is a red line going over the top of the
# dashboard". No repositioning attempted -- the rivet seam already reads
# as the edge treatment there; a second accent line competing with it in
# the same tight space was the problem, not just its old position.

out_path = __file__.rsplit("\\", 1)[0] + "\\dash_bg.bmp" if "\\" in __file__ else "dash_bg.bmp"
img.save(out_path, "BMP")
print("wrote", out_path, img.size)
