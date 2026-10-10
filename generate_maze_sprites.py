"""
Генератор спрайтов лабиринта для EasyLearnSite.
Запуск: python generate_maze_sprites.py
Результат: PNG-файлы в static/img/maze/
"""

import os
import math
from PIL import Image, ImageDraw


OUT_DIR = os.path.join('static', 'img', 'maze')
os.makedirs(OUT_DIR, exist_ok=True)

SIZE = 256
RADIUS = 26


def rgba(h, a=255):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (a,)


# ============================================================
# СТЕНА
# ============================================================
def make_wall():
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        [(0, 0), (SIZE - 1, SIZE - 1)],
        radius=RADIUS,
        fill=rgba('#252048'),
    )
    glow = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.rounded_rectangle(
        [(8, 8), (SIZE - 9, SIZE // 2 + 8)],
        radius=RADIUS - 6,
        fill=(255, 255, 255, 26),
    )
    return Image.alpha_composite(img, glow)


# ============================================================
# ПУТЬ
# ============================================================
def make_path():
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        [(0, 0), (SIZE - 1, SIZE - 1)],
        radius=RADIUS,
        fill=rgba('#f5f5fb'),
    )
    return img


# ============================================================
# ИГРОК
# ============================================================
def make_player():
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    d.rounded_rectangle(
        [(0, 0), (SIZE - 1, SIZE - 1)],
        radius=RADIUS,
        fill=rgba('#9b8bf4'),
    )

    cx = SIZE // 2
    cy = SIZE // 2

    face_w, face_h = 130, 140
    fx0 = cx - face_w // 2
    fy0 = cy - 30

    d.ellipse([(fx0 - 14, fy0 + 55), (fx0 + 10, fy0 + 100)], fill=rgba('#f2c9a0'))
    d.ellipse([(fx0 + face_w - 10, fy0 + 55), (fx0 + face_w + 14, fy0 + 100)], fill=rgba('#f2c9a0'))
    d.ellipse([(fx0, fy0), (fx0 + face_w, fy0 + face_h)], fill=rgba('#fbe0c2'))

    dome_w, dome_h = 140, 110
    dx0 = cx - dome_w // 2
    dy0 = fy0 - 60
    d.ellipse([(dx0, dy0), (dx0 + dome_w, dy0 + dome_h)], fill=rgba('#f5a623'))
    d.ellipse([(dx0 + 22, dy0 + 20), (dx0 + 76, dy0 + 52)], fill=(255, 255, 255, 90))
    brim_w, brim_h = 176, 40
    bx0 = cx - brim_w // 2
    by0 = fy0 - 30
    d.ellipse([(bx0, by0), (bx0 + brim_w, by0 + brim_h)], fill=rgba('#e08e0b'))
    d.ellipse(
        [(bx0, by0 + brim_h - 12), (bx0 + brim_w, by0 + brim_h + 8)],
        fill=rgba('#b8730a'),
    )

    eye_r = 13
    eye_y = fy0 + 62
    d.ellipse([(cx - 34 - eye_r, eye_y - eye_r), (cx - 34 + eye_r, eye_y + eye_r)], fill=rgba('#1f2937'))
    d.ellipse([(cx - 38, eye_y - 6), (cx - 30, eye_y + 2)], fill=(255, 255, 255, 240))
    d.ellipse([(cx + 34 - eye_r, eye_y - eye_r), (cx + 34 + eye_r, eye_y + eye_r)], fill=rgba('#1f2937'))
    d.ellipse([(cx + 30, eye_y - 6), (cx + 38, eye_y + 2)], fill=(255, 255, 255, 240))

    d.ellipse([(cx - 60, fy0 + 78), (cx - 38, fy0 + 100)], fill=(244, 114, 182, 90))
    d.ellipse([(cx + 38, fy0 + 78), (cx + 60, fy0 + 100)], fill=(244, 114, 182, 90))

    d.arc(
        [(cx - 22, fy0 + 88), (cx + 22, fy0 + 120)],
        start=20, end=160,
        fill=rgba('#8b4513'),
        width=5,
    )

    return img


# ============================================================
# ФИНИШ
# ============================================================
def make_goal():
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    for i, alpha in [(20, 45), (12, 75), (4, 115)]:
        d.rounded_rectangle(
            [(i, i), (SIZE - 1 - i, SIZE - 1 - i)],
            radius=RADIUS + i // 2,
            fill=rgba('#fbbf24', alpha),
        )

    d.rounded_rectangle(
        [(10, 10), (SIZE - 11, SIZE - 11)],
        radius=RADIUS,
        fill=rgba('#fcd34d'),
    )

    glow = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.rounded_rectangle(
        [(24, 24), (SIZE - 25, SIZE // 2)],
        radius=RADIUS - 8,
        fill=(255, 255, 255, 70),
    )
    img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img)

    pole_w = 10
    pole_h = 140
    pole_x = SIZE // 2 - 70
    pole_y = SIZE // 2 - pole_h // 2

    d.rounded_rectangle(
        [(pole_x + 3, pole_y + 4), (pole_x + pole_w + 3, pole_y + pole_h + 3)],
        radius=4,
        fill=rgba('#3f1f00'),
    )
    d.rounded_rectangle(
        [(pole_x, pole_y), (pole_x + pole_w, pole_y + pole_h)],
        radius=4,
        fill=rgba('#7a3b0f'),
    )
    d.rounded_rectangle(
        [(pole_x + 2, pole_y + 6), (pole_x + 3, pole_y + pole_h - 6)],
        radius=1,
        fill=rgba('#b8730a'),
    )

    fx0 = pole_x + pole_w
    fy0 = pole_y + 8
    flag_size = 110
    cells = 3
    cell_size = flag_size // cells

    black = rgba('#111111')
    white = rgba('#ffffff')

    for row in range(cells):
        for col in range(cells):
            x0 = fx0 + col * cell_size
            y0 = fy0 + row * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            color = black if (row + col) % 2 == 0 else white
            d.rectangle([(x0, y0), (x1, y1)], fill=color)

    d.rectangle(
        [(fx0, fy0), (fx0 + flag_size, fy0 + flag_size)],
        outline=black,
        width=4,
    )

    return img


# ============================================================
# КАПКАН — ярко-красный квадрат с иконкой капкана
# ============================================================
def make_trap():
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ярко-красный фон
    d.rounded_rectangle(
        [(0, 0), (SIZE - 1, SIZE - 1)],
        radius=RADIUS,
        fill=rgba('#ef4444'),
    )

    # верхний блик
    glow = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.rounded_rectangle(
        [(10, 10), (SIZE - 11, SIZE // 2)],
        radius=RADIUS - 8,
        fill=(255, 255, 255, 60),
    )
    img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img)

    cx = SIZE // 2
    cy = SIZE // 2 + 6

    # зубья капкана
    teeth = 12
    r_out = 92
    r_in = 58
    for i in range(teeth):
        a = (2 * math.pi / teeth) * i - math.pi / 2
        px = cx + r_out * math.cos(a)
        py = cy + r_out * math.sin(a)
        a1 = a - math.pi / teeth
        a2 = a + math.pi / teeth
        p1 = (cx + r_in * math.cos(a1), cy + r_in * math.sin(a1))
        p2 = (cx + r_in * math.cos(a2), cy + r_in * math.sin(a2))
        d.polygon([p1, p2, (px, py)], fill=rgba('#111111'))

    # тёмное дно
    d.ellipse([(cx - 60, cy - 60), (cx + 60, cy + 60)], fill=rgba('#7f1d1d'))
    d.ellipse([(cx - 50, cy - 50), (cx + 50, cy + 50)], fill=rgba('#450a0a'))

    # белый восклицательный знак
    d.rounded_rectangle(
        [(cx - 8, cy - 38), (cx + 8, cy + 6)],
        radius=6,
        fill=rgba('#ffffff'),
    )
    d.ellipse(
        [(cx - 10, cy + 18), (cx + 10, cy + 38)],
        fill=rgba('#ffffff'),
    )

    # жёлтая обводка
    d.ellipse(
        [(cx - 92, cy - 92), (cx + 92, cy + 92)],
        outline=rgba('#fbbf24'),
        width=4,
    )

    return img


# ============================================================
def save(img, name):
    p = os.path.join(OUT_DIR, name)
    img.save(p, 'PNG')
    print(f'  ✓ {name}')


print(f'Генерация спрайтов лабиринта ({SIZE}×{SIZE})...')
save(make_wall(),   'wall.png')
save(make_path(),   'path.png')
save(make_path(),   'start.png')
save(make_goal(),   'goal.png')
save(make_player(), 'player.png')
save(make_trap(),   'trap.png')
print(f'\nГотово! Файлы в: {OUT_DIR}')