"""Daniel's private dashboard at maineventcardvault.com/owner (Daniel, Nov 27, 2026).

For every current break guide, works out each spot's share of the break's value: each name's points in each box
(base 1, autograph 2, insert 0.5, multi-person 0.5, the Spot Builder's defaults) times its typical eBay asking price
from watch/prices.json, with unpriced names counted at the break's typical price. Then compares that share with
what the spot costs, so the best value spots stand out.

Writes owner/dashboard.js (one self-contained page as a string). worker.js serves it only after the password check,
and .assetsignore keeps the owner folder from being published as a plain file. hub.py runs this at the end.

  python3 build/breaks/owner.py
"""
import datetime, html, json, os, re, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
W = {'B': 1.0, 'A': 2.0, 'I': 0.5, 'M': 0.5}
MIN_COVER = 0.5   # priced names must hold this share of the points before a break's values are shown


def key_of(name):
    return ' '.join(re.sub(r'"[^"]*"', '', name).split())


def box_query(full):   # same as build.py's box_query
    q = re.sub(r'\(.*?\)', '', full)
    q = re.sub(r'\b(Hobby|Jumbo|Mega|Blaster|Value|Boxes|Box|Case|Breaker\'s Delight)\b', '', q)
    return ' '.join(q.split())


def box_count(full):
    m = re.search(r'\((\d+)\s+box', full)
    return int(m.group(1)) if m else 1


def page_data(pid):
    p = os.path.join(ROOT, 'breaks', pid + '.html')
    if not os.path.exists(p): return None
    h = open(p, encoding='utf-8').read()
    if 'var D = ' not in h: return None
    i = h.index('var D = '); j = h.index('{', i)
    return json.JSONDecoder().raw_decode(h[j:])[0]


def flat_price(D):
    for f in D.get('facts', []):
        m = re.search(r'\$([\d,]+(?:\.\d+)?) (?:per|a) spot', f)
        if m: return float(m.group(1).replace(',', ''))
    return None


def analyze(D, PR):
    boxes = {b['k']: b for b in D['boxes']}
    q = {k: box_query(b['full']) for k, b in boxes.items()}
    n = {k: box_count(b['full']) for k, b in boxes.items()}
    rows = []   # (spot index, weight, price or None)
    for si, s in enumerate(D['spots']):
        for bk, ents in D['names'].get(s['id'], {}).items():
            if bk not in boxes: continue
            for e in ents:
                w = sum(W.get(c, 0) for c in set(e[1] or 'B')) * n[bk]
                if not w: continue
                v = PR.get(q[bk] + ' ' + key_of(e[0]))
                rows.append((si, w, v[0] if v and v[0] else None, e[0]))
    tw = sum(r[1] for r in rows) or 1
    priced = [r for r in rows if r[2]]
    cover = sum(r[1] for r in priced) / tw
    ref = statistics.median([r[2] for r in priced]) if priced else 0
    spots = [{'label': s['label'], 'sub': s.get('g') or '', 'price': s.get('price'), 'pts': 0.0, 'val': 0.0, 'top': {}} for s in D['spots']]
    for si, w, px, nm in rows:
        sp = spots[si]; sp['pts'] += w; v = w * (px or ref); sp['val'] += v; sp['top'][nm] = sp['top'].get(nm, 0) + v
    tv = sum(s['val'] for s in spots) or 1
    fp = flat_price(D)
    prices = [s['price'] or fp for s in spots]
    known = [p for p in prices if p]
    tp = sum(known) if len(known) == len(spots) else None
    for s, p in zip(spots, prices):
        s['vs'] = s['val'] / tv; s['ps'] = s['pts'] / tw; s['cost'] = p
        # how much value the spot holds for what it costs: 1.0 is a fair price, 2.0 is twice the value
        s['ratio'] = (s['vs'] / (p / tp)) if tp else s['vs'] * len(spots)
        s['top'] = [nm for nm, v in sorted(s['top'].items(), key=lambda x: -x[1])[:5]]
    return {'cover': cover, 'priced': len(priced), 'names': len(rows), 'ok': cover >= MIN_COVER and len(priced) >= 8,
            'spots': spots, 'total_cost': tp}


def esc(t):
    return html.escape(str(t), quote=True)


def money(x):
    return '' if x is None else ('$%s' % format(round(x), ','))


