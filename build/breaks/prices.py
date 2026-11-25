"""eBay asking prices for the names in the current breaks (Daniel, Nov 24, 2026).

Uses eBay's Browse API (free developer account, application token) to look at current Buy It Now listings for
"<product> <player>" in Sports Trading Card Singles, and keeps a rough typical price per player per product:
the median of matching raw (ungraded) single-card listings. These are asking prices, not sales.

  EBAY_CLIENT_ID=... EBAY_CLIENT_SECRET=... python3 build/breaks/prices.py

Reads  watch/price_targets.json  (written by build.py: every product + player in the breaks that haven't run)
Writes watch/prices.json         {"<query>": [median, low, listings, "YYYY-MM-DD"]}

Each run refreshes the targets with no price yet first, then the oldest, up to MAX_CALLS searches, so a big
break fills in over a day or two and the run stays well inside eBay's daily call limit. Without keys it does
nothing and exits cleanly.
"""
import base64, datetime, json, os, re, statistics, sys, time, unicodedata, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WATCH = os.path.join(HERE, 'watch')
MAX_CALLS = int(os.environ.get('PRICE_MAX_CALLS', '4500'))
KEEP_DAYS = 3                      # a price newer than this isn't looked up again
CATEGORY = '261328'                # eBay: Sports Trading Cards > Trading Card Singles
SKIP = re.compile(r'\b(lots?|you pick|pick your|choose|complete set|team set|base set|psa|bgs|sgc|cgc|graded|slab(bed)?|'
                  r'box|packs?|break|digital|reprint|custom|rp|u-?pick)\b', re.I)


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower()


def token(cid, secret):
    req = urllib.request.Request('https://api.ebay.com/identity/v1/oauth2/token',
        data=urllib.parse.urlencode({'grant_type': 'client_credentials', 'scope': 'https://api.ebay.com/oauth/api_scope'}).encode(),
        headers={'Authorization': 'Basic ' + base64.b64encode((cid + ':' + secret).encode()).decode(),
                 'Content-Type': 'application/x-www-form-urlencoded'})
    return json.load(urllib.request.urlopen(req, timeout=30))['access_token']


def search(tok, q):
    url = 'https://api.ebay.com/buy/browse/v1/item_summary/search?' + urllib.parse.urlencode(
        {'q': q, 'category_ids': CATEGORY, 'limit': '50', 'filter': 'buyingOptions:{FIXED_PRICE},priceCurrency:USD'})
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + tok, 'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'})
    return json.load(urllib.request.urlopen(req, timeout=30)).get('itemSummaries', [])


def summarize(items, player):
    """median and low of single raw cards whose title names the player"""
    last = fold(player.split()[-1]).strip('.,')
    vals = []
    for it in items:
        t = fold(it.get('title', ''))
        if last not in t or SKIP.search(t): continue
        try: vals.append(float(it['price']['value']))
        except (KeyError, ValueError): pass
    if len(vals) < 3: return None
    return [round(statistics.median(vals), 2), round(min(vals), 2), len(vals)]


def main():
    cid, secret = os.environ.get('EBAY_CLIENT_ID'), os.environ.get('EBAY_CLIENT_SECRET')
    if not (cid and secret):
        print('No eBay keys (EBAY_CLIENT_ID, EBAY_CLIENT_SECRET); skipping prices.'); return
    targets = json.load(open(os.path.join(WATCH, 'price_targets.json')))
    path = os.path.join(WATCH, 'prices.json')
    prices = json.load(open(path)) if os.path.exists(path) else {}
    today = datetime.date.today()
    def age(q):
        p = prices.get(q)
        return 9999 if not p else (today - datetime.date.fromisoformat(p[3])).days
    todo = sorted((t for t in targets if age(t['q']) >= KEEP_DAYS), key=lambda t: -age(t['q']))[:MAX_CALLS]
    print(len(targets), 'targets,', len(todo), 'to look up')
    tok = token(cid, secret)
    done = 0
    for t in todo:
        try:
            s = summarize(search(tok, t['q']), t['player'])
        except urllib.error.HTTPError as e:
            if e.code == 429: print('eBay call limit reached; stopping for today.'); break
            if e.code == 401: tok = token(cid, secret); continue
            print('skip', t['q'], e.code); continue
        except Exception as e:
            print('skip', t['q'], e); continue
        prices[t['q']] = (s or [None, None, 0]) + [today.isoformat()]
        done += 1
        time.sleep(0.15)
    keep = {t['q'] for t in targets}
    prices = {q: v for q, v in sorted(prices.items()) if q in keep}   # drop players from breaks that are over
    json.dump(prices, open(path, 'w'), indent=0, ensure_ascii=False)
    print('looked up', done, '; prices on file', sum(1 for v in prices.values() if v[0] is not None))


if __name__ == '__main__':
    main()
