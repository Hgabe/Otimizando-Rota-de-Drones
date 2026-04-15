import pygame
import random
import collections
import time
import heapq

pygame.init()

class Planner:
    def __init__(self):
        self.astral = {}

    def game(self):
        width, height = 500, 500
        maze_size = 20  
        block_size = width // maze_size

        BLACK = (0, 0, 0)
        WHITE = (255, 255, 255)
        RED = (255, 0, 0)
        BLUE = (0, 0, 255)

        NUM_TREASURES = 12

        
        screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption('Maze Treasure Hunt')

        
        try:
            treasure_image = pygame.image.load('treasure.png')
            treasure_image = pygame.transform.scale(treasure_image, (block_size, block_size))
        except pygame.error:
            print("Error loading treasure image")
            return
        
        
        player_pos = (random.randint(0, maze_size - 1), random.randint(0, maze_size - 1))
        used_coordinates = set()
        treasures = []

        while len(treasures) < NUM_TREASURES:
            x = random.randint(0, maze_size - 1)
            y = random.randint(0, maze_size - 1)
            if (x, y) not in used_coordinates:
                treasures.append((x, y))
                used_coordinates.add((x, y))

        treasures = tuple(treasures)

        
        def generate_walls():
            walls = []
            for i in range(1, maze_size - 1): 
                for j in range(1, maze_size - 1):
                    if (i, j) != player_pos and (i, j) not in treasures and random.choice([True, False, False]):
                        walls.append((i, j))
            return walls

        def generate_water(slope):
            water = []
            water_size = min(maze_size, maze_size) // 2
            start_x = random.randint(0, maze_size - water_size)
            start_y = random.randint(0, maze_size - water_size)
            
            
            for i in range(start_x, start_x + water_size // 2):
                for j in range(start_y, start_y + water_size):
                    water.append((i, j))
            return water

        slope = 0.5  
        water = generate_water(slope)
        walls = generate_walls()

        def a_star_move(player_pos, treasures, walls, water):

            def is_valid_move(x, y):
                if 0 <= x < maze_size and 0 <= y < maze_size:
                    if (x, y) not in walls:
                        return True
                return False

            def heuristic(a, b):
                return abs(a[0] - b[0]) + abs(a[1] - b[1])

            def move_cost(x, y):
                if (x, y) in water:
                    return 5
                return 1

            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)] 
            goal = min(treasures, key=lambda t: heuristic(player_pos, t))  
            open_list = []
            heapq.heappush(open_list, (0, player_pos, []))
            g_costs = {player_pos: 0}
            visited = set()

            while open_list:
                _, current_pos, path = heapq.heappop(open_list)
                if current_pos in treasures:
                    return path[0] if path else None 
                if current_pos in visited:
                    continue
                visited.add(current_pos)

                for direction in directions:
                    next_x = current_pos[0] + direction[0]
                    next_y = current_pos[1] + direction[1]
                    if is_valid_move(next_x, next_y):
                        next_pos = (next_x, next_y)
                        new_cost = g_costs[current_pos] + move_cost(next_x, next_y)
                        if next_pos not in g_costs or new_cost < g_costs[next_pos]:
                            g_costs[next_pos] = new_cost
                            priority = new_cost + heuristic(next_pos, goal)
                            heapq.heappush(open_list, (priority, next_pos, path + [direction]))

            return None

        running = True
        score = 0
        steps = 0
        treasures_collected = 0
        start_time = time.perf_counter()

        while running:
            if treasures_collected > 7:
                running = False
                break

            # Get next move from A*
            next_move = a_star_move(player_pos, treasures, walls, water)
            if not next_move:
                print("No valid move found!")
                running = False
                break

            direction = next_move
            score -= 1
            next_pos = player_pos

            if direction == (-1, 0):
                next_pos = (player_pos[0] - 1, player_pos[1])  # UP
            elif direction == (1, 0):
                next_pos = (player_pos[0] + 1, player_pos[1])  # DOWN
            elif direction == (0, -1):
                next_pos = (player_pos[0], player_pos[1] - 1)  # LEFT
            elif direction == (0, 1):
                next_pos = (player_pos[0], player_pos[1] + 1)  # RIGHT
            else:
                print("Invalid direction:", direction)
                running = False
                continue

            px, py = next_pos

            if (px, py) not in walls and 0 <= next_pos[0] < maze_size and 0 <= next_pos[1] < maze_size:
                player_pos = next_pos
            else:
                print("Invalid move!", next_pos)
                continue

            screen.fill(BLACK)
            for row in range(maze_size):
                for col in range(maze_size):
                    rect = pygame.Rect(col * block_size, row * block_size, block_size, block_size)
                    if (col, row) in walls:
                        pygame.draw.rect(screen, BLACK, rect)
                    elif (col, row) in water:
                        pygame.draw.rect(screen, BLUE, rect)
                    else:
                        pygame.draw.rect(screen, WHITE, rect)
                    if (col, row) == (px, py):
                        pygame.draw.rect(screen, RED, rect)
                    elif (col, row) in treasures:
                        pygame.draw.rect(screen, WHITE, rect)
                        screen.blit(treasure_image, (col * block_size, row * block_size))

            if (px, py) in treasures:
                treasures = tuple(t for t in treasures if t != (px, py))
                treasures_collected += 1
                print(f"Treasure found! {NUM_TREASURES - treasures_collected - 4} treasures left")

            if (px, py) in water:
                score -= 5
                print("In water! Paying a heavier price:", (px, py))

            pygame.display.flip()
            pygame.time.wait(100)  # Slow down the game a bit
            steps += 1

        end_time = time.perf_counter()
        total_time = end_time - start_time

        found_treasures = NUM_TREASURES - len(treasures) 
        print(f"Found {found_treasures} treasures")
        final_score = (found_treasures * 50) + score
        print(f"Final score: {final_score}")
        print(f"Total time taken: {total_time:.2f} seconds")
        print(f"Total steps: {steps}")
        pygame.quit()

        return found_treasures, final_score, total_time, steps

    def run_games(self, num_games):
        number = 1
        while number <= num_games:
            treasures, final_score, total_time, steps = self.game()
            total_time = f"{total_time:.2f}"
            self.astral[number] = [treasures, final_score, total_time, steps]
            number += 1

planner = Planner()
planner.run_games(3)
print(planner.astral)