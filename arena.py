"""
Launcher da arena visual baseada na implementação em `legacy/astas3d.py`.
"""

import os

import pygame

import legacy.astas3d as arena_mod

arena_mod.MOVE_DELAY = 180 # Delay entre ações em ms (quanto maior, mais lento).
arena_mod.WATER_DENSITY = 0.12 # Densidade de água na layer 0 (0.0 a 1.0).

def main() -> None:
    # Garante modo visual (remove driver headless, se existir no ambiente).
    os.environ.pop("SDL_VIDEODRIVER", None)
    os.environ.pop("SDL_AUDIODRIVER", None)

    pygame.quit()
    pygame.init()

    arena_mod.run_game(algorithm="astar")


if __name__ == "__main__":
    main()
