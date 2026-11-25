import os
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'..','..'))
import json, re
css = open(os.path.join(HERE,'base.css')).read()
tpl = open(os.path.join(HERE,'template.html')).read()
icon = re.search(r'<link rel="icon" href="([^"]+)"', open(os.path.join(ROOT,'breaks','cc871.html')).read()).group(1)
items = json.load(open(os.path.join(HERE,'index.json')))
items.append(dict(id='cc874', title='CC874 Monster Multi: Random Letter', kicker='Colfax Collectibles · Random letter · Multi-sport', when='Ran Sunday, November 22, 2026', facts=['7 boxes', '21 letter spots'], ended='yes'))
order = ['cc871', 'cc872', 'cc874', 'cc875', 'jwj0246', 'jwj0247', 'jwj0244', 'gb1037', 'gb1038b', 'gb1038a', 'gb1040', 'rgl6128', 'rgl6129', 'rgl6130', 'rgl6131', 'rgl6132', 'rgl6133']
def is_past(i): return bool(i.get('ended')) or 'has passed' in i['when']
items.sort(key=lambda x: (is_past(x), order.index(x['id'])))
def esc(s): return s.replace('&','&amp;').replace('<','&lt;')
EDGE = {'gb': '#4c9a2a', 'jwj': '#c2452c', 'cc': '#8a3fd6', 'rgl': '#3b7be0'}  # breaker colors: Acme green, JWJ rust, Colfax purple
def edge(i): return next((c for k, c in EDGE.items() if i['id'].startswith(k)), 'var(--line)')
# Each breaker's own title card image for the break (Daniel, Nov 24), from the watcher's images.json, keyed by store and
# product handle. Shopify serves a smaller copy with &width=.
SHOP_OF = {'acmepackscards.com': 'acme', 'jwjcollectorbreaks.com': 'jwj', 'colfaxcc.com': 'colfax', 'rungoodlife.com': 'rgl'}
_ip = os.path.join(HERE, 'watch', 'images.json')
IMAGES = json.load(open(_ip)) if os.path.exists(_ip) else {}
def image_of(i):
    if i.get('image'): return i['image']
    m = re.match(r'https?://(?:www\.)?([^/]+)/products/([^/?#]+)', i.get('url', ''))
    if not m: return ''
    src = IMAGES.get(SHOP_OF.get(m.group(1), ''), {}).get(m.group(2), '')
    return (src + ('&' if '?' in src else '?') + 'width=640') if src else ''
def thumb(i):
    src = image_of(i)
    return f'<div class="thumb"><img src="{esc(src)}" alt="{esc(i["title"])} title card" loading="lazy" onerror="this.parentNode.remove()"></div>' if src else ''
