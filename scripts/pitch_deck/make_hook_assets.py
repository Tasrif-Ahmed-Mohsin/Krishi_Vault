"""Slide 1's after-the-clip assets.

1. hook_after.jpg: a still of the farmer (a tone-mapped frame of the interview), darkened on the right,
   where the newspaper cards go, and at the bottom left, under the caption. His face stays clear.
2. news_paper.png and journal_paper.png: newsprint for the cards: grain, fibres, slightly rough cut
   edges and a soft shadow, on a transparent canvas with PAD px of margin on every side.

Usage: python make_hook_assets.py <frame.jpg> <out dir> <card width in> <card height in>
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

DPI, PAD = 300, 30
FOREST = (15, 51, 35)


def still(frame, out):
    img = Image.open(frame).convert("RGB").resize((1920, 1080), Image.LANCZOS)
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    px = mask.load()
    for x in range(w):
        # right side: clear until 40% of the width, then up to 88% forest from 58%
        r = min(1.0, max(0.0, (x / w - 0.40) / 0.18)) * 0.88
        for y in range(h):
            # bottom left: a band under the caption, from half the height (below his face)
            b = min(1.0, max(0.0, (y / h - 0.50) / 0.16)) * 0.9 * (1.0 - min(1.0, max(0.0, (x / w - 0.52) / 0.1)))
            px[x, y] = int(255 * max(r, b))
    img = Image.composite(Image.new("RGB", (w, h), FOREST), img, mask)
    img.save(out, quality=90)
    print("wrote", out)


def paper(wi, hi, base, seed, out):
    rnd = random.Random(seed)
    cw, ch = int(wi * DPI), int(hi * DPI)
    W, H = cw + 2 * PAD, ch + 2 * PAD
    # fine grain plus soft, low-frequency mottling (newsprint, not plaster)
    def noise(scale, sigma, blur):
        small = Image.new("L", (max(2, cw // scale), max(2, ch // scale)))
        small.putdata([max(0, min(255, int(128 + rnd.gauss(0, sigma)))) for _ in range(small.width * small.height)])
        return small.resize((cw, ch), Image.BICUBIC).filter(ImageFilter.GaussianBlur(blur))
    fine, mottle = noise(2, 6, 0.8), noise(45, 9, 25)
    sheet = Image.new("RGB", (cw, ch), base)
    sheet = ImageChops.add(sheet, Image.merge("RGB", [fine] * 3), scale=1.0, offset=-128)
    sheet = ImageChops.add(sheet, Image.merge("RGB", [mottle] * 3), scale=1.0, offset=-128)
    # fibres: short faint strokes
    d = ImageDraw.Draw(sheet)
    for _ in range(int(cw * ch / 2500)):
        x, y = rnd.uniform(0, cw), rnd.uniform(0, ch)
        dx, dy = rnd.uniform(-14, 14), rnd.uniform(-3, 3)
        shade = rnd.choice([-10, -6, 6])
        col = tuple(max(0, min(255, c + shade)) for c in base)
        d.line([(x, y), (x + dx, y + dy)], fill=col, width=1)
    # age: slightly darker towards the edges
    vign = Image.new("L", (cw, ch), 0)
    dv = ImageDraw.Draw(vign)
    for i in range(40):
        dv.rectangle([i, i, cw - 1 - i, ch - 1 - i], outline=int(55 * (1 - i / 40)))
    vign = vign.filter(ImageFilter.GaussianBlur(12))
    sheet = Image.composite(Image.new("RGB", (cw, ch), tuple(int(c * 0.86) for c in base)), sheet, vign)
    # the cut: edges wander a few pixels, like a hand-cut clipping
    edge = Image.new("L", (cw, ch), 0)
    pts, n = [], 60
    for i in range(n + 1):
        pts.append((cw * i / n, rnd.uniform(0, 5)))
    for i in range(n + 1):
        pts.append((cw - rnd.uniform(0, 5), ch * i / n))
    for i in range(n, -1, -1):
        pts.append((cw * i / n, ch - rnd.uniform(0, 5)))
    for i in range(n, -1, -1):
        pts.append((rnd.uniform(0, 5), ch * i / n))
    ImageDraw.Draw(edge).polygon(pts, fill=255)
    # shadow, then the sheet, on a transparent canvas
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow = Image.new("L", (W, H), 0)
    shadow.paste(edge.point(lambda v: int(v * 0.55)), (PAD + 7, PAD + 9))
    canvas.paste((0, 0, 0, 255), (0, 0), shadow.filter(ImageFilter.GaussianBlur(9)))
    sheet_rgba = sheet.convert("RGBA")
    sheet_rgba.putalpha(edge)
    canvas.alpha_composite(sheet_rgba, (PAD, PAD))
    canvas.save(out)
    print("wrote", out)


frame, outdir, cw_in, ch_in = sys.argv[1], Path(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
outdir.mkdir(parents=True, exist_ok=True)
still(frame, outdir / "hook_after.jpg")
paper(cw_in, ch_in, (233, 226, 208), 3, outdir / "news_paper.png")      # newsprint
paper(cw_in, ch_in, (246, 243, 234), 5, outdir / "journal_paper.png")   # journal page, a little whiter
