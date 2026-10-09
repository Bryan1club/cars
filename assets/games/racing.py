# racing.py -- a real game for the GAMES launcher in club.py
# Drop this into /sd/Games.
#
# Same architecture/constraints as snake.py (the other example game in this
# folder), proven on this hardware -- standalone (hdmi/pcgui/time only, no
# club.py imports, since GAMES launcher exec()'s this in a fresh namespace),
# button-driven UI (continuous mouse-drag/on_move is confirmed NOT to work
# on this hardware), incremental per-tick drawing rather than clearing the
# whole screen every frame.
#
# Spectator/betting game, not a driving game (2026-09-08 redesign) -- every
# car is AI-controlled with a freshly randomized pace each race, you PICK
# one before the start (tapping a car's button both picks it and starts the
# race) and then just watch -- same "no way to know the winner in advance"
# guarantee as before, just expressed as picking a runner rather than
# steering one.
#
# Track is a stylized (not GPS-accurate) loop evoking Monaco's shape -- the
# most recognizable F1 circuit, tight and winding, good fit for a small
# screen. Cars move along the track's arc length ("progress") with a fixed
# lateral offset from the centreline (keeps them apart visually, no
# overtaking physics needed) rather than free 2D physics -- keeps the math
# to "walk along a polyline" instead of a real physics engine, same
# complexity trade-off snake.py made with grid cells instead of pixel
# collision.

import hdmi
import pcgui
import time

PAGE = 0x102010
INK = 0xFFFFFF
BTN = 0x2E7D32
RED = 0xCC3333
TRACK_COLOUR = 0x606060
TRACK_EDGE = 0x707070  # softened 2026-09-08 (was 0x888888) -- real ask: the
# boundary line read as too hard/stark against the track surface (0x606060);
# a smaller contrast step reads as a boundary without the harsh outline
GRASS_COLOUR = 0x1E4A1E
CAR_COLOURS = (0xFFCC00, 0x3388FF, 0xFF4444, 0x33CC33, 0xCC66FF)  # 5 runners
CAR_NAMES = ("HOLDEN", "FORD", "HONDA", "SUBARU", "TOYOTA")  # real brands,
# 2026-09-08 (were colour names) -- still just labels/colours under the
# hood, not real makes/models or liveries; see the 3D-model idea for that

# -- multiplayer betting economy (2026-09-08 real ask) -- hot-seat, named
# players with a persistent budget each (saved to a file, so it carries
# over between sessions). Each player who wants in on a race pays
# ENTRY_FEE into the event pot; the event runs EVENT_RACES races before
# paying out (see the "event" system below). A random cost event (see
# roll_random_event) can also hit each entrant after every race,
# independent of whether they won -- "so if the budget is down a full
# race can't be run" is enforced by simply refusing entry to anyone below
# ENTRY_FEE.
PLAYERS_FILE = "/sd/Games/racing_players.dat"
CARS_FILE = "/sd/Games/racing_cars.dat"
ENTRY_FEE = 200.0  # was 20 -- scaled up 2026-09-08 alongside STARTING_BUDGET
# so the pooled event prize stays meaningful next to car purchase prices
STARTING_BUDGET = 20000.0  # was 100 -- real ask 2026-09-08: big enough to
# actually buy into CAR_VALUES below and survive a few bad damage events
EVENT_RACES = 5  # real ask 2026-09-08: "make an event of 5 races for big
# prize money" -- the pot no longer pays out every single race, it builds
# across EVENT_RACES races and pays out once at the end (see `event` /
# advance()'s end-of-race block)

# cars now range in value -- real ask 2026-09-08 ("cars can range in value
# now the cars that cost more will also cop more damage than a cheaper
# car"). Buying an unowned car is a one-time capital cost from CAR_VALUES;
# once bought a player owns it persistently (see cars_data below) until
# damage/RANDOM_EVENTS wear it down. Damage cost scales off the car's own
# value, not a flat fee, so a Toyota crash actually stings more than a
# Holden one.
CAR_VALUES = (4000.0, 6000.0, 9000.0, 13000.0, 18000.0)  # matches CAR_NAMES order

# weighted random event rolled once per entrant after each race resolves,
# regardless of whether they won -- a genuine mix of severities, not one
# tier: (weight, cost as a fraction of the car's own value, description or
# None). Also adds persistent damage% to the car itself (see advance()).
RANDOM_EVENTS = (
    (50, 0.0, None),
    (30, 0.05, "minor tune-up"),
    (15, 0.15, "engine trouble"),
    (5, 0.35, "crash damage"),
)


def roll_random_event():
    total = 0
    for w, _frac, _desc in RANDOM_EVENTS:
        total += w
    r = rand_below(total)
    acc = 0
    for w, frac, desc in RANDOM_EVENTS:
        acc += w
        if r < acc:
            return frac, desc
    return 0.0, None


def load_players():
    try:
        f = open(PLAYERS_FILE)
        text = f.read()
        f.close()
    except OSError:
        return []
    out = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) >= 2:
            try:
                out.append({"name": parts[0], "budget": float(parts[1])})
            except ValueError:
                pass
    return out


def save_players():
    try:
        f = open(PLAYERS_FILE, "w")
        for p in players:
            f.write("%s,%g\n" % (p["name"], p["budget"]))
        f.close()
    except OSError as e:
        # best-effort -- a failed save shouldn't crash the game, just means
        # budgets won't carry over to the next session
        pass


players = load_players()


def load_cars_data():
    # persistent per-car ownership + damage -- real ask 2026-09-08 ("open a
    # new car owners page so the mechanic can relay the damage"), separate
    # file from players since this is data about the 5 cars, not about who
    # is playing tonight. owner is a player name (or "" / missing = unowned)
    try:
        f = open(CARS_FILE)
        text = f.read()
        f.close()
    except OSError:
        return [{"owner": None, "damage": 0.0} for _ in CAR_NAMES]
    out = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) >= 2:
            owner = parts[0] if parts[0] else None
            try:
                out.append({"owner": owner, "damage": float(parts[1])})
            except ValueError:
                out.append({"owner": owner, "damage": 0.0})
    while len(out) < len(CAR_NAMES):
        out.append({"owner": None, "damage": 0.0})
    return out[:len(CAR_NAMES)]


