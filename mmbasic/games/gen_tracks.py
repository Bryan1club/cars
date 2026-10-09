# gen_tracks.py -- the racing game's circuits, from real track layouts.
#
# Source: assets/f1-circuits.geojson from github.com/bacinger/f1-circuits
# (MIT licence, Copyright (c) 2019-2025 Tomislav Bacinger; see
# assets/f1-circuits.LICENSE.md). Unofficial data, not endorsed by Formula
# One Licensing B.V. -- the game just uses the circuits' names.
#
# Each circuit: map coordinates flattened, turned to whichever angle fills
# the screen best (north-up unless turning it makes it clearly bigger),
# 50 points spaced evenly along it from the start/finish line in race
# order, fitted to the game's raw box (BuildTrack scales that dynamically
# onto however much of the actual screen it has, whatever the resolution
# -- but a track this box is proportioned much wider than the play area
# ends up bound by width with real height left unused, so every corner on
# every circuit is that bit tighter than it needs to be. BOX's aspect
# ratio (520:333, 1.56) is board 2's own 640x480 play area with its
# margins already taken out (see BuildTrack's TRACK_MARGIN), so a track's
# natural shape gets to use all of both dimensions rather than being
# bottlenecked by whichever's tighter -- smooths the 50 points into 100).
# Written into racing.bas between its TRACKS BEGIN / TRACKS END markers.
# Run: python mmbasic/games/gen_tracks.py   (then python mmbasic/build.py)
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "assets", "f1-circuits.geojson")
NL = chr(10)
N = 50
BOX = (40, 20, 560, 353)

# the current calendar, in race order: (dataset id, name shown in the game)
CALENDAR = [("au-1953", "Albert Park"), ("cn-2004", "Shanghai"), ("jp-1962", "Suzuka"),
            ("bh-2002", "Bahrain"), ("sa-2021", "Jeddah"), ("us-2022", "Miami"),
            ("it-1953", "Imola"), ("mc-1929", "Monaco"), ("es-1991", "Barcelona"),
            ("ca-1978", "Montreal"), ("at-1969", "Red Bull Ring"), ("gb-1948", "Silverstone"),
            ("be-1925", "Spa"), ("hu-1986", "Hungaroring"), ("nl-1948", "Zandvoort"),
            ("it-1922", "Monza"), ("az-2016", "Baku"), ("sg-2008", "Singapore"),
            ("us-2012", "Austin COTA"), ("mx-1962", "Mexico City"), ("br-1940", "Interlagos"),
            ("us-2023", "Las Vegas"), ("qa-2004", "Lusail"), ("ae-2009", "Yas Marina")]


def resample(pts, n):
    """n points evenly spaced round the closed loop pts, from pts[0]"""
    loop = pts + [pts[0]]
    seg = [math.dist(loop[i], loop[i + 1]) for i in range(len(pts))]
    total = sum(seg)
    out, i, run = [], 0, 0.0
    for k in range(n):
        want = total * k / n
        while run + seg[i] < want:
            run += seg[i]
            i += 1
        t = (want - run) / seg[i] if seg[i] else 0
        out.append((loop[i][0] + (loop[i + 1][0] - loop[i][0]) * t,
                    loop[i][1] + (loop[i + 1][1] - loop[i][1]) * t))
    return out


