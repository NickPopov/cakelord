"""Async entry point. Compatible with pygbag (Pygame -> WASM)."""

import asyncio

import pygame

from config import FPS, SCREEN_H, SCREEN_W
from scene import PlayScene, WinScene


async def main() -> None:
    pygame.init()
    pygame.display.set_caption("Napoleon Cake Builder")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()

    scene = PlayScene()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            scene.handle_event(event)

        scene.render(screen)
        pygame.display.flip()

        if getattr(scene, "next_scene", None) == "win":
            scene = WinScene(
                getattr(scene, "win_avg_coverage", 0.0),
                getattr(scene, "win_crumbs", 0),
            )
        elif getattr(scene, "next_scene", None) == "play":
            scene = PlayScene()

        clock.tick(FPS)
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
