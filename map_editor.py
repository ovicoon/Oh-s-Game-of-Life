import json
from pathlib import Path
import pygame

GRID_SIZE = 20
COLS = 100
ROWS = 100
PANEL_WIDTH = 260
FPS = 60

GRID_WIDTH = 800
GRID_HEIGHT = 600
WINDOW_WIDTH = GRID_WIDTH + PANEL_WIDTH
WINDOW_HEIGHT = GRID_HEIGHT

# 타일별 색상 (Tile Colors - 0 ~ 7)
COLORS = {
    0: (35, 35, 35),  # Empty
    1: (100, 100, 120),  # Cell Membrane
    2: (46, 204, 113),  # Glucose Spawner
    3: (241, 196, 15),  # Sodium Spawner
    4: (231, 76, 60),  # Despawner / Exit
    5: (155, 89, 182),  # Regular Pump
    6: (52, 152, 219),  # Active Pump
    7: (70, 70, 80),  # Solid Wall
}

# 2열 그리드 배치를 위한 라벨 (Labels for 2-column layout)
LABELS = {
    0: "0. Eraser",
    1: "1. Membrane",
    2: "2. Glu Spawner",
    3: "3. Na Spawner",
    4: "4. Exit",
    5: "5. Reg Pump",
    6: "6. Act Pump",
    7: "7. Solid Wall",
}

DIRECTIONS = {
    "right": (1, 0),
    "left": (-1, 0),
    "up": (0, -1),
    "down": (0, 1),
}

DIRECTION_LABELS = {
    "right": "Right",
    "left": "Left",
    "up": "Up",
    "down": "Down",
}

BG = (20, 20, 20)
PANEL_BG = (29, 29, 29)
GRID_LINE = (65, 65, 65)
TEXT = (240, 240, 240)
MUTED = (185, 185, 185)


def load_font(size, bold=False):
    return pygame.font.SysFont(None, size, bold=bold)


def in_bounds(x, y):
    return 0 <= x < COLS and 0 <= y < ROWS


