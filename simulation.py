from collections import deque
import json
from pathlib import Path
import random
import pygame

# --- 설정 ---
WIDTH, HEIGHT = 800, 600
GRID_SIZE = 20  # 각 그리드 칸의 픽셀 크기
COLS = WIDTH // GRID_SIZE
ROWS = HEIGHT // GRID_SIZE
FPS = 30

# 색상 정의 (RGB)
COLOR_BG = (20, 20, 20)  # 혈관 바깥 조직 배경
COLOR_BLOOD = (60, 25, 25)  # 혈액이 흐르는 내부 공간 (어두운 붉은빛)
COLOR_GRID = (40, 40, 40)
COLOR_CELL = (100, 100, 120)  # 세포 (벽)
COLOR_SPAWNER = (46, 204, 113)  # 스포너 (입구)
COLOR_DESPAWNER = (231, 76, 60)  # 디스파워너 (출구)
COLOR_SUBSTANCE = (52, 152, 219)  # 수용성 물질

DIRECTIONS_8 = [
    (-1, -1),
    (0, -1),
    (1, -1),
    (-1, 0),
    (0, 0),
    (1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
]
DIRECTIONS_4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]


class Substance:

    def __init__(self, x, y):
        self.x = x
        self.y = y


def load_map_from_json():
    """같은 폴더의 map.json 파일을 불러옵니다."""
    path = Path(__file__).resolve().parent / "map.json"
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("grid")
        except Exception as e:
            print(f"맵 로드 중 오류 발생: {e}")
    return None


