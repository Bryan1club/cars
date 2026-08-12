# snake.py -- a real game for the GAMES launcher in club.py
# Drop this into /sd/Games.
#
# Movement is driven by four D-pad buttons (LEFT/UP/DOWN/RIGHT), not
# a mouse drag -- this app's on_move (continuous mouse-move) hook is
# confirmed not to work on this hardware, so anything needing smooth
# real-time input has to be built out of discrete button clicks
# instead. The snake still advances on its own on a timer regardless
# of whether a button was pressed; only the NEXT direction changes.
#
# Drawing is incremental (erase the vacated tail cell, draw the new
# head cell) rather than clearing and redrawing the whole board every
# tick -- a full-board clear at CELL-height resolution is hundreds of
# line draws, and doing that every 220ms is exactly the kind of dense,
# repeated pixel-pushing that caused a real hang/reset elsewhere in
# this project (a 1mm GRID spacing -- see club.py's GRID_MAX_DOTS
# comment). Incremental redraw keeps the per-tick cost to a handful of
# small fills regardless of how long the snake gets.
#
# Standalone: only uses hdmi/pcgui/time, the same set already proven
# throughout club.py -- no imports from club.py itself, since the
# GAMES launcher exec()'s this in a fresh namespace. `random` is used
# if available but not required -- see rand_below() below.

import hdmi
import pcgui
import time

PAGE = 0x102010
INK = 0xFFFFFF
BTN = 0x2E7D32
RED = 0xCC3333
SNAKE_COLOUR = 0x33CC33
FOOD_COLOUR = 0xCC3333

CELL = 20
COLS = 30
ROWS = 18
PLAY_X0 = 20
PLAY_Y0 = 50
PLAY_X1 = PLAY_X0 + COLS * CELL   # 620
PLAY_Y1 = PLAY_Y0 + ROWS * CELL   # 410

MOVE_INTERVAL_MS = 220

try:
    import random
    def rand_below(n):
        return random.randint(0, n - 1)
except ImportError:
    # fallback PRNG (xorshift) -- random.randint() isn't used anywhere
    # else in this project, so its availability on this board's
    # MicroPython build is unverified; this removes the hard dependency
    _seed = [(time.ticks_us() & 0xFFFF) or 1]
    def rand_below(n):
        x = _seed[0]
        x ^= (x << 7) & 0xFFFF
        x ^= (x >> 9)
        x ^= (x << 8) & 0xFFFF
        _seed[0] = x & 0xFFFF
        return x % n


def fb_line(fb, x0, y0, x1, y1, colour):
    try:
        fb.line(int(x0), int(y0), int(x1), int(y1), colour)
    except Exception:
        pass


def fill_cell(fb, col, row, colour):
    x = PLAY_X0 + col * CELL
    y = PLAY_Y0 + row * CELL
    for dy in range(CELL - 1):
        fb_line(fb, x, y + dy, x + CELL - 2, y + dy, colour)


def clear_rect(fb, x0, y0, x1, y1, colour):
    for y in range(y0, y1):
        fb_line(fb, x0, y, x1 - 1, y, colour)


hdmi.fill(hdmi.fb().colour(PAGE))
BG = hdmi.fb().colour(PAGE)

g = pcgui.GUI()
g.start()

g.caption(320, 8, "SNAKE", fg=INK, bg=PAGE, font=3, just="CT")
score_box = g.displaybox(460, 8, 160, 24, "Score: 0", fg=INK, bg=PAGE, font=2)
g.frame(PLAY_X0 - 2, PLAY_Y0 - 2, COLS * CELL + 4, ROWS * CELL + 4, "", fg=INK, font=1)

state = {"done": False}


def new_game():
    mid_c, mid_r = COLS // 2, ROWS // 2
    return {
        "body": [(mid_c, mid_r), (mid_c - 1, mid_r), (mid_c - 2, mid_r)],
        "dir": (1, 0),
        "next_dir": (1, 0),
        "food": None,
        "score": 0,
        "over": False,
    }


game = new_game()


def place_food():
    while True:
        p = (rand_below(COLS), rand_below(ROWS))
        if p not in game["body"]:
            game["food"] = p
            fill_cell(hdmi.fb(), p[0], p[1], FOOD_COLOUR)
            return


def draw_full():
    fb = hdmi.fb()
    clear_rect(fb, PLAY_X0, PLAY_Y0, PLAY_X1, PLAY_Y1, BG)
    for c, r in game["body"]:
        fill_cell(fb, c, r, SNAKE_COLOUR)
    if game["food"]:
        fill_cell(fb, game["food"][0], game["food"][1], FOOD_COLOUR)


place_food()
draw_full()


def set_dir(dx, dy):
    # can't reverse straight into your own neck
    cdx, cdy = game["dir"]
    if (dx, dy) == (-cdx, -cdy):
        return
    game["next_dir"] = (dx, dy)


def restart():
    global game
    game = new_game()
    score_box.value = "Score: 0"
    place_food()
    draw_full()


def on_left(b):
    restart() if game["over"] else set_dir(-1, 0)


def on_right(b):
    restart() if game["over"] else set_dir(1, 0)


def on_up(b):
    restart() if game["over"] else set_dir(0, -1)


def on_down(b):
    restart() if game["over"] else set_dir(0, 1)


def on_quit(b):
    state["done"] = True


BTN_Y = PLAY_Y1 + 12
g.button(20, BTN_Y, 110, 40, "LEFT", fg=INK, bg=BTN, font=2, callback=on_left)
g.button(140, BTN_Y, 110, 40, "UP", fg=INK, bg=BTN, font=2, callback=on_up)
g.button(260, BTN_Y, 110, 40, "DOWN", fg=INK, bg=BTN, font=2, callback=on_down)
g.button(380, BTN_Y, 110, 40, "RIGHT", fg=INK, bg=BTN, font=2, callback=on_right)
g.button(500, BTN_Y, 120, 40, "QUIT", fg=INK, bg=RED, font=2, callback=on_quit)


def advance():
    if game["over"]:
        return
    game["dir"] = game["next_dir"]
    dx, dy = game["dir"]
    hx, hy = game["body"][0]
    nx, ny = hx + dx, hy + dy

    # moving into the current tail cell is legal (the tail vacates it
    # this same step) UNLESS food is eaten this move, in which case
    # the tail doesn't move and the cell really is still occupied
    would_eat = (nx, ny) == game["food"]
    blocking_body = game["body"] if would_eat else game["body"][:-1]

    if nx < 0 or nx >= COLS or ny < 0 or ny >= ROWS or (nx, ny) in blocking_body:
        game["over"] = True
        score_box.value = "GAME OVER: %d (press a direction to retry)" % game["score"]
        return

    game["body"].insert(0, (nx, ny))
    fill_cell(hdmi.fb(), nx, ny, SNAKE_COLOUR)

    if (nx, ny) == game["food"]:
        game["score"] += 1
        score_box.value = "Score: %d" % game["score"]
        place_food()
    else:
        tail = game["body"].pop()
        fill_cell(hdmi.fb(), tail[0], tail[1], BG)


last_move = time.ticks_ms()
while not state["done"]:
    g.poll()
    now = time.ticks_ms()
    if time.ticks_diff(now, last_move) >= MOVE_INTERVAL_MS:
        last_move = now
        advance()
    time.sleep_ms(10)

try:
    g.stop()
except Exception:
    pass