def card(i): return f'''<a class="tile" href="/breaks/{i['id']}" style="border-left:4px solid {edge(i)}">{thumb(i)}<div class="kicker" style="font-size:11px">{esc(i['kicker'])}</div><div class="lab display" style="font-size:26px;margin-top:6px">{esc(i['title'])}</div><div class="cnt" style="margin-top:8px">{esc(i['when'])}</div><div class="peek">{esc(' · '.join(i['facts']))}</div></a>'''
up = ''.join(card(i) for i in items if not is_past(i)); past = ''.join(card(i) for i in items if is_past(i))
cards = up or '<p class="sub">No breaks on the schedule right now.</p>'  # past breaks stay online but aren't listed
html = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Break Guides | Main Event Card Vault</title><meta name="theme-color" content="#081524"><link rel="icon" href="{icon}">
<style>{css}
.grid {{ grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }}
.bar .bmenu {{ margin-left: auto; }}
.grid.past .tile {{ opacity: .72; }}
.tile .thumb {{ margin: -4px -4px 12px; border-radius: 10px; overflow: hidden; line-height: 0; }}
.tile .thumb img {{ width: 100%; height: auto; display: block; }}
/*BMENU-CSS*//*/BMENU-CSS*/
</style></head><body>
<header class="site"><div class="wrap"><div class="bar"><a class="brand" href="/"><img src="{icon}" alt=""><div><b class="display">Main Event Card Vault</b><span>Break guides</span></div></a><!--BMENU--><!--/BMENU--></div></div></header>
<div class="wrap hero"><div class="kicker">Spot guides</div><h1 class="display">Break guides</h1>
<p class="lede">Who you could pull in each spot, box by box, built from the published checklists. Pick-your-letter breaks show which spots are still open and what they cost.</p></div>
<main class="wrap"><a class="tile" href="/breaks/builder" style="display:block;margin-bottom:18px;border-color:var(--gold)"><div class="kicker" style="font-size:11px">Breaker tool</div><div class="lab display" style="font-size:26px;margin-top:6px">Spot builder</div><div class="peek" style="margin-top:6px">Pick checklists, set a spot count, and get the most evenly balanced letter spots, with optional pricing.</div></a><div class="grid">{cards}</div></main>
<p class="sub" style="margin-top:22px">Looking for a break that already ran? Its guide is still up on <a href="/breaks/past">Past breaks</a>.</p>
<footer><div class="wrap">Main Event Card Vault. Reference only; confirm checklists and house rules with the breaker. <a href="/breaks/release-notes">Release notes</a> · <a href="/breaks/past">Past breaks</a></div></footer>
</body></html>'''
open(os.path.join(ROOT,'breaks','index.html'),'w').write(html)
print(len(html))

# ---------------- "Breaks" menu: one list, written into every page ----------------
MENU_CSS = '''.bmenu { position: relative; }
.bmenu > summary { list-style: none; cursor: pointer; display: inline-flex; align-items: center; gap: 7px; padding: 7px 13px; border-radius: 999px;
  border: 1px solid var(--line-2); background: var(--panel); color: var(--ink); font-size: 14px; font-weight: 600; user-select: none; white-space: nowrap; }
