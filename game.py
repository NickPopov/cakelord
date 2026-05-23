"""Game state and core operations."""

from typing import List, Optional, Set, Tuple

from config import (
    CAKE_CELLS,
    GRID_CELL,
    LAYERS_NEEDED,
    TARGET_H,
    TARGET_ORIGIN,
    TARGET_W,
    TOTAL_CAKES,
)
from shape import CellCoord, PolyominoShape
from shape_factory import make_cake_shapes


class Mode:
    MOVE = "move"
    CUT = "cut"


class GameState:
    def __init__(self, seed: Optional[int] = None):
        cakes = make_cake_shapes(TOTAL_CAKES, CAKE_CELLS, seed=seed)
        self.inventory: List[PolyominoShape] = cakes
        self.work_pieces: List[PolyominoShape] = []
        self.placed_pieces: List[PolyominoShape] = []
        self.layers_done: int = 0
        self.dragging: Optional[PolyominoShape] = None
        self.drag_offset: Tuple[float, float] = (0.0, 0.0)
        self.mode: str = Mode.MOVE

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

    def is_won(self) -> bool:
        return self.layers_done >= LAYERS_NEEDED

    # ----- Drag lifecycle -----

    def grab_from_inventory(self, idx: int, mouse_x: float, mouse_y: float) -> Optional[PolyominoShape]:
        if idx < 0 or idx >= len(self.inventory):
            return None
        shape = self.inventory.pop(idx)
        cw, ch = shape.cell_dimensions()
        shape.move_to(mouse_x - cw * GRID_CELL / 2, mouse_y - ch * GRID_CELL / 2)
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

    def update_drag(self, mouse_x: float, mouse_y: float) -> None:
        if self.dragging is None:
            return
        dx, dy = self.drag_offset
        self.dragging.move_to(mouse_x + dx, mouse_y + dy)

    def release_drag(self, over_discard: bool) -> None:
        if self.dragging is None:
            return
        shape = self.dragging
        self.dragging = None
        if over_discard:
            if shape in self.work_pieces:
                self.work_pieces.remove(shape)
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

    def try_cut(self, shape: PolyominoShape, point: Tuple[float, float], max_dist: float) -> bool:
        cut = shape.closest_cut(point, max_dist)
        if cut is None:
            return False
        pieces = shape.apply_cut(cut)
        if len(pieces) < 2:
            return False
        nudge_x, nudge_y = 0.0, 0.0
        if cut.direction == "h":
            nudge_y = 6.0
        else:
            nudge_x = 6.0
        in_work = shape in self.work_pieces
        in_placed = shape in self.placed_pieces
        container = self.work_pieces if in_work else (self.placed_pieces if in_placed else None)
        if container is None:
            return False
        idx = container.index(shape)
        # When cutting a placed piece, separation breaks the grid alignment, so
        # demote it to work_pieces (the layer is no longer "sealed" there).
        if in_placed:
            container.pop(idx)
            target_container = self.work_pieces
        else:
            container.pop(idx)
            target_container = container
        from shape import CutDirection
        # First piece stays put; subsequent pieces nudge to remain visible.
        for k, p in enumerate(pieces):
            if k > 0:
                p.move_by(nudge_x * k, nudge_y * k)
            target_container.append(p)
        return True

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
        if not self.is_layer_complete():
            return False
        self.layers_done += 1
        self.placed_pieces.clear()
        return True
