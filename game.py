"""Game state and core operations."""

import random
from typing import List, NamedTuple, Optional, Set, Tuple

from config import (
    BREAK_CHANCE_LARGE,
    BREAK_CHANCE_SMALL,
    BREAK_CRUMB_CHANCE,
    BREAK_CRUMB_MAX,
    BREAK_JAGGEDNESS,
    BREAK_LARGE_SIZE,
    BREAK_SMALL_SIZE,
    CAKE_SIZE_MAX,
    CAKE_SIZE_MIN,
    CRUMB_GOAL,
    GRID_CELL,
    LAYERS_NEEDED,
    TARGET_H,
    TARGET_ORIGIN,
    TARGET_W,
    TOTAL_CAKES,
)
from shape import CellCoord, PolyominoShape
from shape_factory import make_varied_cake_shapes


class Mode:
    MOVE = "move"
    CUT = "cut"


class CutOutcome(NamedTuple):
    """Result of a cut attempt. ``crumb_world_cells`` are (x, y) top-left pixel
    positions of cells lost as crumbs, for transient UI feedback."""

    success: bool
    broke: bool = False
    crumbs_lost: int = 0
    crumb_world_cells: Tuple[Tuple[float, float], ...] = ()


class GameState:
    def __init__(self, seed: Optional[int] = None):
        cakes = make_varied_cake_shapes(TOTAL_CAKES, CAKE_SIZE_MIN, CAKE_SIZE_MAX, seed=seed)
        self.inventory: List[PolyominoShape] = cakes
        self.work_pieces: List[PolyominoShape] = []
        self.placed_pieces: List[PolyominoShape] = []
        self.layers_done: int = 0
        self.layer_coverages: List[float] = []
        self.dragging: Optional[PolyominoShape] = None
        self.drag_offset: Tuple[float, float] = (0.0, 0.0)
        self.mode: str = Mode.MOVE
        self.rng = random.Random(seed)
        self.crumbs: int = 0

    def toggle_mode(self) -> None:
        self.mode = Mode.CUT if self.mode == Mode.MOVE else Mode.MOVE

    @property
    def target_cells(self) -> Set[CellCoord]:
        return {(i, j) for i in range(TARGET_W) for j in range(TARGET_H)}

    def placed_cells(self) -> Set[CellCoord]:
        result: Set[CellCoord] = set()
        for piece in self.placed_pieces:
            result.update(piece.cells_in_target(TARGET_ORIGIN))
        return result

    def is_layer_complete(self) -> bool:
        return self.placed_cells() == self.target_cells

    def coverage_fraction(self) -> float:
        return len(self.placed_cells()) / len(self.target_cells)

    @staticmethod
    def _perimeter(cells: Set[CellCoord]) -> int:
        """Edge count of a polyomino: 4 per cell minus shared inner edges."""
        perim = 0
        for (i, j) in cells:
            for ni, nj in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if (ni, nj) not in cells:
                    perim += 1
        return perim

    def seam_penalty_percent(self) -> float:
        """Cost of cutting the layer into pieces, independent of placement.

        Each piece's own perimeter is intrinsic to its shape, so cutting a
        single cake into more pieces adds total edge length wherever the
        pieces are dropped. The penalty is that extra edge over an uncut
        layer (the target's perimeter), at 1% per edge: a lone 6x4 cake has
        perimeter 20 -> no penalty -> 100%, while two 3x4 pieces total 28
        -> 8 extra edges -> 8% -> 92%.
        """
        total = sum(self._perimeter(p.cells) for p in self.placed_pieces)
        target_perimeter = 2 * (TARGET_W + TARGET_H)
        return float(max(0, total - target_perimeter))

    def coverage_percent(self) -> float:
        return max(0.0, 100.0 * self.coverage_fraction() - self.seam_penalty_percent())

    def can_bake(self) -> bool:
        return len(self.placed_cells()) > 0

    def average_coverage(self) -> float:
        if not self.layer_coverages:
            return 0.0
        return sum(self.layer_coverages) / len(self.layer_coverages)

    def is_won(self) -> bool:
        return self.layers_done >= LAYERS_NEEDED

    def decoration_coverage_percent(self) -> float:
        return 100.0 * min(self.crumbs, CRUMB_GOAL) / CRUMB_GOAL

    # ----- Drag lifecycle -----

    def grab_from_inventory(self, idx: int, mouse_x: float, mouse_y: float) -> Optional[PolyominoShape]:
        if idx < 0 or idx >= len(self.inventory):
            return None
        shape = self.inventory.pop(idx)
        # Center the piece's bounding box on the cursor. Using the bounding box
        # (rather than cell_dimensions from the local origin) keeps offcuts whose
        # cells don't start at (0,0) centered, instead of biased to one side.
        shape.move_to(mouse_x, mouse_y)
        bb = shape.bounding_box()
        shape.move_by(mouse_x - bb.centerx, mouse_y - bb.centery)
        self.work_pieces.append(shape)
        self.dragging = shape
        self.drag_offset = (shape.world_x - mouse_x, shape.world_y - mouse_y)
        return shape

    def grab_work_piece(self, shape: PolyominoShape, mouse_x: float, mouse_y: float) -> None:
        self.dragging = shape
        self.drag_offset = (shape.world_x - mouse_x, shape.world_y - mouse_y)
        if shape in self.work_pieces:
            self.work_pieces.remove(shape)
            self.work_pieces.append(shape)

    def grab_placed_piece(self, shape: PolyominoShape, mouse_x: float, mouse_y: float) -> None:
        if shape in self.placed_pieces:
            self.placed_pieces.remove(shape)
            self.work_pieces.append(shape)
        self.grab_work_piece(shape, mouse_x, mouse_y)

    def return_to_inventory(self, shape: PolyominoShape) -> None:
        """Send a placed or free-floating piece back to the inventory as a draggable cake."""
        if shape is self.dragging:
            self.dragging = None
        if shape in self.placed_pieces:
            self.placed_pieces.remove(shape)
            self.inventory.append(shape)
        elif shape in self.work_pieces:
            self.work_pieces.remove(shape)
            self.inventory.append(shape)

    def update_drag(self, mouse_x: float, mouse_y: float) -> None:
        if self.dragging is None:
            return
        dx, dy = self.drag_offset
        self.dragging.move_to(mouse_x + dx, mouse_y + dy)

    # ----- Rotation / Flip -----

    @staticmethod
    def _transform_keeping_center(shape: PolyominoShape, transform: str) -> None:
        bb = shape.bounding_box()
        cx, cy = bb.center
        if transform == "rotate":
            shape.rotate(clockwise=True)
        else:
            shape.flip()
        nb = shape.bounding_box()
        shape.move_by(cx - nb.centerx, cy - nb.centery)

    def _transform_dragging(self, transform: str, mouse_x: float, mouse_y: float) -> None:
        if self.dragging is None:
            return
        self._transform_keeping_center(self.dragging, transform)
        self.drag_offset = (self.dragging.world_x - mouse_x, self.dragging.world_y - mouse_y)

    def _transform_under_cursor(self, transform: str, point: Tuple[float, float]) -> None:
        shape = self.find_shape_at(point)
        if shape is None:
            return
        prev_cells = set(shape.cells)
        prev_pos = (shape.world_x, shape.world_y)
        self._transform_keeping_center(shape, transform)
        if shape in self.placed_pieces:
            snapped = shape.snapped_position(TARGET_ORIGIN)
            shape.move_to(*snapped)
            cells = shape.cells_in_target(TARGET_ORIGIN)
            others = self.placed_cells() - shape.cells_in_target(TARGET_ORIGIN)
            within = cells <= self.target_cells
            no_overlap = cells.isdisjoint(others)
            if not (within and no_overlap):
                shape.cells = prev_cells
                shape.move_to(*prev_pos)

    def rotate_dragging(self, mouse_x: float, mouse_y: float) -> None:
        self._transform_dragging("rotate", mouse_x, mouse_y)

    def rotate_under_cursor(self, point: Tuple[float, float]) -> None:
        self._transform_under_cursor("rotate", point)

    def flip_dragging(self, mouse_x: float, mouse_y: float) -> None:
        self._transform_dragging("flip", mouse_x, mouse_y)

    def flip_under_cursor(self, point: Tuple[float, float]) -> None:
        self._transform_under_cursor("flip", point)

    def release_drag(self, over_inventory: bool = False) -> None:
        if self.dragging is None:
            return
        shape = self.dragging
        self.dragging = None
        if over_inventory:
            if shape in self.work_pieces:
                self.work_pieces.remove(shape)
                self.inventory.append(shape)
            return
        snapped = shape.snapped_position(TARGET_ORIGIN)
        prev = (shape.world_x, shape.world_y)
        shape.move_to(*snapped)
        cells = shape.cells_in_target(TARGET_ORIGIN)
        within_target = cells <= self.target_cells
        no_overlap = cells.isdisjoint(self.placed_cells())
        if within_target and no_overlap:
            if shape in self.work_pieces:
                self.work_pieces.remove(shape)
            self.placed_pieces.append(shape)
        else:
            shape.move_to(*prev)

    # ----- Cut -----

    @staticmethod
    def break_chance(n_cells: int) -> float:
        """Probability that a cut of a piece with ``n_cells`` cells cracks.
        Lerp between the small/large anchors; smaller pieces are more fragile."""
        if n_cells <= BREAK_SMALL_SIZE:
            return BREAK_CHANCE_SMALL
        if n_cells >= BREAK_LARGE_SIZE:
            return BREAK_CHANCE_LARGE
        t = (n_cells - BREAK_SMALL_SIZE) / (BREAK_LARGE_SIZE - BREAK_SMALL_SIZE)
        return BREAK_CHANCE_SMALL + t * (BREAK_CHANCE_LARGE - BREAK_CHANCE_SMALL)

    def try_cut(self, shape: PolyominoShape, point: Tuple[float, float], max_dist: float) -> CutOutcome:
        cut = shape.cut_at(point, max_dist)
        if cut is None:
            return CutOutcome(success=False)

        broke = self.rng.random() < self.break_chance(len(shape.cells))
        crumb_world_cells: Tuple[Tuple[float, float], ...] = ()
        pieces: List[PolyominoShape] = []
        if broke:
            pieces, lost = shape.apply_broken_cut(
                cut, self.rng, BREAK_JAGGEDNESS, BREAK_CRUMB_CHANCE, BREAK_CRUMB_MAX
            )
            crumb_world_cells = tuple(
                (shape.world_x + i * GRID_CELL, shape.world_y + j * GRID_CELL)
                for (i, j) in lost
            )
        if not pieces:  # not broken, or the crack collapsed -> clean fallback
            broke = False
            crumb_world_cells = ()
            pieces = shape.apply_cut(cut)
        if len(pieces) < 2:
            return CutOutcome(success=False)

        nudge_x, nudge_y = 0.0, 0.0
        if cut.direction == "h":
            nudge_y = 6.0
        else:
            nudge_x = 6.0
        in_work = shape in self.work_pieces
        in_placed = shape in self.placed_pieces
        container = self.work_pieces if in_work else (self.placed_pieces if in_placed else None)
        if container is None:
            return CutOutcome(success=False)
        idx = container.index(shape)
        # When cutting a placed piece, separation breaks the grid alignment, so
        # demote it to work_pieces (the layer is no longer "sealed" there).
        if in_placed:
            container.pop(idx)
            target_container = self.work_pieces
        else:
            container.pop(idx)
            target_container = container
        # First piece stays put; subsequent pieces nudge to remain visible.
        for k, p in enumerate(pieces):
            if k > 0:
                p.move_by(nudge_x * k, nudge_y * k)
            target_container.append(p)
        crumbs_lost = len(crumb_world_cells)
        self.crumbs += crumbs_lost
        # A "crack" the player can't see (a break that shed no crumbs) is
        # indistinguishable from a clean cut, so don't report it as one.
        return CutOutcome(
            success=True,
            broke=crumbs_lost > 0,
            crumbs_lost=crumbs_lost,
            crumb_world_cells=crumb_world_cells,
        )

    # ----- Lookup -----

    def find_shape_at(self, point: Tuple[float, float]) -> Optional[PolyominoShape]:
        for shape in reversed(self.work_pieces):
            if shape.contains_point(point):
                return shape
        for shape in reversed(self.placed_pieces):
            if shape.contains_point(point):
                return shape
        return None

    # ----- Layer baking -----

    def bake_layer(self) -> bool:
        if not self.can_bake():
            return False
        self.layer_coverages.append(self.coverage_percent())
        self.layers_done += 1
        self.placed_pieces.clear()
        if self.is_won():
            # Unused cakes are swept up as crumbs for the final decoration.
            for piece in self.inventory:
                self.crumbs += len(piece.cells)
            for piece in self.work_pieces:
                self.crumbs += len(piece.cells)
            self.inventory.clear()
            self.work_pieces.clear()
        return True
