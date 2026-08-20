#!/usr/bin/env python3
"""Scrape all products from https://meroliving.com/products/ (a Shopify store).

Uses the store's public products.json endpoint rather than parsing HTML,
since the /products/ page itself only lists collections and the actual
product grids are loaded client-side. Shopify exposes each product's full
catalog data (title, images, price, variants) at /products.json.

Usage:
    python3 scrape_products.py [--out-dir output] [--base-url https://meroliving.com]
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
PAGE_SIZE = 250  # Shopify's max allowed limit for /products.json


def fetch_all_products(base_url: str, session: requests.Session) -> list[dict]:
    products: list[dict] = []
    page = 1
    while True:
        resp = session.get(
            urljoin(base_url, "/products.json"),
            params={"limit": PAGE_SIZE, "page": page},
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json().get("products", [])
        if not batch:
            break
        products.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        page += 1
        time.sleep(0.5)  # be polite
    return products


def extract_color_variations(product: dict) -> list[str]:
    """Return the distinct color option values for a product, if it has one."""
    color_option_index = None
    for i, option in enumerate(product.get("options", [])):
        if option.get("name", "").strip().lower() == "color":
            color_option_index = i
            break
    if color_option_index is None:
        return []

    option_key = f"option{color_option_index + 1}"
    seen: list[str] = []
    for variant in product.get("variants", []):
        value = variant.get(option_key)
        if value and value not in seen:
            seen.append(value)
    return seen


def main_image_url(base_url: str, product: dict) -> str | None:
    images = product.get("images", [])
    if not images:
        return None
    src = images[0].get("src")
    if not src:
        return None
    return urljoin(base_url, src) if src.startswith("/") else src


def price_range(product: dict) -> str:
    prices = [v.get("price") for v in product.get("variants", []) if v.get("price")]
    if not prices:
        return ""
    prices = sorted(set(prices), key=float)
    if len(prices) == 1:
        return prices[0]
    return f"{prices[0]}–{prices[-1]}"


def build_rows(base_url: str, products: list[dict]) -> list[dict]:
    rows = []
    for product in products:
        rows.append(
            {
                "name": product.get("title", ""),
                "url": urljoin(base_url, f"/products/{product.get('handle', '')}"),
                "image": main_image_url(base_url, product),
                "colors": extract_color_variations(product),
                "price_range": price_range(product),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://meroliving.com")
    parser.add_argument("--out-dir", default="output")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    products = fetch_all_products(args.base_url, session)
    rows = build_rows(args.base_url, products)

    json_path = out_dir / "products.json"
    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False))

    csv_path = out_dir / "products.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Image URL", "Colors", "Price Range (PKR)", "Product URL"])
        for row in rows:
            writer.writerow(
                [
                    row["name"],
                    row["image"] or "",
                    ", ".join(row["colors"]),
                    row["price_range"],
                    row["url"],
                ]
            )

    print(f"Scraped {len(rows)} products.")
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
