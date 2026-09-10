# Mero Living Product Scraper

Scrapes [meroliving.com/products/](https://meroliving.com/products/) for the full
catalog: product name, one photo, price range, and colour variations.

The `/products/` page itself only lists collections — the actual product grids
are rendered client-side — so the scraper pulls from Shopify's public
`/products.json` feed instead, which returns complete structured data (title,
images, price, variants) for every product in the store.

## Usage

```bash
pip install -r requirements.txt
python3 scraper/scrape_products.py
```

Writes `output/products.json` and `output/products.csv`.

Options:

```bash
python3 scraper/scrape_products.py --base-url https://meroliving.com --out-dir output
```

## Output

Each row/record has:

- `name` — product title
- `image` — one representative photo URL
- `colors` — list of distinct colour variants (empty if the product has no colour option)
- `price_range` — lowest–highest variant price
- `url` — product page link

---

# Scale Reference Image Generator

Turns a planter's real-world width and height into a standardized black-and-white
scale reference image. The reference PNG goes to the image model alongside the
product prompt so the generated photo renders the planter at an accurate size,
both against the scene and against every other planter in the catalogue.

## How it works

Every reference image is a 2048x2048 white canvas with one solid black rectangle:
horizontally centered, bottom edge anchored to a fixed ground line at 85% down
the canvas. The rectangle's pixel size comes from a single pixels-per-inch
constant shared by the whole catalogue:

```
PPI = (CANVAS_SIZE * MAX_SHAPE_FRACTION) / REFERENCE_MAX_INCHES
    = (2048 * 0.75) / 40
    = 38.4 px per inch

rect_width_px  = width_in  * PPI
rect_height_px = height_in * PPI
```

Because the constant never changes per planter, the ratio between any two
reference images is exactly the ratio between the two real planters. Absolute
scale is tuned by changing one number, not by eyeballing each generation.

The three calibration constants live at the top of
`scaleref/generate_scale_refs.py` and can be overridden per run:

| Constant | Default | What it controls |
| --- | --- | --- |
| `REFERENCE_MAX_INCHES` | 40 | Largest dimension the system is calibrated for |
| `MAX_SHAPE_FRACTION` | 0.75 | Share of canvas width that largest item occupies |
| `GROUND_LINE_FRACTION` | 0.85 | Where the floor sits, measured from the top |

## Usage

```bash
pip install -r requirements.txt

# whole catalogue
python3 scaleref/generate_scale_refs.py --csv data/catalogue.csv

# one item
python3 scaleref/generate_scale_refs.py --sku tura-large --width 27 --height 26

# recalibrate without touching the source
python3 scaleref/generate_scale_refs.py --csv data/catalogue.csv \
    --reference-max 45 --ground-line 0.80
```

PNGs land in `output/scalerefs/`, named `<sku>-scaleref.png`, alongside a
`manifest.csv` recording the computed pixel size and position of every rectangle
so the math can be checked by direct measurement.

## Input data

`data/catalogue.csv` carries one row per item with `sku`, `name`, `width_in`,
`height_in` and free-text `notes`. Width is the widest horizontal span as seen
from the front, so for round planters that is the larger of the top and bottom
diameters.

Three items from the product list are not in it:

- **Mukul S** has no published dimensions.
- **Deco Chair 2-Seater (65 in)** and **3-Seater (84 in)** exceed the 40 inch
  reference span. Including them means raising `REFERENCE_MAX_INCHES`, which
  shrinks every planter's rectangle in proportion. The tool warns and still
  renders if you pass an oversize item, but the rectangle will be clipped.

Two rows carry judgement calls worth confirming: **Soho S (Textured)** is listed
as 6 in L and 16 in 1H, read here as 16x16x16 to match plain Soho S; and
**Flora with Stand** uses the 24 in total height including the stand.

## Still to confirm

The core hypothesis is untested: it is not yet known whether the image model
treats a secondary reference image as a literal size cue or a loose composition
hint. Test on two or three SKUs before relying on the full set. If generated
photos do not place the floor around 85% down the frame, adjust
`GROUND_LINE_FRACTION` and regenerate.
