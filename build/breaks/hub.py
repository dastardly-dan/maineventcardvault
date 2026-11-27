import os
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'..','..'))
import json, re
css = open(os.path.join(HERE,'base.css')).read()
tpl = open(os.path.join(HERE,'template.html')).read()
icon = re.search(r'<link rel="icon" href="([^"]+)"', open(os.path.join(ROOT,'breaks','cc871.html')).read()).group(1)
items = json.load(open(os.path.join(HERE,'index.json')))
items.append(dict(id='cc874', title='CC874 Monster Multi: Random Letter', kicker='Colfax Collectibles · Random letter · Multi-sport', when='Ran Sunday, November 22, 2026', facts=['7 boxes', '21 letter spots'], ended='yes'))
order = ['cc871', 'cc872', 'cc873', 'cc874', 'cc875', 'jwj0246', 'jwj0247', 'jwj0247u', 'jwj0244', 'gb1037', 'gb1038b', 'gb1038a', 'gb1040', 'gb1041', 'gb1042', 'gb1043', 'gb1044', 'gb1045', 'gb1046', 'rgl6144', 'rgl6145', 'rgl6146', 'rgl6147', 'rgl6148', 'cc876', 'cc877', 'cc878', 'cc879', 'rgl6128', 'rgl612xwwe2', 'rgl6129', 'rgl6130', 'rgl6131', 'rgl6132', 'rgl6133', 'rgl6134', 'rgl6135', 'rgl6136', 'rgl6137', 'rgl6138', 'rgl6139', 'rgl6140', 'rgl6141', 'rgl612xmarvel', 'rgl6142']
def is_past(i): return bool(i.get('ended')) or 'has passed' in i['when']
items.sort(key=lambda x: (is_past(x), order.index(x['id'])))
def esc(s): return s.replace('&','&amp;').replace('<','&lt;')

