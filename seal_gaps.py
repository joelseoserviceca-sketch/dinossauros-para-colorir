#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seal small gaps in coloring-page line art so bucket-fill can't leak.

Method: thin the line art to a skeleton, find line endpoints, and bridge
each endpoint to the nearest nearby skeleton pixel (endpoint-to-line or
endpoint-to-endpoint). Surgical: line thickness and art otherwise untouched.

Usage:
    python3 seal_gaps.py assets/<slug>/<name>.webp [--max-gap 14] [--dry-run]
    python3 seal_gaps.py --all   # process every assets/*/[0-9]*.webp
"""
import glob
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import cKDTree

# Art region: safely inside the page border, above the brand tag.
AX0, AY0, AX1, AY1 = 100, 100, 1244, 1690
BRIDGE_WIDTH = 5
EDGE_MARGIN = 8  # ignore endpoints this close to the art-region edge
# Endpoints on tiny skeleton components (short interior detail lines like
# knee creases, texture dashes) are never bridged: connecting them to the
# nearest outline draws ugly visible "staple" blobs and closes nothing that
# bucket-fill needs. Real outline breaks live on long components.
MIN_COMP_LEN = 40


def zhang_suen(fg):
    """Zhang-Suen thinning. fg: bool array (True = line). Returns skeleton."""
    img = fg.copy()
    while True:
        changed = False
        for step in (0, 1):
            p2 = np.roll(img, -1, 0)
            p3 = np.roll(np.roll(img, -1, 0), 1, 1)
            p4 = np.roll(img, 1, 1)
            p5 = np.roll(np.roll(img, 1, 0), 1, 1)
            p6 = np.roll(img, 1, 0)
            p7 = np.roll(np.roll(img, 1, 0), -1, 1)
            p8 = np.roll(img, -1, 1)
            p9 = np.roll(np.roll(img, -1, 0), -1, 1)
            nbrs = np.stack([p2, p3, p4, p5, p6, p7, p8, p9])
            seq = np.concatenate([nbrs, nbrs[:1]]).astype(np.uint8)
            trans = ((seq[:-1] == 0) & (seq[1:] == 1)).sum(axis=0)
            ncount = nbrs.sum(axis=0)
            if step == 0:
                cond = (img & (ncount >= 2) & (ncount <= 6) & (trans == 1)
                        & (~p2 | ~p4 | ~p6) & (~p4 | ~p6 | ~p8))
            else:
                cond = (img & (ncount >= 2) & (ncount <= 6) & (trans == 1)
                        & (~p2 | ~p4 | ~p8) & (~p2 | ~p6 | ~p8))
            cond[0, :] = cond[-1, :] = False
            cond[:, 0] = cond[:, -1] = False
            img = img & ~cond
            changed = changed or bool(cond.any())
        if not changed:
            return img


def neighbor_count(skel):
    k = np.ones((3, 3), dtype=np.uint8)
    k[1, 1] = 0
    return ndimage.convolve(skel.astype(np.uint8), k, mode="constant")


def segment_is_white(lines, p0, p1):
    """True if the straight segment between p0/p1 crosses no line pixels."""
    y0, x0 = p0
    y1, x1 = p1
    n = int(max(abs(y1 - y0), abs(x1 - x0))) + 1
    ys = np.linspace(y0, y1, n).astype(int)
    xs = np.linspace(x0, x1, n).astype(int)
    # exclude the two endpoint pixels themselves (they sit on lines)
    if n > 4:
        ys, xs = ys[2:-2], xs[2:-2]
    else:
        return True
    return not lines[ys, xs].any()


def seal_image(gray, max_gap=14):
    """gray: 2D uint8 array (full canvas). Returns (sealed_gray, n_bridges)."""
    art = gray[AY0:AY1, AX0:AX1]
    lines = art < 128
    skel = zhang_suen(lines)
    ncount = neighbor_count(skel)
    ends = np.argwhere(skel & (ncount == 1))
    h, w = skel.shape
    # drop endpoints hugging the region edge (shapes are never clipped there)
    ends = ends[(ends[:, 0] > EDGE_MARGIN) & (ends[:, 0] < h - EDGE_MARGIN)
                & (ends[:, 1] > EDGE_MARGIN) & (ends[:, 1] < w - EDGE_MARGIN)]
    if len(ends) == 0:
        return gray, 0
    # component length per skeleton pixel, to skip tiny detail lines
    # (8-connectivity: diagonal strokes are one component)
    comp, ncomp = ndimage.label(skel, structure=np.ones((3, 3), dtype=int))
    comp_sizes = ndimage.sum(skel, comp, range(1, ncomp + 1))
    coords = np.argwhere(skel)
    tree = cKDTree(coords)
    done = set()
    bridges = []
    for ei, ep in enumerate(ends):
        if ei in done:
            continue
        if comp_sizes[comp[tuple(ep)] - 1] < MIN_COMP_LEN:
            continue  # short interior detail line, not an outline break
        dists, idxs = tree.query(ep, k=14, distance_upper_bound=max_gap + 1)
        dists = np.atleast_1d(dists)
        idxs = np.atleast_1d(idxs)
        for d, ii in zip(dists, idxs):
            if not np.isfinite(d) or d < 1.0 or ii >= len(coords):
                continue
            tgt = coords[ii]
            if max(abs(int(tgt[0]) - int(ep[0])),
                   abs(int(tgt[1]) - int(ep[1]))) <= 4:
                continue  # own branch
            # don't double-bridge the same pair
            key = tuple(sorted((tuple(ep), tuple(tgt))))
            if key in done:
                break
            if segment_is_white(lines, tuple(ep), tuple(tgt)):
                bridges.append((tuple(ep), tuple(tgt)))
                done.add(key)
                # mark the target endpoint as handled too if it's an endpoint
                break
    if not bridges:
        return gray, 0
    out = Image.fromarray(gray)
    dr = ImageDraw.Draw(out)
    for (y0, x0), (y1, x1) in bridges:
        dr.line([AX0 + x0, AY0 + y0, AX0 + x1, AY0 + y1],
                fill=0, width=BRIDGE_WIDTH, joint="curve")
    return np.array(out), len(bridges)


def process_file(path, max_gap=14, dry_run=False):
    img = Image.open(path).convert("L")
    gray = np.array(img)
    sealed, n = seal_image(gray, max_gap=max_gap)
    print(f"  {os.path.basename(path)}: {n} bridges")
    if not dry_run and n:
        Image.fromarray(sealed).save(path)
    return n


def main():
    args = sys.argv[1:]
    max_gap = 14
    if "--max-gap" in args:
        i = args.index("--max-gap")
        max_gap = int(args[i + 1])
        del args[i:i + 2]
    dry_run = "--dry-run" in args
    if dry_run:
        args.remove("--dry-run")
    if args == ["--all"]:
        files = sorted(glob.glob("assets/*/*.webp"))
        files = [f for f in files if os.path.basename(f)[0].isdigit()
                 or "-" in os.path.basename(f)]
        # only numbered coloring images: <base>-N.webp
        files = [f for f in files
                 if os.path.splitext(os.path.basename(f))[0].rsplit("-", 1)[-1].isdigit()]
    else:
        files = args
    total = 0
    for f in files:
        total += process_file(f, max_gap=max_gap, dry_run=dry_run)
    print(f"TOTAL bridges: {total} across {len(files)} files")


if __name__ == "__main__":
    main()
