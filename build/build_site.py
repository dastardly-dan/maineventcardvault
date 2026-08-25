#!/usr/bin/env python3
"""
Main Event Card Vault — site builder.

Inputs
  build/raw_listings.tsv   live active eBay listings (see README for the scrape)
  build/collection.tsv     cards NOT listed on eBay — owned-but-not-for-sale, and sold
  build/template.html      the page shell, with a __MECV_DATA__ placeholder

Outputs
  index.html               the deployed page (generated — never hand-edit)
  listings.json            the same feed, published for reference

Run:  python3 build/build_site.py
"""

import csv
import json
import re
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "build" / "raw_listings.tsv"
COLLECTION = ROOT / "build" / "collection.tsv"
LISTING_PHOTOS = ROOT / "build" / "listing_photos.tsv"
TEMPLATE = ROOT / "build" / "template.html"
OUT_HTML = ROOT / "index.html"
OUT_JSON = ROOT / "listings.json"

STORE_URL = "https://www.ebay.com/str/maineventcardvault"

# --- category detection -------------------------------------------------
WWE_WORDS = [
    "wwe", "nxt", "smackdown", "raw", "wrestlemania", "lita", "triple h",
    "rhea ripley", "liv morgan", "cody rhodes", "roxanne perez", "seth rollins",
    "jey uso", "alexa bliss", "tiffany stratton", "stephanie vaquer", "giulia",
    "jacob fatu", "joe hendry", "damian priest", "damien priest", "superstar auto",
    "aleister black", "kendal grey",
    "ciampa", "gargano", "irs", "royalty", "charlotte flair", "john cena",
    "rhonda rousey", "ronda rousey", "chris sabin", "cameron grimes",
    "cowboy bob orton", "channing lorenzo", "carmelo hayes", "oba femi",
    "talla tonga", "raquel rodriguez", "wrestling",
]
MARVEL_WORDS = ["marvel", "moon knight", "wolverine", "spider-man", "x-men"]
BASKETBALL_WORDS = [
    "mavericks", "nba", "lakers", "celtics", "cooper flagg", "clutch gene",
    "inception", "cactus jack", "chris paul", "gilgeous", "thunder",
    "oklahoma city", "pacers", "toni kukoc", "thomas sorber", "taelon peter",
    "tajh ariza", "todd golden",
    "knicks", "orlando magic", "ewing", "shaquille",
    # added 2026-08-25
    "jazz", "grizzlies", "wizards", "cavaliers", "spurs", "razorbacks",
    "taurasi", "ace bailey", "walker kessler", "enrique freeman",
    "ja morant", "tre johnson", "john stockton", "jr smith",
    "jordan smith", "dylan harper", "prizm break",
    # added 2026-08-25, batch 2
    "rodman", "kingston flemings",
]
FOOTBALL_WORDS = [
    "chiefs", "nfl", "xavier worthy", "resurgence", "49ers", "cowboys",
    "vikings", "tai felton", "commanders", "titans", "packers", "buccaneers",
    "tony pollard", "terry mclaurin", "tucker kraft", "tez johnson",
    # added 2026-08-25
    "ravens", "bills", "steelers", "colts", "longhorns", "ducks",
    "cam ward", "tyler loop", "jim kelly", "deion sanders", "dia bell",
    "dakorien moore", "kaleb johnson", "peyton manning", "freshman fabric",
    # added 2026-08-25, batch 2
    "patriots", "michigan", "phil mafah", "drake maye", "kalel mullings",
    "bryce underwood",
    # added 2026-08-25, batch 3
    "lions", "jared goff", "photogenic",
]
BASEBALL_WORDS = [
    "mlb", "brewers", "braves", "pirates", "red sox", "angels", "imanaga",
    "zach neto", "misiorowski", "acuna", "roman anthony", "konnor griffin",
    "stadium club", "tribute", "topps now", "yankees", "padres", "twins", "mets",
    "expos", "giants", "phillies", "orioles", "blue jays", "cubs",
    "greg maddux", "paul skenes", "anthony rizzo", "aaron judge",
    "don mattingly", "travis bazzana", "trey yesavage", "athletics",
    "tyler soderstrom", "cleveland guardians",
    # added 2026-08-21 with the _Not On Site batch
    "dodgers", "rockies", "cardinals", "rays", "diamondbacks", "astros",
    "reds", "marlins", "indians", "royals", "tigers", "white sox",
    "stars of mlb", "stadium club", "worlds finest", "bowmans best",
    "major league managers", "top prospects", "coming attraction",
    "pedro martinez", "larry walker", "trea turner", "joey votto",
    "max fried", "dylan cease", "luis severino", "christian walker",
    "kevin alcantara", "thomas saggese", "seiya suzuki", "jacob wilson",
    "moises ballesteros", "junior caminero", "jackson chourio",
    "mookie betts", "freddie freeman", "pete alonso", "luke keaschall",
    "steve carlton", "pie traynor", "nick pivetta", "merrill kelly",
    "jermaine palacios", "matt williams", "bret saberhagen", "moises alou",
    "gerald williams", "javier lopez", "tim wallach", "brad pennington",
    "chris sale", "adrian gonzalez",
    # added 2026-08-25 with the Photos-1-001 Cropped 2026-08-25 batch
    "nationals", "mariners", "rangers", "pristine", "harry ford",
    "brice turang", "paul molitor", "johnny bench", "jonah tong",
    "dwight gooden", "dave winfield", "marcus semien", "brett baty",
    "julio rodriguez", "ken griffey", "sebastian walcott", "trey sweeney",
    "baseball nation",
    # added 2026-08-25, batch 2
    "chipper jones", "prospects shortstops", "corbin carroll", "nolan arenado",
    "ezequiel tovar", "masyn winn", "kodai senga", "nolan mclean",
    "bubba chandler",
]

