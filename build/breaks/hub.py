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
</style></head><body>
<header class="site"><div class="wrap"><div class="bar"><a class="brand" href="/"><img src="{icon}" alt=""><div><b class="display">Main Event Card Vault</b><span>Break guides</span></div></a></div></div></header>
<div class="wrap hero"><div class="kicker">Spot guides</div><h1 class="display">Break guides</h1>
<p class="lede">Who you could pull in each spot, box by box, built from the published checklists. Pick-your-letter breaks show which spots are still open and what they cost.</p></div>
<main class="wrap"><div class="grid">{cards}</div></main>
<footer><div class="wrap">Main Event Card Vault. Reference only; confirm checklists and house rules with the breaker.</div></footer>
</body></html>'''
open(os.path.join(ROOT,'breaks','index.html'),'w').write(html)
print(len(html))
