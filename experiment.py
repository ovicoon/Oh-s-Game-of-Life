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
    pygame.display.set_caption("Sealed Spawner Vessel Simulation")
    clock = pygame.time.Clock()

    # 그리드 초기화 (0: 빈 공간, 1: 세포막, 2: 스포너, 3: 디스파워너)
    grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]

    # --- 구조물 배치 설정 ---
    start_x, end_x = 8, COLS - 6  # end_x = 34
    channel_top, channel_bottom = 8, 16

    # 1. 위/아래 긴 외곽 벽 설정
    for x in range(start_x, end_x + 1):
        for y in range(channel_top - 3, channel_top):
            grid[x][y] = 1
        for y in range(channel_bottom + 1, channel_bottom + 4):
            grid[x][y] = 1

    # 2. Despawner 뒤쪽 영역을 완전히 세포벽으로 차단
    for x in range(end_x + 1, COLS):
        for y in range(channel_top - 3, channel_bottom + 4):
            grid[x][y] = 1

    # 3. 혈관 내부 중간 구간을 매우 좁고(두께 1칸) 구불구불하게 설정 (대각선 없이 4방향 직교 연결)
    for x in range(16, end_x):
        for y in range(channel_top, channel_bottom + 1):
            grid[x][y] = 1  # 먼저 해당 구간 내부를 모두 세포벽으로 채움

    # 1칸 두께의 구불구불한 길 좌표 지정 (오직 상/하/좌/우 인접 칸으로만 구성)
    winding_coords = [
        # 첫 번째 상향 꺾임
        (16, 12),
        (17, 12),
        (18, 12),
        (19, 12),
        (19, 11),
        (19, 10),
        # 오른쪽으로 이동 후 하향 꺾임
        (20, 10),
        (21, 10),
        (22, 10),
        (23, 10),
        (23, 11),
        (23, 12),
        (23, 13),
        (23, 14),
        # 오른쪽으로 이동 후 상향 꺾임
        (24, 14),
        (25, 14),
        (26, 14),
        (27, 14),
        (27, 13),
        (27, 12),
        (27, 11),
        (27, 10),
        # 오른쪽으로 이동 후 출구로 연결
        (28, 10),
        (29, 10),
        (30, 10),
        (31, 10),
        (31, 11),
        (31, 12),
        (32, 12),
        (33, 12),
        (34, 12),
    ]
    for px, py in winding_coords:
        if 0 <= px < COLS and 0 <= py < ROWS:
            grid[px][py] = 0

    # 4. 입구(Spawner) 및 왼쪽 차단 벽 설정
    spawner_y = channel_top + (channel_bottom - channel_top) // 2
    spawner_pos = (start_x, spawner_y)

    for y in range(channel_top, channel_bottom + 1):
        grid[start_x][y] = 1
    grid[spawner_pos[0]][spawner_pos[1]] = 2

    for y in range(channel_top - 3, channel_bottom + 4):
        grid[start_x - 1][y] = 1

    # 5. 출구(Despawner) 여러 개 설정 (오른쪽 끝 단면 전체)
    despawner_coords = []
    for y in range(channel_top, channel_bottom + 1):
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