def run_simulation():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Glomerulus and Capillary Simulation (Loaded Map)")
    clock = pygame.time.Clock()

    # 1. 맵 파일 불러오기 시도
    grid = load_map_from_json()

    # 만약 map.json이 없다면 기본 빈 맵 생성
    if grid is None:
        print("map.json을 찾을 수 없어 빈 맵으로 시작합니다.")
        grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]

    # 2. 불러온 맵에서 스포너(2)와 디스파워너(3) 위치 동적 탐색
    spawner_pos = None
    despawner_coords = []

    for x in range(COLS):
        for y in range(ROWS):
            if grid[x][y] == 2:
                spawner_pos = (x, y)
            elif grid[x][y] == 3:
                despawner_coords.append((x, y))

    # 스포너가 정의되지 않은 경우 기본 위치 지정
    if not spawner_pos:
        spawner_pos = (0, ROWS // 2)

    # --- BFS를 이용한 자동 유선(Flow Field) 계산 ---
    flow_field = [[(0, 0) for _ in range(ROWS)] for _ in range(COLS)]
    distance_map = [[float("inf") for _ in range(ROWS)] for _ in range(COLS)]
    queue = deque()

    for dx, dy in despawner_coords:
        distance_map[dx][dy] = 0
        queue.append((dx, dy))

    while queue:
        cx, cy = queue.popleft()
        current_dist = distance_map[cx][cy]
        for dx, dy in DIRECTIONS_4:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS:
                if grid[nx][ny] != 1 and distance_map[nx][ny] == float("inf"):
                    distance_map[nx][ny] = current_dist + 1
                    queue.append((nx, ny))

    for x in range(COLS):
        for y in range(ROWS):
            if grid[x][y] == 1:
                continue
            best_dx, best_dy = 0, 0
            min_dist = distance_map[x][y]
            for dx, dy in DIRECTIONS_4:
                nx, ny = x + dx, y + dy
                if 0 <= nx < COLS and 0 <= ny < ROWS:
                    if distance_map[nx][ny] < min_dist:
                        min_dist = distance_map[nx][ny]
                        best_dx, best_dy = dx, dy
            flow_field[x][y] = (best_dx, best_dy)

    substances = []
    running = True
    frame_count = 0

    while running:
        clock.tick(FPS)
        frame_count += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 스포너가 존재할 때만 물질 생성
        if spawner_pos and frame_count % 8 == 0:
            substances.append(Substance(spawner_pos[0], spawner_pos[1]))

        # --- 1단계: 현재 프레임의 물질 위치 맵 구성 ---
        substance_grid = [[[] for _ in range(ROWS)] for _ in range(COLS)]
        for sub in substances:
            substance_grid[sub.x][sub.y].append(sub)

        # --- 2단계: 모든 물질의 미래 이동 위치 계산 ---
        future_positions = []
        cell_pass_probability = 0.2

        for sub in substances:
            if grid[sub.x][sub.y] == 3:
                continue
            current_x, current_y = sub.x, sub.y

            fx_dir, fy_dir = flow_field[current_x][current_y]
            neighbor_counts = {}
            total_neighbors = 0

            for bdx, bdy in DIRECTIONS_8:
                nx, ny = current_x + bdx, current_y + bdy
                if 0 <= nx < COLS and 0 <= ny < ROWS:
                    count = len(substance_grid[nx][ny])
                    if (nx, ny) == (current_x, current_y):
                        count = max(0, count - 1)
                    neighbor_counts[(bdx, bdy)] = count
                    total_neighbors += count
                else:
                    neighbor_counts[(bdx, bdy)] = float("inf")

            valid_moves = []
            for bdx, bdy in DIRECTIONS_8:
                nx, ny = current_x + bdx, current_y + bdy
                if 0 <= nx < COLS and 0 <= ny < ROWS:
                    target_type = grid[nx][ny]
                    can_pass = True
                    if target_type == 1:
                        if random.random() >= cell_pass_probability:
                            can_pass = False
                    if can_pass:
                        valid_moves.append((bdx, bdy))

            if valid_moves:
                min_count = float("inf")
                for bdx, bdy in valid_moves:
                    cnt = neighbor_counts[(bdx, bdy)]
                    if cnt < min_count:
                        min_count = cnt
                least_crowded_moves = [
                    m for m in valid_moves if neighbor_counts[m] == min_count
                ]
                if len(least_crowded_moves) == len(valid_moves) or total_neighbors == 0:
                    if (fx_dir, fy_dir) in valid_moves:
                        chosen_dx, chosen_dy = fx_dir, fy_dir
                    else:
                        chosen_dx, chosen_dy = random.choice(valid_moves)
                else:
                    if (fx_dir, fy_dir) in least_crowded_moves:
                        chosen_dx, chosen_dy = fx_dir, fy_dir
                    else:
                        chosen_dx, chosen_dy = random.choice(least_crowded_moves)
                current_x += chosen_dx
                current_y += chosen_dy

            if grid[current_x][current_y] == 3:
                future_positions.append((sub, current_x, current_y))
                continue

            # --- 브라운 운동 추가 적용 ---
            bdx, bdy = random.choice(DIRECTIONS_8)
            bx, by = current_x + bdx, current_y + bdy
            if 0 <= bx < COLS and 0 <= by < ROWS:
                target_cell_type = grid[bx][by]
                can_brown_pass = True
                if target_cell_type == 1:
                    if random.random() >= cell_pass_probability:
                        can_brown_pass = False
                if can_brown_pass:
                    current_x, current_y = bx, by
            future_positions.append((sub, current_x, current_y))

        # --- 3단계: 일괄 업데이트 ---
        new_substances = []
        for sub, nx, ny in future_positions:
            if 0 <= nx < COLS and 0 <= ny < ROWS and grid[nx][ny] == 3:
                continue
            sub.x = nx
            sub.y = ny
            new_substances.append(sub)
        substances = new_substances

        # --- 화면 렌더링 ---
        screen.fill(COLOR_BG)
        for x in range(COLS):
            for y in range(ROWS):
                rect = pygame.Rect(
                    x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE - 1, GRID_SIZE - 1
                )
                cell_type = grid[x][y]
                if distance_map[x][y] != float("inf") and cell_type == 0:
                    pygame.draw.rect(screen, COLOR_BLOOD, rect)
                elif cell_type == 1:
                    pygame.draw.rect(screen, COLOR_CELL, rect)
                elif cell_type == 2:
                    pygame.draw.rect(screen, COLOR_SPAWNER, rect)
                elif cell_type == 3:
                    pygame.draw.rect(screen, COLOR_DESPAWNER, rect)
                else:
                    pygame.draw.rect(screen, COLOR_GRID, rect, 1)

        for sub in substances:
            center = (
                sub.x * GRID_SIZE + GRID_SIZE // 2,
                sub.y * GRID_SIZE + GRID_SIZE // 2,
            )
            pygame.draw.circle(screen, COLOR_SUBSTANCE, center, GRID_SIZE // 3)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run_simulation()
