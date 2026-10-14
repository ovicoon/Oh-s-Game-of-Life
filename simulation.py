from collections import deque
import json
from pathlib import Path
import random
import pygame

# =========================================================
# 설정
# =========================================================

WIDTH, HEIGHT = 800, 600
GRID_SIZE = 20
COLS = WIDTH // GRID_SIZE
ROWS = HEIGHT // GRID_SIZE
FPS = 30

# 색상
COLOR_BG = (20, 20, 20)
COLOR_BLOOD = (60, 25, 25)
COLOR_GRID = (40, 40, 40)
COLOR_CELL = (100, 100, 120)
COLOR_SPAWNER = (46, 204, 113)
COLOR_DESPAWNER = (231, 76, 60)
COLOR_PUMP = (155, 89, 182)
COLOR_ACTIVE_PUMP = (241, 196, 15)
COLOR_SOLID_WALL = (70, 70, 80)  # 완전한 벽 색상 (진한 회색)

# 물질별 색상 구분
COLOR_SODIUM = (241, 196, 15)  # 나트륨 (노란색)
COLOR_GLUCOSE = (52, 152, 219)  # 포도당 (파란색)

DIRECTIONS_4 = [
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),
]

# JSON 방향 문자열 -> 좌표 변화량
DIRECTION_MAP = {
    "left": (-1, 0),
    "right": (1, 0),
    "up": (0, -1),
    "down": (0, 1),
}

DIRECTION_LABELS = {
    "left": "왼쪽",
    "right": "오른쪽",
    "up": "위쪽",
    "down": "아래쪽",
}

# 방향 정보가 없는 능동수송 펌프의 기본 방향
DEFAULT_ACTIVE_PUMP_DIRECTION = "right"

# 벽을 통과할 확률 (타일 1: 세포막)
CELL_PASS_PROBABILITY = 0.2

# 생성 주기
SPAWN_INTERVAL = 8

SPAWN_PER_INTERVAL = (1, 30)  # (포도당, 나트륨) 비율


# =========================================================
# 클래스
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
# 공통 함수
# =========================================================


def in_bounds(x, y):
    return 0 <= x < COLS and 0 <= y < ROWS


def load_map_from_json():
    path = Path(__file__).resolve().parent / "map.json"

    if not path.exists():
        print("map.json이 없습니다.")
        return None, []

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        grid = data.get("grid")

        if data.get("cols") != COLS or data.get("rows") != ROWS:
            print(f"맵 크기가 일치하지 않습니다. 필요한 크기: {COLS}x{ROWS}")
            return None, []

        if (
            not isinstance(grid, list)
            or len(grid) != COLS
            or not all(
                isinstance(column, list) and len(column) == ROWS for column in grid
            )
        ):
            print("map.json의 grid 데이터 형식이 잘못되었습니다.")
            return None, []

        # 타일 값 검증 (0 ~ 6 허용)
        for x in range(COLS):
            for y in range(ROWS):
                if (
                    not isinstance(grid[x][y], int)
                    or isinstance(grid[x][y], bool)
                    or grid[x][y] not in range(7)
                ):
                    print(f"잘못된 타일 값: ({x}, {y}) = {grid[x][y]}")
                    return None, []

        settings = data.get("active_pumps", [])

        if not isinstance(settings, list):
            print("active_pumps는 배열이어야 합니다.")
            return None, []

        print(f"맵 로드 완료: {path.name}")
        return grid, settings

    except (OSError, json.JSONDecodeError) as exc:
        print(f"맵 파일 읽기 실패: {exc}")
        return None, []

    except Exception as exc:
        print(f"맵 로드 중 오류 발생: {exc}")
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

            if not in_bounds(x, y):
                continue

            if grid[x][y] != 5:
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
            if grid[x][y] != 5:
                continue

            direction = directions_by_position.get(
                (x, y),
                DEFAULT_ACTIVE_PUMP_DIRECTION,
            )
            active_pumps.append(ActivePump(x, y, direction))

    pump_map = {(pump.x, pump.y): pump for pump in active_pumps}
    print(f"능동수송 펌프 {len(active_pumps)}개 로드 완료")
    return active_pumps, pump_map


# =========================================================
# BFS 유선 계산
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

            # 타일 1(세포벽)과 타일 6(완전한 벽)은 BFS 길찾기에서 통과 불가
            if grid[nx][ny] == 1 or grid[nx][ny] == 6:
                continue

            if distance_map[nx][ny] == float("inf"):
                distance_map[nx][ny] = current_distance + 1
                queue.append((nx, ny))

    for x in range(COLS):
        for y in range(ROWS):
            if grid[x][y] == 1 or grid[x][y] == 6:
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
# 렌더링
# =========================================================


