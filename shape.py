"""Shape abstraction and PolyominoShape implementation.

The Shape ABC isolates geometry details. Game logic and UI use this interface
only, so swapping in a free-polygon implementation later only touches this file
and shape_factory.py.
"""

import math
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
    """A cut along one contiguous run ("island") where a straight grid line
    crosses the cake, in shape-local cell units.

    A straight line can cross the cake in several disjoint runs when gaps leave
    cake on both sides at separate spans; each run is its own cut, so cutting
    one island leaves the others intact. ``span_lo``..``span_hi`` (inclusive) is
    the run severed:

    HORIZONTAL: the line at j == ``line`` severs each vertical seam
    ``(s, line - 1)`` / ``(s, line)`` for s in the span. VERTICAL: the line at
    i == ``line`` severs each horizontal seam ``(line - 1, s)`` / ``(line, s)``.
    """

    def __init__(self, direction: str, line: int, span_lo: int, span_hi: int):
        self.direction = direction
        self.line = line
        self.span_lo = span_lo
        self.span_hi = span_hi

    def severed_pairs(self) -> List[Tuple[CellCoord, CellCoord]]:
        """Every adjacent cell pair whose shared edge this cut severs."""
        pairs: List[Tuple[CellCoord, CellCoord]] = []
        for s in range(self.span_lo, self.span_hi + 1):
            if self.direction == CutDirection.HORIZONTAL:
                pairs.append(((s, self.line - 1), (s, self.line)))
            else:
                pairs.append(((self.line - 1, s), (self.line, s)))
        return pairs


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
        """One cut per island: each maximal contiguous run where a grid line
        crosses the cake (cake present on both sides of the line at that span)."""
        cuts: List[Cut] = []
        if not self.cells:
            return cuts
        i_values = {i for i, _ in self.cells}
        j_values = {j for _, j in self.cells}
        for line in range(min(j_values) + 1, max(j_values) + 1):
            crossable = sorted(
                i for (i, j) in self.cells if j == line and (i, line - 1) in self.cells
            )
            for lo, hi in _contiguous_runs(crossable):
                cuts.append(Cut(CutDirection.HORIZONTAL, line, lo, hi))
        for line in range(min(i_values) + 1, max(i_values) + 1):
            crossable = sorted(
                j for (i, j) in self.cells if i == line and (line - 1, j) in self.cells
            )
            for lo, hi in _contiguous_runs(crossable):
                cuts.append(Cut(CutDirection.VERTICAL, line, lo, hi))
        return cuts

    def cut_hint_segment(self, cut: Cut) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """The segment drawn for ``cut`` — spans only the island being cut."""
        if cut.direction == CutDirection.HORIZONTAL:
            y = self.world_y + cut.line * GRID_CELL
            x1 = self.world_x + cut.span_lo * GRID_CELL
            x2 = self.world_x + (cut.span_hi + 1) * GRID_CELL
            return ((x1, y), (x2, y))
        x = self.world_x + cut.line * GRID_CELL
        y1 = self.world_y + cut.span_lo * GRID_CELL
        y2 = self.world_y + (cut.span_hi + 1) * GRID_CELL
        return ((x, y1), (x, y2))

    def closest_cut(self, point: Tuple[float, float], max_dist: float) -> Optional[Cut]:
        """Find the island whose segment is closest to ``point`` (within max_dist px)."""
        best: Optional[Cut] = None
        best_d = max_dist
        for cut in self.candidate_cuts():
            a, b = self.cut_hint_segment(cut)
            d = _point_segment_dist(point, a, b)
            if d < best_d:
                best_d = d
                best = cut
        return best

    def widen_cut_to_separate(self, cut: Cut) -> Optional[Cut]:
        """Grow ``cut``'s span outward — adding the nearest island each step
        (gaps between have no seam, so they sever nothing) — until the cut
        actually divides the cake, then stop. Returns the minimal widened cut,
        or ``None`` if no extent along this line can separate it."""
        if cut.direction == CutDirection.HORIZONTAL:
            crossable = sorted(
                i for (i, j) in self.cells if j == cut.line and (i, cut.line - 1) in self.cells
            )
        else:
            crossable = sorted(
                j for (i, j) in self.cells if i == cut.line and (cut.line - 1, j) in self.cells
            )
        lo, hi = cut.span_lo, cut.span_hi
        while True:
            candidate = Cut(cut.direction, cut.line, lo, hi)
            if len(self.apply_cut(candidate)) >= 2:
                return candidate
            below = [s for s in crossable if s < lo]
            above = [s for s in crossable if s > hi]
            if not below and not above:
                return None
            # Add whichever neighbouring island is closer to the current span.
            if below and (not above or (lo - below[-1]) <= (above[0] - hi)):
                lo = below[-1]
            else:
                hi = above[0]

    def cut_at(self, point: Tuple[float, float], max_dist: float) -> Optional[Cut]:
        """The cut a click performs: the nearest island, but minimally widened
        (toward the nearest island) when cutting that island alone wouldn't
        divide the cake — e.g. a ring loops around the gap, so one island isn't
        enough but the donut still splits in one click without disturbing
        unrelated islands further along the line."""
        cut = self.closest_cut(point, max_dist)
        if cut is None:
            return None
        if len(self.apply_cut(cut)) < 2:
            widened = self.widen_cut_to_separate(cut)
            if widened is not None:
                return widened
        return cut

    def apply_cut(self, cut: Cut) -> List["PolyominoShape"]:
        """Sever every seam in the cut island and re-split into connected
        components. Other islands on the same line stay intact, so this yields
        more than one piece only if cutting this island disconnects the cake."""
        broken = {frozenset(p) for p in cut.severed_pairs()}
        pieces: List[PolyominoShape] = []
        for comp in _connected_components(self.cells, broken_edges=broken):
            if comp:
                pieces.append(PolyominoShape(comp, self.world_x, self.world_y))
        return pieces

    def apply_broken_cut(
        self,
        cut: Cut,
        rng,
        jaggedness: int,
        crumb_chance: float,
        crumb_max: int,
    ) -> Tuple[List["PolyominoShape"], List[CellCoord]]:
        """Cracked variant of a single-seam cut: sever the seam, then shed a few
        cells off the fragile (smaller) offcut as crumbs.

        Returns (pieces, lost_cells). lost_cells are in shape-local coordinates.
        ``jaggedness`` widens how far from the seam crumbs may chip away. If the
        island doesn't separate the shape into at least 2 pieces, returns ([], [])
        so the caller can fall back to a clean cut.
        """
        broken = {frozenset(p) for p in cut.severed_pairs()}
        comps = [c for c in _connected_components(self.cells, broken_edges=broken) if c]
        if len(comps) < 2:
            return [], []

        # The smaller offcut is the fragile part the crumbs chip away from. Keep
        # at least one cell so the cut still yields a real piece, never dust.
        comps.sort(key=len)
        lost: List[CellCoord] = []
        if crumb_max > 0 and rng.random() < crumb_chance:
            small = comps[0]
            seam_cells = {c for pair in cut.severed_pairs() for c in pair if c in small}
            # Chip cells nearest the severed seam first, within the jagged reach.
            reach = max(1, jaggedness)
            near = [
                c for c in small
                if any(abs(c[0] - s[0]) + abs(c[1] - s[1]) <= reach for s in seam_cells)
            ]
            rng.shuffle(near)
            budget = min(crumb_max, len(small) - 1)
            for cell in near[:budget]:
                lost.append(cell)
                small.discard(cell)

        pieces: List[PolyominoShape] = []
        for comp in comps:
            for sub in _connected_components(comp):
                if sub:
                    pieces.append(PolyominoShape(sub, self.world_x, self.world_y))
        if len(pieces) < 2:
            return [], []
        return pieces, lost

    def rotate(self, clockwise: bool = True) -> None:
        """Rotate cells 90 degrees and re-normalize so min i/j = 0.

        World position is unchanged here; callers that want to keep the piece
        centered (e.g. under the cursor) adjust world position afterwards."""
        if not self.cells:
            return
        if clockwise:
            rotated = {(j, -i) for (i, j) in self.cells}
        else:
            rotated = {(-j, i) for (i, j) in self.cells}
        mi = min(i for i, _ in rotated)
        mj = min(j for _, j in rotated)
        self.cells = {(i - mi, j - mj) for (i, j) in rotated}

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


def _point_segment_dist(
    p: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]
) -> float:
    """Shortest distance from point ``p`` to segment ``a``-``b``."""
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def _contiguous_runs(values: List[int]) -> List[Tuple[int, int]]:
    """Maximal runs of consecutive integers in a sorted list, as (lo, hi)."""
    runs: List[List[int]] = []
    for v in values:
        if runs and v == runs[-1][1] + 1:
            runs[-1][1] = v
        else:
            runs.append([v, v])
    return [(lo, hi) for lo, hi in runs]


def _connected_components(
    cells: Set[CellCoord],
    broken_edges: Optional[Set[frozenset]] = None,
) -> List[Set[CellCoord]]:
    """Connected components under 4-adjacency. Any cell pair in ``broken_edges``
    (each a ``frozenset`` of two cells) is treated as not adjacent (severed)."""
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
                    if broken_edges and frozenset((c, n)) in broken_edges:
                        continue  # severed seam: don't traverse this edge
                    stack.append(n)
        components.append(comp)
    return components