def main():
    PR = json.load(open(os.path.join(HERE, 'watch', 'prices.json'), encoding='utf-8'))
    idx = json.load(open(os.path.join(HERE, 'index.json'), encoding='utf-8'))
    hub = open(os.path.join(HERE, 'hub.py'), encoding='utf-8').read()
    order = re.findall(r"'([a-z0-9]+)'", re.search(r"order\s*=\s*\[(.*?)\]", hub, re.S).group(1))
    cur = [b for b in idx if not b.get('ended')]
    cur.sort(key=lambda b: order.index(b['id']) if b['id'] in order else 999)
    dates = sorted(v[3] for v in PR.values() if v)
    targets = json.load(open(os.path.join(HERE, 'watch', 'price_targets.json'), encoding='utf-8'))
    have = sum(1 for v in PR.values() if v and v[0])

    breaks, best = [], []
    for b in cur:
        D = page_data(b['id'])
        if not D or not D.get('spots') or not D.get('names'): continue
        a = analyze(D, PR); a['id'] = b['id']; a['title'] = D['title']; a['when'] = D.get('when', '').split('. ')[0]
        a['format'] = D.get('format', ''); breaks.append(a)
        if a['ok']:
            for s in a['spots']:
                best.append((s['ratio'], a, s))
    best.sort(key=lambda x: -x[0])

    def ratio_cell(r):
        cls = 'up' if r >= 1.25 else 'dn' if r <= 0.8 else ''
        return '<td class="r %s">%.2fx</td>' % (cls, r)

    def spot_table(a):
        if not a['ok']:   # too few prices: show the spots by points only, no value columns
            body = ''.join('<tr><td><b>%s</b>%s<div class="sm">%s</div></td><td class="n">%s</td><td class="n">%.1f%%</td></tr>' % (
                esc(s['label']), (' <span class="tag">%s</span>' % esc(s['sub'])) if s['sub'] else '', esc(', '.join(s['top'])),
                money(s['cost']) or '&nbsp;', s['ps'] * 100) for s in sorted(a['spots'], key=lambda s: -s['ps']))
            return '<table><thead><tr><th>Spot</th><th class="n">Cost</th><th class="n">Points</th></tr></thead><tbody>%s</tbody></table>' % body
        rows = sorted(a['spots'], key=lambda s: -s['ratio'])
        body = ''.join('<tr><td><b>%s</b>%s<div class="sm">%s</div></td><td class="n">%s</td><td class="n">%.1f%%</td><td class="n">%.1f%%</td>%s</tr>' % (
            esc(s['label']), (' <span class="tag">%s</span>' % esc(s['sub'])) if s['sub'] else '', esc(', '.join(s['top'])),
            money(s['cost']) or '&nbsp;', s['ps'] * 100, s['vs'] * 100, ratio_cell(s['ratio'])) for s in rows)
        return ('<table><thead><tr><th>Spot</th><th class="n">Cost</th><th class="n">Points</th><th class="n">Value</th><th class="n">Value for cost</th></tr></thead><tbody>%s</tbody></table>' % body)

    secs = []
    # overview
    top = best[:15]
    ov = ['<h2>Best value spots right now</h2><p class="lede">Across every current break with enough eBay prices. "Value for cost" of 1.00x is a fair price; 2.00x means the spot holds twice the value of what it costs, going by typical asking prices.</p>']
    if top:
        ov.append('<table><thead><tr><th>Spot</th><th>Break</th><th class="n">Cost</th><th class="n">Value</th><th class="n">Value for cost</th></tr></thead><tbody>' + ''.join(
            '<tr><td><b>%s</b><div class="sm">%s</div></td><td><a href="#/b/%s">%s</a><div class="sm">%s</div></td><td class="n">%s</td><td class="n">%.1f%%</td>%s</tr>' % (
                esc(s['label']), esc(', '.join(s['top'][:3])), a['id'], esc(a['title']), esc(a['when']), money(s['cost']) or '&nbsp;', s['vs'] * 100, ratio_cell(r))
            for r, a, s in top) + '</tbody></table>')
    else:
        ov.append('<p class="empty">No current break has enough eBay prices yet. Prices fill in each day.</p>')
    ok = [a for a in breaks if a['ok']]; wait = [a for a in breaks if not a['ok']]
    ov.append('<div class="stats"><div><b>%d</b><span>current breaks</span></div><div><b>%d</b><span>with values</span></div><div><b>%d</b><span>waiting on prices</span></div><div><b>%s</b><span>names with an eBay price</span></div></div>' % (
        len(breaks), len(ok), len(wait), format(have, ',')))
    secs.append(('overview', 'Overview', ''.join(ov)))
    # each break
    bl = ['<h2>Current breaks</h2><div class="list">']
    for a in breaks:
        bl.append('<a class="item" href="#/b/%s"><b>%s</b><span>%s</span><span class="%s">%s</span></a>' % (
            a['id'], esc(a['title']), esc(a['when']), 'ok' if a['ok'] else 'wait',
            ('Values ready, %d%% of points priced' % round(a['cover'] * 100)) if a['ok'] else ('Waiting on prices, %d%% of points priced' % round(a['cover'] * 100))))
    bl.append('</div>')
    secs.append(('breaks', 'Breaks', ''.join(bl)))
    for a in breaks:
        h = ['<p><a href="#/breaks">&lsaquo; All breaks</a></p><h2>%s</h2><p class="lede">%s · <a href="/breaks/%s" target="_blank" rel="noopener">Open the guide</a></p>' % (
            esc(a['title']), esc(a['when']), a['id'])]
        h.append('<p class="sm">%d of %d names in this break have an eBay price, holding %d%% of the points.%s</p>' % (
            a['priced'], a['names'], round(a['cover'] * 100),
            '' if a['ok'] else ' Values show once priced names hold at least half the points. Until then the spots are listed by points only.'))
        h.append(spot_table(a))
        secs.append(('b/' + a['id'], None, ''.join(h)))
    # prices
    pr = ['<h2>eBay price data</h2><p class="lede">Typical Buy It Now asking prices for each player\'s cards from the same product, looked up once a day by the price job. Asking prices, not sales.</p>',
          '<div class="stats"><div><b>%s</b><span>names in current breaks</span></div><div><b>%s</b><span>looked up</span></div><div><b>%s</b><span>with a price</span></div><div><b>%s</b><span>latest lookup</span></div></div>' % (
              format(len(targets), ','), format(len(PR), ','), format(have, ','),
              datetime.date.fromisoformat(dates[-1]).strftime('%B %-d, %Y') if dates else 'none yet')]
    pr.append('<h3>How value is worked out</h3><ul><li>Each name gets points for its cards in each box: base 1, autograph 2, insert 0.5, multi-person 0.5, times the number of boxes.</li><li>Points times that player\'s typical asking price is the name\'s value. Names with no price count at the break\'s typical price.</li><li>A spot\'s value is its names added up, shown as a share of the whole break.</li><li>Value for cost compares that share with the spot\'s share of what all the spots cost (or, when every spot costs the same, with an even share).</li></ul>')
    secs.append(('prices', 'Prices', ''.join(pr)))
    secs.append(('pulls', 'Pulls', '<h2>Pulls from streams</h2><p class="lede">Coming next: hits called out on each breaker\'s stream, matched to the checklist, so we can see what actually comes out of each product next to what the values say should.</p>'))

    nav = ''.join('<a href="#/%s" data-v="%s">%s</a>' % (k, k, t) for k, t, _ in secs if t)
    body = ''.join('<section data-v="%s" hidden>%s</section>' % (k, c) for k, _, c in secs)
    built = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).strftime('%B %-d, %Y at %-I:%M %p Eastern')
    page = '''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Owner dashboard | Main Event Card Vault</title>
<style>
:root{--bg:#f6f4ef;--panel:#fff;--ink:#14202e;--ink2:#46505c;--ink3:#7a838d;--line:#e2ddd2;--gold:#b8902c;--up:#2e8b57;--dn:#b5543c}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
header{position:sticky;top:0;background:#14202e;color:#fff;z-index:5}header .w{display:flex;flex-wrap:wrap;align-items:center;gap:6px 16px;padding:10px 18px}
header b{color:#e6c766;letter-spacing:.06em;text-transform:uppercase;font-size:13px}header nav{display:flex;gap:4px;flex-wrap:wrap}
header nav a{color:#d7dde4;text-decoration:none;padding:5px 10px;border-radius:8px;font-size:14px}header nav a.on{background:#e6c766;color:#14202e;font-weight:700}
header input{margin-left:auto;padding:6px 10px;border-radius:8px;border:0;min-width:200px;font:inherit;font-size:14px}header .out{color:#9aa6b2;font-size:13px}
main{max-width:1100px;margin:0 auto;padding:18px}h2{margin:6px 0 4px}.lede{color:var(--ink2);margin:0 0 14px}.sm{color:var(--ink3);font-size:12.5px}
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin:8px 0 18px}
th{text-align:left;font-size:12px;color:var(--ink3);font-weight:600;padding:8px 10px;border-bottom:1px solid var(--line);background:#faf8f3}td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.n{text-align:right;white-space:nowrap}.r{text-align:right;font-weight:700;white-space:nowrap}.r.up{color:var(--up)}.r.dn{color:var(--dn)}
.tag{font-size:11px;border:1px solid var(--line);border-radius:999px;padding:0 6px;color:var(--ink2)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:8px 0 18px}.stats div{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.stats b{display:block;font-size:22px}.stats span{color:var(--ink3);font-size:13px}
.list{display:grid;gap:8px}.item{display:grid;grid-template-columns:1fr auto auto;gap:12px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px;color:var(--ink);text-decoration:none}
.item span{font-size:13px;color:var(--ink2)}.item .ok{color:var(--up)}.item .wait{color:var(--ink3)}@media(max-width:700px){.item{grid-template-columns:1fr}}
.empty{color:var(--ink3)}a{color:#8a6a14}footer{max-width:1100px;margin:0 auto;padding:0 18px 30px;color:var(--ink3);font-size:12.5px}
mark{background:#f3e3a6}
</style></head><body><header><div class="w"><b>Owner dashboard</b><nav>__NAV__</nav><input id="q" type="search" placeholder="Search spots, names, breaks"><a class="out" href="/owner/logout">Sign out</a></div></header>
<main>__BODY__<section data-v="search" hidden><h2>Search</h2><div id="res"></div></section></main>
<footer>Updated __BUILT__. Values come from typical eBay asking prices and checklist points. They're a guide, not a promise of what comes out of the box.</footer>
<script>
(function(){var S=[].slice.call(document.querySelectorAll("main section")),N=[].slice.call(document.querySelectorAll("header nav a")),q=document.getElementById("q");
function show(v){S.forEach(function(s){s.hidden=s.getAttribute("data-v")!==v});var top=v.indexOf("b/")===0?"breaks":v;N.forEach(function(a){a.classList.toggle("on",a.getAttribute("data-v")===top)});window.scrollTo(0,0)}
function route(){var v=(location.hash.replace(/^#\\/?/,"")||"overview");if(v.indexOf("search/")===0){q.value=decodeURIComponent(v.slice(7));search(q.value);v="search"}
if(!S.some(function(s){return s.getAttribute("data-v")===v}))v="overview";show(v)}
function search(t){t=t.trim().toLowerCase();var out=[];if(t)S.forEach(function(s){var v=s.getAttribute("data-v");if(v==="search")return;var h=s.querySelector("h2");
[].forEach.call(s.querySelectorAll("tbody tr"),function(tr){if(tr.textContent.toLowerCase().indexOf(t)>-1)out.push('<tr><td><a href="#/'+v+'">'+(h?h.textContent:v)+"</a></td>"+tr.innerHTML+"</tr>")})});
document.getElementById("res").innerHTML=t?(out.length?"<table><tbody>"+out.slice(0,200).join("")+"</tbody></table>":'<p class="empty">Nothing matches.</p>'):""}
var tm;q.addEventListener("input",function(){clearTimeout(tm);tm=setTimeout(function(){var v=q.value.trim();history.replaceState(null,"",v?"#/search/"+encodeURIComponent(v):"#/overview");route()},150)});
window.addEventListener("hashchange",route);route()})();
</script></body></html>'''
    page = page.replace('__NAV__', nav).replace('__BODY__', body).replace('__BUILT__', built)
    out = os.path.join(ROOT, 'owner')
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'dashboard.js'), 'w', encoding='utf-8').write(
        '// Built by build/breaks/owner.py. Served by worker.js at /owner, only after the password check.\nexport const DASHBOARD = ' + json.dumps(page, ensure_ascii=False) + ';\n')
    print('owner dashboard', len(breaks), 'breaks,', len(ok), 'with values,', len(page), 'bytes')


if __name__ == '__main__':
    main()
