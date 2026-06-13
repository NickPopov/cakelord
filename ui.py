"""UI components: target area, inventory bar, stack view, button, help overlay."""

from typing import List, Optional, Tuple

import pygame

from config import (
    COLOR_BUTTON,
    COLOR_BUTTON_HOVER,
    COLOR_BUTTON_TEXT,
    COLOR_GRID,
    COLOR_INVENTORY_BG,
    COLOR_INVENTORY_SLOT,
    COLOR_OVERLAY_BG,
    COLOR_OVERLAY_PANEL,
    COLOR_PANEL_BORDER,
    COLOR_SCROLLBAR_THUMB,
    COLOR_SCROLLBAR_THUMB_HOVER,
    COLOR_SCROLLBAR_TRACK,
    COLOR_STACK_LAYER_DONE,
    COLOR_STACK_LAYER_EMPTY,
    COLOR_TARGET_BG,
    COLOR_TARGET_BORDER,
    COLOR_TEXT,
    GRID_CELL,
    SCREEN_H,
    INVENTORY_MARGIN,
    INVENTORY_PADDING,
    INVENTORY_SCROLLBAR_H,
    INVENTORY_SLOT_H,
    INVENTORY_SLOT_W,
    INVENTORY_WHEEL_STEP,
    INVENTORY_Y,
    LAYERS_NEEDED,
    SCREEN_W,
    STACK_ORIGIN,
    STACK_SLOT_H,
    STACK_SLOT_W,
    TARGET_H,
    TARGET_ORIGIN,
    TARGET_W,
)
from shape import PolyominoShape


def draw_target_area(surface: pygame.Surface) -> None:
    tx, ty = TARGET_ORIGIN
    w = TARGET_W * GRID_CELL
    h = TARGET_H * GRID_CELL
    pygame.draw.rect(surface, COLOR_TARGET_BG, (tx, ty, w, h))
    for i in range(TARGET_W + 1):
        x = tx + i * GRID_CELL
        pygame.draw.line(surface, COLOR_GRID, (x, ty), (x, ty + h), 1)
    for j in range(TARGET_H + 1):
        y = ty + j * GRID_CELL
        pygame.draw.line(surface, COLOR_GRID, (tx, y), (tx + w, y), 1)
    pygame.draw.rect(surface, COLOR_TARGET_BORDER, (tx, ty, w, h), 3)