def declutter(pts, min_gap, iters=40):
    """nudges apart any two points (not near each other along the path)
    that end up closer than min_gap once fitted to the screen. Real
    circuits (Jeddah especially) run two stretches of track close enough
    in real life that, simplified and scaled down to game-screen size,
    the road (TRACK_W=32px wide in racing.bas) draws as one merged blob
    instead of two separate strips -- this pulls them apart just enough
    to read as two roads, at the cost of being slightly less true to the
    real layout right at that spot"""
    pts = [list(p) for p in pts]
    n = len(pts)
    for _ in range(iters):
        moved = False
        for i in range(n):
            for j in range(i + 1, n):
                # points near each other ALONG the path are supposed to be
                # close (that's just the road curving) -- only push apart
                # points from different, unrelated parts of the circuit
                if min(j - i, n - (j - i)) < 4:
                    continue
                dx, dy = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
                dist = math.hypot(dx, dy)
                if 0 < dist < min_gap:
                    push = (min_gap - dist) / 2
                    ux, uy = dx / dist, dy / dist
                    pts[i][0] -= ux * push
                    pts[i][1] -= uy * push
                    pts[j][0] += ux * push
                    pts[j][1] += uy * push
                    moved = True
        if not moved:
            break
    return [(round(x), round(y)) for x, y in pts]


def smooth_window(pts, lo, hi, passes=4):
    """3-point moving average over pts[lo..hi] (inclusive), lo and hi held
    fixed so it blends into the rest of the lap either side. 50 points
    round a whole real circuit is coarse enough that a genuinely tight
    real-world esses -- direction changing every 20-30m, at Monaco -- can
    alias into a zigzag no car (or the collision code, which assumes a
    locally straight-ish road) can actually read as one bend; several
    passes turn that zigzag into the single smooth sweep it should be"""
    pts = [list(p) for p in pts]
    idxs = range(lo, hi + 1)
    for _ in range(passes):
        new = {i: ((pts[i - 1][0] + pts[i][0] + pts[i + 1][0]) / 3,
                    (pts[i - 1][1] + pts[i][1] + pts[i + 1][1]) / 3)
               for i in idxs if i != lo and i != hi}
        for i, p in new.items():
            pts[i] = list(p)
    return [(round(x), round(y)) for x, y in pts]


# per-track fixes, applied after declutter: (lo, hi) windows (inclusive,
# post-declutter indices), one or more per track, that alias into an
# unreadable zigzag and need smoothing over. Squeezing a whole real
# circuit into just 50 points means a genuinely tight run of esses --
# direction changing every 20-30m in real life -- can come out as several
# consecutive points each turning 60-140 degrees, which reads as a
# flat-out U-turn (or several) rather than the one bend it should be, and
# was the single biggest trigger of collision pile-ups. Found by scanning
# every circuit for 2+ consecutive points over 60 degrees (a single sharp
# point on its own, e.g. Spa's La Source or Suzuka's hairpin, is a real
# hairpin and left alone -- only a genuine multi-point zigzag is a
# resampling artifact rather than the track's actual shape); windows
# widened by hand from there until the whole cluster smoothed out cleanly.
# Monaco: Massenet/Casino/Mirabeau/Fairmont, right after the start/finish
EASE_ZIGZAG = {
    "mc-1929": [(2, 10)],                     # Monaco
    "cn-2004": [(23, 30)],                     # Shanghai
    "bh-2002": [(17, 22), (21, 26)],           # Bahrain
    "sa-2021": [(17, 22), (43, 47)],           # Jeddah
    "es-1991": [(15, 20), (19, 24), (37, 42)], # Barcelona
    "gb-1948": [(41, 47)],                     # Silverstone
    "hu-1986": [(41, 46)],                     # Hungaroring
    "nl-1948": [(28, 33)],                     # Zandvoort
    "us-2012": [(18, 23), (28, 40)],           # Austin COTA
    "br-1940": [(25, 31), (30, 34)],           # Interlagos (2nd window: a real
                                                # single hairpin, but the owner
                                                # confirmed it pile-up-causing
                                                # tight in play, so smoothed too
    "qa-2004": [(19, 24)],                     # Lusail
    "ae-2009": [(10, 15), (32, 37)],           # Yas Marina
}


