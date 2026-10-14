from collections import deque

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

COLOR_DESPAWNER = (231, 76, 60)  # 디스파워너 (출구 다중 차단)

COLOR_SUBSTANCE = (52, 152, 219)  # 수용성 물질

# 8방향 이동을 위한 오프셋 목록 (자기 자신 포함 9칸 탐색용)

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


def run_simulation():

    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))

    pygame.display.set_caption("Glomerulus and Capillary Simulation")

    clock = pygame.time.Clock()

    # 그리드 초기화 (0: 빈 공간, 1: 세포막, 2: 스포너, 3: 디스파워너)

    grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]

    # --- 구조물 배치 설정 ---
    # 혈관 입구를 화면 맨 왼쪽에 두어 사용 가능한 가로 공간을 늘린다.
    start_x, end_x = 0, COLS - 1
    channel_top, channel_bottom = 8, 16

    # 일반 모세혈관의 내강은 2칸 높이(y=11, 12)이며,
    # 위/아래 벽은 여러 칸 두께로 유지한다.
    vessel_top_y, vessel_bottom_y = 11, 12
    thin_start_x, thin_end_x = 16, 26  # 토리 역할을 하는 직선·1칸 내강 구간
    glomerulus_y = 12
    lower_wall_y = glomerulus_y + 1

    for x in range(start_x, end_x):
        # 우선 혈관 구조물 구역을 벽으로 채운다.
        for y in range(channel_top, channel_bottom + 1):
            grid[x][y] = 1

        # 일반 모세혈관: 2칸 높이의 내강.
        if not (thin_start_x <= x < thin_end_x):
            grid[x][vessel_top_y] = 0
            grid[x][vessel_bottom_y] = 0
        else:
            # 토리 구간: 직선이며 내강은 1칸 높이.
            # 아래쪽 벽은 y=13 한 칸만 남겨 물질 이동을 관찰할 수 있게 한다.
            grid[x][glomerulus_y] = 0
            grid[x][lower_wall_y] = 1
            for y in range(lower_wall_y + 1, channel_bottom + 1):
                grid[x][y] = 0

    # 일반 모세혈관 구간의 위쪽/아래쪽 벽을 두껍게 유지한다.
    # 토리 구간에서는 아래쪽 벽 아래를 조직 공간으로 열어 둔다.
    for x in range(thin_start_x, thin_end_x):
        for y in range(channel_top, vessel_top_y):
            grid[x][y] = 1
        # 내강 바로 아래 벽 한 칸만 유지
        grid[x][lower_wall_y] = 1
        for y in range(lower_wall_y + 1, channel_bottom + 1):
            grid[x][y] = 0

    # 토리 구간과 일반 모세혈관 사이의 연결은 같은 높이에서 유지한다.
    # 화면 왼쪽 끝에서 바로 혈관으로 들어오도록 별도의 왼쪽 차단벽은 두지 않는다.
    spawner_y = vessel_top_y
    spawner_pos = (start_x, spawner_y)
    grid[start_x][spawner_y] = 2

    # 출구는 화면 맨 오른쪽 끝에 둔다.
    despawner_coords = []
    for y in (vessel_top_y, vessel_bottom_y):
        grid[end_x][y] = 3
        despawner_coords.append((end_x, y))

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

        if frame_count % 8 == 0:

            substances.append(Substance(spawner_pos[0], spawner_pos[1]))

        # --- 1단계: 현재 프레임의 물질 위치 맵 구성 (9칸 주변 개수 조회를 위함) ---

        substance_grid = [[[] for _ in range(ROWS)] for _ in range(COLS)]

        for sub in substances:

            substance_grid[sub.x][sub.y].append(sub)

        # --- 2단계: 모든 물질의 미래 이동 위치 계산 (반발력 + 브라운 운동 + 일괄 처리) ---

        future_positions = []

        cell_pass_probability = 0.2

        for sub in substances:

            # 이미 출구(Despawner)에 도달한 경우 스킵

            if grid[sub.x][sub.y] == 3:

                continue

            current_x, current_y = sub.x, sub.y

            # --- [파트 1] 반발력 + 흐름장 기반 이동 계산 ---

            fx_dir, fy_dir = flow_field[current_x][current_y]

            # 9칸 주변(3x3 영역)의 다른 물질 개수 조사

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

            # --- [파트 2] 브라운 운동 (Diffusion) 추가 적용 ---

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

        # --- 3단계: 일괄 업데이트 (Batch Update) ---

        new_substances = []

        for sub, nx, ny in future_positions:

            if 0 <= nx < COLS and 0 <= ny < ROWS and grid[nx][ny] == 3:

                continue  # 출구 도착 시 소멸

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
