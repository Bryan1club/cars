# gen_game_icons.py -- placeholder icon bmps for GamesPage's icon grid
# (games_page.py: "make bmp's for each game that can be used"). One
# 96x96 bmp per game in assets/games/, named to match
# (snake.py -> snake.bmp), simple/recognisable rather than real art --
# swap these out for real box art later without touching any code, the
# page just draws whatever bmp is there. Run with: python gen_game_icons.py
# (needs Pillow). Not deployed to the board itself -- only the bmp output
# is (wifi-upload it, same *_bg.bmp-style auto-routing as everything
# else -- see club.py's handle_upload_connection/_is_game_icon).

import os

from PIL import Image, ImageDraw

W, H = 96, 96
OUT_DIR = os.path.join(os.path.dirname(__file__), "games")


def base(bg):
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W - 1, H - 1), outline=(200, 200, 200))
    return img, d


def gen_snake():
    img, d = base((18, 40, 20))
    body = (60, 200, 90)
    cell = 10
    segs = [(3, 5), (4, 5), (5, 5), (5, 4), (5, 3), (6, 3)]
    for cx, cy in segs:
        x, y = 8 + cx * cell, 8 + cy * cell
        d.rectangle((x, y, x + cell - 2, y + cell - 2), fill=body)
    fx, fy = 8 + 8 * cell, 8 + 3 * cell
    d.ellipse((fx, fy, fx + cell - 2, fy + cell - 2), fill=(220, 60, 60))
    img.save(os.path.join(OUT_DIR, "snake.bmp"), "BMP")


def gen_racing():
    img, d = base((30, 30, 34))
    # checkered strip along the top
    sq = 8
    for i in range(W // sq):
        c = (230, 230, 230) if i % 2 == 0 else (20, 20, 20)
        d.rectangle((i * sq, 4, i * sq + sq - 1, 4 + sq - 1), fill=c)
    # simple car silhouette
    body = (210, 60, 40)
    d.rounded_rectangle((18, 46, 78, 68), radius=6, fill=body)
    d.rectangle((30, 36, 66, 50), fill=body)
    d.ellipse((24, 62, 40, 78), fill=(15, 15, 15))
    d.ellipse((56, 62, 72, 78), fill=(15, 15, 15))
    img.save(os.path.join(OUT_DIR, "racing.bmp"), "BMP")


def gen_clicker():
    img, d = base((25, 25, 40))
    d.ellipse((18, 18, 78, 78), fill=(70, 110, 220), outline=(220, 220, 240), width=3)
    d.ellipse((34, 34, 62, 62), fill=(230, 230, 240))
    # cursor arrow
    d.polygon([(58, 58), (58, 84), (65, 77), (70, 86), (75, 83), (70, 74), (79, 74)],
              fill=(255, 255, 255), outline=(0, 0, 0))
    img.save(os.path.join(OUT_DIR, "clicker.bmp"), "BMP")


gen_snake()
gen_racing()
gen_clicker()
print("wrote snake.bmp, racing.bmp, clicker.bmp to", OUT_DIR)