def draw_direction_triangle(screen, rx, ry, size, direction):
    dx, dy = DIRECTIONS[direction]
    cx = rx + size // 2
    cy = ry + size // 2
    tip = (cx + dx * (size // 4), cy + dy * (size // 4))
    px = -dy
    py = dx
    base_x = cx - dx * (size // 6)
    base_y = cy - dy * (size // 6)
    offset = size // 4
    left = (base_x + px * offset, base_y + py * offset)
    right = (base_x - px * offset, base_y - py * offset)
    pygame.draw.polygon(screen, (45, 45, 45), [tip, left, right])


def load_map():
    path = Path(__file__).resolve().parent / "map.json"
    if not path.exists():
        return (
            [[1 for _ in range(ROWS)] for _ in range(COLS)],
            {},
            "map.json not found (New map created)",
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if data.get("cols") != COLS or data.get("rows") != ROWS or "grid" not in data:
            return (
                [[1 for _ in range(ROWS)] for _ in range(COLS)],
                {},
                "Size mismatch, created new map.",
            )

        grid = data["grid"]
        for x in range(COLS):
            for y in range(ROWS):
                if grid[x][y] not in range(8):
                    return (
                        [[1 for _ in range(ROWS)] for _ in range(COLS)],
                        {},
                        "Invalid value found, created new map.",
                    )

        active_pump_directions = {}
        for item in data.get("active_pumps", []):
            try:
                x = int(item["x"])
                y = int(item["y"])
                direction = item["direction"]
                if in_bounds(x, y) and grid[x][y] == 6 and direction in DIRECTIONS:
                    active_pump_directions[(x, y)] = direction
            except (KeyError, TypeError, ValueError):
                continue

        return grid, active_pump_directions, f"Loaded successfully: {path.name}"

    except Exception:
        return (
            [[1 for _ in range(ROWS)] for _ in range(COLS)],
            {},
            "Load failed, created new map.",
        )


def save_map(grid, active_pump_directions):
    path = Path(__file__).resolve().parent / "map.json"
    active_pumps = []

    for x in range(COLS):
        for y in range(ROWS):
            if grid[x][y] != 6:
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
            "0": "Empty",
            "1": "Cell Membrane",
            "2": "Glucose Spawner",
            "3": "Sodium Spawner",
            "4": "Exit",
            "5": "Regular Pump",
            "6": "Active Pump",
            "7": "Solid Wall",
        },
    }

    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))

    return path


def main():
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Oh's Game Of Life - Map Editor")
    clock = pygame.time.Clock()

    title_font = load_font(18, True)
    small_font = load_font(12)

    loaded_grid, loaded_directions, init_status = load_map()
    if loaded_grid is not None:
        grid = loaded_grid
        active_pump_directions = loaded_directions
    else:
        grid = [[1 for _ in range(ROWS)] for _ in range(COLS)]
        active_pump_directions = {}

    grid_size = float(GRID_SIZE)
    camera_x = 0.0
    camera_y = 0.0

    panel_x = GRID_WIDTH
    margin = 10
    col_w = (PANEL_WIDTH - margin * 3) // 2  # 2열 배치를 위한 너비

    # 2열 그리드 형태로 팔레트 버튼 생성 (공간 절약)
    palette_rects = {}
    for value in range(8):
        row_idx = value // 2
        col_idx = value % 2
        bx = panel_x + margin + col_idx * (col_w + margin)
        by = 45 + row_idx * 32
        palette_rects[value] = pygame.Rect(bx, by, col_w, 26)

    # 방향 설정 버튼 영역 조정
    dir_start_y = 185
    direction_rects = {
        "up": pygame.Rect(panel_x + margin + 55, dir_start_y, 55, 25),
        "left": pygame.Rect(panel_x + margin, dir_start_y + 28, 80, 25),
        "right": pygame.Rect(panel_x + margin + 85, dir_start_y + 28, 80, 25),
        "down": pygame.Rect(panel_x + margin + 55, dir_start_y + 56, 55, 25),
    }

    save_rect = pygame.Rect(panel_x + margin, 290, PANEL_WIDTH - margin * 2, 32)
    clear_rect = pygame.Rect(panel_x + margin, 332, PANEL_WIDTH - margin * 2, 28)

    selected_value = 1
    selected_pump = None

    mouse_painting = False
    paint_value = 1
    last_painted_cell = None

    panning = False
    pan_start_pos = (0, 0)

    status = init_status
    status_color = (100, 230, 150) if "Loaded" in init_status else MUTED
    status_expiry = pygame.time.get_ticks() + 3000

    def set_status(message, color=MUTED, duration=2500):
        nonlocal status, status_color, status_expiry
        status = message
        status_color = color
        status_expiry = pygame.time.get_ticks() + duration

    def draw_text(text, x, y, font, color=TEXT):
        screen.blit(font.render(text, True, color), (x, y))

    def screen_to_grid(mx, my):
        if not (0 <= mx < GRID_WIDTH and 0 <= my < GRID_HEIGHT):
            return None
        gx = int((mx - camera_x) // grid_size)
        gy = int((my - camera_y) // grid_size)
        if in_bounds(gx, gy):
            return gx, gy
        return None

    def paint_at(pos, value):
        cell = screen_to_grid(*pos)
        if cell is None:
            return None
        if cell == last_painted_cell:
            return None

        x, y = cell
        old_value = grid[x][y]

        if old_value == 6 and value != 6:
            active_pump_directions.pop((x, y), None)

        grid[x][y] = value
        if value == 6:
            active_pump_directions.setdefault((x, y), "right")

        return cell

    def set_pump_direction(direction):
        if selected_pump is None:
            set_status("Please select an active pump first.", (255, 180, 100))
            return

        x, y = selected_pump
        if grid[x][y] != 6:
            set_status("No active pump at selected position.")
            return

        active_pump_directions[(x, y)] = direction
        set_status(
            f"Pump ({x}, {y}) Direction: {DIRECTION_LABELS[direction]}", (100, 230, 150)
        )

    running = True
    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if 0 <= mx < GRID_WIDTH and 0 <= my < GRID_HEIGHT:
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
                mx, my = event.pos

                if event.button == 2:
                    if 0 <= mx < GRID_WIDTH and 0 <= my < GRID_HEIGHT:
                        panning = True
                        pan_start_pos = event.pos

                elif event.button == 1:
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
                            set_status(f"Saved: {path.name}", (100, 230, 150), 3000)
                        except OSError as exc:
                            set_status(f"Save failed: {exc}", (255, 130, 120), 3000)
                        mouse_painting = False
                        last_painted_cell = None

                    elif clear_rect.collidepoint(event.pos):
                        grid = [[1 for _ in range(ROWS)] for _ in range(COLS)]
                        active_pump_directions.clear()
                        selected_pump = None
                        set_status("Map cleared (Filled with membrane)")
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

                        else:
                            cell = screen_to_grid(mx, my)
                            if cell is not None:
                                x, y = cell
                                if grid[x][y] == 6:
                                    selected_pump = (x, y)

                                mouse_painting = True
                                paint_value = selected_value
                                last_painted_cell = None

                                painted_cell = paint_at(event.pos, paint_value)
                                if painted_cell is not None:
                                    last_painted_cell = painted_cell

                                if grid[x][y] == 6:
                                    selected_pump = (x, y)

                elif event.button == 3:
                    cell = screen_to_grid(mx, my)
                    if cell is not None:
                        x, y = cell
                        if grid[x][y] == 6:
                            active_pump_directions.pop((x, y), None)

                        grid[x][y] = 0
                        if selected_pump == (x, y):
                            selected_pump = None

                        mouse_painting = True
                        paint_value = 0
                        last_painted_cell = (x, y)

            elif event.type == pygame.MOUSEMOTION:
                if panning:
                    mx, my = event.pos
                    dx = mx - pan_start_pos[0]
                    dy = my - pan_start_pos[1]
                    camera_x += dx
                    camera_y += dy
                    pan_start_pos = (mx, my)
                elif mouse_painting:
                    cell = paint_at(event.pos, paint_value)
                    if cell is not None:
                        last_painted_cell = cell
                        x, y = cell
                        if grid[x][y] == 6:
                            selected_pump = (x, y)
                        elif selected_pump == (x, y):
                            selected_pump = None

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    panning = False
                elif event.button in (1, 3):
                    mouse_painting = False
                    last_painted_cell = None

        # 렌더링 (Rendering)
        screen.fill(BG)

        for x in range(COLS):
            for y in range(ROWS):
                rx = camera_x + x * grid_size
                ry = camera_y + y * grid_size

                if (
                    rx + grid_size < 0
                    or rx > GRID_WIDTH
                    or ry + grid_size < 0
                    or ry > GRID_HEIGHT
                ):
                    continue

                rect = pygame.Rect(
                    int(rx), int(ry), int(grid_size) + 1, int(grid_size) + 1
                )
                value = grid[x][y]
                screen.fill(COLORS[value], rect)

                if value == 6:
                    direction = active_pump_directions.get((x, y), "right")
                    draw_direction_triangle(
                        screen, int(rx), int(ry), int(grid_size), direction
                    )

                pygame.draw.rect(screen, GRID_LINE, rect, 1)

                if selected_pump == (x, y):
                    pygame.draw.rect(screen, (255, 255, 255), rect, 2)

        pygame.draw.rect(screen, PANEL_BG, (panel_x, 0, PANEL_WIDTH, WINDOW_HEIGHT))

        draw_text("Map Editor", panel_x + margin, 10, title_font)
        draw_text(
            f"{COLS}x{ROWS}", panel_x + PANEL_WIDTH - margin - 45, 14, small_font, MUTED
        )

        # 팔레트 버튼 렌더링 (2열 배치)
        for value, rect in palette_rects.items():
            is_selected = selected_value == value
            border_color = (255, 255, 255) if is_selected else (80, 80, 80)
            pygame.draw.rect(screen, COLORS[value], rect)
            pygame.draw.rect(screen, border_color, rect, 2 if is_selected else 1)
            draw_text(LABELS[value], rect.x + 4, rect.y + 6, small_font, TEXT)

        # 방향 설정 버튼 렌더링
        draw_text(
            "Active Pump Direction:",
            panel_x + margin,
            dir_start_y - 18,
            small_font,
            MUTED,
        )
        for direction, rect in direction_rects.items():
            pygame.draw.rect(screen, (60, 60, 70), rect)
            pygame.draw.rect(screen, (90, 90, 100), rect, 1)
            draw_text(
                DIRECTION_LABELS[direction], rect.x + 8, rect.y + 6, small_font, TEXT
            )

        # 저장 및 초기화 버튼 렌더링
        pygame.draw.rect(screen, (41, 128, 185), save_rect)
        draw_text("Save Map", save_rect.x + 65, save_rect.y + 8, title_font, TEXT)

        pygame.draw.rect(screen, (192, 57, 43), clear_rect)
        draw_text("Clear Map", clear_rect.x + 60, clear_rect.y + 6, title_font, TEXT)

        if pygame.time.get_ticks() < status_expiry:
            draw_text(
                status, panel_x + margin, WINDOW_HEIGHT - 30, small_font, status_color
            )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
