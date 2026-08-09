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
# /sd/models; and shows a live isometric wireframe view with zoom, pan,
# and grid snapping. LINE has both a typed-numbers entry and a
# click-on-the-grid entry mode. Icons for the command buttons are
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

PAGE = 0x66B2FF
INK = 0x103018
BTN = 0x2E7D32


def ulog(text):
    try:
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
#   GRID plane spacing extent    -- at most one per file, no layer
#   LAYER name visible           -- visible is 1 or 0, one per layer
def serialize_model(boxes, lines, circles, arcs, grid, layers, layer_visible):
    out = []
    for (c0, c1, layer) in boxes:
        out.append("BOX %g %g %g %g %g %g %s" % (c0[0], c0[1], c0[2], c1[0], c1[1], c1[2], layer))
    for (p0, p1, layer) in lines:
        out.append("LINE %g %g %g %g %g %g %s" % (p0[0], p0[1], p0[2], p1[0], p1[1], p1[2], layer))
    for (c, r, plane, layer) in circles:
        out.append("CIRCLE %g %g %g %g %s %s" % (c[0], c[1], c[2], r, plane, layer))
    for (c, r, plane, a0, a1, layer) in arcs:
        out.append("ARC %g %g %g %g %s %g %g %s" % (c[0], c[1], c[2], r, plane, a0, a1, layer))
    if grid:
        plane, spacing, extent = grid
        out.append("GRID %s %g %g" % (plane, spacing, extent))
    for name in layers:
        out.append("LAYER %s %d" % (name, 1 if layer_visible.get(name, True) else 0))
    return "\n".join(out) + "\n"


def parse_model(text):
    boxes, lines, circles, arcs = [], [], [], []
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
        elif parts[0] == "GRID" and len(parts) >= 4:
            grid = (parts[1], float(parts[2]), float(parts[3]))
        elif parts[0] == "LAYER" and len(parts) >= 3:
            layers.append(parts[1])
            layer_visible[parts[1]] = parts[2] != "0"
    if not layers:
        layers = ["Layer1"]
        layer_visible = {"Layer1": True}
    return boxes, lines, circles, arcs, grid, layers, layer_visible


def save_model_file(name, boxes, lines, circles, arcs, grid, layers, layer_visible):
    try:
        os.mkdir(MODELS_DIR)
    except OSError:
        pass  # already exists
    path = MODELS_DIR + "/" + name + ".model"
    f = open(path, "w")
    try:
        f.write(serialize_model(boxes, lines, circles, arcs, grid, layers, layer_visible))
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


