#!/usr/bin/env python3
"""Work out which colourway each product photo shows.

The photos arrive unlabelled, so the colour has to come from the pixels. Two
things make a direct match to the swatch value unreliable: the warm studio
light lifts a black planter to around 80 luminance, nowhere near #0a0909, and
some colourways in the same range are told apart only by hue (Neto's grey and
terracotta sit within one luminance point of each other).

So the photos of one product are clustered by colour, and the clusters are
matched to that product's catalogue colours by rank — darkest cluster to
darkest colour — with hue breaking ties. Everything is relative to the
product's own set, which is what makes it survive the lighting.
"""

import json
import sys
from itertools import permutations
from pathlib import Path

import numpy as np
from PIL import Image

# Reference values for the colour names the store uses.
SWATCH = {
    "black": (10, 9, 9), "white": (247, 247, 247), "grey": (130, 130, 130),
    "gray": (130, 130, 130), "ash grey": (154, 154, 154), "sand": (216, 201, 180),
    "stone": (184, 176, 164), "concrete": (166, 166, 162),
    "terracotta": (181, 98, 63), "orange": (210, 118, 47),
    "sky blue": (168, 196, 214),
}
LUM = np.array([0.299, 0.587, 0.114])


def subject_colour(path):
    """White-balanced median colour of the product in the frame."""
    with Image.open(path) as im:
        a = np.asarray(im.convert("RGB").resize((220, 220))).astype(float)

    edge = np.concatenate([a[:14].reshape(-1, 3), a[-14:].reshape(-1, 3),
                           a[:, :14].reshape(-1, 3), a[:, -14:].reshape(-1, 3)])
    bg = np.median(edge, 0)

    dist = np.linalg.norm(a - bg, axis=2)
    yy, xx = np.mgrid[0:220, 0:220]
    centre = np.exp(-(((yy - 115) / 85.0) ** 2 + ((xx - 110) / 85.0) ** 2))
    mask = (dist > 30) & (centre > 0.3)
    if mask.sum() < 300:                       # macro shots fill the frame
        mask = dist > max(20, np.percentile(dist, 93))

    px = a[mask]
    px = px[(px @ LUM) > np.percentile(px @ LUM, 12)]   # drop contact shadow
    med = np.median(px, 0)
    return np.clip(med / np.maximum(bg, 1) * bg.mean(), 0, 255)


def chroma(c):
    """Colour with lightness divided out, so hues compare on equal terms."""
    c = np.asarray(c, float)
    return c - c.mean()


def cluster(colours, tol=26.0):
    """Group photos of the same colourway. Returns a label per photo."""
    labels = [-1] * len(colours)
    centres = []
    for i, c in enumerate(colours):
        for k, cen in enumerate(centres):
            if np.linalg.norm(c - cen) < tol:
                members = [colours[j] for j in range(i) if labels[j] == k] + [c]
                centres[k] = np.mean(members, 0)
                labels[i] = k
                break
        else:
            centres.append(np.asarray(c, float))
            labels[i] = len(centres) - 1
    return labels, centres


def _unit(values):
    """Map values onto 0..1 within their own set."""
    values = np.asarray(values, float)
    lo, hi = values.min(), values.max()
    return np.full_like(values, 0.5) if hi - lo < 1e-6 else (values - lo) / (hi - lo)


def assign(centres, names):
    """Match each cluster to a catalogue colour, by rank first then hue."""
    if not names:
        return [None] * len(centres)
    refs = [np.array(SWATCH.get(n.lower(), (150, 150, 150)), float) for n in names]
    cl = _unit([c @ LUM for c in centres])
    rl = _unit([r @ LUM for r in refs])

    # Rank is only worth trusting when the colours are actually spread out in
    # lightness. Black/Grey/White span 237 levels and rank decides; Neto's grey
    # and terracotta are 11 apart, where rank is noise and hue must decide.
    spread = max(r @ LUM for r in refs) - min(r @ LUM for r in refs)
    w_lum = min(spread / 120.0, 1.0)

    def cost(ci, ri):
        return (w_lum * abs(cl[ci] - rl[ri])
                + 0.02 * np.linalg.norm(chroma(centres[ci]) - chroma(refs[ri])))

    n_c, n_r = len(centres), len(names)
    if n_c <= n_r:                    # each cluster gets its own colour
        best, score = None, float("inf")
        for perm in permutations(range(n_r), n_c):
            s = sum(cost(i, perm[i]) for i in range(n_c))
            if s < score:
                best, score = perm, s
        return [names[i] for i in best]
    # more clusters than colours: nearest colour, reuse allowed
    return [names[min(range(n_r), key=lambda ri: cost(ci, ri))]
            for ci in range(n_c)]


def colours_for(product, products_dir):
    """{filename: colour name} for one catalogue entry."""
    names = [c["name"] for c in product.get("colors", [])]
    files = product.get("images", [])
    if not files or not names:
        return {}
    cols = [subject_colour(Path(products_dir) / product["slug"] / f) for f in files]
    labels, centres = cluster(cols)
    per_cluster = assign(centres, names)
    return {f: per_cluster[labels[i]] for i, f in enumerate(files)}


def main():
    repo = Path(__file__).resolve().parent.parent
    catalog_js = repo / "site" / "data" / "catalog.js"
    text = catalog_js.read_text()
    catalog = json.loads(text[text.index("["):text.rindex(";")])
    products_dir = repo / "site" / "assets" / "products"

    for p in catalog:
        mapping = colours_for(p, products_dir)
        if mapping:
            print(f"{p['slug']:22s} " +
                  "  ".join(f"{f[:2]}={c}" for f, c in mapping.items()))


if __name__ == "__main__":
    main()