def save_cars_data():
    try:
        f = open(CARS_FILE, "w")
        for d in cars_data:
            f.write("%s,%g\n" % (d["owner"] or "", d["damage"]))
        f.close()
    except OSError:
        pass  # best-effort, same as save_players()


cars_data = load_cars_data()

try:
    import random
    def rand_below(n):
        return random.randint(0, n - 1)
    def rand_float():
        return random.random()
except ImportError:
    # same fallback PRNG as snake.py -- random.randint()/random() aren't
    # used anywhere else in this project, so availability on this board's
    # MicroPython build is unverified
    _seed = [(time.ticks_us() & 0xFFFF) or 1]
    def _next():
        x = _seed[0]
        x ^= (x << 7) & 0xFFFF
        x ^= (x >> 9)
        x ^= (x << 8) & 0xFFFF
        _seed[0] = x & 0xFFFF
        return x
    def rand_below(n):
        return _next() % n
    def rand_float():
        return _next() / 65536.0


def fb_line(fb, x0, y0, x1, y1, colour, width=1):
    try:
        if width <= 1:
            fb.line(int(x0), int(y0), int(x1), int(y1), colour)
            return
        # crude thick line: offset parallel 1px lines perpendicular to the
        # segment -- good enough for a track edge or a car body, no need
        # for a real polygon-fill approach here. Real bug found 2026-09-08:
        # steps=int(width) spaces adjacent offset lines ~1.03px apart at
        # width=32 (the track surface) -- juuust over 1px, so pixel-
        # snapping (the int() below) left thin gaps between some of them,
        # showing the grass colour through and reading as the track being
        # "multi-coloured" rather than solid. Also affected draw_car
        # (width=3, only 3 steps -> 1.5px gaps), reported separately as
        # cars "leaving parts" / looking like they were shrinking -- same
        # root cause, this one function used everywhere thick lines are
        # drawn. First attempt (1.3x oversampling) still landed exactly on
        # 1.0px spacing at width=3, the same risky boundary, just less bad
        # -- 2x with a safety +1 keeps every width's spacing at or under
        # 0.5px, comfortably past the rounding-gap boundary rather than
        # sitting right on it.
        dx, dy = x1 - x0, y1 - y0
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1e-6:
            return
        nx, ny = -dy / length, dx / length
        half = width / 2.0
        steps = max(1, int(width * 2) + 1)
        for s in range(steps):
            t = -half + width * s / max(1, steps - 1) if steps > 1 else 0
            ox, oy = nx * t, ny * t
            fb.line(int(x0 + ox), int(y0 + oy), int(x1 + ox), int(y1 + oy), colour)
    except Exception:
        pass


def fill_dot(fb, x, y, r, colour):
    for dy in range(-r, r + 1):
        w = int((r * r - dy * dy) ** 0.5) if r * r >= dy * dy else 0
        fb_line(fb, x - w, y + dy, x + w, y + dy, colour)


def draw_car(fb, cx, cy, tx, ty, colour):
    # a real car shape (2026-09-08, was a plain dot) -- a short thick line
    # along the direction of travel (tx,ty must be a unit vector), reusing
    # fb_line's width support rather than a separate polygon-fill routine.
    # Reads as a small oriented body rather than a circular blob. Size
    # here is load-bearing, not just cosmetic -- it's part of the lane/
    # edge clearance math below (TRACK_WIDTH/LATERAL_LIMIT), so don't bump
    # it up without re-checking that.
    hl = 3.0  # half-length, nose to tail
    fb_line(fb, cx - tx * hl, cy - ty * hl, cx + tx * hl, cy + ty * hl, colour, width=3)


# -- track: hand-placed shape, then scaled up to use nearly the full screen
# instead of a cramped corner -- real ask 2026-09-08, once the track and
# the button row were found to actually overlap at the smaller size (see
# TRACK_WIDTH's comment below): scale the whole thing up and give the
# button row (BTN_Y) and status row their own checked-clear strips instead
# of a tight fit.
_RAW = [
    (60, 40), (260, 30), (320, 20), (380, 30), (420, 70), (400, 110),
    (330, 120), (300, 150), (330, 180), (420, 190), (470, 160), (520, 170),
    (560, 210), (540, 260), (460, 270), (420, 240), (360, 250), (320, 290),
    (260, 300), (180, 290), (140, 250), (150, 200), (100, 180), (60, 140),
    (40, 90),
]
_RAW_MINX, _RAW_MINY = 40, 20  # bounding box of _RAW above (520 wide, 280 tall)
_SCALE = 1.1  # -> 572x308 scaled -- can't go much higher: the track's own
# tightest corner (a 42.4px gap between two non-adjacent segments at 1x
# scale) needs to stay wider than TRACK_WIDTH once scaled, or the road
# visually overlaps itself; 1.1 is close to the ceiling that still leaves
# real margin there (see the printed check this was verified against).
_TARGET_X0, _TARGET_Y0 = 30, 86  # track's top-left after scaling -- 86
# clears the compact command row (ends at 56) with real margin


def _scaled(pt):
    x, y = pt
    return (_TARGET_X0 + (x - _RAW_MINX) * _SCALE, _TARGET_Y0 + (y - _RAW_MINY) * _SCALE)


