import pygame
import random
import time
import math
import csv
import os
from collections import deque
from simpleai.search import SearchProblem, astar, greedy

pygame.init()

# ---------------------------------------------------------------#
#                    CONFIGURAÇÕES                               #
# ---------------------------------------------------------------#
WIDTH, HEIGHT       = 900, 650
MAZE_SIZE           = 20
TILE_W              = 64
TILE_H              = 28
WALL_H              = 30
PLAYER_H            = 30
TREASURE_H          = 24
NUM_WIND_GROUPS     = 10
MAX_WIND_TILES      = 10
R_ZONE_COST         = 3000
WIND_COST           = 3
WIN_DELIVERIES      = 5        
NUM_CHARGE_STATIONS = 5
CSV_FILE            = "resultados.csv" 
MIN_DIST            = 5        
MAX_BATTERY         = int(MAZE_SIZE * MAZE_SIZE * 0.15)

OFFSET_X = WIDTH  // 2
OFFSET_Y = HEIGHT // 10 + MAZE_SIZE * TILE_H // 20

FPS        = 60
MOVE_DELAY = 0

HEIGHT_PER_LEVEL = {
    0: 0,
    1: (TILE_H // 2) + WALL_H,
    2: (TILE_H // 2) + WALL_H * 2,
}
MIN_LEVEL_FOR_WALL = {1: 1, 2: 2}

ANIM_SPEED_UP   = 0.4
ANIM_SPEED_DOWN = 0.2

# ---------------------------------------------------------------#
#                          PALETA                                #
# ---------------------------------------------------------------#
C_FLOOR_TOP    = (210, 220, 200)
C_FLOOR_R      = (160, 170, 152)
C_FLOOR_L      = (185, 195, 175)
C_WALL_TOP     = (130, 120, 110)
C_WALL_R       = ( 70,  62,  55)
C_WALL_L       = ( 95,  88,  80)
C_WALL2_TOP    = ( 90,  80,  75)
C_WALL2_R      = ( 45,  38,  33)
C_WALL2_L      = ( 65,  58,  52)
C_PLAYER_TOP   = (220,  60,  60)
C_PLAYER_R     = (140,  25,  25)
C_PLAYER_L     = (180,  40,  40)
C_COLLECT_TOP  = (100, 180, 255)   
C_COLLECT_R    = ( 50, 110, 180)
C_COLLECT_L    = ( 70, 145, 220)
C_GOAL_TOP     = (255, 210,  40)   
C_GOAL_R       = (180, 130,  10)
C_GOAL_L       = (220, 170,  20)
C_GOAL_LID     = (255, 230, 100)
C_CHARGE_TOP   = ( 80, 220, 120)
C_CHARGE_R     = ( 40, 150,  80)
C_CHARGE_L     = ( 60, 185, 100)
C_WHITE        = (255, 255, 255)
C_GOLD         = (255, 210,  40)
C_BATTERY_OK   = ( 80, 220, 120)
C_BATTERY_LOW  = (255, 100,  60)
C_CARGO_YES    = ( 80, 255, 180)   
C_CARGO_NO     = (160, 160, 160)   


# ---------------------------------------------------------------#
#                        COORDENADAS                             #
# ---------------------------------------------------------------#
def to_screen(col, row, height=0):
    sx = OFFSET_X + (col - row) * (TILE_W // 2)
    sy = OFFSET_Y + (col + row) * (TILE_H // 2) - height
    return sx, sy

def darken(color, amount):
    return tuple(max(0, c - amount) for c in color)

def lighten(color, amount):
    return tuple(min(255, c + amount) for c in color)


# ---------------------------------------------------------------#
#                   DADOS DOS MUROS                              #
# ---------------------------------------------------------------#
def build_wall_data(walls):
    mult_map   = {}
    height_map = {}
    for (col, row) in walls:
        state = random.getstate()
        random.seed(col * 1000 + row)
        mult = random.randint(1, 2)
        random.setstate(state)
        mult_map[(col, row)]   = mult
        height_map[(col, row)] = (TILE_H // 2) + (WALL_H * mult)
    return mult_map, height_map


# ---------------------------------------------------------------#
#                   VALIDAÇÃO DE ACESSIBILIDADE                  #
# ---------------------------------------------------------------#
def is_accessible(drone_pos, collect_pos, goal_pos, charge_stations, walls, restricted_zone, maze_size):

    blocked = walls | restricted_zone

    def bfs_reachable(start):
        visited = {start}
        queue   = deque([start])
        while queue:
            col, row = queue.popleft()
            for dc, dr in [(-1,0),(1,0),(0,-1),(0,1)]:
                nc, nr = col+dc, row+dr
                npos = (nc, nr)
                if (0 <= nc < maze_size and 0 <= nr < maze_size
                        and npos not in visited
                        and npos not in blocked):
                    visited.add(npos)
                    queue.append(npos)
        return visited

    reachable = bfs_reachable(drone_pos)

    critical = [collect_pos, goal_pos] + list(charge_stations)
    return all(p in reachable for p in critical)


# ---------------------------------------------------------------#
#              GERAÇÃO DE UM NOVO CICLO (coleta + objetivo)      #
# ---------------------------------------------------------------#
def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


def generate_cycle(drone_pos, charge_stations, walls, maze_size, min_dist):

    all_fixed = {drone_pos} | charge_stations | walls

    def random_free_pos(excluded):
        for _ in range(2000):
            p = (random.randint(0, maze_size-1),
                 random.randint(0, maze_size-1))
            if p in excluded:
                continue
            if any(manhattan(p, e) < min_dist for e in excluded
                   if e not in walls):
                continue
            return p
        return None

    collect_pos = random_free_pos(all_fixed)
    if collect_pos is None:
        return None, None, set()

    goal_pos = random_free_pos(all_fixed | {collect_pos})
    if goal_pos is None:
        return None, None, set()

    for _ in range(50):
        restricted_zone = set()
        wx = random.randint(0, maze_size - 4)
        wy = random.randint(0, maze_size - 4)
        w  = random.randint(2, 6)
        h  = random.randint(2, 6)
        for i in range(wx, wx + w):
            for j in range(wy, wy + h):
                p = (i % maze_size, j % maze_size)
                if p in all_fixed or p == collect_pos or p == goal_pos:
                    continue
                if manhattan(p, drone_pos)   < 2: continue
                if manhattan(p, collect_pos) < 2: continue
                if manhattan(p, goal_pos)    < 2: continue
                if p not in walls:
                    restricted_zone.add(p)

        if is_accessible(drone_pos, collect_pos, goal_pos,
                         charge_stations, walls, restricted_zone, maze_size):
            return collect_pos, goal_pos, restricted_zone

    return collect_pos, goal_pos, set()


# ---------------------------------------------------------------#
#                    PRIMITIVOS DE DESENHO                       #
# ---------------------------------------------------------------#
def draw_iso_box(surface, col, row, box_h, top_col, right_col, left_col,
                 outline=True, outline_alpha=60):
    cx, cy = to_screen(col, row)
    hw, hh = TILE_W//2, TILE_H//2
    top_center = (cx,      cy-box_h)
    top_right  = (cx+hw,   cy-box_h+hh)
    top_left   = (cx-hw,   cy-box_h+hh)
    top_bottom = (cx,      cy-box_h+hh*2)
    bot_center = (cx,      cy+hh)
    bot_right  = (cx+hw,   cy+hh)
    bot_left   = (cx-hw,   cy+hh)
    top_face   = [top_left, top_center, top_right, top_bottom]
    right_face = [top_right, top_bottom, bot_center, bot_right]
    left_face  = [top_left,  top_bottom, bot_center, bot_left]
    pygame.draw.polygon(surface, left_col,  left_face)
    pygame.draw.polygon(surface, right_col, right_face)
    pygame.draw.polygon(surface, top_col,   top_face)
    if outline:
        oc = darken(top_col, outline_alpha)
        pygame.draw.polygon(surface, oc, top_face,   1)
        pygame.draw.polygon(surface, oc, right_face, 1)
        pygame.draw.polygon(surface, oc, left_face,  1)


def draw_iso_box_floating(surface, col, row, base_z, box_h,
                          top_col, right_col, left_col,
                          outline=True, outline_alpha=60):
    cx, cy = to_screen(col, row)
    hw, hh = TILE_W//2, TILE_H//2
    top_center = (cx,    cy-base_z-box_h)
    top_right  = (cx+hw, cy-base_z-box_h+hh)
    top_left   = (cx-hw, cy-base_z-box_h+hh)
    top_bottom = (cx,    cy-base_z-box_h+hh*2)
    bot_center = (cx,    cy-base_z+hh)
    bot_right  = (cx+hw, cy-base_z+hh)
    bot_left   = (cx-hw, cy-base_z+hh)
    top_face   = [top_left, top_center, top_right, top_bottom]
    right_face = [top_right, top_bottom, bot_center, bot_right]
    left_face  = [top_left,  top_bottom, bot_center, bot_left]
    pygame.draw.polygon(surface, left_col,  left_face)
    pygame.draw.polygon(surface, right_col, right_face)
    pygame.draw.polygon(surface, top_col,   top_face)
    if outline:
        oc = darken(top_col, outline_alpha)
        pygame.draw.polygon(surface, oc, top_face,   1)
        pygame.draw.polygon(surface, oc, right_face, 1)
        pygame.draw.polygon(surface, oc, left_face,  1)


# ---------------------------------------------------------------#
#                           TILES                                #
# ---------------------------------------------------------------#
def draw_floor(surface, col, row):
    draw_iso_box(surface, col, row, TILE_H//2,
                 C_FLOOR_TOP, C_FLOOR_R, C_FLOOR_L, outline_alpha=20)


def draw_wall(surface, col, row, mult):
    altura = (TILE_H//2) + (WALL_H * mult)
    if mult == 1:
        tc, rc, lc = C_WALL_TOP, C_WALL_R, C_WALL_L
    else:
        tc, rc, lc = C_WALL2_TOP, C_WALL2_R, C_WALL2_L
    draw_iso_box(surface, col, row, altura, tc, rc, lc, outline_alpha=50)


def draw_restricted_zone(surface, col, row):
    cx, cy = to_screen(col, row)
    hw, hh = TILE_W//2, TILE_H//2
    box_h  = 75
    top_face   = [(cx-hw,cy-box_h+hh),(cx,cy-box_h),(cx+hw,cy-box_h+hh),(cx,cy-box_h+hh*2)]
    right_face = [(cx+hw,cy-box_h+hh),(cx,cy-box_h+hh*2),(cx,cy+hh),(cx+hw,cy+hh)]
    left_face  = [(cx-hw,cy-box_h+hh),(cx,cy-box_h+hh*2),(cx,cy+hh),(cx-hw,cy+hh)]
    zs = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.polygon(zs, (100,30,40,80), left_face)
    pygame.draw.polygon(zs, ( 80,20,30,80), right_face)
    pygame.draw.polygon(zs, (140,50,60,80), top_face)
    surface.blit(zs, (0,0))


def draw_collect_point(surface, col, row, pulse):
    cx, cy = to_screen(col, row)
    shadow = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0,0,0,60),
                        (8, TILE_H//2, TILE_W-16, TILE_H//2))
    surface.blit(shadow, (cx-TILE_W//2, cy-TILE_H//4))
    h = 20 + int(4 * math.sin(pulse))
    draw_iso_box(surface, col, row, h, C_COLLECT_TOP, C_COLLECT_R, C_COLLECT_L)
    lid = int(5 + 3 * math.sin(pulse))
    draw_iso_box(surface, col, row, h+lid,
                 lighten(C_COLLECT_TOP, 30),
                 lighten(C_COLLECT_R,   10),
                 lighten(C_COLLECT_L,   20))


def draw_goal(surface, col, row, pulse):
    cx, cy = to_screen(col, row)
    shadow = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0,0,0,60),
                        (8, TILE_H//2, TILE_W-16, TILE_H//2))
    surface.blit(shadow, (cx-TILE_W//2, cy-TILE_H//4))
    h = TREASURE_H + int(4 * math.sin(pulse))
    draw_iso_box(surface, col, row, h, C_GOAL_TOP, C_GOAL_R, C_GOAL_L)
    lid = int(6 + 3 * math.sin(pulse))
    draw_iso_box(surface, col, row, h+lid,
                 C_GOAL_LID, darken(C_GOAL_LID, 40), darken(C_GOAL_LID, 20))


def draw_charge_station(surface, col, row, pulse):
    cx, cy = to_screen(col, row)
    shadow = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0,0,0,60),
                        (8, TILE_H//2, TILE_W-16, TILE_H//2))
    surface.blit(shadow, (cx-TILE_W//2, cy-TILE_H//4))
    h = 20 + int(3 * math.sin(pulse))
    draw_iso_box(surface, col, row, h, C_CHARGE_TOP, C_CHARGE_R, C_CHARGE_L)
    lid = int(4 + 2 * math.sin(pulse))
    draw_iso_box(surface, col, row, h+lid,
                 lighten(C_CHARGE_TOP, 30),
                 lighten(C_CHARGE_R,   10),
                 lighten(C_CHARGE_L,   20))


def draw_wind(surface, col, row):
    cx, cy = to_screen(col, row)
    hw, hh = TILE_W//2, TILE_H//2
    box_h  = WALL_H//2
    top_face   = [(cx-hw,cy-box_h+hh),(cx,cy-box_h),(cx+hw,cy-box_h+hh),(cx,cy-box_h+hh*2)]
    right_face = [(cx+hw,cy-box_h+hh),(cx,cy-box_h+hh*2),(cx,cy+hh),(cx+hw,cy+hh)]
    left_face  = [(cx-hw,cy-box_h+hh),(cx,cy-box_h+hh*2),(cx,cy+hh),(cx-hw,cy+hh)]
    ws = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.polygon(ws, (180,220,255,120), left_face)
    pygame.draw.polygon(ws, (150,200,255,120), right_face)
    pygame.draw.polygon(ws, (200,230,255,120), top_face)
    surface.blit(ws, (0,0))


# ---------------------------------------------------------------#
#                       DRONE — DESENHO                          #
# ---------------------------------------------------------------#
def draw_drone(surface, col, row, drone_z_px, carrying):
    sx, sy = to_screen(col, row)
    shadow_alpha = max(15, 110 - int(drone_z_px * 0.8))
    shadow = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0,0,0,shadow_alpha),
                        (8, TILE_H//2, TILE_W-16, TILE_H//2))
    surface.blit(shadow, (sx-TILE_W//2, sy-TILE_H//4))

    if carrying:
        tc = (255, 120, 120)
        rc = (200,  60,  60)
        lc = (230,  80,  80)
    else:
        tc, rc, lc = C_PLAYER_TOP, C_PLAYER_R, C_PLAYER_L

    draw_iso_box_floating(surface, col, row,
                          base_z=drone_z_px, box_h=PLAYER_H,
                          top_col=tc, right_col=rc, left_col=lc)


# ---------------------------------------------------------------#
#                            HUD                                 #
# ---------------------------------------------------------------#
def draw_hud(surface, score, deliveries, total, steps, level,
             drone_z_px, battery, carrying, small_font):
    pad = 16
    panel_w, panel_h = 270, 200
    hud = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    hud.fill((12, 16, 28, 210))
    pygame.draw.rect(hud, (60, 80, 120, 180), (0, 0, panel_w, panel_h), 1)
    surface.blit(hud, (pad, pad))

    cor_level   = [(100,255,100),(255,210,40),(255,80,80)][level]
    bat_pct     = battery / MAX_BATTERY
    bat_color   = C_BATTERY_OK if bat_pct > 0.30 else C_BATTERY_LOW
    cargo_color = C_CARGO_YES if carrying else C_CARGO_NO
    cargo_text  = "SIM" if carrying else "NÃO"

    lines = [
        (f"PONTOS:    {score:+d}",               C_WHITE,       0),
        (f"ENTREGAS:  {deliveries}/{total}",      C_GOLD,       28),
        (f"PASSOS:    {steps}",                   (160,200,255), 56),
        (f"NIVEL:     {level} ({int(drone_z_px)}px)", cor_level, 84),
        (f"BATERIA:   {battery}/{MAX_BATTERY}",   bat_color,   112),
        (f"COM CARGA: {cargo_text}",              cargo_color, 140),
    ]
    for text, color, dy in lines:
        surf = small_font.render(text, True, color)
        surface.blit(surf, (pad+12, pad+10+dy))

    bar_x = pad+12
    bar_y = pad+176
    bar_w = panel_w-24
    bar_h = 8
    pygame.draw.rect(surface, (40,40,60), (bar_x, bar_y, bar_w, bar_h))
    pygame.draw.rect(surface, bat_color,  (bar_x, bar_y, int(bar_w*bat_pct), bar_h))


def draw_message(surface, text, font, w, h):
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0,0,0,160))
    surface.blit(overlay, (0,0))
    msg = font.render(text, True, C_GOLD)
    surface.blit(msg, (w//2-msg.get_width()//2, h//2-msg.get_height()//2))


# ---------------------------------------------------------------#
#                              A* 3D                             #
# ---------------------------------------------------------------#

class DroneProblem(SearchProblem):

    def __init__(self, initial_state, goals, charge_stations,
                 mult_map, restricted_zone, wind, maze_size):
        # Chama o construtor do simpleai passando o estado inicial
        super().__init__(initial_state=initial_state)
        self.nodes_expanded  = 0   # contador de nós expandidos
        self.goals           = goals
        self.charge_stations = charge_stations
        self.mult_map        = mult_map
        self.restricted_zone = restricted_zone
        self.wind            = wind
        self.maze_size       = maze_size

    def _min_level_for_cell(self, pos):
        mult = self.mult_map.get(pos, 0)
        return MIN_LEVEL_FOR_WALL.get(mult, 0)

    def actions(self, state):
        self.nodes_expanded += 1
        col, row, level, battery = state
        valid_actions = []
        if battery == 0:
            if (col, row) in self.charge_stations and level == 0:
                pass 
            else:
                return []  

        directions = [(-1,0),(1,0),(0,-1),(0,1)]

        for d in directions:
            nc, nr = col+d[0], row+d[1]
            if not (0 <= nc < self.maze_size and 0 <= nr < self.maze_size):
                continue
            dest = (nc, nr)
            if level < self._min_level_for_cell(dest):
                continue
            new_battery = battery - 1
            if dest in self.charge_stations and level == 0:
                new_battery = MAX_BATTERY
            if new_battery < 0:
                continue
            valid_actions.append({'type': 'move', 'direction': d})

        if level < 2 and battery > 0:
            valid_actions.append({'type': 'rise', 'levels': 1})

        if level > 0 and battery > 0:
            new_level = level - 1
            if new_level >= self._min_level_for_cell((col, row)):
                valid_actions.append({'type': 'descend', 'levels': 1})

        return valid_actions

    def result(self, state, action):
        col, row, level, battery = state

        if action['type'] == 'move':
            d = action['direction']
            nc, nr = col+d[0], row+d[1]
            new_battery = battery - 1
            if (nc, nr) in self.charge_stations and level == 0:
                new_battery = MAX_BATTERY
            return (nc, nr, level, new_battery)

        elif action['type'] == 'rise':
            return (col, row, level+1, battery-1)

        elif action['type'] == 'descend':
            new_level   = level - 1
            new_battery = battery - 1
            if (col, row) in self.charge_stations and new_level == 0:
                new_battery = MAX_BATTERY
            return (col, row, new_level, new_battery)

        return state

    def is_goal(self, state):
        col, row, level, battery = state
        return (col, row) in self.goals and level == 0

    def heuristic(self, state):
        col, row, level, battery = state
        dist_to_goal = min(
            abs(col-t[0]) + abs(row-t[1]) for t in self.goals
        )
        custo_base   = dist_to_goal + level
        bat_restante = battery - custo_base
        threshold    = MAX_BATTERY * 0.20
        if bat_restante < threshold:
            return custo_base + (threshold - bat_restante) * 0.5
        return custo_base

    def cost(self, state1, action, state2):
        if action['type'] == 'move':
            col2, row2, _, _ = state2
            dest = (col2, row2)
            rzone_cost    = R_ZONE_COST if dest in self.restricted_zone else 0
            _, _, level1, _ = state1
            wind_levels   = self.wind.get(dest, frozenset())
            wind_cost_val = WIND_COST if level1 in wind_levels else 0
            return 1 + rzone_cost + wind_cost_val
        return 1 


def a_star_3d(start_pos, start_level, start_battery, goals, charge_stations, mult_map, restricted_zone, wind, maze_size, _return_nodes=False, algorithm='astar'):
    initial_state = (start_pos[0], start_pos[1], start_level, start_battery)

    problem = DroneProblem(
        initial_state  = initial_state,
        goals          = goals,
        charge_stations= charge_stations,
        mult_map       = mult_map,
        restricted_zone= restricted_zone,
        wind           = wind,
        maze_size      = maze_size,
    )

    _search_fn = astar if algorithm == 'astar' else greedy
    result = _search_fn(problem, graph_search=True)

    actions_list = None if result is None else [
        action for action, state in result.path() if action is not None
    ]
    if _return_nodes:
        return actions_list, problem.nodes_expanded
    return actions_list


# ---------------------------------------------------------------#
#                       GERAÇÃO DO MAPA                          #
# ---------------------------------------------------------------#
def generate_map(maze_size, num_stations):
    used = set()

    drone_pos = (random.randint(1, maze_size-2),
                 random.randint(1, maze_size-2))
    used.add(drone_pos)

    charge_stations = set()
    while len(charge_stations) < num_stations:
        p = (random.randint(0, maze_size-1),
             random.randint(0, maze_size-1))
        if p not in used and manhattan(p, drone_pos) >= MIN_DIST:
            charge_stations.add(p)
            used.add(p)

    walls = set()
    for i in range(maze_size):
        for j in range(maze_size):
            p = (i, j)
            if p not in used and random.random() < 0.22:
                walls.add(p)

    mult_map, height_map = build_wall_data(walls)

    wind = {}
    for _ in range(NUM_WIND_GROUPS):
        group_levels = frozenset(
            random.sample([0,1,2], k=random.randint(1,3))
        )
        col = random.randint(0, maze_size-1)
        row = random.randint(0, maze_size-1)
        for _ in range(random.randint(1, MAX_WIND_TILES)):
            p = (col, row)
            if p not in used and p not in walls:
                wind[p] = wind[p] | group_levels if p in wind else group_levels
            d = random.choice([(0,1),(0,-1),(1,0),(-1,0)])
            col = max(0, min(maze_size-1, col+d[0]))
            row = max(0, min(maze_size-1, row+d[1]))

    return drone_pos, charge_stations, walls, mult_map, height_map, wind



# ---------------------------------------------------------------#
#                     EXPORTAÇÃO DE MÉTRICAS                     #
# ---------------------------------------------------------------#

_instancia_counter = [0]

def save_metrics(algoritmo, sucesso, custo, tempo_s, nos_expandidos, entregas):

    _instancia_counter[0] += 1
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "instancia", "algoritmo", "sucesso", "custo",
            "tempo_s", "nos_expandidos", "entregas",
            "max_battery", "maze_size", "num_estacoes", "num_entregas_alvo",
        ])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "instancia":         _instancia_counter[0],
            "algoritmo":         algoritmo,
            "sucesso":           sucesso,
            "custo":             custo,
            "tempo_s":           round(tempo_s, 4),
            "nos_expandidos":    nos_expandidos,
            "entregas":          entregas,
            "max_battery":       MAX_BATTERY,
            "maze_size":         MAZE_SIZE,
            "num_estacoes":      NUM_CHARGE_STATIONS,
            "num_entregas_alvo": WIN_DELIVERIES,
        })
    print(f"[CSV] instância {_instancia_counter[0]} | {algoritmo} | "
          f"sucesso={sucesso} | custo={custo} | "
          f"tempo={tempo_s:.2f}s | nós={nos_expandidos}")

# ---------------------------------------------------------------#
#                     ORDEM DE RENDERIZAÇÃO                      #
# ---------------------------------------------------------------#
def render_order(maze_size):
    cells = []
    for s in range(2*maze_size-1):
        for col in range(s+1):
            row = s - col
            if 0 <= col < maze_size and 0 <= row < maze_size:
                cells.append((col, row))
    return cells


# ---------------------------------------------------------------#
#                        LOOP PRINCIPAL                          #
# ---------------------------------------------------------------#
def run_game():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Drone Cargo 3D")
    clock  = pygame.time.Clock()

    try:
        font       = pygame.font.SysFont("consolas", 32, bold=True)
        small_font = pygame.font.SysFont("consolas", 18)
    except:
        font       = pygame.font.SysFont(None, 36)
        small_font = pygame.font.SysFont(None, 22)

    (drone_pos, charge_stations,
     walls, mult_map, height_map, wind) = generate_map(
        MAZE_SIZE, NUM_CHARGE_STATIONS
    )
    order = render_order(MAZE_SIZE)

    collect_pos, goal_pos, restricted_zone = generate_cycle(
        drone_pos, charge_stations, walls, MAZE_SIZE, MIN_DIST
    )

    drone_level   = 0
    drone_z_px    = 0.0
    drone_col, drone_row = drone_pos

    carrying  = False 

    battery    = MAX_BATTERY
    score      = 0
    steps      = 0
    deliveries = 0
    pulse      = 0.0

    action_queue = []
    action_timer = 0
    total_nodes_expanded = 0  

    running    = True
    game_over  = False
    win_msg    = ""
    start_time = time.perf_counter()

    bg = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        r = int(18 + (y/HEIGHT)*10)
        g = int(22 + (y/HEIGHT)*12)
        b = int(36 + (y/HEIGHT)*20)
        pygame.draw.line(bg, (r,g,b), (0,y), (WIDTH,y))

    while running:
        dt = clock.tick(FPS)
        pulse += dt * 0.003

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                return run_game()

        if not game_over and battery <= 0:
            game_over = True
            elapsed_fail = time.perf_counter() - start_time
            win_msg   = "SEM BATERIA! DRONE PERDIDO."
            save_metrics("astar", False, score, elapsed_fail,
                         total_nodes_expanded, deliveries)

        if not game_over and not action_queue:
            if not carrying:
                current_goals = {collect_pos}
            else:
                current_goals = {goal_pos}

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
                escape_test = a_star_3d(
                    dest_goal, 0, bat_apos,
                    charge_stations, charge_stations,
                    mult_map, restricted_zone, wind, MAZE_SIZE
                )
                if escape_test is None:
                    current_goals = charge_stations

            result, n_nodes = a_star_3d(
                (drone_col, drone_row), drone_level, battery,
                current_goals, charge_stations,
                mult_map, restricted_zone, wind, MAZE_SIZE,
                _return_nodes=True,
            )
            total_nodes_expanded += n_nodes
            if result:
                action_queue = result
            else:
                game_over = True
                elapsed_fail = time.perf_counter() - start_time
                win_msg   = "SEM CAMINHO!"
                save_metrics("astar", False, score, elapsed_fail,
                             total_nodes_expanded, deliveries)

        if not game_over and action_queue:
            action_timer += dt
            if action_timer >= MOVE_DELAY:
                action_timer = 0
                action = action_queue.pop(0)

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
                        action_queue.clear()

                    elif drone_pos == goal_pos and drone_level == 0 and carrying:
                        carrying    = False
                        deliveries += 1
                        score      += 50
                        action_queue.clear()

                        if deliveries >= WIN_DELIVERIES:
                            game_over = True
                            elapsed   = time.perf_counter() - start_time
                            win_msg   = (f"VITÓRIA! {deliveries} entregas | "
                                         f"{score:+d} pts | {elapsed:.1f}s")
                            save_metrics("astar", True, score, elapsed,
                                         total_nodes_expanded, deliveries)
                        else:
                            # Gera novo ciclo após entrega
                            collect_pos, goal_pos, restricted_zone = generate_cycle(
                                drone_pos, charge_stations, walls,
                                MAZE_SIZE, MIN_DIST
                            )

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
                        action_queue.clear()

                    elif drone_pos == goal_pos and drone_level == 0 and carrying:
                        carrying    = False
                        deliveries += 1
                        score      += 50
                        action_queue.clear()

                        if deliveries >= WIN_DELIVERIES:
                            game_over = True
                            elapsed   = time.perf_counter() - start_time
                            win_msg   = (f"VITÓRIA! {deliveries} entregas | "
                                         f"{score:+d} pts | {elapsed:.1f}s")
                            save_metrics("astar", True, score, elapsed,
                                         total_nodes_expanded, deliveries)
                        else:
                            collect_pos, goal_pos, restricted_zone = generate_cycle(
                                drone_pos, charge_stations, walls,
                                MAZE_SIZE, MIN_DIST
                            )

        target_px = float(HEIGHT_PER_LEVEL[drone_level])
        if drone_z_px < target_px:
            drone_z_px = min(target_px, drone_z_px + ANIM_SPEED_UP * dt)
        else:
            drone_z_px = max(target_px, drone_z_px - ANIM_SPEED_DOWN * dt)

        screen.blit(bg, (0,0))

        for (col, row) in order:
            pos = (col, row)

            if pos in walls:
                draw_wall(screen, col, row, mult_map.get(pos, 1))
            elif pos in restricted_zone:
                draw_restricted_zone(screen, col, row)
            else:
                draw_floor(screen, col, row)

            if pos in charge_stations:
                draw_charge_station(screen, col, row, pulse+col+row)

            if pos == collect_pos and not carrying:
                draw_collect_point(screen, col, row, pulse+col+row)

            if pos == goal_pos and carrying:
                draw_goal(screen, col, row, pulse+col+row)

            if pos == (drone_col, drone_row):
                draw_drone(screen, col, row, drone_z_px, carrying)

        for (col, row) in order:
            if (col, row) in wind:
                draw_wind(screen, col, row)

        draw_hud(screen, score, deliveries, WIN_DELIVERIES, steps,
                 drone_level, drone_z_px, battery, carrying, small_font)

        hint = small_font.render("R = reiniciar", True, (100,120,160))
        screen.blit(hint, (WIDTH-hint.get_width()-16, HEIGHT-30))

        if game_over:
            draw_message(screen, win_msg, font, WIDTH, HEIGHT)

        pygame.display.flip()

    pygame.quit()
    return score, deliveries, steps


if __name__ == "__main__":
    run_game()