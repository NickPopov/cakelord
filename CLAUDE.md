# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Napoleon Cake Builder: a single-player puzzle game written in pure Python with **pygame-ce**, compiled to WebAssembly via **pygbag** to run in the browser. You drag irregular polyomino "cakes" from an inventory, optionally cut/rotate them, and fit them into a 6×4 target rectangle to "bake" layers — 8 layers wins. Cuts are risky: a cut can **crack**, producing an uneven (jagged) split and sometimes shedding cells as lost crumbs; smaller pieces are more fragile. Those crumbs aren't wasted — they accumulate into a **crumbs resource** (1 cake cell = 1 unit) used to decorate the napoleon top, a placement-independent quality score shown in the HUD and on the win screen but **not** a win gate.

## Commands

The system `python` is **not** pygame-capable. Use the project virtualenv interpreter at `.venv/bin/python` (Python 3.13, pygame-ce 2.5).

```bash
.venv/bin/python main.py                 # run the game locally (opens a window)
pip install -r requirements.txt          # (re)install deps into the active env
pygbag main.py                           # serve in browser at http://localhost:8000
pygbag --build main.py                   # static web build -> build/web/
```

There is **no test suite**. Verify changes with quick scripts against the venv interpreter:

```bash
# compile-check every module
.venv/bin/python -c "import py_compile,glob; [py_compile.compile(f,doraise=True) for f in glob.glob('*.py')]; print('OK')"

# exercise game logic headlessly (no display/audio)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -c "import pygame; pygame.init(); pygame.display.set_mode((1024,768)); from scene import PlayScene; PlayScene(seed=1).render(pygame.display.get_surface()); print('render OK')"
```

`GameState(seed=...)` makes generation **and** cut breaking deterministic — pass a seed in tests. Generation uses its own seeded RNG; `GameState.rng` (a separate `random.Random(seed)`) drives break rolls, jagged seams, and crumb loss.

## Architecture

The render/update loop lives in `main.py` (async, required by pygbag) and is intentionally thin: it pumps events into the active scene, calls `scene.render`, and swaps scenes based on `scene.next_scene` (`"win"` / `"play"`). All real logic is below it.

**Scene layer (`scene.py`)** — `PlayScene` owns one `GameState` plus stateless UI widgets, translating pygame events into `GameState` method calls and drawing everything each frame. `WinScene` is the victory screen. Scenes never mutate shape geometry directly; they go through `GameState`.

**State layer (`game.py`)** — `GameState` is the single source of truth. Cakes flow through three lists: `inventory` (uncut cakes) → `work_pieces` (grabbed/cut, free-floating) → `placed_pieces` (snapped into the target). Key invariants enforced here:
- Placement (`release_drag`) snaps to the grid and only accepts a piece if its cells stay within the 6×4 target **and** don't overlap already-placed cells.
- Coverage is tracked, not required: `bake_layer` succeeds at any coverage > 0, appends `coverage_percent()` to in-session `layer_coverages`, and clears `placed_pieces`. Win = `layers_done >= LAYERS_NEEDED`. On the winning bake, `bake_layer` also sweeps every remaining `inventory`/`work_pieces` cake into crumbs (`+= len(cells)`) and clears those lists, so leftovers count toward decoration.
- Crumbs are a running integer resource (`GameState.crumbs`, reset per game). It rises from two sources: cells shed by a cracked cut (`try_cut` adds `crumbs_lost`) and the leftover sweep at win. `release_drag`'s DISCARD path is **not** a source — discarded pieces are thrown away, not crumbed. `decoration_coverage_percent()` = `100 * min(crumbs, CRUMB_GOAL) / CRUMB_GOAL` (`CRUMB_GOAL = 24`), mirroring per-layer coverage and likewise placement-independent. It's a score only; don't gate `is_won()` on it.
- `coverage_percent()` = `100 * coverage_fraction()` (filled cells / 24) **minus** `seam_penalty_percent()`, clamped at 0. The penalty is a **cutting cost** that is deliberately *placement-independent*: it sums each piece's own perimeter (`_perimeter`, an intrinsic property of its `cells`) and charges 1% per edge exceeding an uncut layer's perimeter (`2*(TARGET_W+TARGET_H)`). So one 6×4 cake = 100%, two 3×4 pieces = 92% (28 − 20 = 8 extra edges), and rearranging the same pieces never changes the score — only how they were cut does. Empty space lowers coverage separately, via the filled-cell fraction. Don't reintroduce adjacency/seam-touch logic here; that made coverage depend on position.
- All target-frame math keys off `TARGET_ORIGIN` and `GRID_CELL`; a piece's `cells_in_target()` converts its world pixel position into target grid coordinates.
- Cutting (`try_cut`) rolls `GameState.rng.random() < break_chance(len(shape.cells))` — `break_chance` lerps between the small/large size anchors so smaller pieces crack more. On a break it calls `apply_broken_cut`; if the crack collapses to <2 pieces it falls back to a clean `apply_cut`, so a cut never silently no-ops. It returns a `CutOutcome` namedtuple (`success`, `broke`, `crumbs_lost`, `crumb_world_cells`) that `PlayScene` turns into the transient "Cracked!" message and crumb flash.