def draw_direction_triangle(screen, x, y, dx, dy):
    cx = x * GRID_SIZE + GRID_SIZE // 2
    cy = y * GRID_SIZE + GRID_SIZE // 2
    tip = (cx + dx * 7, cy + dy * 7)
    px = -dy
    py = dx
    base_x = cx - dx * 4
    base_y = cy - dy * 4
    left = (base_x + px * 5, base_y + py * 5)
    right = (base_x - px * 5, base_y - py * 5)

    pygame.draw.polygon(screen, (40, 40, 40), [tip, left, right])


def draw_world(
    screen,
    grid,
    distance_map,
    active_pump_map,
    substances,
    show_sodium=True,
):
    screen.fill(COLOR_BG)

    for x in range(COLS):
        for y in range(ROWS):
            rect = pygame.Rect(
                x * GRID_SIZE,
                y * GRID_SIZE,
                GRID_SIZE - 1,
                GRID_SIZE - 1,
            )
            cell_type = grid[x][y]

            if cell_type == 0 and distance_map[x][y] != float("inf"):
                pygame.draw.rect(screen, COLOR_BLOOD, rect)
            elif cell_type == 1:
                pygame.draw.rect(screen, COLOR_CELL, rect)
            elif cell_type == 2:
                pygame.draw.rect(screen, COLOR_SPAWNER, rect)
            elif cell_type == 3:
                pygame.draw.rect(screen, COLOR_DESPAWNER, rect)
            elif cell_type == 4:
                pygame.draw.rect(screen, COLOR_PUMP, rect)
            elif cell_type == 5:
                pygame.draw.rect(screen, COLOR_ACTIVE_PUMP, rect)
                pump = active_pump_map.get((x, y))
                if pump is not None:
                    draw_direction_triangle(screen, x, y, pump.dx, pump.dy)
            elif cell_type == 6:
                pygame.draw.rect(screen, COLOR_SOLID_WALL, rect)
            else:
                pygame.draw.rect(screen, COLOR_GRID, rect, 1)

    for sub in substances:
        # 나트륨 숨기기 옵션 적용
        if sub.sub_type == "sodium" and not show_sodium:
            continue

        center = (
            sub.x * GRID_SIZE + GRID_SIZE // 2,
            sub.y * GRID_SIZE + GRID_SIZE // 2,
        )
        color = COLOR_SODIUM if sub.sub_type == "sodium" else COLOR_GLUCOSE
        pygame.draw.circle(screen, color, center, GRID_SIZE // 3)

    pygame.display.flip()


# =========================================================
# 이동 알고리즘
# =========================================================


def can_normal_pass(grid, x, y):
    if not in_bounds(x, y):
        return False

    cell_type = grid[x][y]
    if cell_type == 6:
        return False  # 타일 6(완전한 벽): 절대 통과 불가
    if cell_type == 1:
        return random.random() < CELL_PASS_PROBABILITY  # 타일 1(세포막): 20% 확률 통과

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

    if grid[x][y] == 3:
        return x, y, False

    nx, ny, used_pump = apply_active_pump_if_overlapping(
        sub,
        active_pump_map,
        substance_grid,
    )
    if used_pump:
        return nx, ny, True

    flow_dx, flow_dy = flow_field[x][y]

    # 주변 밀집도 계산 (같은 물질끼리만 카운트)
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

    if grid[x][y] == 3:
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
# 메인 시뮬레이션
# =========================================================


def run_simulation():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("SGLT Simulation (H: 나트륨 토글)")
    clock = pygame.time.Clock()

    grid, active_pump_settings = load_map_from_json()

    if grid is None:
        print("빈 맵으로 시작합니다.")
        grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]
        active_pump_settings = []

    spawner_coords = []
    despawner_coords = []
    pump_coords = []

    for x in range(COLS):
        for y in range(ROWS):
            cell_type = grid[x][y]
            if cell_type == 2:
                spawner_coords.append((x, y))
            elif cell_type == 3:
                despawner_coords.append((x, y))
            elif cell_type == 4:
                pump_coords.append((x, y))

    if not spawner_coords:
        spawner_coords.append((0, ROWS // 2))

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
    frame_count = 0
    running = True
    show_sodium = True  # 나트륨 표시 기본값

    while running:
        clock.tick(FPS)
        frame_count += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # H 키를 누르면 나트륨 표시 여부 토글
                if event.key == pygame.K_h:
                    show_sodium = not show_sodium
                    print(f"나트륨 표시: {show_sodium}")

        if frame_count % SPAWN_INTERVAL == 0:
            for sx, sy in spawner_coords:
                for _ in range(SPAWN_PER_INTERVAL[0]):
                    substances.append(Substance(sx, sy, "glucose"))
                for _ in range(SPAWN_PER_INTERVAL[1]):
                    substances.append(Substance(sx, sy, "sodium"))

        substance_grid = [[[] for _ in range(ROWS)] for _ in range(COLS)]
        for sub in substances:
            substance_grid[sub.x][sub.y].append(sub)

        future_positions = []
        for sub in substances:
            if grid[sub.x][sub.y] == 3:
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
            if grid[nx][ny] == 3:
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
        )

    pygame.quit()


if __name__ == "__main__":
    run_simulation()
