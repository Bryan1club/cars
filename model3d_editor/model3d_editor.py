# model3d_editor.py -- standalone 3D Model Editor for the Pico Computer 3
#
# Extracted from a larger car-club management program (club.py) so it
# can run and be shared on its own. This file only pulls in what
# Model3DPage actually depends on: the Page base class, colour
# constants, a couple of raw-framebuffer drawing helpers, the model
# save/load file format, and a minimal help screen -- none of the
# original program's membership/events/wifi/calculator/games code.
#
# Requirements: a Pico Computer 3 board (or compatible) with the
# hdmi/pcgui/pcgfx/pcconfig/pcconsole/pcimage MicroPython modules
# available, and an SD card mounted at /sd.
#
# Draws boxes, lines, circles, and arcs; lets you SELECT and undo/redo;
# supports named layers with show/hide; saves/loads named models to
# /sd/models; and shows a live rotatable wireframe view with zoom, pan,
# grid snapping, and a WIRE toggle to hide/show the modelled geometry.
# LINE has both a typed-numbers entry and a click-on-the-grid entry
# mode. Icons for the command buttons are
# expected at /sd/icons/<name>.bmp (26x26, see this project's
# assets/icons/*.svg for the sources) -- if they're missing, the
# buttons still work, they just won't have an icon drawn on them.
#
# Run this directly (e.g. from the REPL: exec(open('model3d_editor.py').read())
# or import it as a module and call main()) rather than launching it
# from inside club.py's own GAMES page, since main() below manages the
# HDMI screen mode and serial console itself.

import gc
import os
import math
import struct
import time
import hdmi
import pcgui
import pcimage
from pcgfx import WHITE, RED
from pcconfig import screen
from pcconsole import console

MODELS_DIR = "/sd/models"     # saved 3D models
ICONS_DIR = "/sd/icons"       # command button icons (26x26 .bmp)
UPLOAD_LOG = "/sd/model3d_editor_log.txt"  # separate from club.py's own log
UPLOAD_LOG_MAX_BYTES = 100000  # truncated (not deleted) once exceeded, so a chatty
                                # diagnostic caller can't quietly fill the SD card

PAGE = 0x66B2FF
INK = 0x103018
BTN = 0x2E7D32


def ulog(text):
    try:
        try:
            if os.stat(UPLOAD_LOG)[6] > UPLOAD_LOG_MAX_BYTES:
                # truncate rather than remove -- keeps the path present
                # so anything else opening it for read doesn't hit a
                # missing-file error, just starts it fresh instead of
                # ever growing past the cap
                f = open(UPLOAD_LOG, "w")
                f.write("--- log truncated: exceeded %d bytes ---\n" % UPLOAD_LOG_MAX_BYTES)
                f.close()
        except OSError:
            pass  # file doesn't exist yet -- nothing to truncate
        f = open(UPLOAD_LOG, "a")
        t = time.localtime()
        s = "%04d-%02d-%02d %02d:%02d:%02d  " % (t[0], t[1], t[2], t[3], t[4], t[5])
        f.write(s + text + "\n")
        f.close()
    except Exception:
        pass


def _fb_pixel(fb, x, y, color):
    try:
        fb.pixel(int(x), int(y), color)
    except Exception:
        pass


def _fb_line(fb, x0, y0, x1, y1, color):
    try:
        fb.line(int(x0), int(y0), int(x1), int(y1), color)
        return
    except Exception:
        pass
    # Bresenham fallback, pixel by pixel
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        _fb_pixel(fb, x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


# --- 3D model file format: a plain text file under MODELS_DIR, one
# line per element:
#   BOX x0 y0 z0 x1 y1 z1 layer        -- opposite corners
#   LINE x0 y0 z0 x1 y1 z1 layer       -- endpoints
#   CIRCLE cx cy cz radius plane layer -- plane is XY/XZ/YZ
#   ARC cx cy cz radius plane start end layer  -- start/end in degrees
#   POLY plane height n x0 y0 z0 x1 y1 z1 ... layer  -- MULTI LINE's
#     closed n-point outline (last point implicitly connects back to
#     the first); height is 0 until EXTRUDE gives it one, at which
#     point it exports as a solid prism rather than just an outline
#     (see _poly_solid_triangles)
#   GRID plane spacing extent_i extent_j [position]  -- at most one per
#     file, no layer; extent_i/extent_j are along the plane's two axes
#     in AXIS_NAMES order (e.g. X then Y for an XY grid), independent
#     so a grid can exactly cover a non-square face; position is where
#     the grid sits along its plane's normal axis (Z for XY, Y for XZ,
#     X for YZ) -- omitted/missing means 0, for files saved before that
#     field existed. Files saved before extent_i/extent_j existed have
#     just one extent value, applied to both axes (a square grid).
#   LAYER name visible           -- visible is 1 or 0, one per layer
def serialize_model(boxes, lines, circles, arcs, polys, grid, layers, layer_visible):
    out = []
    for (c0, c1, layer) in boxes:
        out.append("BOX %g %g %g %g %g %g %s" % (c0[0], c0[1], c0[2], c1[0], c1[1], c1[2], layer))
    for (p0, p1, layer) in lines:
        out.append("LINE %g %g %g %g %g %g %s" % (p0[0], p0[1], p0[2], p1[0], p1[1], p1[2], layer))
    for (c, r, plane, layer) in circles:
        out.append("CIRCLE %g %g %g %g %s %s" % (c[0], c[1], c[2], r, plane, layer))
    for (c, r, plane, a0, a1, layer) in arcs:
        out.append("ARC %g %g %g %g %s %g %g %s" % (c[0], c[1], c[2], r, plane, a0, a1, layer))
    for (points, plane, height, layer) in polys:
        coords = " ".join("%g %g %g" % (p[0], p[1], p[2]) for p in points)
        out.append("POLY %s %g %d %s %s" % (plane, height, len(points), coords, layer))
    if grid:
        plane, spacing, extent_i, extent_j, position = grid
        out.append("GRID %s %g %g %g %g" % (plane, spacing, extent_i, extent_j, position))
    for name in layers:
        out.append("LAYER %s %d" % (name, 1 if layer_visible.get(name, True) else 0))
    return "\n".join(out) + "\n"


def parse_model(text):
    boxes, lines, circles, arcs, polys = [], [], [], [], []
    grid = None
    layers = []
    layer_visible = {}
    for line in text.split("\n"):
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "BOX" and len(parts) >= 8:
            boxes.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                          (float(parts[4]), float(parts[5]), float(parts[6])), parts[7]))
        elif parts[0] == "BOX" and len(parts) >= 7:
            boxes.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                          (float(parts[4]), float(parts[5]), float(parts[6])), "Layer1"))
        elif parts[0] == "BOX" and len(parts) >= 4:
            boxes.append(((0.0, 0.0, 0.0), (float(parts[1]), float(parts[2]), float(parts[3])), "Layer1"))
        elif parts[0] == "LINE" and len(parts) >= 8:
            lines.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                          (float(parts[4]), float(parts[5]), float(parts[6])), parts[7]))
        elif parts[0] == "LINE" and len(parts) >= 7:
            lines.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                          (float(parts[4]), float(parts[5]), float(parts[6])), "Layer1"))
        elif parts[0] == "CIRCLE" and len(parts) >= 7:
            circles.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                            float(parts[4]), parts[5], parts[6]))
        elif parts[0] == "CIRCLE" and len(parts) >= 6:
            circles.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                            float(parts[4]), parts[5], "Layer1"))
        elif parts[0] == "ARC" and len(parts) >= 9:
            arcs.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                         float(parts[4]), parts[5], float(parts[6]), float(parts[7]), parts[8]))
        elif parts[0] == "ARC" and len(parts) >= 8:
            arcs.append(((float(parts[1]), float(parts[2]), float(parts[3])),
                         float(parts[4]), parts[5], float(parts[6]), float(parts[7]), "Layer1"))
        elif parts[0] == "POLY" and len(parts) >= 4:
            plane = parts[1]
            height = float(parts[2])
            n = int(parts[3])
            need = 4 + n * 3
            if n >= 3 and len(parts) >= need + 1:
                pts = [(float(parts[4 + k * 3]), float(parts[5 + k * 3]), float(parts[6 + k * 3]))
                       for k in range(n)]
                polys.append((pts, plane, height, parts[need]))
        elif parts[0] == "GRID" and len(parts) >= 6:
            grid = (parts[1], float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5]))
        elif parts[0] == "GRID" and len(parts) >= 5:
            # pre-independent-extents save: one extent, applied to both axes
            grid = (parts[1], float(parts[2]), float(parts[3]), float(parts[3]), float(parts[4]))
        elif parts[0] == "GRID" and len(parts) >= 4:
            grid = (parts[1], float(parts[2]), float(parts[3]), float(parts[3]), 0.0)
        elif parts[0] == "LAYER" and len(parts) >= 3:
            layers.append(parts[1])
            layer_visible[parts[1]] = parts[2] != "0"
    if not layers:
        layers = ["Layer1"]
        layer_visible = {"Layer1": True}
    return boxes, lines, circles, arcs, polys, grid, layers, layer_visible


def save_model_file(name, boxes, lines, circles, arcs, polys, grid, layers, layer_visible):
    try:
        os.mkdir(MODELS_DIR)
    except OSError:
        pass  # already exists
    path = MODELS_DIR + "/" + name + ".model"
    f = open(path, "w")
    try:
        f.write(serialize_model(boxes, lines, circles, arcs, polys, grid, layers, layer_visible))
    finally:
        f.close()
    return path


def load_model_file(name):
    path = MODELS_DIR + "/" + name + ".model"
    f = open(path)
    try:
        text = f.read()
    finally:
        f.close()
    return parse_model(text)


def list_saved_models():
    try:
        names = [f[:-6] for f in os.listdir(MODELS_DIR) if f.endswith(".model")]
        names.sort()
        return names
    except OSError:
        return []


def delete_model_file(name):
    try:
        os.remove(MODELS_DIR + "/" + name + ".model")
        return True
    except OSError:
        return False


# --- template wireframes: a reference cube (dots on its XY/XZ/YZ faces
# through the origin, plus optional centre lines) that's independent of
# whatever model is currently open -- unaffected by NEW FILE/OPEN, not
# saved into any .model file. Named and saved like models are, so you
# can build up a small library (e.g. a big reference cube and a small
# one for detail work) and pick up to two of them -- MAIN and LOCAL --
# to show at once. Each saved as one line:
#   size spacing scale centerlines show_xy show_xz show_yz
# size/spacing are the base values; scale multiplies both together, so
# the same saved template can be reused at any real-world size.
WIREFRAMES_DIR = "/sd/wireframes"
TEMPLATE_ACTIVE_FILE = "/sd/template_active.txt"


def serialize_wireframe(cfg):
    size, spacing, scale, centerlines, show_xy, show_xz, show_yz = cfg
    return "%g %g %g %d %d %d %d\n" % (
        size, spacing, scale, 1 if centerlines else 0,
        1 if show_xy else 0, 1 if show_xz else 0, 1 if show_yz else 0)


def parse_wireframe(text):
    parts = text.split()
    if len(parts) < 7:
        return None
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]), parts[3] != "0",
                parts[4] != "0", parts[5] != "0", parts[6] != "0")
    except ValueError:
        return None


def save_wireframe_file(name, cfg):
    try:
        os.mkdir(WIREFRAMES_DIR)
    except OSError:
        pass  # already exists
    path = WIREFRAMES_DIR + "/" + name + ".wf"
    f = open(path, "w")
    try:
        f.write(serialize_wireframe(cfg))
    finally:
        f.close()
    return path


def load_wireframe_file(name):
    path = WIREFRAMES_DIR + "/" + name + ".wf"
    f = open(path)
    try:
        text = f.read()
    finally:
        f.close()
    return parse_wireframe(text)


def list_saved_wireframes():
    try:
        names = [f[:-3] for f in os.listdir(WIREFRAMES_DIR) if f.endswith(".wf")]
        names.sort()
        return names
    except OSError:
        return []


def delete_wireframe_file(name):
    try:
        os.remove(WIREFRAMES_DIR + "/" + name + ".wf")
        return True
    except OSError:
        return False


def load_template_active():
    # returns (main_name, local_name), either/both None if unset
    try:
        f = open(TEMPLATE_ACTIVE_FILE)
        try:
            text = f.read()
        finally:
            f.close()
    except OSError:
        return None, None
    main_name = None
    local_name = None
    for line in text.split("\n"):
        parts = line.split(None, 1)
        if len(parts) == 2:
            if parts[0] == "MAIN":
                main_name = parts[1]
            elif parts[0] == "LOCAL":
                local_name = parts[1]
    return main_name, local_name


def save_template_active(main_name, local_name):
    lines = []
    if main_name:
        lines.append("MAIN " + main_name)
    if local_name:
        lines.append("LOCAL " + local_name)
    try:
        f = open(TEMPLATE_ACTIVE_FILE, "w")
        try:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        finally:
            f.close()
    except OSError as e:
        ulog("save_template_active failed: " + str(e))


# --- STL export: the model is a wireframe (edges only), but STL needs
# a solid triangle mesh -- BOX converts directly (it's already a solid
# box), LINE/CIRCLE/ARC don't have any volume of their own, so each
# gets "solidified" into a thin rectangular strut/tube of a chosen
# thickness (a circle/arc becomes a ring of straight struts, reusing
# the same chord approximation _draw_arc already uses on screen, so
# what you see is what gets printed). Adjacent struts around a circle/
# arc don't perfectly weld at their shared joints (each is its own
# independent oblique box) -- fine for FDM printing, where slicers
# routinely repair much worse, but worth knowing if a strict mesh
# checker complains. Written as binary STL (compact, simple format).
def _v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _v_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _v_scale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _v_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _v_length(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _v_normalize(a):
    length = _v_length(a)
    if length < 1e-9:
        return (0.0, 0.0, 1.0)
    return (a[0] / length, a[1] / length, a[2] / length)


def _perp_basis(d):
    # d must already be a unit vector -- returns (u, v) such that
    # u, v, d form a right-handed orthonormal basis (cross(u, v) == d),
    # the same convention as cross(X_AXIS, Y_AXIS) == Z_AXIS
    ref = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 1.0, 0.0)
    u = _v_normalize(_v_cross(ref, d))
    v = _v_cross(d, u)
    return u, v


def _box_corner_triangles(b0, b1, b2, b3, t0, t1, t2, t3):
    # 12 triangles (2 per face) for a box given its 4 bottom corners
    # (in order, forming a right-handed ring when viewed from "outside
    # the top") and the matching 4 top corners directly above them.
    # Winding is chosen so every face's normal points outward.
    tris = []

    def quad(p0, p1, p2, p3):
        tris.append((p0, p1, p2))
        tris.append((p0, p2, p3))
    quad(b3, b2, b1, b0)
    quad(t0, t1, t2, t3)
    quad(b0, b1, t1, t0)
    quad(b1, b2, t2, t1)
    quad(b2, b3, t3, t2)
    quad(b3, b0, t0, t3)
    return tris


def _box_triangles(c0, c1):
    x0, y0, z0 = c0
    x1, y1, z1 = c1
    b0, b1, b2, b3 = (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)
    t0, t1, t2, t3 = (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)
    return _box_corner_triangles(b0, b1, b2, b3, t0, t1, t2, t3)


def _strut_triangles(p0, p1, half_width):
    # a thin rectangular beam (square cross-section) running from p0
    # to p1 -- how LINE/CIRCLE/ARC edges get turned into something
    # with actual volume for printing (see the module comment above)
    d = _v_sub(p1, p0)
    if _v_length(d) < 1e-6:
        return []
    d = _v_normalize(d)
    u, v = _perp_basis(d)
    hu, hv = _v_scale(u, half_width), _v_scale(v, half_width)
    b0 = _v_sub(_v_sub(p0, hu), hv)
    b1 = _v_sub(_v_add(p0, hu), hv)
    b2 = _v_add(_v_add(p0, hu), hv)
    b3 = _v_add(_v_sub(p0, hu), hv)
    offset = _v_sub(p1, p0)
    t0, t1, t2, t3 = _v_add(b0, offset), _v_add(b1, offset), _v_add(b2, offset), _v_add(b3, offset)
    return _box_corner_triangles(b0, b1, b2, b3, t0, t1, t2, t3)


def _triangle_normal(p0, p1, p2):
    return _v_normalize(_v_cross(_v_sub(p1, p0), _v_sub(p2, p0)))


# --- MULTI LINE / POLY solid extrude: unlike LINE/CIRCLE/ARC (hollow
# struts, see the module comment above), a closed POLY shape gets a
# genuinely solid prism -- a triangulated flat cap top and bottom plus
# straight side walls -- so EXTRUDE on it (e.g. a hand-placed star
# outline) produces something actually printable, not another
# wireframe. Ear-clipping handles concave outlines like a star fine;
# it only assumes the polygon is simple (edges don't cross themselves).
def _polygon_signed_area2d(pts2d):
    area = 0.0
    n = len(pts2d)
    for i in range(n):
        u0, v0 = pts2d[i]
        u1, v1 = pts2d[(i + 1) % n]
        area += u0 * v1 - u1 * v0
    return area * 0.5


def _point_in_triangle2d(p, a, b, c):
    def sign(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
    d1 = sign(p, a, b)
    d2 = sign(p, b, c)
    d3 = sign(p, c, a)
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)


def _ear_clip_triangulate(pts2d):
    # simple (non-self-intersecting) polygon, any winding -- returns a
    # list of (i, j, k) index-triples into pts2d. Degenerates
    # gracefully (returns whatever it managed) rather than raising on
    # a shape it can't fully clip, since a slightly imperfect cap
    # beats no export at all
    n = len(pts2d)
    if n < 3:
        return []
    order = list(range(n)) if _polygon_signed_area2d(pts2d) >= 0 else list(range(n - 1, -1, -1))
    triangles = []
    guard = 0
    while len(order) > 3 and guard < 400:
        guard += 1
        ear_found = False
        m = len(order)
        for k in range(m):
            ia, ib, ic = order[(k - 1) % m], order[k], order[(k + 1) % m]
            a, b, c = pts2d[ia], pts2d[ib], pts2d[ic]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 0:
                continue  # reflex or degenerate vertex, not a valid ear tip
            is_ear = True
            for other in order:
                if other in (ia, ib, ic):
                    continue
                if _point_in_triangle2d(pts2d[other], a, b, c):
                    is_ear = False
                    break
            if is_ear:
                triangles.append((ia, ib, ic))
                del order[k]
                ear_found = True
                break
        if not ear_found:
            break  # degenerate/self-intersecting input; use what we have
    if len(order) == 3:
        triangles.append((order[0], order[1], order[2]))
    return triangles


def _poly_solid_triangles(points, i, j, axis, height):
    # points: closed loop, all sharing the plane's constant axis (i, j
    # are the two in-plane indices, axis the extrude direction, same
    # convention as Model3DPage.PLANE_AXES/_plane_normal_axis)
    n = len(points)
    if n < 3:
        return []
    pts2d = [(p[i], p[j]) for p in points]
    tris2d = _ear_clip_triangulate(pts2d)
    if not tris2d:
        return []

    def lift(p, amount):
        q = list(p)
        q[axis] += amount
        return tuple(q)

    top_points = [lift(p, height) for p in points]

    # the bottom cap must face -axis (outward/down) and the top +axis
    # -- checked against the actual first triangle produced rather
    # than derived by hand, since ear-clipping's internal handling of
    # CW vs CCW input makes the "obvious" formula wrong for some of
    # the three planes (confirmed by testing all three against an
    # outward-normal check before trusting this)
    ia0, ib0, ic0 = tris2d[0]
    bottom_reversed = _triangle_normal(points[ia0], points[ib0], points[ic0])[axis] > 0
    input_reversed = _polygon_signed_area2d(pts2d) < 0

    triangles = []
    for (ia, ib, ic) in tris2d:
        if bottom_reversed:
            triangles.append((points[ia], points[ic], points[ib]))
        else:
            triangles.append((points[ia], points[ib], points[ic]))
    for (ia, ib, ic) in tris2d:
        if bottom_reversed:
            triangles.append((top_points[ia], top_points[ib], top_points[ic]))
        else:
            triangles.append((top_points[ia], top_points[ic], top_points[ib]))
    # side walls -- judged by the ORIGINAL input's own winding, not
    # bottom_reversed (ear-clipping already normalises CW input to CCW
    # internally, so bottom_reversed alone doesn't tell us which way
    # points[e]/points[e+1] actually run)
    for e in range(n):
        p0b, p1b = points[e], points[(e + 1) % n]
        p0t, p1t = top_points[e], top_points[(e + 1) % n]
        if bottom_reversed != input_reversed:
            triangles.append((p0b, p1b, p1t))
            triangles.append((p0b, p1t, p0t))
        else:
            triangles.append((p1b, p0b, p0t))
            triangles.append((p1b, p0t, p1t))
    return triangles


# --- RADIUS: rounds the outer corner where two BOX walls meet at a
# right angle -- e.g. two adjacent walls of a printed enclosure. Only
# handles this one case (two axis-aligned walls sharing a full-height
# vertical edge), not arbitrary object pairs or box-to-box fillets in
# general, which would need real solid boolean operations -- this
# instead trims both walls back from the shared corner and fills the
# gap with a quarter-cylinder POLY (reusing _poly_solid_triangles), so
# no new export code was needed for the actual solid.
def _wall_corner_info(boxA, boxB):
    # boxA/boxB: ((x0,y0,z0),(x1,y1,z1)) already normalized so
    # c0[i] <= c1[i]. Returns None if these don't look like two
    # perpendicular walls of the same height sharing an outer corner.
    a0, a1 = boxA
    b0, b1 = boxB
    if abs(a0[2] - b0[2]) > 1e-6 or abs(a1[2] - b1[2]) > 1e-6:
        return None  # different height ranges -- not matching walls
    aw = (a1[0] - a0[0], a1[1] - a0[1])
    bw = (b1[0] - b0[0], b1[1] - b0[1])
    thin_a = 0 if aw[0] < aw[1] else 1
    thin_b = 0 if bw[0] < bw[1] else 1
    if thin_a == thin_b:
        return None  # parallel (or both square) -- not a corner pair
    long_a, long_b = 1 - thin_a, 1 - thin_b
    a_min, a_max = [a0[0], a0[1]], [a1[0], a1[1]]
    b_min, b_max = [b0[0], b0[1]], [b1[0], b1[1]]

    # which end of A's long axis does B's thin slab sit nearest?
    b_thin_center = (b_min[thin_b] + b_max[thin_b]) / 2.0
    a_at_start = abs(b_thin_center - a_min[long_a]) <= abs(b_thin_center - a_max[long_a])
    a_corner_coord = a_min[long_a] if a_at_start else a_max[long_a]

    # which end of B's long axis does A's thin slab sit nearest?
    a_thin_center = (a_min[thin_a] + a_max[thin_a]) / 2.0
    b_at_start = abs(a_thin_center - b_min[long_b]) <= abs(a_thin_center - b_max[long_b])
    b_corner_coord = b_min[long_b] if b_at_start else b_max[long_b]

    corner = [0.0, 0.0]
    corner[long_a] = a_corner_coord   # same physical axis as thin_b
    corner[thin_a] = b_corner_coord   # same physical axis as long_b

    a_outer_at_min = abs(a_min[thin_a] - corner[thin_a]) < abs(a_max[thin_a] - corner[thin_a])

    return {
        "corner_xy": tuple(corner), "z0": a0[2], "z1": a1[2],
        "long_a": long_a, "thin_a": thin_a, "a_at_start": a_at_start, "a_outer_at_min": a_outer_at_min,
        "long_b": long_b, "thin_b": thin_b, "b_at_start": b_at_start,
    }


