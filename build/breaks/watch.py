"""Break watcher: run on a timer by GitHub Actions (.github/workflows/break-watch.yml).

Reads each breaker's public Shopify product list and keeps three files in build/breaks/watch/:

  seen.json   every product handle seen so far, per shop
  queue.json  products that showed up (or disappeared) since the last time Claude cleared the queue,
              with the full listing text, price options and dates, so a page can be built from them
  posts.json  when each product was published and when the watcher first saw it, used to learn
              when each breaker usually posts new breaks
  stats.md    weekday and hour (Eastern) each breaker publishes, from posts.json

Files are only rewritten when something changed, so the job only commits when a product is added
or removed. Open/sold counts are not stored here; the site reads those live through the Worker.
"""
import json, os, re, sys, urllib.request
from collections import Counter
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SHOPS = {
    'acme': 'https://acmepackscards.com',
    'jwj': 'https://jwjcollectorbreaks.com',
    'colfax': 'https://colfaxcc.com',
    'rgl': 'https://rungoodlife.com',
}
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'watch')
ET = ZoneInfo('America/New_York')
# Extra collections to read besides /products.json (some stores keep breaks in their own collection).
COLLECTIONS = {'rgl': ['rgl-breaks'], 'acme': ['group-breaks'], 'jwj': ['group-breaks']}
UA = {'User-Agent': 'MainEventCardVault break watcher (+https://maineventcardvault.com)', 'Accept': 'application/json'}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def plain(html):
    s = re.sub(r'<\s*(br|/p|/div|/li|/h[1-6]|/tr)\b[^>]*>', '\n', html or '', flags=re.I)
    s = re.sub(r'<li\b[^>]*>', '- ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', '', s)
    for a, b in (('&nbsp;', ' '), ('&amp;', '&'), ('&#39;', "'"), ('&rsquo;', "'"), ('&quot;', '"'), ('&ldquo;', '"'), ('&rdquo;', '"'), ('&ndash;', '-'), ('&mdash;', '-')):
        s = s.replace(a, b)
    s = re.sub(r'[ \t]+', ' ', s)
    return re.sub(r'\n\s*\n+', '\n', s).strip()


def products(shop, origin):
    out, have = [], set()
    for base in [''] + [f'/collections/{c}' for c in COLLECTIONS.get(shop, [])]:
        for page in range(1, 6):
            try:
                data = get(f'{origin}{base}/products.json?limit=250&page={page}').get('products', [])
            except Exception:
                if base:  # a missing collection is fine
                    break
                raise
            for p in data:
                if p['handle'] not in have:
                    have.add(p['handle']); out.append(p)
            if len(data) < 250:
                break
    return out


def load(name, default):
    p = os.path.join(OUT, name)
    return json.load(open(p)) if os.path.exists(p) else default


def save(name, obj):
    p = os.path.join(OUT, name)
    text = json.dumps(obj, indent=1, ensure_ascii=False) + '\n'
    if not os.path.exists(p) or open(p).read() != text:
        open(p, 'w').write(text)
        return True
    return False


def stats(posts):
    days = 'Mon Tue Wed Thu Fri Sat Sun'.split()
    lines = ['# When each breaker publishes new products', '',
             'Built by watch.py from published dates (Eastern time). Merch and fee listings are counted too,',
             'so read it as a guide. Updated whenever a product is added.', '']
    by = {}
    for p in posts:
        try:
            t = datetime.fromisoformat(p['published_at']).astimezone(ET)
        except Exception:
            continue
        by.setdefault(p['shop'], []).append((t, p))
    for shop in SHOPS:
        rows = sorted(by.get(shop, []), key=lambda x: x[0])
        lines.append(f'## {shop} ({len(rows)} products)')
        if not rows:
            lines += ['', 'No dated products yet.', '']
            continue
        dc = Counter(days[t.weekday()] for t, _ in rows)
        hc = Counter(t.hour for t, _ in rows)
        lines.append('')
        lines.append('- Days: ' + ', '.join(f'{d} {dc[d]}' for d in days if dc[d]))
        lines.append('- Hours (ET): ' + ', '.join(f'{h:02d}:00 {n}' for h, n in sorted(hc.items())))
        lines.append('- Latest: ' + '; '.join(f"{t:%a %b %d %I:%M %p} {p['title'][:50]}" for t, p in rows[-8:]))
        lines.append('')
    return '\n'.join(lines) + '\n'


def main():
    os.makedirs(OUT, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    seen = load('seen.json', {})
    queue = load('queue.json', [])
    posts = load('posts.json', [])
    first_run = not seen
    known_posts = {(p['shop'], p['handle']) for p in posts}
    changed = False
    errors = []
    for shop, origin in SHOPS.items():
        try:
            items = products(shop, origin)
        except Exception as e:  # one store being down shouldn't stop the rest
            errors.append(f'{shop}: {e}')
            continue
        handles = [p['handle'] for p in items]
        before = set(seen.get(shop, []))
        for p in items:
            key = (shop, p['handle'])
            if key not in known_posts:
                posts.append(dict(shop=shop, handle=p['handle'], title=p.get('title', ''), published_at=p.get('published_at') or '',
                                  first_seen='' if first_run else now))
                known_posts.add(key)
            if p['handle'] in before or first_run:
                continue
            queue.append(dict(
                event='added', shop=shop, first_seen=now, handle=p['handle'], title=p.get('title', ''),
                url=f"{origin}/products/{p['handle']}", published_at=p.get('published_at') or '', created_at=p.get('created_at') or '',
                type=p.get('product_type', ''), tags=p.get('tags', []),
                variants=[dict(title=v.get('title', ''), price=v.get('price', ''), available=bool(v.get('available'))) for v in p.get('variants', [])],
                text=plain(p.get('body_html', '')),
            ))
        if not first_run:
            for h in sorted(before - set(handles)):
                queue.append(dict(event='removed', shop=shop, first_seen=now, handle=h, url=f'{origin}/products/{h}'))
        if sorted(handles) != sorted(before):
            seen[shop] = sorted(handles)
    changed |= save('seen.json', seen)
    changed |= save('queue.json', queue)
    changed |= save('posts.json', posts)
    if changed:
        open(os.path.join(OUT, 'stats.md'), 'w').write(stats(posts))
    for e in errors:
        print('warning:', e, file=sys.stderr)
    print(f"{'changed' if changed else 'no change'}; queue has {len(queue)} item(s)")


if __name__ == '__main__':
    main()
