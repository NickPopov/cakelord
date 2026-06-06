"""Generates random connected polyomino cake shapes of a given size."""

import random
from typing import List, Optional, Set, Tuple

from shape import CellCoord, PolyominoShape


def generate_polyomino_cells(n_cells: int, rng: random.Random,
                             max_extent: Optional[int] = None) -> Set[CellCoord]:
    """Grow a connected polyomino of n_cells by adding random neighbors.

    Uses a frontier-set so all candidates have equal chance, avoiding the
    bias of plain random walks (which tend to produce snake shapes)."""
    cells: Set[CellCoord] = {(0, 0)}
    frontier: Set[CellCoord] = {(1, 0), (-1, 0), (0, 1), (0, -1)}
    while len(cells) < n_cells and frontier:
        candidates = list(frontier)
        rng.shuffle(candidates)
        chosen = None
        for c in candidates:
            if max_extent is not None:
                xs = [i for i, _ in cells] + [c[0]]
                ys = [j for _, j in cells] + [c[1]]
                if (max(xs) - min(xs) >= max_extent) or (max(ys) - min(ys) >= max_extent):
                    continue
            chosen = c
            break
        if chosen is None:
            chosen = candidates[0]
        cells.add(chosen)
        frontier.discard(chosen)
        ci, cj = chosen
        for n in ((ci - 1, cj), (ci + 1, cj), (ci, cj - 1), (ci, cj + 1)):
            if n not in cells:
                frontier.add(n)
    return _normalized(cells)


def _normalized(cells: Set[CellCoord]) -> Set[CellCoord]:
    if not cells:
        return cells
    mi = min(i for i, _ in cells)
    mj = min(j for _, j in cells)
    return {(i - mi, j - mj) for (i, j) in cells}


def generate_cakes(count: int, n_cells: int, seed: Optional[int] = None,
                   max_extent: int = 6) -> List[Set[CellCoord]]:
    """Generate `count` polyomino shapes, attempting to avoid duplicates and
    overly rectangular forms."""
    rng = random.Random(seed)
    results: List[Set[CellCoord]] = []
    attempts = 0
    while len(results) < count and attempts < count * 50:
        attempts += 1
        cells = generate_polyomino_cells(n_cells, rng, max_extent=max_extent)
        if _is_perfect_rectangle(cells) and attempts < count * 25:
            continue
        if any(cells == existing for existing in results):
            continue
        results.append(cells)
    while len(results) < count:
        results.append(generate_polyomino_cells(n_cells, rng, max_extent=max_extent))
    return results


def _is_perfect_rectangle(cells: Set[CellCoord]) -> bool:
    if not cells:
        return False
    max_i = max(i for i, _ in cells)
    max_j = max(j for _, j in cells)
    return len(cells) == (max_i + 1) * (max_j + 1)


def make_cake_shapes(count: int, n_cells: int, seed: Optional[int] = None,
                     max_extent: int = 6) -> List[PolyominoShape]:
    cell_sets = generate_cakes(count, n_cells, seed=seed, max_extent=max_extent)
    return [PolyominoShape(cells, 0, 0) for cells in cell_sets]


def make_varied_cake_shapes(count: int, size_min: int, size_max: int,
                            seed: Optional[int] = None,
                            max_extent: int = 6) -> List[PolyominoShape]:
    """Generate `count` cakes, each with a random size in [size_min, size_max].

    Mirrors generate_cakes' dedup + anti-rectangle behavior, but per-cake so
    sizes can differ. Bigger-than-a-layer cakes are intended (cut/rotate to fit)."""
    rng = random.Random(seed)
    results: List[Set[CellCoord]] = []
    while len(results) < count:
        n_cells = rng.randint(size_min, size_max)
        cells = None
        for attempt in range(50):
            candidate = generate_polyomino_cells(n_cells, rng, max_extent=max_extent)
            if _is_perfect_rectangle(candidate) and attempt < 25:
                continue
            if any(candidate == existing for existing in results):
                continue
            cells = candidate
            break
        if cells is None:
            cells = generate_polyomino_cells(n_cells, rng, max_extent=max_extent)
        results.append(cells)
    return [PolyominoShape(cells, 0, 0) for cells in results]
