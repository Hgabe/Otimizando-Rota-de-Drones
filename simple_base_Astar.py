import pygame
import random
import heapq
import time
import math

pygame.init()

# ---------------------------------------------------------------#
#                    CONFIGURAÇÕES SIMPLES                       #
# ---------------------------------------------------------------#
WIDTH, HEIGHT  = 900, 650
MAZE_SIZE      = 20
TILE_W         = 64
TILE_H         = 28
WALL_H         = 30      
PLAYER_H       = 30     
TREASURE_H     = 24
WATER_DEPTH    = 22
NUM_WIND_GROUPS = 20   
MAX_WIND_TILES  = 10     
WATER_COST      = 3     
WIND_COST       = 3   
NUM_TREASURES  = 10
WIN_TREASURES  = 10

OFFSET_X = WIDTH  // 2
OFFSET_Y = HEIGHT // 10 + MAZE_SIZE * TILE_H // 20

FPS        = 60
MOVE_DELAY = 200   

HEIGHT_PER_LEVEL = {
    0: 0,                          
    1: (TILE_H // 2) + WALL_H,     
    2: (TILE_H // 2) + WALL_H * 2
}

MIN_LEVEL_FOR_WALL = {
    1: 1,  
    2: 2,  
}

ANIM_SPEED_UP   = 0.4
ANIM_SPEED_DOWN = 0.2




# ---------------------------------------------------------------#
#                             PALETA                             #
# ---------------------------------------------------------------#
C_FLOOR_TOP  = (210, 220, 200)
C_FLOOR_R    = (160, 170, 152)
C_FLOOR_L    = (185, 195, 175)
C_WALL_TOP   = (130, 120, 110)
C_WALL_R     = ( 70,  62,  55)
C_WALL_L     = ( 95,  88,  80)
C_WALL2_TOP  = ( 90,  80,  75)   
C_WALL2_R    = ( 45,  38,  33)
C_WALL2_L    = ( 65,  58,  52)
C_WATER_TOP  = ( 60, 140, 210)
C_WATER_R    = ( 30,  90, 160)
C_WATER_L    = ( 45, 115, 185)
C_PLAYER_TOP = (220,  60,  60)
C_PLAYER_R   = (140,  25,  25)
C_PLAYER_L   = (180,  40,  40)
C_TREAS_TOP  = (255, 210,  40)
C_TREAS_R    = (180, 130,  10)
C_TREAS_L    = (220, 170,  20)
C_TREAS_LID  = (255, 230, 100)
C_WHITE      = (255, 255, 255)
C_GOLD       = (255, 210,  40)


# ---------------------------------------------------------------#
#                         COORDENADAS                            #
# ---------------------------------------------------------------#

def to_screen(col, row, height=0):
    sx = OFFSET_X + (col - row) * (TILE_W // 2)
    sy = OFFSET_Y + (col + row) * (TILE_H // 2) - height
    return sx, sy


def darken(color, amount):
    return tuple(max(0, c - amount) for c in color)


# ---------------------------------------------------------------#
#               MAPA DE ALTURAS E MULTIPLICADORES                #
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
#                     PRIMITIVOS DE DESENHO                      #
# ---------------------------------------------------------------#

def draw_iso_box(surface, col, row, box_h, top_col, right_col, left_col, outline=True, outline_alpha=60):
    cx, cy = to_screen(col, row)
    hw = TILE_W // 2
    hh = TILE_H // 2

    top_center = (cx,      cy - box_h)
    top_right  = (cx + hw, cy - box_h + hh)
    top_left   = (cx - hw, cy - box_h + hh)
    top_bottom = (cx,      cy - box_h + hh * 2)
    bot_center = (cx,      cy + hh)
    bot_right  = (cx + hw, cy + hh)
    bot_left   = (cx - hw, cy + hh)

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


def draw_iso_box_floating(surface, col, row, base_z, box_h, top_col, right_col, left_col, outline=True, outline_alpha=60):
    cx, cy = to_screen(col, row)   
    hw = TILE_W // 2
    hh = TILE_H // 2

    top_center = (cx,      cy - base_z - box_h)
    top_right  = (cx + hw, cy - base_z - box_h + hh)
    top_left   = (cx - hw, cy - base_z - box_h + hh)
    top_bottom = (cx,      cy - base_z - box_h + hh * 2)

    bot_center = (cx,      cy - base_z + hh)
    bot_right  = (cx + hw, cy - base_z + hh)
    bot_left   = (cx - hw, cy - base_z + hh)

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
    draw_iso_box(surface, col, row, TILE_H // 2, C_FLOOR_TOP, C_FLOOR_R, C_FLOOR_L, outline_alpha=20)


def draw_wall(surface, col, row, mult):
    altura = (TILE_H // 2) + (WALL_H * mult)

    if mult == 1:
        top_col, right_col, left_col = C_WALL_TOP, C_WALL_R, C_WALL_L
    else:
        top_col, right_col, left_col = C_WALL2_TOP, C_WALL2_R, C_WALL2_L

    draw_iso_box(surface, col, row, altura, top_col, right_col, left_col, outline_alpha=50)


def draw_water(surface, col, row):
    cx, cy = to_screen(col, row)
    hw = TILE_W // 2
    hh = TILE_H // 2
    depth = WATER_DEPTH - 20

    top_face   = [(cx-hw, cy+depth), (cx, cy-hh+depth), (cx+hw, cy+depth), (cx, cy+hh+depth)]
    right_face = [(cx+hw, cy+depth), (cx, cy+hh+depth), (cx, cy+hh+depth+8), (cx+hw, cy+depth+8)]
    left_face  = [(cx-hw, cy+depth), (cx, cy+hh+depth), (cx, cy+hh+depth+8), (cx-hw, cy+depth+8)]

    
    pygame.draw.polygon(surface, C_WATER_TOP, top_face,60)

    


def draw_objective(surface, col, row, pulse):
    cx, cy = to_screen(col, row)
    shadow = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 60),
                        (8, TILE_H//2, TILE_W-16, TILE_H//2))
    surface.blit(shadow, (cx - TILE_W//2, cy - TILE_H//4))

    h = TREASURE_H + int(4 * math.sin(pulse))
    draw_iso_box(surface, col, row, h, C_TREAS_TOP, C_TREAS_R, C_TREAS_L)
    lid_offset = int(6 + 3 * math.sin(pulse))
    draw_iso_box(surface, col, row, h + lid_offset,
                 C_TREAS_LID, darken(C_TREAS_LID, 40), darken(C_TREAS_LID, 20))

def draw_wind(surface, col, row):
    cx, cy = to_screen(col, row)
    hw = TILE_W // 2
    hh = TILE_H // 2
    box_h = WALL_H // 2

    top_face = [
        (cx - hw, cy - box_h + hh),
        (cx,      cy - box_h),
        (cx + hw, cy - box_h + hh),
        (cx,      cy - box_h + hh * 2),
    ]
    right_face = [
        (cx + hw, cy - box_h + hh),
        (cx,      cy - box_h + hh * 2),
        (cx,      cy + hh),
        (cx + hw, cy + hh),
    ]
    left_face = [
        (cx - hw, cy - box_h + hh),
        (cx,      cy - box_h + hh * 2),
        (cx,      cy + hh),
        (cx - hw, cy + hh),
    ]

    wind_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.polygon(wind_surf, (180, 220, 255, 120), left_face)
    pygame.draw.polygon(wind_surf, (150, 200, 255, 120), right_face)
    pygame.draw.polygon(wind_surf, (200, 230, 255, 120), top_face)
    surface.blit(wind_surf, (0, 0))

# ---------------------------------------------------------------#
#                       DRONE — DESENHO                          #
# ---------------------------------------------------------------#




def draw_drone(surface, col, row, drone_z_px):
    sx, sy = to_screen(col, row)

    shadow_alpha = max(15, 110 - int(drone_z_px * 0.8))
    shadow = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, shadow_alpha), (8, TILE_H//2, TILE_W-16, TILE_H//2))
    surface.blit(shadow, (sx - TILE_W//2, sy - TILE_H//4))

    draw_iso_box_floating(surface, col, row, base_z  = drone_z_px, box_h   = PLAYER_H, top_col = C_PLAYER_TOP, right_col = C_PLAYER_R, left_col  = C_PLAYER_L)


# ---------------------------------------------------------------#
#                               HUD                              #
# ---------------------------------------------------------------#

def draw_hud(surface, score, t_coll, total, steps, level, drone_z_px, small_font):
    pad = 16
    panel_w, panel_h = 250, 140
    hud = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    hud.fill((12, 16, 28, 210))
    pygame.draw.rect(hud, (60, 80, 120, 180), (0, 0, panel_w, panel_h), 1)
    surface.blit(hud, (pad, pad))

    cor_level = [(100, 255, 100), (255, 210, 40), (255, 80, 80)][level]

    lines = [
        (f"PONTOS:    {score:+d}",          C_WHITE,    0),
        (f"OBJETIVOS: {t_coll}/{total}",    C_GOLD,    28),
        (f"PASSOS:    {steps}",             (160,200,255), 56),
        (f"NIVEL:     {level}  ({int(drone_z_px)}px)", cor_level, 84),
    ]
    for text, color, dy in lines:
        surf = small_font.render(text, True, color)
        surface.blit(surf, (pad + 12, pad + 10 + dy))


def draw_message(surface, text, font, w, h):
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surface.blit(overlay, (0, 0))
    msg = font.render(text, True, C_GOLD)
    surface.blit(msg, (w//2 - msg.get_width()//2, h//2 - msg.get_height()//2))

def a_star_3d(start_pos, start_level, goals, mult_map, water, wind, maze_size):

    def min_level_for_cell(pos):
        mult = mult_map.get(pos, 0)   
        return MIN_LEVEL_FOR_WALL.get(mult, 0)

    def is_valid_pos(col, row):
        return 0 <= col < maze_size and 0 <= row < maze_size

    def heuristic(pos, level):
        dist_min = min(abs(pos[0]-t[0]) + abs(pos[1]-t[1]) for t in goals)
        descent_cost = level   
        return dist_min + descent_cost

    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    start = (start_pos[0], start_pos[1], start_level)

    open_list = []
    heapq.heappush(open_list, (0, start, []))

    g = {start: 0}
    visited = set()

    while open_list:
        _, cur, actions = heapq.heappop(open_list)
        col, row, level = cur

        if (col, row) in goals and level == 0:
            return actions

        if cur in visited:
            continue
        visited.add(cur)

        for d in directions:
            nc, nr = col + d[0], row + d[1]
            if not is_valid_pos(nc, nr):
                continue

            dest = (nc, nr)
            required_level = min_level_for_cell(dest)

            if level < required_level:
                continue

            water_cost    = 3 if dest in water else 0
            wind_levels   = wind.get(dest, frozenset())
            wind_cost_val = WIND_COST if level in wind_levels else 0
            cost          = 1 + water_cost + wind_cost_val

            next_state = (nc, nr, level)
            new_g = g[cur] + cost

            if next_state not in g or new_g < g[next_state]:
                g[next_state] = new_g
                pri = new_g + heuristic(dest, level)
                new_action = {'type': 'move', 'direction': d}
                heapq.heappush(open_list, (pri, next_state, actions + [new_action]))

        if level < 2:
            new_level = level + 1
            cost      = 1
            next_state = (col, row, new_level)
            new_g = g[cur] + cost

            if next_state not in g or new_g < g[next_state]:
                g[next_state] = new_g
                pri = new_g + heuristic((col, row), new_level)
                new_action = {'type': 'rise', 'levels': 1}
                heapq.heappush(open_list, (pri, next_state, actions + [new_action]))

        if level > 0:
            new_level = level - 1
            required_level  = min_level_for_cell((col, row))

            if new_level >= required_level:
                cost      = 1
                next_state = (col, row, new_level)
                new_g = g[cur] + cost

                if next_state not in g or new_g < g[next_state]:
                    g[next_state] = new_g
                    pri = new_g + heuristic((col, row), new_level)
                    new_action = {'type': 'descend', 'levels': 1}
                    heapq.heappush(open_list, (pri, next_state, actions + [new_action]))

    return None   


# ---------------------------------------------------------------#
#                       GERAÇÃO DO MAPA                          #
# ---------------------------------------------------------------#

def generate_map(maze_size, num_treasures):
    used = set()

    drone_pos = (random.randint(1, maze_size - 2),
                 random.randint(1, maze_size - 2))
    used.add(drone_pos)

    treasures = set()
    while len(treasures) < num_treasures:
        p = (random.randint(0, maze_size - 1),
             random.randint(0, maze_size - 1))
        if p not in used:
            treasures.add(p)
            used.add(p)

    walls = set()
    for i in range(maze_size):
        for j in range(maze_size):
            p = (i, j)
            if p not in used and random.random() < 0.22:
                walls.add(p)

    water = set()
    wx = random.randint(0, maze_size - 4)
    wy = random.randint(0, maze_size - 4)
    for i in range(wx, wx + random.randint(2, 4)):
        for j in range(wy, wy + random.randint(2, 4)):
            p = (i % maze_size, j % maze_size)
            if p not in used and p not in walls:
                water.add(p)

    mult_map, height_map = build_wall_data(walls)

    wind = {}
    for _ in range(NUM_WIND_GROUPS):
        
        group_levels = frozenset(random.sample([0, 1, 2], k=random.randint(1, 3)))

        col = random.randint(0, maze_size - 1)
        row = random.randint(0, maze_size - 1)

        for _ in range(random.randint(1, MAX_WIND_TILES)):
            p = (col, row)
            if p not in used and p not in walls:
                
                wind[p] = wind[p] | group_levels if p in wind else group_levels

           
            d = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
            col = max(0, min(maze_size - 1, col + d[0]))
            row = max(0, min(maze_size - 1, row + d[1]))

    return drone_pos, treasures, walls, water, mult_map, height_map, wind


# ---------------------------------------------------------------#
#                      ORDEM DE RENDERIZAÇÃO                     #
# ---------------------------------------------------------------#

def render_order(maze_size):
    cells = []
    for s in range(2 * maze_size - 1):
        for col in range(s + 1):
            row = s - col
            if 0 <= col < maze_size and 0 <= row < maze_size:
                cells.append((col, row))
    return cells


# ---------------------------------------------------------------#
#                        LOOP PRINCIPAL                          #
# ---------------------------------------------------------------#

def run_game():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Drone Maze 3D")
    clock = pygame.time.Clock()

    try:
        font       = pygame.font.SysFont("consolas", 32, bold=True)
        small_font = pygame.font.SysFont("consolas", 18)
    except:
        font       = pygame.font.SysFont(None, 36)
        small_font = pygame.font.SysFont(None, 22)

    drone_pos, treasures, walls, water, mult_map, height_map, wind = generate_map(MAZE_SIZE, NUM_TREASURES)
    order = render_order(MAZE_SIZE)

    drone_level = 0         
    drone_z_px  = 0.0        
    drone_col, drone_row = drone_pos

    score  = 0
    steps  = 0
    t_coll = 0
    pulse  = 0.0

    
    action_queue = []
    action_timer = 0

    running   = True
    game_over = False
    win_msg   = ""
    start_time = time.perf_counter()

    bg = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        r = int(18 + (y / HEIGHT) * 10)
        g = int(22 + (y / HEIGHT) * 12)
        b = int(36 + (y / HEIGHT) * 20)
        pygame.draw.line(bg, (r, g, b), (0, y), (WIDTH, y))

    while running:
        dt = clock.tick(FPS)
        pulse += dt * 0.003

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                return run_game()

        if not game_over and not action_queue:
            result = a_star_3d((drone_col, drone_row), drone_level,treasures, mult_map, water, wind, MAZE_SIZE)
            if result:
                action_queue = result
            else:
                game_over = True
                win_msg   = "SEM CAMINHO!"

        if not game_over and action_queue:
            action_timer += dt
            if action_timer >= MOVE_DELAY:
                action_timer = 0
                action = action_queue.pop(0)

                if action['type'] == 'move':
                    dx, dy = action['direction']
                    nx, ny = drone_col + dx, drone_row + dy
                    drone_col, drone_row = nx, ny
                    drone_pos = (drone_col, drone_row)
                    score -= 1
                    steps += 1
                    wind_levels = wind.get(drone_pos, frozenset())

                    if drone_level in wind_levels:
                        score -= WIND_COST
                    if drone_pos in water:
                        score -= WATER_COST

                    if drone_pos in treasures and drone_level == 0:
                        treasures.discard(drone_pos)
                        t_coll += 1
                        score  += 50
                        action_queue.clear()   

                    if t_coll >= WIN_TREASURES:
                        game_over = True
                        elapsed   = time.perf_counter() - start_time
                        win_msg   = (f"VITÓRIA! {t_coll} obj | " f"{score:+d} pts | {elapsed:.1f}s")

                elif action['type'] == 'rise':
                    drone_level += 1
                    score -= 1
                    steps += 1

                elif action['type'] == 'descend':
                    drone_level -= 1
                    score -= 1
                    steps += 1

                    if drone_pos in treasures and drone_level == 0:
                        treasures.discard(drone_pos)
                        t_coll += 1
                        score  += 50
                        action_queue.clear()

                        if t_coll >= WIN_TREASURES:
                            game_over = True
                            elapsed   = time.perf_counter() - start_time
                            win_msg   = (f"VITÓRIA! {t_coll} obj | " f"{score:+d} pts | {elapsed:.1f}s")

        target_px = float(HEIGHT_PER_LEVEL[drone_level])

        if drone_z_px < target_px:
            drone_z_px = min(target_px, drone_z_px + ANIM_SPEED_UP * dt)
        else:
            drone_z_px = max(target_px, drone_z_px - ANIM_SPEED_DOWN * dt)

        screen.blit(bg, (0, 0))

        for (col, row) in order:
            pos = (col, row)

            if pos in walls:
                draw_wall(screen, col, row, mult_map.get(pos, 1))
            elif pos in water:
                draw_water(screen, col, row)
            else:
                draw_floor(screen, col, row)

            if pos in treasures:
                draw_objective(screen, col, row, pulse + col + row)

            if pos == (drone_col, drone_row):
                draw_drone(screen, col, row, drone_z_px)

        for (col, row) in order:
            if (col, row) in wind:
                draw_wind(screen, col, row)

        draw_hud(screen, score, t_coll, WIN_TREASURES, steps, drone_level, drone_z_px, small_font)

        hint = small_font.render("R = reiniciar", True, (100, 120, 160))
        screen.blit(hint, (WIDTH - hint.get_width() - 16, HEIGHT - 30))

        if game_over:
            draw_message(screen, win_msg, font, WIDTH, HEIGHT)

        pygame.display.flip()

    pygame.quit()
    return score, t_coll, steps


if __name__ == "__main__":
    run_game()