**Geometry layer (`shape.py`)** — `Shape` is an ABC that isolates geometry from everything above; only `PolyominoShape` (a `set` of `(i,j)` cells + a world pixel origin) is implemented. This boundary is deliberate: a `PolygonShape` could be added without touching the game loop, scenes, or `GameState`. `PolyominoShape` handles rendering, hit-testing, snapping, rotation (90° with caller-side re-centering), and cutting. `apply_cut` splits along an axis line and re-splits into connected components, so one cut can yield >2 pieces. `apply_broken_cut` is the cracked variant: the seam wanders via a bounded random walk (perpendicular to the split axis) for an uneven split, then optionally drops a few boundary cells as crumbs; it returns `(pieces, lost_cells)` and `([], [])` if the crack fails to yield ≥2 pieces. `apply_cut` is kept clean/lossless as both the ABC method and the no-break/fallback path.

**Generation (`shape_factory.py`)** — `make_varied_cake_shapes` grows each cake via a frontier-set random walk (`generate_polyomino_cells`) at a random size in `[CAKE_SIZE_MIN, CAKE_SIZE_MAX]`, de-duplicating and avoiding perfect rectangles. Cakes intentionally vary in size (some larger than a 24-cell layer) so the puzzle requires cutting/rotating.

**Config (`config.py`)** — all tunables (grid/screen dims, cake size range, layer counts, colors, widget rects) live here as module constants; there is no config file or env-var layer. The cake-breaking knobs (`BREAK_*` size anchors/chances, `BREAK_JAGGEDNESS`, crumb chance/max, `COLOR_CRUMB`, `CRUMB_FLASH_MS`, `CUT_MESSAGE_MS`) are the tuning surface for difficulty — always-on numeric values, not on/off toggles. `CRUMB_GOAL` (= `TARGET_W*TARGET_H`) sets how many crumbs fully decorate the napoleon top; `COLOR_DECOR` is its HUD readout color.

## Conventions

- Cell coordinates are `(i, j)` = `(column, row)`; world coordinates are screen pixels of the shape's local `(0,0)` cell. Don't conflate the two — convert via `GRID_CELL` and `TARGET_ORIGIN`.
- Keep `Shape`'s abstraction intact: game/UI code should use `PolyominoShape` only through the `Shape` interface so the geometry backend stays swappable.
- Controls: **left-drag** move, **R** rotate the active/hovered piece, **right-click** unsnap a placed piece, **C** cut mode (cuts can crack), **B** bake, **N** new game, drop on **DISCARD** to remove.
