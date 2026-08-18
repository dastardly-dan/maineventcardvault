#!/usr/bin/env python3
"""
Main Event Card Vault — data builder.

Reads build/raw_listings.tsv (scraped from eBay Seller Hub) and writes:
  data/listings.json   -- machine-readable feed
  data/listings.js     -- same data as a JS global, so the site works from file://

Refresh flow:
  1. Re-scrape active listings (see README "Refreshing the inventory").
  2. Overwrite build/raw_listings.tsv.
  3. python3 build/build_site.py
"""

import csv
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "build" / "raw_listings.tsv"
OUT_JSON = ROOT / "data" / "listings.json"
OUT_JS = ROOT / "data" / "listings.js"

STORE_URL = "https://www.ebay.com/str/maineventcardvault"

# --- category detection -------------------------------------------------
WWE_WORDS = [
    "wwe", "nxt", "smackdown", "raw", "wrestlemania", "lita", "triple h",
    "rhea ripley", "liv morgan", "cody rhodes", "roxanne perez", "seth rollins",
    "jey uso", "alexa bliss", "tiffany stratton", "stephanie vaquer", "giulia",
    "jacob fatu", "joe hendry", "damian priest", "aleister black", "kendal grey",
    "ciampa", "gargano", "irs", "royalty",
]
MARVEL_WORDS = ["marvel", "moon knight", "wolverine", "spider-man", "x-men"]
BASKETBALL_WORDS = [
    "mavericks", "nba", "lakers", "celtics", "cooper flagg", "clutch gene",
    "inception", "cactus jack",
]
FOOTBALL_WORDS = ["chiefs", "nfl", "xavier worthy", "resurgence", "49ers", "cowboys"]
BASEBALL_WORDS = [
    "mlb", "brewers", "braves", "pirates", "red sox", "angels", "imanaga",
    "zach neto", "misiorowski", "acuna", "roman anthony", "konnor griffin",
    "stadium club", "tribute", "topps now",
]

CATEGORY_RULES = [
    ("Marvel", MARVEL_WORDS),
    ("WWE", WWE_WORDS),
    ("Basketball", BASKETBALL_WORDS),
    ("Football", FOOTBALL_WORDS),
    ("Baseball", BASEBALL_WORDS),
]


def categorize(title: str) -> str:
    low = title.lower()
    for name, words in CATEGORY_RULES:
        if any(w in low for w in words):
            return name
    return "Other"


# --- attribute detection ------------------------------------------------
SERIAL_RE = re.compile(r"(?:\b(\d{2,3})[/](\d{1,4})\b)|(?:\s/(\d{1,4})\b)")


def serial_of(title: str):
    """Return the print-run denominator, e.g. '/10', if the title carries one."""
    m = SERIAL_RE.search(title)
    if not m:
        return None
    den = m.group(2) or m.group(3)
    return f"/{den}" if den else None


def tags_of(title: str):
    low = title.lower()
    out = []
    if re.search(r"\bauto(graph|graphed)?\b", low):
        out.append("Autograph")
    if serial_of(title):
        out.append("Numbered")
    if re.search(r"\brc\b|\brookie\b", low):
        out.append("Rookie")
    if "relic" in low:
        out.append("Relic")
    if "ssp" in low or "case hit" in low:
        out.append("SSP")
    if "refractor" in low:
        out.append("Refractor")
    return out


def year_of(title: str):
    m = re.match(r"\s*(\d{4}(?:-\d{2})?)", title)
    return m.group(1) if m else None


def brand_of(title: str):
    low = title.lower()
    for b in [
        "topps cosmic chrome", "topps chrome update", "topps chrome",
        "topps stadium club", "topps inception", "topps resurgence",
        "topps tribute", "topps universe", "topps royalty", "topps now",
        "topps marvel", "topps",
    ]:
        if b in low:
            return b.title().replace("Topps Now", "Topps NOW")
    return "Other"


def bundle(data):
    """Write a single self-contained HTML file (nice for previewing / emailing)."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")
    js = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")

    html = html.replace(
        '<link rel="stylesheet" href="assets/style.css">',
        "<style>\n" + css + "\n</style>",
    )
    html = html.replace(
        '<script src="data/listings.js"></script>\n<script src="assets/app.js"></script>',
        "<script>window.MECV_DATA = " + json.dumps(data) + ";</script>\n"
        "<script>\n" + js + "\n</script>",
    )
    (ROOT / "main-event-card-vault.html").write_text(html, encoding="utf-8")


def build():
    rows = []
    with RAW.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            title = (r["title"] or "").strip()
            if not title:
                continue
            key = (r["imageKey"] or "").strip()
            price = float(r["price"])
            rows.append({
                "id": r["itemId"].strip(),
                "title": title,
                "price": price,
                "priceLabel": f"${price:,.2f}",
                "url": f"https://www.ebay.com/itm/{r['itemId'].strip()}",
                "image": f"https://i.ebayimg.com/images/g/{key}/s-l1600.jpg" if key else "",
                # s-l960 rather than s-l500: eBay fits the image inside the box, so a
                # portrait card at s-l500 comes back only ~280-380px wide and looks soft.
                "thumb": f"https://i.ebayimg.com/images/g/{key}/s-l960.jpg" if key else "",
                "sku": (r.get("sku") or "").strip(),
                "category": categorize(title),
                "brand": brand_of(title),
                "year": year_of(title),
                "serial": serial_of(title),
                "tags": tags_of(title),
            })

    rows.sort(key=lambda c: -c["price"])

    data = {
        "store": {
            "name": "Main Event Card Vault",
            "ebay": STORE_URL,
            "seller": "feld-111937",
            "facebook": "https://www.facebook.com/profile.php?id=61593632960504",
            "instagram": "https://www.instagram.com/main.eventcards/",
            "location": "Strasburg, Virginia",
            "shipping": "$5.99 flat, USPS Ground Advantage — $0.30 each additional card",
        },
        "updated": date.today().isoformat(),
        "count": len(rows),
        "totalValue": round(sum(c["price"] for c in rows), 2),
        "cards": rows,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    OUT_JS.write_text(
        "// Generated by build/build_site.py — do not edit by hand.\n"
        "window.MECV_DATA = " + json.dumps(data, indent=2) + ";\n",
        encoding="utf-8",
    )

    bundle(data)

    cats = {}
    for c in rows:
        cats[c["category"]] = cats.get(c["category"], 0) + 1
    print(f"{len(rows)} cards  ·  ${data['totalValue']:,.2f} total")
    for k, v in sorted(cats.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<12} {v}")


if __name__ == "__main__":
    build()
