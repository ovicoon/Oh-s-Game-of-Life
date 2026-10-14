import json
import os
import sys
from pathlib import Path

import pygame


# 한글이 표시되는 글꼴을 운영체제별로 순서대로 찾습니다.
# Windows: 맑은 고딕 / Malgun Gothic
# macOS: AppleGothic
# Linux: Noto Sans CJK KR, NanumGothic 등
def load_korean_font(size, bold=False):
    candidates = [
        "Malgun Gothic",
        "맑은 고딕",
        "AppleGothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
        "NanumGothic",
        "Nanum Gothic",
        "UnDotum",
        "Gulim",
        "Arial Unicode MS",
    ]
    available = {name.lower(): name for name in pygame.font.get_fonts()}
    for candidate in candidates:
        key = candidate.lower().replace(" ", "").replace("-", "")
        for installed in available.values():
            normalized = installed.lower().replace(" ", "").replace("-", "")
            if normalized == key:
                return pygame.font.SysFont(installed, size, bold=bold)
    # 한글 글꼴이 없으면 시스템 기본 글꼴을 사용합니다.
    # Linux에서는 별도로 한글 글꼴을 설치해야 한글이 정상 표시될 수 있습니다.
    return pygame.font.SysFont(None, size, bold=bold)


# 편집기 설정
GRID_SIZE = 20
COLS = 40
ROWS = 30
PANEL_WIDTH = 240
MARGIN = 16
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
    0: "0  빈 공간",
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


def save_map(grid):
    # 이 파이썬 파일과 같은 폴더에 저장합니다.
    path = Path(__file__).resolve().parent / "map.json"
    payload = {
        "cols": COLS,
        "rows": ROWS,
        "grid": grid,  # 기존 시뮬레이션과 같은 grid[x][y] 구조
        "legend": {
            "0": "빈 공간",
            "1": "벽 / 세포막",
            "2": "입구 / 스포너",
            "3": "출구 / 디스파워너",
        },
    }
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    return path


def main():
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("맵 편집기")
    clock = pygame.time.Clock()

    font = load_korean_font(22, bold=True)
    body = load_korean_font(18)
    small = load_korean_font(15)

    # grid[x][y]: 0=빈 공간, 1=벽, 2=입구, 3=출구
    grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]

    panel_x = GRID_WIDTH
    button_x = panel_x + MARGIN
    button_w = PANEL_WIDTH - MARGIN * 2
    save_rect = pygame.Rect(button_x, 390, button_w, 42)
    clear_rect = pygame.Rect(button_x, 442, button_w, 38)

    status = "칸을 클릭해 값을 바꾸세요."
    status_color = MUTED
    status_expiry = 0
    running = True

    def draw_text(text, x, y, selected_font=body, color=TEXT):
        surface = selected_font.render(text, True, color)
        screen.blit(surface, (x, y))

    def draw_button(rect, label, mouse_pos, base, hover):
        color = hover if rect.collidepoint(mouse_pos) else base
        pygame.draw.rect(screen, color, rect, border_radius=5)
        surface = body.render(label, True, (255, 255, 255))
        screen.blit(
            surface,
            (
                rect.centerx - surface.get_width() // 2,
                rect.centery - surface.get_height() // 2,
            ),
        )

    while running:
        clock.tick(FPS)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                if 0 <= mx < GRID_WIDTH and 0 <= my < GRID_HEIGHT:
                    gx, gy = mx // GRID_SIZE, my // GRID_SIZE
                    grid[gx][gy] = (grid[gx][gy] + 1) % 4

                elif save_rect.collidepoint(event.pos):
                    try:
                        saved_path = save_map(grid)
                        status = f"저장 완료: {saved_path.name}"
                        status_color = (100, 230, 150)
                    except OSError as exc:
                        status = f"저장 실패: {exc}"
                        status_color = (255, 130, 120)
                    status_expiry = pygame.time.get_ticks() + 4000

                elif clear_rect.collidepoint(event.pos):
                    grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]
                    status = "맵을 초기화했습니다."
                    status_color = MUTED
                    status_expiry = pygame.time.get_ticks() + 2500

        screen.fill(BG)

        # 격자 영역
        for x in range(COLS):
            for y in range(ROWS):
                rect = pygame.Rect(x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
                pygame.draw.rect(screen, COLORS[grid[x][y]], rect)
                pygame.draw.rect(screen, GRID_LINE, rect, 1)

        # 오른쪽 패널: 고정 폭과 고정 좌표를 사용해 겹침을 방지합니다.
        pygame.draw.rect(
            screen,
            PANEL_BG,
            pygame.Rect(panel_x, 0, PANEL_WIDTH, WINDOW_HEIGHT),
        )
        draw_text("맵 편집기", panel_x + MARGIN, 18, font)
        draw_text(f"맵 크기: {COLS} x {ROWS}", panel_x + MARGIN, 52, small, MUTED)
        pygame.draw.line(
            screen,
            (65, 65, 65),
            (panel_x + MARGIN, 82),
            (panel_x + PANEL_WIDTH - MARGIN, 82),
            1,
        )

        draw_text("칸의 값", panel_x + MARGIN, 98, body)
        for value in range(4):
            y = 132 + value * 38
            swatch = pygame.Rect(panel_x + MARGIN, y, 24, 24)
            pygame.draw.rect(screen, COLORS[value], swatch, border_radius=3)
            pygame.draw.rect(screen, GRID_LINE, swatch, 1, border_radius=3)
            draw_text(LABELS[value], panel_x + MARGIN + 36, y + 2, small)

        pygame.draw.line(
            screen,
            (65, 65, 65),
            (panel_x + MARGIN, 300),
            (panel_x + PANEL_WIDTH - MARGIN, 300),
            1,
        )
        draw_text("사용 방법", panel_x + MARGIN, 316, body)
        draw_text("왼쪽 클릭: 다음 값으로 변경", panel_x + MARGIN, 346, small)
        draw_text("순서: 0 → 1 → 2 → 3 → 0", panel_x + MARGIN, 368, small)

        draw_button(save_rect, "맵 저장", mouse_pos, BLUE, BLUE_HOVER)
        draw_button(clear_rect, "전체 초기화", mouse_pos, GRAY, GRAY_HOVER)

        if pygame.time.get_ticks() < status_expiry:
            # 긴 오류 메시지가 패널을 넘지 않도록 여러 줄로 나눕니다.
            max_chars = 20
            lines = [
                status[i : i + max_chars] for i in range(0, len(status), max_chars)
            ]
            for i, line in enumerate(lines[:3]):
                draw_text(line, panel_x + MARGIN, 500 + i * 22, small, status_color)
        else:
            draw_text("저장 파일", panel_x + MARGIN, 500, small, MUTED)
            draw_text("map.json", panel_x + MARGIN, 523, body)
            draw_text("편집기 파일과 같은 폴더", panel_x + MARGIN, 552, small, MUTED)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