.bmenu > summary::-webkit-details-marker { display: none; }
.bmenu > summary::after { content: ""; width: 7px; height: 7px; border-right: 2px solid var(--gold); border-bottom: 2px solid var(--gold); transform: rotate(45deg) translateY(-2px); }
.bmenu[open] > summary { border-color: var(--gold); }
.bmenu[open] > summary::after { transform: rotate(-135deg) translateY(-1px); }
.bmenu-list { position: absolute; right: 0; top: calc(100% + 8px); z-index: 80; width: 340px; max-width: calc(100vw - 24px); background: var(--bg-2, #0d1f38);
  border: 1px solid var(--line-2); border-radius: 14px; box-shadow: 0 18px 40px rgba(3,9,17,.7); padding: 6px; }
.bmenu-list a { display: block; text-decoration: none; color: var(--ink); padding: 9px 11px; border-radius: 10px; font-size: 14px; line-height: 1.35; border: 0; }
.bmenu-list a:hover, .bmenu-list a.on { background: rgba(230,190,85,.1); }
.bmenu-list a b { color: var(--gold); font-weight: 700; margin-right: 4px; }
.bmenu-list a span { display: block; font-size: 12px; color: var(--ink-3); margin-top: 2px; }
.bmenu-list a.all { border-top: 1px solid var(--line); margin-top: 4px; padding-top: 11px; color: var(--gold-2, #f1d07a); font-weight: 600; }
.bmenu-list a.past { opacity: .65; }
@media (max-width: 760px) { .bmenu-list { position: fixed; left: 12px; right: 12px; top: 64px; width: auto; max-height: calc(100vh - 80px); overflow-y: auto; } }'''

MENU_JS = '<script>document.querySelectorAll("details.bmenu").forEach(function(d){d.addEventListener("toggle",function(){var l=d.querySelector(".bmenu-list");if(d.open&&window.innerWidth<=760){l.style.top=(d.querySelector("summary").getBoundingClientRect().bottom+8)+"px";}else{l.style.top="";}});});document.addEventListener("click",function(e){document.querySelectorAll("details.bmenu[open]").forEach(function(d){if(!d.contains(e.target))d.removeAttribute("open");});});document.addEventListener("keydown",function(e){if(e.key==="Escape")document.querySelectorAll("details.bmenu[open]").forEach(function(d){d.removeAttribute("open");});});</script>'

def short_date(w):
    m = re.search(r'(November|December|January|October)\s+(\d+)', w)
    return (m.group(1)[:3] + ' ' + m.group(2)) if m else ''

def code_and_name(title):
    m = re.match(r'(CC\d+|JWJ #\d+|GB\d+|RGL #\d+)\s*[:\-]?\s*(.*)', title)
    return (m.group(1), m.group(2)) if m else ('', title)

def menu_html(current=None):
    # Daniel wants the menu short: no list of individual breaks, just these four links.
    on = ';background:rgba(230,190,85,.1)'
    first = 'border-top:0;margin-top:0;padding-top:9px'
    links = [
        f'<a class="all" href="/breaks/" style="{first}{on if current == "hub" else ""}">All break guides<span>Every break with a guide right now</span></a>',
        f'<a class="all" href="/breaks/builder" style="{first}{on if current == "builder" else ""}">Spot builder<span>Turn checklists into balanced spots</span></a>',
        f'<a class="all" href="/" style="{first}">Main Event Card Vault<span>Shop all my cards</span></a>',
        f'<a class="all" href="/iron-ledger.html" style="{first}{on if current == "ironledger" else ""}">Iron Ledger<span>My workout program</span></a>',
    ]
    return '<!--BMENU--><details class="bmenu"><summary>Breaks</summary><div class="bmenu-list">' + ''.join(links) + '</div></details>' + MENU_JS + '<!--/BMENU-->'

def fill(path, current=None):
    s = open(path).read()
    s = re.sub(r'<!--BMENU-->.*?<!--/BMENU-->', lambda m: menu_html(current), s, count=1, flags=re.S)
    s = re.sub(r'/\*BMENU-CSS\*/.*?/\*/BMENU-CSS\*/', lambda m: '/*BMENU-CSS*/' + MENU_CSS + '/*/BMENU-CSS*/', s, count=1, flags=re.S)
    s = footer_link(s, current)
    open(path, 'w').write(s)

# Iron Ledger is a packed single-file app: its real page lives in a JSON string in
# <script type="__bundler/template">, which replaces the document when it loads. The Breaks menu goes
# into that template as a slim bar above the app (Daniel, Nov 24). No script, the <details> menu works
# on its own. "</" and "<!--" are escaped when the template is written back so the outer script tag holds.
BAR_CSS = """#mecv-bar { --line: #1f3550; --line-2: #2d4766; --panel: #10243d; --bg-2: #0d1f38; --ink: #e9eef5; --ink-3: #8397ae;
  --gold: #e6be55; --gold-2: #f1d07a; position: relative; z-index: 50; background: #081524; border-bottom: 1px solid #1f3550;
  font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
#mecv-bar .mb-wrap { max-width: 912px; margin: 0 auto; padding: 10px 16px; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
#mecv-bar .mb-brand { color: #e9eef5; text-decoration: none; font-weight: 700; font-size: 14px; letter-spacing: .04em; text-transform: uppercase; }
#mecv-bar .mb-brand span { color: #e6be55; }
@media (max-width: 760px) { #mecv-bar .bmenu-list { top: 58px; } }
"""
def fill_bundled(path, current):
    s = open(path).read()
    tag = '<script type="__bundler/template">'
    a = s.index(tag) + len(tag); b = s.index('</script>', a)
    t = json.loads(s[a:b].strip())
    t = re.sub(r'<!--MECVBAR-->.*?<!--/MECVBAR-->', '', t, flags=re.S)
    menu = menu_html(current).replace('<!--BMENU-->', '').replace('<!--/BMENU-->', '').replace(MENU_JS, '')
    bar = ('<!--MECVBAR--><div id="mecv-bar"><style>' + MENU_CSS + '\n' + BAR_CSS + '</style><div class="mb-wrap">'
           '<a class="mb-brand" href="/">Main Event <span>Card Vault</span></a>' + menu + '</div></div><!--/MECVBAR-->')
    i = t.index('<body>') + len('<body>')
    t = t[:i] + bar + t[i:]
    enc = json.dumps(t, ensure_ascii=False).replace('</', '<\\u002F').replace('<!--', '<\\u0021--')
    open(path, 'w').write(s[:a] + '\n' + enc + '\n  ' + s[b:])

# A Release notes link at the bottom of every page that has the Breaks menu (Daniel, Nov 24).
RN_LINK = '<!--RNLINK--><a href="/breaks/release-notes">Release notes</a> · <a href="/breaks/past">Past breaks</a><!--/RNLINK-->'  # Past breaks: Daniel, Nov 24
def footer_link(s, current):
    if current == 'notes':
        return s
    if '<!--RNLINK-->' in s:
        link = RN_LINK.replace(' · ', '\n    ') if '<div class="socials">' in s else RN_LINK.replace('<a ', '· <a ', 1)
        return re.sub(r'<!--RNLINK-->.*?<!--/RNLINK-->', lambda m: link, s, count=1, flags=re.S)
    f = s.rfind('<footer')
    if f < 0:
        return s
    end = s.index('</footer>', f)
    if 'href="/breaks/release-notes"' in s[f:end]:
        return s
    sock = s.find('<div class="socials">', f, end)
    if sock > -1:  # storefront footer: add it to the row of links
        close = s.index('</div>', sock)
        return s[:close] + '  ' + RN_LINK.replace(' · ', '\n    ') + '\n    ' + s[close:]
    close = s.rfind('</div>', f, end)  # break pages: end of the footer line
    return s[:close] + ' ' + RN_LINK.replace('<a ', '· <a ', 1) + s[close:]

# ---------------- Release notes: breaks/release-notes.html from release_notes.json ----------------
RN = json.load(open(os.path.join(HERE, 'release_notes.json')))['releases']
TAGC = {'New': '#5ec98a', 'Improved': '#5aa9ff', 'Fixed': '#e6be55'}
def rn_item(t):
    tag, area, text = t
    return f'<li><span class="rtag" style="--t:{TAGC.get(tag, "#8397ae")}">{esc(tag)}</span><span class="rarea">{esc(area)}</span><p>{esc(text)}</p></li>'
rn_body = ''.join(f'<section class="rel"><div class="rdate">{esc(r["date"])}</div><h2 class="display">{esc(r["title"])}</h2><ul>{"".join(rn_item(t) for t in r["items"])}</ul></section>' for r in RN)
rn = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Release Notes | Main Event Card Vault</title><meta name="theme-color" content="#081524"><link rel="icon" href="{icon}">
<style>{css}
.bar .bmenu {{ margin-left: auto; }}
.rel {{ background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); padding: 18px 20px 8px; margin: 0 0 16px; }}
.rdate {{ color: var(--gold); font-size: 12px; letter-spacing: .18em; text-transform: uppercase; font-weight: 600; }}
.rel h2 {{ font-size: 26px; margin: 4px 0 10px; }}
.rel ul {{ list-style: none; margin: 0; padding: 0; }}
.rel li {{ padding: 10px 0 12px; border-top: 1px solid var(--line); }}
.rel li p {{ margin: 6px 0 0; color: var(--ink-2); font-size: 15px; max-width: 860px; }}
.rtag {{ display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; padding: 2px 9px; border-radius: 999px; color: var(--t); border: 1px solid var(--t); margin-right: 8px; }}
.rarea {{ font-size: 13px; color: var(--ink-3); font-weight: 600; }}
.rfilter {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 16px; }}
.rfilter button {{ font: inherit; font-size: 13.5px; padding: 7px 13px; border-radius: 999px; cursor: pointer; background: var(--bg-2); color: var(--ink-2); border: 1px solid var(--line-2); }}
.rfilter button.on {{ background: var(--gold); color: #1a1405; border-color: var(--gold); font-weight: 600; }}
/*BMENU-CSS*//*/BMENU-CSS*/
</style></head><body>
<header class="site"><div class="wrap"><div class="bar"><a class="brand" href="/"><img src="{icon}" alt=""><div><b class="display">Main Event Card Vault</b><span>Release notes</span></div></a><!--BMENU--><!--/BMENU--></div></div></header>
<div class="wrap hero"><div class="kicker">What's new</div><h1 class="display">Release notes</h1>
<p class="lede">Changes to the break guides, the Spot Builder and the site, newest first.</p></div>
<main class="wrap"><div class="rfilter" id="rf"><button class="on" data-a="">Everything</button><button data-a="Break guides">Break guides</button><button data-a="Spot Builder">Spot Builder</button><button data-a="Site">Site</button></div>
{rn_body}</main>
<footer><div class="wrap">Main Event Card Vault. <a href="/breaks/">All break guides</a> · <a href="/breaks/past">Past breaks</a></div></footer>
<script>(function(){{var bs=document.querySelectorAll("#rf button");bs.forEach(function(b){{b.onclick=function(){{var a=b.getAttribute("data-a");bs.forEach(function(x){{x.classList.toggle("on",x===b);}});document.querySelectorAll(".rel").forEach(function(r){{var n=0;r.querySelectorAll("li").forEach(function(li){{var ok=!a||li.querySelector(".rarea").textContent===a;li.hidden=!ok;if(ok)n++;}});r.hidden=!n;}});}};}});}})();</script>
</body></html>'''
open(os.path.join(ROOT, 'breaks', 'release-notes.html'), 'w').write(rn)
fill(os.path.join(ROOT, 'breaks', 'release-notes.html'), 'notes')

# ---------------- Past breaks: breaks/past.html (Daniel, Nov 24) ----------------
# Breaks that have run come off the Break guides list, but their pages stay up; this page lists them, newest first.
import datetime
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
def ran_on(i):
    m = re.search(r'(' + '|'.join(MONTHS) + r') (\d{1,2}), (\d{4})', i['when'])
    return datetime.date(int(m.group(3)), MONTHS.index(m.group(1)) + 1, int(m.group(2))) if m else datetime.date(2000, 1, 1)
BREAKER = {'gb': 'Acme Packs', 'jwj': 'JWJ Collector Breaks', 'cc': 'Colfax Collectibles', 'rgl': 'Run Good Life'}
def breaker_name(i): return next((v for k, v in BREAKER.items() if i['id'].startswith(k)), 'Other')
past_items = sorted((i for i in items if is_past(i)), key=lambda x: (ran_on(x), order.index(x['id'])), reverse=True)
def past_card(i):
    d = ran_on(i); q = ' '.join([i['title'], i['kicker'], i['when'], ' '.join(i['facts'])]).lower()
    attrs = f'data-b="{esc(breaker_name(i))}" data-m="{d:%Y-%m}" data-q="{esc(q).replace(chr(34), "")}"'
    return card(i).replace('<a class="tile"', '<a class="tile" ' + attrs, 1)
past_cards = ''.join(past_card(i) for i in past_items) or '<p class="sub">No past breaks yet.</p>'
_bk = [b for b in BREAKER.values() if any(breaker_name(i) == b for i in past_items)]
_mo = sorted({ran_on(i).strftime('%Y-%m') for i in past_items}, reverse=True)
past_tools = ('<div class="ptools"><input type="search" id="pq" placeholder="Search past breaks: product, breaker or break number" autocomplete="off">'
    + '<select id="pm" aria-label="Month"><option value="">All months</option>'
    + ''.join(f'<option value="{m}">{MONTHS[int(m[5:]) - 1]} {m[:4]}</option>' for m in _mo) + '</select></div>'
    + '<div class="chips" id="pb"><button class="chip on" data-b="">All breakers</button>'
    + ''.join(f'<button class="chip" data-b="{esc(b)}">{esc(b)}</button>' for b in _bk) + '</div>'
    + '<p class="sub" id="pcount"></p>') if past_items else ''
pb = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Past Breaks | Main Event Card Vault</title><meta name="theme-color" content="#081524"><link rel="icon" href="{icon}">
<style>{css}
.grid {{ grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }}
.bar .bmenu {{ margin-left: auto; }}
.tile .thumb {{ margin: -4px -4px 12px; border-radius: 10px; overflow: hidden; line-height: 0; }}
.tile .thumb img {{ width: 100%; height: auto; display: block; }}
.ptools {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 10px; }}
.ptools input {{ flex: 1 1 280px; min-width: 0; padding: 10px 14px; border-radius: 999px; border: 1px solid var(--line-2); background: var(--panel); color: var(--ink); font: inherit; }}
.ptools select {{ padding: 10px 14px; border-radius: 999px; border: 1px solid var(--line-2); background: var(--panel); color: var(--ink); font: inherit; }}
#pb {{ margin: 0 0 6px; }}
#pb .chip {{ cursor: pointer; font: inherit; font-size: 13.5px; padding: 7px 13px; border-radius: 999px; background: var(--bg-2); color: var(--ink-2); border: 1px solid var(--line-2); }}
#pb .chip.on {{ background: var(--gold); color: #1a1405; border-color: var(--gold); font-weight: 600; }}
/*BMENU-CSS*//*/BMENU-CSS*/
</style></head><body>
<header class="site"><div class="wrap"><div class="bar"><a class="brand" href="/"><img src="{icon}" alt=""><div><b class="display">Main Event Card Vault</b><span>Past breaks</span></div></a><!--BMENU--><!--/BMENU--></div></div></header>
<div class="wrap hero"><div class="kicker">Archive</div><h1 class="display">Past breaks</h1>
<p class="lede">Breaks that have already run, newest first. Each guide is still up, so you can look back at who was in every spot and check off what you pulled.</p></div>
<main class="wrap">{past_tools}<div class="grid" id="pgrid">{past_cards}</div><p class="sub" id="pnone" hidden>No past breaks match. Try another search or clear the filters.</p></main>
<footer><div class="wrap">Main Event Card Vault. <a href="/breaks/">All break guides</a> · <a href="/breaks/release-notes">Release notes</a></div></footer>
<script>(function () {{
  var q = document.getElementById("pq"); if (!q) return;
  var m = document.getElementById("pm"), bs = document.querySelectorAll("#pb .chip"), ts = document.querySelectorAll("#pgrid .tile"), b = "";
  function go() {{
    var w = q.value.trim().toLowerCase().split(/\\s+/).filter(Boolean), n = 0;
    ts.forEach(function (t) {{
      var ok = (!b || t.getAttribute("data-b") === b) && (!m.value || t.getAttribute("data-m") === m.value) && w.every(function (x) {{ return t.getAttribute("data-q").indexOf(x) > -1; }});
      t.hidden = !ok; if (ok) n++;
    }});
    document.getElementById("pcount").textContent = n === ts.length ? ts.length + " past breaks" : "Showing " + n + " of " + ts.length + " past breaks";
    document.getElementById("pnone").hidden = n > 0;
  }}
  q.oninput = go; m.onchange = go;
  bs.forEach(function (x) {{ x.onclick = function () {{ b = x.getAttribute("data-b"); bs.forEach(function (y) {{ y.classList.toggle("on", y === x); }}); go(); }}; }});
  go();
}})();</script>
</body></html>'''
open(os.path.join(ROOT, 'breaks', 'past.html'), 'w').write(pb)
fill(os.path.join(ROOT, 'breaks', 'past.html'), 'past')

for i in items:
    fill(os.path.join(ROOT, 'breaks', i['id'] + '.html'), i['id'])
fill(os.path.join(ROOT, 'breaks', 'index.html'), 'hub')
if os.path.exists(os.path.join(ROOT, 'breaks', 'builder.html')): fill(os.path.join(ROOT, 'breaks', 'builder.html'), 'builder')
if os.path.exists(os.path.join(ROOT, 'iron-ledger.html')): fill_bundled(os.path.join(ROOT, 'iron-ledger.html'), 'ironledger')
fill(os.path.join(ROOT, 'build', 'template.html'))
print('menu written to', len(items) + 2, 'files')