def _chaikin(points, iterations=2):
    # corner-cutting smoothing (2026-09-08, real ask: cars visibly snapped
    # direction at every waypoint since the track was plain straight
    # segments) -- each iteration replaces every edge with two points at
    # 1/4 and 3/4 along it, which rounds every corner using only linear
    # interpolation, no trig/arc math needed. 2 iterations turns 25 points
    # into 100 -- drawn once at startup, not per-tick, so the extra points
    # cost nothing that matters (unlike the earlier GRID_MAX_LINES issue,
    # which was about a per-tick redraw cost, not a one-time draw).
    pts = list(points)
    for _ in range(iterations):
        n = len(pts)
        new_pts = []
        for i in range(n):
            p0, p1 = pts[i], pts[(i + 1) % n]
            new_pts.append((0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1]))
            new_pts.append((0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1]))
        pts = new_pts
    return pts


_CORNERS = [_scaled(p) for p in _RAW]  # pre-smoothing corners, kept for
# sand-trap placement below (post-smoothing points don't cleanly
# correspond to the original hand-placed corners any more)
WAYPOINTS = _chaikin(_CORNERS, iterations=2)
TRACK_WIDTH = 32  # px, full width -- real bug found 2026-09-08: at the
# ORIGINAL width (22, edges at +-11) a car's erase-dot reached the edge
# line and permanently painted over it with flat track colour (the edge is
# only drawn once, never restored), visibly "wiping out the road" wherever
# a car had driven near the boundary. Pulled back from an earlier attempt
# at 44 -- the Chaikin smoothing above (real ask, smoother cornering)
# turned out to tighten the track's closest self-approach in a way that
# was hard to measure reliably (naive segment-distance checks gave false
# positives against genuinely adjacent segments), so this stays
# conservative rather than trusting an unreliable number.
# real ask 2026-09-08: "single laps or a full race and everything between"
# -- LAPS_OPTIONS is the cycle set, laps_to_win (lowercase, mutable state
# in `state` below) is the current pick, defaulting to the middle-ish
# option (3) rather than the smallest or largest
LAPS_OPTIONS = (1, 2, 3, 5, 8, 10)
LATERAL_OFFSETS = (-12.0, -6.0, 0.0, 6.0, 12.0)  # starting positions only --
# see LATERAL_LIMIT/LATERAL_DRIFT_STEP below, cars don't stay in these lanes
LATERAL_LIMIT = 12.0  # with TRACK_WIDTH=32 and the radius-3 car body below:
# edge clearance = 16-12-3 = 1px, lane gap = 24/4 = 6 = exactly 2*radius
# (touching, not overlapping) -- thin margins, chosen deliberately tight
# rather than widening TRACK_WIDTH again after the smoothing pass made
# self-overlap risk hard to measure reliably at a wider value
LATERAL_DRIFT_STEP = 0.5  # px/tick max change -- real ask 2026-09-08: real
# cars don't hold a fixed lane all race, so this makes lateral position a
# slow random walk instead of a constant, letting cars weave and pass
# rather than run in permanent parallel lanes
MIN_CAR_PROGRESS_GAP = 8.0  # real bug found 2026-09-08: only track EDGES had
# clearance math, cars had none against each other -- two cars could drift
# to the same lateral offset while close together in progress (drafting)
# and their bodies would visibly overlap, reported as "blue car is going
# over the yellow car" (always the same car on top, since the draw loop
# always processes cars in the same fixed index order). See the
# separation pass in advance() -- these two gaps are the "close enough to
# push apart" window, not a hard collision (real cars don't collide here).
MIN_CAR_LATERAL_GAP = 7.0

# commands moved into a compact top row + hidden pick list (2026-09-08,
# was a full-width button row along the bottom) -- track now gets nearly
# the whole screen below that row instead of giving up its bottom third
CONTENT_TOP = 56
CONTENT_BOTTOM = 460

# -- sand traps, real ask 2026-09-08 -- placed at the sharpest corners
# (computed, not guessed): sharpness is how closely the incoming and
# outgoing edges at a corner point back toward each other (a near-U-turn
# scores near +1, a near-straight-through point scores near -1), and
# "outward" is approximated as away from the track loop's own centroid --
# a reasonable heuristic for a roughly-convex loop like this one, not a
# general solution for any track shape.
SAND_COLOUR = 0xD2B48C
SAND_TRAP_COUNT = 4
SAND_TRAP_RADIUS = 12


def _corner_sharpness(pts, i):
    n = len(pts)
    a, p, b = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
    v1 = (a[0] - p[0], a[1] - p[1])
    v2 = (b[0] - p[0], b[1] - p[1])
    l1 = (v1[0] ** 2 + v1[1] ** 2) ** 0.5 or 1.0
    l2 = (v2[0] ** 2 + v2[1] ** 2) ** 0.5 or 1.0
    return (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)


def _build_sand_traps():
    cx = sum(p[0] for p in _CORNERS) / len(_CORNERS)
    cy = sum(p[1] for p in _CORNERS) / len(_CORNERS)
    ranked = sorted(range(len(_CORNERS)), key=lambda i: -_corner_sharpness(_CORNERS, i))
    traps = []
    for i in ranked[:SAND_TRAP_COUNT]:
        p = _CORNERS[i]
        dx, dy = p[0] - cx, p[1] - cy
        dlen = (dx * dx + dy * dy) ** 0.5 or 1.0
        ox, oy = dx / dlen, dy / dlen
        tx = p[0] + ox * (TRACK_WIDTH / 2.0 + 10)
        ty = p[1] + oy * (TRACK_WIDTH / 2.0 + 10)
        # real bug found 2026-09-08: one corner sits close enough to the
        # screen edge that projecting outward from it landed a trap almost
        # off-screen (x~633 against a 640px width) -- clamp into the same
        # safe drawable area everything else uses
        tx = max(SAND_TRAP_RADIUS + 2, min(640 - SAND_TRAP_RADIUS - 2, tx))
        ty = max(CONTENT_TOP + SAND_TRAP_RADIUS, min(CONTENT_BOTTOM - SAND_TRAP_RADIUS, ty))
        traps.append((tx, ty))
    return traps


