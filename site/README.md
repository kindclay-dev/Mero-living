# MERO storefront

Two pages sharing one design system and one generated catalogue.

```
site/
├── index.html          grid of every product, with the folder drop
├── product.html        a product page, chosen by ?p=<slug>
├── data/catalog.js     generated — window.MERO_CATALOG
└── assets/
    ├── site.css        the whole design system, both pages
    ├── uploads.js      photos added in the browser (IndexedDB)
    ├── products/<slug>/NN.jpg
    ├── fonts/          Jost and Cormorant Garamond
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
python3 scraper/build_site.py                      # feed + output/product_photos.zip
python3 scraper/build_site.py --photos ~/new-shoot # a folder of product sub-folders
python3 scraper/build_site.py --skip-images        # metadata only, leave photos alone
```

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
product's gallery, ahead of the bulk set. That's how Mavi keeps the styled
hero shots its page was designed around.

## Adding photos from the browser

The grid page takes a whole folder — via **Choose folder** or by dropping it —
splits it by sub-folder and files each set against the matching product.
Photos are held in IndexedDB, so they survive navigation and reloads and show
up on the product pages too. Nothing is uploaded anywhere. **Clear uploads**
removes them. The product page's **Add photo** does the same for one product.

This is for previewing real photography before it's wired to a backend; to
make photos permanent, put them in `photos/<slug>/` and rebuild.

## Type

Futura is the storefront's face. The pages ask for Futura first and fall back
to **Jost**, the closest open-source match, bundled as woff2 so the design
holds without Futura installed and without a Google Fonts request. The italic
`series` in the Mavi lockup is **Cormorant Garamond**.

Sizes and tracking were calibrated against the original design PDF: every
landmark lands within ~3px at a 1440px viewport, and the justified DETAILS
copy breaks on the same words.

## Catalogue fields

Each entry in `catalog.js` carries `slug, title, price, priceRange, sku,
colors[{name,hex}], sizes, category, details, images[]` and a `lockup` flag.
`lockup` is opt-in (`LOCKUP_SLUGS` in the build script) — it draws the
name/`series` type over the opening shot, which only suits products
photographed with room for it.

Categories come from the feed's tags: the furniture is tagged `home`,
everything else is a planter. Lighting and Decor exist in the nav with no
stock behind them yet and show an empty state.
