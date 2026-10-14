import json
from pathlib import Path
import pygame

GRID_SIZE = 20
COLS = 40
ROWS = 30
PANEL_WIDTH = 220
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
}
LABELS = {
    0: "0 지우개",
    1: "1 벽",
    2: "2 생성기",
    3: "3 출구",
    4: "4 펌프",
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


def load_map():
    path = Path(__file__).resolve().parent / "map.json"
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
                if (
                    data.get("cols") == COLS
                    and data.get("rows") == ROWS
                    and "grid" in data
                ):
                    return data["grid"], f"불러오기 완료: {path.name}"
        except Exception as exc:
            return None, f"불러오기 실패: {exc}"
    return None, "map.json 없음"


def save_map(grid):
    path = Path(__file__).resolve().parent / "map.json"
    payload = {
        "cols": COLS,
        "rows": ROWS,
        "grid": grid,
        "legend": {
            "0": "빈 공간",
            "1": "벽 / 세포막",
            "2": "물질 생성기",
            "3": "출구 / 디스파워너",
            "4": "액체 펌프",
        },
    }
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))
    return path


def main():
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("맵 편집기")
    clock = pygame.time.Clock()

    title_font = load_korean_font(20, True)
    body_font = load_korean_font(15)
    small_font = load_korean_font(13)

    loaded_grid, init_status = load_map()
    grid = (
        loaded_grid
        if loaded_grid is not None
        else [[0 for _ in range(ROWS)] for _ in range(COLS)]
    )

    panel_x = GRID_WIDTH
    margin = 12
    button_w = PANEL_WIDTH - margin * 2

    palette_rects = {
        value: pygame.Rect(panel_x + margin, 70 + value * 34, button_w, 30)
        for value in range(5)
    }
    save_rect = pygame.Rect(panel_x + margin, 250, button_w, 36)
    clear_rect = pygame.Rect(panel_x + margin, 292, button_w, 32)

    last_painted_cell = None
    paint_value = 1
    selected_value = 1
    mouse_painting = False
    status = init_status
    status_color = (100, 230, 150) if "완료" in init_status else MUTED
    status_expiry = pygame.time.get_ticks() + 3000

    def draw_text(text, x, y, font, color=TEXT):
        screen.blit(font.render(text, True, color), (x, y))

    def paint_at(pos, value):
        mx, my = pos
        if 0 <= mx < GRID_WIDTH and 0 <= my < GRID_HEIGHT:
            cell = (mx // GRID_SIZE, my // GRID_SIZE)
            if cell != last_painted_cell:
                grid[cell[0]][cell[1]] = value
                return cell
        return None

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
                            path = save_map(grid)
                            status = f"저장 완료: {path.name}"
                            status_color = (100, 230, 150)
                        except OSError as exc:
                            status = f"저장 실패: {exc}"
                            status_color = (255, 130, 120)
                        status_expiry = pygame.time.get_ticks() + 3000
                        mouse_painting = False
                        last_painted_cell = None
                    elif clear_rect.collidepoint(event.pos):
                        grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]
                        status = "초기화됨"
                        status_color = MUTED
                        status_expiry = pygame.time.get_ticks() + 2000
                        mouse_painting = False
                        last_painted_cell = None
                    elif 0 <= mx < GRID_WIDTH and 0 <= my < GRID_HEIGHT:
                        mouse_painting = True
                        paint_value = selected_value
                        last_painted_cell = None
                        cell = paint_at(event.pos, paint_value)
                        if cell is not None:
                            last_painted_cell = cell

                elif event.button == 3:
                    if 0 <= mx < GRID_WIDTH and 0 <= my < GRID_HEIGHT:
                        mouse_painting = True
                        paint_value = 0
                        last_painted_cell = None
                        cell = paint_at(event.pos, 0)
                        if cell is not None:
                            last_painted_cell = cell

            elif event.type == pygame.MOUSEMOTION and mouse_painting:
                cell = paint_at(event.pos, paint_value)
                if cell is not None:
                    last_painted_cell = cell

            elif event.type == pygame.MOUSEBUTTONUP and event.button in (1, 3):
                mouse_painting = False
                last_painted_cell = None

        screen.fill(BG)
        for x in range(COLS):
            px = x * GRID_SIZE
            for y in range(ROWS):
                value = grid[x][y]
                rect = pygame.Rect(px, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
                screen.fill(COLORS[value], rect)
                pygame.draw.rect(screen, GRID_LINE, rect, 1)

        pygame.draw.rect(screen, PANEL_BG, (panel_x, 0, PANEL_WIDTH, WINDOW_HEIGHT))
        draw_text("맵 편집기", panel_x + margin, 14, title_font)
        draw_text(
            f"{COLS}x{ROWS}", panel_x + PANEL_WIDTH - margin - 45, 18, small_font, MUTED
        )

        mouse_pos = pygame.mouse.get_pos()
        for value, rect in palette_rects.items():
            pygame.draw.rect(screen, COLORS[value], rect, border_radius=4)
            if value == selected_value:
                pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=4)
            else:
                pygame.draw.rect(screen, GRID_LINE, rect, 1, border_radius=4)
            label = body_font.render(LABELS[value], True, (255, 255, 255))
            screen.blit(label, (rect.x + 8, rect.centery - label.get_height() // 2))

        for rect, label, base, hover in (
            (save_rect, "맵 저장", BLUE, BLUE_HOVER),
            (clear_rect, "초기화", GRAY, GRAY_HOVER),
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

        if pygame.time.get_ticks() < status_expiry:
            draw_text(status, panel_x + margin, 345, small_font, status_color)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