SAND_TRAPS = _build_sand_traps()

# precompute segment lengths and cumulative arc length for progress->point
_seg_len = []
_cum = [0.0]
for _i in range(len(WAYPOINTS)):
    _a = WAYPOINTS[_i]
    _b = WAYPOINTS[(_i + 1) % len(WAYPOINTS)]
    _d = ((_b[0] - _a[0]) ** 2 + (_b[1] - _a[1]) ** 2) ** 0.5
    _seg_len.append(_d)
    _cum.append(_cum[-1] + _d)
TRACK_LENGTH = _cum[-1]


def _locate(progress):
    # shared segment lookup for track_point/track_tangent/restore_track_at
    # below -- also returns the segment index now (2026-09-08, needed so
    # restore_track_at knows exactly which segments to redraw)
    p = progress % TRACK_LENGTH
    seg = 0
    while seg < len(_seg_len) and _cum[seg + 1] <= p:
        seg += 1
    if seg >= len(_seg_len):
        seg = len(_seg_len) - 1
    a = WAYPOINTS[seg]
    b = WAYPOINTS[(seg + 1) % len(WAYPOINTS)]
    seg_p = p - _cum[seg]
    seg_d = _seg_len[seg] or 1.0
    t = seg_p / seg_d
    return a, b, t, seg


def track_point(progress, lateral=0.0):
    # progress: arc length along the loop, wraps automatically. Returns
    # (x, y) offset perpendicular to the segment direction by `lateral`.
    a, b, t, _seg = _locate(progress)
    x = a[0] + (b[0] - a[0]) * t
    y = a[1] + (b[1] - a[1]) * t
    dx, dy = b[0] - a[0], b[1] - a[1]
    dlen = (dx * dx + dy * dy) ** 0.5 or 1.0
    nx, ny = -dy / dlen, dx / dlen
    return (x + nx * lateral, y + ny * lateral)


def restore_track_at(fb, progress):
    # real fix, 2026-09-08: repeated attempts to erase a car with a flat-
    # colour dot sized "just right" to avoid the track edge kept breaking
    # again (smoothing changed the geometry enough to make the exact
    # clearance hard to verify precisely each time). This sidesteps the
    # whole class of problem -- instead of guessing a colour and hoping it
    # matches what's underneath, redraw the ACTUAL track (surface + edge)
    # for the segments around this position from the real geometry. Always
    # correct by construction, however wide a car's erase footprint is.
    # Three segments (prev/current/next), not just one, so an erase-dot
    # straddling a segment boundary is still fully covered.
    _a, _b, _t, seg = _locate(progress)
    n = len(WAYPOINTS)
    segs = ((seg - 1) % n, seg, (seg + 1) % n)
    for si in segs:
        a, b = WAYPOINTS[si], WAYPOINTS[(si + 1) % n]
        fb_line(fb, a[0], a[1], b[0], b[1], TRACK_COLOUR, width=TRACK_WIDTH)
    for si in segs:
        a, b = WAYPOINTS[si], WAYPOINTS[(si + 1) % n]
        fb_line(fb, a[0], a[1], b[0], b[1], TRACK_EDGE, width=1)
    # the start/finish line sits at progress 0 specifically and isn't part
    # of the segment loop above -- redrawn unconditionally each call since
    # it's one cheap line and a car crosses it every single lap, the exact
    # repeated-damage pattern that caused this whole class of bug
    x, y = track_point(0.0, -TRACK_WIDTH / 2)
    x2, y2 = track_point(0.0, TRACK_WIDTH / 2)
    fb_line(fb, x, y, x2, y2, INK, width=1)


def track_tangent(progress):
    # unit direction of travel at this arc-length position -- used to
    # orient draw_car() so cars visibly face the way they're moving
    a, b, _t, _seg = _locate(progress)
    dx, dy = b[0] - a[0], b[1] - a[1]
    dlen = (dx * dx + dy * dy) ** 0.5 or 1.0
    return (dx / dlen, dy / dlen)


hdmi.fill(hdmi.fb().colour(PAGE))

g = pcgui.GUI()
g.start()

g.caption(320, 8, "CIRCUIT RACE", fg=INK, bg=PAGE, font=3, just="CT")
# compact command row (2026-09-08 redesign, real ask: "use the top system
# so commands can be hidden and we can expand the base") -- PICK CAR opens
# a small dropdown list instead of 5 always-visible buttons, QUIT stays
# directly reachable, status sits centred between them. Frees the entire
# rest of the screen (CONTENT_TOP downward) for the track.
pick_car_btn = g.button(10, 32, 100, 24, "PICK CAR", fg=INK, bg=BTN, font=1, callback=lambda b: on_pick_car_button(b))
laps_btn = g.button(115, 32, 95, 24, "LAPS: 3", fg=INK, bg=BTN, font=1, callback=lambda b: on_cycle_laps(b))
owners_btn = g.button(215, 32, 80, 24, "OWNERS", fg=INK, bg=BTN, font=1, callback=lambda b: on_owners_button(b))
status_box = g.displaybox(300, 32, 225, 24, "Pick a car to start", fg=INK, bg=PAGE, font=1)
quit_btn = g.button(530, 32, 100, 24, "QUIT", fg=INK, bg=RED, font=1, callback=lambda b: on_quit(b))
# real bug found 2026-09-08: status_box got squeezed to 170px when OWNERS
# was added, too narrow for a real message -- widened using the unused
# strip of screen to the right (buttons only reached x=575 of 640) rather
# than shortening the text into something cryptic

state = {"done": False, "laps_to_win": 3}


def _rand_speed(car_idx):
    # base pace plus a damage penalty -- real ask 2026-09-08: cars that cop
    # more damage should actually run worse, not just cost more to fix.
    # Shared by new_race() (start of a race) and advance() (per-lap
    # re-roll below), so the two can't drift out of sync with each other.
    base = 1.8 + rand_float() * 0.9  # 1.8-2.7 px/tick
    dmg = cars_data[car_idx]["damage"]
    return base * (1.0 - dmg / 100.0 * 0.4)  # up to 40% slower fully damaged


