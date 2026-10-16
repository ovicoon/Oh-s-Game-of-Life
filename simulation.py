from collections import deque
import json
from pathlib import Path
import random
import pygame

# =========================================================
# 설정 (Configuration)
# =========================================================

WIDTH, HEIGHT = 800, 600
GRID_SIZE = 15.0  # 기본 그리드 크기 (줌에 따라 변경됨)
COLS = 100
ROWS = 100
FPS = 30

# 색상 (Colors)
COLOR_BG = (20, 20, 20)
COLOR_BLOOD = (60, 25, 25)
COLOR_GRID = (40, 40, 40)
COLOR_CELL = (100, 100, 120)
COLOR_SPAWNER_GLUCOSE = (46, 204, 113)  # 포도당 생성기 (초록색)
COLOR_SPAWNER_SODIUM = (241, 196, 15)  # 소금 생성기 (노란색)
COLOR_DESPAWNER = (231, 76, 60)
COLOR_PUMP = (155, 89, 182)
COLOR_ACTIVE_PUMP = (52, 152, 219)
COLOR_SOLID_WALL = (70, 70, 80)

# 물질별 색상 구분 (Substance Colors)
COLOR_SODIUM = (241, 196, 15)  # 소금/나트륨 (노란색)
COLOR_GLUCOSE = (52, 152, 219)  # 포도당 (파란색)

DIRECTIONS_4 = [
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),
]

DIRECTION_MAP = {
    "left": (-1, 0),
    "right": (1, 0),
    "up": (0, -1),
    "down": (0, 1),
}

DEFAULT_ACTIVE_PUMP_DIRECTION = "right"
CELL_PASS_PROBABILITY = 0.2

# 생성기 확률 설정 (Spawner Probability Constants)
SODIUM_SPAWN_PROBABILITY = 0.1
GLUCOSE_SPAWN_PROBABILITY = 0.1


# =========================================================
# 클래스 (Classes)
# =========================================================


class Substance:
    def __init__(self, x, y, sub_type):
        self.x = x
        self.y = y
        self.sub_type = sub_type  # "sodium" 또는 "glucose"


class ActivePump:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction
        self.dx, self.dy = DIRECTION_MAP[direction]


# =========================================================
# 공통 함수 (Common Functions)
# =========================================================


def in_bounds(x, y):
    return 0 <= x < COLS and 0 <= y < ROWS


def load_map_from_json():
    path = Path(__file__).resolve().parent / "map.json"

    if not path.exists():
        print("map.json not found.")
        return None, []

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        grid = data.get("grid")

        if data.get("cols") != COLS or data.get("rows") != ROWS:
            print(f"Map size mismatch. Required: {COLS}x{ROWS}")
            return None, []

        if (
            not isinstance(grid, list)
            or len(grid) != COLS
            or not all(
                isinstance(column, list) and len(column) == ROWS for column in grid
            )
        ):
            print("Invalid grid data format in map.json.")
            return None, []

        for x in range(COLS):
            for y in range(ROWS):
                if (
                    not isinstance(grid[x][y], int)
                    or isinstance(grid[x][y], bool)
                    or grid[x][y] not in range(8)
                ):
                    print(f"Invalid tile value: ({x}, {y}) = {grid[x][y]}")
                    return None, []

        settings = data.get("active_pumps", [])
        if not isinstance(settings, list):
            print("active_pumps must be an array.")
            return None, []

        print(f"Map loaded successfully: {path.name} (Size: {COLS}x{ROWS})")
        return grid, settings

    except (OSError, json.JSONDecodeError) as exc:
        print(f"Failed to read map file: {exc}")
        return None, []

    except Exception as exc:
        print(f"Error loading map: {exc}")
        return None, []


def load_active_pumps(grid, settings):
    directions_by_position = {}

    for item in settings:
        try:
            x = item["x"]
            y = item["y"]
            direction = item["direction"]

            if (
                not isinstance(x, int)
                or isinstance(x, bool)
                or not isinstance(y, int)
                or isinstance(y, bool)
            ):
                continue
            if not in_bounds(x, y) or grid[x][y] != 6:  # 능동수송 펌프 ID (6)
                continue
            if not isinstance(direction, str):
                continue

            direction = direction.lower()
            if direction not in DIRECTION_MAP:
                continue

            directions_by_position[(x, y)] = direction
        except (KeyError, TypeError):
            pass

    active_pumps = []
    for x in range(COLS):
        for y in range(ROWS):
            if grid[x][y] != 6:
                continue
            direction = directions_by_position.get(
                (x, y), DEFAULT_ACTIVE_PUMP_DIRECTION
            )
            active_pumps.append(ActivePump(x, y, direction))

    pump_map = {(pump.x, pump.y): pump for pump in active_pumps}
    print(f"Loaded {len(active_pumps)} active pumps.")
    return active_pumps, pump_map


