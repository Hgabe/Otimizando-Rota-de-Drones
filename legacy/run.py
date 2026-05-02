import json
import random
import time
import os
import sys
import signal 
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
pygame.init()

MAX_TIME_PER_INSTANCE = 5 
from astas3d import (
    generate_map, generate_cycle,
    a_star_3d, DroneProblem,
    MAZE_SIZE, NUM_CHARGE_STATIONS, MIN_DIST,
    MAX_BATTERY, WIN_DELIVERIES,
    R_ZONE_COST, WIND_COST,
    run_game,
)

NUM_INSTANCES = 100
ALGORITHMS    = ["astar", "greedy"]
RESULTS_FILE  = "resultados.json"


def simulate(algo, seed):
    random.seed(seed)

    drone_pos, charge_stations, walls, mult_map, height_map, wind = generate_map(
        MAZE_SIZE, NUM_CHARGE_STATIONS
    )
    collect_pos, goal_pos, restricted_zone = generate_cycle(
        drone_pos, charge_stations, walls, MAZE_SIZE, MIN_DIST
    )

    drone_col, drone_row = drone_pos
    drone_level = 0
    carrying    = False
    battery     = MAX_BATTERY
    score       = 0
    steps       = 0
    deliveries  = 0
    total_nodes = 0
    sucesso     = False
    motivo_falha = None

    start_time = time.perf_counter()
    MAX_STEPS  = 10_000

    while steps < MAX_STEPS:
        if time.perf_counter() - start_time > MAX_TIME_PER_INSTANCE:
            motivo_falha = "timeout"
            break

        current_goals = {collect_pos} if not carrying else {goal_pos}
        dest_goal = collect_pos if not carrying else goal_pos
        dist_dest = (
            abs(drone_col - dest_goal[0]) +
            abs(drone_row - dest_goal[1]) +
            drone_level
        )
        bat_apos = battery - dist_dest

        if bat_apos <= 0:
            current_goals = charge_stations
        elif charge_stations:
            from simpleai.search import astar as _astar_fn
            _prob_test = DroneProblem(
                initial_state=(dest_goal[0], dest_goal[1], 0, bat_apos),
                goals=charge_stations,
                charge_stations=charge_stations,
                mult_map=mult_map,
                restricted_zone=restricted_zone,
                wind=wind,
                maze_size=MAZE_SIZE,
            )
            _res = _astar_fn(_prob_test, graph_search=True)
            total_nodes += _prob_test.nodes_expanded
            if _res is None:
                current_goals = charge_stations

        actions, n_nodes = a_star_3d(
            (drone_col, drone_row), drone_level, battery,
            current_goals, charge_stations,
            mult_map, restricted_zone, wind, MAZE_SIZE,
            _return_nodes=True,
            algorithm=algo,
        )
        total_nodes += n_nodes

        if actions is None:
            motivo_falha = "sem_caminho"
            break

        plan_done = False
        for action in actions:
            if battery <= 0:
                motivo_falha = "sem_bateria"
                plan_done = True
                break

            if action['type'] == 'move':
                dx, dy = action['direction']
                drone_col += dx
                drone_row += dy
                drone_pos  = (drone_col, drone_row)
                battery   -= 1
                score     -= 1
                steps     += 1

                wind_levels = wind.get(drone_pos, frozenset())
                if drone_level in wind_levels:
                    score -= WIND_COST
                if drone_pos in restricted_zone:
                    score -= R_ZONE_COST
                if drone_pos in charge_stations and drone_level == 0:
                    battery = MAX_BATTERY

                if drone_pos == collect_pos and drone_level == 0 and not carrying:
                    carrying = True
                    score   += 10
                    break
                elif drone_pos == goal_pos and drone_level == 0 and carrying:
                    carrying    = False
                    deliveries += 1
                    score      += 50
                    if deliveries >= WIN_DELIVERIES:
                        sucesso    = True
                        plan_done  = True
                        break
                    collect_pos, goal_pos, restricted_zone = generate_cycle(
                        drone_pos, charge_stations, walls, MAZE_SIZE, MIN_DIST
                    )
                    break

            elif action['type'] == 'rise':
                drone_level += 1
                battery     -= 1
                score       -= 1
                steps       += 1

            elif action['type'] == 'descend':
                drone_level -= 1
                battery     -= 1
                score       -= 1
                steps       += 1
                if drone_pos in charge_stations and drone_level == 0:
                    battery = MAX_BATTERY
                if drone_pos == collect_pos and drone_level == 0 and not carrying:
                    carrying = True
                    score   += 10
                    break
                elif drone_pos == goal_pos and drone_level == 0 and carrying:
                    carrying    = False
                    deliveries += 1
                    score      += 50
                    if deliveries >= WIN_DELIVERIES:
                        sucesso   = True
                        plan_done = True
                        break
                    collect_pos, goal_pos, restricted_zone = generate_cycle(
                        drone_pos, charge_stations, walls, MAZE_SIZE, MIN_DIST
                    )
                    break

        if sucesso or motivo_falha or plan_done:
            break

    elapsed = time.perf_counter() - start_time
    if steps >= MAX_STEPS and not sucesso:
        motivo_falha = "limite_de_passos"

    return {
        "algoritmo":      algo,
        "seed":           seed,
        "sucesso":        sucesso,
        "motivo_falha":   motivo_falha,
        "custo":          score,
        "tempo_s":        round(elapsed, 4),
        "nos_expandidos": total_nodes,
        "passos":         steps,
        "entregas":       deliveries,
        "max_battery":    MAX_BATTERY,
        "maze_size":      MAZE_SIZE,
        "num_estacoes":   NUM_CHARGE_STATIONS,
        "win_deliveries": WIN_DELIVERIES,
    }