# Non-Marvel comics, combat sports and soccer arrived with the 2026-08-21 batch.
DC_WORDS = ["batman", "owlman", "metal universe"]
UFC_WORDS = ["ufc", "chimaev", "poirier"]
SOCCER_WORDS = [
    "pitch kings", "la liga", "celta", "el-abdellaoui",
    # added 2026-08-25
    "uefa", "leverkusen", "prized footballers", "grimaldo", "konate",
    # added 2026-08-25, batch 2
    "neymar", "nottingham", "club leon", "lewandowski", "fermin lopez",
    "valverde", "mastantuono", "igor jesus",
]
# Star Wars and hockey arrived with the 2026-08-25 batch.
STAR_WARS_WORDS = ["star wars", "kylo ren", "masterwork"]
HOCKEY_WORDS = ["nhl", "utah mammoth", "hot prospects", "daniil but"]

CATEGORY_RULES = [
    ("Marvel", MARVEL_WORDS),
    ("DC", DC_WORDS),
    ("Star Wars", STAR_WARS_WORDS),
    ("UFC", UFC_WORDS),
    ("WWE", WWE_WORDS),
    ("Basketball", BASKETBALL_WORDS),
    ("Football", FOOTBALL_WORDS),
    ("Soccer", SOCCER_WORDS),
    ("Hockey", HOCKEY_WORDS),
    ("Baseball", BASEBALL_WORDS),
]


def categorize(title: str) -> str:
    low = title.lower()
    for name, words in CATEGORY_RULES:
        if any(w in low for w in words):
            return name
    return "Other"


# --- attribute detection ------------------------------------------------
SERIAL_RE = re.compile(r"(?:\b(\d{1,3})[/](\d{1,4})\b)|(?:\s/(\d{1,4})\b)")


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
    if "relic" in low or "patch" in low:
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
        "topps marvel", "topps", "donruss optic", "donruss", "panini prizm",
        "panini", "score", "pinnacle", "upper deck", "bowman",
    ]:
        if b in low:
            return b.title().replace("Topps Now", "Topps NOW")
    return "Other"


def money(n) -> str:
    return f"${n:,.2f}"


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "card"


def listing_photo_overrides():
    """
    itemId -> stem, for active eBay listings whose photo we would rather serve
    from assets/cards than hotlink from eBay. An eBay listing photo is whatever
    was shot when the card was listed; these are the studio re-shoots. Missing
    file or missing map = fall back to the eBay image, so this can never break a
    listing that has no local photo.
    """
    out = {}
    if not LISTING_PHOTOS.exists():
        return out
    with LISTING_PHOTOS.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            iid = (r.get("itemId") or "").strip()
            stem = (r.get("stem") or "").strip()
            if not iid or not stem:
                continue
            front = f"assets/cards/{stem}_front.jpg"
            if (ROOT / front).exists():
                out[iid] = front
    return out


def back_photo(photo: str) -> str:
    """Same path with `_front` swapped for `_back`, when that file exists."""
    photo = (photo or "").strip()
    if not photo.startswith("assets/cards/") or "_front." not in photo:
        return ""
    cand = photo.replace("_front.", "_back.")
    return cand if (ROOT / cand).exists() else ""


def photo_urls(photo: str):
    """
    A collection row's `photo` field accepts three forms:
      ebay:<imageKey>    -> hotlinked from i.ebayimg.com, same as the live listings
      assets/cards/x.jpg -> a file committed to this repo
      https://...        -> any absolute URL
    Returns (fullsize, thumb).
    """
    photo = (photo or "").strip()
    if not photo:
        return "", ""
    if photo.startswith("ebay:"):
        key = photo[5:].strip()
        if not key:
            return "", ""
        base = f"https://i.ebayimg.com/images/g/{key}/"
        # s-l960 for thumbs, s-l1600 for the lightbox: eBay fits inside the box, so a
        # portrait card at s-l500 comes back only ~280-380px wide and looks soft.
        return base + "s-l1600.jpg", base + "s-l960.jpg"
    return photo, photo


def pretty_month(iso: str) -> str:
    try:
        return datetime.strptime(iso.strip(), "%Y-%m-%d").strftime("%b %Y")
    except Exception:
        return iso.strip()