# =========================================================
# BFS 경로 계산 (Flow Field Calculation)
# =========================================================


def build_flow_field(grid, despawner_coords):
    flow_field = [[(0, 0) for _ in range(ROWS)] for _ in range(COLS)]
    distance_map = [[float("inf") for _ in range(ROWS)] for _ in range(COLS)]
    queue = deque()

    for x, y in despawner_coords:
        distance_map[x][y] = 0
        queue.append((x, y))

    while queue:
        cx, cy = queue.popleft()
        current_distance = distance_map[cx][cy]

        for dx, dy in DIRECTIONS_4:
            nx = cx + dx
            ny = cy + dy

            if not in_bounds(nx, ny):
                continue
            if grid[nx][ny] == 1 or grid[nx][ny] == 7:  # 세포막 또는 단단한 벽
                continue

            if distance_map[nx][ny] == float("inf"):
                distance_map[nx][ny] = current_distance + 1
                queue.append((nx, ny))

    for x in range(COLS):
        for y in range(ROWS):
            if grid[x][y] == 1 or grid[x][y] == 7:
                continue

            current_distance = distance_map[x][y]
            best_direction = (0, 0)
            min_distance = current_distance

            for dx, dy in DIRECTIONS_4:
                nx = x + dx
                ny = y + dy

                if not in_bounds(nx, ny):
                    continue

                if distance_map[nx][ny] < min_distance:
                    min_distance = distance_map[nx][ny]
                    best_direction = (dx, dy)

            flow_field[x][y] = best_direction

    return flow_field, distance_map


# =========================================================
# 렌더링 (Rendering)
# =========================================================


def draw_direction_triangle(screen, x, y, dx, dy, camera_x, camera_y, grid_size):
    cx = camera_x + x * grid_size + grid_size / 2
    cy = camera_y + y * grid_size + grid_size / 2

    scale = grid_size / 20.0
    tip = (cx + dx * 7 * scale, cy + dy * 7 * scale)
    px = -dy
    py = dx
    base_x = cx - dx * 4 * scale
    base_y = cy - dy * 4 * scale
    left = (base_x + px * 5 * scale, base_y + py * 5 * scale)
    right = (base_x - px * 5 * scale, base_y - py * 5 * scale)

    pygame.draw.polygon(screen, (40, 40, 40), [tip, left, right])


