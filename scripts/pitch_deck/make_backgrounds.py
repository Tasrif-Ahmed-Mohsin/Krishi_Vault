"""Draw the deck's grid-paper backgrounds: a hand-drawn (slightly wobbly) grid and a dashed border.

Usage: python make_backgrounds.py <out dir>
Writes bg_light.jpg (sage paper, white grid) and bg_dark.jpg (forest board, faint grid, gold dashes), 2400 x 1350.
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

W, H, SS = 2400, 1350, 2  # final size and supersampling
CELL = 218                 # grid cell, px at final size


def wobble_line(draw, points, color, width):
    draw.line(points, fill=color, width=width, joint="curve")


def grid(draw, rnd, color, width):
    # vertical lines
    x = rnd.uniform(0.15, 0.6) * CELL
    while x < W:
        phase, amp, tilt = rnd.uniform(0, 6.3), rnd.uniform(4, 9), rnd.uniform(-10, 10)
        pts = [((x + tilt * (y / H) + amp * math.sin(y / 170 + phase)) * SS, y * SS) for y in range(-20, H + 21, 18)]
        wobble_line(draw, pts, color, width)
        x += CELL * rnd.uniform(0.9, 1.1)
    # horizontal lines
    y = rnd.uniform(0.15, 0.6) * CELL
    while y < H:
        phase, amp, tilt = rnd.uniform(0, 6.3), rnd.uniform(4, 9), rnd.uniform(-12, 12)
        pts = [(x * SS, (y + tilt * (x / W) + amp * math.sin(x / 210 + phase)) * SS) for x in range(-20, W + 21, 18)]
        wobble_line(draw, pts, color, width)
        y += CELL * rnd.uniform(0.9, 1.1)


def dashed_border(draw, rnd, color, width, inset=30, dash=48, gap=26):
    corners = [(inset + rnd.uniform(-6, 6), inset + rnd.uniform(-6, 6)), (W - inset + rnd.uniform(-6, 6), inset + rnd.uniform(-6, 6)),
               (W - inset + rnd.uniform(-6, 6), H - inset + rnd.uniform(-6, 6)), (inset + rnd.uniform(-6, 6), H - inset + rnd.uniform(-6, 6))]
    r = width * SS / 2
    for (x0, y0), (x1, y1) in zip(corners, corners[1:] + corners[:1]):
        length = math.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        nx, ny = -uy, ux
        t, phase = 0.0, rnd.uniform(0, 6.3)
        while t < length:
            d = min(dash * rnd.uniform(0.85, 1.15), length - t)
            seg = []
            for k in range(6):
                s = t + d * k / 5
                off = 7 * math.sin(s / 160 + phase)
                seg.append(((x0 + ux * s + nx * off) * SS, (y0 + uy * s + ny * off) * SS))
            draw.line(seg, fill=color, width=width * SS, joint="curve")
            for px, py in (seg[0], seg[-1]):  # round ends
                draw.ellipse([px - r, py - r, px + r, py + r], fill=color)
            t += d + gap * rnd.uniform(0.8, 1.2)


def paper(base, noise, seed):
    rnd = random.Random(seed)
    img = Image.new("RGB", (W // 4, H // 4), base)
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            n = rnd.gauss(0, noise)
            px[x, y] = tuple(max(0, min(255, int(c + n))) for c in base)
    return img.resize((W * SS, H * SS), Image.BICUBIC).filter(ImageFilter.GaussianBlur(3 * SS)).convert("RGBA")


def make(base, grid_rgba, border_rgba, seed, out):
    rnd = random.Random(seed)
    img = paper(base, 3.5, seed)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    grid(draw, rnd, grid_rgba, 3 * SS)
    dashed_border(draw, rnd, border_rgba, 11)
    img = Image.alpha_composite(img, layer).convert("RGB").resize((W, H), Image.LANCZOS)
    img.save(out, quality=90, optimize=True)
    print("wrote", out)


out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
make((207, 221, 178), (255, 255, 255, 215), (255, 255, 255, 240), 7, out / "bg_light.jpg")
make((27, 67, 50), (255, 255, 255, 30), (242, 176, 53, 190), 11, out / "bg_dark.jpg")
