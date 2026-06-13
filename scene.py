"""Scenes: PlayScene (main gameplay) and WinScene (victory screen)."""

from typing import Optional

import pygame

from config import (
    COLOR_BG,
    COLOR_CAKE_HOVER,
    COLOR_CRUMB,
    COLOR_CUT_HINT,
    COLOR_CUT_VALID,
    COLOR_PLACED_FILL,
    COLOR_TEXT,
    CRUMB_FLASH_MS,
    CRUMB_GOAL,
    CUT_MESSAGE_MS,
    GRID_CELL,
    LAYERS_NEEDED,
    SCREEN_H,
    SCREEN_W,
)
from game import GameState, Mode
from ui import (
    Button,
    InventoryBar,
    StackView,
    draw_help_overlay,
    draw_target_area,
)


class PlayScene:
    def __init__(self, seed: Optional[int] = None):
        self.game = GameState(seed=seed)
        self.inventory_bar = InventoryBar()
        self.stack_view = StackView()
        self.cut_button = Button((24, 356, 106, 40), "Cut: OFF")
        self.bake_button = Button((138, 356, 106, 40), "Done")
        self.reset_button = Button((24, 16, 124, 32), "New Game")
        self.keys_button = Button((156, 16, 88, 32), "Help")
        self.font: Optional[pygame.font.Font] = None
        self.big_font: Optional[pygame.font.Font] = None
        self.next_scene: Optional[str] = None
        self.show_help: bool = False
        self.win_avg_coverage: float = 0.0
        self.win_crumbs: int = 0
        self.win_layer_coverages: list = []
        self.cut_message: str = ""
        self.cut_message_until: int = 0
        self.crumb_flashes: list = []  # (x, y, until_ms)
        self.scrollbar_drag: bool = False
        self.scrollbar_grab_dx: float = 0.0

    def _ensure_fonts(self) -> None:
        if self.font is None:
            self.font = pygame.font.SysFont(None, 22)
            self.big_font = pygame.font.SysFont(None, 36)

    def handle_event(self, event: pygame.event.Event) -> None:
        self._ensure_fonts()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_h:
                self.show_help = not self.show_help
            elif event.key == pygame.K_ESCAPE:
                self.show_help = False
            elif event.key == pygame.K_BACKSPACE:
                self.game.toggle_mode()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._try_bake()
            elif event.key == pygame.K_r:
                mx, my = pygame.mouse.get_pos()
                if self.game.dragging is not None:
                    self.game.rotate_dragging(mx, my)
                else:
                    self.game.rotate_under_cursor((mx, my))
            elif event.key == pygame.K_n:
                self.game = GameState()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_down(event)
        elif event.type == pygame.MOUSEMOTION:
            if self.scrollbar_drag:
                self.inventory_bar.set_scroll_from_thumb_x(
                    event.pos[0] - self.scrollbar_grab_dx, len(self.game.inventory)
                )
            elif self.game.dragging is not None:
                mx, my = event.pos
                self.game.update_drag(mx, my)
        elif event.type == pygame.MOUSEWHEEL:
            if self.inventory_bar.contains(pygame.mouse.get_pos()):
                self.inventory_bar.scroll_by(
                    -event.y * self.inventory_bar.wheel_step(), len(self.game.inventory)
                )
        elif event.type == pygame.MOUSEBUTTONUP:
            self._handle_mouse_up(event)

    def _handle_mouse_down(self, event: pygame.event.Event) -> None:
        mx, my = event.pos

        if self.show_help:
            self.show_help = False  # any click dismisses the overlay
            return

        if event.button == 3:
            shape = self.game.find_shape_at(event.pos)
            if shape is not None:
                self.game.return_to_inventory(shape)
            return

        if event.button != 1:
            return

        # A cake under the cursor takes priority over any button beneath it, so a
        # piece resting on a button can still be grabbed (or cut) instead of clicking it.
        shape_under = self.game.find_shape_at(event.pos)
        if shape_under is None:
            if self.keys_button.clicked(event.pos):
                self.show_help = not self.show_help
                return
            if self.cut_button.clicked(event.pos):
                self.game.toggle_mode()
                return
            if self.bake_button.clicked(event.pos):
                self._try_bake()
                return
            if self.reset_button.clicked(event.pos):
                self.game = GameState()
                return

        # Scrollbar: grab the thumb, or click the track to jump it under the cursor.
        track = self.inventory_bar.scrollbar_rect()
        thumb = self.inventory_bar.thumb_rect(len(self.game.inventory))
        if thumb is not None and track.collidepoint(event.pos):
            if thumb.collidepoint(event.pos):
                self.scrollbar_grab_dx = event.pos[0] - thumb.x
            else:
                self.scrollbar_grab_dx = thumb.width / 2
                self.inventory_bar.set_scroll_from_thumb_x(
                    event.pos[0] - self.scrollbar_grab_dx, len(self.game.inventory)
                )
            self.scrollbar_drag = True
            return

        idx = self.inventory_bar.slot_at_point(event.pos, len(self.game.inventory))
        if idx >= 0:
            self.game.grab_from_inventory(idx, mx, my)
            return

        if self.game.mode == Mode.CUT:
            if shape_under is not None:
                outcome = self.game.try_cut(shape_under, event.pos, max_dist=GRID_CELL / 2)
                if outcome.broke:
                    now = pygame.time.get_ticks()
                    self.cut_message = f"Cracked! lost {outcome.crumbs_lost} crumb(s)"
                    self.cut_message_until = now + CUT_MESSAGE_MS
                    self.crumb_flashes = [
                        (x, y, now + CRUMB_FLASH_MS) for (x, y) in outcome.crumb_world_cells
                    ]
            return

        if shape_under is not None:
            if shape_under in self.game.placed_pieces:
                self.game.grab_placed_piece(shape_under, mx, my)
            elif shape_under in self.game.work_pieces:
                self.game.grab_work_piece(shape_under, mx, my)

    def _handle_mouse_up(self, event: pygame.event.Event) -> None:
        if self.scrollbar_drag:
            self.scrollbar_drag = False
            return
        if self.game.dragging is None:
            return
        over_inventory = self.inventory_bar.contains(event.pos)
        self.game.release_drag(over_inventory)

    def _try_bake(self) -> None:
        if self.game.bake_layer():
            if self.game.is_won():
                self.win_avg_coverage = self.game.average_coverage()
                self.win_crumbs = self.game.crumbs
                self.win_layer_coverages = list(self.game.layer_coverages)
                self.next_scene = "win"

    def _update_button_state(self) -> None:
        on_off = "ON" if self.game.mode == Mode.CUT else "OFF"
        self.cut_button.label = f"Cut: {on_off}"
        self.bake_button.enabled = self.game.can_bake()

    def render(self, surface: pygame.Surface) -> None:
        self._ensure_fonts()
        self._update_button_state()
        mouse_pos = pygame.mouse.get_pos()

        surface.fill(COLOR_BG)

        # --- Backdrops draw first, under the pieces ---
        self.stack_view.draw(surface, self.game.layers_done, self.game.layer_coverages, self.font)
        draw_target_area(surface)
        self.inventory_bar.draw(surface, self.game.inventory, self.font, mouse_pos)

        # --- HUD readouts + buttons ---
        # Coverage shares the top header line with the stack title; crumbs sit under
        # the stack image (in the standard dark text color).
        pct = self.game.coverage_percent()
        complete = self.game.is_layer_complete()
        cov_color = COLOR_CUT_VALID if complete else COLOR_TEXT
        cov_surf = self.font.render(f"Coverage: {pct:.0f}%", True, cov_color)
        surface.blit(cov_surf, (336, 76))
        decor = self.game.decoration_coverage_percent()
        crumb_surf = self.font.render(
            f"Crumbs: {self.game.crumbs}/{CRUMB_GOAL}  Decoration: {decor:.0f}%",
            True,
            COLOR_TEXT,
        )
        surface.blit(crumb_surf, (24, 318))
        # A cake under the cursor takes click priority over the buttons, so don't
        # highlight a button while a piece is covering it.
        btn_hoverable = self.game.find_shape_at(mouse_pos) is None
        self.cut_button.draw(surface, self.font, mouse_pos, hoverable=btn_hoverable)
        self.bake_button.draw(surface, self.font, mouse_pos, hoverable=btn_hoverable)
        self.keys_button.draw(surface, self.font, mouse_pos, hoverable=btn_hoverable)
        self.reset_button.draw(surface, self.font, mouse_pos, hoverable=btn_hoverable)

        # --- Pieces: placed, then floating work pieces, then the dragged piece on top ---
        for piece in self.game.placed_pieces:
            piece.render(surface, override_color=COLOR_PLACED_FILL)
        for piece in self.game.work_pieces:
            if piece is self.game.dragging:
                continue
            piece.render(surface)
        if self.game.dragging is not None:
            # Drawn last so it floats above the inventory bar when returning a piece.
            self.game.dragging.render(surface, override_color=COLOR_CAKE_HOVER)

        now = pygame.time.get_ticks()
        if self.crumb_flashes:
            self.crumb_flashes = [(x, y, u) for (x, y, u) in self.crumb_flashes if u > now]
            for (x, y, until) in self.crumb_flashes:
                alpha = max(0, min(255, int(255 * (until - now) / CRUMB_FLASH_MS)))
                crumb = pygame.Surface((GRID_CELL, GRID_CELL), pygame.SRCALPHA)
                crumb.fill((*COLOR_CRUMB, alpha))
                surface.blit(crumb, (x, y))

        if self.game.mode == Mode.CUT and self.game.dragging is None:
            shape = self.game.find_shape_at(mouse_pos)
            if shape is not None:
                cut = shape.cut_at(mouse_pos, max_dist=GRID_CELL / 2)
                if cut is not None:
                    (x1, y1), (x2, y2) = shape.cut_hint_segment(cut)
                    pygame.draw.line(surface, COLOR_CUT_HINT, (x1, y1), (x2, y2), 4)

        if self.cut_message and now < self.cut_message_until:
            msg_surf = self.big_font.render(self.cut_message, True, COLOR_CUT_HINT)
            surface.blit(msg_surf, msg_surf.get_rect(center=(SCREEN_W // 2, 110)))

        if self.show_help:
            draw_help_overlay(surface, self.font, self.big_font)


class WinScene:
    def __init__(self, avg_coverage: float = 0.0, crumbs: int = 0,
                 layer_coverages: Optional[list] = None):
        self.avg_coverage = avg_coverage
        self.crumbs = crumbs
        self.layer_coverages = list(layer_coverages or [])
        self.decoration = 100.0 * min(crumbs, CRUMB_GOAL) / CRUMB_GOAL
        self.font: Optional[pygame.font.Font] = None
        self.big_font: Optional[pygame.font.Font] = None
        self.next_scene: Optional[str] = None

    def _ensure_fonts(self) -> None:
        if self.font is None:
            self.font = pygame.font.SysFont(None, 26)
            self.big_font = pygame.font.SysFont(None, 64)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self.next_scene = "play"
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.next_scene = "play"

    def render(self, surface: pygame.Surface) -> None:
        self._ensure_fonts()
        surface.fill((40, 25, 15))
        title = self.big_font.render("Napoleon Cake Done!", True, (255, 230, 180))
        surface.blit(title, title.get_rect(center=(SCREEN_W // 2, 56)))

        avg = self.font.render(f"Average coverage: {self.avg_coverage:.0f}%", True, (255, 230, 180))
        surface.blit(avg, avg.get_rect(center=(SCREEN_W // 2, 104)))

        decor_surf = self.font.render(
            f"Decoration: {self.decoration:.0f}%  ({self.crumbs}/{CRUMB_GOAL} crumbs)",
            True,
            (255, 230, 180),
        )
        surface.blit(decor_surf, decor_surf.get_rect(center=(SCREEN_W // 2, 134)))

        cx = SCREEN_W // 2
        base_y = SCREEN_H - 70
        layer_h = 36
        layer_w = 360
        for k in range(LAYERS_NEEDED):
            y = base_y - k * (layer_h - 4)
            cake_color = (220, 170, 90) if k % 2 == 0 else (235, 195, 120)
            cream_color = (250, 240, 210)
            pygame.draw.rect(surface, cake_color, (cx - layer_w // 2, y, layer_w, layer_h - 8))
            pygame.draw.rect(surface, (140, 90, 30), (cx - layer_w // 2, y, layer_w, layer_h - 8), 2)
            if k < LAYERS_NEEDED - 1:
                pygame.draw.rect(surface, cream_color, (cx - layer_w // 2, y - 4, layer_w, 4))
            # Per-layer statistic: each baked layer's coverage, on the layer itself.
            if k < len(self.layer_coverages):
                stat = self.font.render(
                    f"Layer {k + 1}:  {self.layer_coverages[k]:.0f}%", True, (60, 40, 20)
                )
                surface.blit(stat, stat.get_rect(center=(cx, y + (layer_h - 8) // 2)))

        msg = self.font.render("Click or press R to play again", True, (255, 230, 180))
        surface.blit(msg, msg.get_rect(center=(SCREEN_W // 2, SCREEN_H - 22)))
