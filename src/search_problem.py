"""
Problema de busca para o simpleai: o drone na cidade.

Resumo para quem lê o código:
- Cada *estado* é (x, y, z, bateria, t): posição na grelha, bateria restante, instante
  discreto do simulador (o relógio avança em cada ação).
- *Objetivo*: mesma célula que o destino definido na instância, com bateria >= 1.
- *Ações*: andar para um vizinho 6-conexo; esperar um instante; recarregar até ao
  máximo se estiveres numa estação (tudo isto consome tempo e/ou “energia” no custo).
- *Custo* de um passo: combinação linear tempo + energia (pesos na UrbanInstance).
- *Heurística*: distância Manhattan até ao destino × custo mínimo de um movimento
  (relaxação: ignora obstáculos e TNFZ na estimativa, para não superestimar).
"""

from __future__ import annotations

import math

from simpleai.search import SearchProblem

from src.environment import MOVES_6, UrbanInstance, manhattan

State = tuple[int, int, int, int, int]


class DroneUrbanSearchProblem(SearchProblem):
    """
    Estado: (x, y, z, battery, t).
    Objetivo: estar na célula goal com bateria >= 1.
    """

    def __init__(self, instance: UrbanInstance):
        self.instance = instance
        x, y, z = instance.start
        self.initial_state = (x, y, z, instance.initial_battery, 0)
        self.goal_cell = instance.goal
        self._c_min_move = _compute_min_move_cost(instance)
        super().__init__(self.initial_state)

    def is_goal(self, state: State) -> bool:
        x, y, z, b, _t = state
        return (x, y, z) == self.goal_cell and b >= 1

    def heuristic(self, state: State) -> float:
        x, y, z, b, _t = state
        dist = manhattan((x, y, z), self.goal_cell)
        return float(dist) * self._c_min_move

    def actions(self, state: State):
        inst = self.instance
        x, y, z, b, t = state
        acts = []

        if t + 1 <= inst.time_horizon:
            if not inst.is_forbidden(x, y, z, t + 1):
                nb = b - inst.hover_battery
                if nb >= 1:
                    acts.append(("wait",))

        if t + 1 <= inst.time_horizon:
            for dx, dy, dz in MOVES_6:
                nx, ny, nz = x + dx, y + dy, z + dz
                if not inst.in_bounds(nx, ny, nz) or inst.is_obstacle(nx, ny, nz):
                    continue
                if inst.is_forbidden(nx, ny, nz, t + 1):
                    continue
                drain = _move_battery_drain(inst, dx, dy, dz, nx, ny, nz)
                if b - drain >= 1:
                    acts.append(("move", dx, dy, dz))

        if (x, y, z) in inst.stations:
            rt = inst.recharge_duration
            if t + rt <= inst.time_horizon:
                if not any(
                    inst.is_forbidden(x, y, z, tau) for tau in range(t + 1, t + rt + 1)
                ):
                    acts.append(("recharge",))

        return acts

    def result(self, state: State, action) -> State:
        inst = self.instance
        x, y, z, b, t = state
        kind = action[0]
        if kind == "wait":
            return (x, y, z, b - inst.hover_battery, t + 1)
        if kind == "move":
            _k, dx, dy, dz = action
            nx, ny, nz = x + dx, y + dy, z + dz
            drain = _move_battery_drain(inst, dx, dy, dz, nx, ny, nz)
            return (nx, ny, nz, b - drain, t + 1)
        if kind == "recharge":
            rt = inst.recharge_duration
            return (x, y, z, inst.battery_max, t + rt)
        raise ValueError(f"Ação desconhecida: {action}")

    def cost(self, state: State, action, state2: State) -> float:
        inst = self.instance
        kind = action[0]
        if kind == "wait":
            dt = 1.0
            de = float(inst.hover_battery)
            return inst.w_time * dt + inst.w_energy * de
        if kind == "move":
            _k, dx, dy, dz = action
            x, y, z, _b, _t = state
            nx, ny, nz = x + dx, y + dy, z + dz
            dt, de = _move_time_energy(inst, dx, dy, dz, nx, ny, nz)
            return inst.w_time * dt + inst.w_energy * de
        if kind == "recharge":
            rt = inst.recharge_duration
            dt = float(rt)
            de = float(inst.recharge_idle_battery * rt)
            return inst.w_time * dt + inst.w_energy * de
        raise ValueError(f"Ação desconhecida: {action}")

    def value(self, state: State) -> float:
        return 0.0


def _wind_opposing(inst: UrbanInstance, dx: int, dy: int, dz: int, nx: int, ny: int, nz: int) -> float:
    w = inst.wind.get((nx, ny, nz), (0, 0, 0))
    dot = w[0] * dx + w[1] * dy + w[2] * dz
    return float(max(0, -dot))


def _move_time_energy(
    inst: UrbanInstance, dx: int, dy: int, dz: int, nx: int, ny: int, nz: int
) -> tuple[float, float]:
    opp = _wind_opposing(inst, dx, dy, dz, nx, ny, nz)
    dt = 1.0 + inst.wind_time_scale * opp
    de = float(inst.move_battery_base) + inst.wind_energy_scale * opp
    return dt, de


def _move_battery_drain(inst: UrbanInstance, dx: int, dy: int, dz: int, nx: int, ny: int, nz: int) -> int:
    _dt, de = _move_time_energy(inst, dx, dy, dz, nx, ny, nz)
    return int(math.ceil(de))


def _compute_min_move_cost(inst: UrbanInstance) -> float:
    """Menor custo de um movimento unitário válido (para h admissível com Manhattan)."""
    best = None
    for x in range(inst.nx):
        for y in range(inst.ny):
            for z in range(inst.nz):
                if inst.is_obstacle(x, y, z):
                    continue
                for dx, dy, dz in MOVES_6:
                    nx, ny, nz = x + dx, y + dy, z + dz
                    if not inst.in_bounds(nx, ny, nz) or inst.is_obstacle(nx, ny, nz):
                        continue
                    dt, de = _move_time_energy(inst, dx, dy, dz, nx, ny, nz)
                    c = inst.w_time * dt + inst.w_energy * de
                    if best is None or c < best:
                        best = c
    return float(best if best is not None else 1.0)
