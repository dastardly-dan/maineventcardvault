"""Break watcher: run on a timer by GitHub Actions (.github/workflows/break-watch.yml).

Reads each breaker's public Shopify product list and keeps three files in build/breaks/watch/:

  seen.json   every product handle seen so far, per shop
  queue.json  products that showed up (or disappeared) since the last time Claude cleared the queue,
              with the full listing text, price options and dates, so a page can be built from them
  posts.json  when each product was published and when the watcher first saw it, used to learn
              when each breaker usually posts new breaks
  stats.md    weekday and hour (Eastern) each breaker publishes, from posts.json
  images.json each product's title card image, shown on the Break guides page

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


# ---- Streams (Daniel, Nov 25, 2026): note when a breaker's YouTube stream goes live, so the page builder can run every
# 5 minutes for the first 4 hours of the stream. streams.json: {shop: {video, title, live, started, first_start}}.
# Each breaker's YouTube channel (Daniel, Nov 25, 2026). None: read the channel link off the store's homepage.
STREAM_PAGES = {'rgl': 'https://www.youtube.com/@RunGoodLife/live', 'jml': 'https://www.youtube.com/@THEJMLEXPERIENCE/live',
                'acme': 'https://www.youtube.com/@AcmePacks/live', 'jwj': 'https://www.youtube.com/@JWJBreaks/live', 'colfax': None}
STREAM_STORE = {'jml': 'rgl'}  # JML Breaks sells on Run Good Life's store
# Weekly stream times Daniel sent (Nov 25, 2026), used when the listings don't give a start time.
# (weekday Monday=0, hour, minute, time zone)
WEEKLY = {'colfax': [(6, 17, 0, 'America/Chicago'), (1, 18, 0, 'America/Chicago')],   # Sundays 5 pm and Tuesdays 6 pm Central
          'jwj': [(0, 20, 0, 'America/New_York')]}                                  # Mondays 8 pm Eastern
YT_LINK = re.compile(r'https?://(?:www\.)?youtube\.com/(@[\w.-]+|channel/[\w-]+|c/[\w-]+|user/[\w-]+)')

def channel_live_url(shop, st):
    """The breaker's YouTube /live page, found once on its store homepage and remembered in streams.json."""
    if STREAM_PAGES.get(shop):
        return STREAM_PAGES[shop]
    if not st.get('channel'):
        req = urllib.request.Request(SHOPS[STREAM_STORE.get(shop, shop)], headers={'User-Agent': UA['User-Agent']})
        with urllib.request.urlopen(req, timeout=30) as r:
            m = YT_LINK.search(r.read().decode('utf-8', 'replace'))
        if not m:
            return None
        st['channel'] = 'https://www.youtube.com/' + m.group(1)
    return st['channel'].rstrip('/') + '/live'

def weekly_start(shop, now_dt):
    """The scheduled stream start closest to now (looking from 12 hours back to a day ahead), or None."""
    best = None
    for wd, h, mi, tz in WEEKLY.get(shop, []):
        z = ZoneInfo(tz); local = now_dt.astimezone(z)
        for back in range(-1, 2):
            d = (local - __import__('datetime').timedelta(days=back)).date()
            if d.weekday() != wd:
                continue
            t = datetime(d.year, d.month, d.day, h, mi, tzinfo=z).astimezone(timezone.utc)
            if now_dt - __import__('datetime').timedelta(hours=12) <= t <= now_dt + __import__('datetime').timedelta(days=1):
                best = t if best is None or t < best else best
    return best
PT = ZoneInfo('America/Los_Angeles')
MONTHS = {m: i for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september',
                                      'october', 'november', 'december'], 1)}
START_RE = re.compile(r'(?:ESTIMATED START TIME:|hosted by\b.*?\bon)\s*\w+day,\s*([A-Za-z]+)\s+(\d{1,2})\w*,?\s*(?:(\d{4})\s*)?@\s*(\d{1,2})(?::(\d{2}))?\s*([AP]M)\s*PT', re.I | re.S)

def listing_start(text, now):
    """The listing's estimated start time (RGL writes 'ESTIMATED START TIME: Wednesday, November 25th @ 8:45 PM PT')."""
    m = START_RE.search(text or '')
    if not m or m.group(1).lower() not in MONTHS:
        return None
    mon, day, yr, hr, mi, ap = MONTHS[m.group(1).lower()], int(m.group(2)), int(m.group(3) or now.year), int(m.group(4)), int(m.group(5) or 0), m.group(6).upper()
    hr = hr % 12 + (12 if ap == 'PM' else 0)
    try:
        return datetime(yr, mon, day, hr, mi, tzinfo=PT).astimezone(timezone.utc)
    except ValueError:
        return None

