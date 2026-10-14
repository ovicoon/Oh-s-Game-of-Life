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

# 8방향 브라운 운동을 위한 오프셋 목록
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
    start_x, end_x = 8, COLS - 6
    channel_top, channel_bottom = 8, 16

    # 1. 위/아래 긴 외곽 벽 설정
    for x in range(start_x, end_x + 1):
        for y in range(channel_top - 3, channel_top):
            grid[x][y] = 1
        for y in range(channel_bottom + 1, channel_bottom + 4):
            grid[x][y] = 1

    # 2. 혈관 내부를 꼬불꼬불하게 만드는 장애물(세포 벽) 추가
    for x in range(20, 25):
        for y in range(channel_top, channel_bottom - 2):
            grid[x][y] = 1
    for x in range(28, 33):
        for y in range(channel_top + 2, channel_bottom + 1):
            grid[x][y] = 1

    # 3. 입구(Spawner) 및 왼쪽 차단 벽 설정
    spawner_y = channel_top + (channel_bottom - channel_top) // 2
    spawner_pos = (start_x, spawner_y)

    # 스포너를 감싸는 왼쪽 및 주변 세포벽 구축 (왼쪽으로 혈액이 새지 않도록 완전 차단)
    for y in range(channel_top, channel_bottom + 1):
        grid[start_x][y] = 1  # 통로 시작면을 전부 세포로 막고
    grid[spawner_pos[0]][spawner_pos[1]] = 2  # 중앙에만 스포너 배치

    # 스포너의 바로 왼쪽 칸들(start_x - 1)도 세포벽으로 채워 왼쪽 공간과 완전히 격리
    for y in range(channel_top - 3, channel_bottom + 4):
        grid[start_x - 1][y] = 1

    # 4. 출구(Despawner) 여러 개 설정 (오른쪽 끝 단면 전체)
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

        new_substances = []
        for sub in substances:
            if grid[sub.x][sub.y] == 3:
                continue

            cell_pass_probability = 0.2

            # 1단계: 강제 이동 (Advection)
            fx_dir, fy_dir = flow_field[sub.x][sub.y]
            fx = sub.x + fx_dir
            fy = sub.y + fy_dir

            if 0 <= fx < COLS and 0 <= fy < ROWS:
                target_cell_type = grid[fx][fy]
                if target_cell_type == 1:
                    if random.random() < cell_pass_probability:
                        sub.x, sub.y = fx, fy
                else:
                    sub.x, sub.y = fx, fy

            if grid[sub.x][sub.y] == 3:
                continue

            # 2단계: 브라운 운동 (Diffusion)
            bdx, bdy = random.choice(DIRECTIONS_8)
            bx = sub.x + bdx
            by = sub.y + bdy

            if 0 <= bx < COLS and 0 <= by < ROWS:
                target_cell_type = grid[bx][by]
                if target_cell_type == 1:
                    if random.random() < cell_pass_probability:
                        sub.x, sub.y = bx, by
                else:
                    sub.x, sub.y = bx, by

            if grid[sub.x][sub.y] == 3:
                continue

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
