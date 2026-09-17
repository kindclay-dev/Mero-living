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
| Body copy, labels, quantity | Outfit | regular 400 | as set |

Buttons deliberately share the nav's voice — regular at 10% — so the chrome
reads as one system.

Earlier revisions set the body in Jost as a Futura stand-in, calibrated so the
DETAILS copy broke line-for-line with the original design PDF. Outfit is
narrower, so those line breaks and the ~3px landmark match no longer hold; the
layout geometry (columns, gallery, spacing) is unchanged.

## Catalogue fields

Each entry in `catalog.js` carries `slug, title, price, priceRange, sku,
colors[{name,hex}], sizes, category, details, images[]` and a `lockup` flag.
`lockup` is opt-in (`LOCKUP_SLUGS` in the build script) — it draws the
name/`series` type over the opening shot, which only suits products
photographed with room for it.

Categories come from the feed's tags: the furniture is tagged `home`,
everything else is a planter. Lighting and Decor exist in the nav with no
stock behind them yet and show an empty state.