def draw_world(
    screen,
    grid,
    distance_map,
    active_pump_map,
    substances,
    show_sodium,
    camera_x,
    camera_y,
    grid_size,
):
    screen.fill(COLOR_BG)

    for x in range(COLS):
        for y in range(ROWS):
            rx = camera_x + x * grid_size
            ry = camera_y + y * grid_size

            if rx + grid_size < 0 or rx > WIDTH or ry + grid_size < 0 or ry > HEIGHT:
                continue

            rect = pygame.Rect(
                int(rx),
                int(ry),
                int(grid_size) + 1,
                int(grid_size) + 1,
            )
            cell_type = grid[x][y]

            if cell_type == 0 and distance_map[x][y] != float("inf"):
                pygame.draw.rect(screen, COLOR_BLOOD, rect)
            elif cell_type == 1:
                pygame.draw.rect(screen, COLOR_CELL, rect)
            elif cell_type == 2:
                pygame.draw.rect(screen, COLOR_SPAWNER_GLUCOSE, rect)
            elif cell_type == 3:
                pygame.draw.rect(screen, COLOR_SPAWNER_SODIUM, rect)
            elif cell_type == 4:
                pygame.draw.rect(screen, COLOR_DESPAWNER, rect)
            elif cell_type == 5:
                pygame.draw.rect(screen, COLOR_PUMP, rect)
            elif cell_type == 6:
                pygame.draw.rect(screen, COLOR_ACTIVE_PUMP, rect)
                pump = active_pump_map.get((x, y))
                if pump is not None:
                    draw_direction_triangle(
                        screen, x, y, pump.dx, pump.dy, camera_x, camera_y, grid_size
                    )
            elif cell_type == 7:
                pygame.draw.rect(screen, COLOR_SOLID_WALL, rect)
            else:
                pygame.draw.rect(screen, COLOR_GRID, rect, 1)

    for sub in substances:
        if sub.sub_type == "sodium" and not show_sodium:
            continue

        rx = camera_x + sub.x * grid_size
        ry = camera_y + sub.y * grid_size

        if rx + grid_size < 0 or rx > WIDTH or ry + grid_size < 0 or ry > HEIGHT:
            continue

        center = (
            int(rx + grid_size / 2),
            int(ry + grid_size / 2),
        )
        color = COLOR_SODIUM if sub.sub_type == "sodium" else COLOR_GLUCOSE
        radius = max(2, int(grid_size // 3))
        pygame.draw.circle(screen, color, center, radius)

    pygame.display.flip()


# =========================================================
# 이동 알고리즘 (Movement Algorithms)
# =========================================================


def can_normal_pass(grid, x, y):
    if not in_bounds(x, y):
        return False
    cell_type = grid[x][y]
    if cell_type == 7:  # 단단한 벽
        return False
    if cell_type == 1:  # 세포막
        return random.random() < CELL_PASS_PROBABILITY
    return True


def apply_active_pump_if_overlapping(
    sub,
    active_pump_map,
    substance_grid,
):
    pump = active_pump_map.get((sub.x, sub.y))
    if pump is None:
        return sub.x, sub.y, False

    nx = sub.x + pump.dx
    ny = sub.y + pump.dy

    if not in_bounds(nx, ny):
        return sub.x, sub.y, True

    if sub.sub_type == "sodium":
        for dx, dy in DIRECTIONS_4:
            check_x = sub.x + dx
            check_y = sub.y + dy
            if in_bounds(check_x, check_y):
                for other_sub in substance_grid[check_x][check_y]:
                    if other_sub.sub_type == "glucose":
                        other_sub.x = nx
                        other_sub.y = ny
                        break

    return nx, ny, True


def move_substance(
    sub,
    grid,
    flow_field,
    substance_grid,
    active_pump_map,
):
    x, y = sub.x, sub.y

    if grid[x][y] == 4:  # 출구(Despawner)
        return x, y, False

    nx, ny, used_pump = apply_active_pump_if_overlapping(
        sub,
        active_pump_map,
        substance_grid,
    )
    if used_pump:
        return nx, ny, True

    flow_dx, flow_dy = flow_field[x][y]

    neighbor_counts = {}
    total_neighbors = 0

    for dx, dy in DIRECTIONS_4:
        nx = x + dx
        ny = y + dy

        if in_bounds(nx, ny):
            count = sum(
                1 for other in substance_grid[nx][ny] if other.sub_type == sub.sub_type
            )
            neighbor_counts[(dx, dy)] = count
            total_neighbors += count
        else:
            neighbor_counts[(dx, dy)] = float("inf")

    valid_moves = []
    for dx, dy in DIRECTIONS_4:
        nx = x + dx
        ny = y + dy
        if in_bounds(nx, ny) and can_normal_pass(grid, nx, ny):
            valid_moves.append((dx, dy))

    used_active_pump = False

    if valid_moves:
        min_count = min(neighbor_counts[move] for move in valid_moves)
        least_crowded_moves = [
            move for move in valid_moves if neighbor_counts[move] == min_count
        ]

        if len(least_crowded_moves) == len(valid_moves) or total_neighbors == 0:
            if (flow_dx, flow_dy) in valid_moves:
                chosen_dx, chosen_dy = flow_dx, flow_dy
            else:
                chosen_dx, chosen_dy = random.choice(valid_moves)
        else:
            if (flow_dx, flow_dy) in least_crowded_moves:
                chosen_dx, chosen_dy = flow_dx, flow_dy
            else:
                chosen_dx, chosen_dy = random.choice(least_crowded_moves)

        nx = x + chosen_dx
        ny = y + chosen_dy

        adjacent_pump = active_pump_map.get((nx, ny))
        if (
            adjacent_pump is not None
            and adjacent_pump.dx == chosen_dx
            and adjacent_pump.dy == chosen_dy
        ):
            tx = nx + adjacent_pump.dx
            ty = ny + adjacent_pump.dy

            if in_bounds(tx, ty):
                if sub.sub_type == "sodium":
                    for dx, dy in DIRECTIONS_4:
                        check_x = nx + dx
                        check_y = ny + dy
                        if in_bounds(check_x, check_y):
                            for other_sub in substance_grid[check_x][check_y]:
                                if other_sub.sub_type == "glucose":
                                    other_sub.x = tx
                                    other_sub.y = ty
                                    break
                return tx, ty, True

        x, y = nx, ny
        sub.x, sub.y = x, y
        nx_p, ny_p, used_pump = apply_active_pump_if_overlapping(
            sub,
            active_pump_map,
            substance_grid,
        )
        if used_pump:
            return nx_p, ny_p, True

    if grid[x][y] == 4:
        return x, y, False

    dx, dy = random.choice(DIRECTIONS_4)
    bx = x + dx
    by = y + dy

    if can_normal_pass(grid, bx, by):
        x, y = bx, by
        sub.x, sub.y = x, y
        nx_p, ny_p, used_pump = apply_active_pump_if_overlapping(
            sub,
            active_pump_map,
            substance_grid,
        )
        if used_pump:
            return nx_p, ny_p, True

    return x, y, used_active_pump


# =========================================================
# 메인 시뮬레이션 (Main Simulation Loop)
# =========================================================


def run_simulation():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Oh's Game Of Life")
    clock = pygame.time.Clock()

    grid, active_pump_settings = load_map_from_json()

    if grid is None:
        print("Starting with an empty map.")
        grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]
        active_pump_settings = []

    glucose_spawner_coords = []
    sodium_spawner_coords = []
    despawner_coords = []

    for x in range(COLS):
        for y in range(ROWS):
            cell_type = grid[x][y]
            if cell_type == 2:
                glucose_spawner_coords.append((x, y))
            elif cell_type == 3:
                sodium_spawner_coords.append((x, y))
            elif cell_type == 4:
                despawner_coords.append((x, y))

    if not glucose_spawner_coords and not sodium_spawner_coords:
        glucose_spawner_coords.append((0, ROWS // 2))

    if not despawner_coords:
        despawner_coords.append((COLS - 1, ROWS // 2))

    active_pumps, active_pump_map = load_active_pumps(
        grid,
        active_pump_settings,
    )
    flow_field, distance_map = build_flow_field(
        grid,
        despawner_coords,
    )

    substances = []
    running = True
    show_sodium = True

    grid_size = 15.0
    camera_x = 0.0
    camera_y = 0.0
    panning = False
    pan_start_pos = (0, 0)

    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_h:
                    show_sodium = not show_sodium
                    print(f"Sodium Visible: {show_sodium}")

            elif event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                old_grid_size = grid_size
                if event.y > 0:
                    grid_size = min(60.0, grid_size + 2.0)
                elif event.y < 0:
                    grid_size = max(5.0, grid_size - 2.0)

                world_x = (mx - camera_x) / old_grid_size
                world_y = (my - camera_y) / old_grid_size
                camera_x = mx - world_x * grid_size
                camera_y = my - world_y * grid_size

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2:
                    panning = True
                    pan_start_pos = event.pos

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    panning = False

            elif event.type == pygame.MOUSEMOTION:
                if panning:
                    mx, my = event.pos
                    dx = mx - pan_start_pos[0]
                    dy = my - pan_start_pos[1]
                    camera_x += dx
                    camera_y += dy
                    pan_start_pos = (mx, my)

        # 포도당 스폰 확률 적용
        for sx, sy in glucose_spawner_coords:
            if random.random() < GLUCOSE_SPAWN_PROBABILITY:
                substances.append(Substance(sx, sy, "glucose"))

        # 소금 스폰 확률 적용
        for sx, sy in sodium_spawner_coords:
            if random.random() < SODIUM_SPAWN_PROBABILITY:
                substances.append(Substance(sx, sy, "sodium"))

        substance_grid = [[[] for _ in range(ROWS)] for _ in range(COLS)]
        for sub in substances:
            substance_grid[sub.x][sub.y].append(sub)

        future_positions = []
        for sub in substances:
            if grid[sub.x][sub.y] == 4:
                continue
            nx, ny, _ = move_substance(
                sub,
                grid,
                flow_field,
                substance_grid,
                active_pump_map,
            )
            future_positions.append((sub, nx, ny))

        new_substances = []
        for sub, nx, ny in future_positions:
            if not in_bounds(nx, ny):
                continue
            if grid[nx][ny] == 4:
                continue
            sub.x = nx
            sub.y = ny
            new_substances.append(sub)

        substances = new_substances

        draw_world(
            screen,
            grid,
            distance_map,
            active_pump_map,
            substances,
            show_sodium,
            camera_x,
            camera_y,
            grid_size,
        )

    pygame.quit()


if __name__ == "__main__":
    run_simulation()
