import os
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.abspath(os.path.join(HERE,'..','..'))
import json, re
css = open(os.path.join(HERE,'base.css')).read()
tpl = open(os.path.join(HERE,'template.html')).read()
icon = re.search(r'<link rel="icon" href="([^"]+)"', open(os.path.join(ROOT,'breaks','cc871.html')).read()).group(1)
items = json.load(open(os.path.join(HERE,'index.json')))
items.append(dict(id='cc874', title='CC874 Monster Multi: Random Letter', kicker='Colfax Collectibles · Random letter · Multi-sport', when='Sunday, November 22, 2026, 5:00 pm Central', facts=['7 boxes', '21 letter spots']))
order = ['cc871', 'cc872', 'cc874', 'jwj0246', 'jwj0247', 'jwj0244']
items.sort(key=lambda x: order.index(x['id']))
def esc(s): return s.replace('&','&amp;').replace('<','&lt;')
cards = ''.join(f'''<a class="tile" href="/breaks/{i['id']}"><div class="kicker" style="font-size:11px">{esc(i['kicker'])}</div><div class="lab display" style="font-size:26px;margin-top:6px">{esc(i['title'])}</div><div class="cnt" style="margin-top:8px">{esc(i['when'])}</div><div class="peek">{esc(' · '.join(i['facts']))}</div></a>''' for i in items)
html = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Break Guides | Main Event Card Vault</title><meta name="theme-color" content="#081524"><link rel="icon" href="{icon}">
<style>{css}
.grid {{ grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }}
.bar .bmenu {{ margin-left: auto; }}
/*BMENU-CSS*//*/BMENU-CSS*/
</style></head><body>
<header class="site"><div class="wrap"><div class="bar"><a class="brand" href="/"><img src="{icon}" alt=""><div><b class="display">Main Event Card Vault</b><span>Break guides</span></div></a><!--BMENU--><!--/BMENU--></div></div></header>
<div class="wrap hero"><div class="kicker">Spot guides</div><h1 class="display">Break guides</h1>
<p class="lede">Who you could pull in each spot, box by box, built from the published checklists. Pick-your-letter breaks show which spots are still open and what they cost.</p></div>
<main class="wrap"><div class="grid">{cards}</div></main>
<footer><div class="wrap">Main Event Card Vault. Reference only; confirm checklists and house rules with the breaker.</div></footer>
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
.bmenu-list { position: absolute; right: 0; top: calc(100% + 8px); z-index: 80; width: 340px; max-width: calc(100vw - 24px); background: #0d1f38;
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
    m = re.match(r'(CC\d+|JWJ #\d+)\s*[:\-]?\s*(.*)', title)
    return (m.group(1), m.group(2)) if m else ('', title)

def menu_html(current=None):
    links = []
    for i in items:
        code, name = code_and_name(i['title'])
        parts = i['kicker'].split(' · ')
        host = parts[0].replace(' Collectibles', '').replace(' Collector Breaks', '')
        meta = ' · '.join([host] + parts[1:] + [short_date(i['when'])])
        cls = ' class="on"' if i['id'] == current else (' class="past"' if 'has passed' in i['when'] else '')
        links.append(f'<a href="/breaks/{i["id"]}"{cls}><b>{esc(code)}</b>{esc(name)}<span>{esc(meta)}</span></a>')
    links.append('<a class="all" href="/breaks/">All break guides</a>')
    return '<!--BMENU--><details class="bmenu"><summary>Breaks</summary><div class="bmenu-list">' + ''.join(links) + '</div></details>' + MENU_JS + '<!--/BMENU-->'

def fill(path, current=None):
    s = open(path).read()
    s = re.sub(r'<!--BMENU-->.*?<!--/BMENU-->', lambda m: menu_html(current), s, count=1, flags=re.S)
    s = re.sub(r'/\*BMENU-CSS\*/.*?/\*/BMENU-CSS\*/', lambda m: '/*BMENU-CSS*/' + MENU_CSS + '/*/BMENU-CSS*/', s, count=1, flags=re.S)
    open(path, 'w').write(s)

for i in items:
    fill(os.path.join(ROOT, 'breaks', i['id'] + '.html'), i['id'])
fill(os.path.join(ROOT, 'breaks', 'index.html'))
fill(os.path.join(ROOT, 'build', 'template.html'))
print('menu written to', len(items) + 2, 'files')
