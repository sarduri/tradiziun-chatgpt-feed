#!/usr/bin/env python3
"""Konvertiert den öffentlichen Shopify-Feed (/products.json) ins OpenAI-Produktfeed-Format (JSONL).

Spezifikation: https://developers.openai.com/commerce/specs/file-upload/products

Beispiel:
    python3 tools/chatgpt_feed.py --base-url https://www.example.ch -o feed.jsonl.gz   # .gz -> gzip-komprimiert (vom Business Hub verlangt)

--base-url ist die öffentliche Shop-Domain (für die Produkt-URLs im Feed).
--source   ist die Domain, von der products.json gelesen wird (Standard: --base-url).
Nur Python-Standardbibliothek.
"""
import argparse
import gzip
import html
import json
import re
import sys
import time
import urllib.request

UA = "tradiziun-chatgpt-feed/1.0"


def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    return None


def fetch_all_products(source):
    page, out = 1, []
    while True:
        data = fetch_json(f"{source}/products.json?limit=250&page={page}")
        products = data.get("products", [])
        if not products:
            return out
        out.extend(products)
        page += 1


def plain_text(body_html, limit=5000):
    text = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h[1-6]>", "\n", body_html or "")
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return text[:limit]


def money(value, currency):
    return f"{float(value):.2f} {currency}"


def build_rows(products, args):
    base = args.base_url.rstrip("/")
    rows, skipped = [], 0
    for p in products:
        variants = p.get("variants", [])
        images = p.get("images", [])
        if not images:
            skipped += len(variants)
            continue
        option_names = [o["name"] for o in p.get("options", [])]
        multi = not (len(variants) == 1 and variants[0].get("title") == "Default Title")
        by_id = {img["id"]: img["src"] for img in images}
        description = plain_text(p.get("body_html")) or p["title"]
        for v in variants:
            price = float(v["price"])
            if price <= 0:
                skipped += 1
                continue
            vimg = v.get("featured_image") or {}
            image_url = vimg.get("src") or by_id.get(vimg.get("id")) or images[0]["src"]
            others = [i["src"] for i in images if i["src"] != image_url][:9]
            url = f"{base}/products/{p['handle']}"
            title = p["title"]
            if multi:
                url += f"?variant={v['id']}"
                opts = [v.get(f"option{i + 1}") for i in range(len(option_names))]
                title = f"{title} - {' / '.join(o for o in opts if o)}"[:150]
            row = {
                "item_id": str(v["id"]),
                "title": title[:150],
                "description": description,
                "url": url,
                "brand": p.get("vendor") or args.seller_name,
                "seller_name": args.seller_name,
                "image_url": image_url,
                "availability": "in_stock" if v.get("available") else "out_of_stock",
                "price": money(price, args.currency),
                "target_countries": args.countries,
                "store_country": args.store_country,
            }
            compare = v.get("compare_at_price")
            if compare and float(compare) > price:
                row["price"] = money(compare, args.currency)
                row["sale_price"] = money(price, args.currency)
            if others:
                row["additional_image_urls"] = others
            if p.get("product_type"):
                row["product_category"] = p["product_type"]
            if v.get("grams"):
                row["weight"] = str(v["grams"])
                row["item_weight_unit"] = "g"
            if multi:
                row["group_id"] = str(p["id"])
                row["listing_has_variations"] = True
                row["variant_dict"] = {
                    n: v.get(f"option{i + 1}")
                    for i, n in enumerate(option_names)
                    if v.get(f"option{i + 1}")
                }
            row["condition"] = "new"
            rows.append(row)
    return rows, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", required=True, help="öffentliche Shop-URL, z. B. https://www.example.ch")
    ap.add_argument("--source", help="Domain für products.json (Standard: --base-url)")
    ap.add_argument("-o", "--output", default="feed.jsonl")
    ap.add_argument("--seller-name", default="Butia Tradiziun")
    ap.add_argument("--currency", default="CHF")
    ap.add_argument("--countries", nargs="+", default=["CH"], help="target_countries (Standard-Uploads: US)")
    ap.add_argument("--store-country", default="CH")
    args = ap.parse_args()

    source = (args.source or args.base_url).rstrip("/")
    products = fetch_all_products(source)
    rows, skipped = build_rows(products, args)
    if not rows:
        sys.exit("Keine Zeilen erzeugt – Feed wird nicht geschrieben.")
    opener = gzip.open if args.output.endswith(".gz") else open
    with opener(args.output, "wt", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(products)} Produkte -> {len(rows)} Feed-Zeilen ({skipped} übersprungen: ohne Bild/Preis) -> {args.output}")


if __name__ == "__main__":
    main()