# "I'm in this break" (Daniel, Nov 26): break pages keep a list of the breaks you bought into in this browser ("mecv-in"; saving a spot
# or checking a pull counts too). The Break guides list and Past breaks flag those with a "You're in" badge, and Past breaks gets a My breaks filter.
IN_CSS = '.inb { display: inline-block; margin-bottom: 8px; padding: 2px 10px; border-radius: 999px; background: var(--gold); color: #1a1405; font-size: 11px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; }\n'
IN_SCRIPT = """<script>(function () {
  var ts = document.querySelectorAll("a.tile[href^='/breaks/']"), s = {}, a = [], n = 0;
  try { a = JSON.parse(localStorage.getItem("mecv-in") || "[]"); } catch (e) {}
  (Array.isArray(a) ? a : []).forEach(function (x) { s[x] = 1; });
  [].forEach.call(ts, function (t) {
    var id = t.getAttribute("href").slice(8);
    try { ["mine", "got"].forEach(function (k) { var v = localStorage.getItem("mecv-" + id + "-" + k); if (v && v !== "[]") s[id] = 1; }); } catch (e) {}
    if (!s[id]) return;
    n++; t.setAttribute("data-in", "1");
    var k = t.querySelector(".kicker"); if (k) k.insertAdjacentHTML("beforebegin", '<div class="inb">You\\'re in</div>');
  });
  var pb = document.getElementById("pb");
  if (pb && n) pb.insertAdjacentHTML("beforeend", '<button class="chip" data-b="__mine">My breaks (' + n + ')</button>');
})();</script>
"""
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
cards = up or '<a class="tile" href="/breaks/past" style="display:block;border-color:var(--gold)"><div class="kicker" style="font-size:11px">No breaks posted right now</div><div class="lab display" style="font-size:26px;margin-top:6px">Past breaks</div><div class="peek" style="margin-top:6px">Every break that already ran is on the Past breaks page, with its full guide. New guides show up here as soon as the breakers post them.</div></a>'  # past breaks stay online but aren't listed
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
{IN_CSS}</style></head><body>
<header class="site"><div class="wrap"><div class="bar"><a class="brand" href="/"><img src="{icon}" alt=""><div><b class="display">Main Event Card Vault</b><span>Break guides</span></div></a><!--BMENU--><!--/BMENU--></div></div></header>
<div class="wrap hero"><div class="kicker">Spot guides</div><h1 class="display">Break guides</h1>
<p class="lede">Who you could pull in each spot, box by box, built from the published checklists. Pick-your-letter breaks show which spots are still open and what they cost.</p></div>
<main class="wrap"><div class="grid">{cards}</div>{"" if not up else '<p class="sub" style="margin-top:22px">Looking for a break that already ran? Its guide is still up on <a href="/breaks/past">Past breaks</a>.</p>'}<a class="tile" href="/breaks/builder" style="display:block;margin:22px 0 32px;border-color:var(--gold)"><div class="kicker" style="font-size:11px">Breaker tool</div><div class="lab display" style="font-size:26px;margin-top:6px">Spot builder</div><div class="peek" style="margin-top:6px">Pick checklists, set a spot count, and get the most evenly balanced letter spots, with optional pricing.</div></a></main>
<footer><div class="wrap">Main Event Card Vault. Reference only; confirm checklists and house rules with the breaker. <a href="/breaks/release-notes">Release notes</a> · <a href="/breaks/past">Past breaks</a> · <a href="/owner">Developer dashboard</a></div></footer>
</body></html>'''
html = html.replace('</body>', IN_SCRIPT + '</body>')
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
        f'<a class="all" href="/breaks/watch" style="{first}{on if current == "watch" else ""}">Watch your breaks<span>Stream, chat and your spot on one page</span></a>',
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
RN_LINK = '<!--RNLINK--><a href="/breaks/release-notes">Release notes</a> · <a href="/breaks/past">Past breaks</a> · <a href="/owner">Developer dashboard</a><!--/RNLINK-->'  # Past breaks: Daniel, Nov 24; Developer dashboard (the password-protected /owner page): Daniel, Nov 27
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
<footer><div class="wrap">Main Event Card Vault. <a href="/breaks/">All break guides</a> · <a href="/breaks/past">Past breaks</a> · <a href="/owner">Developer dashboard</a></div></footer>
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
{IN_CSS}</style></head><body>
<header class="site"><div class="wrap"><div class="bar"><a class="brand" href="/"><img src="{icon}" alt=""><div><b class="display">Main Event Card Vault</b><span>Past breaks</span></div></a><!--BMENU--><!--/BMENU--></div></div></header>
<div class="wrap hero"><div class="kicker">Archive</div><h1 class="display">Past breaks</h1>
<p class="lede">Breaks that have already run, newest first. Each guide is still up, so you can look back at who was in every spot and check off what you pulled.</p>
<p class="lede" style="margin-top:8px">Bought into a break? Open its guide and tap <b>I'm in this break</b>, even if you don't know your spot yet. It gets a "You're in" badge here and under a <b>My breaks</b> filter. Saved only in this browser.</p></div>
<main class="wrap">{past_tools}<div class="grid" id="pgrid">{past_cards}</div><p class="sub" id="pnone" hidden>No past breaks match. Try another search or clear the filters.</p></main>
<footer><div class="wrap">Main Event Card Vault. <a href="/breaks/">All break guides</a> · <a href="/breaks/release-notes">Release notes</a> · <a href="/owner">Developer dashboard</a></div></footer>
{IN_SCRIPT}<script>(function () {{
  var q = document.getElementById("pq"); if (!q) return;
  var m = document.getElementById("pm"), bs = document.querySelectorAll("#pb .chip"), ts = document.querySelectorAll("#pgrid .tile"), b = "";
  function go() {{
    var w = q.value.trim().toLowerCase().split(/\\s+/).filter(Boolean), n = 0;
    ts.forEach(function (t) {{
      var ok = (!b || (b === "__mine" ? t.getAttribute("data-in") === "1" : t.getAttribute("data-b") === b)) && (!m.value || t.getAttribute("data-m") === m.value) && w.every(function (x) {{ return t.getAttribute("data-q").indexOf(x) > -1; }});
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

# ---------------- Watch along: breaks/watch.html (Daniel, Nov 27, 2026) ----------------
# One public page to follow your breaks: pick a break (yours first, from "I'm in this break" and saved spots in this browser),
# its stream with the chat beside it, and a spot dropdown that shows every player in that spot, box by box. No prices or
# values of cards (Nov 25 rule); spot prices and open or sold only where the guide shows them.
import owner as _ow
def _at(w):
    m = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4}).*?\(?(\d{1,2}:\d{2} [ap]m) Eastern', w)
    if not m: return None
    try: return datetime.datetime.strptime(m.group(1) + ' ' + m.group(2), '%B %d, %Y %I:%M %p').isoformat()
    except ValueError: return None
_recent = datetime.date.today() - datetime.timedelta(days=1)   # past breaks from today and yesterday only, to keep the page light
W = []
for i in items:
    if is_past(i) and ran_on(i) < _recent: continue
    D = _ow.page_data(i['id'])
    if not D or not D.get('spots'): continue
    W.append(dict(id=i['id'], title=D['title'], breaker=breaker_name(i), when=D.get('when', i['when']).split('. ')[0], at=_at(D.get('when', i['when'])),
        past=is_past(i), video=D.get('video'), vstart=D.get('videoStart') or 0, url=D.get('url', ''), team=D.get('format') in ('pyt', 'random') and any(sp.get('teams') for sp in D['spots']),
        boxes=[[b['k'], b.get('short', b['k']), b.get('c', '#e6be55')] for b in D['boxes']],
        spots=[dict(id=sp['id'], label=sp['label'], sub=sp.get('g') or '', price=sp.get('price'), status=sp.get('status') or '', hits=(D.get('hits') or {}).get(sp['id'], []),
                    names={k: [[e[0], e[1] or '', 1 if e[2] else 0] for e in v] for k, v in D['names'].get(sp['id'], {}).items()}) for sp in D['spots']]))
W.sort(key=lambda b: (b['past'], b['at'] or '9999'))
WATCH_JS = r"""<script>(function () {
var W = __DATA__, $ = function (i) { return document.getElementById(i); }, host = location.hostname || "maineventcardvault.com", curVid = null;
function e(t) { return String(t == null ? "" : t).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
function get(k, d) { try { var v = JSON.parse(localStorage.getItem(k) || "null"); return v == null ? d : v; } catch (x) { return d; } }
function put(k, a) { try { a && a.length ? localStorage.setItem(k, JSON.stringify(a)) : localStorage.removeItem(k); } catch (x) {} }
function mine(id) { var a = get("mecv-" + id + "-mine", []); return Array.isArray(a) ? a : [String(a)]; }
function ins() { var a = get("mecv-in", []); return Array.isArray(a) ? a : []; }
function isIn(b) { return ins().indexOf(b.id) > -1 || mine(b.id).length > 0; }
function tm(b) { var m = b.when.match(/\(([^)]*Eastern)\)/) || b.when.match(/(\d{1,2}:\d{2} [ap]m [A-Z][a-z]+)/); return m ? m[1].replace(" Eastern", " ET") : ""; }
function day(b) { var m = b.when.match(/^([A-Za-z]+, [A-Za-z]+ \d+)/); return m ? m[1] : ""; }
function byId(id) { for (var i = 0; i < W.length; i++) if (W[i].id === id) return W[i]; return null; }
function pickDefault() {
  var now = Date.now(), soon = function (b) { return b.at && new Date(b.at + "-05:00").getTime() + 3 * 3600e3 > now; };
  var m = W.filter(function (b) { return isIn(b) && !b.past && soon(b); }); if (m.length) return m[0].id;
  m = W.filter(isIn); if (m.length) return m[0].id;
  m = W.filter(function (b) { return !b.past && soon(b); }); return (m[0] || W[0] || {}).id;
}
function fillBreaks(sel) {
  var you = W.filter(isIn), up = W.filter(function (b) { return !b.past; }), ran = W.filter(function (b) { return b.past; }), h = "";
  function grp(n, a) { if (!a.length) return; h += '<optgroup label="' + e(n) + '">' + a.map(function (b) { return '<option value="' + b.id + '">' + e(b.title + "  ·  " + day(b) + " " + tm(b)) + "</option>"; }).join("") + "</optgroup>"; }
  grp("Your breaks", you); grp("Coming up", up.filter(function (b) { return you.indexOf(b) < 0; })); grp("Recently ran", ran.filter(function (b) { return you.indexOf(b) < 0; }));
  $("wb").innerHTML = h; $("wb").value = sel;
}
function video(b) {
  if (curVid === b.id) return; curVid = b.id; var v = $("wvid"), c = $("wchat");
  if (!b.video) { v.innerHTML = '<div class="wnone">No stream link for this break yet. It shows up here as soon as the breaker goes live.' + (b.url ? '<br><a href="' + e(b.url) + '" target="_blank" rel="noopener">Breaker\'s listing</a>' : "") + "</div>"; c.innerHTML = '<div class="wnone">The live chat shows up here with the stream.</div>'; return; }
  v.innerHTML = '<iframe src="https://www.youtube-nocookie.com/embed/' + b.video + (b.vstart ? "?start=" + b.vstart : "") + '" title="' + e(b.title) + ' stream" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>';
  c.innerHTML = b.past ? '<div class="wnone">This break already ran, so the video above is the replay and the chat is closed.</div>'
    : '<iframe src="https://www.youtube.com/live_chat?v=' + b.video + "&embed_domain=" + encodeURIComponent(host) + '&dark_theme=1" title="Live chat"></iframe><div class="wsm">Sign in to YouTube to post. <a href="https://www.youtube.com/watch?v=' + b.video + '" target="_blank" rel="noopener">Open on YouTube</a></div>';
}
function tags(n, team) {
  var f = n[1], h = "";
  if (f.indexOf("A") > -1) h += '<span class="tag">' + (team && !n[2] ? "hit" : "auto") + "</span>";
  if (f.indexOf("I") > -1 && !n[2] && f.indexOf("A") < 0) h += '<span class="tag i">insert</span>';
  if (f.indexOf("M") > -1) h += '<span class="tag m">multi</span>';
  if (f.indexOf("N") > -1) h += '<span class="tag n">NIL</span>';
  return h;
}
function show(b, spotId) {
  var my = mine(b.id), sel = spotId || my[0] || "";
  $("ws").innerHTML = '<option value="">Pick a spot</option>' + b.spots.map(function (s) {
    return '<option value="' + e(s.id) + '">' + e(s.label + (s.sub ? " (" + s.sub + ")" : "") + (my.indexOf(s.id) > -1 ? "  ·  yours" : "") + (s.status === "sold" ? "  ·  sold" : s.status === "open" ? "  ·  open" : "")) + "</option>"; }).join("");
  $("ws").value = sel;
  var inb = isIn(b);
  $("whead").innerHTML = '<div class="wcard"><div><div class="kicker">' + e(b.breaker) + "</div><h2 class=\"display\">" + e(b.title) + '</h2><div class="sub">' + e(b.when) + (b.past ? " · already ran" : "") + '</div></div><div class="wbtns">' +
    '<button type="button" id="win" class="' + (inb ? "on" : "") + '">' + (inb ? "You're in this break" : "I'm in this break") + "</button>" +
    '<button type="button" id="wwide" class="on">' + (document.body.classList.contains("wide") ? "Video and chat side by side" : "Bigger video") + "</button>" +
    '<a href="/breaks/' + b.id + '">Full guide</a>' + (b.url ? '<a href="' + e(b.url) + '" target="_blank" rel="noopener">Breaker\'s listing</a>' : "") + "</div></div>";
  $("wwide").onclick = function () { var w = !document.body.classList.contains("wide"); document.body.classList.toggle("wide", w); try { w ? localStorage.setItem("mecv-watch-wide", "1") : localStorage.removeItem("mecv-watch-wide"); } catch (x) {} this.textContent = w ? "Video and chat side by side" : "Bigger video"; $("wvid").scrollIntoView({ block: "start", behavior: "smooth" }); };
  $("win").onclick = function () { var a = ins(), i = a.indexOf(b.id); if (i > -1) a.splice(i, 1); else a.push(b.id); put("mecv-in", a); show(b, $("ws").value); list(); };
  video(b); spot(b, sel); list();
}
function hitsHTML(b, s) {
  if (!s.hits || !s.hits.length) return "";
  var bk = {}; b.boxes.forEach(function (x) { bk[x[0]] = x; });
  return '<div class="whits"><div class="wbn">Special hits <span>' + s.hits.length + '</span></div>' + s.hits.map(function (h) { var x = bk[h[0]] || [h[0], h[0], "#888"];
    return '<div class="whit"><i style="background:' + e(x[2]) + '"></i><b>' + e(h[1]) + "</b>" + (h[2] === "auto" ? '<span class="tag">auto</span>' : "") + ' <span class="wsm2">' + e(x[1]) + "</span><div>" + e(h[3]) + (h[4] ? ' <span class="wsm2">(also ' + e(h[4]) + ")</span>" : "") + "</div></div>"; }).join("") + "</div>";
}
function spot(b, id) {
  var s = null; b.spots.forEach(function (x) { if (x.id === id) s = x; });
  if (!s) { $("wspot").innerHTML = '<div class="wcard"><p class="sub">Pick a spot above to see every player in it, box by box.' + (b.spots.length ? " Your saved spots come up first next time." : "") + "</p></div>"; return; }
  var my = mine(b.id), on = my.indexOf(s.id) > -1, n = 0, body = "";
  b.boxes.forEach(function (bx) {
    var a = s.names[bx[0]] || []; if (!a.length) return; n += a.length;
    body += '<div class="wbox"><div class="wbn"><i style="background:' + e(bx[2]) + '"></i>' + e(bx[1]) + ' <span>' + a.length + "</span></div><div class=\"pills\">" + a.map(function (x) { return '<span class="pill">' + e(x[0]) + tags(x, b.team) + "</span>"; }).join("") + "</div></div>";
  });
  $("wspot").innerHTML = '<div class="wcard"><div class="wsh"><h3 class="display">' + e(s.label) + (s.sub ? ' <span class="sub">' + e(s.sub) + "</span>" : "") + "</h3>" +
    (s.price ? '<span class="wst">$' + s.price + "</span>" : "") + (s.status ? '<span class="wst ' + e(s.status) + '">' + e(s.status) + "</span>" : "") +
    '<button type="button" id="wmine" class="' + (on ? "on" : "") + '">' + (on ? "My spot" : "This is my spot") + "</button></div>" +
    '<p class="sub">' + n + " players in this spot across " + b.boxes.length + " box" + (b.boxes.length > 1 ? "es" : "") + ".</p>" + hitsHTML(b, s) + (body || '<p class="sub">No names in this spot.</p>') + "</div>";
  $("wmine").onclick = function () {
    var a = mine(b.id), i = a.indexOf(s.id); if (i > -1) a.splice(i, 1); else a.push(s.id); put("mecv-" + b.id + "-mine", a);
    if (a.length) { var q = ins(); if (q.indexOf(b.id) < 0) { q.push(b.id); put("mecv-in", q); } }
    fillBreaks(b.id); show(b, s.id);
  };
}
function list() {
  var you = W.filter(isIn);
  $("wmy").innerHTML = you.length ? you.map(function (b) {
    var my = mine(b.id).map(function (id) { var s = null; b.spots.forEach(function (x) { if (x.id === id) s = x; }); return s ? s.label : null; }).filter(Boolean);
    return '<a class="tile" href="#' + b.id + '"><div class="kicker" style="font-size:11px">' + e(b.breaker) + (b.video ? " · stream ready" : "") + '</div><div class="lab display" style="font-size:22px;margin-top:6px">' + e(b.title) + '</div><div class="cnt" style="margin-top:6px">' + e(day(b) + ", " + tm(b)) + (b.past ? " · ran" : "") + '</div><div class="peek">' + (my.length ? "Your spot" + (my.length > 1 ? "s" : "") + ": " + e(my.join(", ")) : "No spot saved yet") + "</div></a>";
  }).join("") : '<p class="sub">Nothing saved yet. Pick a break above and tap <b>I\'m in this break</b>, or <b>This is my spot</b> once you know your spot. It\'s saved only in this browser, and it\'s the same list the guides use.</p>';
}
function route() {
  var h = location.hash.replace(/^#/, "").split("/"), b = byId(h[0]) || byId(pickDefault());
  if (!b) { $("whead").innerHTML = '<p class="sub">No breaks to follow right now.</p>'; return; }
  fillBreaks(b.id); show(b, h[1] ? decodeURIComponent(h[1]) : "");
}
try { if (localStorage.getItem("mecv-watch-wide")) document.body.classList.add("wide"); } catch (x) {}
$("wb").onchange = function () { location.hash = $("wb").value; };
$("ws").onchange = function () { var b = byId($("wb").value); if (b) history.replaceState(null, "", "#" + b.id + ($("ws").value ? "/" + encodeURIComponent($("ws").value) : "")); spot(b, $("ws").value); };
window.addEventListener("hashchange", route); route();
})();</script>"""
wp = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Watch Your Breaks | Main Event Card Vault</title><meta name="theme-color" content="#081524"><link rel="icon" href="{icon}">
<style>{css}
.bar .bmenu {{ margin-left: auto; }}
:root {{ --maxw: 1600px; }}
.hero {{ padding-top: 14px; padding-bottom: 4px; }} .hero h1 {{ font-size: clamp(28px, 4vw, 40px); margin: 4px 0 6px; }} .hero .lede {{ font-size: 15px; margin: 0; }}
.wpick {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 0 0 14px; }}
.wpick label {{ flex: 1 1 300px; display: flex; flex-direction: column; gap: 5px; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--ink-3); }}
.wpick select {{ padding: 11px 14px; border-radius: 12px; border: 1px solid var(--line-2); background: var(--panel); color: var(--ink); font: inherit; font-size: 15px; text-transform: none; letter-spacing: 0; }}
.wcard {{ background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 16px 18px; margin: 0 0 14px; }}
.wcard h2 {{ font-size: 22px; margin: 2px 0 0; }} #whead .wcard {{ display: flex; flex-wrap: wrap; align-items: center; gap: 6px 18px; padding: 12px 16px; }} #whead .wbtns {{ margin: 0 0 0 auto; }} .wcard h3 {{ font-size: 24px; margin: 0; }}
.wbtns {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
.wbtns a, .wbtns button, #wmine {{ font: inherit; font-size: 14px; font-weight: 600; padding: 8px 14px; border-radius: 999px; border: 1px solid var(--line-2); background: var(--bg-2); color: var(--ink); text-decoration: none; cursor: pointer; }}
.wbtns button, #wmine {{ background: var(--gold); color: #1a1405; border-color: var(--gold); }}
.wbtns button.on, #wmine.on {{ background: transparent; color: var(--gold); }}
.wgrid {{ display: grid; grid-template-columns: 1fr 340px; gap: 12px; margin: 0 0 14px; }}
body.wide .wgrid {{ grid-template-columns: 1fr; }} body.wide .wchat {{ height: 460px; }}
.vh {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }}
.wpick {{ margin-bottom: 10px; }} .wpick select {{ padding: 9px 12px; }}
.wvbox {{ display: flex; justify-content: center; background: #050c16; border-radius: 16px; }}
.wvid {{ position: relative; width: 100%; max-width: calc((100vh - 170px) * 16 / 9); aspect-ratio: 16 / 9; background: #050c16; border: 1px solid var(--line); border-radius: 16px; overflow: hidden; }}
.wvid iframe {{ position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }}
.wchat {{ max-height: calc(100vh - 170px); display: flex; flex-direction: column; background: var(--panel); border: 1px solid var(--line); border-radius: 16px; overflow: hidden; min-height: 320px; }}
.wchat iframe {{ flex: 1; width: 100%; border: 0; min-height: 320px; }}
.wnone {{ display: flex; align-items: center; justify-content: center; text-align: center; height: 100%; padding: 20px; color: var(--ink-3); font-size: 14px; line-height: 1.5; }}
.wsm {{ font-size: 12px; color: var(--ink-3); padding: 7px 12px; }}
.wsh {{ display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }} #wmine {{ margin-left: auto; }}
.wst {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; padding: 3px 10px; border-radius: 999px; border: 1px solid var(--line-2); color: var(--ink-2); }}
.wst.open {{ color: #7fd3a1; border-color: #2f6b4c; }} .wst.sold {{ color: var(--ink-3); }}
.whits {{ margin: 12px 0 4px; padding: 10px 12px; border: 1px solid var(--line); border-left: 4px solid var(--gold); border-radius: 12px; background: var(--bg-2); }}
.whit {{ position: relative; padding-left: 16px; margin: 6px 0; font-size: 14px; }} .whit i {{ position: absolute; left: 0; top: 6px; width: 9px; height: 9px; border-radius: 3px; }} .wsm2 {{ font-size: 12.5px; color: var(--ink-3); }}
.wbox {{ margin: 12px 0 0; }} .wbn {{ font-weight: 700; font-size: 14px; display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }}
.wbn i {{ width: 10px; height: 10px; border-radius: 3px; display: inline-block; }} .wbn span {{ color: var(--ink-3); font-weight: 400; }}
.pills {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.pill {{ font-size: 13.5px; padding: 5px 10px; border-radius: 999px; background: var(--bg-2); border: 1px solid var(--line); color: var(--ink); }}
.tag {{ font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; margin-left: 6px; padding: 1px 6px; border-radius: 6px; background: var(--gold); color: #1a1405; }}
.tag.i {{ background: #3c6fd8; color: #fff; }} .tag.m {{ background: #7e57c2; color: #fff; }} .tag.n {{ background: #2f6b4c; color: #fff; }}
.grid {{ grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }}
@media (max-width: 900px) {{ .wgrid {{ grid-template-columns: 1fr; }} .wchat {{ height: 420px; }} }}
/*BMENU-CSS*//*/BMENU-CSS*/
{IN_CSS}</style></head><body>
<header class="site"><div class="wrap"><div class="bar"><a class="brand" href="/"><img src="{icon}" alt=""><div><b class="display">Main Event Card Vault</b><span>Watch your breaks</span></div></a><!--BMENU--><!--/BMENU--></div></div></header>
<main class="wrap" style="padding-top:14px"><h1 class="vh">Watch your breaks</h1><div class="wpick"><label>Break<select id="wb"></select></label><label>Spot<select id="ws"></select></label></div>
<div class="wgrid"><div class="wvbox"><div class="wvid" id="wvid"></div></div><div class="wchat" id="wchat"></div></div><div id="whead"></div><div id="wspot"></div>
<p class="sub" style="margin:4px 0 0">Pick a break to watch the stream with the live chat beside it, then pick a spot to see every player in it while the boxes get opened. Breaks you're in come up first.</p>
<h2 class="display" style="font-size:26px;margin:26px 0 10px">Your breaks</h2><div class="grid" id="wmy"></div></main>
<footer><div class="wrap">Main Event Card Vault. Reference only; confirm checklists and house rules with the breaker. <a href="/breaks/">All break guides</a> · <a href="/breaks/release-notes">Release notes</a></div></footer>
{WATCH_JS.replace('__DATA__', json.dumps(W, ensure_ascii=False).replace('</', '<\\/'))}
</body></html>"""
open(os.path.join(ROOT, 'breaks', 'watch.html'), 'w').write(wp)
fill(os.path.join(ROOT, 'breaks', 'watch.html'), 'watch')
print('watch page', len(W), 'breaks', len(wp), 'bytes')

for i in items:
    fill(os.path.join(ROOT, 'breaks', i['id'] + '.html'), i['id'])
fill(os.path.join(ROOT, 'breaks', 'index.html'), 'hub')
if os.path.exists(os.path.join(ROOT, 'breaks', 'builder.html')): fill(os.path.join(ROOT, 'breaks', 'builder.html'), 'builder')
if os.path.exists(os.path.join(ROOT, 'iron-ledger.html')): fill_bundled(os.path.join(ROOT, 'iron-ledger.html'), 'ironledger')
fill(os.path.join(ROOT, 'build', 'template.html'))
print('menu written to', len(items) + 2, 'files')

# Daniel's private dashboard (owner/dashboard.js, served by worker.js at /owner behind the password)
import owner
owner.main()
