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
    1: (100, 100, 120),
    2: (46, 204, 113),
    3: (231, 76, 60),
    4: (155, 89, 182),
    5: (241, 196, 15),
}

LABELS = {
    0: "0 지우개",
    1: "1 벽",
    2: "2 생성기",
    3: "3 출구",
    4: "4 물펌프",
    5: "5 능동수송 펌프",
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

DIRECTION_ORDER = ["up", "down", "left", "right"]

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
    """펌프 칸 안에 방향을 가리키는 삼각형을 그린다."""

    dx, dy = DIRECTIONS[direction]

    cx = x * GRID_SIZE + GRID_SIZE // 2
    cy = y * GRID_SIZE + GRID_SIZE // 2

    tip = (cx + dx * 7, cy + dy * 7)

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
        (45, 45, 45),
        [tip, left, right],
    )


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

        # 좌표별 펌프 방향 복원
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

        return (
            grid,
            active_pump_directions,
            f"불러오기 완료: {path.name}",
        )

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
            "1": "벽 / 세포막",
            "2": "물질 생성기",
            "3": "출구 / 디스포너",
            "4": "액체 펌프",
            "5": "능동수송 펌프",
        },
    }

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    return path


def main():
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

    pygame.display.set_caption("맵 에디터")
    clock = pygame.time.Clock()

    title_font = load_korean_font(20, True)
    body_font = load_korean_font(15)
    small_font = load_korean_font(13)

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

    palette_rects = {
        value: pygame.Rect(
            panel_x + margin,
            60 + value * 33,
            button_w,
            29,
        )
        for value in range(6)
    }

    # 펌프 방향 선택 버튼
    direction_rects = {
        "up": pygame.Rect(panel_x + margin + 57, 300, 48, 29),
        "left": pygame.Rect(panel_x + margin, 333, 74, 29),
        "right": pygame.Rect(panel_x + margin + 82, 333, 74, 29),
        "down": pygame.Rect(panel_x + margin + 57, 366, 48, 29),
    }

    save_rect = pygame.Rect(panel_x + margin, 410, button_w, 34)

    clear_rect = pygame.Rect(panel_x + margin, 450, button_w, 30)

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
        screen.blit(
            font.render(text, True, color),
            (x, y),
        )

    def paint_at(pos, value):
        mx, my = pos

        if not (0 <= mx < GRID_WIDTH and 0 <= my < GRID_HEIGHT):
            return None

        cell = (
            mx // GRID_SIZE,
            my // GRID_SIZE,
        )

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
            set_status(
                "먼저 맵에서 능동수송 펌프를 선택하세요.",
                (255, 180, 100),
            )
            return

        x, y = selected_pump

        if grid[x][y] != 5:
            set_status("선택한 위치에 능동수송 펌프가 없습니다.")
            return

        active_pump_directions[(x, y)] = direction

        set_status(
            f"펌프 ({x}, {y}) 방향: " f"{DIRECTION_LABELS[direction]}",
            (100, 230, 150),
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
                            path = save_map(
                                grid,
                                active_pump_directions,
                            )
                            set_status(
                                f"저장 완료: {path.name}",
                                (100, 230, 150),
                                3000,
                            )
                        except OSError as exc:
                            set_status(
                                f"저장 실패: {exc}",
                                (255, 130, 120),
                                3000,
                            )

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

                            # 기존 능동수송 펌프를 클릭하면
                            # 방향 편집 대상으로 선택한다.
                            if grid[x][y] == 5:
                                selected_pump = (x, y)

                            mouse_painting = True
                            paint_value = selected_value
                            last_painted_cell = None

                            cell = paint_at(
                                event.pos,
                                paint_value,
                            )

                            if cell is not None:
                                last_painted_cell = cell

                            # 새로 펌프를 배치한 경우 선택
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
                cell = paint_at(
                    event.pos,
                    paint_value,
                )

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

        # ---------------- 렌더링 ----------------

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

                    draw_direction_triangle(
                        screen,
                        x,
                        y,
                        direction,
                    )

                pygame.draw.rect(
                    screen,
                    GRID_LINE,
                    rect,
                    1,
                )

                if selected_pump == (x, y):
                    pygame.draw.rect(
                        screen,
                        (255, 255, 255),
                        rect,
                        2,
                    )

        pygame.draw.rect(
            screen,
            PANEL_BG,
            (panel_x, 0, PANEL_WIDTH, WINDOW_HEIGHT),
        )

        draw_text(
            "맵 에디터",
            panel_x + margin,
            12,
            title_font,
        )

        draw_text(
            f"{COLS}x{ROWS}",
            panel_x + PANEL_WIDTH - margin - 45,
            17,
            small_font,
            MUTED,
        )

        mouse_pos = pygame.mouse.get_pos()

        for value, rect in palette_rects.items():
            pygame.draw.rect(
                screen,
                COLORS[value],
                rect,
                border_radius=4,
            )

            if value == selected_value:
                pygame.draw.rect(
                    screen,
                    (255, 255, 255),
                    rect,
                    2,
                    border_radius=4,
                )
            else:
                pygame.draw.rect(
                    screen,
                    GRID_LINE,
                    rect,
                    1,
                    border_radius=4,
                )

            label = body_font.render(
                LABELS[value],
                True,
                (30, 30, 30) if value == 5 else (255, 255, 255),
            )

            screen.blit(
                label,
                (
                    rect.x + 8,
                    rect.centery - label.get_height() // 2,
                ),
            )

        draw_text(
            "능동수송 펌프 방향",
            panel_x + margin,
            270,
            body_font,
        )

        if selected_pump is not None:
            sx, sy = selected_pump

            if grid[sx][sy] == 5:
                direction = active_pump_directions.get((sx, sy), "right")

                draw_text(
                    f"선택: ({sx}, {sy})",
                    panel_x + margin,
                    290,
                    small_font,
                    MUTED,
                )

                draw_text(
                    f"현재: {DIRECTION_LABELS[direction]}",
                    panel_x + margin + 110,
                    290,
                    small_font,
                    MUTED,
                )
            else:
                selected_pump = None

        for direction, rect in direction_rects.items():
            color = BLUE_HOVER if rect.collidepoint(mouse_pos) else GRAY

            pygame.draw.rect(
                screen,
                color,
                rect,
                border_radius=4,
            )

            label = DIRECTION_LABELS[direction]

            rendered = body_font.render(
                label,
                True,
                (255, 255, 255),
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

            pygame.draw.rect(
                screen,
                color,
                rect,
                border_radius=4,
            )

            rendered = body_font.render(
                label,
                True,
                (255, 255, 255),
            )

            screen.blit(
                rendered,
                (
                    rect.centerx - rendered.get_width() // 2,
                    rect.centery - rendered.get_height() // 2,
                ),
            )

        draw_text(
            "좌클릭: 배치 / 선택",
            panel_x + margin,
            495,
            small_font,
            MUTED,
        )

        draw_text(
            "우클릭: 지우기",
            panel_x + margin,
            515,
            small_font,
            MUTED,
        )

        draw_text(
            "펌프 선택 후 방향 버튼 클릭",
            panel_x + margin,
            535,
            small_font,
            MUTED,
        )

        if pygame.time.get_ticks() < status_expiry:
            # 상태 메시지를 패널 폭에 맞게 자른다.
            max_width = PANEL_WIDTH - margin * 2
            rendered = small_font.render(
                status,
                True,
                status_color,
            )

            if rendered.get_width() > max_width:
                while status and small_font.size(status + "...")[0] > max_width:
                    status = status[:-1]

                rendered = small_font.render(
                    status + "...",
                    True,
                    status_color,
                )

            screen.blit(
                rendered,
                (panel_x + margin, 565),
            )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