def read_listings():
    """Active eBay listings -> for-sale cards."""
    rows = []
    if not RAW.exists():
        return rows
    OVERRIDES = listing_photo_overrides()
    with RAW.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            title = (r.get("title") or "").strip()
            if not title:
                continue
            key = (r.get("imageKey") or "").strip()
            override = OVERRIDES.get((r.get("itemId") or "").strip(), "")
            price = float(r["price"])
            item_id = r["itemId"].strip()
            rows.append({
                "id": item_id,
                "status": "forsale",
                "title": title,
                "price": price,
                "priceLabel": money(price),
                "priceNote": "",
                "url": f"https://www.ebay.com/itm/{item_id}",
                "image": override or (f"https://i.ebayimg.com/images/g/{key}/s-l1600.jpg" if key else ""),
                "thumb": override or (f"https://i.ebayimg.com/images/g/{key}/s-l960.jpg" if key else ""),
                "imageBack": back_photo(override),
                "thumbBack": back_photo(override),
                "sku": (r.get("sku") or "").strip(),
                "note": "",
            })
    return rows


def read_collection():
    """Cards that are not on eBay right now: owned-not-for-sale, and previously sold."""
    rows = []
    if not COLLECTION.exists():
        return rows
    with COLLECTION.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for lineno, r in enumerate(reader, start=2):
            # A stray tab silently shifts every later column, so fail loudly instead.
            if None in r or any(v is None for v in r.values()):
                raise SystemExit(
                    f"collection.tsv line {lineno}: expected {len(reader.fieldnames)} "
                    f"tab-separated columns — check for a missing or extra tab.\n"
                    f"  {r.get('title') or list(r.values())[:2]}"
                )
            title = (r.get("title") or "").strip()
            if not title or title.startswith("#"):
                continue
            status = (r.get("status") or "collection").strip().lower()
            if status not in ("collection", "sold"):
                status = "collection"

            est = (r.get("estValue") or "").strip()
            est_val = float(est.replace("$", "").replace(",", "")) if est else None
            sold = (r.get("soldPrice") or "").strip()
            sold_val = float(sold.replace("$", "").replace(",", "")) if sold else None
            comp_date = (r.get("compDate") or "").strip()
            sold_date = (r.get("soldDate") or "").strip()

            if status == "sold":
                shown = sold_val if sold_val is not None else est_val
                label = money(shown) if shown is not None else "Sold"
                note = "Sold " + pretty_month(sold_date) if sold_date else "Sold"
            else:
                shown = est_val
                label = money(shown) if shown is not None else "Not for sale"
                note = ("Est. value" + (" · " + pretty_month(comp_date) if comp_date else "")
                        if shown is not None else "")

            image, thumb = photo_urls(r.get("photo"))
            back = back_photo(r.get("photo"))
            image_back, thumb_back = photo_urls(back) if back else ("", "")
            rows.append({
                "id": (r.get("sku") or "").strip() or slugify(title),
                "status": status,
                "title": title,
                "price": shown if shown is not None else 0.0,
                "priceLabel": label,
                "priceNote": note,
                "url": "",
                "image": image,
                "thumb": thumb,
                "imageBack": image_back,
                "thumbBack": thumb_back,
                "sku": (r.get("sku") or "").strip(),
                "note": (r.get("notes") or "").strip(),
            })
    return rows


def enrich(card):
    title = card["title"]
    card["category"] = categorize(title)
    card["brand"] = brand_of(title)
    card["year"] = year_of(title)
    card["serial"] = serial_of(title)
    card["tags"] = tags_of(title)
    return card


def build():
    cards = [enrich(c) for c in read_listings() + read_collection()]
    cards.sort(key=lambda c: (0 if c["status"] == "forsale" else 1, -c["price"]))

    for_sale = [c for c in cards if c["status"] == "forsale"]
    owned = [c for c in cards if c["status"] == "collection"]
    sold = [c for c in cards if c["status"] == "sold"]

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
        "count": len(for_sale),
        "collectionCount": len(owned),
        "soldCount": len(sold),
        "totalValue": round(sum(c["price"] for c in for_sale), 2),
        "collectionValue": round(sum(c["price"] for c in owned), 2),
        "cards": cards,
    }

    payload = json.dumps(data)
    tpl = TEMPLATE.read_text(encoding="utf-8")
    if "__MECV_DATA__" not in tpl:
        raise SystemExit("build/template.html is missing the __MECV_DATA__ placeholder")
    OUT_HTML.write_text(tpl.replace("__MECV_DATA__", payload), encoding="utf-8")
    OUT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")

    cats = {}
    for c in cards:
        cats[c["category"]] = cats.get(c["category"], 0) + 1
    print(f"{len(for_sale)} for sale  ·  {money(data['totalValue'])}")
    if owned:
        print(f"{len(owned)} in the collection  ·  {money(data['collectionValue'])} est.")
    if sold:
        print(f"{len(sold)} sold")
    print(f"{len(cards)} cards total")
    for k, v in sorted(cats.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<12} {v}")


if __name__ == "__main__":
    build()
