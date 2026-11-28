"""Daniel's private dashboard at maineventcardvault.com/owner, linked as "Developer dashboard" (Daniel, Nov 27, 2026).

For every current break guide it answers two questions a buyer asks, using whatever data we have, and says plainly
what's missing:

  Is the break priced fairly?  What all the spots sell for, next to what the sealed boxes cost on eBay (the asking
                               price of one sealed box times the number of boxes). The difference is the breaker's markup.
  Which spot is the best deal? Each spot's share of the break's value, turned into a fair price (its share of the box
                               cost) and compared with what the spot sells for. Only for pick-your-spot breaks; in a
                               random break every spot is the same ticket, so only the break-level number counts.

A spot's share of the value comes from the checklists: each name gets points for its cards in each box (base 1,
autograph 2, insert 0.5, multi-person 0.5), and autograph, insert and multi points grow with how many of those sets the
player is in, weighted by pack odds where we have them (depth.json, the same "hit depth" the Spot Builder uses). When at
least half of those points have an eBay asking price (watch/prices.json), each name's points are also multiplied by
its typical price, and that market share is used instead.

Writes owner/dashboard.js (one self-contained page as a string). worker.js serves it only after the password check, and
.assetsignore keeps the owner folder from being published as a plain file. hub.py runs this at the end. The Owner menu
at the top lives only in this page, never on the public site.

  python3 build/breaks/owner.py
"""
import datetime, glob, html, json, math, os, re, statistics, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LIB = os.path.join(HERE, 'checklists')
W = {'B': 1.0, 'A': 2.0, 'I': 0.5, 'M': 0.5}
MIN_COVER = 0.5   # priced names must hold this share of the points before market value is used
ACCOUNT = 'c5b859f32ead50b6cd5f9a304a0b34b3'   # Cloudflare account, for the Owner menu link
COPIED = re.compile(r'diamondcardsonline|checklistcenter|checklistinsider|cardsmithsbreaks|beckett', re.I)
BREAKER = {'gb': 'Acme Packs', 'cc': 'Colfax Collectibles', 'rg': 'Run Good Life', 'jw': 'JWJ Collector Breaks'}