def run_visual_instance(algo, seed):
    print(f"\n{'='*55}")
    print(f"  INSTÂNCIA VISUAL -- {algo.upper()}  (seed={seed})")
    print(f"  Feche a janela para continuar os experimentos.")
    print(f"{'='*55}\n")

    for k in ("SDL_VIDEODRIVER", "SDL_AUDIODRIVER"):
        if k in os.environ:
            del os.environ[k]

    pygame.quit()   
    pygame.init()   

    random.seed(seed)

    import astas3d as mc
    _original_fn = mc.a_star_3d
    _nodes_acc   = [0]

    def _wrapped(*args, **kwargs):
        kwargs["algorithm"] = algo
        want_nodes = kwargs.pop("_return_nodes", False)
        resultado = _original_fn(*args, **kwargs)
        if isinstance(resultado, tuple):
            actions, n = resultado
        else:
            actions, n = resultado, 0
        _nodes_acc[0] += n
        if want_nodes:
            return actions, n
        return actions

    mc.a_star_3d = _wrapped
    start_t = time.perf_counter()
    score, deliveries, steps = mc.run_game()
    elapsed = time.perf_counter() - start_t
    mc.a_star_3d = _original_fn

    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.quit()
    pygame.init()

    return {
        "algoritmo":      algo,
        "seed":           seed,
        "sucesso":        deliveries >= WIN_DELIVERIES,
        "motivo_falha":   None if deliveries >= WIN_DELIVERIES else "interrompido",
        "custo":          score,
        "tempo_s":        round(elapsed, 4),
        "nos_expandidos": _nodes_acc[0],
        "passos":         steps,
        "entregas":       deliveries,
        "max_battery":    MAX_BATTERY,
        "maze_size":      MAZE_SIZE,
        "num_estacoes":   NUM_CHARGE_STATIONS,
        "win_deliveries": WIN_DELIVERIES,
    }

def main():
    results = []
    seeds   = list(range(1, NUM_INSTANCES + 1))

    for algo in ALGORITHMS:
        print(f"\n{'#'*55}")
        print(f"  {NUM_INSTANCES} instâncias -- {algo.upper()}")
        print(f"{'#'*55}")

        for i, seed in enumerate(seeds):
            instance_num = i + 1

            if instance_num == 1:
                result = run_visual_instance(algo, seed)
            else:
                result = simulate(algo, seed)
                status = "OK" if result["sucesso"] else "XX"
                print(f"  [{status}] #{instance_num:3d} seed={seed:3d} "
                      f"custo={result['custo']:+5d} "
                      f"tempo={result['tempo_s']:6.2f}s "
                      f"nos={result['nos_expandidos']:6d} "
                      f"entregas={result['entregas']}")

            result["instancia"] = instance_num
            results.append(result)

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*55}")
    print(f"  {len(results)} resultados salvos em '{RESULTS_FILE}'")

    for algo in ALGORITHMS:
        subset   = [r for r in results if r["algoritmo"] == algo]
        sucessos = sum(1 for r in subset if r["sucesso"])
        t_med    = sum(r["tempo_s"] for r in subset) / len(subset)
        n_med    = sum(r["nos_expandidos"] for r in subset) / len(subset)
        c_med    = sum(r["custo"] for r in subset if r["sucesso"] or True) / len(subset)
        print(f"\n  {algo.upper()}:")
        print(f"    Taxa de sucesso: {sucessos}/{len(subset)} ({100*sucessos/len(subset):.0f}%)")
        print(f"    Custo médio:     {c_med:.1f}")
        print(f"    Tempo médio:     {t_med:.3f}s")
        print(f"    Nos médios:      {n_med:.0f}")

    print(f"\n  Execute: python plot_results.py\n")


if __name__ == "__main__":
    main()