import json
from pathlib import Path
import pygame

GRID_SIZE = 20
COLS = 40
ROWS = 30
PANEL_WIDTH = 260
FPS = 60

GRID_WIDTH = COLS * GRID_SIZE
GRID_HEIGHT = ROWS * GRID_SIZE
WINDOW_WIDTH = GRID_WIDTH + PANEL_WIDTH
WINDOW_HEIGHT = GRID_HEIGHT

COLORS = {
    0: (35, 35, 35),
    1: (100, 100, 120),  # 세포막
    2: (46, 204, 113),  # 생성기
    3: (231, 76, 60),  # 출구
    4: (155, 89, 182),  # 일반 펌프
    5: (241, 196, 15),  # 능동수송 펌프
    6: (70, 70, 80),  # 단단한 벽 추가
}

LABELS = {
    0: "0 지우개",
    1: "1 세포막",
    2: "2 생성기",
    3: "3 출구",
    4: "4 일반 펌프",
    5: "5 능동수송 펌프",
    6: "6 단단한 벽",
}

DIRECTIONS = {
    "right": (1, 0),
    "left": (-1, 0),
    "up": (0, -1),
    "down": (0, 1),
}

DIRECTION_LABELS = {
    "right": "오른쪽",
    "left": "왼쪽",
    "up": "위쪽",
    "down": "아래쪽",
}

BG = (20, 20, 20)
PANEL_BG = (29, 29, 29)
GRID_LINE = (65, 65, 65)
TEXT = (240, 240, 240)
MUTED = (185, 185, 185)
BLUE = (52, 152, 219)
BLUE_HOVER = (41, 128, 185)
GRAY = (75, 75, 75)
GRAY_HOVER = (95, 95, 95)


def load_korean_font(size, bold=False):
    installed_fonts = pygame.font.get_fonts()
    normalized = {
        name.lower().replace(" ", "").replace("-", ""): name for name in installed_fonts
    }
    for candidate in (
        "malgungothic",
        "맑은고딕",
        "applegothic",
        "notosanscjkr",
        "notosanskr",
        "nanumgothic",
        "gulim",
        "arialunicodems",
    ):
        if candidate in normalized:
            return pygame.font.SysFont(normalized[candidate], size, bold=bold)
    return pygame.font.SysFont(None, size, bold=bold)


def in_bounds(x, y):
    return 0 <= x < COLS and 0 <= y < ROWS


def draw_direction_triangle(screen, x, y, direction):
    dx, dy = DIRECTIONS[direction]
    cx = x * GRID_SIZE + GRID_SIZE // 2
    cy = y * GRID_SIZE + GRID_SIZE // 2
    tip = (cx + dx * 7, cy + dy * 7)
    px = -dy
    py = dx
    base_x = cx - dx * 4
    base_y = cy - dy * 4
    left = (base_x + px * 5, base_y + py * 5)
    right = (base_x - px * 5, base_y - py * 5)
    pygame.draw.polygon(screen, (45, 45, 45), [tip, left, right])


def load_map():
    path = Path(__file__).resolve().parent / "map.json"
    if not path.exists():
        return None, {}, "map.json 없음"

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if data.get("cols") != COLS or data.get("rows") != ROWS or "grid" not in data:
            return None, {}, "맵 크기가 일치하지 않습니다."

        grid = data["grid"]
        if (
            not isinstance(grid, list)
            or len(grid) != COLS
            or not all(
                isinstance(column, list) and len(column) == ROWS for column in grid
            )
        ):
            return None, {}, "맵 데이터 형식이 올바르지 않습니다."

        # 타일 값 유효성 검사 (0~6 범위 허용)
        for x in range(COLS):
            for y in range(ROWS):
                if grid[x][y] not in range(7):
                    return None, {}, "잘못된 타일 값이 포함되어 있습니다."

        active_pump_directions = {}
        for item in data.get("active_pumps", []):
            try:
                x = int(item["x"])
                y = int(item["y"])
                direction = item["direction"]
                if in_bounds(x, y) and grid[x][y] == 5 and direction in DIRECTIONS:
                    active_pump_directions[(x, y)] = direction
            except (KeyError, TypeError, ValueError):
                continue

        return grid, active_pump_directions, f"불러오기 완료: {path.name}"

    except Exception as exc:
        return None, {}, f"불러오기 실패: {exc}"


def save_map(grid, active_pump_directions):
    path = Path(__file__).resolve().parent / "map.json"
    active_pumps = []

    for x in range(COLS):
        for y in range(ROWS):
            if grid[x][y] != 5:
                continue
            direction = active_pump_directions.get((x, y), "right")
            active_pumps.append(
                {
                    "x": x,
                    "y": y,
                    "direction": direction,
                }
            )

    payload = {
        "cols": COLS,
        "rows": ROWS,
        "grid": grid,
        "active_pumps": active_pumps,
        "legend": {
            "0": "빈 공간",
            "1": "세포막",
            "2": "물질 생성기",
            "3": "출구",
            "4": "일반 펌프",
            "5": "능동수송 펌프",
            "6": "단단한 벽",
        },
    }

    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))

    return path


