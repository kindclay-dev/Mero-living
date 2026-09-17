# Mero Living

A storefront built from the live meroliving.com catalogue.

- **`site/`** — the storefront: a product grid and a dynamic product page.
  See [site/README.md](site/README.md).
- **`scraper/build_site.py`** — builds `site/data/catalog.js` and the product
  photography from the feed plus a folder of photos.
- **`new-products/`** — drop new planter photography here (a zip is fine),
  then ask me to update.
- **`photos/`** — curated shots that lead a product's gallery.
- **`scraper/scrape_products.py`** — the original catalogue scrape, below.

## Product scraper

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
