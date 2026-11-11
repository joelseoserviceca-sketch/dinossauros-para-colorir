#!/usr/bin/env python3
"""QA audit: edge-cut check + uniform fill check for Brazil dino site webps.
Uses the locked verification method from the cron prompt (mask border stroke
band + tag area, find dark pixels outside mask, min distance to border rect,
flag anything <40px from the border).
"""
import glob
import os
import sys

import numpy as np
from PIL import Image

BX, BY, BW, BH = 80, 82, 1184, 1626  # border rect at 1344x1792
CANVAS_W, CANVAS_H = 1344, 1792
INTERIOR_W, INTERIOR_H = BW, BH
MIN_MARGIN = 40
ROOT = os.path.expanduser("~/workspace/brazil-dino-site/assets")


def audit_image(path):
    img = np.asarray(Image.open(path).convert("L"))
    h, w = img.shape
    s = w / CANVAS_W  # webp may be downscaled to fit 90KB; scale all coords
    bx, by, bw, bh = (int(v * s) for v in (BX, BY, BW, BH))
    band = max(4, int(10 * s))  # cover full 5px inner stroke + rounded corner curves + AA
    tag_cut = int(1715 * s)
    min_margin = 40 * s
    dark = img < 128
    mask = np.zeros_like(dark, dtype=bool)
    # mask border stroke bands (top/bottom/left/right)
    mask[by - band:by + band + 1, bx - band:bx + bw + band] = True   # top band
    mask[by + bh - band:by + bh + band + 1, bx - band:bx + bw + band] = True  # bottom band
    mask[by - band:by + bh + band, bx - band:bx + band + 1] = True           # left band
    mask[by - band:by + bh + band, bx + bw - band:bx + bw + band + 1] = True # right band
    mask[tag_cut:, :] = True  # tag area
    art = dark & ~mask
    if not art.any():
        return None, 0.0, s
    ys, xs = np.nonzero(art)
    # distance to border rect edges: inside rect, min dist to nearest edge
    dx = np.minimum(xs - bx, bx + bw - xs)
    dy = np.minimum(ys - by, by + bh - ys)
    d = np.minimum(dx, dy) / s  # back to full-size px
    min_dist = float(d.min())
    # fill %: dark-pixel bbox area relative to interior
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    bbox_area = (x1 - x0 + 1) * (y1 - y0 + 1)
    fill = bbox_area / (INTERIOR_W * INTERIOR_H) * 100
    return min_dist, fill, s


def main():
    slugs = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)))
    print(f"{'post':45s} {'n':>3s} {'min_margin_px':>13s} {'fill%':>7s} {'fill_range':>12s}  flags")
    for slug in slugs:
        files = sorted(glob.glob(os.path.join(ROOT, slug, "*.webp")))
        files = [f for f in files if os.path.basename(f).rsplit(".", 1)[0].rsplit("-", 1)[-1].isdigit()]
        if not files:
            continue
        results = []
        for f in files:
            md, fill, s = audit_image(f)
            results.append((f, md, fill, s))
        fills = [r[2] for r in results]
        bad = [(os.path.basename(r[0]), r[1], r[3]) for r in results if r[1] is not None and r[1] < MIN_MARGIN]
        flag = f"CUT<{MIN_MARGIN}px: " + ", ".join(f"{n}({d:.0f}px,{s:.2f}x)" for n, d, s in bad) if bad else "ok"
        print(f"{slug:45s} {len(files):>3d} {min(r[1] for r in results if r[1] is not None):>13.1f} "
              f"{sum(fills)/len(fills):>6.1f}% {min(fills):.0f}-{max(fills):.0f}%  {flag}")
        # per-image detail for bad ones
        for f, md, fill, s in results:
            if md is not None and md < MIN_MARGIN:
                print(f"    -> {os.path.basename(f)}: min margin {md:.0f}px (scale {s:.2f}), fill {fill:.0f}%")


if __name__ == "__main__":
    main()