def new_race():
    # cars are no longer pre-populated for all 5 -- real ask 2026-09-08
    # ("lets say 3 players so only 3 cars"): the field is now exactly
    # whoever bought in this race, built once entrants are final (see
    # begin_race()), not a fixed 5-runner spectacle everyone bets on.
    # entrants: list of {"player": index into `players`, "car": car index}
    # -- betting economy, 2026-09-08. Entry fees go into the EVENT pot
    # (see `event` below), not a per-race one -- races only pay out at the
    # end of a 5-race event now. phase: "picking" -> "qualifying" ->
    # "racing" -> over=True (see begin_race()/_advance_qualifying()).
    return {"cars": {}, "finish_order": [], "over": False, "started": False,
            "entrants": [], "phase": "picking"}


def new_event():
    # real ask 2026-09-08: "make an event of 5 races for big prize money".
    # wins tracks race-wins per player index across the event, needed for
    # the handicap cash-up rule at the end (see advance()). start_budget
    # snapshots each entrant's budget the moment they FIRST join this
    # event, so "a bad run" can be judged against where they started it,
    # not against everyone else.
    return {"race_num": 1, "pot": 0.0, "wins": {}, "start_budget": {}}


race = new_race()
event = new_event()
last_pos = {}  # index -> last drawn (x, y) for incremental erase


def draw_track():
    fb = hdmi.fb()
    n = len(WAYPOINTS)
    for p in SAND_TRAPS:
        fill_dot(fb, int(p[0]), int(p[1]), SAND_TRAP_RADIUS, fb.colour(SAND_COLOUR))
    for i in range(n):
        a, b = WAYPOINTS[i], WAYPOINTS[(i + 1) % n]
        fb_line(fb, a[0], a[1], b[0], b[1], TRACK_COLOUR, width=TRACK_WIDTH)
    for i in range(n):
        a, b = WAYPOINTS[i], WAYPOINTS[(i + 1) % n]
        fb_line(fb, a[0], a[1], b[0], b[1], TRACK_EDGE, width=1)
    # start/finish line, perpendicular to the first segment at waypoint 0
    x, y = track_point(0.0, -TRACK_WIDTH / 2)
    x2, y2 = track_point(0.0, TRACK_WIDTH / 2)
    fb_line(fb, x, y, x2, y2, INK, width=1)


def redraw_all(cars=None):
    # cars=None means "whatever's in race['cars'] right now" (the normal
    # case); begin_race() passes cars={} explicitly to draw the track with
    # nobody on it yet -- real bug found 2026-09-08 while adding
    # qualifying: drawing all entrants parked at the start line before
    # qualifying began meant the active qualifier's own restore_track_at
    # (which repaints a whole segment width, not a small dot) could wipe
    # out a parked car sitting in that same stretch of track. Simplest fix
    # is to just not draw anyone until they've actually got a position to
    # be at -- see _start_next_qualifier()/_finish_qualifying().
    fb = hdmi.fb()
    # grass background -- screen-width, from just under the compact
    # command row down to near the bottom of the screen
    fb.fill_rect(0, CONTENT_TOP, 640, CONTENT_BOTTOM - CONTENT_TOP, fb.colour(GRASS_COLOUR))
    draw_track()
    last_pos.clear()
    if cars is None:
        cars = race["cars"]
    for idx, car in cars.items():
        pos = track_point(car["progress"], car["lateral"])
        tan = track_tangent(car["progress"])
        draw_car(fb, pos[0], pos[1], tan[0], tan[1], fb.colour(car["colour"]))
        last_pos[idx] = pos


redraw_all()


def on_quit(b):
    state["done"] = True


def restart_to_pick():
    global race
    race = new_race()
    status_box.value = "Pick a car to start"
    redraw_all()


QUALIFY_GRID_GAP = 6.0  # progress px of head-start per grid position -- real
# ask 2026-09-08: "each owner has to get a lap time before the race can
# start" -- the fastest qualifying lap gets pole position (a small head
# start), not just a formality, same idea as a real motorsport grid


def begin_race():
    # cars now built fresh here, one per entrant only -- real ask
    # 2026-09-08 ("lets say 3 players so only 3 cars"). Positions get
    # finalised once qualifying (below) sets the grid.
    race["cars"] = {}
    for e in race["entrants"]:
        i = e["car"]
        race["cars"][i] = {"progress": 0.0, "lateral": LATERAL_OFFSETS[i % len(LATERAL_OFFSETS)],
                            "speed": _rand_speed(i), "laps": 0, "colour": CAR_COLOURS[i],
                            "finished": False, "place": None}
    race["started"] = True
    race["phase"] = "qualifying"
    race["qualify_order"] = [e["car"] for e in race["entrants"]]
    race["qualify_idx"] = 0
    race["qualify_times"] = {}
    redraw_all(cars={})  # track only -- see redraw_all()'s comment
    _start_next_qualifier()


def _start_next_qualifier():
    car_idx = race["qualify_order"][race["qualify_idx"]]
    car = race["cars"][car_idx]
    car["progress"] = 0.0
    car["lateral"] = 0.0
    car["speed"] = _rand_speed(car_idx)
    race["qualify_start_tick"] = time.ticks_ms()
    status_box.value = "QUALIFYING %d/%d: %s -- clean lap for pole" % (
        race["qualify_idx"] + 1, len(race["qualify_order"]), CAR_NAMES[car_idx])