def _wall_radius_pie(boxA, boxB, radius):
    # returns (new_boxA, new_boxB, pie_points, wall_height), or raises
    # ValueError if these boxes aren't a valid corner pair or the
    # radius doesn't fit -- pie_points is a closed loop (centre point
    # plus an arc) ready to hand straight to a POLY entry, already
    # "extruded" (its height is the wall height, not 0) since it's a
    # real 3D wall from the moment it's created, not a flat sketch
    info = _wall_corner_info(boxA, boxB)
    if info is None:
        raise ValueError("these two boxes don't share a vertical outer edge")
    a0, a1 = [list(boxA[0]), list(boxA[1])]
    b0, b1 = [list(boxB[0]), list(boxB[1])]
    la, ta = info["long_a"], info["thin_a"]
    lb = info["long_b"]
    a_len = a1[la] - a0[la]
    b_len = b1[lb] - b0[lb]
    if radius <= 0 or radius >= a_len or radius >= b_len:
        raise ValueError("radius too large for one of these walls")

    dir_a = 1.0 if info["a_at_start"] else -1.0
    if info["a_at_start"]:
        a0[la] += radius
    else:
        a1[la] -= radius
    if info["b_at_start"]:
        b0[lb] += radius
    else:
        b1[lb] -= radius

    corner = list(info["corner_xy"])
    in_dir_a = 1.0 if info["a_outer_at_min"] else -1.0
    center = [0.0, 0.0]
    center[la] = corner[la] + dir_a * radius
    center[ta] = corner[ta] + in_dir_a * radius

    # the two points where the arc meets each (now-trimmed) wall end --
    # each shares the centre's long-axis position but stays out at the
    # OTHER wall's untrimmed outer face on the thin axis
    edge_a_pt = [0.0, 0.0]
    edge_a_pt[la] = center[la]
    edge_a_pt[ta] = corner[ta]
    edge_b_pt = [0.0, 0.0]
    edge_b_pt[la] = corner[la]
    edge_b_pt[ta] = center[ta]

    def ang(pt):
        return math.degrees(math.atan2(pt[1] - center[1], pt[0] - center[0]))
    a0deg, a1deg = ang(edge_b_pt), ang(edge_a_pt)
    delta = (a1deg - a0deg + 180) % 360 - 180  # shortest signed turn, always the 90deg way

    z0, z1 = info["z0"], info["z1"]
    segs = max(2, int(round(8 * abs(delta) / 90.0)))
    pie_points = [(center[0], center[1], z0)]
    for i in range(segs + 1):
        deg = math.radians(a0deg + delta * i / segs)
        pie_points.append((center[0] + radius * math.cos(deg), center[1] + radius * math.sin(deg), z0))

    return (tuple(a0), tuple(a1)), (tuple(b0), tuple(b1)), pie_points, (z1 - z0)


def _box_corner_pie(box, x_side, y_side, radius):
    # rounds ONE box's own corner directly -- x_side/y_side are each
    # "min" or "max", picking which of its 4 vertical corners. Same
    # trim-and-fill-with-a-quarter-cylinder idea as _wall_radius_pie,
    # just without needing a second box to find the corner from.
    c0, c1 = list(box[0]), list(box[1])
    x_len, y_len = c1[0] - c0[0], c1[1] - c0[1]
    if radius <= 0 or radius >= x_len or radius >= y_len:
        raise ValueError("radius too large for this box")
    corner_x = c0[0] if x_side == "min" else c1[0]
    corner_y = c0[1] if y_side == "min" else c1[1]
    dir_x = 1.0 if x_side == "min" else -1.0
    dir_y = 1.0 if y_side == "min" else -1.0
    if x_side == "min":
        c0[0] += radius
    else:
        c1[0] -= radius
    if y_side == "min":
        c0[1] += radius
    else:
        c1[1] -= radius

    center = (corner_x + dir_x * radius, corner_y + dir_y * radius)
    edge_x_pt = (center[0], corner_y)   # meets the X-trimmed edge, at the untrimmed Y extreme
    edge_y_pt = (corner_x, center[1])   # meets the Y-trimmed edge, at the untrimmed X extreme

    def ang(pt):
        return math.degrees(math.atan2(pt[1] - center[1], pt[0] - center[0]))
    a0deg, a1deg = ang(edge_y_pt), ang(edge_x_pt)
    delta = (a1deg - a0deg + 180) % 360 - 180

    z0, z1 = box[0][2], box[1][2]
    segs = max(2, int(round(8 * abs(delta) / 90.0)))
    pie_points = [(center[0], center[1], z0)]
    for i in range(segs + 1):
        deg = math.radians(a0deg + delta * i / segs)
        pie_points.append((center[0] + radius * math.cos(deg), center[1] + radius * math.sin(deg), z0))

    return (tuple(c0), tuple(c1)), pie_points, (z1 - z0)


STL_DIR = "/sd/stl"


def write_stl_file(path, triangles):
    f = open(path, "wb")
    try:
        header = b"model3d_editor STL export"
        f.write(header + b"\x00" * (80 - len(header)))
        f.write(struct.pack("<I", len(triangles)))
        for (p0, p1, p2) in triangles:
            n = _triangle_normal(p0, p1, p2)
            f.write(struct.pack("<3f", n[0], n[1], n[2]))
            f.write(struct.pack("<3f", p0[0], p0[1], p0[2]))
            f.write(struct.pack("<3f", p1[0], p1[1], p1[2]))
            f.write(struct.pack("<3f", p2[0], p2[1], p2[2]))
            f.write(struct.pack("<H", 0))
    finally:
        f.close()


def save_stl_file(name, triangles):
    try:
        os.mkdir(STL_DIR)
    except OSError:
        pass  # already exists
    path = STL_DIR + "/" + name + ".stl"
    write_stl_file(path, triangles)
    return path


# command name -> icon file under ICONS_DIR (see assets/icons/*.svg in
# the repo -- rendered to 26x26 BMP) -- module level so both
# Model3DPage's own buttons and HelpPage's icon-illustrated entries for
# the "model3d" topic can use the same mapping
ICON_NAMES = {
    "NEW FILE": "new_file", "OPEN": "open", "SAVE AS": "save_as", "DELETE": "delete",
    "SELECT": "select", "LINE": "line", "CTR LINE": "centerline", "BOX": "box",
    "CIRCLE": "circle", "ARC": "arc", "MULTI LINE": "multi_line", "RADIUS": "radius", "GRID": "grid",
}

HELP_TEXT = {
    "model3d": ("3D Model Editor", [
        ("NEW FILE", "Clears everything currently modelled and starts from a blank canvas (undoable)."),
        ("OPEN", "Pick a saved model from the list and load it into the viewer."),
        ("SAVE AS", "Type a name and save everything currently modelled to the SD card."),
        ("DELETE", "If something is SELECTED (highlighted red), removes just that item (undoable). Otherwise, pick a saved model from the list and remove that file."),
        ("SELECT", "Click near an item's outline in the VIEW panel to select it (highlighted red) -- press DELETE to remove it, or pick another command to cancel."),
        ("LINE", "Choose CLICK ON GRID (tap start then end point in the VIEW panel, snaps to the grid if one's set) or TYPE VALUES (enter X/Y/Z numbers)."),
        ("CTR LINE", "Pick an axis (tap to cycle X/Y/Z) and a length -- adds a line through the origin along that axis. Snaps the length to the nearest GRID spacing if a grid is set."),
        ("BOX", "Choose CLICK ON GRID (tap one corner then the opposite corner in the VIEW panel) or TYPE VALUES (enter X/Y/Z numbers)."),
        ("CIRCLE", "Enter a centre point and radius; tap the plane button to cycle XY/XZ/YZ. Adds a selectable centre-mark crosshair through the middle too."),
        ("ARC", "Same as CIRCLE plus a start/end angle in degrees, swept counter-clockwise."),
        ("MULTI LINE", "Type how many points (3+), then click each one in the VIEW panel in order -- the last point connects back to the first, forming a closed shape (e.g. a star). SELECT + EXTRUDE turns it into a solid, not just an outline."),
        ("RADIUS", "Click two BOX walls that meet at a right angle (e.g. two adjacent enclosure walls), then give a radius in mm -- rounds that outer corner, trimming both walls and filling the gap with a solid quarter-round. Click the SAME wall twice instead to round one of its own corners (e.g. a flat base plate)."),
        ("GRID", "Set a spacing, extent, plane (tap to cycle XY/XZ/YZ), and position along that plane's normal axis (e.g. Y for an XZ 'vertical' grid, to line it up with a wall). Replaces any existing grid. Once set, every typed X/Y/Z/radius/angle value in every dialog rounds to this spacing."),
        ("LAYER button", "Shows the active layer -- new items go on it. Opens LAYERS: pick one then SET ACTIVE, TOGGLE SHOW (hide/unhide), or NEW LAYER."),
        ("VIEW panel", "Rotatable view of everything modelled -- X is red, Y is green, Z is blue, all from the origin marked 0,0."),
        ("+ / - / RST", "Zoom in, zoom out, or reset the view back to its default position, zoom, and rotation."),
        ("U / D / L / R", "Pan the view up/down/left/right in fixed steps."),
        ("AZ - / AZ +", "Spin the viewpoint left/right around the model."),
        ("EL - / EL +", "Tilt the viewpoint down/up, from edge-on towards looking straight down."),
        ("WIRE", "Show or hide LINE/CIRCLE/ARC entries -- BOX, the grid, and the axis arrows stay visible either way."),
        ("GRID button", "Below the mouse position readout -- shows or hides the GRID dots on their own, independent of WIRE."),
        ("SNAP", "Master on/off for grid snapping -- when off, every typed value and click position is used exactly as entered even if a GRID is set."),
        ("EXTRUDE", "SELECT anything first, then give a height in mm: LINE becomes a wall, BOX grows taller, CIRCLE becomes a cylinder, ARC becomes a curved wall, MULTI LINE becomes a solid extruded shape."),
        ("EDIT", "SELECT anything first -- opens its points/radius/angles pre-filled so you can fix a mistake without deleting and redrawing it. Also has its own DELETE THIS ITEM button."),
        ("UNDO / REDO", "Step back or forward through NEW FILE/OPEN/LINE/BOX/CIRCLE/ARC/GRID/EXTRUDE/EDIT changes."),
        ("MENU", "Exit the editor."),
    ]),
}


class Page:
    def __init__(self):
        self.next = None

    def go(self, where):
        self.next = where

    def show(self):
        hdmi.fill(hdmi.fb().colour(PAGE))
        g = pcgui.GUI()
        self.g = g
        g.start()
        self.build(g)
        self.enter()
        while self.next is None:
            self.g.poll()
            time.sleep_ms(10)
        try:
            self.g.stop()
        except Exception:
            pass
        gc.collect()
        return self.next

    def enter(self):
        pass

    def help_button(self, g, topic, return_to):
        g.button(602, 4, 32, 26, "?", fg=WHITE, bg=BTN, font=2,
                 callback=lambda b: self.go("help|" + topic + "|" + return_to))


class HelpPage(Page):
    # content rows run from just under the title/BACK row down to
    # ROW_BOTTOM, leaving room below that for PREV/NEXT when a topic
    # doesn't fit on one screen
    ROW_TOP = 34
    ROW_BOTTOM = 404
    ICON_SIZE = 26
    ICON_GAP = 8

    def __init__(self, topic, return_to):
        Page.__init__(self)
        self.topic = topic
        self.return_to = return_to
        self.page = 0

    def wrap(self, text, width=76):
        words = text.split(" ")
        lines = []
        cur = ""
        for word in words:
            candidate = (cur + " " + word).strip()
            if len(candidate) <= width:
                cur = candidate
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        if len(lines) > 2:
            lines = lines[:2]
            lines[1] = lines[1][:width - 3] + "..."
        return lines

    def _row_height(self, label, desc):
        text_h = 18 + 14 * len(self.wrap(desc, self._desc_width(label)))
        icon_h = self.ICON_SIZE if label in ICON_NAMES else 0
        return max(text_h, icon_h) + 8

    def _desc_width(self, label):
        # narrower wrap for rows with an icon -- their text starts
        # further right, so fewer characters fit per line
        return 66 if label in ICON_NAMES else 76

    def _paginate(self, entries):
        pages = []
        current = []
        y = self.ROW_TOP
        for entry in entries:
            h = self._row_height(entry[0], entry[1])
            if current and y + h > self.ROW_BOTTOM:
                pages.append(current)
                current = []
                y = self.ROW_TOP
            current.append(entry)
            y += h
        pages.append(current)
        return pages

    def _redraw(self):
        try:
            self.g.stop()
        except Exception:
            pass
        g = pcgui.GUI()
        self.g = g
        g.start()
        self.build(g)

    def build(self, g):
        title, entries = HELP_TEXT.get(self.topic, ("Help", []))
        pages = self._paginate(entries)
        self.page = max(0, min(self.page, len(pages) - 1))
        page_entries = pages[self.page]

        header = "Help -- " + title
        if len(pages) > 1:
            header += "  (%d/%d)" % (self.page + 1, len(pages))
        g.caption(320, 6, header, fg=INK, bg=PAGE, font=3, just="CT")
        g.button(486, 4, 140, 28, "BACK", fg=WHITE, bg=RED, font=2, callback=self.on_back)

        y = self.ROW_TOP
        for label, desc in page_entries:
            icon_name = ICON_NAMES.get(label)
            text_x = 20
            if icon_name:
                path = ICONS_DIR + "/" + icon_name + ".bmp"
                try:
                    pcimage.draw_bmp(path, 20, y, dither=True)
                except Exception as e:
                    ulog("HelpPage: icon load failed for " + label + ": " + type(e).__name__ + " " + str(e))
                text_x = 20 + self.ICON_SIZE + self.ICON_GAP
            g.caption(text_x, y, label, fg=INK, bg=PAGE, font=2)
            ty = y + 18
            for line in self.wrap(desc, self._desc_width(label)):
                g.caption(text_x + 10, ty, line, fg=INK, bg=PAGE, font=1)
                ty += 14
            y += self._row_height(label, desc)

        if len(pages) > 1:
            if self.page > 0:
                g.button(20, 440, 90, 28, "PREV", fg=WHITE, bg=BTN, font=2, callback=self.on_prev_page)
            if self.page < len(pages) - 1:
                g.button(530, 440, 90, 28, "NEXT", fg=WHITE, bg=BTN, font=2, callback=self.on_next_page)

    def on_prev_page(self, b):
        self.page -= 1
        self._redraw()

    def on_next_page(self, b):
        self.page += 1
        self._redraw()

    def on_back(self, b):
        self.go(self.return_to)


