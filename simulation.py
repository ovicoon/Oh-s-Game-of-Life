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

# 벽을 통과할 확률
CELL_PASS_PROBABILITY = 0.2

# 생성 주기
SPAWN_INTERVAL = 8

SODIUM_TO_GLUCOSE_RATIO = 30  # 포도당 1개당 나트륨 생성 비율


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
    """
    맵 에디터에서 저장한 map.json을 읽는다.

    반환:
        grid: grid[x][y] 형태의 맵
        active_pump_settings: 능동수송 펌프 설정 목록
    """

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

        # 타일 값 검증
        for x in range(COLS):
            for y in range(ROWS):
                if (
                    not isinstance(grid[x][y], int)
                    or isinstance(grid[x][y], bool)
                    or grid[x][y] not in range(6)
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
    """
    JSON 설정을 검증하고 능동수송 펌프를 생성한다.

    JSON에 방향이 없는 펌프는 오른쪽을 기본 방향으로 사용한다.
    """

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
                print(f"펌프 좌표가 정수가 아닙니다: {item}")
                continue

            if not in_bounds(x, y):
                print(f"펌프 좌표가 범위를 벗어났습니다: {item}")
                continue

            if grid[x][y] != 5:
                print(f"({x}, {y}) 위치는 능동수송 펌프(5)가 아닙니다.")
                continue

            if not isinstance(direction, str):
                print(f"펌프 방향이 문자열이 아닙니다: {item}")
                continue

            direction = direction.lower()

            if direction not in DIRECTION_MAP:
                print(f"잘못된 펌프 방향: {item}")
                continue

            directions_by_position[(x, y)] = direction

        except (KeyError, TypeError):
            print(f"잘못된 펌프 설정: {item}")

    active_pumps = []

    for x in range(COLS):
        for y in range(ROWS):
            if grid[x][y] != 5:
                continue

            direction = directions_by_position.get(
                (x, y),
                DEFAULT_ACTIVE_PUMP_DIRECTION,
            )

            if (x, y) not in directions_by_position:
                print(
                    f"펌프 ({x}, {y})의 방향 정보가 없어 "
                    f"{DIRECTION_LABELS[direction]}을 기본 방향으로 사용합니다."
                )

            active_pumps.append(ActivePump(x, y, direction))

    pump_map = {(pump.x, pump.y): pump for pump in active_pumps}

    print(f"능동수송 펌프 {len(active_pumps)}개 로드 완료")

    return active_pumps, pump_map


# =========================================================
# BFS 유선 계산
# =========================================================


def build_flow_field(grid, despawner_coords):
    """
    출구에서 역방향 BFS를 수행해 각 칸의 출구 방향을 계산한다.
    벽(1)은 BFS 경로에서 통과할 수 없다.
    """

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

            if grid[nx][ny] == 1:
                continue

            if distance_map[nx][ny] == float("inf"):
                distance_map[nx][ny] = current_distance + 1
                queue.append((nx, ny))

    for x in range(COLS):
        for y in range(ROWS):
            if grid[x][y] == 1:
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
    """능동수송 펌프 안에 방향 삼각형을 그린다."""

    cx = x * GRID_SIZE + GRID_SIZE // 2
    cy = y * GRID_SIZE + GRID_SIZE // 2

    tip = (
        cx + dx * 7,
        cy + dy * 7,
    )

    px = -dy
    py = dx

    base_x = cx - dx * 4
    base_y = cy - dy * 4

    left = (
        base_x + px * 5,
        base_y + py * 5,
    )

    right = (
        base_x - px * 5,
        base_y - py * 5,
    )

    pygame.draw.polygon(
        screen,
        (40, 40, 40),
        [tip, left, right],
    )


def draw_world(
    screen,
    grid,
    distance_map,
    active_pump_map,
    substances,
):
    screen.fill(COLOR_BG)

    # 맵 그리기
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
                pygame.draw.rect(
                    screen,
                    COLOR_BLOOD,
                    rect,
                )

            elif cell_type == 1:
                pygame.draw.rect(
                    screen,
                    COLOR_CELL,
                    rect,
                )

            elif cell_type == 2:
                pygame.draw.rect(
                    screen,
                    COLOR_SPAWNER,
                    rect,
                )

            elif cell_type == 3:
                pygame.draw.rect(
                    screen,
                    COLOR_DESPAWNER,
                    rect,
                )

            elif cell_type == 4:
                pygame.draw.rect(
                    screen,
                    COLOR_PUMP,
                    rect,
                )

            elif cell_type == 5:
                pygame.draw.rect(
                    screen,
                    COLOR_ACTIVE_PUMP,
                    rect,
                )

                pump = active_pump_map.get((x, y))

                if pump is not None:
                    draw_direction_triangle(
                        screen,
                        x,
                        y,
                        pump.dx,
                        pump.dy,
                    )

            else:
                pygame.draw.rect(
                    screen,
                    COLOR_GRID,
                    rect,
                    1,
                )

    # 물질을 마지막에 그려 구조물과 겹쳐도 표시되도록 한다.
    for sub in substances:
        center = (
            sub.x * GRID_SIZE + GRID_SIZE // 2,
            sub.y * GRID_SIZE + GRID_SIZE // 2,
        )

        color = COLOR_SODIUM if sub.sub_type == "sodium" else COLOR_GLUCOSE

        pygame.draw.circle(
            screen,
            color,
            center,
            GRID_SIZE // 3,
        )

    pygame.display.flip()


# =========================================================
# 이동 알고리즘
# =========================================================


def can_normal_pass(grid, x, y):
    """
    일반 이동과 브라운 운동에 사용하는 통과 검사.
    벽은 20% 확률로 통과한다.
    """

    if not in_bounds(x, y):
        return False

    if grid[x][y] == 1:
        return random.random() < CELL_PASS_PROBABILITY

    return True


def apply_active_pump_if_overlapping(
    sub,
    active_pump_map,
    substance_grid,
):
    """
    현재 위치에 능동수송 펌프가 있으면 펌프 방향으로 한 칸 이동한다.
    만약 이 물질이 나트륨(sodium)이고 펌프가 작동한다면, 사방을 확인해
    포도당(glucose)을 찾아 함께 순간이동시킨다.
    """

    pump = active_pump_map.get((sub.x, sub.y))

    if pump is None:
        return sub.x, sub.y, False

    nx = sub.x + pump.dx
    ny = sub.y + pump.dy

    if not in_bounds(nx, ny):
        return sub.x, sub.y, True

    # SGLT 공동 수송 로직: 나트륨인 경우 주변 포도당과 함께 이동
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
    """
    물질 하나의 다음 위치를 계산한다.

    반환:
        (x, y, used_active_pump)
    """

    x, y = sub.x, sub.y

    # 출구에 있는 물질은 이동시키지 않는다.
    if grid[x][y] == 3:
        return x, y, False

    # -----------------------------------------------------
    # 1. 물질이 펌프 칸과 겹쳐 있는 경우
    # -----------------------------------------------------

    nx, ny, used_pump = apply_active_pump_if_overlapping(
        sub,
        active_pump_map,
        substance_grid,
    )

    if used_pump:
        return nx, ny, True

    # -----------------------------------------------------
    # 2. 현재 위치의 주변 밀집도 계산
    # -----------------------------------------------------

    flow_dx, flow_dy = flow_field[x][y]

    neighbor_counts = {}
    total_neighbors = 0

    for dx, dy in DIRECTIONS_4:
        nx = x + dx
        ny = y + dy

        if in_bounds(nx, ny):
            count = len(substance_grid[nx][ny])

            if (nx, ny) == (x, y):
                count = max(0, count - 1)

            neighbor_counts[(dx, dy)] = count
            total_neighbors += count

        else:
            neighbor_counts[(dx, dy)] = float("inf")

    # -----------------------------------------------------
    # 3. 일반 이동 후보
    # -----------------------------------------------------

    valid_moves = []

    for dx, dy in DIRECTIONS_4:
        nx = x + dx
        ny = y + dy

        if not in_bounds(nx, ny):
            continue

        if can_normal_pass(grid, nx, ny):
            valid_moves.append((dx, dy))

    # -----------------------------------------------------
    # 4. 밀집도 회피 및 BFS 방향 선택
    # -----------------------------------------------------

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

        # 일반 이동의 바로 앞 칸
        nx = x + chosen_dx
        ny = y + chosen_dy

        # -------------------------------------------------
        # 5. 펌프를 뛰어넘는 순간이동
        # -------------------------------------------------

        adjacent_pump = active_pump_map.get((nx, ny))

        if (
            adjacent_pump is not None
            and adjacent_pump.dx == chosen_dx
            and adjacent_pump.dy == chosen_dy
        ):
            tx = nx + adjacent_pump.dx
            ty = ny + adjacent_pump.dy

            if in_bounds(tx, ty):
                # SGLT 공동 수송 로직 (점프 순간)
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

        # 순간이동이 발생하지 않았다면 일반 이동
        x, y = nx, ny

        # 일반 이동으로 펌프 칸에 도착했다면 펌프가 작동한다.
        sub.x, sub.y = x, y
        nx_p, ny_p, used_pump = apply_active_pump_if_overlapping(
            sub,
            active_pump_map,
            substance_grid,
        )

        if used_pump:
            return nx_p, ny_p, True

    # -----------------------------------------------------
    # 6. 출구 확인
    # -----------------------------------------------------

    if grid[x][y] == 3:
        return x, y, False

    # -----------------------------------------------------
    # 7. 브라운 운동
    # -----------------------------------------------------

    dx, dy = random.choice(DIRECTIONS_4)

    bx = x + dx
    by = y + dy

    if can_normal_pass(grid, bx, by):
        x, y = bx, by

        # 브라운 운동으로 펌프 칸에 들어온 경우도 작동
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

    pygame.display.set_caption("Substance Simulation - SGLT Cotransport")

    clock = pygame.time.Clock()

    grid, active_pump_settings = load_map_from_json()

    if grid is None:
        print("빈 맵으로 시작합니다.")

        grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]

        active_pump_settings = []

    # 구조물 위치 탐색
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

    # 기본 생성기와 출구
    if not spawner_coords:
        spawner_coords.append((0, ROWS // 2))

    if not despawner_coords:
        despawner_coords.append((COLS - 1, ROWS // 2))

    # 능동수송 펌프 및 방향 로드
    active_pumps, active_pump_map = load_active_pumps(
        grid,
        active_pump_settings,
    )

    # BFS 경로 계산
    flow_field, distance_map = build_flow_field(
        grid,
        despawner_coords,
    )

    substances = []
    frame_count = 0
    running = True

    while running:
        clock.tick(FPS)
        frame_count += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # ---------------------------------------------
        # 물질 생성 (나트륨과 포도당 모두 스폰)
        # ---------------------------------------------

        if frame_count % SPAWN_INTERVAL == 0:
            for sx, sy in spawner_coords:
                substances.append(Substance(sx, sy, "glucose"))
                for _ in range(SODIUM_TO_GLUCOSE_RATIO):
                    substances.append(Substance(sx, sy, "sodium"))

        # ---------------------------------------------
        # 현재 물질 위치 맵 생성
        # ---------------------------------------------

        substance_grid = [[[] for _ in range(ROWS)] for _ in range(COLS)]

        for sub in substances:
            substance_grid[sub.x][sub.y].append(sub)

        # ---------------------------------------------
        # 모든 물질의 다음 위치 계산
        # ---------------------------------------------

        future_positions = []

        for sub in substances:
            if grid[sub.x][sub.y] == 3:
                continue

            nx, ny, used_pump = move_substance(
                sub,
                grid,
                flow_field,
                substance_grid,
                active_pump_map,
            )

            future_positions.append((sub, nx, ny))

        # ---------------------------------------------
        # 이동 결과 일괄 적용
        # ---------------------------------------------

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

        # ---------------------------------------------
        # 렌더링
        # ---------------------------------------------

        draw_world(
            screen,
            grid,
            distance_map,
            active_pump_map,
            substances,
        )

    pygame.quit()


if __name__ == "__main__":
    run_simulation()