def _advance_qualifying():
    fb = hdmi.fb()
    car_idx = race["qualify_order"][race["qualify_idx"]]
    car = race["cars"][car_idx]
    prev_progress = car["progress"]
    car["progress"] += car["speed"]
    if car_idx in last_pos:
        restore_track_at(fb, prev_progress)
    pos = track_point(car["progress"], car["lateral"])
    tan = track_tangent(car["progress"])
    draw_car(fb, pos[0], pos[1], tan[0], tan[1], fb.colour(car["colour"]))
    last_pos[car_idx] = pos
    if car["progress"] >= TRACK_LENGTH:
        race["qualify_times"][car_idx] = time.ticks_diff(time.ticks_ms(), race["qualify_start_tick"])
        race["qualify_idx"] += 1
        if race["qualify_idx"] >= len(race["qualify_order"]):
            _finish_qualifying()
        else:
            _start_next_qualifier()


def _finish_qualifying():
    order = sorted(race["qualify_order"], key=lambda i: race["qualify_times"][i])
    n = len(order)
    for rank, car_idx in enumerate(order):  # rank 0 = fastest qualifier
        race["cars"][car_idx]["progress"] = (n - 1 - rank) * QUALIFY_GRID_GAP
        race["cars"][car_idx]["lateral"] = LATERAL_OFFSETS[rank % len(LATERAL_OFFSETS)]
    race["phase"] = "racing"
    redraw_all()
    status_box.value = "Race %d/%d -- %d entrant(s), event pot $%.0f" % (
        event["race_num"], EVENT_RACES, len(race["entrants"]), event["pot"])


# hidden overlay widgets -- created on demand, removed after use (or left
# closed if PICK CAR is pressed mid-race). Sit over the track temporarily;
# redraw_all() after closing one repaints whatever track/car pixels it was
# covering. Only one of these three is ever open at a time.
OVERLAY_X, OVERLAY_Y, OVERLAY_W, OVERLAY_H = 190, 80, 260, 200
_player_list = [None]
_car_list = [None]
_owners_list = [None]
_overlay_header = [None]
_add_player_widgets = [None, None, None]  # textbox, ADD button, CANCEL button
_pending_entrant_player = [None]


def hide_all_overlays():
    if _player_list[0] is not None:
        g.remove(_player_list[0])
        _player_list[0] = None
    if _car_list[0] is not None:
        g.remove(_car_list[0])
        _car_list[0] = None
    if _owners_list[0] is not None:
        g.remove(_owners_list[0])
        _owners_list[0] = None
    if _overlay_header[0] is not None:
        g.remove(_overlay_header[0])
        _overlay_header[0] = None
    for i in range(3):
        if _add_player_widgets[i] is not None:
            g.remove(_add_player_widgets[i])
            _add_player_widgets[i] = None


def show_overlay_header(title):
    # real bug found 2026-09-08: the OWNERS list ("HOLDEN $4000 unowned
    # dmg0% OK") and the buy-a-car list ("HOLDEN $4000 (buy)") look almost
    # identical whenever most cars are still unowned -- reported as
    # "'owners' brings up the car sale page". None of the overlays had any
    # title at all, so there was nothing to tell them apart by. One shared
    # header bar, just above OVERLAY_Y, labelled per dialog.
    _overlay_header[0] = g.displaybox(OVERLAY_X, OVERLAY_Y - 22, OVERLAY_W, 20, title,
                                       fg=INK, bg=BTN, font=1)


def mechanic_word(damage):
    # real ask 2026-09-08: "a new car owners page so the mechanic can
    # relay the damage" -- short tiered word rather than a full sentence,
    # same one-line-budget lesson learned from status_box elsewhere here
    if damage < 20:
        return "OK"
    if damage < 50:
        return "WORN"
    if damage < 80:
        return "BAD"
    return "CRITICAL"


def show_car_owners_page():
    hide_all_overlays()
    show_overlay_header("CAR OWNERS")
    lines = []
    for i, name in enumerate(CAR_NAMES):
        d = cars_data[i]
        owner = d["owner"] or "unowned"
        lines.append("%s $%.0f %s dmg%.0f%% %s" % (name, CAR_VALUES[i], owner, d["damage"], mechanic_word(d["damage"])))
    lines.append("CLOSE")
    _owners_list[0] = g.listbox(OVERLAY_X, OVERLAY_Y, OVERLAY_W, min(OVERLAY_H, 30 * len(lines) + 20),
                                 lines, 0, font=1, callback=lambda c: on_close_owners_page(c))


def on_close_owners_page(c):
    hide_all_overlays()
    redraw_all()


def on_owners_button(b):
    show_car_owners_page()


def show_player_list():
    hide_all_overlays()
    show_overlay_header("PLAYERS")
    items = []
    for p in players:
        items.append("%s  $%.0f" % (p["name"], p["budget"]))
    items.append("+ ADD PLAYER")
    start_race_row = None
    if race["entrants"]:
        start_race_row = len(items)
        items.append(">> QUALIFY + RACE %d/%d (event pot $%.0f)" % (event["race_num"], EVENT_RACES, event["pot"]))
    _player_list[0] = g.listbox(OVERLAY_X, OVERLAY_Y, OVERLAY_W, min(OVERLAY_H, 30 * len(items) + 20),
                                 items, 0, font=1,
                                 callback=lambda c: on_pick_from_player_list(c, len(players), start_race_row))


def on_pick_from_player_list(c, num_players, start_race_row):
    idx = c.value
    if start_race_row is not None and idx == start_race_row:
        hide_all_overlays()
        redraw_all()
        begin_race()
        return
    if idx == num_players:  # "+ ADD PLAYER" always sits right after the last real player
        hide_all_overlays()
        redraw_all()
        show_add_player_dialog()
        return
    if 0 <= idx < num_players:
        if players[idx]["budget"] < ENTRY_FEE:
            # real ask, 2026-09-08: "if the budget is down a full race
            # can't be run" -- enforced here, at the point of entry
            status_box.value = "%s: below $%.0f entry, can't race" % (players[idx]["name"], ENTRY_FEE)
            return
        _pending_entrant_player[0] = idx
        hide_all_overlays()
        redraw_all()
        show_car_list_for_entrant()


