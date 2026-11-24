import os
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'..','..'))
import json, re
css = open(os.path.join(HERE,'base.css')).read()
tpl = open(os.path.join(HERE,'template.html')).read()
icon = re.search(r'<link rel="icon" href="([^"]+)"', open(os.path.join(ROOT,'breaks','cc871.html')).read()).group(1)
items = json.load(open(os.path.join(HERE,'index.json')))
items.append(dict(id='cc874', title='CC874 Monster Multi: Random Letter', kicker='Colfax Collectibles · Random letter · Multi-sport', when='Ran Sunday, November 22, 2026', facts=['7 boxes', '21 letter spots'], ended='yes'))
order = ['cc871', 'cc872', 'cc874', 'cc875', 'jwj0246', 'jwj0247', 'jwj0244', 'gb1037', 'gb1038b', 'gb1038a']
def is_past(i): return bool(i.get('ended')) or 'has passed' in i['when']
items.sort(key=lambda x: (is_past(x), order.index(x['id'])))
def esc(s): return s.replace('&','&amp;').replace('<','&lt;')
EDGE = {'gb': '#4c9a2a', 'jwj': '#c2452c', 'cc': '#8a3fd6'}  # breaker colors: Acme green, JWJ rust, Colfax purple
def edge(i): return next((c for k, c in EDGE.items() if i['id'].startswith(k)), 'var(--line)')
def card(i): return f'''<a class="tile" href="/breaks/{i['id']}" style="border-left:4px solid {edge(i)}"><div class="kicker" style="font-size:11px">{esc(i['kicker'])}</div><div class="lab display" style="font-size:26px;margin-top:6px">{esc(i['title'])}</div><div class="cnt" style="margin-top:8px">{esc(i['when'])}</div><div class="peek">{esc(' · '.join(i['facts']))}</div></a>'''
up = ''.join(card(i) for i in items if not is_past(i)); past = ''.join(card(i) for i in items if is_past(i))
cards = up or '<p class="sub">No breaks on the schedule right now.</p>'  # past breaks stay online but aren't listed
html = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Break Guides | Main Event Card Vault</title><meta name="theme-color" content="#081524"><link rel="icon" href="{icon}">
<style>{css}
.grid {{ grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }}
.bar .bmenu {{ margin-left: auto; }}
.grid.past .tile {{ opacity: .72; }}
/*BMENU-CSS*//*/BMENU-CSS*/
</style></head><body>
<header class="site"><div class="wrap"><div class="bar"><a class="brand" href="/"><img src="{icon}" alt=""><div><b class="display">Main Event Card Vault</b><span>Break guides</span></div></a><!--BMENU--><!--/BMENU--></div></div></header>
<div class="wrap hero"><div class="kicker">Spot guides</div><h1 class="display">Break guides</h1>
<p class="lede">Who you could pull in each spot, box by box, built from the published checklists. Pick-your-letter breaks show which spots are still open and what they cost.</p></div>
<main class="wrap"><a class="tile" href="/breaks/builder" style="display:block;margin-bottom:18px;border-color:var(--gold)"><div class="kicker" style="font-size:11px">Breaker tool</div><div class="lab display" style="font-size:26px;margin-top:6px">Spot builder</div><div class="peek" style="margin-top:6px">Pick checklists, set a spot count, and get the most evenly balanced letter spots, with optional pricing.</div></a><div class="grid">{cards}</div></main>
<footer><div class="wrap">Main Event Card Vault. Reference only; confirm checklists and house rules with the breaker. <a href="/breaks/release-notes">Release notes</a></div></footer>
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
    m = re.match(r'(CC\d+|JWJ #\d+|GB\d+)\s*[:\-]?\s*(.*)', title)
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
RN_LINK = '<!--RNLINK--><a href="/breaks/release-notes">Release notes</a><!--/RNLINK-->'
def footer_link(s, current):
    if current == 'notes':
        return s
    if '<!--RNLINK-->' in s:
        link = RN_LINK if '<div class="socials">' in s else RN_LINK.replace('<a ', '· <a ', 1)
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
        return s[:close] + '  ' + RN_LINK + '\n    ' + s[close:]
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
<footer><div class="wrap">Main Event Card Vault. <a href="/breaks/">All break guides</a></div></footer>
<script>(function(){{var bs=document.querySelectorAll("#rf button");bs.forEach(function(b){{b.onclick=function(){{var a=b.getAttribute("data-a");bs.forEach(function(x){{x.classList.toggle("on",x===b);}});document.querySelectorAll(".rel").forEach(function(r){{var n=0;r.querySelectorAll("li").forEach(function(li){{var ok=!a||li.querySelector(".rarea").textContent===a;li.hidden=!ok;if(ok)n++;}});r.hidden=!n;}});}};}});}})();</script>
</body></html>'''
open(os.path.join(ROOT, 'breaks', 'release-notes.html'), 'w').write(rn)
fill(os.path.join(ROOT, 'breaks', 'release-notes.html'), 'notes')

for i in items:
    fill(os.path.join(ROOT, 'breaks', i['id'] + '.html'), i['id'])
fill(os.path.join(ROOT, 'breaks', 'index.html'), 'hub')
if os.path.exists(os.path.join(ROOT, 'breaks', 'builder.html')): fill(os.path.join(ROOT, 'breaks', 'builder.html'), 'builder')
if os.path.exists(os.path.join(ROOT, 'iron-ledger.html')): fill_bundled(os.path.join(ROOT, 'iron-ledger.html'), 'ironledger')
fill(os.path.join(ROOT, 'build', 'template.html'))
print('menu written to', len(items) + 2, 'files')
