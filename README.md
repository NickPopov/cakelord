# Napoleon Cake Builder

A web puzzle game where you assemble a Napoleon cake from 9 irregular cake layers (коржі) of varying size. Cut and rotate each cake into pieces and fit them into a 6×4 rectangle, then bake the layer — the more of the rectangle you cover, the better. Bake 8 layers to win.

Cutting is risky: cakes can **crack**. A cracked cut doesn't follow a straight line (you get one bigger and one smaller piece) and may shed a few cells as lost crumbs. Smaller pieces are more fragile, so trimming an offcut down to fit a tight gap is a gamble.

Written entirely in Python with Pygame, compiled to WebAssembly via Pygbag.

## Controls

- **Left-click + drag** — grab a cake from the inventory or move a piece in the work area.
- **R** — rotate the piece you're dragging (or hovering over) by 90°.
- **Right-click** on a placed piece — unsnap it from the target rectangle.
- **C** (or click "Cut Mode") — toggle cut mode. In cut mode, hover over a piece to preview the cut line, then click to cut. Cuts can crack — watch for the "Cracked!" message and the crumb flash where cells fall off.
- **B** (or click "Bake Layer") — bake the current layer. Allowed at any coverage above 0%; your coverage is recorded per layer, so aim to fill as much as possible.
- **N** (or click "New Game") — start a new game.
- Drop a piece on **DISCARD** to throw it away.

## Run locally

```bash
pip install -r requirements.txt
python main.py
```

## Build/serve for the web (Pygbag)

From the project root:

```bash
pygbag main.py
```

This opens a local web server (default `http://localhost:8000`) where the game runs inside the browser.

To produce a static build for deployment:

```bash
pygbag --build main.py
```

The output is placed in `build/web/`.

## Architecture

```
main.py              # async entry point (required for pygbag)
scene.py             # PlayScene + WinScene
game.py              # GameState — inventory, work pieces, placed pieces, layers, coverage
shape.py             # Shape ABC + PolyominoShape (cells, cut, snap, rotate)
shape_factory.py     # Random polyomino generator (frontier-set growth)
ui.py                # InventoryBar, StackView, Button, DiscardZone, target area
config.py            # Constants (grid size, colors, layout)
pygbag.ini           # Tells pygbag to skip .venv and other dev folders
```

The `Shape` abstract base class isolates geometry from the rest of the code. The MVP ships `PolyominoShape` (grid-of-cells), but a `PolygonShape` could be dropped in later without touching the game loop or scenes.