def show_add_player_dialog():
    hide_all_overlays()
    show_overlay_header("ADD PLAYER")
    # real bug, 2026-09-08: got stuck in this dialog with no way out --
    # the ADD/CANCEL buttons weren't reliably reachable. Two fixes: the
    # textbox itself now has a callback (same proven pattern as
    # club.py's EmailMemberPage.search box), so pressing Enter on the
    # on-screen keyboard submits directly -- doesn't depend on a
    # separately-tapped button at all. CANCEL also moved up right next to
    # the textbox instead of below it, so it's not competing with
    # wherever the on-screen keyboard itself renders.
    _add_player_widgets[0] = g.textbox(OVERLAY_X + 10, OVERLAY_Y + 10, OVERLAY_W - 130, 26, "", font=1,
                                        callback=lambda c: on_confirm_add_player(None))
    _add_player_widgets[1] = g.button(OVERLAY_X + OVERLAY_W - 110, OVERLAY_Y + 10, 100, 26, "CANCEL",
                                       fg=INK, bg=RED, font=1, callback=lambda b: on_cancel_add_player(b))
    _add_player_widgets[2] = g.button(OVERLAY_X + 10, OVERLAY_Y + 46, 200, 32, "ADD PLAYER", fg=INK, bg=BTN,
                                       font=1, callback=lambda b: on_confirm_add_player(None))


def on_confirm_add_player(b):
    name = (_add_player_widgets[0].value or "").strip()
    if not name:
        return  # leave the dialog open -- nothing typed yet
    players.append({"name": name[:20], "budget": STARTING_BUDGET})
    save_players()
    hide_all_overlays()
    redraw_all()
    show_player_list()


def on_cancel_add_player(b):
    hide_all_overlays()
    redraw_all()
    show_player_list()


def show_car_list_for_entrant():
    hide_all_overlays()
    show_overlay_header("BUY / PICK CAR")
    items = []
    for i, name in enumerate(CAR_NAMES):
        owner = cars_data[i]["owner"]
        if owner is None:
            items.append("%s  $%.0f (buy)" % (name, CAR_VALUES[i]))
        else:
            items.append("%s  owned: %s" % (name, owner))
    _car_list[0] = g.listbox(OVERLAY_X, OVERLAY_Y, OVERLAY_W, 5 * 26 + 30,
                              items, 0, font=2, callback=lambda c: on_pick_car_for_entrant(c))


def on_pick_car_for_entrant(c):
    car_idx = c.value
    player_idx = _pending_entrant_player[0]
    hide_all_overlays()
    redraw_all()
    if player_idx is None or not (0 <= car_idx < len(CAR_NAMES)):
        show_player_list()
        return
    player = players[player_idx]
    if player_idx not in event["start_budget"]:
        # snapshot BEFORE any spend this race -- used at event end to judge
        # whether this player had "a bad run" (real ask 2026-09-08)
        event["start_budget"][player_idx] = player["budget"]
    owner = cars_data[car_idx]["owner"]
    if owner is not None and owner != player["name"]:
        status_box.value = "%s owned by %s -- pick another" % (CAR_NAMES[car_idx], owner)
        show_player_list()
        return
    if owner is None:
        cost = CAR_VALUES[car_idx]
        if player["budget"] < cost + ENTRY_FEE:
            status_box.value = "Can't afford %s ($%.0f + entry)" % (CAR_NAMES[car_idx], cost)
            show_player_list()
            return
        player["budget"] -= cost
        cars_data[car_idx]["owner"] = player["name"]
        save_cars_data()
    player["budget"] -= ENTRY_FEE
    event["pot"] += ENTRY_FEE
    race["entrants"].append({"player": player_idx, "car": car_idx})
    save_players()
    show_player_list()  # loop back -- another player can enter, or START RACE


def on_pick_car_button(b):
    if race["started"] and not race["over"]:
        return  # mid-race -- no entering until it finishes
    if race["over"]:
        restart_to_pick()
    # always through the player list, even with zero players -- real bug,
    # 2026-09-08: the old "if not players: go straight to the add-player
    # dialog" shortcut was a second, less-tested entry path into that
    # dialog, and reports of getting stuck there (and separately, of
    # somehow reaching car-picking before a player existed) both trace
    # back to this special case. One single path now, always via the list
    # (which already includes "+ ADD PLAYER" even when it's otherwise
    # empty), so there's only one way in and one way this can go wrong,
    # not two.
    show_player_list()


def on_cycle_laps(b):
    global laps_btn
    if race["started"] and not race["over"]:
        return  # mid-race -- lap count is locked in once a race is running
    i = LAPS_OPTIONS.index(state["laps_to_win"])
    state["laps_to_win"] = LAPS_OPTIONS[(i + 1) % len(LAPS_OPTIONS)]
    # same recreate-to-relabel pattern club.py's own SIZE-cycle buttons use
    # (EmailMemberPage.on_cycle_size) -- no g.button() API for changing an
    # existing button's text in place
    g.remove(laps_btn)
    laps_btn = g.button(115, 32, 95, 24, "LAPS: %d" % state["laps_to_win"], fg=INK, bg=BTN, font=1,
                         callback=lambda b: on_cycle_laps(b))