class Model3DPage(Page):
    # window chrome: an 8px grey border framing the whole 640x480
    # screen, drawn as concentric 1px g.frame() outlines (this app's
    # only bordered-box primitive) since there's no filled-rect call
    # available at the g level. INNER_* marks the usable area inside
    # the border for whatever gets built next.
    BORDER = 8
    GREY = 0x808080
    BLACK = 0x000000
    INNER_X0 = BORDER
    INNER_Y0 = BORDER
    INNER_X1 = 640 - BORDER
    INNER_Y1 = 480 - BORDER

    # left-hand commands panel geometry -- narrow now that the buttons
    # are icon-only (no text label to fit), which hands the reclaimed
    # width to the VIEW canvas below
    PANEL_X = 16
    PANEL_Y = 44
    PANEL_W = 56
    PANEL_H = 400

    # CMD_BTN_H has shrunk twice now (40->34->30, icons 32->26->22px)
    # to keep fitting more buttons in the same panel height as they've
    # been added.
    COMMANDS = ("NEW FILE", "OPEN", "SAVE AS", "DELETE", "SELECT", "LINE", "CTR LINE",
                "BOX", "CIRCLE", "ARC", "MULTI LINE", "RADIUS", "GRID", "TEMPLATE")
    CMD_BTN_H = 26  # shrunk again (30->26, icons 22->18px) to fit SELECT as an 11th button
    CMD_BTN_GAP = 5

    # centred modal dialog box used by NEW FILE / SAVE AS / DELETE --
    # width/x are shared, height/y vary per dialog since NEW FILE needs
    # three input rows and the others don't
    DLG_W = 320
    DLG_X = (640 - DLG_W) // 2

    # wireframe viewport -- the empty area right of the commands panel,
    # below the status readout and above the MENU button
    CANVAS_X0 = PANEL_X + PANEL_W + 20
    CANVAS_Y0 = 76
    CANVAS_X1 = INNER_X1 - 8
    CANVAS_Y1 = 396
    CANVAS_W = CANVAS_X1 - CANVAS_X0
    CANVAS_H = CANVAS_Y1 - CANVAS_Y0
    CANVAS_CX = CANVAS_X0 + CANVAS_W // 2
    CANVAS_CY = CANVAS_Y0 + CANVAS_H // 2

    # zoom/reset buttons, top-right corner of the VIEW canvas
    ZOOM_BTN_Y = CANVAS_Y0 + 4
    ZOOM_BTN_W = 30
    ZOOM_BTN_H = 24
    RESET_BTN_W = 44
    RESET_VIEW_X = CANVAS_X1 - 4 - RESET_BTN_W
    ZOOM_IN_X = RESET_VIEW_X - 4 - ZOOM_BTN_W
    ZOOM_OUT_X = ZOOM_IN_X - 4 - ZOOM_BTN_W
    ZOOM_STEP = 1.2
    MIN_ZOOM = 0.2
    MAX_ZOOM = 20.0  # raised from 5.0 -- 5x wasn't enough to work on a small part of a larger model

    # undo/redo, directly below the zoom row -- edit controls, not
    # drawing tools, so (like zoom) no CONFIRM popup for these
    UNDO_REDO_Y = ZOOM_BTN_Y + ZOOM_BTN_H + 4
    UNDO_REDO_W = 55
    UNDO_REDO_H = 24
    UNDO_MAX = 20  # capped so this doesn't grow without bound on an embedded board

    # hard cap on GRID dot count -- a 1mm spacing over the default
    # 100mm extent is 40,401 points (161,604 _fb_pixel calls in one
    # synchronous loop), which is what actually caused a board
    # hang/reset from far too much blocking pixel-pushing at once
    GRID_MAX_DOTS = 500
    REDO_X = CANVAS_X1 - 4 - UNDO_REDO_W
    UNDO_X = REDO_X - 4 - UNDO_REDO_W

    # LAYERS button, directly below the undo/redo row, spanning the
    # same combined width
    LAYERS_BTN_Y = UNDO_REDO_Y + UNDO_REDO_H + 4
    LAYERS_BTN_X = UNDO_X
    LAYERS_BTN_W = (REDO_X + UNDO_REDO_W) - UNDO_X
    LAYERS_BTN_H = 24

    # pan nudge buttons -- reliable click-based control (dragging was
    # tried and dropped -- see on_touch's caveat) stacked in the narrow
    # gap between the commands panel and the canvas
    PAN_NUDGE = 20
    DPAD_W = 18
    DPAD_H = 18
    DPAD_GAP = 4
    DPAD_X = CANVAS_X0 - DPAD_W - 1
    DPAD_Y0 = CANVAS_CY - (4 * DPAD_H + 3 * DPAD_GAP) // 2

    # two on_touch calls inside the VIEW canvas within this many ms of
    # each other count as one drag -- see the caveat on on_touch
    DRAG_TIMEOUT_MS = 500

    # rotate/wireframe row, directly under the VIEW canvas -- azimuth
    # (spin) and elevation (tilt) step buttons plus the wireframe
    # show/hide toggle, all left-aligned under the canvas so they never
    # reach as far right as MENU
    ROT_BTN_Y = CANVAS_Y1 + 6
    ROT_BTN_H = 26
    ROT_STEP_BTN_W = 56
    ROT_GAP = 6
    AZ_MINUS_X = CANVAS_X0
    AZ_PLUS_X = AZ_MINUS_X + ROT_STEP_BTN_W + ROT_GAP
    EL_MINUS_X = AZ_PLUS_X + ROT_STEP_BTN_W + ROT_GAP
    EL_PLUS_X = EL_MINUS_X + ROT_STEP_BTN_W + ROT_GAP
    WIRE_BTN_X = EL_PLUS_X + ROT_STEP_BTN_W + ROT_GAP + 10
    WIRE_BTN_W = 130

    # mouse position readout -- narrowed from its original 260 to make
    # room for GRID/EXTRUDE/SNAP/EDIT sharing the rest of this row
    MOUSE_BOX_W = 220

    # GRID show/hide toggle, SNAP master on/off, EXTRUDE, and EDIT all
    # share this row beside the mouse position readout, since the row
    # under the canvas is already full
    GRID_BTN_Y = PANEL_Y + PANEL_H + 4
    GRID_BTN_H = 20
    GRID_BTN_X = PANEL_X + MOUSE_BOX_W + 14
    GRID_BTN_W = 90
    EXTRUDE_BTN_X = GRID_BTN_X + GRID_BTN_W + 6
    EXTRUDE_BTN_W = 100
    SNAP_BTN_X = EXTRUDE_BTN_X + EXTRUDE_BTN_W + 6
    SNAP_BTN_W = 90
    EDIT_BTN_X = SNAP_BTN_X + SNAP_BTN_W + 6
    EDIT_BTN_W = 60

    # orbit-camera projection: an azimuth (spin around the vertical Z
    # axis) and an elevation (tilt between edge-on and looking straight
    # down) drive a plain rotation, then dropped straight to screen X/Y
    # -- orthographic, no perspective, no depth foreshortening, still
    # no quaternion/camera machinery. Z always renders straight up on
    # screen regardless of azimuth. The defaults below (45/30) reproduce
    # the project's original fixed isometric look -- X down-right,
    # Y down-left, Z up -- as just one point in the now-rotatable range.
    AZIMUTH_DEFAULT = 45.0
    ELEVATION_DEFAULT = 30.0
    AZIMUTH_STEP = 15.0
    ELEVATION_STEP = 10.0
    ELEVATION_MIN = -80.0
    ELEVATION_MAX = 80.0

    # world-space unit basis vectors spanning each GRID/click plane,
    # used to turn a screen click back into a 3D point on that plane
    # (see _screen_to_plane_point) -- generic across any azimuth/
    # elevation rather than a per-plane formula tied to one fixed view
    PLANE_BASIS = {"XY": ((1, 0, 0), (0, 1, 0)),
                   "XZ": ((1, 0, 0), (0, 0, 1)),
                   "YZ": ((0, 1, 0), (0, 0, 1))}

    # (0,0,0) is pinned to a fixed spot in the lower-right area of the
    # canvas rather than auto-centring the whole model -- as fractions
    # of the canvas, not a fixed margin from the corner, since a small
    # margin from the actual corner left almost no room on the
    # down-right side for a model that (with only positive X/Y/Z
    # modelled so far) always grows down and to both sides from here
    ORIGIN_X = CANVAS_X0 + CANVAS_W * 0.62
    ORIGIN_Y = CANVAS_Y0 + CANVAS_H * 0.75

    # axis gizmo -- direction + a perpendicular (for the arrowhead
    # wings) + colour per axis, always drawn from the origin so the
    # X/Y/Z planes stay readable regardless of what's been modelled.
    # Each arrow starts past wherever the model itself already reaches
    # along that axis (see _axis_extent) instead of at literal (0,0,0),
    # so it doesn't trace back over -- and cancel out -- a wireframe
    # edge running the same direction.
    AXIS_DIRS = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}
    AXIS_PERP = {"X": (0, 1, 0), "Y": (1, 0, 0), "Z": (1, 0, 0)}
    AXIS_COLORS = {"X": RED, "Y": 0x00CC00, "Z": 0x3399FF}

    # SELECT -- click near an element's projected outline to select it.
    # RED, not a raw hex literal like the original yellow (0xFFFF00) --
    # confirmed on real hardware that a "selected" item hit-tested fine
    # (status bar showed "SELECTED: ...") but rendered as nothing at
    # all, which a raw untested colour value silently failing in
    # _fb_line/_fb_pixel's own try/except would explain. RED is
    # imported from pcgfx (like WHITE) rather than being a raw literal,
    # and is already proven to draw via this exact framebuffer path
    # (the dashed active-command frame, the LINE start-point marker).
    SELECT_COLOR = RED
    CIRCLE_PREVIEW_COLOR = 0xFFFF00  # yellow -- distinct from SELECT_COLOR/grid grey/geometry white
    SELECT_THRESHOLD = 15    # px -- closest hit within this radius wins

    def __init__(self):
        Page.__init__(self)
        # build() runs before enter() (Page.show()), so anything build()
        # reads must exist before the first build() call
        self.dialog = None        # None, "open", "saveas", "delete", "line",
                                   # "box", "circle", or "arc"
        self.model_name = "mycar"
        self.stl_strut_thickness = 4.0  # mm -- default cross-section for solidified LINE/CIRCLE/ARC edges
        self.boxes = []             # list of ((x0,y0,z0), (x1,y1,z1)) opposite corners
        self.lines = []             # list of ((x0,y0,z0), (x1,y1,z1)) segments
        self.circles = []           # list of ((cx,cy,cz), radius, plane)
        self.arcs = []               # list of ((cx,cy,cz), radius, plane, start_deg, end_deg)
        self.polys = []              # list of (points, plane, extrude_height, layer) -- see MULTI LINE
        self.multiline_points = []   # points placed so far in the current MULTI LINE pick
        self.multiline_target = 0    # how many points MULTI LINE is waiting for
        self.radius_pick_a = None    # index into self.boxes of RADIUS's first picked wall
        self.radius_pick_b = None    # index into self.boxes of RADIUS's second picked wall
        self.radius_corner_side = None  # (x_side, y_side) once a single box's own corner is picked
        self._radius_dialog_message = ""

        self.line_start_point = None
        self.line_stage = "start"  # "start" or "end", within the LINE dialog
        self.box_start_point = None
        self.box_stage = "start"   # "start" or "end", within the BOX dialog
        self.circle_plane = "XY"   # cycles XY -> XZ -> YZ, within the CIRCLE dialog
        self._circle_radius_pending = None  # typed radius, preserved across a same-dialog redraw
        self._circle_pick_radius = 20.0     # confirmed radius, used once CIRCLE switches to click-to-place
        self._axis_label_widgets = []  # g.caption() widgets from the last _draw_axes call -- removed
                                        # before creating new ones so repeated lightweight _draw_scene()
                                        # calls (e.g. live mouse polling) don't pile up stale duplicates
        self.arc_plane = "XY"      # same, within the ARC dialog
        self.grid_plane = "XY"     # same, within the GRID dialog
        self.grid = None          # (plane, spacing, extent_i, extent_j, position) or None -- one
                                   # grid at a time, a fresh GRID replaces whatever grid was there
        self.snap_enabled = True  # master switch -- grid snapping only actually applies
                                   # when this is True AND self.grid is set
        self.centerline_axis = "X"  # cycles X -> Y -> Z, within the CTR LINE dialog

        # layers -- every box/line/circle/arc is tagged with the name
        # of whichever layer was "active" (current_layer) when it was
        # created. Hidden layers are skipped entirely by drawing, the
        # auto-fit scale, and SELECT's hit-testing.
        self.layers = ["Layer1"]
        self.current_layer = "Layer1"
        self.layer_visible = {"Layer1": True}
        self._dialog_selected_layer = None
        self._layers_dialog_message = ""  # feedback shown inside the LAYERS dialog, e.g. why a delete was blocked

        self._dialog_file_names = []     # filled in by _build_file_list_dialog
        self._dialog_selected_name = None  # read by on_confirm_open / on_confirm_delete

        # view pan/zoom -- pan is a screen-pixel offset added on top of
        # the fixed ORIGIN_X/ORIGIN_Y anchor, zoom multiplies the
        # auto-fit scale. Dragging is reconstructed from on_touch
        # (confirmed working) rather than on_move (confirmed NOT
        # working) -- see on_touch for the caveat about what that means
        # in practice.
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 1.0
        self.azimuth_deg = self.AZIMUTH_DEFAULT
        self.elevation_deg = self.ELEVATION_DEFAULT
        self._update_rotation_trig()
        self.wireframe_visible = True  # hides boxes/lines/circles/arcs when off; grid/axes stay
        self.grid_visible = True       # independent of wireframe_visible -- hides just the grid dots
        self._last_touch = None
        self._last_touch_time = 0
        self._last_scale = 1.0            # set for real by _draw_scene each redraw --
        self._last_origin = (0.0, 0.0)    # used by on_touch to report a model-space position

        self.box_pick_start = None  # BOX's "CLICK ON GRID" mode -- first corner, or None

        # diagnostic only -- counts every on_touch call regardless of
        # dialog state, logged via ulog() so a hardware test can tell
        # "on_touch never fired" apart from "on_touch fired but the
        # pick logic did nothing"
        self.touch_count = 0

        self.active_command = None  # last command clicked, gets the red dashed frame
        self.selected = None  # (kind, index) e.g. ("box", 0), or None -- highlighted red

        self.undo_stack = []  # snapshots of (boxes, lines, circles, arcs, grid)
        self.redo_stack = []  # cleared whenever a new action is taken, not just undone

        # most recent EXTRUDE's base + the geometry it generated, or
        # None -- lets a second EXTRUDE on the same (just-edited) base
        # replace the old generated pieces instead of adding a stale
        # duplicate ("refresh"), and lets SELECT highlight the whole
        # group instead of just whichever piece was clicked. Cleared
        # whenever indices could no longer be trusted (DELETE/UNDO/
        # REDO/NEW FILE/OPEN) -- see _remove_generated.
        self._last_extrude = None

        # live mouse tracking -- pcgui.GUI itself only ever fires
        # on_touch (a discrete click), but pcgui.pccursor.mouse.query()
        # is a separate, lower-level HID poll that returns the mouse's
        # current screen position at any moment, click or not. Confirmed
        # on real hardware: query('present') is 1 with a mouse attached,
        # query('x')/query('y') read back live screen coordinates.
        # _last_live_mouse_xy avoids redundant readout updates (and the
        # position-readout math) on every 10ms tick when the mouse
        # hasn't actually moved since the last poll.
        self._last_live_mouse_xy = None

        # template wireframes -- see save_wireframe_file/load_template_active
        # near the top of this file. Independent of the open model:
        # loaded once here, not touched by NEW FILE/OPEN, not part of
        # undo/redo. template_main/template_local are the actual
        # (size, spacing, scale, centerlines, show_xy, show_xz, show_yz)
        # configs currently active, or None if that slot is unset or its
        # saved file has gone missing.
        self.template_main_name, self.template_local_name = load_template_active()
        self.template_main = self._safe_load_wireframe(self.template_main_name)
        self.template_local = self._safe_load_wireframe(self.template_local_name)
        self._template_dialog_message = ""
        # NEW TEMPLATE dialog's own working fields, separate from the
        # active MAIN/LOCAL config above -- only written into a saved
        # .wf file (and possibly promoted to a slot) on SAVE
        self._template_new_pending = None  # (name, size, spacing, scale) strings, preserved across a same-dialog redraw
        self._template_new_centerlines = True
        self._template_new_xy = True
        self._template_new_xz = True
        self._template_new_yz = True

    def _safe_load_wireframe(self, name):
        if not name:
            return None
        try:
            return load_wireframe_file(name)
        except OSError as e:
            ulog("Model3DPage: template '%s' missing: %s" % (name, e))
            return None

    def show(self):
        # overrides Page.show() to add a live mouse-position poll into
        # the same 10ms tick loop that already drives g.poll() -- see
        # _poll_live_mouse. Everything else here matches Page.show()
        # exactly.
        hdmi.fill(hdmi.fb().colour(PAGE))
        g = pcgui.GUI()
        self.g = g
        g.start()
        self.build(g)
        self.enter()
        while self.next is None:
            self.g.poll()
            self._poll_live_mouse()
            time.sleep_ms(10)
        try:
            self.g.stop()
        except Exception:
            pass
        gc.collect()
        return self.next

    def _poll_live_mouse(self):
        if self.dialog not in (None, "line_pick", "select_pick", "box_pick", "circle_pick", "multiline_pick",
                                "radius_pick_a", "radius_pick_b", "radius_pick_corner"):
            # no mouse_box on any other (modal) dialog -- see _build_main
            return
        try:
            if not pcgui.pccursor.mouse.query("present"):
                return
            x = pcgui.pccursor.mouse.query("x")
            y = pcgui.pccursor.mouse.query("y")
        except Exception as e:
            ulog("Model3DPage: live mouse query failed: " + str(e))
            return
        if (x, y) == self._last_live_mouse_xy:
            return
        self._last_live_mouse_xy = (x, y)
        try:
            self.mouse_box.value = self._safe_position_readout(x, y)
        except Exception as e:
            ulog("Model3DPage: live mouse readout failed: " + str(e))
        if self.dialog == "circle_pick":
            # lightweight repaint (just the framebuffer scene, not a
            # full widget rebuild) so the snap-preview marker follows
            # the mouse smoothly -- safe to call every tick now that
            # _draw_axes cleans up its own widgets first
            try:
                self._draw_scene(self.g)
            except Exception as e:
                ulog("Model3DPage: circle preview redraw failed: " + str(e))

    def build(self, g):
        hdmi.fill(hdmi.fb().colour(self.BLACK))
        for i in range(self.BORDER):
            g.frame(i, i, 640 - 2 * i, 480 - 2 * i, "", fg=self.GREY, font=1)
        g.caption(320, self.INNER_Y0 + 6, "3D Model Editor", fg=WHITE, bg=self.BLACK, font=3, just="CT")
        self.help_button(g, "model3d", "model3d")

        if self.dialog == "open":
            self._build_open_dialog(g)
        elif self.dialog == "saveas":
            self._build_saveas_dialog(g)
        elif self.dialog == "delete":
            self._build_delete_dialog(g)
        elif self.dialog == "line_choice":
            self._build_line_choice_dialog(g)
        elif self.dialog == "line":
            self._build_line_dialog(g)
        elif self.dialog == "centerline":
            self._build_centerline_dialog(g)
        elif self.dialog == "box_choice":
            self._build_box_choice_dialog(g)
        elif self.dialog == "box":
            self._build_box_dialog(g)
        elif self.dialog == "circle":
            self._build_circle_dialog(g)
        elif self.dialog == "arc":
            self._build_arc_dialog(g)
        elif self.dialog == "multiline":
            self._build_multiline_dialog(g)
        elif self.dialog == "radius":
            self._build_radius_dialog(g)
        elif self.dialog == "grid":
            self._build_grid_dialog(g)
        elif self.dialog == "extrude":
            self._build_extrude_dialog(g)
        elif self.dialog == "edit":
            self._build_edit_dialog(g)
        elif self.dialog == "layers":
            self._build_layers_dialog(g)
        elif self.dialog == "template":
            self._build_template_dialog(g)
        elif self.dialog == "template_pick_main":
            self._build_wireframe_list_dialog(g, "PICK MAIN", "SELECT", self.on_confirm_pick_main)
        elif self.dialog == "template_pick_local":
            self._build_wireframe_list_dialog(g, "PICK LOCAL", "SELECT", self.on_confirm_pick_local)
        elif self.dialog == "template_delete":
            self._build_wireframe_list_dialog(g, "DELETE TEMPLATE", "DELETE", self.on_confirm_delete_template)
        elif self.dialog == "template_new":
            self._build_template_new_dialog(g)
        elif (self.dialog == "line_pick" or self.dialog == "select_pick" or self.dialog == "box_pick"
              or self.dialog == "circle_pick" or self.dialog == "multiline_pick"
              or self.dialog == "radius_pick_a" or self.dialog == "radius_pick_b"
              or self.dialog == "radius_pick_corner"):
            # reuses the normal main layout (canvas, zoom, D-pad, all
            # of it) rather than a modal -- picking points/elements
            # needs the wireframe/grid actually visible and clickable,
            # which no modal dialog in this app currently shows
            self._build_main(g)
        else:
            self._build_main(g)

    # command name -> its real dialog key
    COMMAND_DIALOG = {
        "OPEN": "open", "SAVE AS": "saveas", "DELETE": "delete",
        "SELECT": "select_pick", "LINE": "line_choice", "CTR LINE": "centerline", "BOX": "box_choice",
        "CIRCLE": "circle", "ARC": "arc", "MULTI LINE": "multiline", "RADIUS": "radius_pick_a",
        "GRID": "grid", "TEMPLATE": "template",
    }

    def _build_main(self, g):
        g.frame(self.PANEL_X, self.PANEL_Y, self.PANEL_W, self.PANEL_H, "COMMANDS", fg=WHITE, font=1)

        btn_x = self.PANEL_X + 6
        btn_w = self.PANEL_W - 12
        y = self.PANEL_Y + 26
        icon_slots = []
        button_rects = []
        for name in self.COMMANDS:
            # blank label, background matches the page so only the icon
            # shows -- real click handling still goes through this
            # button's own callback, the icon is just drawn on top
            g.button(btn_x, y, btn_w, self.CMD_BTN_H, "", fg=WHITE, bg=self.BLACK, font=1,
                     callback=self._make_command_handler(name))
            icon_slots.append((name, btn_x + 4, y + 4))
            button_rects.append((name, btn_x, y, btn_w, self.CMD_BTN_H))
            y += self.CMD_BTN_H + self.CMD_BTN_GAP

        # status readout for whichever command was last pressed, in the
        # (currently empty) area to the right of the panel
        self.status_box = g.displaybox(self.PANEL_X + self.PANEL_W + 20, self.PANEL_Y,
                                        640 - self.BORDER - (self.PANEL_X + self.PANEL_W + 20) - 8, 24,
                                        "Ready", fg=WHITE, bg=self.BLACK, font=2)
        snap_status = "grid snap ON" if (self.grid and self.snap_enabled) else "not snapped"
        if self.dialog == "line_pick":
            verb = "START" if self.line_stage == "start" else "END"
            self.status_box.value = "LINE: click %s point in VIEW (%s) -- pick another command to cancel" % (verb, snap_status)
        elif self.dialog == "select_pick":
            self.status_box.value = "SELECT: click near an item in VIEW -- pick another command to cancel"
        elif self.dialog == "box_pick":
            verb = "FIRST" if self.box_pick_start is None else "OPPOSITE"
            self.status_box.value = "BOX: click %s corner in VIEW (%s) -- pick another command to cancel" % (verb, snap_status)
        elif self.dialog == "circle_pick":
            self.status_box.value = "CIRCLE: click centre in VIEW (%s) -- pick another command to cancel" % snap_status
        elif self.dialog == "multiline_pick":
            self.status_box.value = ("MULTI LINE: click point %d/%d in VIEW (%s) -- pick another command to cancel"
                                      % (len(self.multiline_points) + 1, self.multiline_target, snap_status))
        elif self.dialog == "radius_pick_a":
            self.status_box.value = "RADIUS: click the FIRST wall in VIEW -- pick another command to cancel"
        elif self.dialog == "radius_pick_b":
            self.status_box.value = ("RADIUS: click the SECOND wall (meeting the first), or click the SAME wall "
                                      "again to round one of its own corners")
        elif self.dialog == "radius_pick_corner":
            self.status_box.value = "RADIUS: click near the CORNER of that box to round -- pick another command to cancel"

        # mouse/touch coordinate readout below the panel
        self.mouse_box = g.displaybox(self.PANEL_X, self.PANEL_Y + self.PANEL_H + 4,
                                       self.MOUSE_BOX_W, 20, "X:--  Y:--  Z:--", fg=WHITE, bg=self.BLACK, font=1)
        grid_label = "GRID: ON" if self.grid_visible else "GRID: OFF"
        g.button(self.GRID_BTN_X, self.GRID_BTN_Y, self.GRID_BTN_W, self.GRID_BTN_H, grid_label,
                 fg=WHITE, bg=BTN, font=1, callback=self.on_toggle_grid_visible)
        snap_label = "SNAP: ON" if self.snap_enabled else "SNAP: OFF"
        g.button(self.SNAP_BTN_X, self.GRID_BTN_Y, self.SNAP_BTN_W, self.GRID_BTN_H, snap_label,
                 fg=WHITE, bg=BTN, font=1, callback=self.on_toggle_snap)
        g.button(self.EXTRUDE_BTN_X, self.GRID_BTN_Y, self.EXTRUDE_BTN_W, self.GRID_BTN_H, "EXTRUDE",
                 fg=WHITE, bg=BTN, font=1, callback=self.on_extrude_pressed)
        g.button(self.EDIT_BTN_X, self.GRID_BTN_Y, self.EDIT_BTN_W, self.GRID_BTN_H, "EDIT",
                 fg=WHITE, bg=BTN, font=1, callback=self.on_edit_pressed)
        try:
            g.on_touch(self.on_touch)
        except Exception as e:
            ulog("Model3DPage: on_touch registration failed: " + str(e))
        # on_move (continuous hover) and mouse-wheel zoom were both
        # tried and dropped again: dir(pcgui.GUI) on real hardware
        # shows on_touch as the only interactive input method this
        # class defines at all. on_move is a plain instance attribute
        # rather than a registration method (assigning it didn't
        # error), but assigning it made no observable difference on
        # real hardware -- the mouse position readout stayed silent
        # between clicks, confirming poll() never actually reads it.
        # It's still updated on every click via on_touch below.

        g.button(522, 410, 110, 32, "MENU", fg=WHITE, bg=RED, font=2, callback=self.on_back)

        g.frame(self.CANVAS_X0, self.CANVAS_Y0, self.CANVAS_W, self.CANVAS_H, "VIEW", fg=WHITE, font=1)
        g.button(self.ZOOM_OUT_X, self.ZOOM_BTN_Y, self.ZOOM_BTN_W, self.ZOOM_BTN_H, "-",
                 fg=WHITE, bg=BTN, font=2, callback=self.on_zoom_out)
        g.button(self.ZOOM_IN_X, self.ZOOM_BTN_Y, self.ZOOM_BTN_W, self.ZOOM_BTN_H, "+",
                 fg=WHITE, bg=BTN, font=2, callback=self.on_zoom_in)
        g.button(self.RESET_VIEW_X, self.ZOOM_BTN_Y, self.RESET_BTN_W, self.ZOOM_BTN_H, "RST",
                 fg=WHITE, bg=RED, font=1, callback=self.on_reset_view)
        g.button(self.UNDO_X, self.UNDO_REDO_Y, self.UNDO_REDO_W, self.UNDO_REDO_H, "UNDO",
                 fg=WHITE, bg=BTN, font=1, callback=self.on_undo)
        g.button(self.REDO_X, self.UNDO_REDO_Y, self.UNDO_REDO_W, self.UNDO_REDO_H, "REDO",
                 fg=WHITE, bg=BTN, font=1, callback=self.on_redo)
        g.button(self.LAYERS_BTN_X, self.LAYERS_BTN_Y, self.LAYERS_BTN_W, self.LAYERS_BTN_H,
                 "LAYER: " + self.current_layer, fg=WHITE, bg=BTN, font=1, callback=self.on_open_layers)

        dpad = (("U", self.on_pan_up), ("D", self.on_pan_down),
                ("L", self.on_pan_left), ("R", self.on_pan_right))
        for i, (label, callback) in enumerate(dpad):
            by = self.DPAD_Y0 + i * (self.DPAD_H + self.DPAD_GAP)
            g.button(self.DPAD_X, by, self.DPAD_W, self.DPAD_H, label,
                     fg=WHITE, bg=0x3399FF, font=1, callback=callback)

        g.button(self.AZ_MINUS_X, self.ROT_BTN_Y, self.ROT_STEP_BTN_W, self.ROT_BTN_H, "AZ -",
                 fg=WHITE, bg=0x3399FF, font=1, callback=self.on_rotate_az_minus)
        g.button(self.AZ_PLUS_X, self.ROT_BTN_Y, self.ROT_STEP_BTN_W, self.ROT_BTN_H, "AZ +",
                 fg=WHITE, bg=0x3399FF, font=1, callback=self.on_rotate_az_plus)
        g.button(self.EL_MINUS_X, self.ROT_BTN_Y, self.ROT_STEP_BTN_W, self.ROT_BTN_H, "EL -",
                 fg=WHITE, bg=0x3399FF, font=1, callback=self.on_rotate_el_minus)
        g.button(self.EL_PLUS_X, self.ROT_BTN_Y, self.ROT_STEP_BTN_W, self.ROT_BTN_H, "EL +",
                 fg=WHITE, bg=0x3399FF, font=1, callback=self.on_rotate_el_plus)
        wire_label = "WIRE: ON" if self.wireframe_visible else "WIRE: OFF"
        g.button(self.WIRE_BTN_X, self.ROT_BTN_Y, self.WIRE_BTN_W, self.ROT_BTN_H, wire_label,
                 fg=WHITE, bg=BTN, font=1, callback=self.on_toggle_wireframe)

        # raw framebuffer drawing happens LAST, strictly after every
        # widget above, so it can't be clobbered by the widget rebuild
        self._draw_scene(g)
        self._draw_command_icons(icon_slots)

        if self.active_command:
            for name, bx, by, bw, bh in button_rects:
                if name == self.active_command:
                    self._draw_dashed_rect(hdmi.fb(), bx - 2, by - 2, bw + 4, bh + 4, RED)
                    break

        if self.dialog == "line_pick" and self.line_stage == "end" and self.line_start_point:
            # marks where the start point landed -- the only feedback
            # available between the two clicks
            try:
                fb = hdmi.fb()
                sx, sy = self._project(self.line_start_point[0], self.line_start_point[1],
                                        self.line_start_point[2], self._last_scale,
                                        self._last_origin[0], self._last_origin[1])
                r = 5
                self._clipped_line(fb, sx - r, sy, sx + r, sy, RED)
                self._clipped_line(fb, sx, sy - r, sx, sy + r, RED)
            except Exception as e:
                ulog("Model3DPage: start marker draw error: " + type(e).__name__ + " " + str(e))

        if self.dialog == "box_pick" and self.box_pick_start:
            # marks where the first corner landed -- the only feedback
            # available between the two clicks (no live outline: that
            # needs on_move, confirmed not to fire on this hardware)
            try:
                fb = hdmi.fb()
                sx, sy = self._project(self.box_pick_start[0], self.box_pick_start[1],
                                        self.box_pick_start[2], self._last_scale,
                                        self._last_origin[0], self._last_origin[1])
                r = 5
                self._clipped_line(fb, sx - r, sy, sx + r, sy, RED)
                self._clipped_line(fb, sx, sy - r, sx, sy + r, RED)
            except Exception as e:
                ulog("Model3DPage: box start marker draw error: " + type(e).__name__ + " " + str(e))

        if self.dialog == "multiline_pick" and self.multiline_points:
            # shows the points placed so far, connected in order -- the
            # only feedback available between clicks (no live "follows
            # the mouse" segment, matching every other click-to-place
            # tool on this hardware -- see the on_touch drag caveat)
            try:
                fb = hdmi.fb()
                projected = [self._project(p[0], p[1], p[2], self._last_scale,
                                            self._last_origin[0], self._last_origin[1])
                             for p in self.multiline_points]
                for k in range(len(projected) - 1):
                    s0, s1 = projected[k], projected[k + 1]
                    self._clipped_line(fb, s0[0], s0[1], s1[0], s1[1], self.CIRCLE_PREVIEW_COLOR)
                sx, sy = projected[-1]
                r = 5
                self._clipped_line(fb, sx - r, sy, sx + r, sy, RED)
                self._clipped_line(fb, sx, sy - r, sx, sy + r, RED)
            except Exception as e:
                ulog("Model3DPage: multiline marker draw error: " + type(e).__name__ + " " + str(e))

    def _draw_command_icons(self, icon_slots):
        for name, ix, iy in icon_slots:
            icon_name = ICON_NAMES.get(name)
            if not icon_name:
                continue
            path = ICONS_DIR + "/" + icon_name + ".bmp"
            try:
                pcimage.draw_bmp(path, ix, iy, dither=True)
            except Exception as e:
                ulog("Model3DPage: icon load failed for " + name + ": " + type(e).__name__ + " " + str(e))

    # --- scene projection -------------------------------------------

    def _update_rotation_trig(self):
        # cached once per azimuth/elevation change rather than
        # recomputed per point -- _raw_project runs for every vertex of
        # every box/line/circle/arc/grid-dot in a redraw
        az = math.radians(self.azimuth_deg)
        el = math.radians(self.elevation_deg)
        self._rot_ct = math.cos(az)
        self._rot_st = math.sin(az)
        self._rot_cp = math.cos(el)
        self._rot_sp = math.sin(el)

    def _raw_project(self, x, y, z):
        # projects at scale=1, origin=(0,0) -- just used to measure
        # extents before the real scale/origin are known. Z is "up" on
        # screen at any azimuth; elevation 0 is edge-on (only Z moves
        # vertically), elevation 90 is straight down (only X/Y move
        # vertically, Z is invisible).
        ct, st, cp, sp = self._rot_ct, self._rot_st, self._rot_cp, self._rot_sp
        x1 = x * ct - y * st
        y1 = x * st + y * ct
        sx = x1
        sy = y1 * sp - z * cp
        return sx, sy

    # which two coordinate indices sweep around a circle/arc in each
    # plane -- the third index stays fixed at the centre's value
    PLANE_AXES = {"XY": (0, 1), "XZ": (0, 2), "YZ": (1, 2)}
    AXIS_NAMES = {0: "X", 1: "Y", 2: "Z"}

    def _plane_normal_axis(self, plane):
        # the one coordinate index NOT in PLANE_AXES[plane] -- 0/1/2
        # sum to 3, so subtracting the two in-plane indices leaves it
        i, j = self.PLANE_AXES[plane]
        return 3 - i - j

    def _box_corners(self, box):
        c0, c1 = box[0], box[1]
        xs, ys, zs = (c0[0], c1[0]), (c0[1], c1[1]), (c0[2], c1[2])
        return [(x, y, z) for x in xs for y in ys for z in zs]

    def _box_edges(self, box):
        c0, c1 = box[0], box[1]
        (x0, y0, z0), (x1, y1, z1) = c0, c1
        corners = {
            (0, 0, 0): (x0, y0, z0), (1, 0, 0): (x1, y0, z0),
            (0, 1, 0): (x0, y1, z0), (0, 0, 1): (x0, y0, z1),
            (1, 1, 0): (x1, y1, z0), (1, 0, 1): (x1, y0, z1),
            (0, 1, 1): (x0, y1, z1), (1, 1, 1): (x1, y1, z1),
        }
        edge_keys = [
            ((0, 0, 0), (1, 0, 0)), ((1, 0, 0), (1, 1, 0)), ((1, 1, 0), (0, 1, 0)), ((0, 1, 0), (0, 0, 0)),
            ((0, 0, 1), (1, 0, 1)), ((1, 0, 1), (1, 1, 1)), ((1, 1, 1), (0, 1, 1)), ((0, 1, 1), (0, 0, 1)),
            ((0, 0, 0), (0, 0, 1)), ((1, 0, 0), (1, 0, 1)), ((1, 1, 0), (1, 1, 1)), ((0, 1, 0), (0, 1, 1)),
        ]
        return [(corners[a], corners[b]) for a, b in edge_keys]

    def _circle_point(self, center, radius, plane, angle_deg):
        i, j = self.PLANE_AXES[plane]
        p = [center[0], center[1], center[2]]
        rad = math.radians(angle_deg)
        p[i] = center[i] + radius * math.cos(rad)
        p[j] = center[j] + radius * math.sin(rad)
        return (p[0], p[1], p[2])

    def _circle_bounds_points(self, center, radius, plane):
        return [self._circle_point(center, radius, plane, a) for a in (0, 90, 180, 270)]

    def _model_points(self):
        # everything actually modelled -- NOT the axis arrows and NOT
        # the grid (deliberately -- the grid's extent is usually much
        # bigger than the actual model, and letting it into the
        # auto-fit scale calculation shrinks the real model down to
        # fit the grid instead of the other way round)
        pts = []
        for box in self.boxes:
            if self.layer_visible.get(box[2], True):
                pts.extend(self._box_corners(box))
        for (p0, p1, layer) in self.lines:
            if self.layer_visible.get(layer, True):
                pts.append(p0)
                pts.append(p1)
        for (c, r, plane, layer) in self.circles:
            if self.layer_visible.get(layer, True):
                pts.extend(self._circle_bounds_points(c, r, plane))
        for (c, r, plane, a0, a1, layer) in self.arcs:
            if self.layer_visible.get(layer, True):
                pts.extend(self._circle_bounds_points(c, r, plane))
        for (points, plane, height, layer) in self.polys:
            if self.layer_visible.get(layer, True):
                pts.extend(points)
                if height:
                    axis = self._plane_normal_axis(plane)
                    for p in points:
                        top = list(p)
                        top[axis] += height
                        pts.append(tuple(top))
        return pts

    def _axis_length(self):
        pts = self._model_points()
        if not pts:
            return 50.0
        m = 0.0
        for (x, y, z) in pts:
            m = max(m, abs(x), abs(y), abs(z))
        return max(m * 1.3, 30.0)

    def _axis_extent(self, axis_index):
        pts = self._model_points()
        m = 0.0
        for p in pts:
            m = max(m, abs(p[axis_index]))
        return m

    def _scene_points(self):
        pts = self._model_points()
        length = self._axis_length()
        pts.append((0, 0, 0))
        for axis, d in self.AXIS_DIRS.items():
            pts.append((d[0] * length, d[1] * length, d[2] * length))
        return pts

    def _compute_transform(self, pts):
        # (0,0,0) is pinned at (ORIGIN_X, ORIGIN_Y) -- scale is
        # whatever fits the furthest point in each of the four
        # directions into the space actually available on that side
        # of the fixed anchor
        raws = [self._raw_project(p[0], p[1], p[2]) for p in pts]
        xs = [r[0] for r in raws] or [0.0]
        ys = [r[1] for r in raws] or [0.0]
        max_right = max(max(xs), 0.0)
        max_left = -min(min(xs), 0.0)
        max_down = max(max(ys), 0.0)
        max_up = -min(min(ys), 0.0)

        space_right = self.CANVAS_X1 - self.ORIGIN_X
        space_left = self.ORIGIN_X - self.CANVAS_X0
        space_down = self.CANVAS_Y1 - self.ORIGIN_Y
        space_up = self.ORIGIN_Y - self.CANVAS_Y0

        candidates = []
        for extent, space in ((max_right, space_right), (max_left, space_left),
                               (max_down, space_down), (max_up, space_up)):
            if extent > 0:
                candidates.append((space * 0.9) / extent)
        scale = min(candidates) if candidates else 1.0
        return scale * self.zoom, self.ORIGIN_X + self.pan_x, self.ORIGIN_Y + self.pan_y

    def _project(self, x, y, z, scale, origin_x, origin_y):
        sx, sy = self._raw_project(x, y, z)
        return origin_x + sx * scale, origin_y + sy * scale

    def _clip_to_canvas(self, x0, y0, x1, y1):
        # Cohen-Sutherland clip against the VIEW canvas rectangle --
        # without this, zooming in sends wireframe lines straight past
        # the canvas edge. Returns a clipped (x0,y0,x1,y1) or None.
        xmin, ymin, xmax, ymax = self.CANVAS_X0, self.CANVAS_Y0, self.CANVAS_X1, self.CANVAS_Y1

        def out_code(x, y):
            c = 0
            if x < xmin: c |= 1
            elif x > xmax: c |= 2
            if y < ymin: c |= 4
            elif y > ymax: c |= 8
            return c

        c0, c1 = out_code(x0, y0), out_code(x1, y1)
        for _ in range(8):  # bounded loop -- 4 clip edges is always enough
            if not (c0 | c1):
                return x0, y0, x1, y1
            if c0 & c1:
                return None
            c_out = c0 or c1
            if c_out & 8:
                x = x0 + (x1 - x0) * (ymax - y0) / (y1 - y0)
                y = ymax
            elif c_out & 4:
                x = x0 + (x1 - x0) * (ymin - y0) / (y1 - y0)
                y = ymin
            elif c_out & 2:
                y = y0 + (y1 - y0) * (xmax - x0) / (x1 - x0)
                x = xmax
            else:
                y = y0 + (y1 - y0) * (xmin - x0) / (x1 - x0)
                x = xmin
            if c_out == c0:
                x0, y0 = x, y
                c0 = out_code(x0, y0)
            else:
                x1, y1 = x, y
                c1 = out_code(x1, y1)
        return None

    def _clipped_line(self, fb, x0, y0, x1, y1, colour):
        clipped = self._clip_to_canvas(x0, y0, x1, y1)
        if clipped:
            _fb_line(fb, clipped[0], clipped[1], clipped[2], clipped[3], colour)

    def _draw_scene(self, g):
        pts = self._scene_points()
        if not pts:
            return
        try:
            scale, ox, oy = self._compute_transform(pts)
            self._last_scale, self._last_origin = scale, (ox, oy)
            fb = hdmi.fb()
            # geometry always draws in plain WHITE, selected or not --
            # confirmed on real hardware that swapping in SELECT_COLOR
            # here (even RED, otherwise proven to render fine
            # elsewhere) made the selected item vanish entirely rather
            # than highlight, and undoing then redoing (which both just
            # clear self.selected back to None) brought it straight
            # back. Whatever's actually wrong with that colour swap
            # isn't worth the risk of ever hiding real geometry again
            # -- selection now gets a separate, additive marker instead
            # (_draw_selection_marker)
            #
            # BOX is not "the wireframe" -- it stays visible regardless
            # of WIRE, which only toggles LINE/CIRCLE/ARC
            for bi, box in enumerate(self.boxes):
                if not self.layer_visible.get(box[2], True):
                    continue
                for p1, p2 in self._box_edges(box):
                    s1 = self._project(p1[0], p1[1], p1[2], scale, ox, oy)
                    s2 = self._project(p2[0], p2[1], p2[2], scale, ox, oy)
                    self._clipped_line(fb, s1[0], s1[1], s2[0], s2[1], WHITE)
            if self.wireframe_visible:
                for li, (p0, p1, layer) in enumerate(self.lines):
                    if not self.layer_visible.get(layer, True):
                        continue
                    s0 = self._project(p0[0], p0[1], p0[2], scale, ox, oy)
                    s1 = self._project(p1[0], p1[1], p1[2], scale, ox, oy)
                    self._clipped_line(fb, s0[0], s0[1], s1[0], s1[1], WHITE)
                for ci, (c, r, plane, layer) in enumerate(self.circles):
                    if not self.layer_visible.get(layer, True):
                        continue
                    self._draw_arc(fb, c, r, plane, 0, 360, scale, ox, oy, colour=WHITE)
                for ai, (c, r, plane, a0, a1, layer) in enumerate(self.arcs):
                    if not self.layer_visible.get(layer, True):
                        continue
                    self._draw_arc(fb, c, r, plane, a0, a1, scale, ox, oy, colour=WHITE)
                for pi, (points, plane, height, layer) in enumerate(self.polys):
                    if not self.layer_visible.get(layer, True):
                        continue
                    self._draw_poly(fb, points, plane, height, scale, ox, oy)
            self._draw_selection_marker(fb, scale, ox, oy)
            if self.grid and self.grid_visible:
                self._draw_grid_dots(fb, scale, ox, oy)
            if self.template_main:
                self._draw_template_wireframe(fb, scale, ox, oy, self.template_main)
            if self.template_local:
                self._draw_template_wireframe(fb, scale, ox, oy, self.template_local)
            if self.dialog == "circle_pick":
                self._draw_circle_snap_preview(fb, scale, ox, oy)

            self._draw_axes(g, fb, scale, ox, oy)
        except Exception as e:
            ulog("Model3DPage: scene draw error: " + type(e).__name__ + " " + str(e))

    def _center_point_of(self, kind, idx):
        # 3D point to mark for a given (kind, idx) -- a midpoint for
        # box/line, the centre itself for circle/arc
        try:
            if kind == "box":
                c0, c1 = self.boxes[idx][0], self.boxes[idx][1]
                return tuple((c0[i] + c1[i]) / 2.0 for i in range(3))
            if kind == "line":
                p0, p1 = self.lines[idx][0], self.lines[idx][1]
                return tuple((p0[i] + p1[i]) / 2.0 for i in range(3))
            if kind == "circle":
                return self.circles[idx][0]
            if kind == "arc":
                return self.arcs[idx][0]
            if kind == "poly":
                points = self.polys[idx][0]
                n = len(points)
                return tuple(sum(p[i] for p in points) / n for i in range(3))
        except IndexError:
            return None
        return None

    def _selected_center_point(self):
        if not self.selected:
            return None
        return self._center_point_of(self.selected[0], self.selected[1])

    def _selection_highlight_targets(self):
        # normally just whatever's selected, but if it's part of the
        # most recent extrude's base+generated group (see
        # on_confirm_extrude/_last_extrude), highlight the whole group
        # -- so clicking any one piece of an extrusion shows the whole
        # thing, not just that one line/arc/circle
        if not self.selected:
            return []
        if self._last_extrude:
            group = [(self._last_extrude["kind"], self._last_extrude["idx"])] + self._last_extrude["generated"]
            if self.selected in group:
                return group
        return [self.selected]

    def _draw_selection_marker(self, fb, scale, ox, oy):
        # additive-only feedback for SELECT -- a crosshair drawn ON TOP
        # of the (always-WHITE) selected geometry rather than replacing
        # its colour, so a marker that fails to render for whatever
        # reason still leaves the geometry itself visible
        for kind, idx in self._selection_highlight_targets():
            self._draw_one_selection_marker(fb, scale, ox, oy, kind, idx)

    def _draw_one_selection_marker(self, fb, scale, ox, oy, kind, idx):
        center = self._center_point_of(kind, idx)
        if center is None:
            return
        mx, my = self._project(center[0], center[1], center[2], scale, ox, oy)
        r = 8
        self._clipped_line(fb, mx - r, my, mx + r, my, self.SELECT_COLOR)
        self._clipped_line(fb, mx, my - r, mx, my + r, self.SELECT_COLOR)

    def _draw_circle_snap_preview(self, fb, scale, ox, oy):
        # live preview for CIRCLE's click-to-place centre step -- a
        # crosshair at wherever a click would land right now (grid-
        # snapped if SNAP TO GRID is on), so you can see the target
        # before committing. Uses the last live-polled mouse position
        # (see _poll_live_mouse); does nothing if the mouse hasn't been
        # seen yet or is currently outside the canvas.
        if self._last_live_mouse_xy is None:
            return
        x, y = self._last_live_mouse_xy
        if not self._in_canvas(x, y):
            return
        try:
            plane, point = self._plane_point_at(x, y)
        except Exception:
            return
        mx, my = self._project(point[0], point[1], point[2], scale, ox, oy)
        r = 6
        self._clipped_line(fb, mx - r, my, mx + r, my, self.CIRCLE_PREVIEW_COLOR)
        self._clipped_line(fb, mx, my - r, mx, my + r, self.CIRCLE_PREVIEW_COLOR)

    def _draw_grid_dots(self, fb, scale, ox, oy):
        # a dot at every grid intersection in its plane. Grey, not
        # white, so it reads as background reference rather than part
        # of the actual model. Spans 0 to extent_i/extent_j (not
        # -extent to +extent) in the plane's two axes -- independent
        # extents so a grid can exactly cover a non-square face --
        # matching every box/line/circle/arc's own 0-based convention.
        # `position` places the whole plane along its normal axis (e.g.
        # a "vertical" XZ grid's Y), so it can line up with an actual
        # wall instead of sitting at 0.
        plane, spacing, extent_i, extent_j, position = self.grid
        i, j = self.PLANE_AXES[plane]
        k = self._plane_normal_axis(plane)
        ni = int(extent_i / spacing)
        nj = int(extent_j / spacing)
        for gi in range(0, ni + 1):
            for gj in range(0, nj + 1):
                p = [0.0, 0.0, 0.0]
                p[i] = gi * spacing
                p[j] = gj * spacing
                p[k] = position
                sx, sy = self._project(p[0], p[1], p[2], scale, ox, oy)
                if self.CANVAS_X0 <= sx <= self.CANVAS_X1 and self.CANVAS_Y0 <= sy <= self.CANVAS_Y1:
                    ix, iy = int(sx), int(sy)
                    _fb_pixel(fb, ix, iy, self.GREY)
                    _fb_pixel(fb, ix + 1, iy, self.GREY)
                    _fb_pixel(fb, ix, iy + 1, self.GREY)
                    _fb_pixel(fb, ix + 1, iy + 1, self.GREY)

    def _draw_template_wireframe(self, fb, scale, ox, oy, cfg):
        # a reference cube through the origin -- unlike the per-file
        # GRID (0 to extent, matching the model's own convention), this
        # spans -size/2 to +size/2 in each axis so it's actually
        # centred on the origin, which is what makes "centre lines"
        # (the two lines through 0,0 on each shown plane) meaningful.
        size, spacing, template_scale, centerlines, show_xy, show_xz, show_yz = cfg
        eff_size = size * template_scale
        eff_spacing = spacing * template_scale
        if eff_spacing <= 0:
            return
        half = eff_size / 2.0
        show = {"XY": show_xy, "XZ": show_xz, "YZ": show_yz}
        for plane in ("XY", "XZ", "YZ"):
            if not show[plane]:
                continue
            i, j = self.PLANE_AXES[plane]
            k = self._plane_normal_axis(plane)
            n = int(eff_size / eff_spacing)
            for gi in range(0, n + 1):
                for gj in range(0, n + 1):
                    p = [0.0, 0.0, 0.0]
                    p[i] = -half + gi * eff_spacing
                    p[j] = -half + gj * eff_spacing
                    p[k] = 0.0
                    sx, sy = self._project(p[0], p[1], p[2], scale, ox, oy)
                    if self.CANVAS_X0 <= sx <= self.CANVAS_X1 and self.CANVAS_Y0 <= sy <= self.CANVAS_Y1:
                        ix, iy = int(sx), int(sy)
                        _fb_pixel(fb, ix, iy, self.GREY)
                        _fb_pixel(fb, ix + 1, iy, self.GREY)
                        _fb_pixel(fb, ix, iy + 1, self.GREY)
                        _fb_pixel(fb, ix + 1, iy + 1, self.GREY)
            if centerlines:
                p0 = [0.0, 0.0, 0.0]
                p0[i] = -half
                p1 = [0.0, 0.0, 0.0]
                p1[i] = half
                s0 = self._project(p0[0], p0[1], p0[2], scale, ox, oy)
                s1 = self._project(p1[0], p1[1], p1[2], scale, ox, oy)
                self._clipped_line(fb, s0[0], s0[1], s1[0], s1[1], self.GREY)
                p2 = [0.0, 0.0, 0.0]
                p2[j] = -half
                p3 = [0.0, 0.0, 0.0]
                p3[j] = half
                s2 = self._project(p2[0], p2[1], p2[2], scale, ox, oy)
                s3 = self._project(p3[0], p3[1], p3[2], scale, ox, oy)
                self._clipped_line(fb, s2[0], s2[1], s3[0], s3[1], self.GREY)

    def _draw_arc(self, fb, center, radius, plane, a0, a1, scale, ox, oy, segments=32, colour=WHITE):
        # approximates a circle (a0=0, a1=360) or arc as a polyline of
        # short chords -- fewer chords for a short arc, always at
        # least 3 so nothing degenerates to a single dot
        sweep = a1 - a0
        n = max(3, int(round(segments * abs(sweep) / 360.0)))
        prev = None
        for i in range(n + 1):
            angle = a0 + sweep * i / n
            p3d = self._circle_point(center, radius, plane, angle)
            s = self._project(p3d[0], p3d[1], p3d[2], scale, ox, oy)
            if prev is not None:
                self._clipped_line(fb, prev[0], prev[1], s[0], s[1], colour)
            prev = s

    def _draw_poly(self, fb, points, plane, height, scale, ox, oy, colour=WHITE):
        # closed n-point outline (last point implicitly back to the
        # first); once EXTRUDEd (height > 0) also draws the raised top
        # outline plus verticals at each point -- same wireframe
        # language as CIRCLE/ARC's "swept into a cylinder" look, even
        # though a POLY solidifies into a real capped mesh in the STL
        # export rather than just hollow struts (see _poly_solid_triangles)
        n = len(points)
        projected = [self._project(p[0], p[1], p[2], scale, ox, oy) for p in points]
        for k in range(n):
            s0, s1 = projected[k], projected[(k + 1) % n]
            self._clipped_line(fb, s0[0], s0[1], s1[0], s1[1], colour)
        if height:
            axis = self._plane_normal_axis(plane)
            top_points = []
            for p in points:
                q = list(p)
                q[axis] += height
                top_points.append(tuple(q))
            projected_top = [self._project(p[0], p[1], p[2], scale, ox, oy) for p in top_points]
            for k in range(n):
                s0, s1 = projected_top[k], projected_top[(k + 1) % n]
                self._clipped_line(fb, s0[0], s0[1], s1[0], s1[1], colour)
            for k in range(n):
                s0, s1 = projected[k], projected_top[k]
                self._clipped_line(fb, s0[0], s0[1], s1[0], s1[1], colour)

    def _draw_axes(self, g, fb, scale, ox, oy):
        # X/Y/Z reference arrows, one colour each. When the wireframe
        # is showing, each starts past wherever the model already
        # reaches along that axis (not at literal (0,0,0)) so it
        # doesn't trace back over -- and cancel out -- a wireframe edge
        # running the same direction. With WIRE off there's no edge to
        # avoid, so they run the full length from the origin instead --
        # otherwise, with the model hidden, all that's left on screen is
        # a short sliver near the tip (or nothing at all, if that
        # sliver falls outside the canvas).
        #
        # the axis/origin labels are real g.caption() widgets (not raw
        # framebuffer pixels), so calling this repeatedly without
        # removing the previous batch first would pile up stale
        # duplicates -- matters now that _draw_scene (which calls this)
        # can be invoked directly on every live mouse-move tick, not
        # just from a full build()
        for w in self._axis_label_widgets:
            try:
                g.remove(w)
            except Exception:
                pass
        self._axis_label_widgets = []

        length = self._axis_length()
        wing = length * 0.15
        axis_index = {"X": 0, "Y": 1, "Z": 2}
        for axis, d in self.AXIS_DIRS.items():
            perp = self.AXIS_PERP[axis]
            colour = self.AXIS_COLORS[axis]
            start_at = self._axis_extent(axis_index[axis]) if self.wireframe_visible else 0.0
            start3d = (d[0] * start_at, d[1] * start_at, d[2] * start_at)
            tip3d = (d[0] * length, d[1] * length, d[2] * length)
            start = self._project(start3d[0], start3d[1], start3d[2], scale, ox, oy)
            tip = self._project(tip3d[0], tip3d[1], tip3d[2], scale, ox, oy)
            self._clipped_line(fb, start[0], start[1], tip[0], tip[1], colour)

            w1 = tuple(tip3d[i] - wing * d[i] + wing * 0.5 * perp[i] for i in range(3))
            w2 = tuple(tip3d[i] - wing * d[i] - wing * 0.5 * perp[i] for i in range(3))
            w1s = self._project(w1[0], w1[1], w1[2], scale, ox, oy)
            w2s = self._project(w2[0], w2[1], w2[2], scale, ox, oy)
            self._clipped_line(fb, tip[0], tip[1], w1s[0], w1s[1], colour)
            self._clipped_line(fb, tip[0], tip[1], w2s[0], w2s[1], colour)

            if self.CANVAS_X0 <= tip[0] <= self.CANVAS_X1 and self.CANVAS_Y0 <= tip[1] <= self.CANVAS_Y1:
                w = g.caption(int(tip[0]) + 6, int(tip[1]) - 8, axis, fg=colour, bg=self.BLACK, font=1)
                self._axis_label_widgets.append(w)

        origin = self._project(0, 0, 0, scale, ox, oy)
        w = g.caption(int(origin[0]) + 6, int(origin[1]) + 4, "0,0", fg=WHITE, bg=self.BLACK, font=1)
        self._axis_label_widgets.append(w)

    # --- modal dialogs --------------------------------------------------

    def _redraw(self):
        try:
            self.g.stop()
        except Exception:
            pass
        g = pcgui.GUI()
        self.g = g
        g.start()
        self.build(g)

    def _build_saveas_dialog(self, g):
        h = 280
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "SAVE AS", fg=WHITE, font=2)
        g.caption(self.DLG_X + 20, y0 + 40, "Name:", fg=WHITE, bg=self.BLACK, font=1)
        self.saveas_box = g.textbox(self.DLG_X + 20, y0 + 58, self.DLG_W - 40, 26,
                                     self.model_name, font=1)

        # EXPORT STL below reuses this same name field -- solidifies
        # LINE/CIRCLE/ARC edges into struts of this thickness (BOX
        # elements are already solid, unaffected). See the STL export
        # module comment near write_stl_file for what this can't do
        # (it's not a slicer -- load the .stl into one for G-code).
        g.caption(self.DLG_X + 20, y0 + 100, "STL strut thickness (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.stl_thickness_box = g.textbox(self.DLG_X + 20, y0 + 118, self.DLG_W - 40, 26,
                                            str(self.stl_strut_thickness), font=1)

        g.button(self.DLG_X + 20, y0 + h - 110, 120, 40, "SAVE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_saveas)
        g.button(self.DLG_X + 180, y0 + h - 110, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)
        g.button(self.DLG_X + 20, y0 + h - 60, self.DLG_W - 40, 40, "EXPORT STL", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_export_stl)

    def _build_line_choice_dialog(self, g):
        h = 180
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "LINE", fg=WHITE, font=2)
        g.caption(self.DLG_X + self.DLG_W // 2, y0 + 40, "How do you want to place the points?",
                  fg=WHITE, bg=self.BLACK, font=1, just="CT")
        g.button(self.DLG_X + 20, y0 + 70, 120, 44, "CLICK ON GRID", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_line_choice_click)
        g.button(self.DLG_X + 180, y0 + 70, 120, 44, "TYPE VALUES", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_line_choice_type)
        g.button(self.DLG_X + 100, y0 + 126, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_box_choice_dialog(self, g):
        h = 180
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "BOX", fg=WHITE, font=2)
        g.caption(self.DLG_X + self.DLG_W // 2, y0 + 40, "How do you want to place the corners?",
                  fg=WHITE, bg=self.BLACK, font=1, just="CT")
        g.button(self.DLG_X + 20, y0 + 70, 120, 44, "CLICK ON GRID", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_box_choice_click)
        g.button(self.DLG_X + 180, y0 + 70, 120, 44, "TYPE VALUES", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_box_choice_type)
        g.button(self.DLG_X + 100, y0 + 126, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _grid_snap_title_suffix(self):
        # every typed X/Y/Z/radius/angle value across every dialog
        # snaps to this once a GRID is set (see _snap_to_grid) -- shown
        # in each dialog's own title bar since there's no spare row for
        # a separate caption in most of them
        if not self.grid:
            return " (no grid snap)"
        return " (snap: %gmm)" % self.grid[1]

    def _build_line_dialog(self, g):
        # two-step: START POINT then END POINT, using the same three
        # boxes -- they come up blank each step
        h = 240
        y0 = (480 - h) // 2
        title = "LINE -- START POINT" if self.line_stage == "start" else "LINE -- END POINT"
        title += self._grid_snap_title_suffix()
        g.frame(self.DLG_X, y0, self.DLG_W, h, title, fg=WHITE, font=2)

        labels = ("X (mm):", "Y (mm):", "Z (mm):")
        boxes = []
        for i, label in enumerate(labels):
            ly = y0 + 40 + i * 44
            g.caption(self.DLG_X + 20, ly + 6, label, fg=WHITE, bg=self.BLACK, font=1)
            boxes.append(g.textbox(self.DLG_X + 130, ly, 100, 26, "", font=1))
        self.line_x_box, self.line_y_box, self.line_z_box = boxes

        if self.line_stage == "start":
            g.button(self.DLG_X + 20, y0 + 180, 120, 40, "NEXT", fg=WHITE, bg=BTN, font=2,
                     callback=self.on_line_next)
        else:
            g.button(self.DLG_X + 20, y0 + 180, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                     callback=self.on_line_create)
        g.button(self.DLG_X + 180, y0 + 180, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_box_dialog(self, g):
        # two-step: CORNER 1 then CORNER 2 -- any two opposite corners,
        # not necessarily min/max order (on_box_create sorts that out)
        h = 240
        y0 = (480 - h) // 2
        title = "BOX -- CORNER 1" if self.box_stage == "start" else "BOX -- CORNER 2"
        title += self._grid_snap_title_suffix()
        g.frame(self.DLG_X, y0, self.DLG_W, h, title, fg=WHITE, font=2)

        labels = ("X (mm):", "Y (mm):", "Z (mm):")
        boxes = []
        for i, label in enumerate(labels):
            ly = y0 + 40 + i * 44
            g.caption(self.DLG_X + 20, ly + 6, label, fg=WHITE, bg=self.BLACK, font=1)
            boxes.append(g.textbox(self.DLG_X + 130, ly, 100, 26, "", font=1))
        self.box_x_box, self.box_y_box, self.box_z_box = boxes

        if self.box_stage == "start":
            g.button(self.DLG_X + 20, y0 + 180, 120, 40, "NEXT", fg=WHITE, bg=BTN, font=2,
                     callback=self.on_box_next)
        else:
            g.button(self.DLG_X + 20, y0 + 180, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                     callback=self.on_box_create)
        g.button(self.DLG_X + 180, y0 + 180, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_circle_dialog(self, g):
        # radius (+ plane, + snap) only -- the centre is placed by
        # clicking in VIEW afterward (see on_confirm_circle/circle_pick)
        # rather than typed, with a live snap-preview marker following
        # the mouse (_draw_circle_snap_preview)
        h = 280
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "CIRCLE" + self._grid_snap_title_suffix(), fg=WHITE, font=2)

        if self._circle_radius_pending is not None:
            radius_str = self._circle_radius_pending
            self._circle_radius_pending = None
        else:
            radius_str = ""

        ly = y0 + 40
        g.caption(self.DLG_X + 20, ly + 6, "Radius:", fg=WHITE, bg=self.BLACK, font=1)
        self.circle_r_box = g.textbox(self.DLG_X + 160, ly, 100, 26, radius_str, font=1)

        ly += 44
        g.caption(self.DLG_X + 20, ly + 6, "Plane:", fg=WHITE, bg=self.BLACK, font=1)
        g.button(self.DLG_X + 160, ly, 100, 26, self.circle_plane, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_cycle_circle_plane)

        ly += 44
        snap_label = "SNAP TO GRID: ON" if self.snap_enabled else "SNAP TO GRID: OFF"
        g.button(self.DLG_X + 20, ly, self.DLG_W - 40, 32, snap_label, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_toggle_circle_snap)

        g.button(self.DLG_X + 20, y0 + h - 60, 120, 40, "NEXT", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_circle)
        g.button(self.DLG_X + 180, y0 + h - 60, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_arc_dialog(self, g):
        h = 360
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "ARC" + self._grid_snap_title_suffix(), fg=WHITE, font=2)

        labels = ("Center X:", "Center Y:", "Center Z:", "Radius:", "Start (deg):", "End (deg):")
        boxes = []
        for i, label in enumerate(labels):
            ly = y0 + 36 + i * 38
            g.caption(self.DLG_X + 20, ly + 6, label, fg=WHITE, bg=self.BLACK, font=1)
            boxes.append(g.textbox(self.DLG_X + 130, ly, 100, 24, "", font=1))
        (self.arc_cx_box, self.arc_cy_box, self.arc_cz_box, self.arc_r_box,
         self.arc_start_box, self.arc_end_box) = boxes

        ly = y0 + 36 + 6 * 38
        g.caption(self.DLG_X + 20, ly + 6, "Plane:", fg=WHITE, bg=self.BLACK, font=1)
        g.button(self.DLG_X + 130, ly, 100, 24, self.arc_plane, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_cycle_arc_plane)

        g.button(self.DLG_X + 20, y0 + h - 50, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_arc)
        g.button(self.DLG_X + 180, y0 + h - 50, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    MULTILINE_MAX_POINTS = 30

    def _build_multiline_dialog(self, g):
        h = 200
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "MULTI LINE" + self._grid_snap_title_suffix(), fg=WHITE, font=2)

        g.caption(self.DLG_X + 20, y0 + 50, "Number of points (3-%d):" % self.MULTILINE_MAX_POINTS,
                  fg=WHITE, bg=self.BLACK, font=1)
        self.multiline_count_box = g.textbox(self.DLG_X + 20, y0 + 70, 100, 26, "5", font=1)
        g.caption(self.DLG_X + 20, y0 + 106,
                  "Click each point in the VIEW panel in order --", fg=WHITE, bg=self.BLACK, font=1)
        g.caption(self.DLG_X + 20, y0 + 124,
                  "the last one connects back to the first.", fg=WHITE, bg=self.BLACK, font=1)

        g.button(self.DLG_X + 20, y0 + h - 50, 120, 40, "START", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_multiline_count)
        g.button(self.DLG_X + 180, y0 + h - 50, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_radius_dialog(self, g):
        h = 180
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "RADIUS", fg=WHITE, font=2)

        g.caption(self.DLG_X + 20, y0 + 50, "Corner radius (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.radius_amount_box = g.textbox(self.DLG_X + 20, y0 + 70, 100, 26, "5", font=1)
        if self._radius_dialog_message:
            g.caption(self.DLG_X + self.DLG_W // 2, y0 + 106, self._radius_dialog_message,
                      fg=RED, bg=self.BLACK, font=1, just="CT")

        g.button(self.DLG_X + 20, y0 + h - 50, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_radius)
        g.button(self.DLG_X + 180, y0 + h - 50, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_centerline_dialog(self, g):
        h = 200
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "CTR LINE", fg=WHITE, font=2)

        ly = y0 + 40
        g.caption(self.DLG_X + 20, ly + 6, "Axis:", fg=WHITE, bg=self.BLACK, font=1)
        g.button(self.DLG_X + 160, ly, 100, 26, self.centerline_axis, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_cycle_centerline_axis)

        ly += 44
        g.caption(self.DLG_X + 20, ly + 6, "Length (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.centerline_len_box = g.textbox(self.DLG_X + 160, ly, 100, 26, "100", font=1)

        g.button(self.DLG_X + 20, y0 + h - 60, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_centerline)
        g.button(self.DLG_X + 180, y0 + h - 60, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_grid_dialog(self, g):
        h = 348
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "GRID", fg=WHITE, font=2)

        # pre-fill from the current grid (if any) so re-opening this
        # dialog to tweak an existing grid doesn't mean retyping every
        # field from scratch
        if self.grid:
            _, cur_spacing, cur_extent_i, cur_extent_j, cur_position = self.grid
        else:
            cur_spacing, cur_extent_i, cur_extent_j, cur_position = 10, 100, 100, 0

        # independent per-axis extents, so a grid can exactly cover a
        # non-square face instead of being forced into a square region
        axis_i, axis_j = self.PLANE_AXES[self.grid_plane]
        axis_i_name = self.AXIS_NAMES[axis_i]
        axis_j_name = self.AXIS_NAMES[axis_j]

        ly = y0 + 40
        g.caption(self.DLG_X + 20, ly + 6, "Spacing (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.grid_spacing_box = g.textbox(self.DLG_X + 160, ly, 100, 26, str(cur_spacing), font=1)

        ly += 44
        g.caption(self.DLG_X + 20, ly + 6, "Extent " + axis_i_name + " (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.grid_extent_i_box = g.textbox(self.DLG_X + 160, ly, 100, 26, str(cur_extent_i), font=1)

        ly += 44
        g.caption(self.DLG_X + 20, ly + 6, "Extent " + axis_j_name + " (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.grid_extent_j_box = g.textbox(self.DLG_X + 160, ly, 100, 26, str(cur_extent_j), font=1)

        ly += 44
        g.caption(self.DLG_X + 20, ly + 6, "Plane:", fg=WHITE, bg=self.BLACK, font=1)
        g.button(self.DLG_X + 160, ly, 100, 26, self.grid_plane, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_cycle_grid_plane)

        ly += 44
        # where the grid sits along its plane's normal axis -- e.g. for
        # an XZ ("vertical") grid, this is its Y position, so it can
        # line up with an actual wall instead of always sitting at 0
        axis_name = self.AXIS_NAMES[self._plane_normal_axis(self.grid_plane)]
        g.caption(self.DLG_X + 20, ly + 6, axis_name + " position (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.grid_position_box = g.textbox(self.DLG_X + 160, ly, 100, 26, str(cur_position), font=1)

        g.button(self.DLG_X + 20, y0 + h - 60, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_grid)
        g.button(self.DLG_X + 180, y0 + h - 60, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_extrude_dialog(self, g):
        # only reachable with something already selected -- see
        # on_extrude_pressed
        h = 200
        y0 = (480 - h) // 2
        kind = self.selected[0] if self.selected else "?"
        g.frame(self.DLG_X, y0, self.DLG_W, h, "EXTRUDE " + kind.upper() + self._grid_snap_title_suffix(),
                fg=WHITE, font=2)

        if kind == "line":
            label = "Wall height (mm):"
        elif kind == "box":
            label = "Add to height (mm):"
        else:
            label = "Extrude height (mm):"
        g.caption(self.DLG_X + 20, y0 + 44, label, fg=WHITE, bg=self.BLACK, font=1)
        self.extrude_amount_box = g.textbox(self.DLG_X + 20, y0 + 66, 200, 26, "50", font=1)

        g.button(self.DLG_X + 20, y0 + h - 60, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_extrude)
        g.button(self.DLG_X + 180, y0 + h - 60, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _edit_fields(self):
        # (label, current value) pairs for whatever's selected -- the
        # shared source for both building the dialog's textboxes and
        # (via defaults, re-derived the same way in on_confirm_edit)
        # knowing what each typed value means once SAVE is pressed
        kind, idx = self.selected if self.selected else (None, -1)
        if kind == "line":
            p0, p1, layer = self.lines[idx]
            return [("P1 X:", p0[0]), ("P1 Y:", p0[1]), ("P1 Z:", p0[2]),
                    ("P2 X:", p1[0]), ("P2 Y:", p1[1]), ("P2 Z:", p1[2])]
        if kind == "box":
            c0, c1, layer = self.boxes[idx]
            return [("Corner1 X:", c0[0]), ("Corner1 Y:", c0[1]), ("Corner1 Z:", c0[2]),
                    ("Corner2 X:", c1[0]), ("Corner2 Y:", c1[1]), ("Corner2 Z:", c1[2])]
        if kind == "circle":
            c, r, plane, layer = self.circles[idx]
            return [("Center X:", c[0]), ("Center Y:", c[1]), ("Center Z:", c[2]), ("Radius:", r)]
        if kind == "arc":
            c, r, plane, a0, a1, layer = self.arcs[idx]
            return [("Center X:", c[0]), ("Center Y:", c[1]), ("Center Z:", c[2]),
                    ("Radius:", r), ("Start deg:", a0), ("End deg:", a1)]
        raise ValueError("unsupported kind")

    def _build_edit_dialog(self, g):
        # only reachable with something already selected -- see
        # on_edit_pressed. Fields come pre-filled with the item's
        # current values so a small mistake (like a bad SELECT/DELETE-
        # and-redraw, or a mis-snapped point) can be nudged straight
        # rather than deleted and re-entered from scratch.
        h = 360
        y0 = (480 - h) // 2
        kind = self.selected[0] if self.selected else "?"
        try:
            fields = self._edit_fields()
        except (IndexError, ValueError):
            g.frame(self.DLG_X, y0, self.DLG_W, h, "EDIT", fg=WHITE, font=2)
            g.caption(self.DLG_X + self.DLG_W // 2, y0 + 100, "Nothing valid selected",
                      fg=WHITE, bg=self.BLACK, font=1, just="CT")
            g.button(self.DLG_X + 100, y0 + h - 60, 120, 40, "CLOSE", fg=WHITE, bg=RED, font=2,
                     callback=self.on_cancel_dialog)
            return

        g.frame(self.DLG_X, y0, self.DLG_W, h, "EDIT " + kind.upper() + self._grid_snap_title_suffix(),
                fg=WHITE, font=2)
        self.edit_boxes = []
        for i, (label, default) in enumerate(fields):
            ly = y0 + 36 + i * 38
            g.caption(self.DLG_X + 20, ly + 6, label, fg=WHITE, bg=self.BLACK, font=1)
            self.edit_boxes.append(g.textbox(self.DLG_X + 130, ly, 100, 24, "%g" % default, font=1))

        g.button(self.DLG_X + 20, y0 + h - 96, self.DLG_W - 40, 36, "DELETE THIS ITEM",
                 fg=WHITE, bg=RED, font=1, callback=self.on_edit_delete)
        g.button(self.DLG_X + 20, y0 + h - 50, 120, 40, "SAVE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_edit)
        g.button(self.DLG_X + 180, y0 + h - 50, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_layers_dialog(self, g):
        h = 340
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "LAYERS", fg=WHITE, font=2)

        items = []
        for name in self.layers:
            mark = "* " if name == self.current_layer else "  "
            vis = "" if self.layer_visible.get(name, True) else "  (hidden)"
            items.append(mark + name + vis)
        if self._dialog_selected_layer not in self.layers:
            self._dialog_selected_layer = self.layers[0]
        start_index = self.layers.index(self._dialog_selected_layer)
        self.layers_list = g.listbox(self.DLG_X + 20, y0 + 40, self.DLG_W - 40, 120, items,
                                      start_index, font=1, callback=self.on_pick_layer)

        g.button(self.DLG_X + 20, y0 + 170, 130, 36, "SET ACTIVE", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_set_active_layer)
        g.button(self.DLG_X + 170, y0 + 170, 130, 36, "TOGGLE SHOW", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_toggle_layer_visible)
        g.button(self.DLG_X + 20, y0 + 212, self.DLG_W - 40, 36, "DELETE LAYER", fg=WHITE, bg=RED, font=1,
                 callback=self.on_delete_layer)
        if self._layers_dialog_message:
            g.caption(self.DLG_X + self.DLG_W // 2, y0 + 258, self._layers_dialog_message,
                       fg=WHITE, bg=self.BLACK, font=1, just="CT")
        g.button(self.DLG_X + 20, y0 + h - 60, 130, 40, "NEW LAYER", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_new_layer)
        g.button(self.DLG_X + 170, y0 + h - 60, 130, 40, "CLOSE", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_file_list_dialog(self, g, title, action_label, action_callback):
        # shared by OPEN and DELETE -- a listbox of everything under
        # MODELS_DIR plus one action button, or a plain "none yet"
        # message with just CLOSE if there's nothing saved
        h = 240
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, title, fg=WHITE, font=2)
        saved = list_saved_models()
        self._dialog_file_names = saved
        if not saved:
            g.caption(self.DLG_X + self.DLG_W // 2, y0 + 60, "No saved files yet",
                      fg=WHITE, bg=self.BLACK, font=1, just="CT")
            g.button(self.DLG_X + 100, y0 + 180, 120, 40, "CLOSE", fg=WHITE, bg=BTN, font=2,
                     callback=self.on_cancel_dialog)
            return
        self._dialog_selected_name = saved[0]
        self.dialog_list = g.listbox(self.DLG_X + 20, y0 + 40, self.DLG_W - 40, 120, saved, 0,
                                      font=1, callback=self.on_pick_dialog_file)
        g.button(self.DLG_X + 20, y0 + 180, 120, 40, action_label, fg=WHITE, bg=BTN, font=2,
                 callback=action_callback)
        g.button(self.DLG_X + 180, y0 + 180, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_open_dialog(self, g):
        self._build_file_list_dialog(g, "OPEN", "OPEN", self.on_confirm_open)

    def _build_delete_dialog(self, g):
        self._build_file_list_dialog(g, "DELETE", "DELETE", self.on_confirm_delete)

    def on_pick_dialog_file(self, c):
        i = c.value
        if 0 <= i < len(self._dialog_file_names):
            self._dialog_selected_name = self._dialog_file_names[i]

    # --- template wireframes -----------------------------------------

    def _build_template_dialog(self, g):
        h = 300
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "TEMPLATE", fg=WHITE, font=2)

        ly = y0 + 44
        main_label = self.template_main_name if self.template_main_name else "(none)"
        g.caption(self.DLG_X + 20, ly, "MAIN: " + main_label, fg=WHITE, bg=self.BLACK, font=1)
        ly += 24
        local_label = self.template_local_name if self.template_local_name else "(none)"
        g.caption(self.DLG_X + 20, ly, "LOCAL: " + local_label, fg=WHITE, bg=self.BLACK, font=1)

        ly += 36
        g.button(self.DLG_X + 20, ly, 130, 36, "PICK MAIN", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_open_template_pick_main)
        g.button(self.DLG_X + 170, ly, 130, 36, "PICK LOCAL", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_open_template_pick_local)

        ly += 46
        g.button(self.DLG_X + 20, ly, 130, 36, "NEW", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_open_template_new)
        g.button(self.DLG_X + 170, ly, 130, 36, "DELETE", fg=WHITE, bg=RED, font=1,
                 callback=self.on_open_template_delete)

        if self._template_dialog_message:
            g.caption(self.DLG_X + self.DLG_W // 2, ly + 46, self._template_dialog_message,
                       fg=WHITE, bg=self.BLACK, font=1, just="CT")

        g.button(self.DLG_X + 20, y0 + h - 50, self.DLG_W - 40, 36, "CLOSE", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_wireframe_list_dialog(self, g, title, action_label, action_callback):
        # mirrors _build_file_list_dialog, but lists saved templates
        # (list_saved_wireframes) instead of models, and CANCEL returns
        # to the TEMPLATE manager dialog rather than the main panel
        h = 240
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, title, fg=WHITE, font=2)
        saved = list_saved_wireframes()
        self._dialog_file_names = saved
        if not saved:
            g.caption(self.DLG_X + self.DLG_W // 2, y0 + 60, "No saved templates yet",
                      fg=WHITE, bg=self.BLACK, font=1, just="CT")
            g.button(self.DLG_X + 100, y0 + 180, 120, 40, "CLOSE", fg=WHITE, bg=BTN, font=2,
                     callback=self.on_cancel_to_template)
            return
        self._dialog_selected_name = saved[0]
        self.dialog_list = g.listbox(self.DLG_X + 20, y0 + 40, self.DLG_W - 40, 120, saved, 0,
                                      font=1, callback=self.on_pick_dialog_file)
        g.button(self.DLG_X + 20, y0 + 180, 120, 40, action_label, fg=WHITE, bg=BTN, font=2,
                 callback=action_callback)
        g.button(self.DLG_X + 180, y0 + 180, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_to_template)

    def _build_template_new_dialog(self, g):
        h = 400
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "NEW TEMPLATE", fg=WHITE, font=2)

        if self._template_new_pending:
            name_str, size_str, spacing_str, scale_str = self._template_new_pending
            self._template_new_pending = None
        else:
            name_str, size_str, spacing_str, scale_str = "", "1000", "100", "1"

        ly = y0 + 36
        g.caption(self.DLG_X + 20, ly + 6, "Name:", fg=WHITE, bg=self.BLACK, font=1)
        self.template_new_name_box = g.textbox(self.DLG_X + 130, ly, 160, 26, name_str, font=1)

        ly += 38
        g.caption(self.DLG_X + 20, ly + 6, "Size (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.template_new_size_box = g.textbox(self.DLG_X + 130, ly, 100, 26, size_str, font=1)

        ly += 38
        g.caption(self.DLG_X + 20, ly + 6, "Spacing (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.template_new_spacing_box = g.textbox(self.DLG_X + 130, ly, 100, 26, spacing_str, font=1)

        ly += 38
        g.caption(self.DLG_X + 20, ly + 6, "Scale factor:", fg=WHITE, bg=self.BLACK, font=1)
        self.template_new_scale_box = g.textbox(self.DLG_X + 130, ly, 100, 26, scale_str, font=1)

        ly += 44
        centerlines_label = "CTR LINES: ON" if self._template_new_centerlines else "CTR LINES: OFF"
        g.button(self.DLG_X + 20, ly, 140, 32, centerlines_label, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_toggle_new_centerlines)

        ly += 40
        xy_label = "XY: ON" if self._template_new_xy else "XY: OFF"
        g.button(self.DLG_X + 20, ly, 90, 32, xy_label, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_toggle_new_xy)
        xz_label = "XZ: ON" if self._template_new_xz else "XZ: OFF"
        g.button(self.DLG_X + 115, ly, 90, 32, xz_label, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_toggle_new_xz)
        yz_label = "YZ: ON" if self._template_new_yz else "YZ: OFF"
        g.button(self.DLG_X + 210, ly, 90, 32, yz_label, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_toggle_new_yz)

        if self._template_dialog_message:
            g.caption(self.DLG_X + self.DLG_W // 2, ly + 38, self._template_dialog_message,
                       fg=WHITE, bg=self.BLACK, font=1, just="CT")

        g.button(self.DLG_X + 20, y0 + h - 50, 120, 40, "SAVE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_template_new)
        g.button(self.DLG_X + 180, y0 + h - 50, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_to_template)

    def on_cancel_to_template(self, b):
        self.dialog = "template"
        self._template_dialog_message = ""
        self._redraw()

    def on_open_template_pick_main(self, b):
        self.dialog = "template_pick_main"
        self._redraw()

    def on_open_template_pick_local(self, b):
        self.dialog = "template_pick_local"
        self._redraw()

    def on_open_template_delete(self, b):
        self.dialog = "template_delete"
        self._redraw()

    def on_open_template_new(self, b):
        self._template_new_pending = None
        self._template_new_centerlines = True
        self._template_new_xy = True
        self._template_new_xz = True
        self._template_new_yz = True
        self._template_dialog_message = ""
        self.dialog = "template_new"
        self._redraw()

    def on_confirm_pick_main(self, b):
        name = getattr(self, "_dialog_selected_name", None)
        self.dialog = "template"
        if not name:
            self._redraw()
            return
        self.template_main_name = name
        self.template_main = self._safe_load_wireframe(name)
        save_template_active(self.template_main_name, self.template_local_name)
        self._redraw()

    def on_confirm_pick_local(self, b):
        name = getattr(self, "_dialog_selected_name", None)
        self.dialog = "template"
        if not name:
            self._redraw()
            return
        self.template_local_name = name
        self.template_local = self._safe_load_wireframe(name)
        save_template_active(self.template_main_name, self.template_local_name)
        self._redraw()

    def on_confirm_delete_template(self, b):
        name = getattr(self, "_dialog_selected_name", None)
        self.dialog = "template"
        if not name:
            self._redraw()
            return
        delete_wireframe_file(name)
        # if the deleted template was active in either slot, clear that
        # slot too rather than leaving a dangling name pointing nowhere
        if self.template_main_name == name:
            self.template_main_name = None
            self.template_main = None
        if self.template_local_name == name:
            self.template_local_name = None
            self.template_local = None
        save_template_active(self.template_main_name, self.template_local_name)
        self._template_dialog_message = "Deleted " + name
        self._redraw()

    def on_toggle_new_centerlines(self, b):
        self._stash_template_new_fields()
        self._template_new_centerlines = not self._template_new_centerlines
        self._redraw_dialog_in_place()

    def on_toggle_new_xy(self, b):
        self._stash_template_new_fields()
        self._template_new_xy = not self._template_new_xy
        self._redraw_dialog_in_place()

    def on_toggle_new_xz(self, b):
        self._stash_template_new_fields()
        self._template_new_xz = not self._template_new_xz
        self._redraw_dialog_in_place()

    def on_toggle_new_yz(self, b):
        self._stash_template_new_fields()
        self._template_new_yz = not self._template_new_yz
        self._redraw_dialog_in_place()

    def _stash_template_new_fields(self):
        # preserves whatever's currently typed across the redraw a
        # toggle button triggers -- same problem/fix as GRID's own
        # plane-cycle button (see on_cycle_grid_plane)
        self._template_new_pending = (
            self.template_new_name_box.value, self.template_new_size_box.value,
            self.template_new_spacing_box.value, self.template_new_scale_box.value)

    def on_confirm_template_new(self, b):
        name = self.template_new_name_box.value.strip()
        if not name:
            self._template_dialog_message = "Name can't be empty"
            self._redraw_dialog_in_place()
            return

        def parse(box, fallback):
            try:
                v = float(box.value)
                return v if v > 0 else fallback
            except (ValueError, TypeError):
                return fallback
        size = parse(self.template_new_size_box, 1000.0)
        spacing = parse(self.template_new_spacing_box, 100.0)
        scale = parse(self.template_new_scale_box, 1.0)
        # spacing/size scale together, so the dot-count check only
        # needs the unscaled ratio -- scale can't push it over the cap
        n = int(size / spacing)
        dot_count = (n + 1) ** 2
        if n < 1:
            self._template_dialog_message = "size must be at least as large as spacing"
            self._redraw_dialog_in_place()
            return
        if dot_count > self.GRID_MAX_DOTS:
            self._template_dialog_message = "%d points is too many (max %d)" % (dot_count, self.GRID_MAX_DOTS)
            self._redraw_dialog_in_place()
            return
        cfg = (size, spacing, scale, self._template_new_centerlines,
               self._template_new_xy, self._template_new_xz, self._template_new_yz)
        save_wireframe_file(name, cfg)
        self.dialog = "template"
        self._template_dialog_message = "Saved " + name
        self._redraw()

    def on_new_file(self):
        self._push_undo()
        # NEW FILE starts completely fresh, including layers -- no
        # starting geometry, just an empty canvas
        self.boxes = []
        self.lines = []
        self.circles = []
        self.arcs = []
        self.polys = []
        self.grid = None
        self.layers = ["Layer1"]
        self.current_layer = "Layer1"
        self.layer_visible = {"Layer1": True}
        self.selected = None
        self._last_extrude = None
        self.dialog = None
        self._redraw()
        self.status_box.value = "NEW FILE: blank canvas"

    def on_confirm_saveas(self, b):
        name = (self.saveas_box.value or "").strip()
        self.dialog = None
        self._redraw()
        if not name:
            self.status_box.value = "SAVE AS cancelled -- no name entered"
            return
        self.model_name = name
        try:
            path = save_model_file(name, self.boxes, self.lines, self.circles, self.arcs, self.polys,
                                    self.grid, self.layers, self.layer_visible)
            self.status_box.value = "Saved to " + path
        except Exception as e:
            self.status_box.value = "SAVE AS failed: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage SAVE AS error: " + type(e).__name__ + " " + str(e))

    def _model_to_stl_triangles(self, strut_half_width):
        # only what's actually modelled, and only from visible layers
        # (matching the on-screen view) -- never GRID or the template
        # wireframes, both explicitly not part of the real model
        triangles = []
        for c0, c1, layer in self.boxes:
            if not self.layer_visible.get(layer, True):
                continue
            triangles.extend(_box_triangles(c0, c1))
        for p0, p1, layer in self.lines:
            if not self.layer_visible.get(layer, True):
                continue
            triangles.extend(_strut_triangles(p0, p1, strut_half_width))
        for center, radius, plane, layer in self.circles:
            if not self.layer_visible.get(layer, True):
                continue
            segments = 32
            pts = [self._circle_point(center, radius, plane, 360.0 * i / segments) for i in range(segments)]
            for i in range(segments):
                triangles.extend(_strut_triangles(pts[i], pts[(i + 1) % segments], strut_half_width))
        for center, radius, plane, a0, a1, layer in self.arcs:
            if not self.layer_visible.get(layer, True):
                continue
            sweep = a1 - a0
            segments = max(3, int(round(32 * abs(sweep) / 360.0)))
            pts = [self._circle_point(center, radius, plane, a0 + sweep * i / segments)
                   for i in range(segments + 1)]
            for i in range(segments):
                triangles.extend(_strut_triangles(pts[i], pts[i + 1], strut_half_width))
        for points, plane, height, layer in self.polys:
            if not self.layer_visible.get(layer, True):
                continue
            if not height:
                # not yet EXTRUDEd -- a flat outline has no volume to
                # export (unlike LINE/CIRCLE/ARC, a POLY deliberately
                # doesn't fall back to hollow struts here: the whole
                # point of MULTI LINE + EXTRUDE is a real solid, so an
                # un-extruded one just doesn't appear in the STL yet)
                continue
            i, j = self.PLANE_AXES[plane]
            axis = self._plane_normal_axis(plane)
            triangles.extend(_poly_solid_triangles(points, i, j, axis, height))
        return triangles

    def on_confirm_export_stl(self, b):
        name = (self.saveas_box.value or "").strip()
        try:
            thickness = float(self.stl_thickness_box.value)
            if thickness <= 0:
                thickness = 4.0
        except (ValueError, TypeError):
            thickness = 4.0
        self.stl_strut_thickness = thickness
        self.dialog = None
        self._redraw()
        if not name:
            self.status_box.value = "EXPORT STL cancelled -- no name entered"
            return
        try:
            triangles = self._model_to_stl_triangles(thickness / 2.0)
            if not triangles:
                self.status_box.value = "EXPORT STL: nothing visible to export"
                return
            path = save_stl_file(name, triangles)
            self.status_box.value = "Exported %d triangles to %s" % (len(triangles), name + ".stl")
        except Exception as e:
            self.status_box.value = "EXPORT STL failed: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage EXPORT STL error: " + type(e).__name__ + " " + str(e))

    def on_confirm_open(self, b):
        # load THEN redraw, not the other way round -- redrawing first
        # would rebuild the scene from the OLD model, before the load
        # below ever runs, so the file would load into memory but
        # never actually appear
        name = getattr(self, "_dialog_selected_name", None)
        self.dialog = None
        if not name:
            self._redraw()
            self.status_box.value = "OPEN: nothing selected"
            return
        try:
            boxes, lines, circles, arcs, polys, grid, layers, layer_visible = load_model_file(name)
            self._push_undo()
            self.boxes = boxes
            self.lines = lines
            self.circles = circles
            self.arcs = arcs
            self.polys = polys
            self.grid = grid
            self.layers = layers
            self.layer_visible = layer_visible
            self.current_layer = layers[0]
            self.selected = None
            self._last_extrude = None
            self.model_name = name
            self._redraw()
            self.status_box.value = "Opened " + name
        except Exception as e:
            self._redraw()
            self.status_box.value = "OPEN failed: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage OPEN error: " + type(e).__name__ + " " + str(e))

    def on_confirm_delete(self, b):
        name = getattr(self, "_dialog_selected_name", None)
        self.dialog = None
        self._redraw()
        if not name:
            self.status_box.value = "DELETE: nothing selected"
            return
        if delete_model_file(name):
            self.status_box.value = "Deleted " + name
        else:
            self.status_box.value = "DELETE failed for " + name

    def _read_line_point(self):
        def parse(box):
            try:
                v = float(box.value)
            except (ValueError, TypeError):
                v = 0.0
            return self._snap_to_grid(v)
        return (parse(self.line_x_box), parse(self.line_y_box), parse(self.line_z_box))

    def on_line_choice_click(self, b):
        self.line_stage = "start"
        self.dialog = "line_pick"
        self._redraw()

    def on_line_choice_type(self, b):
        self.line_stage = "start"
        self.dialog = "line"
        self._redraw()

    def on_box_choice_click(self, b):
        self.box_pick_start = None
        self.dialog = "box_pick"
        self._redraw()

    def on_confirm_multiline_count(self, b):
        try:
            n = int(float(self.multiline_count_box.value))
        except (ValueError, TypeError):
            n = 5
        n = max(3, min(self.MULTILINE_MAX_POINTS, n))
        self.multiline_target = n
        self.multiline_points = []
        self.dialog = "multiline_pick"
        self._redraw()

    def on_confirm_radius(self, b):
        try:
            radius = float(self.radius_amount_box.value)
        except (ValueError, TypeError):
            radius = 0.0
        idx_a, idx_b = self.radius_pick_a, self.radius_pick_b
        single_box = idx_a == idx_b
        try:
            box_a = self.boxes[idx_a]
            box_b = box_a if single_box else self.boxes[idx_b]
        except (IndexError, TypeError):
            self.dialog = None
            self.radius_pick_a = None
            self.radius_pick_b = None
            self._redraw()
            self.status_box.value = "RADIUS: one of those walls no longer exists"
            return
        try:
            if single_box:
                x_side, y_side = self.radius_corner_side
                new_a, pie_points, height = _box_corner_pie((box_a[0], box_a[1]), x_side, y_side, radius)
                new_b = None
            else:
                new_a, new_b, pie_points, height = _wall_radius_pie(
                    (box_a[0], box_a[1]), (box_b[0], box_b[1]), radius)
        except ValueError as e:
            self._radius_dialog_message = str(e)
            self._redraw()
            return
        self._push_undo()
        self.boxes[idx_a] = (new_a[0], new_a[1], box_a[2])
        if not single_box:
            self.boxes[idx_b] = (new_b[0], new_b[1], box_b[2])
        self.polys.append((pie_points, "XY", height, box_a[2]))
        self.radius_pick_a = None
        self.radius_pick_b = None
        self.radius_corner_side = None
        self._radius_dialog_message = ""
        self.dialog = None
        self.selected = None
        self._redraw()
        self.status_box.value = "RADIUS: corner rounded to %gmm" % radius

    def on_box_choice_type(self, b):
        self.box_stage = "start"
        self.dialog = "box"
        self._redraw()

    def on_line_next(self, b):
        self.line_start_point = self._read_line_point()
        self.line_stage = "end"
        self._redraw()

    def on_line_create(self, b):
        end_point = self._read_line_point()
        self._push_undo()
        self.lines.append((self.line_start_point, end_point, self.current_layer))
        self.dialog = None
        self.line_stage = "start"
        self._redraw()
        self.status_box.value = "LINE: %s to %s" % (self.line_start_point, end_point)

    def _read_box_point(self):
        def parse(box):
            try:
                v = float(box.value)
            except (ValueError, TypeError):
                v = 0.0
            return self._snap_to_grid(v)
        return (parse(self.box_x_box), parse(self.box_y_box), parse(self.box_z_box))

    def on_box_next(self, b):
        self.box_start_point = self._read_box_point()
        self.box_stage = "end"
        self._redraw()

    def on_box_create(self, b):
        p1 = self.box_start_point
        p2 = self._read_box_point()
        # sorted into (min corner, max corner) so it doesn't matter
        # which of the two opposite corners was entered first
        corner_min = (min(p1[0], p2[0]), min(p1[1], p2[1]), min(p1[2], p2[2]))
        corner_max = (max(p1[0], p2[0]), max(p1[1], p2[1]), max(p1[2], p2[2]))
        self._push_undo()
        self.boxes.append((corner_min, corner_max, self.current_layer))
        self.dialog = None
        self.box_stage = "start"
        self._redraw()
        self.status_box.value = "BOX: %s to %s" % (corner_min, corner_max)

    def on_cycle_circle_plane(self, b):
        self._circle_radius_pending = self.circle_r_box.value
        order = ("XY", "XZ", "YZ")
        self.circle_plane = order[(order.index(self.circle_plane) + 1) % 3]
        self._redraw()

    def on_toggle_circle_snap(self, b):
        self._circle_radius_pending = self.circle_r_box.value
        self.snap_enabled = not self.snap_enabled
        self._redraw()

    def on_confirm_circle(self, b):
        # only the radius is typed -- confirming this hands off to
        # circle_pick, where the centre is placed by clicking in VIEW
        # (with a live snap preview), not typed
        def parse(box, fallback):
            try:
                v = float(box.value)
            except (ValueError, TypeError):
                v = fallback
            return self._snap_to_grid(v)
        r = parse(self.circle_r_box, 20.0)
        if r <= 0:
            r = 20.0
        r = self._snap_length_to_grid(r)
        self._circle_pick_radius = r
        self.dialog = "circle_pick"
        self._redraw()

    def _circle_centerline_segments(self, center, radius, plane):
        # a technical-drawing-style center mark -- two short reference
        # lines through the circle's centre, along the plane's two
        # axes, extending a little past the circle's own edge so they
        # read as a crosshair rather than getting lost inside the
        # circle outline. Added as ordinary lines (own layer tag, own
        # SELECT/DELETE entry) rather than a special element kind.
        i, j = self.PLANE_AXES[plane]
        arm = radius * 1.3
        p0, p1 = list(center), list(center)
        p0[i] -= arm
        p1[i] += arm
        p2, p3 = list(center), list(center)
        p2[j] -= arm
        p3[j] += arm
        return ((tuple(p0), tuple(p1)), (tuple(p2), tuple(p3)))

    def on_cycle_arc_plane(self, b):
        order = ("XY", "XZ", "YZ")
        self.arc_plane = order[(order.index(self.arc_plane) + 1) % 3]
        self._redraw()

    def on_confirm_arc(self, b):
        def parse(box, fallback):
            try:
                v = float(box.value)
            except (ValueError, TypeError):
                v = fallback
            return self._snap_to_grid(v)
        cx = parse(self.arc_cx_box, 0.0)
        cy = parse(self.arc_cy_box, 0.0)
        cz = parse(self.arc_cz_box, 0.0)
        r = parse(self.arc_r_box, 20.0)
        if r <= 0:
            r = 20.0
        r = self._snap_length_to_grid(r)
        a0 = parse(self.arc_start_box, 0.0)
        a1 = parse(self.arc_end_box, 90.0)
        self._push_undo()
        self.arcs.append(((cx, cy, cz), r, self.arc_plane, a0, a1, self.current_layer))
        self.dialog = None
        self._redraw()
        self.status_box.value = "ARC: centre (%g,%g,%g) r=%g %s %g to %g deg" % (cx, cy, cz, r, self.arc_plane, a0, a1)

    def on_cycle_grid_plane(self, b):
        order = ("XY", "XZ", "YZ")
        self.grid_plane = order[(order.index(self.grid_plane) + 1) % 3]
        self._redraw()

    def on_cycle_centerline_axis(self, b):
        order = ("X", "Y", "Z")
        self.centerline_axis = order[(order.index(self.centerline_axis) + 1) % 3]
        self._redraw()

    def _snap_to_grid(self, value):
        # rounds any typed number (not a click position -- see
        # _snap_to_grid_point for that) to the nearest multiple of the
        # current GRID's spacing, if any -- applied to every numeric
        # field across every typed-entry dialog (BOX/LINE points,
        # CIRCLE/ARC centres and radius, ARC's angles, CTR LINE's
        # length), not just positions
        if not self.grid or not self.snap_enabled:
            return value
        spacing = self.grid[1]
        if spacing <= 0:
            return value
        return round(value / spacing) * spacing

    def _snap_length_to_grid(self, length):
        # like _snap_to_grid, but guarantees a positive result -- for
        # lengths/radii, which can't be zero or negative, so it falls
        # back to one full spacing unit rather than 0 if rounding would
        # otherwise collapse a short length to nothing
        snapped = self._snap_to_grid(length)
        return snapped if snapped > 0 else (self.grid[1] if self.grid else length)

    def on_confirm_centerline(self, b):
        try:
            length = float(self.centerline_len_box.value)
            if length <= 0:
                length = 100.0
        except (ValueError, TypeError):
            length = 100.0
        length = self._snap_length_to_grid(length)
        d = self.AXIS_DIRS[self.centerline_axis]
        half = length / 2.0
        p0 = (-half * d[0], -half * d[1], -half * d[2])
        p1 = (half * d[0], half * d[1], half * d[2])
        self._push_undo()
        self.lines.append((p0, p1, self.current_layer))
        self.dialog = None
        self._redraw()
        self.status_box.value = "CTR LINE: %s axis, %g mm" % (self.centerline_axis, length)

    def on_confirm_grid(self, b):
        def parse(box, fallback):
            try:
                v = float(box.value)
                return v if v > 0 else fallback
            except (ValueError, TypeError):
                return fallback
        spacing = parse(self.grid_spacing_box, 10.0)
        extent_i = parse(self.grid_extent_i_box, 100.0)
        extent_j = parse(self.grid_extent_j_box, 100.0)
        try:
            position = float(self.grid_position_box.value)
        except (ValueError, TypeError):
            position = 0.0
        if self.snap_enabled and spacing > 0:
            # snap to the spacing just typed in this dialog, not
            # self.grid's (old) spacing -- self.grid isn't updated
            # until below, so _snap_to_grid would use stale spacing
            position = round(position / spacing) * spacing
        ni = int(extent_i / spacing)
        nj = int(extent_j / spacing)
        self.dialog = None
        if ni < 1 or nj < 1:
            # either extent smaller than spacing -- collapses that axis
            # to a single dot at the origin
            self._redraw()
            self.status_box.value = "GRID: both extents must be at least as large as spacing"
            return
        dot_count = (ni + 1) * (nj + 1)
        if dot_count > self.GRID_MAX_DOTS:
            self._redraw()
            self.status_box.value = ("GRID: %d points is too many (max %d) -- "
                                      "use a bigger spacing or smaller extent" % (dot_count, self.GRID_MAX_DOTS))
            return
        self._push_undo()
        self.grid = (self.grid_plane, spacing, extent_i, extent_j, position)
        self._redraw()
        axis_name = self.AXIS_NAMES[self._plane_normal_axis(self.grid_plane)]
        self.status_box.value = "GRID: %s, %g mm spacing, %gx%g mm extent, %s=%g" % (
            self.grid_plane, spacing, extent_i, extent_j, axis_name, position)

    def on_open_layers(self, b):
        self._dialog_selected_layer = self.current_layer
        self._layers_dialog_message = ""
        self.dialog = "layers"
        self._redraw()

    def on_pick_layer(self, c):
        i = c.value
        if 0 <= i < len(self.layers):
            self._dialog_selected_layer = self.layers[i]
            self._layers_dialog_message = ""

    def on_set_active_layer(self, b):
        self.current_layer = self._dialog_selected_layer
        self._redraw_dialog_in_place()

    def on_toggle_layer_visible(self, b):
        name = self._dialog_selected_layer
        self.layer_visible[name] = not self.layer_visible.get(name, True)
        self._redraw_dialog_in_place()

    def on_new_layer(self, b):
        i = 2
        while ("Layer%d" % i) in self.layers:
            i += 1
        name = "Layer%d" % i
        self._push_undo()
        self.layers.append(name)
        self.layer_visible[name] = True
        self._dialog_selected_layer = name
        self._layers_dialog_message = ""
        self._redraw_dialog_in_place()

    def _layer_item_count(self, name):
        # how many boxes/lines/circles/arcs are tagged with this layer
        # -- used to block deleting a layer out from under real items
        # rather than silently orphaning their layer tag
        count = 0
        for box in self.boxes:
            if box[2] == name:
                count += 1
        for line in self.lines:
            if line[2] == name:
                count += 1
        for circle in self.circles:
            if circle[3] == name:
                count += 1
        for arc in self.arcs:
            if arc[5] == name:
                count += 1
        for poly in self.polys:
            if poly[3] == name:
                count += 1
        return count

    def on_delete_layer(self, b):
        name = self._dialog_selected_layer
        if len(self.layers) <= 1:
            self._layers_dialog_message = "Can't delete the only layer"
            self._redraw_dialog_in_place()
            return
        count = self._layer_item_count(name)
        if count > 0:
            self._layers_dialog_message = "%d item%s still on this layer" % (
                count, "" if count == 1 else "s")
            self._redraw_dialog_in_place()
            return
        self._push_undo()
        self.layers.remove(name)
        self.layer_visible.pop(name, None)
        if self.current_layer == name:
            self.current_layer = self.layers[0]
        self._dialog_selected_layer = self.current_layer
        self._layers_dialog_message = ""
        self._redraw_dialog_in_place()

    def _redraw_dialog_in_place(self):
        # LAYERS' own buttons stay on this dialog after acting (unlike
        # every other dialog's confirm, which closes back to the main
        # panel) -- SET ACTIVE/TOGGLE SHOW/NEW LAYER are all things
        # you'd plausibly do several of in a row
        self._redraw()

    def on_cancel_dialog(self, b):
        self.dialog = None
        self.line_stage = "start"
        self.box_stage = "start"
        self.box_pick_start = None
        self.radius_pick_a = None
        self.radius_pick_b = None
        self.radius_corner_side = None
        self._radius_dialog_message = ""
        self._redraw()

    def _make_command_handler(self, name):
        def handler(b):
            self.on_command(name)
        return handler

    def on_command(self, name):
        self.active_command = name
        if name == "NEW FILE":
            self.on_new_file()
            return
        elif name == "LINE":
            self.line_stage = "start"
        elif name == "BOX":
            self.box_stage = "start"
            self.box_pick_start = None
        elif name == "RADIUS":
            # a stale self.selected from an earlier SELECT would
            # otherwise keep drawing its marker throughout RADIUS's
            # whole (multi-click) pick sequence -- see _draw_selection_marker
            self.selected = None
            self.radius_pick_a = None
            self.radius_pick_b = None
            self.radius_corner_side = None
            self._radius_dialog_message = ""
        elif name == "DELETE" and self.selected is not None:
            # DELETE means "delete the selected item" whenever SELECT
            # has one highlighted -- only falls back to the saved-file
            # list below once nothing's currently selected
            self._delete_selected()
            return
        elif name == "GRID" and self.grid:
            # pre-fill the plane toggle from the actual current grid,
            # not whatever was last left over from a previous (possibly
            # cancelled) visit to this dialog
            self.grid_plane = self.grid[0]
        elif name == "TEMPLATE":
            self._template_dialog_message = ""
        target = self.COMMAND_DIALOG.get(name)
        if target is None:
            self._redraw()
            self.status_box.value = "Pressed: " + name
            ulog("Model3DPage: command pressed: " + name)
            return
        self.dialog = target
        self._redraw()

    def _delete_selected(self):
        kind, idx = self.selected
        collection = {"box": self.boxes, "line": self.lines,
                      "circle": self.circles, "arc": self.arcs, "poly": self.polys}[kind]
        self._push_undo()
        del collection[idx]
        self.selected = None
        self.dialog = None
        # any tracked "last extrude" indices could now point at the
        # wrong thing -- see on_confirm_extrude/_remove_generated
        self._last_extrude = None
        self._redraw()
        self.status_box.value = "DELETE: removed %s #%d (undoable)" % (kind.upper(), idx + 1)

    def _in_canvas(self, x, y):
        return self.CANVAS_X0 <= x <= self.CANVAS_X1 and self.CANVAS_Y0 <= y <= self.CANVAS_Y1

    def _screen_to_plane_point(self, sx, sy, plane):
        # inverts _project(), assuming the point actually lies on
        # `plane` -- a single 2D screen point can't otherwise be turned
        # back into a 3D one. Uses whatever scale/origin the VIEW panel
        # was last drawn with. The third axis is 0 by default, unless
        # the active GRID is on this same plane and has a non-zero
        # position, in which case the point lands on the grid instead
        # (matching what's actually drawn -- see _draw_grid_dots).
        #
        # Solved generically rather than with a per-plane formula, so
        # it keeps working at any azimuth/elevation: `plane`'s two
        # world-space basis vectors are themselves projected (giving
        # the 2x2 Jacobian from plane-space (a,b) to screen pixels),
        # then that's inverted to recover (a,b) for this click.
        scale = self._last_scale or 1.0
        ox, oy = self._last_origin
        normal_offset = 0.0
        if self.grid and self.grid[0] == plane:
            normal_offset = self.grid[4]  # (plane, spacing, extent_i, extent_j, position)
        offset_x = offset_y = 0.0
        if normal_offset:
            k = self._plane_normal_axis(plane)
            off_vec = [0.0, 0.0, 0.0]
            off_vec[k] = normal_offset
            offset_x, offset_y = self._raw_project(off_vec[0], off_vec[1], off_vec[2])
        rsx = (sx - ox) / scale - offset_x
        rsy = (sy - oy) / scale - offset_y
        u, v = self.PLANE_BASIS[plane]
        ux, uy = self._raw_project(u[0], u[1], u[2])
        vx, vy = self._raw_project(v[0], v[1], v[2])
        det = ux * vy - vx * uy
        if -1e-9 < det < 1e-9:
            # near edge-on view of this plane at the current rotation --
            # nudge off zero rather than divide by it; the result will
            # be a poor (likely large) estimate, but GRID snapping
            # clamps it back into range rather than blowing up
            det = 1e-9 if det >= 0 else -1e-9
        a = (rsx * vy - vx * rsy) / det
        b = (ux * rsy - rsx * uy) / det
        p = [0.0, 0.0, 0.0]
        for coeff, vec in ((a, u), (b, v)):
            for i in range(3):
                p[i] += coeff * vec[i]
        if normal_offset:
            p[self._plane_normal_axis(plane)] = normal_offset
        return (p[0], p[1], p[2])

    def _snap_to_grid_point(self, point):
        if not self.grid or not self.snap_enabled:
            return point
        plane, spacing, extent_i, extent_j, position = self.grid
        i, j = self.PLANE_AXES[plane]
        k = self._plane_normal_axis(plane)
        p = list(point)
        extents = {i: extent_i, j: extent_j}
        for idx in (i, j):
            v = round(p[idx] / spacing) * spacing
            p[idx] = max(0.0, min(extents[idx], v))
        p[k] = position
        return (p[0], p[1], p[2])

    def _point_to_segment_dist(self, px, py, x0, y0, x1, y1):
        # math.sqrt, not math.hypot -- confirmed on real hardware that
        # this board's MicroPython math module doesn't implement hypot
        dx, dy = x1 - x0, y1 - y0
        if dx == 0 and dy == 0:
            ex, ey = px - x0, py - y0
            return math.sqrt(ex * ex + ey * ey)
        t = ((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        cx, cy = x0 + t * dx, y0 + t * dy
        ex, ey = px - cx, py - cy
        return math.sqrt(ex * ex + ey * ey)

    def _nearest_box_corner(self, box, x, y, scale, ox, oy):
        # which of a box's 4 vertical (full-height) edges a click
        # landed nearest -- used by RADIUS's single-box corner pick,
        # same nearest-in-screen-space idea as _hit_test
        c0, c1 = box[0], box[1]
        corners = [(c0[0], c0[1]), (c0[0], c1[1]), (c1[0], c0[1]), (c1[0], c1[1])]
        best, best_dist = None, None
        for (cx, cy) in corners:
            p_bot = self._project(cx, cy, c0[2], scale, ox, oy)
            p_top = self._project(cx, cy, c1[2], scale, ox, oy)
            d = self._point_to_segment_dist(x, y, p_bot[0], p_bot[1], p_top[0], p_top[1])
            if best_dist is None or d < best_dist:
                best_dist, best = d, (cx, cy)
        x_side = "min" if best[0] == c0[0] else "max"
        y_side = "min" if best[1] == c0[1] else "max"
        return x_side, y_side

    def _arc_hit_dist(self, x, y, center, radius, plane, a0, a1, scale, ox, oy, segments=32):
        # same chord approximation _draw_arc uses -- distance from
        # (x,y) to the nearest chord, so hit-testing matches what's
        # actually drawn on screen
        sweep = a1 - a0
        n = max(3, int(round(segments * abs(sweep) / 360.0)))
        prev = None
        best = None
        for i in range(n + 1):
            angle = a0 + sweep * i / n
            p3d = self._circle_point(center, radius, plane, angle)
            s = self._project(p3d[0], p3d[1], p3d[2], scale, ox, oy)
            if prev is not None:
                d = self._point_to_segment_dist(x, y, prev[0], prev[1], s[0], s[1])
                if best is None or d < best:
                    best = d
            prev = s
        return best if best is not None else 1.0e9

    def _hit_test(self, x, y):
        # nearest element (by screen-space distance to its projected
        # outline) within SELECT_THRESHOLD px of the click, or None
        scale, (ox, oy) = self._last_scale, self._last_origin
        best_dist = None
        best = None

        for bi, box in enumerate(self.boxes):
            if not self.layer_visible.get(box[2], True):
                continue
            for p1, p2 in self._box_edges(box):
                s1 = self._project(p1[0], p1[1], p1[2], scale, ox, oy)
                s2 = self._project(p2[0], p2[1], p2[2], scale, ox, oy)
                d = self._point_to_segment_dist(x, y, s1[0], s1[1], s2[0], s2[1])
                if best_dist is None or d < best_dist:
                    best_dist, best = d, ("box", bi)

        for li, (p0, p1, layer) in enumerate(self.lines):
            if not self.layer_visible.get(layer, True):
                continue
            s0 = self._project(p0[0], p0[1], p0[2], scale, ox, oy)
            s1 = self._project(p1[0], p1[1], p1[2], scale, ox, oy)
            d = self._point_to_segment_dist(x, y, s0[0], s0[1], s1[0], s1[1])
            if best_dist is None or d < best_dist:
                best_dist, best = d, ("line", li)

        for ci, (c, r, plane, layer) in enumerate(self.circles):
            if not self.layer_visible.get(layer, True):
                continue
            d = self._arc_hit_dist(x, y, c, r, plane, 0, 360, scale, ox, oy)
            if best_dist is None or d < best_dist:
                best_dist, best = d, ("circle", ci)

        for ai, (c, r, plane, a0, a1, layer) in enumerate(self.arcs):
            if not self.layer_visible.get(layer, True):
                continue
            d = self._arc_hit_dist(x, y, c, r, plane, a0, a1, scale, ox, oy)
            if best_dist is None or d < best_dist:
                best_dist, best = d, ("arc", ai)

        for pi, (points, plane, height, layer) in enumerate(self.polys):
            if not self.layer_visible.get(layer, True):
                continue
            n = len(points)
            projected = [self._project(p[0], p[1], p[2], scale, ox, oy) for p in points]
            for k in range(n):
                s0, s1 = projected[k], projected[(k + 1) % n]
                d = self._point_to_segment_dist(x, y, s0[0], s0[1], s1[0], s1[1])
                if best_dist is None or d < best_dist:
                    best_dist, best = d, ("poly", pi)

        if best_dist is not None and best_dist <= self.SELECT_THRESHOLD:
            return best
        return None

    def _plane_point_at(self, x, y):
        # model-space position under the cursor, assuming it lies on
        # the active GRID's plane (or XY if there's no grid) and
        # snapped to that grid if one exists -- shared by the readout
        # and by actual point-picking (LINE's "CLICK ON GRID" mode)
        plane = self.grid[0] if self.grid else "XY"
        point = self._screen_to_plane_point(x, y, plane)
        point = self._snap_to_grid_point(point)
        return plane, point

    def _position_readout(self, x, y):
        if not self._in_canvas(x, y):
            return "X:--  Y:--  Z:--"
        plane, point = self._plane_point_at(x, y)
        # rounded to 1dp -- without an active grid to snap to, the raw
        # inverse-projected position is a long, jittery decimal
        return "X:%.1f  Y:%.1f  Z:%.1f" % (point[0], point[1], point[2])

    def on_touch(self, x, y):
        # g.on_touch(callback) fires with integer (x, y) screen
        # coordinates on any click/tap. Only registered while the main
        # panel (not a dialog) is showing -- see _build_main.
        self.touch_count += 1
        ulog("on_touch fired #%d at (%d,%d) dialog=%s" % (self.touch_count, x, y, self.dialog))
        if self.dialog == "line_pick":
            self._on_line_pick_touch(x, y)
            return
        if self.dialog == "select_pick":
            self._on_select_pick_touch(x, y)
            return
        if self.dialog == "box_pick":
            self._on_box_pick_touch(x, y)
            return
        if self.dialog == "circle_pick":
            self._on_circle_pick_touch(x, y)
            return
        if self.dialog == "multiline_pick":
            self._on_multiline_pick_touch(x, y)
            return
        if self.dialog == "radius_pick_a":
            self._on_radius_pick_a_touch(x, y)
            return
        if self.dialog == "radius_pick_b":
            self._on_radius_pick_b_touch(x, y)
            return
        if self.dialog == "radius_pick_corner":
            self._on_radius_pick_corner_touch(x, y)
            return
        #
        # DRAG CAVEAT: panning is reconstructed from on_touch rather
        # than a continuous drag hook: two clicks inside the
        # VIEW canvas within DRAG_TIMEOUT_MS of each other are treated
        # as a drag, and the view pans by the difference between them.
        # Whether this feels like a smooth drag depends on whether
        # on_touch fires repeatedly while a mouse button is held and
        # moved, or only once per discrete click, on your hardware.
        if self._in_canvas(x, y):
            now = time.ticks_ms()
            dragged = False
            if self._last_touch is not None and time.ticks_diff(now, self._last_touch_time) < self.DRAG_TIMEOUT_MS:
                dx = x - self._last_touch[0]
                dy = y - self._last_touch[1]
                if dx or dy:
                    self.pan_x += dx
                    self.pan_y += dy
                    dragged = True
            self._last_touch = (x, y)
            self._last_touch_time = now
            if dragged:
                self._redraw()
                self.mouse_box.value = self._safe_position_readout(x, y)
                return
        else:
            self._last_touch = None
        self.mouse_box.value = self._safe_position_readout(x, y)

    def _safe_position_readout(self, x, y):
        try:
            text = self._position_readout(x, y)
        except Exception as e:
            ulog("Model3DPage: position readout error: " + type(e).__name__ + " " + str(e))
            text = "Mouse: (%d, %d)" % (x, y)
        return text

    def _on_line_pick_touch(self, x, y):
        # LINE's "CLICK ON GRID" mode -- two clicks in the canvas set
        # start then end; no live "follows the mouse" preview (see the
        # on_touch drag caveat above). Every branch here updates
        # status_box directly so a click's outcome is visible on
        # screen immediately.
        if not self._in_canvas(x, y):
            self.status_box.value = "LINE: click (%d,%d) was outside the VIEW panel" % (x, y)
            return
        try:
            plane, point = self._plane_point_at(x, y)
        except Exception as e:
            self.status_box.value = "LINE pick error: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage: line pick error: " + type(e).__name__ + " " + str(e))
            return
        if self.line_stage == "start":
            self.line_start_point = point
            self.line_stage = "end"
            self._redraw()
            self.status_box.value = "LINE: start point set, click END point"
        else:
            self._push_undo()
            self.lines.append((self.line_start_point, point, self.current_layer))
            end_point = point
            start_point = self.line_start_point
            self.dialog = None
            self.line_stage = "start"
            self._redraw()
            self.status_box.value = "LINE: %s to %s" % (start_point, end_point)

    def _on_box_pick_touch(self, x, y):
        # BOX's "CLICK ON GRID" mode -- mirrors _on_line_pick_touch:
        # first click sets one corner, second click sets the opposite
        # corner and creates the box (on_box_create already sorts
        # whichever two corners come in into min/max order)
        if not self._in_canvas(x, y):
            self.status_box.value = "BOX: click (%d,%d) was outside the VIEW panel" % (x, y)
            return
        try:
            plane, point = self._plane_point_at(x, y)
        except Exception as e:
            self.status_box.value = "BOX pick error: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage: box pick error: " + type(e).__name__ + " " + str(e))
            return
        if self.box_pick_start is None:
            self.box_pick_start = point
            self._redraw()
            self.status_box.value = "BOX: first corner set, click the OPPOSITE corner"
        else:
            p1, p2 = self.box_pick_start, point
            corner_min = (min(p1[0], p2[0]), min(p1[1], p2[1]), min(p1[2], p2[2]))
            corner_max = (max(p1[0], p2[0]), max(p1[1], p2[1]), max(p1[2], p2[2]))
            self._push_undo()
            self.boxes.append((corner_min, corner_max, self.current_layer))
            self.dialog = None
            self.box_pick_start = None
            self._redraw()
            self.status_box.value = "BOX: %s to %s" % (corner_min, corner_max)

    def _on_circle_pick_touch(self, x, y):
        # CIRCLE's centre-placement step -- radius/plane/snap were
        # already confirmed back in the CIRCLE dialog (see
        # on_confirm_circle), so a single click here places the centre
        # and creates the circle. _plane_point_at already applies grid
        # snapping (or not) according to SNAP TO GRID/self.snap_enabled,
        # same as every other click-to-place tool.
        if not self._in_canvas(x, y):
            self.status_box.value = "CIRCLE: click (%d,%d) was outside the VIEW panel" % (x, y)
            return
        try:
            plane, point = self._plane_point_at(x, y)
        except Exception as e:
            self.status_box.value = "CIRCLE pick error: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage: circle pick error: " + type(e).__name__ + " " + str(e))
            return
        r = self._circle_pick_radius
        self._push_undo()
        self.circles.append((point, r, self.circle_plane, self.current_layer))
        for p0, p1 in self._circle_centerline_segments(point, r, self.circle_plane):
            self.lines.append((p0, p1, self.current_layer))
        self.dialog = None
        self._redraw()
        self.status_box.value = "CIRCLE: centre %s r=%g %s" % (point, r, self.circle_plane)

    def _on_multiline_pick_touch(self, x, y):
        # collects self.multiline_target points one click at a time,
        # all on the same plane (whichever the active GRID is on, or
        # XY -- same convention _plane_point_at always uses), then
        # closes the loop into one new POLY entry -- not separate LINE
        # segments, so it can later be SELECTed/EXTRUDEd as one shape
        if not self._in_canvas(x, y):
            self.status_box.value = "MULTI LINE: click (%d,%d) was outside the VIEW panel" % (x, y)
            return
        try:
            plane, point = self._plane_point_at(x, y)
        except Exception as e:
            self.status_box.value = "MULTI LINE pick error: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage: multiline pick error: " + type(e).__name__ + " " + str(e))
            return
        self.multiline_points.append(point)
        if len(self.multiline_points) < self.multiline_target:
            self._redraw()
            self.status_box.value = ("MULTI LINE: point %d/%d placed, click next point"
                                      % (len(self.multiline_points), self.multiline_target))
            return
        self._push_undo()
        self.polys.append((list(self.multiline_points), plane, 0.0, self.current_layer))
        count = len(self.multiline_points)
        self.multiline_points = []
        self.dialog = None
        self._redraw()
        self.status_box.value = ("MULTI LINE: %d-point shape added (closed) -- "
                                  "SELECT + EXTRUDE to make it solid" % count)

    def _on_radius_pick_a_touch(self, x, y):
        if not self._in_canvas(x, y):
            self.status_box.value = "RADIUS: click (%d,%d) was outside the VIEW panel" % (x, y)
            return
        hit = self._hit_test(x, y)
        if hit is None or hit[0] != "box":
            self.status_box.value = "RADIUS: click nearer a BOX wall"
            return
        self.radius_pick_a = hit[1]
        self.dialog = "radius_pick_b"
        self._redraw()
        self.status_box.value = "RADIUS: first wall picked -- click the SECOND wall"

    def _on_radius_pick_b_touch(self, x, y):
        if not self._in_canvas(x, y):
            self.status_box.value = "RADIUS: click (%d,%d) was outside the VIEW panel" % (x, y)
            return
        hit = self._hit_test(x, y)
        if hit is None or hit[0] != "box":
            self.status_box.value = "RADIUS: click nearer a BOX wall"
            return
        if hit[1] == self.radius_pick_a:
            # same wall picked twice -- round one of ITS OWN corners
            # instead of a corner shared with a second wall
            self.dialog = "radius_pick_corner"
            self._redraw()
            self.status_box.value = "RADIUS: click near the CORNER of that box to round"
            return
        self.radius_pick_b = hit[1]
        self.radius_corner_side = None
        self._radius_dialog_message = ""
        self.dialog = "radius"
        self._redraw()

    def _on_radius_pick_corner_touch(self, x, y):
        if not self._in_canvas(x, y):
            self.status_box.value = "RADIUS: click (%d,%d) was outside the VIEW panel" % (x, y)
            return
        try:
            box = self.boxes[self.radius_pick_a]
        except IndexError:
            self.dialog = None
            self.radius_pick_a = None
            self._redraw()
            self.status_box.value = "RADIUS: that box no longer exists"
            return
        self.radius_pick_b = self.radius_pick_a
        self.radius_corner_side = self._nearest_box_corner(
            box, x, y, self._last_scale, self._last_origin[0], self._last_origin[1])
        self._radius_dialog_message = ""
        self.dialog = "radius"
        self._redraw()

    def _on_select_pick_touch(self, x, y):
        if not self._in_canvas(x, y):
            self.status_box.value = "SELECT: click (%d,%d) was outside the VIEW panel" % (x, y)
            return
        try:
            hit = self._hit_test(x, y)
        except Exception as e:
            self.status_box.value = "SELECT error: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage: select error: " + type(e).__name__ + " " + str(e))
            return
        self.selected = hit
        ulog("Model3DPage: SELECT hit=%s at click (%d,%d)" % (str(hit), x, y))
        self.dialog = None
        self._redraw()
        if hit:
            kind, idx = hit
            self.status_box.value = "SELECTED: %s #%d" % (kind.upper(), idx + 1)
        else:
            self.status_box.value = "SELECT: nothing close enough -- try clicking nearer an item"

    def on_zoom_in(self, b):
        self.zoom = min(self.zoom * self.ZOOM_STEP, self.MAX_ZOOM)
        self._redraw()

    def on_zoom_out(self, b):
        self.zoom = max(self.zoom / self.ZOOM_STEP, self.MIN_ZOOM)
        self._redraw()

    def on_reset_view(self, b):
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.azimuth_deg = self.AZIMUTH_DEFAULT
        self.elevation_deg = self.ELEVATION_DEFAULT
        self._update_rotation_trig()
        self._redraw()

    def on_rotate_az_minus(self, b):
        self.azimuth_deg = (self.azimuth_deg - self.AZIMUTH_STEP) % 360.0
        self._update_rotation_trig()
        self._redraw()

    def on_rotate_az_plus(self, b):
        self.azimuth_deg = (self.azimuth_deg + self.AZIMUTH_STEP) % 360.0
        self._update_rotation_trig()
        self._redraw()

    def on_rotate_el_minus(self, b):
        self.elevation_deg = max(self.ELEVATION_MIN, self.elevation_deg - self.ELEVATION_STEP)
        self._update_rotation_trig()
        self._redraw()

    def on_rotate_el_plus(self, b):
        self.elevation_deg = min(self.ELEVATION_MAX, self.elevation_deg + self.ELEVATION_STEP)
        self._update_rotation_trig()
        self._redraw()

    def on_toggle_wireframe(self, b):
        self.wireframe_visible = not self.wireframe_visible
        self._redraw()

    def on_toggle_grid_visible(self, b):
        self.grid_visible = not self.grid_visible
        self._redraw()

    def on_toggle_snap(self, b):
        self.snap_enabled = not self.snap_enabled
        self._redraw()

    def on_extrude_pressed(self, b):
        if self.selected is None:
            self.status_box.value = "EXTRUDE: SELECT an item first"
            return
        self.active_command = "EXTRUDE"
        self.dialog = "extrude"
        self._redraw()

    def on_confirm_extrude(self, b):
        self.dialog = None
        if self.selected is None:
            self._redraw()
            self.status_box.value = "EXTRUDE: nothing selected"
            return
        kind, idx = self.selected
        try:
            amount = float(self.extrude_amount_box.value)
        except (ValueError, TypeError):
            amount = 0.0
        if amount <= 0:
            amount = 50.0
        amount = self._snap_length_to_grid(amount)

        # re-extruding the SAME base as last time (e.g. after editing
        # it) replaces the previous extrusion's generated geometry
        # instead of piling up a second, stale copy alongside it --
        # this is what makes EXTRUDE double as a "refresh"
        refreshed = False
        if (self._last_extrude and self._last_extrude["kind"] == kind
                and self._last_extrude["idx"] == idx):
            self._remove_generated(self._last_extrude["generated"])
            refreshed = True
        self._last_extrude = None

        try:
            if kind == "line":
                p0, p1, layer = self.lines[idx]
            elif kind == "box":
                c0, c1, layer = self.boxes[idx]
            elif kind == "circle":
                center, radius, plane, layer = self.circles[idx]
            elif kind == "poly":
                points, plane, old_height, layer = self.polys[idx]
            else:
                center, radius, plane, a0, a1, layer = self.arcs[idx]
        except IndexError:
            self._redraw()
            self.status_box.value = "EXTRUDE: that item no longer exists"
            return
        self._push_undo()
        generated = []
        if kind == "line":
            # turns a line into a rectangular wall outline: the
            # original line stays as the bottom edge, a copy raised by
            # `amount` in Z becomes the top edge, plus two verticals
            # closing the ends -- all ordinary LINE entries, no new
            # element kind needed
            top0 = (p0[0], p0[1], p0[2] + amount)
            top1 = (p1[0], p1[1], p1[2] + amount)
            self.lines.append((top0, top1, layer))
            generated.append(("line", len(self.lines) - 1))
            self.lines.append((p0, top0, layer))
            generated.append(("line", len(self.lines) - 1))
            self.lines.append((p1, top1, layer))
            generated.append(("line", len(self.lines) - 1))
            self.status_box.value = ("EXTRUDE: wall refreshed at %gmm" if refreshed
                                      else "EXTRUDE: line raised into a %gmm wall") % amount
        elif kind == "box":
            self.boxes[idx] = (c0, (c1[0], c1[1], c1[2] + amount), layer)
            self.status_box.value = "EXTRUDE: box height increased by %gmm" % amount
        elif kind == "circle":
            # sweeps the circle along its plane's normal axis into a
            # cylinder outline: the original stays as the bottom
            # circle, a copy offset by `amount` becomes the top circle,
            # with a few verticals connecting them -- all ordinary
            # CIRCLE/LINE entries, no new element kind needed
            axis = self._plane_normal_axis(plane)
            top_center = list(center)
            top_center[axis] += amount
            top_center = tuple(top_center)
            self.circles.append((top_center, radius, plane, layer))
            generated.append(("circle", len(self.circles) - 1))
            for angle in (0, 90, 180, 270):
                pb = self._circle_point(center, radius, plane, angle)
                pt = self._circle_point(top_center, radius, plane, angle)
                self.lines.append((pb, pt, layer))
                generated.append(("line", len(self.lines) - 1))
            self.status_box.value = ("EXTRUDE: cylinder refreshed at %gmm" if refreshed
                                      else "EXTRUDE: circle swept into a %gmm cylinder") % amount
        elif kind == "poly":
            # unlike LINE/CIRCLE/ARC, this doesn't spawn sibling
            # wireframe pieces -- the height lives directly on the
            # POLY itself (like BOX growing in place), and it's what
            # turns into an actual solid prism in the STL export (see
            # _poly_solid_triangles), not another hollow strut outline
            self.polys[idx] = (points, plane, amount, layer)
            self.status_box.value = ("EXTRUDE: MULTI LINE shape re-extruded to %gmm" if refreshed
                                      else "EXTRUDE: MULTI LINE shape extruded to a solid %gmm high") % amount
        else:
            # same idea as circle, but only the two ends of the arc get
            # a connecting vertical, matching a LINE's wall ends
            axis = self._plane_normal_axis(plane)
            top_center = list(center)
            top_center[axis] += amount
            top_center = tuple(top_center)
            self.arcs.append((top_center, radius, plane, a0, a1, layer))
            generated.append(("arc", len(self.arcs) - 1))
            for angle in (a0, a1):
                pb = self._circle_point(center, radius, plane, angle)
                pt = self._circle_point(top_center, radius, plane, angle)
                self.lines.append((pb, pt, layer))
                generated.append(("line", len(self.lines) - 1))
            self.status_box.value = ("EXTRUDE: curved wall refreshed at %gmm" if refreshed
                                      else "EXTRUDE: arc swept into a %gmm curved wall") % amount
        if generated:
            # not tracked for box -- it extrudes itself in place, no
            # separate generated pieces to refresh or highlight
            self._last_extrude = {"kind": kind, "idx": idx, "generated": generated}
        self.selected = None
        self._redraw()

    def _remove_generated(self, generated):
        # deletes previously-generated extrude geometry (see
        # on_confirm_extrude/_last_extrude) -- highest index first
        # within each kind, so removing one doesn't shift the index of
        # another not-yet-removed entry from the same list. Assumes
        # nothing else has inserted/deleted in boxes/lines/circles/arcs
        # since these indices were recorded (true for the EXTRUDE ->
        # EDIT base -> EXTRUDE again "refresh" workflow this exists
        # for; _last_extrude gets cleared on DELETE/UNDO/REDO/NEW FILE/
        # OPEN specifically because that assumption stops holding)
        by_kind = {}
        for k, i in generated:
            by_kind.setdefault(k, []).append(i)
        collections = {"line": self.lines, "box": self.boxes, "circle": self.circles, "arc": self.arcs}
        for k, indices in by_kind.items():
            collection = collections[k]
            for i in sorted(indices, reverse=True):
                if 0 <= i < len(collection):
                    del collection[i]

    def on_edit_pressed(self, b):
        if self.selected is None:
            self.status_box.value = "EDIT: SELECT an item first"
            return
        if self.selected[0] == "poly":
            # arbitrary point count doesn't fit the generic fixed-field
            # EDIT dialog every other kind uses -- DELETE and redraw is
            # the only way to change a MULTI LINE shape's points for
            # now; EXTRUDE still works fine on it for changing height
            self.status_box.value = "EDIT: not supported for MULTI LINE shapes yet -- DELETE and redraw, or EXTRUDE to change height"
            return
        self.active_command = "EDIT"
        self.dialog = "edit"
        self._redraw()

    def on_edit_delete(self, b):
        if self.selected is None:
            self.dialog = None
            self._redraw()
            self.status_box.value = "EDIT: nothing selected"
            return
        self._delete_selected()

    def on_confirm_edit(self, b):
        self.dialog = None
        if self.selected is None:
            self._redraw()
            self.status_box.value = "EDIT: nothing selected"
            return
        kind, idx = self.selected

        def parse(box, fallback):
            try:
                v = float(box.value)
            except (ValueError, TypeError):
                v = fallback
            return self._snap_to_grid(v)

        try:
            fields = self._edit_fields()
        except (IndexError, ValueError):
            self._redraw()
            self.status_box.value = "EDIT: that item no longer exists"
            return
        values = [parse(box, default) for box, (label, default) in zip(self.edit_boxes, fields)]

        self._push_undo()
        if kind == "line":
            layer = self.lines[idx][2]
            self.lines[idx] = ((values[0], values[1], values[2]), (values[3], values[4], values[5]), layer)
            self.status_box.value = "EDIT: LINE #%d updated" % (idx + 1)
        elif kind == "box":
            layer = self.boxes[idx][2]
            p0 = (values[0], values[1], values[2])
            p1 = (values[3], values[4], values[5])
            corner_min = (min(p0[0], p1[0]), min(p0[1], p1[1]), min(p0[2], p1[2]))
            corner_max = (max(p0[0], p1[0]), max(p0[1], p1[1]), max(p0[2], p1[2]))
            self.boxes[idx] = (corner_min, corner_max, layer)
            self.status_box.value = "EDIT: BOX #%d updated" % (idx + 1)
        elif kind == "circle":
            _, old_r, plane, layer = self.circles[idx]
            r = self._snap_length_to_grid(values[3] if values[3] > 0 else old_r)
            self.circles[idx] = ((values[0], values[1], values[2]), r, plane, layer)
            self.status_box.value = "EDIT: CIRCLE #%d updated" % (idx + 1)
        else:  # arc
            _, old_r, plane, old_a0, old_a1, layer = self.arcs[idx]
            r = self._snap_length_to_grid(values[3] if values[3] > 0 else old_r)
            self.arcs[idx] = ((values[0], values[1], values[2]), r, plane, values[4], values[5], layer)
            self.status_box.value = "EDIT: ARC #%d updated" % (idx + 1)
        self._redraw()

    def _model_snapshot(self):
        return (list(self.boxes), list(self.lines), list(self.circles), list(self.arcs), list(self.polys),
                self.grid, list(self.layers), dict(self.layer_visible), self.current_layer)

    def _restore_snapshot(self, snapshot):
        (self.boxes, self.lines, self.circles, self.arcs, self.polys, self.grid,
         self.layers, self.layer_visible, self.current_layer) = snapshot

    def _push_undo(self):
        # call BEFORE mutating the model -- captures the state to go
        # back to, and a fresh action means any old redo history no
        # longer makes sense
        self.undo_stack.append(self._model_snapshot())
        if len(self.undo_stack) > self.UNDO_MAX:
            self.undo_stack.pop(0)
        self.redo_stack = []

    def on_undo(self, b):
        if not self.undo_stack:
            self.status_box.value = "UNDO: nothing to undo"
            return
        self.redo_stack.append(self._model_snapshot())
        self._restore_snapshot(self.undo_stack.pop())
        # self.selected is a (kind, index) pair into boxes/lines/
        # circles/arcs -- snapshots don't carry selection, so that
        # index can easily point at a different item (or nothing) once
        # the lists it indexes into have just changed underneath it
        self.selected = None
        # same reasoning for any tracked "last extrude" indices
        self._last_extrude = None
        self._redraw()
        self.status_box.value = "Undone"

    def on_redo(self, b):
        if not self.redo_stack:
            self.status_box.value = "REDO: nothing to redo"
            return
        self.undo_stack.append(self._model_snapshot())
        self._restore_snapshot(self.redo_stack.pop())
        self.selected = None
        self._last_extrude = None
        self._redraw()
        self.status_box.value = "Redone"

    def on_pan_left(self, b):
        self.pan_x -= self.PAN_NUDGE
        self._redraw()

    def on_pan_right(self, b):
        self.pan_x += self.PAN_NUDGE
        self._redraw()

    def on_pan_up(self, b):
        self.pan_y -= self.PAN_NUDGE
        self._redraw()

    def on_pan_down(self, b):
        self.pan_y += self.PAN_NUDGE
        self._redraw()

    def _draw_dashed_rect(self, fb, x, y, w, h, color, dash=4, gap=3):
        step = dash + gap
        for edge_y in (y, y + h):
            xi = x
            while xi < x + w:
                xe = min(xi + dash, x + w)
                _fb_line(fb, xi, edge_y, xe, edge_y, color)
                xi += step
        for edge_x in (x, x + w):
            yi = y
            while yi < y + h:
                ye = min(yi + dash, y + h)
                _fb_line(fb, edge_x, yi, edge_x, ye, color)
                yi += step

    def on_back(self, b):
        self.go("exit")


def main():
    screen(hdmi.RGB640)
    time.sleep(2)
    console("serial")
    where = "model3d"
    try:
        while where != "exit":
            try:
                if where == "model3d":
                    where = Model3DPage().show()
                elif isinstance(where, str) and where.startswith("help|"):
                    _, topic, return_to = where.split("|", 2)
                    where = HelpPage(topic, return_to).show()
                else:
                    where = "exit"
            except Exception as e:
                msg = "PAGE ERROR at " + str(where) + " : " + type(e).__name__ + " " + str(e)
                print(msg)
                ulog(msg)
                where = "exit"
    finally:
        console("both")
        hdmi.fill(0)


main()
