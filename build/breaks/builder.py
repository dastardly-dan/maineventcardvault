"""Builds breaks/builder.html (the Spot Builder) from every checklist in build/breaks/checklists/.

Checklist file format (one file per product, UTF-8 text):

    # name: 2026 Topps Stadium Club WWE
    # sport: WWE
    # added: 2026-11-22
    # source: https://...
    # note: optional one-liner shown in the builder

    [base]
    Name
    Name | W            (W = a woman, for Men/Women splits)
    Name | Team         (team products: any other text after | is the team)
    [auto]
    ...
    [insert]
    ...
    [multi]
    Name A / Name B     (cards with 2+ people; each person is listed)

Run:  python3 build/breaks/builder.py   then   python3 build/breaks/hub.py
"""
import json, os, re, glob, base64

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SECTION_FLAG = {'base': 'B', 'auto': 'A', 'autos': 'A', 'autograph': 'A', 'autographs': 'A', 'hits': 'A',
                'insert': 'I', 'inserts': 'I', 'multi': 'M'}

def parse(path):
    meta, entries, sec = {}, {}, 'base'
    for raw in open(path, encoding='utf-8'):
        line = raw.strip()
        if not line: continue
        m = re.match(r'#\s*(\w+)\s*:\s*(.*)', line)
        if m: meta[m.group(1).lower()] = m.group(2).strip(); continue
        if line.startswith('#'): continue
        m = re.match(r'\[(\w+)\]', line)
        if m: sec = m.group(1).lower(); continue
        flag = SECTION_FLAG.get(sec, 'B')
        people = line.split(' / ') if flag == 'M' or ' / ' in line else [line]
        for p in people:
            parts = [x.strip() for x in p.split('|')]
            name, g, team = parts[0], '', ''
            for extra in parts[1:]:
                if extra.upper() in ('W', 'F', 'WOMEN', 'WOMAN'): g = 'F'
                elif extra.upper() in ('M', 'MEN', 'MAN'): g = 'M'
                elif extra: team = extra
            if not name: continue
            f = 'M' if (len(people) > 1) else flag
            e = entries.setdefault(name, {'f': set(), 'g': '', 't': set()})
            e['f'].add(f)
            if g: e['g'] = g
            if team: e['t'].add(team)
    pid = os.path.splitext(os.path.basename(path))[0]
    rows = [[n, ''.join(sorted(e['f'])), e['g'], '/'.join(sorted(e['t']))] for n, e in sorted(entries.items())]
    return dict(id=pid, name=meta.get('name', pid), sport=meta.get('sport', 'Other'), added=meta.get('added', ''),
                source=meta.get('source', ''), note=meta.get('note', ''), gender=any(r[2] == 'F' for r in rows), rows=rows)

def dkey(n):
    import unicodedata
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z]', '', n)

def main():
    prods = [parse(p) for p in sorted(glob.glob(os.path.join(HERE, 'checklists', '*.txt')))]
    # hit depth (see depth.py): append [autoSets, insertSets, multiSets] to rows where any is above 1
    dp = os.path.join(HERE, 'depth.json')
    D = json.load(open(dp)) if os.path.exists(dp) else {}
    for p in prods:
        d = D.get(p['id'], {})
        for r in p['rows']:
            v = d.get(dkey(r[0]))
            if v: r.append(v)
    # box types (Hobby, Jumbo, Breaker's Delight...): per-type set odds, and each row's set list instead of fixed values
    tp = os.path.join(HERE, 'typedrows.json')
    TR = json.load(open(tp)) if os.path.exists(tp) else {}
    for p in prods:
        t = TR.get(p['id'])
        if not t: continue
        p['types'] = t['types']; p['main'] = t['main']
        p['sets'] = [[k, [int(round(x)) if x >= 1 else round(x, 2) for x in o] if o else 0] for k, o in t['sets']]
        for r in p['rows']:
            del r[4:]
            v = t['players'].get(dkey(r[0]))
            if v: r.append(v)
    order = ['WWE', 'MLW', 'UFC', 'MMA', 'NFL', 'NBA', 'WNBA', 'NBL', 'EuroLeague', 'MLB', 'USA Baseball', 'Soccer', 'F1', 'Olympics', 'Marvel', 'Star Wars', 'Disney', 'Pokemon', 'Entertainment', 'Other']
    prods.sort(key=lambda p: (order.index(p['sport']) if p['sport'] in order else 99, p['name']))
    css = open(os.path.join(HERE, 'base.css')).read()
    icon = 'data:image/png;base64,' + base64.b64encode(open(os.path.join(ROOT, 'assets', 'favicon.png'), 'rb').read()).decode()
    tpl = open(os.path.join(HERE, 'builder_template.html'), encoding='utf-8').read()
    html = (tpl.replace('__CSS__', css).replace('__ICON__', icon)
               .replace('__DATA__', json.dumps(prods, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')))
    out = os.path.join(ROOT, 'breaks', 'builder.html')
    open(out, 'w', encoding='utf-8').write(html)
    print('builder.html', len(html), 'bytes,', len(prods), 'checklists,', sum(len(p['rows']) for p in prods), 'names')

if __name__ == '__main__':
    main()
