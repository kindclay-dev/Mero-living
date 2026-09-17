# MERO storefront

Two pages sharing one design system and one generated catalogue.

```
site/
├── index.html          grid of every product
├── product.html        a product page, chosen by ?p=<slug>
├── data/catalog.js     generated — window.MERO_CATALOG
└── assets/
    ├── site.css        the whole design system, both pages
    ├── products/<slug>/NN.jpg
    ├── fonts/          Outfit and Cormorant Garamond
    └── *.png           MERO wordmark, HBL and Bank Alfalah lockups
```

Open `index.html` directly, or serve it:

```bash
python3 -m http.server -d site 8000
```

`catalog.js` is JavaScript rather than JSON so both pages also work straight
off disk — `fetch()` of a local file is blocked on `file://`.

## Rebuilding the catalogue

```bash
python3 scraper/build_site.py                      # metadata only; photos untouched
python3 scraper/build_site.py --photos ~/new-shoot # also rebuild the photos
```

A bare run refreshes `catalog.js` from the feed and leaves the built photos
alone. Rebuilding photography needs an explicit `--photos`, because the
masters live outside the repo and a bare run must not be able to overwrite
them.

The script reads product metadata from the store's `/products.json` feed and
photography from any folder (or zip) laid out one sub-folder per product:

```
new-shoot/
  mavi/01.jpg 02.jpg …
  reewa/…
```

Sub-folder names are matched to product handles, so `20-mavi` and `veeru-a`
both land correctly. Photos are resized to 1100px and written as progressive
JPEG. Anything that doesn't match a product is reported rather than dropped
silently.

`photos/` in the repo root is a curated override: whatever sits there leads a
product's gallery, ahead of whatever `--photos` supplies. It currently holds
the five Mavi shots taken from the design PDF, which the September shoot has
since superseded — so if you pass `--photos` again, Mavi will lead with those
older frames unless you clear the folder first.

Adding photography is a build step — there is no upload control on the site.
Put images in `photos/<slug>/` (or point `--photos` at a folder) and rebuild.

## Type

**Outfit** sets the whole storefront, self-hosted as a variable woff2 and
preloaded — no Google Fonts request, and the design holds offline. The only
other face is **Cormorant Garamond** italic, for the `series` in the Mavi
lockup.

The scale, with 10% tracking shared as `--track`:

| | face | weight | tracking |
|---|---|---|---|
| Nav, buttons, filters, size chips | Outfit | regular 400 | 10% |
| Product titles, catalogue heading, card names | Outfit | light 300 | 10% |
| Prices, on the page and on the cards | Outfit | medium 500 | 10% |
| SKU | Outfit 13px | medium 500 | 0% |
| DETAILS heading | Outfit | bold 700 | 3% |
| DETAILS body copy | Outfit | regular 400 | 0% |
| Other labels, quantity | Outfit | regular 400 | as set |

Buttons deliberately share the nav's voice — regular at 10% — so the chrome
reads as one system.

Earlier revisions set the body in Jost as a Futura stand-in, calibrated so the
DETAILS copy broke line-for-line with the original design PDF. Outfit is
narrower, so those line breaks and the ~3px landmark match no longer hold; the
layout geometry (columns, gallery, spacing) is unchanged.

## Gallery geometry

The stage is square, so its height follows whatever width is left after the
thumbnail rail. The rail is sized at `(gallery - gap) / 5.5` and the row gap at
a 27th of the rail height, which makes four thumbnails plus three gaps come to
exactly the stage height at any viewport — 116px on a 1440 screen, as the
design has it. A product with more photos scrolls the rail; it never shows a
part-cropped fifth.

## Cache busting

Replacement photography reuses `01.jpg`, `02.jpg` …, so a browser will happily
keep serving the previous shoot. Every photo URL therefore carries a short
content hash from `catalog.js` — `01.jpg?v=8ad29864` — which changes only when
the file does.

## Colour swatches

Clicking a swatch on a product page opens that colourway's photograph, and
stepping the gallery moves the swatch back in step.

The photos arrive unlabelled, so `scraper/detect_colors.py` works the colour
out from the pixels and the build writes it into `catalog.js` as
`imageColors` — `{"01.jpg": "White", "03.jpg": "Black", …}`.

Matching a photo to a swatch value directly does not work. The warm studio
light lifts a black planter to about 80 luminance, nowhere near `#0a0909`, and
some colourways separate only by hue — Neto's grey and terracotta are one
luminance point apart. So the detector white-balances each photo against the
wall behind it, clusters a product's photos by colour, and matches the
clusters to that product's catalogue colours by rank, darkest to darkest, with
hue breaking ties. Everything is relative to the product's own set, which is
what survives the lighting.

Blacks and the saturated colourways are reliable. Pale neutrals — white
against sand against stone — are the hard case and do get swapped
occasionally; check `python3 scraper/detect_colors.py`, which prints the
mapping, if a swatch opens the wrong frame.

A colour the shoot never covered is dimmed and leaves the stage alone when
clicked, rather than pretending to work.

## Catalogue fields

Each entry in `catalog.js` carries `slug, title, price, priceRange, sku,
colors[{name,hex}], sizes, category, details, images[]` and a `lockup` flag.
`lockup` is opt-in (`LOCKUP_SLUGS` in the build script) — it draws the
name/`series` type over the opening shot, which only suits products
photographed with room for it.

Categories come from the feed's tags: the furniture is tagged `home`,
everything else is a planter. Lighting and Decor exist in the nav with no
stock behind them yet and show an empty state.
