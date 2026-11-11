#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brand raw generated images to the locked pipeline spec:
canvas 1344x1792 white; artwork fitted INSIDE border (80,82,1184x1626);
rounded border rx=18, 5px #111111; tag 'dinossaurosparacolorir.com.br'
320px wide, centered x=672, glyph top y~1733, DejaVuSans-Bold.
Outputs per image: <name>.webp (<100KB), <name>.pdf (full-res A4), <name>.svg (vtracer).
"""
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
SLUG = "triceratops-desenhos-para-colorir"
ASSETS = os.path.join(ROOT, "assets", SLUG)
RAW = os.path.join(ASSETS, "raw")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TAG = "dinossaurosparacolorir.com.br"

CANVAS_W, CANVAS_H = 1344, 1792
BX, BY, BW, BH = 80, 82, 1184, 1626  # border rect
RADIUS = 18
STROKE = 5
BORDER_COLOR = "#111111"
TAG_TOP = 1733
TAG_WIDTH = 320
TAG_CX = 672


def fit_font(draw, target_width):
    lo, hi = 8, 200
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = ImageFont.truetype(FONT, mid)
        if draw.textlength(TAG, font=f) <= target_width:
            lo = mid
        else:
            hi = mid - 1
    return ImageFont.truetype(FONT, lo)


def brand(raw_path, out_base):
    img = Image.open(raw_path).convert("RGB")
    # Locked standard: artwork fitted at 90% of border interior (1065x1463 max),
    # never 100% — guarantees minimum white margins around every image.
    scale = min(0.9 * BW / img.width, 0.9 * BH / img.height)
    nw, nh = max(1, int(img.width * scale)), max(1, int(img.height * scale))
    art = img.resize((nw, nh), Image.LANCZOS)

    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), "white")
    canvas.paste(art, (BX + (BW - nw) // 2, BY + (BH - nh) // 2))

    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        [BX, BY, BX + BW, BY + BH], radius=RADIUS,
        outline=BORDER_COLOR, width=STROKE,
    )

    font = fit_font(draw, TAG_WIDTH)
    tw = draw.textlength(TAG, font=font)
    draw.text((TAG_CX - tw / 2, TAG_TOP), TAG, font=font,
             fill="#111111", anchor="lt")

    return canvas


def save_webp(img, path):
    for quality, scale in ((82, 1.0), (78, 1.0), (80, 0.75), (80, 0.6)):
        w, h = (int(img.width * scale), int(img.height * scale)) if scale < 1.0 else img.size
        im = img.resize((w, h), Image.LANCZOS) if scale < 1.0 else img
        im.save(path, "WEBP", quality=quality, method=6)
        if os.path.getsize(path) < 100 * 1024:
            return w, h
    return img.size  # last attempt even if slightly over


def save_svg(img, path):
    import vtracer
    tmp = path + ".tmp.png"
    img.save(tmp, "PNG")
    try:
        vtracer.convert_image_to_svg_py(
            tmp, path, colormode="binary",
            filter_speckle=4, color_precision=6, path_precision=3,
        )
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def main():
    results = []
    for n in range(1, 11):
        hits = sorted(glob.glob(os.path.join(RAW, f"*triceratops-raw-{n}-*.webp")))
        if not hits:
            print(f"[{n}] RAW MISSING", flush=True)
            results.append((n, False))
            continue
        raw = hits[0]
        base = f"triceratops-{n}"
        canvas = brand(raw, base)
        wp = os.path.join(ASSETS, base + ".webp")
        pdf = os.path.join(ASSETS, base + ".pdf")
        svg = os.path.join(ASSETS, base + ".svg")
        wsize = save_webp(canvas, wp)
        canvas.save(pdf, "PDF", resolution=150.0)
        save_svg(canvas, svg)
        ok = os.path.getsize(wp) < 100 * 1024
        print(f"[{n}] {os.path.basename(raw)} -> {base} | webp {os.path.getsize(wp)//1024}KB {wsize} "
              f"| pdf {os.path.getsize(pdf)//1024}KB | svg {os.path.getsize(svg)//1024}KB "
              f"{'OK' if ok else 'WEBP-OVER'}", flush=True)
        results.append((n, ok))
    failed = [n for n, ok in results if not ok]
    print("FAILED:", failed if failed else "none")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