def main():
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("맵 에디터")
    clock = pygame.time.Clock()

    title_font = load_korean_font(18, True)
    body_font = load_korean_font(14)
    small_font = load_korean_font(12)

    loaded_grid, loaded_directions, init_status = load_map()
    if loaded_grid is not None:
        grid = loaded_grid
        active_pump_directions = loaded_directions
    else:
        grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]
        active_pump_directions = {}

    panel_x = GRID_WIDTH
    margin = 12
    button_w = PANEL_WIDTH - margin * 2

    # 7개의 팔레트 항목(0~6)이 깔끔하게 들어가도록 높이 및 간격 최적화
    palette_rects = {
        value: pygame.Rect(
            panel_x + margin,
            45 + value * 29,
            button_w,
            25,
        )
        for value in range(7)
    }

    # 펌프 방향 버튼 레이아웃
    direction_rects = {
        "up": pygame.Rect(panel_x + margin + 57, 260, 48, 25),
        "left": pygame.Rect(panel_x + margin, 288, 74, 25),
        "right": pygame.Rect(panel_x + margin + 82, 288, 74, 25),
        "down": pygame.Rect(panel_x + margin + 57, 316, 48, 25),
    }

    save_rect = pygame.Rect(panel_x + margin, 360, button_w, 32)
    clear_rect = pygame.Rect(panel_x + margin, 400, button_w, 28)

    selected_value = 1
    selected_pump = None

    mouse_painting = False
    paint_value = 1
    last_painted_cell = None

    status = init_status
    status_color = (100, 230, 150) if "완료" in init_status else MUTED
    status_expiry = pygame.time.get_ticks() + 3000

    def set_status(message, color=MUTED, duration=2500):
        nonlocal status, status_color, status_expiry
        status = message
        status_color = color
        status_expiry = pygame.time.get_ticks() + duration

    def draw_text(text, x, y, font, color=TEXT):
        screen.blit(font.render(text, True, color), (x, y))

    def paint_at(pos, value):
        mx, my = pos
        if not (0 <= mx < GRID_WIDTH and 0 <= my < GRID_HEIGHT):
            return None

        cell = (mx // GRID_SIZE, my // GRID_SIZE)
        if cell == last_painted_cell:
            return None

        x, y = cell
        old_value = grid[x][y]

        if old_value == 5 and value != 5:
            active_pump_directions.pop((x, y), None)

        grid[x][y] = value
        if value == 5:
            active_pump_directions.setdefault((x, y), "right")

        return cell

    def set_pump_direction(direction):
        if selected_pump is None:
            set_status("먼저 맵에서 능동수송 펌프를 선택하세요.", (255, 180, 100))
            return

        x, y = selected_pump
        if grid[x][y] != 5:
            set_status("선택한 위치에 능동수송 펌프가 없습니다.")
            return

        active_pump_directions[(x, y)] = direction
        set_status(
            f"펌프 ({x}, {y}) 방향: {DIRECTION_LABELS[direction]}", (100, 230, 150)
        )

    running = True
    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                if event.button == 1:
                    selected_palette = None
                    for value, rect in palette_rects.items():
                        if rect.collidepoint(event.pos):
                            selected_palette = value
                            break

                    if selected_palette is not None:
                        selected_value = selected_palette
                        mouse_painting = False
                        last_painted_cell = None

                    elif save_rect.collidepoint(event.pos):
                        try:
                            path = save_map(grid, active_pump_directions)
                            set_status(f"저장 완료: {path.name}", (100, 230, 150), 3000)
                        except OSError as exc:
                            set_status(f"저장 실패: {exc}", (255, 130, 120), 3000)
                        mouse_painting = False
                        last_painted_cell = None

                    elif clear_rect.collidepoint(event.pos):
                        grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]
                        active_pump_directions.clear()
                        selected_pump = None
                        set_status("맵 초기화 완료")
                        mouse_painting = False
                        last_painted_cell = None

                    else:
                        clicked_direction = None
                        for direction, rect in direction_rects.items():
                            if rect.collidepoint(event.pos):
                                clicked_direction = direction
                                break

                        if clicked_direction is not None:
                            set_pump_direction(clicked_direction)
                            mouse_painting = False
                            last_painted_cell = None

                        elif 0 <= mx < GRID_WIDTH and 0 <= my < GRID_HEIGHT:
                            x = mx // GRID_SIZE
                            y = my // GRID_SIZE

                            if grid[x][y] == 5:
                                selected_pump = (x, y)

                            mouse_painting = True
                            paint_value = selected_value
                            last_painted_cell = None

                            cell = paint_at(event.pos, paint_value)
                            if cell is not None:
                                last_painted_cell = cell

                            if grid[x][y] == 5:
                                selected_pump = (x, y)

                elif event.button == 3:
                    if 0 <= mx < GRID_WIDTH and 0 <= my < GRID_HEIGHT:
                        x = mx // GRID_SIZE
                        y = my // GRID_SIZE

                        if grid[x][y] == 5:
                            active_pump_directions.pop((x, y), None)

                        grid[x][y] = 0
                        if selected_pump == (x, y):
                            selected_pump = None

                        mouse_painting = True
                        paint_value = 0
                        last_painted_cell = (x, y)

            elif event.type == pygame.MOUSEMOTION and mouse_painting:
                cell = paint_at(event.pos, paint_value)
                if cell is not None:
                    last_painted_cell = cell
                    x, y = cell
                    if grid[x][y] == 5:
                        selected_pump = (x, y)
                    elif selected_pump == (x, y):
                        selected_pump = None

            elif event.type == pygame.MOUSEBUTTONUP and event.button in (1, 3):
                mouse_painting = False
                last_painted_cell = None

        # 렌더링
        screen.fill(BG)

        for x in range(COLS):
            for y in range(ROWS):
                value = grid[x][y]
                rect = pygame.Rect(
                    x * GRID_SIZE,
                    y * GRID_SIZE,
                    GRID_SIZE,
                    GRID_SIZE,
                )
                screen.fill(COLORS[value], rect)

                if value == 5:
                    direction = active_pump_directions.get((x, y), "right")
                    draw_direction_triangle(screen, x, y, direction)

                pygame.draw.rect(screen, GRID_LINE, rect, 1)

                if selected_pump == (x, y):
                    pygame.draw.rect(screen, (255, 255, 255), rect, 2)

        pygame.draw.rect(
            screen,
            PANEL_BG,
            (panel_x, 0, PANEL_WIDTH, WINDOW_HEIGHT),
        )

        draw_text("맵 에디터", panel_x + margin, 10, title_font)
        draw_text(
            f"{COLS}x{ROWS}", panel_x + PANEL_WIDTH - margin - 40, 14, small_font, MUTED
        )

        mouse_pos = pygame.mouse.get_pos()

        # 팔레트 항목 그리기
        for value, rect in palette_rects.items():
            pygame.draw.rect(screen, COLORS[value], rect, border_radius=4)
            if value == selected_value:
                pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=4)
            else:
                pygame.draw.rect(screen, GRID_LINE, rect, 1, border_radius=4)

            label = body_font.render(
                LABELS[value],
                True,
                (30, 30, 30) if value == 5 else (255, 255, 255),
            )
            screen.blit(label, (rect.x + 8, rect.centery - label.get_height() // 2))

        draw_text("능동수송 펌프 방향", panel_x + margin, 240, body_font)

        if selected_pump is not None:
            sx, sy = selected_pump
            if grid[sx][sy] == 5:
                direction = active_pump_directions.get((sx, sy), "right")
                draw_text(
                    f"선택: ({sx}, {sy})", panel_x + margin, 240, small_font, MUTED
                )
            else:
                selected_pump = None

        for direction, rect in direction_rects.items():
            color = BLUE_HOVER if rect.collidepoint(mouse_pos) else GRAY
            pygame.draw.rect(screen, color, rect, border_radius=4)
            rendered = body_font.render(
                DIRECTION_LABELS[direction], True, (255, 255, 255)
            )
            screen.blit(
                rendered,
                (
                    rect.centerx - rendered.get_width() // 2,
                    rect.centery - rendered.get_height() // 2,
                ),
            )

        for rect, label, base, hover in (
            (save_rect, "맵 저장", BLUE, BLUE_HOVER),
            (clear_rect, "맵 초기화", GRAY, GRAY_HOVER),
        ):
            color = hover if rect.collidepoint(mouse_pos) else base
            pygame.draw.rect(screen, color, rect, border_radius=4)
            rendered = body_font.render(label, True, (255, 255, 255))
            screen.blit(
                rendered,
                (
                    rect.centerx - rendered.get_width() // 2,
                    rect.centery - rendered.get_height() // 2,
                ),
            )

        draw_text("좌클릭: 배치 / 선택", panel_x + margin, 445, small_font, MUTED)
        draw_text("우클릭: 지우기", panel_x + margin, 465, small_font, MUTED)

        if pygame.time.get_ticks() < status_expiry:
            rendered = small_font.render(status, True, status_color)
            screen.blit(rendered, (panel_x + margin, 500))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
