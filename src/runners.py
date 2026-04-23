"""Execução dos algoritmos simpleai com métricas (tempo de parede, nós visitados)."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import dataclass
from typing import Callable

from simpleai.search import astar, breadth_first, depth_first, greedy, uniform_cost
from simpleai.search.viewers import BaseViewer

from src.search_problem import DroneUrbanSearchProblem


class StatsViewer(BaseViewer):
    """Viewer que atualiza estatísticas sem armazenar o log completo de eventos."""

    def log_event(self, name, description):
        return


@dataclass
class RunResult:
    algorithm: str
    success: bool
    path_cost: float | None
    plan_length: int | None
    wall_time_sec: float
    visited_nodes: int
    max_fringe_size: int
    iterations: int
    timeout: bool
    error: str | None = None


def _run_inner(
    name: str,
    algo: Callable,
    problem: DroneUrbanSearchProblem,
    graph_search: bool,
) -> RunResult:
    viewer = StatsViewer()
    t0 = time.perf_counter()
    try:
        node = algo(problem, graph_search=graph_search, viewer=viewer)
    except Exception as exc:
        return RunResult(
            algorithm=name,
            success=False,
            path_cost=None,
            plan_length=None,
            wall_time_sec=time.perf_counter() - t0,
            visited_nodes=viewer.stats["visited_nodes"],
            max_fringe_size=viewer.stats["max_fringe_size"],
            iterations=viewer.stats["iterations"],
            timeout=False,
            error=str(exc),
        )
    elapsed = time.perf_counter() - t0
    if node is None:
        return RunResult(
            algorithm=name,
            success=False,
            path_cost=None,
            plan_length=None,
            wall_time_sec=elapsed,
            visited_nodes=viewer.stats["visited_nodes"],
            max_fringe_size=viewer.stats["max_fringe_size"],
            iterations=viewer.stats["iterations"],
            timeout=False,
        )
    path = node.path()
    plan_length = max(0, len(path) - 1)
    return RunResult(
        algorithm=name,
        success=True,
        path_cost=float(node.cost),
        plan_length=plan_length,
        wall_time_sec=elapsed,
        visited_nodes=viewer.stats["visited_nodes"],
        max_fringe_size=viewer.stats["max_fringe_size"],
        iterations=viewer.stats["iterations"],
        timeout=False,
    )


def run_algorithm(
    problem: DroneUrbanSearchProblem,
    algorithm: str,
    *,
    graph_search: bool = True,
    wall_timeout_sec: float | None = 30.0,
) -> RunResult:
    """
    Roda um algoritmo por nome: bfs, dfs, ucs, greedy, astar.
    `visited_nodes` segue o contador do BaseViewer do simpleai (um incremento por nó
    retirado da fringe, inclusive o objetivo quando encontrado).
    Opcionalmente aplica timeout de parede via executor (o thread continua em segundo plano).
    """
    table = {
        "bfs": ("breadth_first", breadth_first),
        "dfs": ("depth_first", depth_first),
        "ucs": ("uniform_cost", uniform_cost),
        "greedy": ("greedy", greedy),
        "astar": ("astar", astar),
    }
    key = algorithm.lower()
    if key not in table:
        raise ValueError(f"Algoritmo desconhecido: {algorithm}. Use: {', '.join(table)}")
    label, algo = table[key]

    if wall_timeout_sec is None or wall_timeout_sec <= 0:
        return _run_inner(label, algo, problem, graph_search)

    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(_run_inner, label, algo, problem, graph_search)
        try:
            return fut.result(timeout=wall_timeout_sec)
        except FuturesTimeout:
            return RunResult(
                algorithm=label,
                success=False,
                path_cost=None,
                plan_length=None,
                wall_time_sec=wall_timeout_sec,
                visited_nodes=0,
                max_fringe_size=0,
                iterations=0,
                timeout=True,
                error="timeout",
            )


def run_all_algorithms(
    problem: DroneUrbanSearchProblem,
    *,
    graph_search: bool = True,
    wall_timeout_sec: float | None = 30.0,
) -> dict[str, RunResult]:
    out = {}
    for key in ("bfs", "dfs", "ucs", "greedy", "astar"):
        out[key] = run_algorithm(
            problem,
            key,
            graph_search=graph_search,
            wall_timeout_sec=wall_timeout_sec,
        )
    return out