def advance():
    global event
    if race["phase"] == "qualifying":
        _advance_qualifying()
        return
    if not race["started"] or race["over"]:
        return
    fb = hdmi.fb()
    # two passes, not interleaved per car (2026-09-08) -- restoring car A's
    # old track segments could redraw right over car B's already-freshly-
    # drawn body if they're close together (more likely now than with the
    # old flat-dot erase, since restore_track_at repaints a whole segment
    # width, not just a small dot). All restores happen first, then all
    # cars get (re)drawn at their new positions, so a later restore can
    # never erase an earlier car's fresh draw.
    updates = []  # (idx, prev_progress) for cars that moved this tick
    for idx, car in race["cars"].items():
        if car["finished"]:
            continue
        prev_progress = car["progress"]
        car["progress"] += car["speed"]
        car["lateral"] += (rand_float() - 0.5) * LATERAL_DRIFT_STEP * 2
        car["lateral"] = max(-LATERAL_LIMIT, min(LATERAL_LIMIT, car["lateral"]))
        if int(car["progress"] // TRACK_LENGTH) > int(prev_progress // TRACK_LENGTH):
            car["laps"] += 1
            # real ask 2026-09-08: "players can do lap times to gain
            # places again all random" -- pace re-rolled each lap instead
            # of held fixed for the whole race, so a mid-pack car can post
            # a fast lap and move up, and a leader can have a bad one
            car["speed"] = _rand_speed(idx)
            if car["laps"] >= state["laps_to_win"] and not car["finished"]:
                car["finished"] = True
                car["place"] = len(race["finish_order"]) + 1
                race["finish_order"].append(idx)
        updates.append((idx, prev_progress))

    # push apart any two cars that ended up close in BOTH progress and
    # lateral offset this tick -- see MIN_CAR_PROGRESS_GAP/MIN_CAR_LATERAL_GAP
    # above. Runs after the drift loop (so it sees this tick's positions)
    # and before restore/draw (so restore_track_at and draw_car both use
    # the corrected lateral, not the pre-separation one).
    ids = list(race["cars"].keys())
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            ca, cb = race["cars"][ids[a]], race["cars"][ids[b]]
            if ca["finished"] or cb["finished"]:
                continue
            dp = abs(ca["progress"] - cb["progress"]) % TRACK_LENGTH
            dp = min(dp, TRACK_LENGTH - dp)
            if dp > MIN_CAR_PROGRESS_GAP:
                continue
            dl = ca["lateral"] - cb["lateral"]
            if abs(dl) >= MIN_CAR_LATERAL_GAP:
                continue
            push = (MIN_CAR_LATERAL_GAP - abs(dl)) / 2.0
            direction = 1.0 if dl >= 0 else -1.0
            ca["lateral"] = max(-LATERAL_LIMIT, min(LATERAL_LIMIT, ca["lateral"] + push * direction))
            cb["lateral"] = max(-LATERAL_LIMIT, min(LATERAL_LIMIT, cb["lateral"] - push * direction))

    for idx, prev_progress in updates:
        if idx in last_pos:
            restore_track_at(fb, prev_progress)

    for idx, prev_progress in updates:
        car = race["cars"][idx]
        pos = track_point(car["progress"], car["lateral"])
        tan = track_tangent(car["progress"])
        draw_car(fb, pos[0], pos[1], tan[0], tan[1], fb.colour(car["colour"]))
        last_pos[idx] = pos

    if len(race["finish_order"]) >= len(race["cars"]) and not race["over"]:
        race["over"] = True
        winner = race["finish_order"][0]
        winners = [e for e in race["entrants"] if e["car"] == winner]
        for e in winners:
            event["wins"][e["player"]] = event["wins"].get(e["player"], 0) + 1

        # random damage event per entrant, independent of who won -- cost
        # now scales off the CAR's own value (real ask 2026-09-08: pricier
        # cars cop more damage) and persists on the car itself, not just a
        # one-off deduction -- see cars_data / show_car_owners_page
        dmg_count = 0
        for e in race["entrants"]:
            car_idx = e["car"]
            frac, desc = roll_random_event()
            if desc:
                players[e["player"]]["budget"] -= CAR_VALUES[car_idx] * frac
                cars_data[car_idx]["damage"] = min(100.0, cars_data[car_idx]["damage"] + frac * 60.0)
                dmg_count += 1
        save_cars_data()

        if event["race_num"] < EVENT_RACES:
            event["race_num"] += 1
            # real ask 2026-09-08: after a real race, "no prize money or
            # damage was shown" -- correct (payout only happens at the end
            # of the 5-race event), but the old message didn't say so and
            # silently omitted damage when none rolled, reading as broken
            # rather than as "nothing happened this time". Now explicit
            # both ways.
            msg = "%s wins race %d/%d -- pot banked to event: $%.0f" % (
                CAR_NAMES[winner], event["race_num"] - 1, EVENT_RACES, event["pot"])
            save_players()
        else:
            # final race of the event -- cash up time. Real ask
            # 2026-09-08: "if a bad run has been done more lap wins are
            # needed to cash up" -- anyone whose budget is now BELOW where
            # they stood at the start of this event had a bad run, and
            # needs 2 race-wins across the event (not just 1) to qualify
            # for a cut of the pot -- a harsher bar for whoever's already
            # behind, not a softer one.
            qualifiers = []
            for idx in event["wins"]:
                need = 1
                start = event["start_budget"].get(idx, players[idx]["budget"])
                if players[idx]["budget"] < start:
                    need = 2
                if event["wins"][idx] >= need:
                    qualifiers.append(idx)
            if qualifiers and event["pot"] > 0:
                share = event["pot"] / len(qualifiers)
                for idx in qualifiers:
                    players[idx]["budget"] += share
                msg = "EVENT OVER! %s wins final race. $%.0f split %d way(s)" % (
                    CAR_NAMES[winner], event["pot"], len(qualifiers))
            else:
                msg = "EVENT OVER! %s wins final race. Nobody cashed up" % CAR_NAMES[winner]
            save_players()
            event = new_event()

        msg += " | %d dmg event(s)" % dmg_count if dmg_count else " | no damage this race"
        status_box.value = msg


last_move = time.ticks_ms()
while not state["done"]:
    g.poll()
    now = time.ticks_ms()
    if time.ticks_diff(now, last_move) >= 60:
        last_move = now
        advance()
    time.sleep_ms(10)

try:
    g.stop()
except Exception:
    pass
