#!/usr/bin/env python3
"""Build the storefront's catalogue and product photography.

Reads product metadata from Shopify's public /products.json feed and product
photography from a folder (or zip) laid out one sub-folder per product:

    photos/
      mavi/01.jpg 02.jpg ...
      reewa/...

Sub-folder names are matched to product handles, so a leading index like
``20-mavi`` works too. Writes:

    site/data/catalog.js            window.MERO_CATALOG = [...]
    site/assets/products/<slug>/NN.jpg

catalog.js is JavaScript rather than JSON on purpose: the pages then work
when opened straight off disk, where fetch() of a local file is blocked.

Without --photos it refreshes catalog.js from the feed and leaves the built
photos alone; pass --photos to rebuild them from a source.

Usage:
    python3 scraper/build_site.py                          # metadata only
    python3 scraper/build_site.py --photos ~/new-shoot     # and the photos
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: pip install -r requirements.txt")

DEFAULT_FEED = "https://meroliving.com/products.json?limit=250"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

# Swatch colours for the option values the store actually uses.
COLOR_HEX = {
    "black": "#0a0909",
    "white": "#f7f7f7",
    "grey": "#828282",
    "gray": "#828282",
    "ash grey": "#9a9a9a",
    "sand": "#d8c9b4",
    "stone": "#b8b0a4",
    "concrete": "#a6a6a2",
    "terracotta": "#b5623f",
    "orange": "#d2762f",
    "sky blue": "#a8c4d6",
}
LIGHT_SWATCHES = {"white", "sand", "stone", "concrete", "sky blue"}

# The store is planters plus a handful of furniture pieces. The feed carries no
# product_type, but the furniture is tagged 'home' — matching on words like
# "table" would wrongly sweep in the Varsha table-top planter and Flora's stand.
FURNITURE_TAG = "home"

# Photo folders whose name cannot be reached from the product handle by
# slugifying and prefix-matching alone.
FOLDER_ALIASES = {
    "earthern": "earthen-collection",   # misspelt "Earthen"
}

# Products whose opening shot is a styled hero, so the name/"series" lockup
# sits over it the way the Mavi design does. Add a slug here once a product
# has photography with room for type.
LOCKUP_SLUGS = {"mavi"}


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def folder_slug(name):
    """'20-mavi' -> 'mavi', 'Mavi Series' -> 'mavi-series'."""
    return slugify(re.sub(r"^\d+[-_\s]*", "", name))


def strip_html(html):
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html or "", flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>|</p>|</li>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&#39;", "'").replace("&quot;", '"')
                .replace("&lt;", "<").replace("&gt;", ">"))
    return re.sub(r"\s+", " ", text).strip()


def load_feed(source):
    if re.match(r"^https?://", str(source)):
        with urllib.request.urlopen(source, timeout=60) as r:
            data = json.load(r)
    else:
        data = json.loads(Path(source).read_text())
    return data["products"]


def money(value):
    return f"PKR {int(round(float(value))):,}"


def categorise(product):
    tags = [t.lower() for t in (product.get("tags") or [])]
    return "furniture" if FURNITURE_TAG in tags else "outdoor"


def build_product(product):
    variants = product.get("variants") or []
    prices = sorted(float(v["price"]) for v in variants if v.get("price"))
    option_names = [o["name"].lower() for o in product.get("options", [])]

    colors = []
    sizes = []
    for option in product.get("options", []):
        name = option["name"].lower()
        if name in ("color", "colour"):
            for value in option["values"]:
                key = value.lower()
                colors.append({
                    "name": value,
                    "hex": COLOR_HEX.get(key, "#b9b3ab"),
                    **({"tone": "light"} if key in LIGHT_SWATCHES else {}),
                })
        elif name == "size":
            sizes = list(option["values"])

    sku = next((v["sku"] for v in variants if v.get("sku")), "")

    return {
        "slug": product["handle"],
        "title": product["title"].strip(),
        "captionName": product["title"].split("(")[0].split("-")[0].strip(),
        "captionSub": "series",
        "lockup": product["handle"] in LOCKUP_SLUGS,
        "price": prices[0] if prices else 0,
        "priceLabel": money(prices[0]) if prices else "",
        "priceRange": (money(prices[0]) if len(set(prices)) <= 1
                       else f"{money(prices[0])} – {money(prices[-1])}"),
        "sku": sku,
        "colors": colors,
        "sizes": sizes,
        "category": categorise(product),
        "details": strip_html(product.get("body_html")),
        "url": f"product.html?p={product['handle']}",
        "images": [],
        "hasOptions": bool(option_names and option_names != ["title"]),
    }


def photo_dirs(source, workdir):
    """Yield (folder_name, [image paths]) from a directory or a zip archive."""
    source = Path(source)
    if source.is_file() and source.suffix.lower() == ".zip":
        extracted = workdir / "photos"
        with zipfile.ZipFile(source) as z:
            z.extractall(extracted)
        source = extracted
    if not source.is_dir():
        sys.exit(f"Photo source not found: {source}")

    # Allow either photos/<product>/*.jpg or a single nested wrapper folder.
    roots = [source]
    children = [p for p in source.iterdir() if p.is_dir()]
    if len(children) == 1 and not any(
            p.suffix.lower() in IMAGE_SUFFIXES for p in source.iterdir() if p.is_file()):
        grandkids = [p for p in children[0].iterdir() if p.is_dir()]
        if grandkids:
            roots = [children[0]]

    for root in roots:
        for folder in sorted(p for p in root.iterdir() if p.is_dir()):
            images = sorted(p for p in folder.rglob("*")
                            if p.suffix.lower() in IMAGE_SUFFIXES)
            if images:
                yield folder.name, images


def match_product(name, by_slug):
    """Map a photo folder name onto a product slug, tolerating drift."""
    slug = folder_slug(name)
    if slug in by_slug:
        return slug
    alias = FOLDER_ALIASES.get(slug)
    if alias in by_slug:
        return alias
    # 'veeru-a' -> 'veeru'; also handles '<slug>-photos', '<slug>-final' etc.
    candidates = [s for s in by_slug if slug.startswith(s) or s.startswith(slug)]
    if candidates:
        return max(candidates, key=len)
    return None


def write_images(images, out_dir, max_width, quality):
    out_dir.mkdir(parents=True, exist_ok=True)
    for existing in out_dir.glob("*.jpg"):
        existing.unlink()
    written = []
    for index, src in enumerate(images, start=1):
        with Image.open(src) as im:
            if im.mode in ("RGBA", "LA") or (im.mode == "P"
                                             and "transparency" in im.info):
                # the studio shots carry an alpha channel; a plain convert()
                # composites it onto black, so lay them on white instead
                rgba = im.convert("RGBA")
                flat = Image.new("RGB", rgba.size, (255, 255, 255))
                flat.paste(rgba, mask=rgba.getchannel("A"))
                im = flat
            else:
                im = im.convert("RGB")
            if max(im.size) > max_width:
                im.thumbnail((max_width, max_width), Image.LANCZOS)
            name = f"{index:02d}.jpg"
            im.save(out_dir / name, "JPEG", quality=quality, optimize=True,
                    progressive=True)
            written.append(name)
    return written


def main():
    repo = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feed", default=DEFAULT_FEED,
                    help="products.json URL or local path")
    ap.add_argument("--photos", default=None,
                    help="folder or zip with one sub-folder per product. "
                         "Omit it and the photos already built stay as they "
                         "are — the masters live outside the repo, so a bare "
                         "run must not be able to overwrite them.")
    ap.add_argument("--extra-photos", default=str(repo / "photos"),
                    help="curated photos that lead the gallery, same layout; "
                         "drop a folder here to override the scraped set")
    ap.add_argument("--out", default=str(repo / "site"), help="site directory")
    ap.add_argument("--max-width", type=int, default=1100)
    ap.add_argument("--quality", type=int, default=88)
    ap.add_argument("--skip-images", action="store_true",
                    help="rebuild catalog.js only, leaving existing photos alone")
    args = ap.parse_args()

    out = Path(args.out)
    products_dir = out / "assets" / "products"

    print(f"Reading feed: {args.feed}")
    products = [build_product(p) for p in load_feed(args.feed)]
    by_slug = {p["slug"]: p for p in products}
    print(f"  {len(products)} products")

    if args.skip_images or not args.photos:
        for product in products:
            folder = products_dir / product["slug"]
            product["images"] = sorted(p.name for p in folder.glob("*.jpg")) \
                if folder.is_dir() else []
    else:
        with tempfile.TemporaryDirectory() as tmp:
            # Curated shots lead each gallery; the bulk set follows.
            collected = {}
            unmatched = []
            sources = [(args.extra_photos, True), (args.photos, False)]
            for source, is_curated in sources:
                if not source or not Path(source).exists():
                    if is_curated:
                        continue
                    sys.exit(f"Photo source not found: {source}")
                print(f"Reading photos: {source}")
                for name, images in photo_dirs(source, Path(tmp) / str(is_curated)):
                    slug = match_product(name, by_slug)
                    if not slug:
                        unmatched.append(name)
                        continue
                    lead, rest = collected.setdefault(slug, ([], []))
                    (lead if is_curated else rest).extend(images)

            for slug, (lead, rest) in collected.items():
                written = write_images(lead + rest, products_dir / slug,
                                       args.max_width, args.quality)
                by_slug[slug]["images"] = written
                mark = " (curated)" if lead else ""
                print(f"  {slug:28s} {len(written)} photos{mark}")
            if unmatched:
                print(f"  ! no product matched: {', '.join(sorted(set(unmatched)))}")

    # a product the photo source says nothing about keeps the gallery it has
    for product in products:
        if product["images"]:
            continue
        folder = products_dir / product["slug"]
        if folder.is_dir():
            product["images"] = sorted(f.name for f in folder.glob("*.jpg"))
            if product["images"]:
                print(f"  {product['slug']:28s} {len(product['images'])} photos (kept)")

    empty = [p["slug"] for p in products if not p["images"]]
    if empty:
        print(f"  ! no photos for: {', '.join(empty)}")

    # Products with photography first, so the grid never opens on a gap.
    products.sort(key=lambda p: (not p["images"], p["title"].lower()))

    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(products, indent=2, ensure_ascii=False)
    (data_dir / "catalog.js").write_text(
        "/* Generated by scraper/build_site.py — do not edit by hand. */\n"
        f"window.MERO_CATALOG = {payload};\n", encoding="utf-8")

    total = sum(len(p["images"]) for p in products)
    size = sum(f.stat().st_size for f in products_dir.rglob("*.jpg")) / 1e6 \
        if products_dir.is_dir() else 0
    print(f"\nWrote {data_dir / 'catalog.js'}")
    print(f"  {len(products)} products, {total} photos, {size:.1f} MB")


if __name__ == "__main__":
    main()