def fold(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()


def dkey(n):   # same key as builder.py and depth.json
    return re.sub(r'[^a-z]', '', fold(n).lower())


def key_of(name):
    return ' '.join(re.sub(r'"[^"]*"', '', name).split())


def box_query(full):   # same as build.py's box_query (the product part of a player price search)
    q = re.sub(r'\(.*?\)', '', full)
    q = re.sub(r'\b(Hobby|Jumbo|Mega|Blaster|Value|Boxes|Box|Case|Breaker\'s Delight)\b', '', q)
    return ' '.join(q.split())


def sealed_query(full):   # same as build.py's sealed_query (the sealed box search)
    q = ' '.join(re.sub(r'\(.*?\)', '', full).replace("'", '').split())
    return q if re.search(r'\bbox\b', q, re.I) else q + ' box'


def box_count(full):
    """'(2 boxes)' -> 2, '(1 Mega box)' -> 1, '(2 Hobby, 1 Jumbo)' -> 3"""
    m = re.search(r'\(([^)]*)\)', full)
    ns = [int(x) for x in re.findall(r'\b(\d+)\b', m.group(1))] if m else []
    return sum(ns) if ns else 1


TYPES = ["Breaker's Delight", 'Chrome Delight', 'Delight', 'Lucky Envelope', 'Jumbo', 'Mega', 'FOTL', 'Hobby', 'Blaster', 'Value']


def parts(full):
    """a box line split into (product, box type, count), the keys of box_prices.json:
    '2026 Topps Chrome Football (2 Hobby, 1 Jumbo)' -> [('2026 Topps Chrome Football', 'Hobby', 2), ('2026 Topps Chrome Football', 'Jumbo', 1)]"""
    m = re.search(r'\(([^)]*)\)', full); inner = m.group(1) if m else ''
    base = re.sub(r'\(.*?\)', '', full)
    found = []
    for t in TYPES:
        if re.search(r'\b' + re.escape(t) + r'\b', base, re.I) and not any(t.lower() in f.lower() for f in found): found.append(t)
    prod = base
    for t in TYPES + ['Boxes', 'Box', 'and', '1st Off The Line', 'First Off The Line']:
        prod = re.sub(r'\b' + re.escape(t) + r'\b', '', prod, flags=re.I)
    prod = ' '.join(prod.replace('&', ' & ').split()).strip(' -,&')
    prod = ' '.join(prod.split())
    dl = lambda t: 'Delight' if 'Delight' in t else t
    out = []
    for n, t in re.findall(r"(\d+)\s+([A-Za-z' ]+?)(?:,|$| boxes| box)", inner):
        tt = next((x for x in TYPES if x.lower() in t.lower()), None)
        if tt: out.append((prod, dl(tt), int(n)))
    if out: return out
    if len(found) >= 2: return [(prod, dl(t), 1) for t in found]
    return [(prod, dl(found[0] if found else 'Hobby'), box_count(full))]


def toks(s):
    s = fold(s).lower().replace("'", '').replace('&', ' and ')
    return [t for t in re.findall(r'[a-z0-9]+', s) if t not in ('the', 'of', 'x', 'and', 'box', 'boxes', 'hobby', 'edition')]


def library():
    out = {}
    for p in glob.glob(os.path.join(LIB, '*.txt')):
        head = {}
        for line in open(p, encoding='utf-8'):
            if not line.startswith('#'): break
            k, _, v = line[1:].partition(':'); head[k.strip()] = v.strip()
        info = (head.get('note', '') + ' ' + head.get('source', '')).lower()
        # copied when it came from a fan or retailer checklist site; everything else is the maker's own file (Topps' CDN, Leaf, Panini CSVs, Kakawow, Card Fun)
        official = not (COPIED.search(info) or 'not an official' in info or 'copied from' in info)
        pid = os.path.basename(p)[:-4]
        out[pid] = dict(name=head.get('name', pid), toks=set(toks(head.get('name', pid))), official=official)
    return out


def match_box(full, lib):
    """the library checklist a box uses: every word of the checklist's name in the box's name (most words wins), or the closest by shared words"""
    bt = set(toks(re.sub(r'\(.*?\)', '', full)))
    bt -= {'jumbo', 'mega', 'blaster', 'value', 'delight', 'breakers', 'fotl', 'lucky', 'envelope'}
    yr = {t for t in bt if re.fullmatch(r'\d{4}', t)}
    best, score = None, 0
    for pid, L in lib.items():
        if yr and not (yr & L['toks']): continue
        if L['toks'] <= bt or bt <= L['toks']:
            sc = 10 + len(L['toks'] & bt)
        else:
            sc = len(L['toks'] & bt) / len(L['toks'] | bt)
            if sc < 0.5: continue
        if sc > score: best, score = pid, sc
    return best


def page_data(pid):
    p = os.path.join(ROOT, 'breaks', pid + '.html')
    if not os.path.exists(p): return None
    h = open(p, encoding='utf-8').read()
    if 'var D = ' not in h: return None
    i = h.index('var D = '); j = h.index('{', i)
    return json.JSONDecoder().raw_decode(h[j:])[0]


def money_of(t):
    m = re.search(r'\$([\d,]+(?:\.\d+)?)', t)
    return float(m.group(1).replace(',', '')) if m else None


def sale_terms(D):
    """(pick, spots sold, flat price, total): pick breaks add up their spot prices; random breaks are flat price x spots sold"""
    facts = ' | '.join(D.get('facts', []))
    pick = D.get('format') in ('pyl', 'pyt') or any(s.get('price') for s in D['spots'])
    if pick:
        ps = [s['price'] for s in D['spots'] if s.get('price')]
        return True, len(ps), None, (sum(ps) if ps else None)
    flat = None
    for f in D.get('facts', []):
        if re.search(r'per spot|a spot', f): flat = money_of(f); break
    n = None
    for rx in (r'listing says (\d+)', r'(\d+) spots for', r'(\d+) (?:team|letter|break) spots', r'(\d+) spots'):
        m = re.search(rx, facts)
        if m: n = int(m.group(1)); break
    m = re.search(r'lists (\d+) spots', D.get('checked', ''))
    if m: n = int(m.group(1))
    if not n: n = len(D['spots'])
    return False, n, flat, (flat * n if flat else None)


def esc(t):
    return html.escape(str(t), quote=True)


def money(x):
    return '' if x is None else '$' + format(round(x), ',')


def main():
    PR = json.load(open(os.path.join(HERE, 'watch', 'prices.json'), encoding='utf-8'))
    DEPTH = json.load(open(os.path.join(HERE, 'depth.json'), encoding='utf-8'))
    ODDS = set(json.load(open(os.path.join(HERE, 'odds.json'), encoding='utf-8'))) | set(json.load(open(os.path.join(HERE, 'typedrows.json'), encoding='utf-8')))
    LIBR = library()
    blp = os.path.join(HERE, 'box_lib.json')
    BOXLIB = json.load(open(blp, encoding='utf-8')) if os.path.exists(blp) else {}   # the checklist each box really used (build.py)
    idx = json.load(open(os.path.join(HERE, 'index.json'), encoding='utf-8'))
    hub = open(os.path.join(HERE, 'hub.py'), encoding='utf-8').read()
    order = re.findall(r"'([a-z0-9]+)'", re.search(r"order\s*=\s*\[(.*?)\]", hub, re.S).group(1))
    cur = [b for b in idx if not b.get('ended')]
    cur.sort(key=lambda b: order.index(b['id']) if b['id'] in order else 999)
    pdates = sorted(v[3] for v in PR.values() if v)
    targets = json.load(open(os.path.join(HERE, 'watch', 'price_targets.json'), encoding='utf-8'))
    have = sum(1 for v in PR.values() if v and v[0])
    bpp = os.path.join(HERE, 'box_prices.json')
    BP = json.load(open(bpp, encoding='utf-8')) if os.path.exists(bpp) else {}
    WEB = BP.get('boxes', {})
    QP = {t['q']: t['player'] for t in targets if not t.get('box')}
    STAR = {}   # star power: a player's highest typical eBay asking price in any product looked up
    for q, v in PR.items():
        if v and v[0] and q in QP:
            k = dkey(QP[q]); STAR[k] = max(STAR.get(k, 0), v[0])   # lowest price found on the web for one sealed box, by 'product|type' (weekly scheduled task)

    breaks, missing_all = [], {}
    for b in cur:
        D = page_data(b['id'])
        if not D or not D.get('spots') or not D.get('names'): continue
        a = dict(id=b['id'], title=D['title'], when=D.get('when', '').split('. ')[0], breaker=BREAKER.get(b['id'][:2], ''), url=D.get('url', ''))
        a['pick'], a['sold'], a['flat'], a['total'] = sale_terms(D)
        # ---- boxes: checklist, odds, eBay coverage, sealed price
        boxes, box_cost, box_missing = [], 0.0, []
        for bx in D['boxes']:
            n = box_count(bx['full']); pid = BOXLIB.get(b['id'], {}).get(bx['k']) or match_box(bx['full'], LIBR)
            if pid not in LIBR: pid = match_box(bx['full'], LIBR)
            sp = PR.get(sealed_query(bx['full']))
            ebay = sp[0] if sp and sp[0] else None
            # web price per part (each box type in the line), falling back to the eBay sealed median for the whole line
            pts, web, src, unpriced = parts(bx['full']), 0.0, [], []
            for prod, typ, cnt in pts:
                w = WEB.get(prod + '|' + typ) or {}
                if w.get('low'):
                    web += w['low'] * cnt; src.append(dict(part='%s %s' % (cnt, typ), low=w['low'], source=w.get('source', ''), url=w.get('url', ''), note=w.get('note', ''), also=w.get('also', '')))
                else: unpriced.append((prod, typ, cnt, w.get('note', '')))
            if pts and not unpriced: cost, how = web, 'web'
            elif ebay: cost, how = ebay * n, 'ebay'
            else: cost, how = None, None
            info = dict(k=bx['k'], full=bx['full'], short=bx.get('short', bx['k']), n=n, pid=pid,
                        official=bool(pid and LIBR[pid]['official']), odds=bool(pid and pid in ODDS),
                        sealed=ebay, sealed_n=(sp[2] if sp and sp[0] else 0), sealed_tried=bool(sp),
                        cost=cost, how=how, src=src, unpriced=unpriced, web_partial=(web if src and unpriced else None),
                        names=0, priced=0)
            if cost: box_cost += cost
            else: box_missing.append(info)
            boxes.append(info)
        a['boxes'] = boxes
        a['box_cost'] = box_cost if not box_missing else None
        a['box_cost_partial'] = box_cost if box_missing and box_cost else None
        # ---- names: checklist points (hit depth) and eBay prices
        rows = []   # (spot index, points, price or None, name)
        crow = []   # (spot index, autograph points, all hit points, name): what you could hit
        bmap = {x['k']: x for x in boxes}
        for si, s in enumerate(D['spots']):
            for bk, ents in D['names'].get(s['id'], {}).items():
                bx = bmap.get(bk)
                if not bx: continue
                dep = DEPTH.get(bx['pid'] or '', {})
                for e in ents:
                    fl = set(e[1] or '')
                    d = dep.get(dkey(key_of(e[0])), [1, 1, 1])
                    pts = (1.0 if e[2] or not (fl & {'A', 'I', 'M'}) else 0) \
                        + (W['A'] * math.sqrt(max(d[0], 0.25)) if 'A' in fl else 0) \
                        + (W['I'] * math.sqrt(max(d[1], 0.25)) if 'I' in fl else 0) \
                        + (W['M'] * math.sqrt(max(d[2], 0.25)) if 'M' in fl else 0)
                    ap = W['A'] * math.sqrt(max(d[0], 0.25)) if 'A' in fl else 0
                    hp = ap + (W['I'] * math.sqrt(max(d[1], 0.25)) if 'I' in fl else 0) + (W['M'] * math.sqrt(max(d[2], 0.25)) if 'M' in fl else 0)
                    if '?' in fl: pts *= 0.5; ap *= 0.5; hp *= 0.5   # listed under two letters (nickname); half to each
                    pts *= bx['n']; ap *= bx['n']; hp *= bx['n']
                    if hp: crow.append((si, ap, hp, e[0]))
                    v = PR.get(box_query(bx['full']) + ' ' + key_of(e[0]).strip())
                    px = v[0] if v and v[0] else None
                    bx['names'] += 1; bx['priced'] += 1 if px else 0
                    rows.append((si, pts, px, e[0]))
        tw = sum(r[1] for r in rows) or 1
        priced = [r for r in rows if r[2]]
        a['cover'] = sum(r[1] for r in priced) / tw
        a['market'] = a['cover'] >= MIN_COVER and len(priced) >= 8
        ref = statistics.median([r[2] for r in priced]) if priced else 0
        spots = [dict(label=s['label'], sub=s.get('g') or '', price=s.get('price') or a['flat'], status=s.get('status') or '', val=0.0, top={}) for s in D['spots']]
        for si, w, px, nm in rows:
            sp = spots[si]
            v = w * (px or ref) if a['market'] else w
            sp['val'] += v; sp['top'][nm] = sp['top'].get(nm, 0) + v
        tv = sum(s['val'] for s in spots) or 1
        for s in spots:
            s['share'] = s['val'] / tv
            s['top'] = [nm for nm, v in sorted(s['top'].items(), key=lambda x: -x[1])[:4]]
            s['fair'] = s['share'] * a['box_cost'] if a['box_cost'] else None
            s['deal'] = (s['fair'] / s['price']) if s['fair'] and s['price'] else None
        a['spots'] = spots
        a['fair_spot'] = (a['box_cost'] / a['sold']) if a['box_cost'] and a['sold'] else None
        # ---- hit potential: the biggest chase names (autographs x star power) and the cheapest shot at one
        stars = [STAR[dkey(key_of(nm))] for _, _, _, nm in crow if dkey(key_of(nm)) in STAR]
        sref = statistics.median(stars) if stars else 1.0
        a['star_cover'] = len(set(nm for _, _, _, nm in crow if dkey(key_of(nm)) in STAR)) / (len(set(nm for *_, nm in crow)) or 1)
        chase, hitv = {}, [0.0] * len(spots)
        pername = [dict() for _ in spots]   # per spot: name -> (hit value, has an autograph)
        for si, ap, hp, nm in crow:
            st = STAR.get(dkey(key_of(nm)), sref)
            chase[nm] = chase.get(nm, 0) + ap * st; hitv[si] += hp * st
            v, au = pername[si].get(nm, (0.0, False)); pername[si][nm] = (v + hp * st, au or ap > 0)
        top = [nm for nm, v in sorted(chase.items(), key=lambda x: -x[1]) if v > 0][:10]
        a['top_chase'] = [(nm, STAR.get(dkey(key_of(nm)))) for nm in top]
        tset, th = set(top), sum(hitv) or 1
        for si, sp in enumerate(spots):
            sp['hit_share'] = hitv[si] / th
            sp['big'] = sorted({nm for s2, _, _, nm in crow if s2 == si and nm in tset}, key=top.index)
            # hit rating: the spot's share of the hit value against an even split (1.0 = average), as 1 to 5 stars
            r = sp['hit_share'] * len(spots)
            sp['hit_ratio'] = r
            sp['stars'] = 5 if r >= 2.0 else 4 if r >= 1.4 else 3 if r >= 0.85 else 2 if r >= 0.45 else 1 if r > 0 else 0
            sp['hit_names'] = [(nm, STAR.get(dkey(key_of(nm))), au) for nm, (v, au) in sorted(pername[si].items(), key=lambda x: -x[1][0])[:3]]
            autos = [(STAR.get(dkey(key_of(nm)), 0), nm) for nm, (v, au) in pername[si].items() if au]
            sp['ceiling'] = max(autos) if autos and max(autos)[0] else None
            sp['value'] = sp['deal'] if a['pick'] else ((a['fair_spot'] / a['flat']) if a['fair_spot'] and a['flat'] else None)
        tot = a['total'] or 0
        for sp in spots:   # hit value for the price: the spot's share of the hits next to its share of what the whole break costs
            sp['hit_deal'] = (sp['hit_share'] / (sp['price'] / tot)) if a['pick'] and sp['price'] and tot else None
            sp['score'] = math.sqrt(sp['hit_deal'] * sp['value']) if sp['hit_deal'] and sp['value'] else (sp['hit_deal'] or None)
        a['best_spots'] = sorted([sp for sp in spots if sp['score']], key=lambda sp: -sp['score'])[:8] if a['pick'] else []
        if a['pick']:
            cands = [sp for sp in spots if sp['big'] and sp['price']]
            best = max(cands, key=lambda sp: (100 / sp['price']) * (sp['value'] or 1) * len(sp['big']) ** 0.5) if cands else None
            a['entry'] = best['price'] if best else (min(sp['price'] for sp in spots if sp['price']) if any(sp['price'] for sp in spots) else None)
            a['chance'] = 1.0 if best else None
            a['up_spot'] = best
            a['up_value'] = best['value'] if best else None
        else:
            n_listed = len(spots); with_big = sum(1 for sp in spots if sp['big'])
            g = (n_listed / a['sold']) if a['sold'] and a['sold'] < n_listed else 1   # spots grouped live hold several teams or letters each
            a['chance'] = 1 - (1 - with_big / n_listed) ** g if n_listed else None
            a['entry'], a['up_spot'] = a['flat'], None
            a['up_value'] = spots[0]['value'] if spots else None
        # what one shot at a top chase name costs you (entry over chance), then adjusted for the spot's value for the price
        a['per_shot'] = (a['entry'] / a['chance']) if a['chance'] and a['entry'] else None
        a['adj'] = (a['per_shot'] / min(a['up_value'] or 1.0, 1.5)) if a['per_shot'] else None
        a['upside'] = a['adj']
        a['markup'] = (a['total'] / a['box_cost']) if a['total'] and a['box_cost'] else None
        a['fair_spot'] = (a['box_cost'] / a['sold']) if a['box_cost'] and a['sold'] else None
        # ---- what's missing, in plain words, with what would help
        miss = []
        for bx in boxes:
            if not bx['pid']:
                miss.append(('checklist', 'No checklist linked for %s, so its cards aren\'t counted.' % bx['full']))
            elif not bx['official']:
                miss.append(('source', 'The %s checklist was copied from a website, not the maker\'s own file.' % bx['short']))
            if not bx['cost']:
                for prod, typ, cnt, note in bx['unpriced']:
                    miss.append(('box', 'No box price for %s %s.%s' % (prod, typ, (' ' + note) if note else ' The weekly price check didn\'t find one; tell me what one costs.')))
            if bx['pid'] and not bx['odds']:
                miss.append(('odds', 'No pack odds for %s, so its hit sets all count about the same.' % bx['short']))
            if bx['names'] and bx['priced'] / bx['names'] < 0.5:
                miss.append(('prices', 'Only %d of %d names in %s have an eBay price so far.' % (bx['priced'], bx['names'], bx['short'])))
        if not a['total']:
            miss.append(('price', 'No spot price on the listing, so the break total can\'t be worked out.'))
        a['miss'] = miss
        for kind, text in miss: missing_all.setdefault(kind, []).append((a, text))
        conf = (1 if a['box_cost'] else 0) + (1 if a['market'] else 0) + (1 if all(x['official'] for x in boxes) else 0) \
            + (1 if all(x['odds'] for x in boxes if x['pid']) else 0)
        a['conf'] = ['Low', 'Low', 'Medium', 'Medium', 'High'][conf]
        breaks.append(a)

    # ---------------- page ----------------
    def deal_cell(r):
        if r is None: return '<td class="r na">needs box cost</td>'
        cls = 'up' if r >= 1.2 else 'dn' if r <= 0.85 else ''
        return '<td class="r %s">%.2fx</td>' % (cls, r)

    def markup_cell(m):
        if m is None: return '<td class="r na">needs box cost</td>'
        pct = round((m - 1) * 100)
        cls = 'up' if m <= 1.10 else 'dn' if m > 1.35 else ''
        return '<td class="r %s">%s%%</td>' % (cls, ('+' if pct > 0 else '') + str(pct))

    def verdict(a):
        if a['markup'] is None: return 'Waiting on sealed box prices'
        m = a['markup']
        if m <= 1.0: return 'Selling for less than the boxes cost'
        if m <= 1.10: return 'Close to what the boxes cost'
        if m <= 1.35: return 'A typical breaker markup'
        return 'A high markup'

    def best_spot(a):
        if not a['pick']: return None
        ds = [s for s in a['spots'] if s['deal']]
        return max(ds, key=lambda s: s['deal']) if ds else max(a['spots'], key=lambda s: s['share'] / (s['price'] or 1e9))

    def box_cell(bx):
        if bx['how'] == 'web':
            lines = []
            for x in bx['src']:
                name = ('<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(x['url']), esc(x['source']))) if x['url'] else esc(x['source'])
                lines.append('%s%s at %s' % ((esc(x['part']) + ': ') if len(bx['src']) > 1 or bx['n'] > 1 else '', money(x['low']), name))
            tip = ' '.join(t for x in bx['src'] for t in (x['note'], ('Also: ' + x['also']) if x['also'] else '') if t)
            return '%s<div class="sm">%s</div>' % (money(bx['cost']), '<br>'.join(lines)) + ('<div class="sm" title="%s">more</div>' % esc(tip) if tip else '')
        if bx['how'] == 'ebay':
            return '%s<div class="sm">eBay median, %d listings%s</div>' % (money(bx['cost']), bx['sealed_n'], (', %s x %d' % (money(bx['sealed']), bx['n'])) if bx['n'] > 1 else '')
        return '<span class="na">not yet</span>' + ('<div class="sm">%s so far</div>' % money(bx['web_partial']) if bx['web_partial'] else '')

    secs = []
    ov = ['<h2>Which breaks are worth it</h2><p class="lede">Every current break, with what all its spots sell for next to the lowest price we found for its sealed boxes. '
          'Breakers usually charge somewhat more than the boxes cost; the lower the markup, the better the deal for buyers. Fillers aren\'t counted.</p>',
          '<table><thead><tr><th>Break</th><th class="n">Spots</th><th class="n">Break total</th><th class="n">Box cost</th><th class="n">Markup</th><th>Best spot for the price</th><th>Confidence</th></tr></thead><tbody>']
    for a in sorted(breaks, key=lambda a: (a['markup'] is None, a['markup'] or 0)):
        bs = best_spot(a)
        bsx = '<span class="na">random, no picking</span>' if not a['pick'] else (
            '<b>%s</b> %s<div class="sm">%s</div>' % (esc(bs['label']), money(bs['price']),
             ('fair price ' + money(bs['fair'])) if bs['fair'] else 'most checklist value per dollar')) if bs else ''
        ov.append('<tr><td><a href="#/b/%s"><b>%s</b></a><div class="sm">%s · %s</div></td><td class="n">%s%s</td><td class="n">%s</td><td class="n">%s</td>%s<td>%s</td><td><span class="conf %s">%s</span></td></tr>' % (
            a['id'], esc(a['title']), esc(a['breaker']), esc(a['when']), a['sold'] or '', (' at ' + money(a['flat'])) if a['flat'] else '',
            money(a['total']) or '<span class="na">unknown</span>',
            money(a['box_cost']) or ('<span class="na">%s</span>' % ('partly priced' if a['box_cost_partial'] else 'not yet')),
            markup_cell(a['markup']), bsx, a['conf'].lower(), a['conf']))
    ov.append('</tbody></table>')
    ov.append('<div class="stats"><div><b>%d</b><span>current breaks</span></div><div><b>%d</b><span>with all box costs</span></div><div><b>%d</b><span>using eBay player prices</span></div><div><b>%s</b><span>names with an eBay price</span></div></div>' % (
        len(breaks), sum(1 for a in breaks if a['box_cost']), sum(1 for a in breaks if a['market']), format(have, ',')))
    # right-now picks, at the top of the overview
    ranked = sorted([a for a in breaks if a['adj']], key=lambda a: a['adj'])
    valued = sorted([a for a in breaks if a['up_value'] and not a['pick']], key=lambda a: -a['up_value'])
    pspots = sorted([(a, sp) for a in breaks if a['pick'] for sp in a['best_spots'][:1]], key=lambda x: -x[1]['score'])
    hl = []
    if ranked:
        r = ranked[0]
        hl.append('<div><span>Best shot at a big hit for the money</span><a href="#/b/%s"><b>%s</b></a><div class="sm">%s%s to get in%s, about %s per shot at one of its 10 biggest chase names</div></div>' % (
            r['id'], esc(r['title']), (esc(r['up_spot']['label']) + ' for ') if r['up_spot'] else '', money(r['entry']),
            (', holds ' + esc(r['up_spot']['big'][0]) + (', already sold' if r['up_spot']['status'] == 'sold' else '')) if r['up_spot'] and r['up_spot']['big'] else (', %d%% chance' % round(r['chance'] * 100)), money(r['per_shot'])))
    if valued:
        r = valued[0]
        hl.append('<div><span>Most value for a random spot</span><a href="#/b/%s"><b>%s</b></a><div class="sm">a %s spot is worth about %s (%.2fx)</div></div>' % (
            r['id'], esc(r['title']), money(r['flat']), money(r['fair_spot']), r['up_value']))
    if pspots:
        r, sp = pspots[0]
        hl.append('<div><span>Best pick-your-spot buy</span><a href="#/b/%s"><b>%s</b></a><div class="sm">%s for %s%s%s</div></div>' % (
            r['id'], esc(r['title']), esc(sp['label']), money(sp['price']), (', with ' + esc(', '.join(sp['big'][:2]))) if sp['big'] else '', ' (already sold)' if sp['status'] == 'sold' else ''))
    if hl: ov.insert(1, '<div class="picks">%s</div>' % ''.join(hl))
    lk = lambda a: '<a href="#/b/%s">%s</a>' % (a['id'], esc(a['title']))
    mk = [a for a in breaks if a['markup']]
    tk = []
    below = [a for a in mk if a['markup'] < 1.0]
    close = [a for a in mk if 1.0 <= a['markup'] <= 1.25]
    high = sorted([a for a in mk if a['markup'] > 1.5], key=lambda a: -a['markup'])
    if below: tk.append('Selling for less than the boxes cost, so buyers get more than they pay: %s.' % ', '.join('%s (%d%% under)' % (lk(a), round((1 - a['markup']) * 100)) for a in below))
    if close: tk.append('Close to box cost: %s.' % ', '.join('%s (+%d%%)' % (lk(a), round((a['markup'] - 1) * 100)) for a in sorted(close, key=lambda a: a['markup'])))
    if high: tk.append('Highest markups: %s.' % ', '.join('%s (+%d%%)' % (lk(a), round((a['markup'] - 1) * 100)) for a in high))
    for a in breaks:
        if a['pick'] and a['best_spots']:
            g = [sp for sp in a['best_spots'] if sp['value'] and sp['value'] >= 1.4 and sp['status'] != 'sold'][:2]
            bad = sorted([sp for sp in a['spots'] if sp['value'] and sp['value'] < 0.5 and sp['price']], key=lambda sp: sp['value'])[:2]
            if g or bad:
                tk.append('%s: %s%s%s.' % (lk(a), ('best open spots ' + ', '.join('%s %s (%.1fx)' % (esc(sp['label']), money(sp['price']), sp['value']) for sp in g)) if g else '',
                          '; ' if g and bad else '', ('weakest ' + ', '.join('%s %s (%.1fx)' % (esc(sp['label']), money(sp['price']), sp['value']) for sp in bad)) if bad else ''))
    nobox = [a for a in breaks if not a['box_cost']]
    if nobox: tk.append('Not scored yet: %s, waiting on a box price.' % ', '.join(lk(a) for a in nobox))
    if tk: ov.insert(2 if hl else 1, '<div class="picks takeaways"><div><span>What this means</span><ul>%s</ul></div></div>' % ''.join('<li>%s</li>' % t for t in tk))
    secs.append(('overview', 'Overview', ''.join(ov)))

    lede = ('Which breaks give you the best shot at a big hit for what it costs to get in, one ranking per breaker. Each break\'s biggest chase names are its '
            'autographs weighted by star power (the player\'s typical eBay asking price in any product we\'ve looked up). The chance is for one spot to hold at least one '
            'of those 10 names; for pick-your-spot breaks it\'s the best spot that holds one. <b>Cost per shot</b> is the price to get in divided by that chance: a $100 spot with a 50% chance costs $200 per shot. '
            '<b>Adjusted</b> divides that by the spot\'s value for the price, so overpriced spots slide down and fairly priced ones move up. Lowest adjusted cost is ranked first. Switch to <b>Best odds</b> to rank by the chance alone.')
    head = ('<table><thead><tr><th>#</th><th>Break</th><th class="n">Entry</th><th class="n">Chance at a top chase</th><th class="n">Cost per shot</th>'
            '<th class="n">Value for the price</th><th class="n">Adjusted</th><th>Biggest chase names</th></tr></thead><tbody>')

    def odds_key(a):   # best odds first; ties go to the cheaper shot
        return (a['chance'] is None, -(a['chance'] or 0), a['per_shot'] or 1e9)

    def hit_rows(group, show_breaker, by='money'):
        out = []
        order = sorted(group, key=odds_key) if by == 'odds' else sorted(group, key=lambda a: (a['adj'] is None, a['adj'] or 0))
        for rk, a in enumerate(order, 1):
            tc = ', '.join('%s%s' % (esc(nm), (' <span class="sm">(%s)</span>' % money(st)) if st else '') for nm, st in a['top_chase'][:3])
            out.append('<tr><td>%d</td><td><a href="#/b/%s"><b>%s</b></a><div class="sm">%s%s%s</div></td><td class="n">%s%s</td><td class="n">%s</td><td class="n">%s</td><td class="n">%s</td><td class="n">%s</td><td>%s</td></tr>' % (
                rk, a['id'], esc(a['title']), (esc(a['breaker']) + ' · ') if show_breaker else '', esc(a['when']), '' if a['star_cover'] >= 0.3 else ' · <span class="warn">few star prices yet</span>',
                money(a['entry']) or '', ('<div class="sm">%s%s</div>' % (esc(a['up_spot']['label']), ' <span class="warn">sold</span>' if a['up_spot']['status'] == 'sold' else '')) if a['up_spot'] else '',
                (('<b>%d%%</b>' if by == 'odds' else '%d%%') % round(a['chance'] * 100)) if a['chance'] else '<span class="na">n/a</span>',
                money(a['per_shot']), ('%.2fx' % a['up_value']) if a['up_value'] else '<span class="na">needs box cost</span>',
                money(a['adj']) if by == 'odds' else '<b>%s</b>' % money(a['adj']), tc))
        return ''.join(out)

    def hit_tables(group, show_breaker):
        return ('<div class="t-money">%s%s</tbody></table></div><div class="t-odds">%s%s</tbody></table></div>' % (
            head, hit_rows(group, show_breaker, 'money'), head, hit_rows(group, show_breaker, 'odds')))

    def best_line(group):
        bits = []
        rnd = sorted([a for a in group if not a['pick'] and a['adj']], key=lambda a: a['adj'])
        if rnd:
            r = rnd[0]
            bits.append('Best random break: <a href="#/b/%s"><b>%s</b></a>, %s a spot, %d%% chance at a top chase name, %s value for the price.' % (
                r['id'], esc(r['title']), money(r['entry']), round(r['chance'] * 100), ('%.2fx' % r['up_value']) if r['up_value'] else 'no'))
        od = sorted([a for a in group if a['chance'] and not a['pick']], key=odds_key)
        if od and (not rnd or od[0] is not rnd[0]):
            r = od[0]
            bits.append('Best odds at a big name: <a href="#/b/%s"><b>%s</b></a>, %d%% chance for %s a spot (%s per shot)%s.' % (
                r['id'], esc(r['title']), round(r['chance'] * 100), money(r['entry']), money(r['per_shot']),
                (', but only %.2fx value for the price' % r['up_value']) if r['up_value'] and r['up_value'] < 0.9 else ''))
        opens = sorted([(a, sp) for a in group if a['pick'] for sp in a['best_spots'] if sp['status'] != 'sold'], key=lambda x: (x[1]['value'] is None, -x[1]['score']))
        if opens:
            r, sp = opens[0]
            bits.append('Best open pick spot: <b>%s</b> in <a href="#/b/%s">%s</a> for %s (%.2fx hits for the price, %s value)%s.' % (
                esc(sp['label']), r['id'], esc(r['title']), money(sp['price']), sp['hit_deal'],
                ('%.2fx' % sp['value']) if sp['value'] else 'not yet scored for', (', holds ' + esc(', '.join(sp['big'][:2]))) if sp['big'] else ''))
        ranked_g = sorted([a for a in group if a['adj']], key=lambda a: a['adj'])
        lnk = lambda a: '<a href="#/b/%s">%s</a>' % (a['id'], esc(a['title']))
        nxt = [a for a in rnd[1:3] if not (len(ranked_g) > 2 and a is ranked_g[-1])]
        if nxt:
            bits.append('Next: %s.' % ', then '.join(lnk(a) for a in nxt))
        if len(ranked_g) > 2:
            w = ranked_g[-1]
            hi = max(ranked_g, key=lambda a: a['chance'] or 0)
            if od and w is od[0] and w['up_value']:
                bits.append('Last for the money: %s, because of the price (%.2fx value), even with the best odds.' % (lnk(w), w['up_value']))
            elif w is hi and w['up_value'] and w['up_value'] < 0.9:
                bits.append('Last: %s has the best odds at a big name here (%d%%), but at %s a spot it\'s overpriced (%.2fx value).' % (lnk(w), round(w['chance'] * 100), money(w['entry']), w['up_value']))
            else:
                bits.append('Last: %s, %s.' % (lnk(w), 'mostly on price (%.2fx value)' % w['up_value'] if w['up_value'] and w['up_value'] < 0.75 else 'with the lowest odds at a top chase name for its price'))
        for a in group:
            if a['up_spot'] and a['up_spot']['status'] == 'sold' and ranked_g and a is ranked_g[0]:
                bits.append('Ranks first, but its best spot is already sold: %s for %s%s.' % (esc(a['up_spot']['label']), money(a['up_spot']['price']),
                    (', holding ' + esc(a['up_spot']['big'][0])) if a['up_spot']['big'] else ''))
        over = [a for a in rnd if a['up_value'] and a['up_value'] >= 1.0]
        if over:
            bits.append('Worth more than the price: %s.' % ', '.join('%s (%.2fx)' % (lnk(a), a['up_value']) for a in over))
        gaps = [a for a in group if not a['up_value']] 
        thin = [a for a in group if a['star_cover'] < 0.3]
        if gaps: bits.append('Not fully scored yet: %s (no box cost).' % ', '.join(lnk(a) for a in gaps))
        if thin: bits.append('Few star prices so far for %s, so treat those rankings loosely.' % ', '.join(lnk(a) for a in thin))
        return ('<div class="picks takeaways"><div><span>What this means</span><ul>%s</ul></div></div>' % ''.join('<li>%s</li>' % b for b in bits)) if bits else ''

    groups = [(nm, [a for a in breaks if a['breaker'] == nm]) for nm in BREAKER.values()]
    groups = [(nm, g) for nm, g in groups if g]
    hp = ['<h2>Hit potential</h2><p class="lede">%s</p><p>%s</p>' % (lede, ' · '.join(
        '<a href="#/hits/%s">%s (%d)</a>' % (re.sub(r'[^a-z]', '', nm.lower()), esc(nm), len(g)) for nm, g in groups))]
    hp.append('<div class="hsort"><span>Rank by</span><button type="button" data-s="money">Best for the money</button><button type="button" data-s="odds">Best odds</button>'
              '<span class="sm t-money">Lowest adjusted cost first.</span><span class="sm t-odds">Highest chance at a top chase name first, whatever the price. Pick-your-spot breaks show 100% when you can buy a spot that holds one.</span></div>')
    for nm, g in groups:
        hp.append('<h3 id="h-%s">%s</h3>%s%s' % (re.sub(r'[^a-z]', '', nm.lower()), esc(nm), best_line(g), hit_tables(g, False)))
    hp.append('<h3>All breakers together</h3>%s' % hit_tables(breaks, True))
    hp.append('<p class="sm">Star power comes from eBay asking prices, so it sharpens as the daily lookup fills in. A break marked "few star prices yet" is ranked mostly by checklist depth.</p>')
    secs.append(('hits', 'Hit potential', ''.join(hp)))

    bl = ['<h2>Current breaks</h2><p class="lede">Open one to see every spot, what it\'s worth for the price, and what data is missing.</p><div class="list">']
    for a in breaks:
        bl.append('<a class="item" href="#/b/%s"><b>%s</b><span>%s</span><span>%s</span><span class="conf %s">%s confidence</span></a>' % (
            a['id'], esc(a['title']), esc(a['when']), esc(verdict(a)), a['conf'].lower(), a['conf']))
    bl.append('</div>')
    secs.append(('breaks', 'Breaks', ''.join(bl)))
    for a in breaks:
        h = ['<p><a href="#/breaks">&lsaquo; All breaks</a></p><h2>%s</h2><p class="lede">%s · %s · <a href="/breaks/%s" target="_blank" rel="noopener">Open the guide</a>%s</p>' % (
            esc(a['title']), esc(a['breaker']), esc(a['when']), a['id'], (' · <a href="%s" target="_blank" rel="noopener">Breaker\'s listing</a>' % esc(a['url'])) if a['url'] else '')]
        h.append('<div class="stats"><div><b>%s</b><span>%s</span></div><div><b>%s</b><span>box cost%s</span></div><div><b>%s</b><span>markup over box cost</span></div><div><b>%s</b><span>confidence</span></div></div>' % (
            money(a['total']) or 'unknown', ('%d spots at %s' % (a['sold'], money(a['flat']))) if a['flat'] else ('all %d spot prices added up' % a['sold']),
            money(a['box_cost']) or ((money(a['box_cost_partial']) + ' so far') if a['box_cost_partial'] else 'not yet'), '' if a['box_cost'] else ' (some boxes missing)',
            ('%+d%%' % round((a['markup'] - 1) * 100)) if a['markup'] else 'n/a', a['conf']))
        if not a['pick'] and a['fair_spot'] and a['flat']:
            tip = 'In a random break every spot is the same ticket, so it comes down to the price: a fair spot would cost about %s, and this one is %s.' % (money(a['fair_spot']), money(a['flat']))
        elif a['pick'] and a['box_cost']:
            tip = 'Look for spots whose fair price is above what they sell for (green below).'
        else:
            tip = 'Once the sealed box prices come in, this shows a fair price for %s.' % ('each spot' if a['pick'] else 'a spot')
        h.append('<p><b>%s.</b> %s</p>' % (esc(verdict(a)), tip))
        h.append('<h3>Boxes and data</h3><table><thead><tr><th>Box</th><th>Checklist</th><th>Pack odds</th><th class="n">eBay player prices</th><th class="n">Box cost (lowest found)</th></tr></thead><tbody>')
        for bx in a['boxes']:
            h.append('<tr><td>%s</td><td>%s</td><td>%s</td><td class="n">%s</td><td class="n">%s</td></tr>' % (
                esc(bx['full']), ('<span class="ok">official</span>' if bx['official'] else '<span class="warn">copied from a website</span>') if bx['pid'] else '<span class="bad">not linked</span>',
                '<span class="ok">yes</span>' if bx['odds'] else '<span class="warn">no</span>',
                ('%d of %d names' % (bx['priced'], bx['names'])) if bx['names'] else '',
                box_cell(bx)))
        h.append('</tbody></table>')
        basis = 'eBay player prices' if a['market'] else 'the checklists (hit depth)'
        if a['top_chase']:
            h.append('<h3>Biggest chase names</h3><p>%s</p>' % ', '.join('%s%s' % (esc(nm), (' <span class="sm">(eBay about %s)</span>' % money(st)) if st else '') for nm, st in a['top_chase']))
        if a['best_spots']:
            h.append('<h3>Best spots to buy into</h3><p class="sm">Every spot ranked, sold or not, on two things together: its share of the hits for its price, and its value for the price overall. 1.00x is fair for both.</p>'
                     '<table><thead><tr><th>#</th><th>Spot</th><th class="n">Price</th><th class="n">Hits for the price</th><th class="n">Value for the price</th><th>Big chase names</th><th>Status</th></tr></thead><tbody>')
            for i, sp in enumerate(a['best_spots'], 1):
                h.append('<tr><td>%d</td><td><b>%s</b>%s</td><td class="n">%s</td>%s%s<td>%s</td><td>%s</td></tr>' % (
                    i, esc(sp['label']), (' <span class="tag">%s</span>' % esc(sp['sub'])) if sp['sub'] else '', money(sp['price']),
                    deal_cell(sp['hit_deal']), deal_cell(sp['value']), esc(', '.join(sp['big'][:3])) or '<span class="na">none of the top 10</span>',
                    '<span class="warn">sold</span>' if sp['status'] == 'sold' else '<span class="ok">open</span>' if sp['status'] in ('open', 'avail', 'available') else esc(sp['status'] or 'not tracked')))
            h.append('</tbody></table>')
        h.append('<h3>Spots</h3><p class="sm">Value share comes from %s.%s</p>' % (basis, '' if a['market'] else ' It switches to eBay player prices once at least half the points have one (now %d%%).' % round(a['cover'] * 100)))
        rows = sorted(a['spots'], key=lambda s: -s['hit_ratio'])
        h.append('<p class="sm"><b>Hit rating</b> ranks each spot by the hits it could bring: its players\' autographs, inserts and multi-player cards, each counted by how much that player\'s cards sell for on eBay, so the more valuable the players, the bigger the possible hit. '
                 '3 stars is an average spot for this break; 5 stars holds at least twice the average hit value. <b>Biggest possible hit</b> is the spot\'s most valuable autograph name, with that player\'s typical eBay asking price.</p>')
        h.append('<table><thead><tr><th>Spot</th><th>Hit rating</th><th>Biggest possible hit</th><th class="n">Price</th><th class="n">Value share</th><th class="n">Fair price</th><th class="n">Value for the price</th></tr></thead><tbody>')
        for s in rows:
            stars = '<span class="stars" title="%.1fx the average spot">%s<span class="off">%s</span></span><div class="sm">%.1fx average</div>' % (s['hit_ratio'], '&#9733;' * s['stars'], '&#9733;' * (5 - s['stars']), s['hit_ratio'])
            hn = ', '.join(esc(nm) + (' <span class="sm">(%s)</span>' % money(st) if st else '') for nm, st, au in s['hit_names'])
            ceil = ('<b>%s</b><div class="sm">eBay about %s</div>' % (esc(s['ceiling'][1]), money(s['ceiling'][0]))) if s['ceiling'] else '<span class="na">no priced autograph</span>'
            h.append('<tr><td><b>%s</b>%s%s<div class="sm">%s</div></td><td>%s</td><td>%s</td><td class="n">%s</td><td class="n">%.1f%%</td><td class="n">%s</td>%s</tr>' % (
                esc(s['label']), (' <span class="tag">%s</span>' % esc(s['sub'])) if s['sub'] else '', ' <span class="warn">sold</span>' if a['pick'] and s['status'] == 'sold' else '',
                hn or esc(', '.join(s['top'])), stars, ceil,
                money(s['price']) or '&nbsp;', s['share'] * 100, money(s['fair']) or '<span class="na">needs box cost</span>',
                deal_cell(s['deal']) if a['pick'] else '<td class="r na">random</td>'))
        h.append('</tbody></table>')
        if a['miss']:
            h.append('<h3>What\'s missing</h3><ul class="miss">%s</ul>' % ''.join('<li>%s</li>' % esc(t) for _, t in a['miss']))
        secs.append(('b/' + a['id'], None, ''.join(h)))

    lab = dict(box=('Box prices', 'The weekly price check looks for these. If one stays missing, tell me what that box sells for.'),
               prices=('eBay player prices', 'Fills in over a few days (about 4,500 names a day).'),
               odds=('Pack odds', 'Send the odds sheet (usually on the maker\'s checklist page) and the hit weights get sharper.'),
               source=('Checklists copied from websites', 'An official checklist file from the maker would replace these.'),
               checklist=('Boxes with no checklist', 'Send the checklist and the box gets counted.'),
               price=('Breaks with no spot price', 'Check the listing; the price may be on a variant.'))
    ms = ['<h2>What\'s missing</h2><p class="lede">Everything the numbers are waiting on, so you can help fill the gaps.</p>']
    for kind in ('box', 'prices', 'odds', 'source', 'checklist', 'price'):
        items = missing_all.get(kind)
        if not items: continue
        ms.append('<h3>%s (%d)</h3><p class="sm">%s</p><ul class="miss">%s</ul>' % (lab[kind][0], len(items), lab[kind][1], ''.join(
            '<li><a href="#/b/%s">%s</a>: %s</li>' % (a['id'], esc(a['title']), esc(t)) for a, t in items)))
    secs.append(('missing', 'Missing', ''.join(ms)))

    pr = ['<h2>How the numbers work</h2>',
          '<div class="stats"><div><b>%s</b><span>names in current breaks</span></div><div><b>%s</b><span>looked up on eBay</span></div><div><b>%s</b><span>with a price</span></div><div><b>%s</b><span>latest lookup</span></div></div>' % (
              format(len([t for t in targets if not t.get('box')]), ','), format(len(PR), ','), format(have, ','),
              datetime.date.fromisoformat(pdates[-1]).strftime('%B %-d, %Y') if pdates else 'none yet'),
          '<ul><li><b>Break total:</b> every spot\'s price added up for pick-your-spot breaks; the spot price times the number of spots sold for random breaks. Fillers aren\'t counted.</li>'
          '<li><b>Box cost:</b> the lowest price found for one sealed box (shops, StockX and eBay Buy It Now, before shipping and tax), times the number of boxes. A scheduled task checks these every week (prices as of BOXDATE). When a box has no web price, the typical eBay Buy It Now asking price from the daily lookup fills in. Breakers often pay less than this by buying whole cases.</li>'
          '<li><b>Markup:</b> break total compared with box cost. Breakers usually charge something over box cost for their time, shipping and the stream.</li>'
          '<li><b>Value share:</b> each name gets points for its cards in each box (base 1, autograph 2, insert 0.5, multi-person 0.5). Autograph, insert and multi points grow with how many of those sets the player is in, weighted by pack odds where we have them. With enough eBay player prices, points are also multiplied by each player\'s typical asking price.</li>'
          '<li><b>Fair price:</b> a spot\'s value share of the box cost. It assumes the cards in the boxes are worth about what the sealed boxes cost, which is roughly true on average and never for any one box.</li>'
          '<li><b>Value for the price:</b> fair price divided by the spot\'s price. 1.00x is fair, 1.20x or more (green) is a good deal, 0.85x or less (red) is a poor one.</li>'
          '<li><b>Confidence:</b> high when the box costs, eBay player prices, official checklists and pack odds are all in; lower as each is missing.</li></ul>']
    secs.append(('how', 'How it works', ''.join(pr).replace('BOXDATE', datetime.date.fromisoformat(BP['updated']).strftime('%B %-d, %Y') if BP.get('updated') else 'not yet')))
    secs.append(('pulls', 'Pulls', '<h2>Pulls from streams</h2><p class="lede">Coming next: hits called out on each breaker\'s stream, matched to the checklist, so we can see what actually comes out of each product next to what the values say should.</p>'))

    nav = ''.join('<a href="#/%s" data-v="%s">%s</a>' % (k, k, t) for k, t, _ in secs if t)
    owner_menu = ('<details class="om"><summary>Owner &#9662;</summary><div class="omenu">'
                  '<b>Dashboard</b><a href="#/overview">Overview</a><a href="#/breaks">Breaks</a><a href="#/missing">What\'s missing</a><a href="#/how">How it works</a><a href="#/pulls">Pulls</a>'
                  '<b>Site</b><a href="/">Main Event Card Vault store</a><a href="/breaks/">Break guides</a><a href="/breaks/builder">Spot builder</a><a href="/breaks/past">Past breaks</a><a href="/breaks/release-notes">Release notes</a><a href="/iron-ledger">Iron Ledger</a>'
                  '<b>Behind the scenes</b><a href="https://dash.cloudflare.com/%s/workers/services/view/maineventcardvault/production" target="_blank" rel="noopener">Cloudflare (site hosting)</a>'
                  '<a href="https://github.com/dastardly-dan/maineventcardvault/actions" target="_blank" rel="noopener">GitHub jobs (watcher, prices)</a>'
                  '<a href="https://www.ebay.com/sh/ovw" target="_blank" rel="noopener">eBay Seller Hub</a>'
                  '<a href="https://www.ebay.com/str/maineventcardvault" target="_blank" rel="noopener">eBay store</a>'
                  '<a href="/owner/logout">Sign out</a></div></details>') % ACCOUNT
    body = ''.join('<section data-v="%s" hidden>%s</section>' % (k, c) for k, _, c in secs)
    built = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).strftime('%B %-d, %Y at %-I:%M %p Eastern')
    page = '''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Developer dashboard | Main Event Card Vault</title>
<style>
:root{--bg:#f6f4ef;--panel:#fff;--ink:#14202e;--ink2:#46505c;--ink3:#7a838d;--line:#e2ddd2;--gold:#b8902c;--up:#2e8b57;--dn:#b5543c}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
header{position:sticky;top:0;background:#14202e;color:#fff;z-index:5}header .w{display:flex;flex-wrap:wrap;align-items:center;gap:6px 14px;padding:10px 18px}
header .brand{color:#e6c766;letter-spacing:.06em;text-transform:uppercase;font-size:13px;font-weight:700}header nav{display:flex;gap:4px;flex-wrap:wrap}
header nav a{color:#d7dde4;text-decoration:none;padding:5px 10px;border-radius:8px;font-size:14px}header nav a.on{background:#e6c766;color:#14202e;font-weight:700}
header input{margin-left:auto;padding:6px 10px;border-radius:8px;border:0;min-width:200px;font:inherit;font-size:14px}
.om{position:relative}.om summary{list-style:none;cursor:pointer;color:#14202e;background:#e6c766;border-radius:8px;padding:5px 12px;font-weight:700;font-size:14px}.om summary::-webkit-details-marker{display:none}
.omenu{position:absolute;right:0;top:36px;background:#fff;color:var(--ink);border:1px solid var(--line);border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.25);padding:8px;min-width:250px;display:flex;flex-direction:column}
.omenu b{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink3);padding:8px 8px 2px}.omenu a{color:var(--ink);text-decoration:none;padding:6px 8px;border-radius:6px;font-size:14px}.omenu a:hover{background:#f3ead0}
main{max-width:1150px;margin:0 auto;padding:18px}h2{margin:6px 0 4px}h3{margin:22px 0 6px}.lede{color:var(--ink2);margin:0 0 14px}.sm{color:var(--ink3);font-size:12.5px}
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin:8px 0 18px}
th{text-align:left;font-size:12px;color:var(--ink3);font-weight:600;padding:8px 10px;border-bottom:1px solid var(--line);background:#faf8f3}td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.n{text-align:right;white-space:nowrap}.r{text-align:right;font-weight:700;white-space:nowrap}.r.up{color:var(--up)}.r.dn{color:var(--dn)}.na{color:var(--ink3);font-weight:400;font-size:13px}
.tag{font-size:11px;border:1px solid var(--line);border-radius:999px;padding:0 6px;color:var(--ink2)}
.ok{color:var(--up)}.warn{color:#a6761d}.bad{color:var(--dn)}
.conf{font-size:12px;font-weight:700;border-radius:999px;padding:1px 8px;white-space:nowrap}.conf.high{background:#e3f3e9;color:var(--up)}.conf.medium{background:#f7efd9;color:#8a6a14}.conf.low{background:#f6e3de;color:var(--dn)}
.picks{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px;margin:6px 0 18px}.picks>div{background:var(--panel);border:1px solid var(--line);border-left:4px solid #3ccf9a;border-radius:10px;padding:10px 12px}.takeaways{grid-template-columns:1fr}.takeaways ul{margin:4px 0 0;padding-left:18px}.takeaways li{margin:3px 0}
.stars{color:#d4a72c;font-size:16px;letter-spacing:1px;white-space:nowrap}.stars .off{color:#c9ced8;opacity:.5}
.hsort{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;margin:4px 0 6px;position:sticky;top:52px;z-index:3;background:var(--bg);padding:6px 0}.hsort>span:first-child{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--ink3)}
.hsort button{font:inherit;font-size:14px;border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:999px;padding:4px 12px;cursor:pointer}.hsort button.on{background:#14202e;color:#fff;border-color:#14202e}
body:not(.hodds) .t-odds,body.hodds .t-money{display:none}
.picks span{display:block;font-size:12px;text-transform:uppercase;letter-spacing:.04em;opacity:.7;margin-bottom:4px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:8px 0 18px}.stats div{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.stats b{display:block;font-size:22px}.stats span{color:var(--ink3);font-size:13px}
.list{display:grid;gap:8px}.item{display:grid;grid-template-columns:1.4fr 1fr 1fr auto;gap:12px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px;color:var(--ink);text-decoration:none}
.item span{font-size:13px;color:var(--ink2)}@media(max-width:760px){.item{grid-template-columns:1fr}header input{min-width:0;width:100%}table{display:block;overflow-x:auto}}
.miss li{margin:4px 0;color:var(--ink2)}a{color:#8a6a14}footer{max-width:1150px;margin:0 auto;padding:0 18px 30px;color:var(--ink3);font-size:12.5px}
</style></head><body><header><div class="w"><span class="brand">Developer dashboard</span><nav>__NAV__</nav><input id="q" type="search" placeholder="Search breaks, spots, names">__OWNER__</div></header>
<main>__BODY__<section data-v="search" hidden><h2>Search</h2><div id="res"></div></section></main>
<footer>Updated __BUILT__. Values come from eBay asking prices and checklist points. They're a guide for deciding, not a promise of what comes out of the box.</footer>
<script>
(function(){var S=[].slice.call(document.querySelectorAll("main section")),N=[].slice.call(document.querySelectorAll("header nav a")),q=document.getElementById("q"),om=document.querySelector(".om");
function show(v){S.forEach(function(s){s.hidden=s.getAttribute("data-v")!==v});var top=v.indexOf("b/")===0?"breaks":v;N.forEach(function(a){a.classList.toggle("on",a.getAttribute("data-v")===top)});if(om)om.open=false;window.scrollTo(0,0)}
function route(){var v=(location.hash.replace(/^#\\/?/,"")||"overview");if(v.indexOf("search/")===0){q.value=decodeURIComponent(v.slice(7));search(q.value);v="search"}
var jump=null;if(v.indexOf("hits/")===0){jump="h-"+v.slice(5);v="hits"}
if(!S.some(function(s){return s.getAttribute("data-v")===v}))v="overview";show(v);if(jump){var j=document.getElementById(jump);if(j)j.scrollIntoView()}}
function search(t){t=t.trim().toLowerCase();var out=[];if(t)S.forEach(function(s){var v=s.getAttribute("data-v");if(v==="search"||v==="overview")return;var h=s.querySelector("h2");
[].forEach.call(s.querySelectorAll("tbody tr, li"),function(tr){if(tr.textContent.toLowerCase().indexOf(t)>-1)out.push('<tr><td><a href="#/'+v+'">'+(h?h.textContent:v)+"</a></td><td>"+tr.innerHTML+"</td></tr>")})});
document.getElementById("res").innerHTML=t?(out.length?"<table><tbody>"+out.slice(0,200).join("")+"</tbody></table>":'<p class="na">Nothing matches.</p>'):""}
var tm;q.addEventListener("input",function(){clearTimeout(tm);tm=setTimeout(function(){var v=q.value.trim();history.replaceState(null,"",v?"#/search/"+encodeURIComponent(v):"#/overview");route()},150)});
document.addEventListener("click",function(e){if(om&&om.open&&!om.contains(e.target))om.open=false});
var HS=[].slice.call(document.querySelectorAll(".hsort button"));function hsort(m){document.body.classList.toggle("hodds",m==="odds");HS.forEach(function(b){b.classList.toggle("on",b.getAttribute("data-s")===m)})}
var hm="money";try{hm=localStorage.getItem("mecv-hsort")||"money"}catch(e){}hsort(hm);HS.forEach(function(b){b.addEventListener("click",function(){var m=b.getAttribute("data-s");hsort(m);try{localStorage.setItem("mecv-hsort",m)}catch(e){}})});
window.addEventListener("hashchange",route);route()})();
</script></body></html>'''
    page = page.replace('__NAV__', nav).replace('__BODY__', body).replace('__BUILT__', built).replace('__OWNER__', owner_menu)
    out = os.path.join(ROOT, 'owner')
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'dashboard.js'), 'w', encoding='utf-8').write(
        '// Built by build/breaks/owner.py. Served by worker.js at /owner, only after the password check.\nexport const DASHBOARD = ' + json.dumps(page, ensure_ascii=False) + ';\n')
    print('owner dashboard', len(breaks), 'breaks,', sum(1 for a in breaks if a['market']), 'with eBay player values,',
          sum(1 for a in breaks if a['box_cost']), 'with box costs,', len(page), 'bytes')
    return breaks


if __name__ == '__main__':
    for a in main():
        print('  %-8s %-6s sold %-3s total %-8s conf %-6s unlinked %s' % (a['id'], 'pick' if a['pick'] else 'random', a['sold'], money(a['total']), a['conf'],
              [x['full'] for x in a['boxes'] if not x['pid']]))
