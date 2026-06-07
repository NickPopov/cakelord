# Napoleon Cake Builder

A web puzzle game where you assemble a Napoleon cake from 9 irregular cake layers (коржі) of varying size. Cut and rotate each cake into pieces and fit them into a 6×4 rectangle, then bake the layer — the more of the rectangle you cover, the better. Bake 8 layers to win.

Cutting is risky: cakes can **crack**. A cracked cut doesn't follow a straight line (you get one bigger and one smaller piece) and may shed a few cells as lost crumbs. Smaller pieces are more fragile, so trimming an offcut down to fit a tight gap is a gamble.

Nothing goes to waste: those crumbs are collected and used to **decorate the top of the napoleon**. Gather 24 crumb units to fully decorate it.

Written entirely in Python with Pygame, compiled to WebAssembly via Pygbag.

## Coverage scoring

Each baked layer is scored on coverage. Coverage starts from how much of the 6×4 rectangle is filled, then subtracts a **cutting penalty**: the more pieces you use, the more total edge you create, and each extra edge over an uncut layer costs 1%. The penalty is based on each piece's own shape, so it's **independent of where you drop the pieces** — only how you cut matters.

- One uncut 6×4 cake fills the rectangle with no extra edges → **100%**.
- Two 3×4 pieces add 8 edges of seam between them → **92%**.
- Leaving empty space lowers coverage too, through the filled-cell fraction.

So a clean fit with fewer cuts always scores higher than the same area split into many pieces.

## Crumbs & decoration

Every cake cell is worth 1 crumb unit, and crumbs are gathered to decorate the top of the finished napoleon. Decoration is scored just like a layer: 24 (6×4) crumbs = **100%**, with the percentage shown live in the HUD and on the win screen. Decoration is a quality score, not a win requirement — you still win by baking 8 layers.

Crumbs come from two places:

- **Cracked cuts** — cells shed when a cut cracks are kept as crumbs (the "lost N crumb(s)" you see on a crack).
- **Leftover cakes** — when you win, any cakes still in the inventory or work area are swept up into crumbs.

Discarded pieces (dropped on **DISCARD**) are thrown away and do **not** become crumbs. Pieces dropped back on the **inventory bar** are returned to your inventory intact (also not crumbed).

## Controls

- **Left-click + drag** — grab a cake from the inventory or move a piece in the work area.
- **R** — rotate the piece you're dragging (or hovering over) by 90°.
- **Right-click** on a placed piece — unsnap it from the target rectangle.
- **C** (or click "Cut Mode") — toggle cut mode. In cut mode, hover over a piece to preview the cut line, then click to cut. Cuts can crack — watch for the "Cracked!" message and the crumb flash where cells fall off.
- **B** (or click "Bake Layer") — bake the current layer. Allowed at any coverage above 0%; your coverage is recorded per layer, so aim to fill as much as possible.
- **N** (or click "New Game") — start a new game.
- Drop a piece on **DISCARD** to throw it away.
- Drop a piece on the **inventory bar** to return it to your inventory (works for offcuts too).
- **Scroll the inventory** — mouse wheel while hovering the bar, drag the scrollbar thumb, or click its track. The scrollbar appears only when the cakes overflow the bar.

Each inventory slot shows the cake at its real play size, with a label reading its size as `N cells · WxH` (`N` = number of squares, `WxH` = bounding box) so you can tell, say, a 1×1 from a 3×3 at a glance.

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