HELP_TEXT = {
    "model3d": ("3D Model Editor", [
        ("NEW FILE", "Type X/Y/Z size in mm and CREATE a box -- clears everything else currently modelled."),
        ("OPEN", "Pick a saved model from the list and load it into the viewer."),
        ("SAVE AS", "Type a name and save everything currently modelled to the SD card."),
        ("DELETE", "Pick a saved model from the list and remove that file."),
        ("SELECT", "Click near an item's outline in the VIEW panel to select it (highlighted yellow) -- pick another command to cancel."),
        ("LINE", "Choose CLICK ON GRID (tap start then end point in the VIEW panel, snaps to the grid if one's set) or TYPE VALUES (enter X/Y/Z numbers)."),
        ("CTR LINE", "Pick an axis (tap to cycle X/Y/Z) and a length -- adds a line through the origin along that axis."),
        ("BOX", "Enter one corner, then the opposite corner, to add a box anywhere (doesn't replace NEW FILE's box)."),
        ("CIRCLE", "Enter a centre point and radius; tap the plane button to cycle XY/XZ/YZ."),
        ("ARC", "Same as CIRCLE plus a start/end angle in degrees, swept counter-clockwise."),
        ("GRID", "Set a spacing, extent, and plane (tap to cycle XY/XZ/YZ) to show a dotted reference plane. Replaces any existing grid."),
        ("LAYER button", "Shows the active layer -- new items go on it. Opens LAYERS: pick one then SET ACTIVE, TOGGLE SHOW (hide/unhide), or NEW LAYER."),
        ("VIEW panel", "Isometric view of everything modelled -- X is red, Y is green, Z is blue, all from the origin marked 0,0."),
        ("+ / - / RST", "Zoom in, zoom out, or reset the view back to its default position and zoom."),
        ("U / D / L / R", "Pan the view up/down/left/right in fixed steps."),
        ("UNDO / REDO", "Step back or forward through NEW FILE/OPEN/LINE/BOX/CIRCLE/ARC/GRID changes."),
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
    def __init__(self, topic, return_to):
        Page.__init__(self)
        self.topic = topic
        self.return_to = return_to

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

    def build(self, g):
        title, entries = HELP_TEXT.get(self.topic, ("Help", []))
        g.caption(320, 6, "Help -- " + title, fg=INK, bg=PAGE, font=3, just="CT")
        g.button(486, 4, 140, 28, "BACK", fg=WHITE, bg=RED, font=2, callback=self.on_back)
        y = 34
        for label, desc in entries:
            if y > 404:
                break  # keep it on one screen -- longer topics get trimmed
            g.caption(20, y, label, fg=INK, bg=PAGE, font=2)
            y += 18
            for line in self.wrap(desc):
                g.caption(30, y, line, fg=INK, bg=PAGE, font=1)
                y += 14
            y += 8

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
                "BOX", "CIRCLE", "ARC", "GRID")
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
    MAX_ZOOM = 5.0

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

    # true isometric projection, still rotation-free (no quaternion/
    # camera machinery) -- X and Y both tilted 30 degrees off
    # horizontal, Z straight up: X goes down-right, Y goes down-left,
    # matching the standard technical-drawing isometric layout. All
    # three axes share one scale (no depth foreshortening).
    ISO_COS30 = 0.8660254
    ISO_SIN30 = 0.5

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

    # SELECT -- click near an element's projected outline to select it
    SELECT_COLOR = 0xFFFF00  # yellow, distinct from white geometry and the axis colours
    SELECT_THRESHOLD = 15    # px -- closest hit within this radius wins

    def __init__(self):
        Page.__init__(self)
        # build() runs before enter() (Page.show()), so anything build()
        # reads must exist before the first build() call
        self.dialog = None        # None, "newfile", "open", "saveas", "delete", "line",
                                   # "box", "circle", or "arc"
        self.model_name = "mycar"
        self.boxes = []             # list of ((x0,y0,z0), (x1,y1,z1)) opposite corners
        self.lines = []             # list of ((x0,y0,z0), (x1,y1,z1)) segments
        self.circles = []           # list of ((cx,cy,cz), radius, plane)
        self.arcs = []               # list of ((cx,cy,cz), radius, plane, start_deg, end_deg)

        self.line_start_point = None
        self.line_stage = "start"  # "start" or "end", within the LINE dialog
        self.box_start_point = None
        self.box_stage = "start"   # "start" or "end", within the BOX dialog
        self.circle_plane = "XY"   # cycles XY -> XZ -> YZ, within the CIRCLE dialog
        self.arc_plane = "XY"      # same, within the ARC dialog
        self.grid_plane = "XY"     # same, within the GRID dialog
        self.grid = None          # (plane, spacing, extent) or None -- one grid at a time,
                                   # a fresh GRID replaces whatever grid was already there
        self.centerline_axis = "X"  # cycles X -> Y -> Z, within the CTR LINE dialog

        # layers -- every box/line/circle/arc is tagged with the name
        # of whichever layer was "active" (current_layer) when it was
        # created. Hidden layers are skipped entirely by drawing, the
        # auto-fit scale, and SELECT's hit-testing.
        self.layers = ["Layer1"]
        self.current_layer = "Layer1"
        self.layer_visible = {"Layer1": True}
        self._dialog_selected_layer = None

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
        self._last_touch = None
        self._last_touch_time = 0
        self._last_scale = 1.0            # set for real by _draw_scene each redraw --
        self._last_origin = (0.0, 0.0)    # used by on_touch to report a model-space position

        self.active_command = None  # last command clicked, gets the red dashed frame
        self.selected = None  # (kind, index) e.g. ("box", 0), or None -- highlighted yellow

        self.undo_stack = []  # snapshots of (boxes, lines, circles, arcs, grid)
        self.redo_stack = []  # cleared whenever a new action is taken, not just undone

    def build(self, g):
        hdmi.fill(hdmi.fb().colour(self.BLACK))
        for i in range(self.BORDER):
            g.frame(i, i, 640 - 2 * i, 480 - 2 * i, "", fg=self.GREY, font=1)
        g.caption(320, self.INNER_Y0 + 6, "3D Model Editor", fg=WHITE, bg=self.BLACK, font=3, just="CT")
        self.help_button(g, "model3d", "model3d")

        if self.dialog == "newfile":
            self._build_newfile_dialog(g)
        elif self.dialog == "open":
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
        elif self.dialog == "box":
            self._build_box_dialog(g)
        elif self.dialog == "circle":
            self._build_circle_dialog(g)
        elif self.dialog == "arc":
            self._build_arc_dialog(g)
        elif self.dialog == "grid":
            self._build_grid_dialog(g)
        elif self.dialog == "layers":
            self._build_layers_dialog(g)
        elif self.dialog == "line_pick" or self.dialog == "select_pick":
            # reuses the normal main layout (canvas, zoom, D-pad, all
            # of it) rather than a modal -- picking points/elements
            # needs the wireframe/grid actually visible and clickable,
            # which no modal dialog in this app currently shows
            self._build_main(g)
        else:
            self._build_main(g)

    # command name -> icon file under ICONS_DIR (see assets/icons/*.svg
    # in the repo -- rendered to 26x26 BMP)
    ICON_NAMES = {
        "NEW FILE": "new_file", "OPEN": "open", "SAVE AS": "save_as", "DELETE": "delete",
        "SELECT": "select", "LINE": "line", "CTR LINE": "centerline", "BOX": "box",
        "CIRCLE": "circle", "ARC": "arc", "GRID": "grid",
    }

    # command name -> its real dialog key
    COMMAND_DIALOG = {
        "NEW FILE": "newfile", "OPEN": "open", "SAVE AS": "saveas", "DELETE": "delete",
        "SELECT": "select_pick", "LINE": "line_choice", "CTR LINE": "centerline", "BOX": "box",
        "CIRCLE": "circle", "ARC": "arc", "GRID": "grid",
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
        if self.dialog == "line_pick":
            verb = "START" if self.line_stage == "start" else "END"
            snap = "grid snap ON" if self.grid else "no grid set, not snapped"
            self.status_box.value = "LINE: click %s point in VIEW (%s) -- pick another command to cancel" % (verb, snap)
        elif self.dialog == "select_pick":
            self.status_box.value = "SELECT: click near an item in VIEW -- pick another command to cancel"

        # mouse/touch coordinate readout below the panel
        self.mouse_box = g.displaybox(self.PANEL_X, self.PANEL_Y + self.PANEL_H + 4,
                                       260, 20, "X:--  Y:--  Z:--", fg=WHITE, bg=self.BLACK, font=1)
        try:
            g.on_touch(self.on_touch)
        except Exception as e:
            ulog("Model3DPage: on_touch registration failed: " + str(e))
        # on_move (hover) is not used -- confirmed not to work on the
        # hardware this was originally built/tested on. Panning below
        # reuses on_touch instead.

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

    def _draw_command_icons(self, icon_slots):
        for name, ix, iy in icon_slots:
            icon_name = self.ICON_NAMES.get(name)
            if not icon_name:
                continue
            path = ICONS_DIR + "/" + icon_name + ".bmp"
            try:
                pcimage.draw_bmp(path, ix, iy, dither=True)
            except Exception as e:
                ulog("Model3DPage: icon load failed for " + name + ": " + type(e).__name__ + " " + str(e))

    # --- scene projection -------------------------------------------

    def _raw_project(self, x, y, z):
        # projects at scale=1, origin=(0,0) -- just used to measure
        # extents before the real scale/origin are known. Z is "up" on
        # screen, matching the usual CAD/3D-printer convention (build
        # plate is the X-Y plane, height is Z). X goes down-right, Y
        # down-left, both at 30 degrees (true isometric).
        sx = (x - y) * self.ISO_COS30
        sy = (x + y) * self.ISO_SIN30 - z
        return sx, sy

    # which two coordinate indices sweep around a circle/arc in each
    # plane -- the third index stays fixed at the centre's value
    PLANE_AXES = {"XY": (0, 1), "XZ": (0, 2), "YZ": (1, 2)}

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
            for bi, box in enumerate(self.boxes):
                if not self.layer_visible.get(box[2], True):
                    continue
                colour = self.SELECT_COLOR if self.selected == ("box", bi) else WHITE
                for p1, p2 in self._box_edges(box):
                    s1 = self._project(p1[0], p1[1], p1[2], scale, ox, oy)
                    s2 = self._project(p2[0], p2[1], p2[2], scale, ox, oy)
                    self._clipped_line(fb, s1[0], s1[1], s2[0], s2[1], colour)
            for li, (p0, p1, layer) in enumerate(self.lines):
                if not self.layer_visible.get(layer, True):
                    continue
                colour = self.SELECT_COLOR if self.selected == ("line", li) else WHITE
                s0 = self._project(p0[0], p0[1], p0[2], scale, ox, oy)
                s1 = self._project(p1[0], p1[1], p1[2], scale, ox, oy)
                self._clipped_line(fb, s0[0], s0[1], s1[0], s1[1], colour)
            for ci, (c, r, plane, layer) in enumerate(self.circles):
                if not self.layer_visible.get(layer, True):
                    continue
                colour = self.SELECT_COLOR if self.selected == ("circle", ci) else WHITE
                self._draw_arc(fb, c, r, plane, 0, 360, scale, ox, oy, colour=colour)
            for ai, (c, r, plane, a0, a1, layer) in enumerate(self.arcs):
                if not self.layer_visible.get(layer, True):
                    continue
                colour = self.SELECT_COLOR if self.selected == ("arc", ai) else WHITE
                self._draw_arc(fb, c, r, plane, a0, a1, scale, ox, oy, colour=colour)
            if self.grid:
                self._draw_grid_dots(fb, scale, ox, oy)

            self._draw_axes(g, fb, scale, ox, oy)
        except Exception as e:
            ulog("Model3DPage: scene draw error: " + type(e).__name__ + " " + str(e))

    def _draw_grid_dots(self, fb, scale, ox, oy):
        # a dot at every grid intersection in its plane. Grey, not
        # white, so it reads as background reference rather than part
        # of the actual model. Spans 0 to extent (not -extent to
        # +extent) in both plane axes, matching every box/line/circle/
        # arc's own 0-based convention.
        plane, spacing, extent = self.grid
        i, j = self.PLANE_AXES[plane]
        n = int(extent / spacing)
        for gi in range(0, n + 1):
            for gj in range(0, n + 1):
                p = [0.0, 0.0, 0.0]
                p[i] = gi * spacing
                p[j] = gj * spacing
                sx, sy = self._project(p[0], p[1], p[2], scale, ox, oy)
                if self.CANVAS_X0 <= sx <= self.CANVAS_X1 and self.CANVAS_Y0 <= sy <= self.CANVAS_Y1:
                    ix, iy = int(sx), int(sy)
                    _fb_pixel(fb, ix, iy, self.GREY)
                    _fb_pixel(fb, ix + 1, iy, self.GREY)
                    _fb_pixel(fb, ix, iy + 1, self.GREY)
                    _fb_pixel(fb, ix + 1, iy + 1, self.GREY)

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

    def _draw_axes(self, g, fb, scale, ox, oy):
        # X/Y/Z reference arrows, one colour each. Each starts past
        # wherever the model already reaches along that axis (not at
        # literal (0,0,0)) so it doesn't trace back over -- and cancel
        # out -- a wireframe edge running the same direction.
        length = self._axis_length()
        wing = length * 0.15
        axis_index = {"X": 0, "Y": 1, "Z": 2}
        for axis, d in self.AXIS_DIRS.items():
            perp = self.AXIS_PERP[axis]
            colour = self.AXIS_COLORS[axis]
            start_at = self._axis_extent(axis_index[axis])
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
                g.caption(int(tip[0]) + 6, int(tip[1]) - 8, axis, fg=colour, bg=self.BLACK, font=1)

        origin = self._project(0, 0, 0, scale, ox, oy)
        g.caption(int(origin[0]) + 6, int(origin[1]) + 4, "0,0", fg=WHITE, bg=self.BLACK, font=1)

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

    def _build_newfile_dialog(self, g):
        h = 240
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "NEW FILE", fg=WHITE, font=2)

        defaults = (100.0, 60.0, 40.0)
        labels = ("X (mm):", "Y (mm):", "Z (mm):")
        boxes = []
        for i, label in enumerate(labels):
            ly = y0 + 40 + i * 44
            g.caption(self.DLG_X + 20, ly + 6, label, fg=WHITE, bg=self.BLACK, font=1)
            boxes.append(g.textbox(self.DLG_X + 130, ly, 100, 26, str(defaults[i]), font=1))
        self.newfile_x_box, self.newfile_y_box, self.newfile_z_box = boxes

        g.button(self.DLG_X + 20, y0 + 180, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_newfile)
        g.button(self.DLG_X + 180, y0 + 180, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_saveas_dialog(self, g):
        h = 160
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "SAVE AS", fg=WHITE, font=2)
        g.caption(self.DLG_X + 20, y0 + 40, "Name:", fg=WHITE, bg=self.BLACK, font=1)
        self.saveas_box = g.textbox(self.DLG_X + 20, y0 + 58, self.DLG_W - 40, 26,
                                     self.model_name, font=1)
        g.button(self.DLG_X + 20, y0 + 96, 120, 40, "SAVE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_saveas)
        g.button(self.DLG_X + 180, y0 + 96, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

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

    def _build_line_dialog(self, g):
        # two-step: START POINT then END POINT, using the same three
        # boxes -- they come up blank each step
        h = 240
        y0 = (480 - h) // 2
        title = "LINE -- START POINT" if self.line_stage == "start" else "LINE -- END POINT"
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
        h = 300
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "CIRCLE", fg=WHITE, font=2)

        labels = ("Center X:", "Center Y:", "Center Z:", "Radius:")
        boxes = []
        for i, label in enumerate(labels):
            ly = y0 + 36 + i * 40
            g.caption(self.DLG_X + 20, ly + 6, label, fg=WHITE, bg=self.BLACK, font=1)
            boxes.append(g.textbox(self.DLG_X + 130, ly, 100, 26, "", font=1))
        self.circle_cx_box, self.circle_cy_box, self.circle_cz_box, self.circle_r_box = boxes

        ly = y0 + 36 + 4 * 40
        g.caption(self.DLG_X + 20, ly + 6, "Plane:", fg=WHITE, bg=self.BLACK, font=1)
        g.button(self.DLG_X + 130, ly, 100, 26, self.circle_plane, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_cycle_circle_plane)

        g.button(self.DLG_X + 20, y0 + h - 60, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_circle)
        g.button(self.DLG_X + 180, y0 + h - 60, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_arc_dialog(self, g):
        h = 360
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "ARC", fg=WHITE, font=2)

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
        h = 260
        y0 = (480 - h) // 2
        g.frame(self.DLG_X, y0, self.DLG_W, h, "GRID", fg=WHITE, font=2)

        ly = y0 + 40
        g.caption(self.DLG_X + 20, ly + 6, "Spacing (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.grid_spacing_box = g.textbox(self.DLG_X + 160, ly, 100, 26, "10", font=1)

        ly += 44
        g.caption(self.DLG_X + 20, ly + 6, "Extent (mm):", fg=WHITE, bg=self.BLACK, font=1)
        self.grid_extent_box = g.textbox(self.DLG_X + 160, ly, 100, 26, "100", font=1)

        ly += 44
        g.caption(self.DLG_X + 20, ly + 6, "Plane:", fg=WHITE, bg=self.BLACK, font=1)
        g.button(self.DLG_X + 160, ly, 100, 26, self.grid_plane, fg=WHITE, bg=BTN, font=1,
                 callback=self.on_cycle_grid_plane)

        g.button(self.DLG_X + 20, y0 + h - 60, 120, 40, "CREATE", fg=WHITE, bg=BTN, font=2,
                 callback=self.on_confirm_grid)
        g.button(self.DLG_X + 180, y0 + h - 60, 120, 40, "CANCEL", fg=WHITE, bg=RED, font=2,
                 callback=self.on_cancel_dialog)

    def _build_layers_dialog(self, g):
        h = 280
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
        g.button(self.DLG_X + 20, y0 + 212, 130, 36, "NEW LAYER", fg=WHITE, bg=BTN, font=1,
                 callback=self.on_new_layer)
        g.button(self.DLG_X + 170, y0 + 212, 130, 36, "CLOSE", fg=WHITE, bg=RED, font=2,
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

    def on_confirm_newfile(self, b):
        def parse(box, fallback):
            try:
                v = float(box.value)
                return v if v > 0 else fallback
            except (ValueError, TypeError):
                return fallback
        x = parse(self.newfile_x_box, 100.0)
        y = parse(self.newfile_y_box, 60.0)
        z = parse(self.newfile_z_box, 40.0)
        self._push_undo()
        # NEW FILE starts completely fresh, including layers -- the
        # new box always lands on a single default one
        self.boxes = [((0.0, 0.0, 0.0), (x, y, z), "Layer1")]
        self.lines = []
        self.circles = []
        self.arcs = []
        self.grid = None
        self.layers = ["Layer1"]
        self.current_layer = "Layer1"
        self.layer_visible = {"Layer1": True}
        self.selected = None
        self.dialog = None
        self._redraw()
        self.status_box.value = "NEW FILE: %g x %g x %g mm box" % (x, y, z)

    def on_confirm_saveas(self, b):
        name = (self.saveas_box.value or "").strip()
        self.dialog = None
        self._redraw()
        if not name:
            self.status_box.value = "SAVE AS cancelled -- no name entered"
            return
        self.model_name = name
        try:
            path = save_model_file(name, self.boxes, self.lines, self.circles, self.arcs, self.grid,
                                    self.layers, self.layer_visible)
            self.status_box.value = "Saved to " + path
        except Exception as e:
            self.status_box.value = "SAVE AS failed: " + type(e).__name__ + " " + str(e)
            ulog("Model3DPage SAVE AS error: " + type(e).__name__ + " " + str(e))

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
            boxes, lines, circles, arcs, grid, layers, layer_visible = load_model_file(name)
            self._push_undo()
            self.boxes = boxes
            self.lines = lines
            self.circles = circles
            self.arcs = arcs
            self.grid = grid
            self.layers = layers
            self.layer_visible = layer_visible
            self.current_layer = layers[0]
            self.selected = None
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
                return float(box.value)
            except (ValueError, TypeError):
                return 0.0
        return (parse(self.line_x_box), parse(self.line_y_box), parse(self.line_z_box))

    def on_line_choice_click(self, b):
        self.line_stage = "start"
        self.dialog = "line_pick"
        self._redraw()

    def on_line_choice_type(self, b):
        self.line_stage = "start"
        self.dialog = "line"
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
                return float(box.value)
            except (ValueError, TypeError):
                return 0.0
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
        order = ("XY", "XZ", "YZ")
        self.circle_plane = order[(order.index(self.circle_plane) + 1) % 3]
        self._redraw()

    def on_confirm_circle(self, b):
        def parse(box, fallback):
            try:
                return float(box.value)
            except (ValueError, TypeError):
                return fallback
        cx = parse(self.circle_cx_box, 0.0)
        cy = parse(self.circle_cy_box, 0.0)
        cz = parse(self.circle_cz_box, 0.0)
        r = parse(self.circle_r_box, 20.0)
        if r <= 0:
            r = 20.0
        self._push_undo()
        self.circles.append(((cx, cy, cz), r, self.circle_plane, self.current_layer))
        self.dialog = None
        self._redraw()
        self.status_box.value = "CIRCLE: centre (%g,%g,%g) r=%g %s" % (cx, cy, cz, r, self.circle_plane)

    def on_cycle_arc_plane(self, b):
        order = ("XY", "XZ", "YZ")
        self.arc_plane = order[(order.index(self.arc_plane) + 1) % 3]
        self._redraw()

    def on_confirm_arc(self, b):
        def parse(box, fallback):
            try:
                return float(box.value)
            except (ValueError, TypeError):
                return fallback
        cx = parse(self.arc_cx_box, 0.0)
        cy = parse(self.arc_cy_box, 0.0)
        cz = parse(self.arc_cz_box, 0.0)
        r = parse(self.arc_r_box, 20.0)
        if r <= 0:
            r = 20.0
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

    def on_confirm_centerline(self, b):
        try:
            length = float(self.centerline_len_box.value)
            if length <= 0:
                length = 100.0
        except (ValueError, TypeError):
            length = 100.0
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
        extent = parse(self.grid_extent_box, 100.0)
        n = int(extent / spacing)
        self.dialog = None
        if n < 1:
            # extent smaller than spacing -- collapses to a single dot
            # at the origin, which looks identical no matter which
            # plane is selected (they all pass through 0,0,0)
            self._redraw()
            self.status_box.value = "GRID: extent must be at least as large as spacing"
            return
        dot_count = (n + 1) ** 2
        if dot_count > self.GRID_MAX_DOTS:
            self._redraw()
            self.status_box.value = ("GRID: %d points is too many (max %d) -- "
                                      "use a bigger spacing or smaller extent" % (dot_count, self.GRID_MAX_DOTS))
            return
        self._push_undo()
        self.grid = (self.grid_plane, spacing, extent)
        self._redraw()
        self.status_box.value = "GRID: %s, %g mm spacing, %g mm extent" % (self.grid_plane, spacing, extent)

    def on_open_layers(self, b):
        self._dialog_selected_layer = self.current_layer
        self.dialog = "layers"
        self._redraw()

    def on_pick_layer(self, c):
        i = c.value
        if 0 <= i < len(self.layers):
            self._dialog_selected_layer = self.layers[i]

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
        self._redraw()

    def _make_command_handler(self, name):
        def handler(b):
            self.on_command(name)
        return handler

    def on_command(self, name):
        self.active_command = name
        if name == "LINE":
            self.line_stage = "start"
        elif name == "BOX":
            self.box_stage = "start"
        target = self.COMMAND_DIALOG.get(name)
        if target is None:
            self._redraw()
            self.status_box.value = "Pressed: " + name
            ulog("Model3DPage: command pressed: " + name)
            return
        self.dialog = target
        self._redraw()

    def _in_canvas(self, x, y):
        return self.CANVAS_X0 <= x <= self.CANVAS_X1 and self.CANVAS_Y0 <= y <= self.CANVAS_Y1

    def _screen_to_plane_point(self, sx, sy, plane):
        # inverts _project(), assuming the point actually lies on
        # `plane` (the third axis is 0) -- a single 2D screen point
        # can't otherwise be turned back into a 3D one. Uses whatever
        # scale/origin the VIEW panel was last drawn with.
        scale = self._last_scale or 1.0
        ox, oy = self._last_origin
        rsx = (sx - ox) / scale
        rsy = (sy - oy) / scale
        C, S = self.ISO_COS30, self.ISO_SIN30
        if plane == "XY":
            x = (rsx / C + rsy / S) / 2.0
            y = (rsy / S - rsx / C) / 2.0
            z = 0.0
        elif plane == "XZ":
            x = rsx / C
            z = x * S - rsy
            y = 0.0
        else:  # YZ
            y = -rsx / C
            z = y * S - rsy
            x = 0.0
        return (x, y, z)

    def _snap_to_grid_point(self, point):
        if not self.grid:
            return point
        plane, spacing, extent = self.grid
        i, j = self.PLANE_AXES[plane]
        p = list(point)
        for idx in (i, j):
            v = round(p[idx] / spacing) * spacing
            p[idx] = max(0.0, min(extent, v))
        return (p[0], p[1], p[2])

    def _point_to_segment_dist(self, px, py, x0, y0, x1, y1):
        dx, dy = x1 - x0, y1 - y0
        if dx == 0 and dy == 0:
            return math.hypot(px - x0, py - y0)
        t = ((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        cx, cy = x0 + t * dx, y0 + t * dy
        return math.hypot(px - cx, py - cy)

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
        if self.dialog == "line_pick":
            self._on_line_pick_touch(x, y)
            return
        if self.dialog == "select_pick":
            self._on_select_pick_touch(x, y)
            return
        #
        # DRAG CAVEAT: a genuine continuous mouse-move/hover hook
        # (on_move) is not used here -- it wasn't reliable on the
        # hardware this was built/tested on -- so panning is
        # reconstructed from on_touch instead: two clicks inside the
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
            return self._position_readout(x, y)
        except Exception as e:
            ulog("Model3DPage: position readout error: " + type(e).__name__ + " " + str(e))
            return "Mouse: (%d, %d)" % (x, y)

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
        else:
            self._push_undo()
            self.lines.append((self.line_start_point, point, self.current_layer))
            end_point = point
            start_point = self.line_start_point
            self.dialog = None
            self.line_stage = "start"
            self._redraw()
            self.status_box.value = "LINE: %s to %s" % (start_point, end_point)

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
        self._redraw()

    def _model_snapshot(self):
        return (list(self.boxes), list(self.lines), list(self.circles), list(self.arcs), self.grid,
                list(self.layers), dict(self.layer_visible), self.current_layer)

    def _restore_snapshot(self, snapshot):
        (self.boxes, self.lines, self.circles, self.arcs, self.grid,
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
        self._redraw()
        self.status_box.value = "Undone"

    def on_redo(self, b):
        if not self.redo_stack:
            self.status_box.value = "REDO: nothing to redo"
            return
        self.undo_stack.append(self._model_snapshot())
        self._restore_snapshot(self.redo_stack.pop())
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
