"""
Demo prática 3D comparativa (lado a lado) dos algoritmos de busca.

Uso:
    python experiments/demo_compare_3d.py
    python experiments/demo_compare_3d.py --seed 7 --timeout 20 --speed 1.25

Controles:
    SPACE  pausa/continua
    R      reinicia com a mesma seed
    +/-    diminui/aumenta velocidade
    ESC    sair
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.environment import TNFZRegion, UrbanInstance, generate_instance
from src.runners import RunResult, run_all_algorithms
from src.search_problem import DroneUrbanSearchProblem

try:
    import pygame
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Pygame não está instalado. Instale com: pip install pygame"
    ) from exc


ALGO_KEYS = ("bfs", "dfs", "ucs", "greedy", "astar")
ALGO_LABELS = {
    "bfs": "Breadth First",
    "dfs": "Depth First",
    "ucs": "Uniform Cost",
    "greedy": "Greedy",
    "astar": "A*",
}
ALGO_COLORS = {
    "bfs": (255, 179, 71),
    "dfs": (179, 157, 219),
    "ucs": (100, 181, 246),
    "greedy": (77, 208, 225),
    "astar": (129, 199, 132),
}

WINDOW_W = 1720
WINDOW_H = 980
PADDING = 14
PANEL_COLS = 3
PANEL_ROWS = 2

TILE_W = 30
TILE_H = 16
LAYER_Z = 14
STEP_MS = 340


@dataclass
class AlgoPlayback:
    key: str
    result: RunResult
    states: list[tuple[int, int, int, int, int]]
    index: int = 0

    @property
    def done(self) -> bool:
        return self.index >= max(0, len(self.states) - 1)

    @property
    def current_state(self) -> tuple[int, int, int, int, int]:
        if not self.states:
            return (0, 0, 0, 0, 0)
        return self.states[min(self.index, len(self.states) - 1)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=7, help="Seed da instância")
    parser.add_argument("--timeout", type=float, default=25.0, help="Timeout por algoritmo (s)")
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Multiplicador da velocidade da animação",
    )
    parser.add_argument(
        "--slice",
        type=str,
        default="baseline",
        choices=("baseline", "no_wind", "no_tnfz", "low_battery"),
        help="Fatia experimental para a instância",
    )
    return parser.parse_args()


def _instance_kwargs(slice_name: str) -> dict:
    if slice_name == "no_wind":
        return {"with_wind": False}
    if slice_name == "no_tnfz":
        return {"with_tnfz": False}
    if slice_name == "low_battery":
        return {"low_battery": True}
    return {}


def iso_point(x: int, y: int, z: int, ox: int, oy: int) -> tuple[int, int]:
    px = ox + (x - y) * (TILE_W // 2)
    py = oy + (x + y) * (TILE_H // 2) - z * LAYER_Z
    return px, py


def draw_diamond(surface: pygame.Surface, center: tuple[int, int], color: tuple[int, int, int], border=(26, 30, 38)) -> None:
    cx, cy = center
    hw = TILE_W // 2
    hh = TILE_H // 2
    pts = [(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)]
    pygame.draw.polygon(surface, color, pts)
    pygame.draw.polygon(surface, border, pts, width=1)


def draw_drone(surface: pygame.Surface, x: int, y: int, z: int, ox: int, oy: int, color: tuple[int, int, int]) -> None:
    cx, cy = iso_point(x, y, z, ox, oy)
    pygame.draw.circle(surface, (20, 20, 24), (cx, cy + 5), 5)
    pygame.draw.circle(surface, color, (cx, cy), 7)
    pygame.draw.circle(surface, (235, 240, 245), (cx + 2, cy - 2), 2)


def _tnfz_active(regions: tuple[TNFZRegion, ...], x: int, y: int, z: int, t: int) -> bool:
    for reg in regions:
        if reg.blocks(x, y, z, t):
            return True
    return False


def draw_panel(
    canvas: pygame.Surface,
    rect: pygame.Rect,
    inst: UrbanInstance,
    playback: AlgoPlayback,
    font_title: pygame.font.Font,
    font_body: pygame.font.Font,
) -> None:
    pygame.draw.rect(canvas, (24, 27, 34), rect, border_radius=8)
    pygame.draw.rect(canvas, (62, 68, 84), rect, width=1, border_radius=8)

    title = ALGO_LABELS[playback.key]
    header = font_title.render(title, True, ALGO_COLORS[playback.key])
    canvas.blit(header, (rect.x + 10, rect.y + 8))

    if playback.result.timeout:
        status_msg = "TIMEOUT"
    elif playback.result.success:
        status_msg = "SUCCESS"
    else:
        status_msg = "NO PATH"
    status = font_body.render(status_msg, True, (220, 225, 235))
    canvas.blit(status, (rect.right - status.get_width() - 10, rect.y + 10))

    margin_top = 36
    arena = pygame.Rect(rect.x + 8, rect.y + margin_top, rect.w - 16, rect.h - margin_top - 104)
    pygame.draw.rect(canvas, (15, 17, 22), arena, border_radius=6)

    ox = arena.centerx
    oy = arena.y + 48 + inst.nz * LAYER_Z

    current_t = playback.current_state[4]
    trail = playback.states[: playback.index + 1]
    trail_cells = {(s[0], s[1], s[2]) for s in trail}

    for z in range(inst.nz):
        for x in range(inst.nx):
            for y in range(inst.ny):
                if (x, y, z) in inst.obstacles:
                    continue
                center = iso_point(x, y, z, ox, oy)
                base_color = (58 + z * 18, 66 + z * 18, 78 + z * 18)
                if (x, y, z) in inst.stations:
                    base_color = (80, 122, 88)
                if _tnfz_active(inst.tnfz_regions, x, y, z, current_t):
                    base_color = (120, 64, 64)
                if (x, y, z) in trail_cells:
                    base_color = tuple(min(255, c + 24) for c in ALGO_COLORS[playback.key])
                draw_diamond(canvas, center, base_color)
                if (x, y, z) in inst.wind and inst.wind[(x, y, z)] != (0, 0, 0):
                    pygame.draw.circle(canvas, (80, 130, 210), (center[0], center[1]), 2)

    for (x, y, z) in sorted(inst.obstacles, key=lambda c: (c[2], c[0] + c[1])):
        draw_diamond(canvas, iso_point(x, y, z, ox, oy), (86, 88, 98))

    sx, sy, sz, battery, tick = playback.current_state
    draw_drone(canvas, sx, sy, sz, ox, oy, ALGO_COLORS[playback.key])

    info_y = arena.bottom + 8
    steps_txt = f"step {playback.index}/{max(0, len(playback.states)-1)}"
    line1 = f"{steps_txt} | cost={playback.result.path_cost if playback.result.path_cost is not None else '-'}"
    line2 = f"battery={battery} | t={tick} | visited={playback.result.visited_nodes}"
    line3 = f"time={playback.result.wall_time_sec:.3f}s | fringe={playback.result.max_fringe_size}"
    for i, text in enumerate((line1, line2, line3)):
        surf = font_body.render(text, True, (207, 214, 225))
        canvas.blit(surf, (rect.x + 10, info_y + i * 18))


def build_playbacks(results: dict[str, RunResult], problem: DroneUrbanSearchProblem) -> list[AlgoPlayback]:
    playbacks: list[AlgoPlayback] = []
    for key in ALGO_KEYS:
        rr = results[key]
        states = rr.plan_states or [problem.initial_state]
        playbacks.append(AlgoPlayback(key=key, result=rr, states=states, index=0))
    return playbacks


def run_demo(seed: int, timeout: float, speed: float, slice_name: str) -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("Comparacao 3D de algoritmos - Drone")
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont("consolas", 20, bold=True)
    body_font = pygame.font.SysFont("consolas", 14)

    inst = generate_instance(seed, experiment_slice=slice_name, **_instance_kwargs(slice_name))
    problem = DroneUrbanSearchProblem(inst)
    results = run_all_algorithms(problem, graph_search=True, wall_timeout_sec=timeout)
    playbacks = build_playbacks(results, problem)

    tick_acc = 0.0
    playing = True
    speed_factor = max(0.1, speed)
    running = True

    while running:
        dt = clock.tick(60)
        tick_acc += dt * speed_factor

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    playing = not playing
                elif event.key == pygame.K_r:
                    return run_demo(seed, timeout, speed_factor, slice_name)
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                    speed_factor = min(4.0, speed_factor + 0.2)
                elif event.key == pygame.K_MINUS:
                    speed_factor = max(0.2, speed_factor - 0.2)

        if playing and tick_acc >= STEP_MS:
            tick_acc = 0.0
            for pb in playbacks:
                if not pb.done:
                    pb.index += 1

        screen.fill((11, 12, 16))
        header = (
            f"Seed={seed} | slice={slice_name} | speed={speed_factor:.1f}x | "
            "SPACE pause/resume | R restart | +/- speed"
        )
        screen.blit(body_font.render(header, True, (194, 200, 212)), (PADDING, PADDING))

        panel_w = (WINDOW_W - PADDING * (PANEL_COLS + 1)) // PANEL_COLS
        panel_h = (WINDOW_H - 56 - PADDING * (PANEL_ROWS + 1)) // PANEL_ROWS

        for i, pb in enumerate(playbacks):
            row = i // PANEL_COLS
            col = i % PANEL_COLS
            rect = pygame.Rect(
                PADDING + col * (panel_w + PADDING),
                40 + PADDING + row * (panel_h + PADDING),
                panel_w,
                panel_h,
            )
            draw_panel(screen, rect, inst, pb, title_font, body_font)

        legend_rect = pygame.Rect(
            PADDING + 2 * (panel_w + PADDING),
            40 + PADDING + 1 * (panel_h + PADDING),
            panel_w,
            panel_h,
        )
        pygame.draw.rect(screen, (24, 27, 34), legend_rect, border_radius=8)
        pygame.draw.rect(screen, (62, 68, 84), legend_rect, width=1, border_radius=8)
        screen.blit(title_font.render("Legenda", True, (230, 233, 240)), (legend_rect.x + 12, legend_rect.y + 10))

        lines = [
            "Azul escuro: arena 3D por nivel z",
            "Cinza: obstaculos",
            "Verde: estacoes de recarga",
            "Vermelho: TNFZ ativa no tempo atual",
            "Cor do algoritmo: trilha + drone",
            "Ponto azul: celula com vento",
        ]
        for idx, line in enumerate(lines):
            screen.blit(body_font.render(line, True, (207, 214, 225)), (legend_rect.x + 12, legend_rect.y + 44 + idx * 20))

        pygame.display.flip()

    pygame.quit()


def main() -> None:
    args = parse_args()
    run_demo(seed=args.seed, timeout=args.timeout, speed=args.speed, slice_name=args.slice)


if __name__ == "__main__":
    main()