def draw_help_overlay(surface: pygame.Surface, font: pygame.font.Font,
                      big_font: pygame.font.Font) -> None:
    """Full-screen dim plus a centered panel listing every control."""
    dim = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    dim.fill(COLOR_OVERLAY_BG)
    surface.blit(dim, (0, 0))

    lines = [
        "L-drag: move piece",
        "R: rotate active / hovered piece",
        "Right-click: return piece to inventory",
        "Backspace: toggle cut mode (cuts can crack)",
        "Enter: finish layer     N: new game",
        "Drop on inventory bar: return piece to inventory",
        "Mouse wheel over inventory: scroll",
        "H / Esc: close this menu",
    ]
    pw, ph = 560, 80 + len(lines) * 30
    px = (SCREEN_W - pw) // 2
    py = (SCREEN_H - ph) // 2
    pygame.draw.rect(surface, COLOR_OVERLAY_PANEL, (px, py, pw, ph), border_radius=10)
    pygame.draw.rect(surface, COLOR_PANEL_BORDER, (px, py, pw, ph), 3, border_radius=10)

    heading = big_font.render("Controls", True, COLOR_TEXT)
    surface.blit(heading, heading.get_rect(center=(SCREEN_W // 2, py + 30)))
    ly = py + 64
    for line in lines:
        surface.blit(font.render(line, True, COLOR_TEXT), (px + 28, ly))
        ly += 30


class InventoryBar:
    def __init__(self):
        self.y = INVENTORY_Y
        self.slot_w = INVENTORY_SLOT_W
        self.slot_h = INVENTORY_SLOT_H
        self.padding = INVENTORY_PADDING
        self.view_x = INVENTORY_MARGIN
        self.view_w = SCREEN_W - 2 * INVENTORY_MARGIN
        self.scroll = 0.0  # px the slot strip is scrolled to the left
        self._small_font: Optional[pygame.font.Font] = None

    # ----- geometry -----

    def viewport(self) -> pygame.Rect:
        return pygame.Rect(self.view_x, self.y, self.view_w, self.slot_h)

    def content_width(self, total: int) -> int:
        if total <= 0:
            return 0
        return total * self.slot_w + (total - 1) * self.padding

    def max_scroll(self, total: int) -> float:
        return max(0.0, self.content_width(total) - self.view_w)

    def _clamp(self, total: int) -> None:
        self.scroll = max(0.0, min(self.scroll, self.max_scroll(total)))

    def slot_rect(self, idx: int, total: int) -> pygame.Rect:
        x = self.view_x - self.scroll + idx * (self.slot_w + self.padding)
        return pygame.Rect(int(x), self.y, self.slot_w, self.slot_h)

    def scrollbar_rect(self) -> pygame.Rect:
        return pygame.Rect(self.view_x, self.y + self.slot_h + 4, self.view_w, INVENTORY_SCROLLBAR_H)

    def thumb_rect(self, total: int) -> Optional[pygame.Rect]:
        """Scrollbar thumb, or None when everything fits (no scrolling needed)."""
        cw = self.content_width(total)
        if cw <= self.view_w:
            return None
        track = self.scrollbar_rect()
        thumb_w = max(30, int(track.width * self.view_w / cw))
        ms = self.max_scroll(total)
        t = (self.scroll / ms) if ms > 0 else 0.0
        thumb_x = track.x + int((track.width - thumb_w) * t)
        return pygame.Rect(thumb_x, track.y, thumb_w, track.height)

    # ----- scrolling -----

    def scroll_by(self, dx: float, total: int) -> None:
        self.scroll += dx
        self._clamp(total)

    def set_scroll_from_thumb_x(self, thumb_x: float, total: int) -> None:
        thumb = self.thumb_rect(total)
        if thumb is None:
            return
        track = self.scrollbar_rect()
        travel = track.width - thumb.width
        if travel <= 0:
            self.scroll = 0.0
            return
        t = max(0.0, min(1.0, (thumb_x - track.x) / travel))
        self.scroll = t * self.max_scroll(total)

    # ----- drawing -----

    def _font_small(self) -> pygame.font.Font:
        if self._small_font is None:
            self._small_font = pygame.font.SysFont(None, 18)
        return self._small_font

    def draw(self, surface: pygame.Surface, inventory: List[PolyominoShape],
             font: pygame.font.Font, mouse_pos: Tuple[int, int] = (-1, -1)) -> None:
        total = len(inventory)
        self._clamp(total)
        bar_rect = pygame.Rect(0, self.y - 16, SCREEN_W, self.slot_h + 32)
        pygame.draw.rect(surface, COLOR_INVENTORY_BG, bar_rect)
        label = font.render(f"Inventory: {total} cakes", True, COLOR_TEXT)
        surface.blit(label, (16, self.y - 14))

        small = self._font_small()
        prev_clip = surface.get_clip()
        surface.set_clip(self.viewport())
        for idx, shape in enumerate(inventory):
            rect = self.slot_rect(idx, total)
            if rect.right < self.view_x or rect.left > self.view_x + self.view_w:
                continue  # fully scrolled out of view
            pygame.draw.rect(surface, COLOR_INVENTORY_SLOT, rect)
            pygame.draw.rect(surface, COLOR_TARGET_BORDER, rect, 2)
            cw, ch = shape.cell_dimensions()
            if cw == 0 or ch == 0:
                continue
            # Reserve a band at the slot bottom for the size label so it never
            # covers the cake; fit the cake into the area above it.
            label_h = small.get_height() + 4
            cake_h = self.slot_h - label_h
            # Show cakes at their true play size; only shrink if too big to fit.
            fit_size = min((self.slot_w - 12) // max(cw, 1), (cake_h - 12) // max(ch, 1))
            cell_size = min(GRID_CELL, fit_size)
            content_w = cw * cell_size
            content_h = ch * cell_size
            ox = rect.x + (self.slot_w - content_w) // 2
            oy = rect.y + (cake_h - content_h) // 2
            shape.render_at(surface, (ox, oy), cell_size)
            self._draw_size_label(surface, small, rect, label_h, len(shape.cells), cw, ch)
        surface.set_clip(prev_clip)

        self._draw_scrollbar(surface, total, mouse_pos)

    def _draw_size_label(self, surface: pygame.Surface, font: pygame.font.Font,
                         rect: pygame.Rect, label_h: int, count: int, cw: int, ch: int) -> None:
        """Draw the cake's size (total cells and bounding box, e.g. '9 cells · 3x3')
        in the reserved band at the slot bottom, below the cake."""
        text = font.render(f"{count} cells · {cw}x{ch}", True, COLOR_TEXT)
        band_cy = rect.bottom - label_h // 2
        surface.blit(text, text.get_rect(center=(rect.centerx, band_cy)))

    def _draw_scrollbar(self, surface: pygame.Surface, total: int,
                        mouse_pos: Tuple[int, int]) -> None:
        thumb = self.thumb_rect(total)
        if thumb is None:
            return  # nothing to scroll
        track = self.scrollbar_rect()
        pygame.draw.rect(surface, COLOR_SCROLLBAR_TRACK, track, border_radius=5)
        hovered = thumb.collidepoint(mouse_pos)
        color = COLOR_SCROLLBAR_THUMB_HOVER if hovered else COLOR_SCROLLBAR_THUMB
        pygame.draw.rect(surface, color, thumb, border_radius=5)

    # ----- hit testing -----

    def slot_at_point(self, point: Tuple[float, float], inventory_count: int) -> int:
        if not self.viewport().collidepoint(point):
            return -1
        for idx in range(inventory_count):
            if self.slot_rect(idx, inventory_count).collidepoint(point):
                return idx
        return -1

    def contains(self, point: Tuple[float, float]) -> bool:
        bar_rect = pygame.Rect(0, self.y - 16, SCREEN_W, self.slot_h + 32)
        return bar_rect.collidepoint(point)

    def wheel_step(self) -> int:
        return INVENTORY_WHEEL_STEP


class StackView:
    def __init__(self):
        self.x, self.y = STACK_ORIGIN
        self.slot_w = STACK_SLOT_W
        self.slot_h = STACK_SLOT_H

    def draw(self, surface: pygame.Surface, layers_done: int,
             layer_coverages: List[float], font: pygame.font.Font) -> None:
        title = font.render("Napoleon Stack", True, COLOR_TEXT)
        surface.blit(title, (self.x, self.y - 28))
        for k in range(LAYERS_NEEDED):
            slot_y = self.y + (LAYERS_NEEDED - 1 - k) * (self.slot_h + 2)
            done = k < layers_done
            color = COLOR_STACK_LAYER_DONE if done else COLOR_STACK_LAYER_EMPTY
            pygame.draw.rect(surface, color, (self.x, slot_y, self.slot_w, self.slot_h))
            pygame.draw.rect(surface, COLOR_TARGET_BORDER, (self.x, slot_y, self.slot_w, self.slot_h), 1)
            if done and k < len(layer_coverages):
                cov = font.render(f"{layer_coverages[k]:.0f}%", True, COLOR_TEXT)
                surface.blit(cov, (self.x + self.slot_w - cov.get_width() - 6,
                                   slot_y + (self.slot_h - cov.get_height()) // 2))


class Button:
    def __init__(self, rect: Tuple[int, int, int, int], label: str):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.enabled = True

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, mouse_pos: Tuple[int, int],
             hoverable: bool = True) -> None:
        hovered = hoverable and self.enabled and self.rect.collidepoint(mouse_pos)
        color = COLOR_BUTTON_HOVER if hovered else COLOR_BUTTON
        if not self.enabled:
            color = (160, 150, 130)
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_TARGET_BORDER, self.rect, 2, border_radius=6)
        text = font.render(self.label, True, COLOR_BUTTON_TEXT)
        text_rect = text.get_rect(center=self.rect.center)
        surface.blit(text, text_rect)

    def clicked(self, point: Tuple[float, float]) -> bool:
        return self.enabled and self.rect.collidepoint(point)
