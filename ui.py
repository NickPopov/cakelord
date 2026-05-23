"""UI components: target area, inventory bar, stack view, button, discard zone."""

from typing import List, Optional, Tuple

import pygame

from config import (
    COLOR_BUTTON,
    COLOR_BUTTON_HOVER,
    COLOR_BUTTON_TEXT,
    COLOR_DISCARD,
    COLOR_DISCARD_HOVER,
    COLOR_GRID,
    COLOR_INVENTORY_BG,
    COLOR_INVENTORY_SLOT,
    COLOR_STACK_LAYER_DONE,
    COLOR_STACK_LAYER_EMPTY,
    COLOR_TARGET_BG,
    COLOR_TARGET_BORDER,
    COLOR_TEXT,
    DISCARD_RECT,
    GRID_CELL,
    INVENTORY_PADDING,
    INVENTORY_SLOT_H,
    INVENTORY_SLOT_W,
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


class InventoryBar:
    def __init__(self):
        self.y = INVENTORY_Y
        self.slot_w = INVENTORY_SLOT_W
        self.slot_h = INVENTORY_SLOT_H
        self.padding = INVENTORY_PADDING

    def slot_rect(self, idx: int, total: int) -> pygame.Rect:
        total_w = total * self.slot_w + (total - 1) * self.padding
        start_x = (SCREEN_W - total_w) // 2
        x = start_x + idx * (self.slot_w + self.padding)
        return pygame.Rect(x, self.y, self.slot_w, self.slot_h)

    def draw(self, surface: pygame.Surface, inventory: List[PolyominoShape], font: pygame.font.Font) -> None:
        bar_rect = pygame.Rect(0, self.y - 16, SCREEN_W, self.slot_h + 32)
        pygame.draw.rect(surface, COLOR_INVENTORY_BG, bar_rect)
        label = font.render(f"Inventory: {len(inventory)} cakes", True, COLOR_TEXT)
        surface.blit(label, (16, self.y - 14))
        for idx, shape in enumerate(inventory):
            rect = self.slot_rect(idx, len(inventory))
            pygame.draw.rect(surface, COLOR_INVENTORY_SLOT, rect)
            pygame.draw.rect(surface, COLOR_TARGET_BORDER, rect, 2)
            cw, ch = shape.cell_dimensions()
            if cw == 0 or ch == 0:
                continue
            cell_size = min((self.slot_w - 12) // max(cw, 1), (self.slot_h - 12) // max(ch, 1))
            content_w = cw * cell_size
            content_h = ch * cell_size
            ox = rect.x + (self.slot_w - content_w) // 2
            oy = rect.y + (self.slot_h - content_h) // 2
            shape.render_at(surface, (ox, oy), cell_size)

    def slot_at_point(self, point: Tuple[float, float], inventory_count: int) -> int:
        for idx in range(inventory_count):
            if self.slot_rect(idx, inventory_count).collidepoint(point):
                return idx
        return -1


class StackView:
    def __init__(self):
        self.x, self.y = STACK_ORIGIN
        self.slot_w = STACK_SLOT_W
        self.slot_h = STACK_SLOT_H

    def draw(self, surface: pygame.Surface, layers_done: int, font: pygame.font.Font) -> None:
        title = font.render("Napoleon Stack", True, COLOR_TEXT)
        surface.blit(title, (self.x, self.y - 28))
        for k in range(LAYERS_NEEDED):
            slot_y = self.y + (LAYERS_NEEDED - 1 - k) * (self.slot_h + 2)
            done = k < layers_done
            color = COLOR_STACK_LAYER_DONE if done else COLOR_STACK_LAYER_EMPTY
            pygame.draw.rect(surface, color, (self.x, slot_y, self.slot_w, self.slot_h))
            pygame.draw.rect(surface, COLOR_TARGET_BORDER, (self.x, slot_y, self.slot_w, self.slot_h), 1)
        progress = font.render(f"{layers_done} / {LAYERS_NEEDED} layers", True, COLOR_TEXT)
        surface.blit(progress, (self.x, self.y + LAYERS_NEEDED * (self.slot_h + 2) + 8))


class Button:
    def __init__(self, rect: Tuple[int, int, int, int], label: str):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.enabled = True

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, mouse_pos: Tuple[int, int]) -> None:
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
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


class DiscardZone:
    def __init__(self):
        self.rect = pygame.Rect(*DISCARD_RECT)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, mouse_pos: Tuple[int, int]) -> None:
        hovered = self.rect.collidepoint(mouse_pos)
        color = COLOR_DISCARD_HOVER if hovered else COLOR_DISCARD
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_TARGET_BORDER, self.rect, 2, border_radius=8)
        label = font.render("DISCARD", True, COLOR_BUTTON_TEXT)
        label_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, label_rect)

    def contains(self, point: Tuple[float, float]) -> bool:
        return self.rect.collidepoint(point)
