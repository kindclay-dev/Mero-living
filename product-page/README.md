# Mavi Series — product page

A recreation of the MERO "Mavi Series" product page as a standalone HTML page.

```
product-page/
├── index.html      the page (markup, styles and gallery script inline)
└── assets/
    ├── *.jpg       product photography
    ├── *.png       MERO wordmark, HBL and Bank Alfalah lockups
    └── fonts/      Jost and Cormorant Garamond (self-hosted woff2)
```

Open `index.html` in a browser, or serve the folder:

```bash
python3 -m http.server -d product-page 8000
```

## Type

The storefront sets its UI in **Futura**. The page asks for Futura first and falls
back to **Jost**, the closest open-source match, which is bundled so the page
renders identically without Futura installed and without a call to Google Fonts.
The italic `series` in the hero lockup is **Cormorant Garamond**.

Sizes and tracking were calibrated against the source design: each landmark
(nav, title, price, swatches, buy row, body copy, gallery) lands within ~3px of
the original at a 1440px viewport, and the justified DETAILS copy breaks on the
same words, line for line.

## Gallery

`PRODUCTS` at the top of the script is the page's data — title, price, SKU,
colours, copy and photos. Everything on the page renders from it.

- The stage cycles a product's photos every `SLIDE_MS`, then switches to the
  next entry in `PRODUCTS` and starts over.
- Autoplay is on by default (`AUTOPLAY`), pauses while the pointer is over the
  stage, respects `prefers-reduced-motion`, and stops for good once a visitor
  uses the arrows, the thumbnails or the arrow keys.
- The `MAVI / series` lockup belongs to each product's opening shot and fades
  out on the others.
- **Add photo** puts local images into the current product's gallery. They are
  held as object URLs for the session only — nothing is uploaded — so they are
  there to preview real photography before it is wired to a backend.

To add products, append to `PRODUCTS`; the rail, swatches, copy and lockup all
follow. Nothing else needs to change.
