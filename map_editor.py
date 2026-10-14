import json
from pathlib import Path

import pygame

# 빠른 드래그 편집 맵 에디터
# 1) 오른쪽 패널에서 블록 종류를 선택합니다.
# 2) 격자에서 마우스를 누른 채 드래그하면 선택한 블록으로 칠해집니다.
# 3) 오른쪽 클릭 또는 지우개 선택으로 0(빈 공간)을 칠할 수 있습니다.

GRID_SIZE = 20
COLS = 40
ROWS = 30
PANEL_WIDTH = 240
FPS = 60

GRID_WIDTH = COLS * GRID_SIZE
GRID_HEIGHT = ROWS * GRID_SIZE
WINDOW_WIDTH = GRID_WIDTH + PANEL_WIDTH
WINDOW_HEIGHT = GRID_HEIGHT

COLORS = {
    0: (35, 35, 35),  # 빈 공간
    1: (100, 100, 120),  # 벽 / 세포막
    2: (46, 204, 113),  # 입구 / 스포너
    3: (231, 76, 60),  # 출구 / 디스파워너
}
LABELS = {
    0: "0  지우개 / 빈 공간",
    1: "1  벽 / 세포막",
    2: "2  입구 / 스포너",
    3: "3  출구 / 디스파워너",
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


def save_map(grid):
    path = Path(__file__).resolve().parent / "map.json"
    payload = {
        "cols": COLS,
        "rows": ROWS,
        "grid": grid,  # 기존 코드와 호환되는 grid[x][y]
        "legend": {
            "0": "빈 공간",
            "1": "벽 / 세포막",
            "2": "입구 / 스포너",
            "3": "출구 / 디스파워너",
        },
    }
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))
    return path


def main():
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("맵 편집기 - 드래그 페인트")
    clock = pygame.time.Clock()

    title_font = load_korean_font(22, True)
    body_font = load_korean_font(17)
    small_font = load_korean_font(14)

    # 표시는 셀마다 다시 글꼴을 렌더링하지 않고, 배경 색상만 그려 빠르게 처리합니다.
    grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]
    panel_x = GRID_WIDTH
    margin = 16
    button_w = PANEL_WIDTH - margin * 2

    palette_rects = {
        value: pygame.Rect(panel_x + margin, 112 + value * 48, button_w, 38)
        for value in range(4)
    }
    save_rect = pygame.Rect(panel_x + margin, 350, button_w, 40)
    clear_rect = pygame.Rect(panel_x + margin, 400, button_w, 36)

    # 한 번의 프레임에서 같은 칸을 반복 수정하지 않도록 합니다.
    last_painted_cell = None
    paint_value = 1
    selected_value = 1
    mouse_painting = False
    status = "블록을 고르고 드래그하세요."
    status_color = MUTED
    status_expiry = 0

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
                    # 패널에서 블록 선택
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
                        status_expiry = pygame.time.get_ticks() + 3500
                        mouse_painting = False
                        last_painted_cell = None
                    elif clear_rect.collidepoint(event.pos):
                        grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]
                        status = "맵을 초기화했습니다."
                        status_color = MUTED
                        status_expiry = pygame.time.get_ticks() + 2500
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
                    # 오른쪽 클릭은 빠른 지우개
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

        # 화면은 매 프레임 갱신하되, 폰트 렌더링은 패널 텍스트에만 제한합니다.
        screen.fill(BG)
        for x in range(COLS):
            px = x * GRID_SIZE
            for y in range(ROWS):
                value = grid[x][y]
                rect = pygame.Rect(px, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
                screen.fill(COLORS[value], rect)
                pygame.draw.rect(screen, GRID_LINE, rect, 1)

        pygame.draw.rect(screen, PANEL_BG, (panel_x, 0, PANEL_WIDTH, WINDOW_HEIGHT))
        draw_text("맵 편집기", panel_x + margin, 18, title_font)
        draw_text(f"맵 크기: {COLS} x {ROWS}", panel_x + margin, 52, small_font, MUTED)
        draw_text("1. 블록 선택", panel_x + margin, 82, body_font)

        mouse_pos = pygame.mouse.get_pos()
        for value, rect in palette_rects.items():
            pygame.draw.rect(screen, COLORS[value], rect, border_radius=4)
            if value == selected_value:
                pygame.draw.rect(screen, (255, 255, 255), rect, 3, border_radius=4)
            else:
                pygame.draw.rect(screen, GRID_LINE, rect, 1, border_radius=4)
            label = body_font.render(LABELS[value], True, (255, 255, 255))
            screen.blit(label, (rect.x + 9, rect.centery - label.get_height() // 2))

        draw_text("2. 격자에서 누른 채 드래그", panel_x + margin, 316, small_font)
        draw_text("오른쪽 클릭: 빈 공간으로 지우기", panel_x + margin, 337, small_font)

        for rect, label, base, hover in (
            (save_rect, "맵 저장", BLUE, BLUE_HOVER),
            (clear_rect, "전체 초기화", GRAY, GRAY_HOVER),
        ):
            color = hover if rect.collidepoint(mouse_pos) else base
            pygame.draw.rect(screen, color, rect, border_radius=5)
            rendered = body_font.render(label, True, (255, 255, 255))
            screen.blit(
                rendered,
                (
                    rect.centerx - rendered.get_width() // 2,
                    rect.centery - rendered.get_height() // 2,
                ),
            )

        if pygame.time.get_ticks() < status_expiry:
            draw_text(status, panel_x + margin, 462, small_font, status_color)
        else:
            draw_text("저장 파일", panel_x + margin, 462, small_font, MUTED)
            draw_text("map.json", panel_x + margin, 484, body_font)
            draw_text(
                "편집기 파일과 같은 폴더", panel_x + margin, 512, small_font, MUTED
            )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