def fit(pts):
    """turned and scaled into BOX: (points, angle)"""
    bw, bh = BOX[2] - BOX[0], BOX[3] - BOX[1]

    def scale_at(a):
        c, s = math.cos(a), math.sin(a)
        r = [(x * c - y * s, x * s + y * c) for x, y in pts]
        xs, ys = [p[0] for p in r], [p[1] for p in r]
        return min(bw / (max(xs) - min(xs)), bh / (max(ys) - min(ys))), r

    best_a, best_s = 0.0, scale_at(0.0)[0]
    for deg in range(0, 360, 15):
        s = scale_at(math.radians(deg))[0]
        if s > best_s * 1.15:
            best_a, best_s = math.radians(deg), s
    s, r = scale_at(best_a)
    xs, ys = [p[0] for p in r], [p[1] for p in r]
    ox = BOX[0] + (bw - (max(xs) - min(xs)) * s) / 2 - min(xs) * s
    oy = BOX[1] + (bh - (max(ys) - min(ys)) * s) / 2 - min(ys) * s
    return [(round(x * s + ox), round(y * s + oy)) for x, y in r], math.degrees(best_a)


feats = {f["properties"]["id"]: f for f in json.load(open(SRC, encoding="utf-8"))["features"]}
lines = ["' circuit layouts from github.com/bacinger/f1-circuits (MIT licence,",
         "' (c) 2019-2025 Tomislav Bacinger), written by games/gen_tracks.py:",
         "' how many, then per circuit its name and %d x,y points in race order" % N,
         "Tracks:", "Data %d" % len(CALENDAR)]
for tid, name in CALENDAR:
    coords = feats[tid]["geometry"]["coordinates"]
    lat0 = math.radians(sum(c[1] for c in coords) / len(coords))
    # flat metres-ish: x east, y south (screen y grows downwards)
    flat = [(c[0] * math.cos(lat0) * 111320, -c[1] * 110540) for c in coords]
    if math.dist(flat[0], flat[-1]) < 1:
        flat = flat[:-1]
    # TRACK_W (racing.bas) is 32px wide; +8 leaves a visible gap between
    # two strips of road instead of them just barely not touching
    pts, ang = fit(resample(flat, N))
    pts = declutter(pts, 32 + 8)
    for lo, hi in EASE_ZIGZAG.get(tid, []):
        pts = smooth_window(pts, lo, hi)
    lines.append('Data "%s"' % name)
    for k in range(0, N, 12):
        lines.append("Data " + ", ".join("%d,%d" % p for p in pts[k:k + 12]))
    print("%-14s turned %3d deg" % (name, ang))

rb = os.path.join(HERE, "racing.bas")
text = open(rb).read()
a = text.index("' TRACKS BEGIN")
a = text.index(NL, a) + 1
b = text.index("' TRACKS END")
open(rb, "w", newline=NL).write(text[:a] + NL.join(lines) + NL + text[b:])

# a look at them all
try:
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (6 * 180, 4 * 120), (30, 74, 30))
    d = ImageDraw.Draw(im)
    for n, (tid, name) in enumerate(CALENDAR):
        coords = feats[tid]["geometry"]["coordinates"]
        lat0 = math.radians(sum(c[1] for c in coords) / len(coords))
        flat = [(c[0] * math.cos(lat0) * 111320, -c[1] * 110540) for c in coords]
        pts, _ = fit(resample(flat, N))
        pts = declutter(pts, 32 + 8)
        ox, oy = (n % 6) * 180, (n // 6) * 120
        sc = 170 / 560
        p = [(ox + 5 + (x - 40) * sc, oy + 14 + (y - 20) * sc) for x, y in pts]
        d.line(p + [p[0]], fill=(96, 96, 96), width=4)
        d.ellipse([p[0][0] - 3, p[0][1] - 3, p[0][0] + 3, p[0][1] + 3], fill=(232, 234, 237))
        d.text((ox + 4, oy + 2), name, fill=(255, 176, 0))
    im.save(os.path.join(HERE, "..", "..", "assets", "tracks_preview.png"))
except ImportError:
    pass
