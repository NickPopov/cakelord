"""Shape abstraction and PolyominoShape implementation.

The Shape ABC isolates geometry details. Game logic and UI use this interface
only, so swapping in a free-polygon implementation later only touches this file
and shape_factory.py.
"""

from abc import ABC, abstractmethod
from typing import Iterable, List, Optional, Set, Tuple

import pygame

from config import (
    COLOR_CAKE_BORDER,
    COLOR_CAKE_FILL,
    COLOR_CAKE_HOVER,
    COLOR_CUT_VALID,
    COLOR_PLACED_FILL,
    GRID_CELL,
)

CellCoord = Tuple[int, int]


class CutDirection:
    HORIZONTAL = "h"
    VERTICAL = "v"


class Cut:
    """A straight axis-aligned cut across a shape, in shape-local cell units.

    For HORIZONTAL: ``line`` is the j-index — separates cells with j < line
    from cells with j >= line. For VERTICAL: same but for i-index.
    """

    def __init__(self, direction: str, line: int):
        self.direction = direction
        self.line = line


class Shape(ABC):
    @abstractmethod
    def render(self, surface: pygame.Surface, override_color=None) -> None: ...

    @abstractmethod
    def contains_point(self, point: Tuple[float, float]) -> bool: ...

    @abstractmethod
    def bounding_box(self) -> pygame.Rect: ...

    @abstractmethod
    def candidate_cuts(self) -> List[Cut]: ...

    @abstractmethod
    def cut_hint_segment(self, cut: Cut) -> Tuple[Tuple[float, float], Tuple[float, float]]: ...

    @abstractmethod
    def apply_cut(self, cut: Cut) -> List["Shape"]: ...

    @abstractmethod
    def move_by(self, dx: float, dy: float) -> None: ...

    @abstractmethod
    def move_to(self, x: float, y: float) -> None: ...