def youtube_live(url):
    """(video id, title, live now) for a channel's /live page, or None. Best effort: YouTube may change its page."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36',
                                               'Accept-Language': 'en-US,en;q=0.9', 'Cookie': 'CONSENT=YES+1'})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode('utf-8', 'replace')
    m = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([\w-]{11})"', html)
    if not m:
        return None
    t = re.search(r'<meta name="title" content="([^"]*)"', html)
    live = '"isLiveNow":true' in html or ('"isLive":true' in html and '"isUpcoming":true' not in html)
    return m.group(1), (t.group(1) if t else ''), live

def check_streams(items_by_shop, now_dt):
    streams = load('streams.json', {})
    for shop in STREAM_PAGES:
        st = dict(streams.get(shop, {}))
        # RGL's listings say which stream they're on only by title; JML breaks are titled JML
        store_items = [p for p in items_by_shop.get(STREAM_STORE.get(shop, shop), [])
                       if shop not in ('rgl', 'jml') or (('jml' in (p.get('title') or '').lower()) == (shop == 'jml'))]
        starts = [listing_start(plain(p.get('body_html', '')), now_dt) for p in store_items]
        starts = sorted(x for x in starts if x and x > now_dt - __import__('datetime').timedelta(hours=12))
        wk = weekly_start(shop, now_dt)
        if wk:
            starts = sorted(starts + [wk])
        # dated break nights from watch/schedule.json (RGL and its sister channel JML sell on the rgl store)
        for n in load('schedule.json', {}).get('nights', []):
            try:
                t = datetime.fromisoformat(n['start']).astimezone(timezone.utc)
            except (KeyError, ValueError):
                continue
            if (n.get('stream') or n.get('store')) == shop and now_dt - __import__('datetime').timedelta(hours=12) <= t <= now_dt + __import__('datetime').timedelta(days=1):
                starts = sorted(starts + [t])
        if starts:
            st['first_start'] = starts[0].isoformat(timespec='minutes')
        # Look for the stream from 2 hours before the first scheduled break (Daniel, Nov 25), and keep checking while it's live.
        fs = datetime.fromisoformat(st['first_start']) if st.get('first_start') else None
        looking = st.get('live') or (fs is not None and fs - __import__('datetime').timedelta(hours=2) <= now_dt <= fs + __import__('datetime').timedelta(hours=10))
        yl = None
        try:
            live_url = channel_live_url(shop, st)  # finds and remembers the channel even outside stream times
        except Exception as e:
            print('warning: channel link', shop, e, file=sys.stderr); live_url = None
        if looking and live_url:
            try:
                yl = youtube_live(live_url)
            except Exception as e:
                print('warning: stream check', shop, e, file=sys.stderr)
        if not looking and st.get('live'):
            st['live'] = False
        if yl:
            vid, title, live = yl
            if vid != st.get('video'):
                st.update(video=vid, title=title, started='')
            if live and not st.get('started'):
                st['started'] = now_dt.isoformat(timespec='minutes')
            st['live'] = live
        streams[shop] = st
    return save('streams.json', streams)


def main():
    os.makedirs(OUT, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    seen = load('seen.json', {})
    queue = load('queue.json', [])
    posts = load('posts.json', [])
    first_run = not seen
    images = load('images.json', {})  # {shop: {handle: title card image}} for the Break guides page
    known_posts = {(p['shop'], p['handle']) for p in posts}
    changed = False
    errors = []
    by_shop = {}
    for shop, origin in SHOPS.items():
        try:
            items = products(shop, origin)
        except Exception as e:  # one store being down shouldn't stop the rest
            errors.append(f'{shop}: {e}')
            continue
        by_shop[shop] = items
        handles = [p['handle'] for p in items]
        imgs = {}
        for p in items:
            src = (p.get('images') or [{}])[0].get('src', '')
            if src:
                imgs[p['handle']] = ('https:' + src) if src.startswith('//') else src
        images[shop] = dict(sorted({**images.get(shop, {}), **imgs}.items()))
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
    changed |= check_streams(by_shop, datetime.now(timezone.utc))
    changed |= save('images.json', images)
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
