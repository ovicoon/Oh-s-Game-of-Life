import json
import pygame
from pathlib import Path

# 간단한 맵 편집기
# 마우스로 칸을 클릭하면 0 -> 1 -> 2 -> 3 -> 0 순서로 바뀝니다.
# 저장 버튼을 누르면 현재 맵이 map.json 파일로 저장됩니다.

WIDTH, HEIGHT = 1000, 700
GRID_SIZE = 20
COLS = 40
ROWS = 30
FPS = 60

PANEL_WIDTH = 200
GRID_WIDTH = COLS * GRID_SIZE
GRID_HEIGHT = ROWS * GRID_SIZE
WINDOW_WIDTH = GRID_WIDTH + PANEL_WIDTH
WINDOW_HEIGHT = max(HEIGHT, GRID_HEIGHT + 60)

COLORS = {
    0: (35, 35, 35),       # 빈 공간
    1: (100, 100, 120),    # 벽 / 세포막
    2: (46, 204, 113),     # 입구 / 스포너
    3: (231, 76, 60),      # 출구 / 디스파워너
}
LABELS = {
    0: "0: 빈 공간",
    1: "1: 벽",
    2: "2: 입구",
    3: "3: 출구",
}
BACKGROUND = (20, 20, 20)
GRID_LINE = (65, 65, 65)
TEXT_COLOR = (240, 240, 240)
BUTTON_COLOR = (52, 152, 219)
BUTTON_HOVER = (41, 128, 185)


def save_map(grid):
    """grid[x][y] 형식으로 JSON 파일에 저장합니다."""
    output_path = Path(__file__).resolve().parent / "map.json"
    data = {
        "cols": COLS,
        "rows": ROWS,
        "grid": grid,
        "legend": {
            "0": "빈 공간",
            "1": "벽 / 세포막",
            "2": "입구 / 스포너",
            "3": "출구 / 디스파워너",
        },
    }
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    return output_path


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("간단한 맵 편집기")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    small_font = pygame.font.SysFont(None, 20)

    # grid[x][y] 구조로 관리하므로 기존 시뮬레이션 코드와 호환하기 쉽습니다.
    grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]

    save_button = pygame.Rect(GRID_WIDTH + 20, 250, PANEL_WIDTH - 40, 45)
    clear_button = pygame.Rect(GRID_WIDTH + 20, 305, PANEL_WIDTH - 40, 40)
    status_message = "칸을 클릭해 값을 바꾸세요."
    status_until = 0
    running = True

    while running:
        clock.tick(FPS)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                # 격자 칸 클릭: 0 -> 1 -> 2 -> 3 -> 0
                if 0 <= mx < GRID_WIDTH and 0 <= my < GRID_HEIGHT:
                    gx = mx // GRID_SIZE
                    gy = my // GRID_SIZE
                    grid[gx][gy] = (grid[gx][gy] + 1) % 4

                elif save_button.collidepoint(event.pos):
                    try:
                        path = save_map(grid)
                        status_message = f"저장 완료: {path.name}"
                    except OSError as error:
                        status_message = f"저장 실패: {error}"
                    status_until = pygame.time.get_ticks() + 3000

                elif clear_button.collidepoint(event.pos):
                    grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]
                    status_message = "모든 칸을 0으로 초기화했습니다."
                    status_until = pygame.time.get_ticks() + 2500

        screen.fill(BACKGROUND)

        # 격자 그리기
        for x in range(COLS):
            for y in range(ROWS):
                rect = pygame.Rect(
                    x * GRID_SIZE,
                    y * GRID_SIZE,
                    GRID_SIZE,
                    GRID_SIZE,
                )
                pygame.draw.rect(screen, COLORS[grid[x][y]], rect)
                pygame.draw.rect(screen, GRID_LINE, rect, 1)

        # 오른쪽 안내 패널
        panel_x = GRID_WIDTH
        pygame.draw.rect(
            screen, (28, 28, 28),
            pygame.Rect(panel_x, 0, PANEL_WIDTH, WINDOW_HEIGHT)
        )

        def draw_text(text, x, y, selected_font=font, color=TEXT_COLOR):
            surface = selected_font.render(text, True, color)
            screen.blit(surface, (x, y))

        draw_text("맵 편집기", panel_x + 20, 20)
        draw_text(f"크기: {COLS} x {ROWS}", panel_x + 20, 55, small_font)
        draw_text("값 순환", panel_x + 20, 95)
        for i, value in enumerate((0, 1, 2, 3)):
            y = 125 + i * 30
            pygame.draw.rect(
                screen, COLORS[value],
                pygame.Rect(panel_x + 20, y, 20, 20)
            )
            pygame.draw.rect(
                screen, GRID_LINE,
                pygame.Rect(panel_x + 20, y, 20, 20), 1
            )
            draw_text(LABELS[value], panel_x + 50, y + 1, small_font)

        draw_text("왼쪽 클릭:", panel_x + 20, 270, small_font)
        draw_text("0 → 1 → 2 → 3 → 0", panel_x + 20, 292, small_font)

        save_color = BUTTON_HOVER if save_button.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, save_color, save_button, border_radius=5)
        save_text = font.render("저장", True, (255, 255, 255))
        screen.blit(
            save_text,
            (save_button.centerx - save_text.get_width() // 2,
             save_button.centery - save_text.get_height() // 2)
        )

        clear_color = (90, 90, 90) if clear_button.collidepoint(mouse_pos) else (65, 65, 65)
        pygame.draw.rect(screen, clear_color, clear_button, border_radius=5)
        clear_text = small_font.render("전체 초기화", True, (255, 255, 255))
        screen.blit(
            clear_text,
            (clear_button.centerx - clear_text.get_width() // 2,
             clear_button.centery - clear_text.get_height() // 2)
        )

        if pygame.time.get_ticks() < status_until:
            # 상태 문구를 패널 폭 안에서 간단히 표시
            draw_text(status_message[:24], panel_x + 12, 370, small_font)
        else:
            draw_text("저장 파일:", panel_x + 20, 370, small_font)
            draw_text("map.json", panel_x + 20, 393, small_font)
            draw_text("편집기와 같은 폴더에", panel_x + 20, 430, small_font)
            draw_text("저장됩니다.", panel_x + 20, 452, small_font)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