class PolyominoShape(Shape):
    """A connected set of unit cells. World position is the screen pixel where
    the shape's local-frame origin (cell (0, 0) if present) is drawn."""

    def __init__(self, cells: Iterable[CellCoord], world_x: float, world_y: float):
        self.cells: Set[CellCoord] = set(cells)
        self.world_x = float(world_x)
        self.world_y = float(world_y)

    @property
    def position(self) -> Tuple[float, float]:
        return (self.world_x, self.world_y)

    def render(self, surface: pygame.Surface, override_color=None) -> None:
        fill = override_color if override_color is not None else COLOR_CAKE_FILL
        for (i, j) in self.cells:
            x = self.world_x + i * GRID_CELL
            y = self.world_y + j * GRID_CELL
            pygame.draw.rect(surface, fill, (x, y, GRID_CELL, GRID_CELL))
        for (i, j) in self.cells:
            x = self.world_x + i * GRID_CELL
            y = self.world_y + j * GRID_CELL
            if (i, j - 1) not in self.cells:
                pygame.draw.line(surface, COLOR_CAKE_BORDER, (x, y), (x + GRID_CELL, y), 2)
            if (i, j + 1) not in self.cells:
                pygame.draw.line(
                    surface, COLOR_CAKE_BORDER, (x, y + GRID_CELL), (x + GRID_CELL, y + GRID_CELL), 2
                )
            if (i - 1, j) not in self.cells:
                pygame.draw.line(surface, COLOR_CAKE_BORDER, (x, y), (x, y + GRID_CELL), 2)
            if (i + 1, j) not in self.cells:
                pygame.draw.line(
                    surface, COLOR_CAKE_BORDER, (x + GRID_CELL, y), (x + GRID_CELL, y + GRID_CELL), 2
                )

    def render_at(self, surface: pygame.Surface, top_left: Tuple[float, float],
                  cell_size: int, override_color=None) -> None:
        """Render at given top-left pixel, with arbitrary cell size (for inventory thumbnails)."""
        if not self.cells:
            return
        fill = override_color if override_color is not None else COLOR_CAKE_FILL
        min_i = min(i for i, _ in self.cells)
        min_j = min(j for _, j in self.cells)
        ox, oy = top_left
        for (i, j) in self.cells:
            x = ox + (i - min_i) * cell_size
            y = oy + (j - min_j) * cell_size
            pygame.draw.rect(surface, fill, (x, y, cell_size, cell_size))
        for (i, j) in self.cells:
            x = ox + (i - min_i) * cell_size
            y = oy + (j - min_j) * cell_size
            if (i, j - 1) not in self.cells:
                pygame.draw.line(surface, COLOR_CAKE_BORDER, (x, y), (x + cell_size, y), 2)
            if (i, j + 1) not in self.cells:
                pygame.draw.line(
                    surface, COLOR_CAKE_BORDER, (x, y + cell_size), (x + cell_size, y + cell_size), 2
                )
            if (i - 1, j) not in self.cells:
                pygame.draw.line(surface, COLOR_CAKE_BORDER, (x, y), (x, y + cell_size), 2)
            if (i + 1, j) not in self.cells:
                pygame.draw.line(
                    surface, COLOR_CAKE_BORDER, (x + cell_size, y), (x + cell_size, y + cell_size), 2
                )

    def contains_point(self, point: Tuple[float, float]) -> bool:
        px, py = point
        lx = (px - self.world_x) / GRID_CELL
        ly = (py - self.world_y) / GRID_CELL
        ci = int(lx) if lx >= 0 else int(lx) - 1
        cj = int(ly) if ly >= 0 else int(ly) - 1
        return (ci, cj) in self.cells

    def bounding_box(self) -> pygame.Rect:
        if not self.cells:
            return pygame.Rect(int(self.world_x), int(self.world_y), 0, 0)
        min_i = min(i for i, _ in self.cells)
        max_i = max(i for i, _ in self.cells)
        min_j = min(j for _, j in self.cells)
        max_j = max(j for _, j in self.cells)
        return pygame.Rect(
            int(self.world_x + min_i * GRID_CELL),
            int(self.world_y + min_j * GRID_CELL),
            (max_i - min_i + 1) * GRID_CELL,
            (max_j - min_j + 1) * GRID_CELL,
        )

    def cell_dimensions(self) -> Tuple[int, int]:
        if not self.cells:
            return (0, 0)
        min_i = min(i for i, _ in self.cells)
        max_i = max(i for i, _ in self.cells)
        min_j = min(j for _, j in self.cells)
        max_j = max(j for _, j in self.cells)
        return (max_i - min_i + 1, max_j - min_j + 1)

    def candidate_cuts(self) -> List[Cut]:
        if not self.cells:
            return []
        i_values = {i for i, _ in self.cells}
        j_values = {j for _, j in self.cells}
        cuts: List[Cut] = []
        for J in range(min(j_values) + 1, max(j_values) + 1):
            if any(j < J for j in j_values) and any(j >= J for j in j_values):
                cuts.append(Cut(CutDirection.HORIZONTAL, J))
        for I in range(min(i_values) + 1, max(i_values) + 1):
            if any(i < I for i in i_values) and any(i >= I for i in i_values):
                cuts.append(Cut(CutDirection.VERTICAL, I))
        return cuts

    def cut_hint_segment(self, cut: Cut) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        bb = self.bounding_box()
        if cut.direction == CutDirection.HORIZONTAL:
            y = self.world_y + cut.line * GRID_CELL
            return ((bb.left, y), (bb.right, y))
        x = self.world_x + cut.line * GRID_CELL
        return ((x, bb.top), (x, bb.bottom))

    def closest_cut(self, point: Tuple[float, float], max_dist: float) -> Optional[Cut]:
        """Find the cut whose line is closest to ``point`` (within max_dist px)."""
        best: Optional[Cut] = None
        best_d = max_dist
        px, py = point
        for cut in self.candidate_cuts():
            (x1, y1), (x2, y2) = self.cut_hint_segment(cut)
            if cut.direction == CutDirection.HORIZONTAL:
                if x1 <= px <= x2:
                    d = abs(py - y1)
                else:
                    continue
            else:
                if y1 <= py <= y2:
                    d = abs(px - x1)
                else:
                    continue
            if d < best_d:
                best_d = d
                best = cut
        return best

    def apply_cut(self, cut: Cut) -> List["PolyominoShape"]:
        if cut.direction == CutDirection.HORIZONTAL:
            side_a = {(i, j) for i, j in self.cells if j < cut.line}
            side_b = {(i, j) for i, j in self.cells if j >= cut.line}
        else:
            side_a = {(i, j) for i, j in self.cells if i < cut.line}
            side_b = {(i, j) for i, j in self.cells if i >= cut.line}

        pieces: List[PolyominoShape] = []
        for group in (side_a, side_b):
            for comp in _connected_components(group):
                if comp:
                    pieces.append(PolyominoShape(comp, self.world_x, self.world_y))
        return pieces

    def move_by(self, dx: float, dy: float) -> None:
        self.world_x += dx
        self.world_y += dy

    def move_to(self, x: float, y: float) -> None:
        self.world_x = float(x)
        self.world_y = float(y)

    def snapped_position(self, target_origin: Tuple[float, float]) -> Tuple[float, float]:
        tx, ty = target_origin
        gx = round((self.world_x - tx) / GRID_CELL)
        gy = round((self.world_y - ty) / GRID_CELL)
        return (tx + gx * GRID_CELL, ty + gy * GRID_CELL)

    def cells_in_target(self, target_origin: Tuple[float, float]) -> Set[CellCoord]:
        """Given current world position, return the cells the shape would
        occupy in the target rectangle's coordinate frame."""
        tx, ty = target_origin
        gx = round((self.world_x - tx) / GRID_CELL)
        gy = round((self.world_y - ty) / GRID_CELL)
        return {(i + gx, j + gy) for (i, j) in self.cells}


def _connected_components(cells: Set[CellCoord]) -> List[Set[CellCoord]]:
    remaining = set(cells)
    components: List[Set[CellCoord]] = []
    while remaining:
        start = next(iter(remaining))
        comp: Set[CellCoord] = set()
        stack = [start]
        while stack:
            c = stack.pop()
            if c in comp or c not in remaining:
                continue
            comp.add(c)
            remaining.discard(c)
            i, j = c
            for n in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
                if n in remaining:
                    stack.append(n)
        components.append(comp)
    return components
