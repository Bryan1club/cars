# 3D Model Editor (standalone)

A wireframe 3D model editor for the **Pico Computer 3** board, extracted
from a larger car-club management program so it can be shared and run
on its own.

Draw boxes, lines, circles, and arcs on named layers; view them as a
live isometric wireframe with pan/zoom and undo/redo; save/load named
models to the SD card.

## Requirements

- A Pico Computer 3 board (or compatible) with the `hdmi`, `pcgui`,
  `pcgfx`, `pcconfig`, `pcconsole`, and `pcimage` MicroPython modules
  available on the firmware.
- An SD card mounted at `/sd`.

## Setup

1. Copy `model3d_editor.py` to the board.
2. Copy the contents of `icons/` (the `.bmp` files) to `/sd/icons/` on
   the SD card. The `.svg` sources are included for reference/editing
   only — they don't need to go on the board.
3. Run `model3d_editor.py` (e.g. from the REPL: `import model3d_editor`,
   or set it as the board's boot script). It takes over the HDMI
   screen and serial console for the duration of the app and hands
   them back on exit.

Models are saved as plain text under `/sd/models/*.model`.

## Notes

- Input is click/tap based (`on_touch`) rather than continuous
  mouse-move — this board's continuous-hover hook wasn't reliable, so
  panning is nudged with on-screen U/D/L/R buttons instead of dragged.
- Layers are organisational groups (show/hide, tag elements), not
  Z-height slicing.
- GRID is capped at 500 dots to avoid a very fine spacing/large extent
  combination overwhelming the board with blocking pixel draws.
