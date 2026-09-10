#!/usr/bin/env python3
"""Generate black-and-white scale reference images for Mero Living planters.

Each output is a square white canvas carrying one solid black rectangle whose
pixel size encodes the planter's real-world width and height. Every planter is
converted with the same pixels-per-inch constant, so the ratio between any two
reference images matches the ratio between the two real planters exactly.

Usage:
    python3 scaleref/generate_scale_refs.py --csv data/catalogue.csv
    python3 scaleref/generate_scale_refs.py --sku tura-large --width 27 --height 26
"""

import argparse
import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# --- Calibration constants -------------------------------------------------
# These are the only numbers that decide scale. Change them here, never per
# planter, or the relative sizing across the catalogue stops being consistent.

CANVAS_SIZE = 2048          # px, square, matches the product photo standard
BACKGROUND = (255, 255, 255)
FOREGROUND = (0, 0, 0)

# Largest real-world dimension the system is calibrated for, in inches. The
# widest catalogue item is Veeru B at 33.9 in, so 40 leaves headroom for
# planned sizes. Raising this shrinks every rectangle proportionally.
REFERENCE_MAX_INCHES = 40.0

# Fraction of the canvas width the largest planter should occupy.
MAX_SHAPE_FRACTION = 0.75

# Where the floor sits, as a fraction of canvas height measured from the top.
# The rectangle's bottom edge is anchored here in every image.
GROUND_LINE_FRACTION = 0.85


def pixels_per_inch(
    canvas_size=CANVAS_SIZE,
    max_fraction=MAX_SHAPE_FRACTION,
    reference_max_inches=REFERENCE_MAX_INCHES,
):
    """One conversion constant, applied to every planter without exception."""
    return (canvas_size * max_fraction) / reference_max_inches


def rectangle_box(width_in, height_in, canvas_size, ppi, ground_line_fraction):
    """Return the rectangle as (left, top, right, bottom) in integer pixels.

    Horizontally centered, bottom-anchored to the ground line.
    """
    # Round the dimensions first, then place them, so equal inches always come
    # out as equal pixels rather than differing by one from independent rounding.
    rect_w = round(width_in * ppi)
    rect_h = round(height_in * ppi)

    left = round((canvas_size - rect_w) / 2)
    bottom = round(canvas_size * ground_line_fraction)
    top = bottom - rect_h

    return (left, top, left + rect_w, bottom)


def render(box, canvas_size=CANVAS_SIZE):
    """Draw the rectangle on a white canvas. No anti-aliasing, crisp edges."""
    image = Image.new("RGB", (canvas_size, canvas_size), BACKGROUND)
    draw = ImageDraw.Draw(image)
    # PIL's rectangle includes both bounds, so pull the far edges in by one px
    # to keep the drawn size equal to the computed size.
    left, top, right, bottom = box
    draw.rectangle((left, top, right - 1, bottom - 1), fill=FOREGROUND)
    return image


def warn_out_of_range(sku, width_in, height_in, reference_max_inches):
    """Flag dimensions the calibration cannot represent inside the canvas."""
    largest = max(width_in, height_in)
    if largest > reference_max_inches:
        print(
            f"  warning: {sku} is {largest} in, beyond the "
            f"{reference_max_inches} in reference span. The rectangle will be "
            f"clipped by the canvas. Raise --reference-max to include it.",
            file=sys.stderr,
        )


def generate_one(sku, width_in, height_in, out_dir, ppi, canvas_size,
                 ground_line_fraction, reference_max_inches):
    warn_out_of_range(sku, width_in, height_in, reference_max_inches)
    box = rectangle_box(width_in, height_in, canvas_size, ppi, ground_line_fraction)
    out_path = Path(out_dir) / f"{sku}-scaleref.png"
    render(box, canvas_size).save(out_path, "PNG")

    left, top, right, bottom = box
    return {
        "sku": sku,
        "width_in": width_in,
        "height_in": height_in,
        "rect_width_px": right - left,
        "rect_height_px": bottom - top,
        "x": left,
        "y_top": top,
        "file": out_path.name,
    }


def read_catalogue(csv_path):
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            sku = (row.get("sku") or row.get("name") or "").strip()
            width = row.get("width_in", "").strip()
            height = row.get("height_in", "").strip()
            if not sku or not width or not height:
                print(f"  skipping row with missing data: {row}", file=sys.stderr)
                continue
            rows.append((sku, float(width), float(height)))
    return rows


def write_manifest(records, path):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", help="catalogue CSV with sku, width_in, height_in columns")
    parser.add_argument("--sku", help="single item: output name")
    parser.add_argument("--width", type=float, help="single item: width in inches")
    parser.add_argument("--height", type=float, help="single item: height in inches")
    parser.add_argument("--out-dir", default="output/scalerefs", help="where to write PNGs")
    parser.add_argument("--canvas", type=int, default=CANVAS_SIZE)
    parser.add_argument("--reference-max", type=float, default=REFERENCE_MAX_INCHES)
    parser.add_argument("--max-fraction", type=float, default=MAX_SHAPE_FRACTION)
    parser.add_argument("--ground-line", type=float, default=GROUND_LINE_FRACTION)
    args = parser.parse_args()

    single = args.sku and args.width and args.height
    if not args.csv and not single:
        parser.error("pass --csv, or all three of --sku, --width and --height")

    ppi = pixels_per_inch(args.canvas, args.max_fraction, args.reference_max)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"canvas {args.canvas}px, reference max {args.reference_max} in, "
          f"shape fraction {args.max_fraction}, ground line {args.ground_line}")
    print(f"pixels per inch: {ppi:.4f}")

    items = [(args.sku, args.width, args.height)] if single else read_catalogue(args.csv)

    records = []
    for sku, width_in, height_in in items:
        records.append(
            generate_one(sku, width_in, height_in, out_dir, ppi, args.canvas,
                         args.ground_line, args.reference_max)
        )

    if records:
        manifest = out_dir / "manifest.csv"
        write_manifest(records, manifest)
        print(f"wrote {len(records)} image(s) to {out_dir}/ and {manifest}")


if __name__ == "__main__":
    main()
