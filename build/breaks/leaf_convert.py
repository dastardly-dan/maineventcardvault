"""Leaf Trading Cards checklists into the Spot Builder library.

Leaf posts one checklist per product on leaftradingcards.com/products/<id>: a Google Sheet (CSV export) or an
.xlsx file. Columns: Set, Subset, Name, Checklist, Foil, then one print-run column per parallel color (or a
Quantity column), then MEM, BASE (Auto / Signed On-Card / Base) and sometimes City Designation. Leaf is
unlicensed, so there are no team names; products go in their own "Leaf ..." sport groups.

  python3 build/breaks/leaf_convert.py <compact.json> <xlsx_dir>

compact.json: {product_id: "subset<TAB>name<TAB>kind<TAB>copies or U<TAB>city" lines}, made in the browser from
the CSV exports (kind A auto, I insert, B base). .xlsx files are read whole (every sheet).
Writes checklists/<id>.txt and adds Player value rarity (print runs, like Panini) to depth.json.
"""
import json, os, re, sys, glob, collections, statistics
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import depth as Dp

PRODUCTS = {  # id: (name, group)
 '2026-leaf-metal-happy-holidays': ('2026 Leaf Metal Happy Holidays', 'Leaf Multi-Sport'),
 '2025-26-leaf-nll': ('2025-26 Leaf NLL', 'Leaf Lacrosse'),
 '2026-leaf-red-carpet-collection': ('2026 Leaf Red Carpet Collection', 'Leaf Pop Culture'),
 '2026-leaf-paintworks-football': ('2026 Leaf Paintworks Football', 'Leaf Football'),
 '2026-leaf-sports-illustrated-for-kids-multi-sport': ('2026 Leaf Sports Illustrated For Kids Multi-Sport', 'Leaf Multi-Sport'),
 '2026-leaf-originals-multi-sport': ('2026 Leaf Originals Multi-Sport', 'Leaf Multi-Sport'),
 '2026-leaf-metal-golden-set-tennis': ('2026 Leaf Metal Golden Set Tennis', 'Leaf Tennis'),
 '2026-leaf-metal-halloween': ('2026 Leaf Metal Halloween', 'Leaf Multi-Sport'),
 '2026-leaf-football': ('2026 Leaf Football', 'Leaf Football'),
 '2026-leaf-city-of-champions': ('2026 Leaf City of Champions', 'Leaf Multi-Sport'),
 '2026-leaf-melange': ('2026 Leaf Melange', 'Leaf Multi-Sport'),
 '2026-leaf-autograph-collection-football': ('2026 Leaf Autograph Collection Football', 'Leaf Football'),
 '2026-leaf-ultimate-sports': ('2026 Leaf Ultimate Sports', 'Leaf Multi-Sport'),
 '2026-leaf-metal-women-of-sport': ('2026 Leaf Metal Women of Sport', 'Leaf Multi-Sport'),
 '2026-leaf-signature-series-sports': ('2026 Leaf Signature Series Sports', 'Leaf Multi-Sport'),
 '2026-leaf-trinity-football': ('2026 Leaf Trinity Football', 'Leaf Football'),
 '2026-leaf-decadence-multi-sport': ('2026 Leaf Decadence Multi-Sport', 'Leaf Multi-Sport'),
 '2026-leaf-seasons-in-the-sun-baseball': ('2026 Leaf Seasons in the Sun Baseball', 'Leaf Baseball'),
 '2026-pro-set-metal-football': ('2026 Pro Set Metal Football', 'Leaf Football'),
 '2026-leaf-art-of-sport': ('2026 Leaf Art of Sport', 'Leaf Multi-Sport'),
 '2026-leaf-national-redemption': ('2026 Leaf National Redemption', 'Leaf Multi-Sport'),
 '2026-leaf-metal-ring-kings': ('2026 Leaf Metal Ring Kings', 'Leaf Wrestling & MMA'),
 '2026-leaf-metal-draft-edition-baseball': ('2026 Leaf Metal Draft Edition Baseball', 'Leaf Baseball'),
 '2026-leaf-glory-of-the-game-soccer': ('2026 Leaf Glory of the Game Soccer', 'Leaf Soccer'),
 '2026-leaf-electrum-baseball': ('2026 Leaf Electrum Baseball', 'Leaf Baseball'),
 '2026-leaf-metal-independence-day': ('2026 Leaf Metal Independence Day', 'Leaf Multi-Sport'),
 '2026-leaf-spectacular-football': ('2026 Leaf Spectacular Football', 'Leaf Football'),
 '2026-leaf-vivid-baseball': ('2026 Leaf Vivid Baseball', 'Leaf Baseball'),
 '2026-leaf-metal-hockey': ('2026 Leaf Metal Hockey', 'Leaf Hockey'),
 '2026-pro-set-metal-baseball': ('2026 Pro Set Metal Baseball', 'Leaf Baseball'),
 '2026-leaf-optichrome-football': ('2026 Leaf Optichrome Football', 'Leaf Football'),
 '2026-leaf-baseball-nation': ('2026 Leaf Baseball Nation', 'Leaf Baseball'),
 '2026-leaf-magnificence-multi-sport': ('2026 Leaf Magnificence Multi-Sport', 'Leaf Multi-Sport'),
 '2025-leaf-eclectic-signature-series-joe-montana-celebration': ('2025 Leaf Eclectic Signature Series Joe Montana Celebration', 'Leaf Football'),
 '2026-leaf-bonus-pack': ('2026 Leaf Bonus Pack', 'Leaf Multi-Sport'),
 '2026-leaf-metal-baseball': ('2026 Leaf Metal Baseball', 'Leaf Baseball'),
 '2026-leaf-slideshow': ('2026 Leaf Slideshow', 'Leaf Pop Culture'),
 '2025-leaf-glory-of-the-game-basketball': ('2025 Leaf Glory of the Game Basketball', 'Leaf Basketball'),
 '2026-leaf-anime-nation-ova': ('2026 Leaf Anime Nation OVA', 'Leaf Pop Culture'),
 '2026-metallic-imaginations-series-3': ('2026 Leaf Metallic Imaginations Series 3', 'Leaf Pop Culture'),
 '2026-leaf-pop-century': ('2026 Leaf Metal Pop Century', 'Leaf Pop Culture'),
 '2025-leaf-optichrome-baseball': ('2025 Leaf Optichrome Baseball', 'Leaf Baseball'),
 '2026-leaf-metal-football': ('2026 Leaf Metal Football', 'Leaf Football'),
 '2026-leaf-metal-st-patricks-day': ("2026 Leaf Metal St. Patrick's Day", 'Leaf Multi-Sport'),
 '2026-leaf-paydirt-football': ('2026 Leaf PayDirt Football', 'Leaf Football'),
 '2025-leaf-in-the-game-used-sports': ('2025 Leaf In The Game Used Sports', 'Leaf Multi-Sport'),
 '2026-leaf-metal-presidents-day': ("2026 Leaf Metal Presidents' Day", 'Leaf Multi-Sport'),
 '2026-leaf-sports-heroes': ('2026 Leaf Sports Heroes', 'Leaf Multi-Sport'),
 '2025-leaf-electrum-multi-sport': ('2025 Leaf Electrum Multi-Sport', 'Leaf Multi-Sport'),
}
ALL_WOMEN = {'2026-leaf-metal-women-of-sport'}
SKIPC = re.compile(r'^(SET|SUBSET|NAME|NAME_OSCAR|CHECKLIST|FOIL|NOTE|NOTE_CARD|MEM|BASE|CITY DESIGNATION|REDEMPTION STATUS|PROMO)$')
PLATE = re.compile(r'printing plate|^plates?$', re.I)

def clean(n):
    n = str(n).replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
    return re.sub(r'\s+', ' ', n).strip()

def from_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    agg = {}
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True)); h = None
        for r in rows:
            cells = [str(c).strip() if c is not None else '' for c in r]
            up = [c.upper() for c in cells]
            if 'SUBSET' in up and any(u.startswith('NAME') for u in up):
                h = up; si = up.index('SUBSET'); ni = next(i for i, u in enumerate(up) if u.startswith('NAME'))
                bi = up.index('BASE') if 'BASE' in up else -1; mi = up.index('MEM') if 'MEM' in up else -1
                ci = up.index('CITY DESIGNATION') if 'CITY DESIGNATION' in up else -1; seti = up.index('SET') if 'SET' in up else -1
                continue
            if not h or len(cells) <= max(si, ni): continue
            nm, sub = cells[ni], cells[si]
            if not nm or not sub: continue
            b = cells[bi] if 0 <= bi < len(cells) else ''; m = cells[mi] if 0 <= mi < len(cells) else ''
            kind = 'A' if re.search(r'auto|signed', b, re.I) else ('I' if m == 'Yes' else ('B' if re.search(r'base', sub, re.I) else 'I'))
            tot, un = 0, False
            for j, c in enumerate(h):
                if j >= len(cells) or SKIPC.match(c) or j == seti or not c: continue
                v = cells[j].replace(',', '')
                if re.match(r'^\d+(\.0)?$', v): tot += int(float(v))
                elif re.search('unnumbered', v, re.I): un = True
            k = (sub, nm, kind)
            a = agg.setdefault(k, {'c': 0, 'u': False})
            a['c'] += tot; a['u'] = a['u'] or un or tot == 0
    return [(s, n, k, 'U' if a['u'] else a['c']) for (s, n, k), a in agg.items()]

def from_compact(text):
    out = []
    for line in text.split('\n'):
        p = line.split('\t')
        if len(p) >= 4: out.append((p[0], p[1], p[2], p[3] if p[3] == 'U' else int(p[3] or 0)))
    return out

def split_names(n):
    parts = [x.strip() for x in re.split(r'\s+/\s+|\s+&\s+(?=[A-Z"])', n) if x.strip()]
    return parts if len(parts) > 1 else [n]

def build(pid, rows):
    name, group = PRODUCTS[pid]
    W = ' | W' if pid in ALL_WOMEN else ''
    sec = {'base': set(), 'auto': set(), 'insert': set(), 'multi': set()}
    sets = collections.defaultdict(lambda: [set(), set(), set()])
    copies = collections.defaultdict(dict)
    for sub, nm, kind, c in rows:
        if PLATE.search(sub): continue
        nm = clean(nm); people = split_names(nm)
        if len(people) > 1:
            sec['multi'].add(' / '.join(p + W for p in people)); idx = 2
        else:
            sec[{'A': 'auto', 'I': 'insert', 'B': 'base'}[kind]].add(nm + W); idx = {'A': 0, 'I': 1}.get(kind)
        n = Dp.UNNUMBERED if c == 'U' else max(1, c)
        for p in people:
            if idx is not None: sets[Dp.key(p)][idx].add(sub)
            copies[sub][Dp.key(p)] = max(copies[sub].get(Dp.key(p), 0), n)
    rar = {s: 10000.0 / sorted(d.values())[len(d) // 2] for s, d in copies.items() if d}
    lines = [f'# name: {name}', f'# sport: {group}', '# added: 2026-11-22', f'# source: https://www.leaftradingcards.com/products/{pid}',
             '# note: Leaf is unlicensed: no team names, so team breaks are not available. Print runs from the official checklist.', '']
    for s in ('base', 'auto', 'insert', 'multi'):
        if sec[s]: lines += [f'[{s}]'] + sorted(sec[s], key=str.lower) + ['']
    open(os.path.join(HERE, 'checklists', pid + '.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    return Dp.pack(sets, rar), sum(len(v) for v in sec.values())

if __name__ == '__main__':
    compact = json.load(open(sys.argv[1])); xdir = sys.argv[2]
    dp = os.path.join(HERE, 'depth.json'); D = json.load(open(dp))
    for pid in PRODUCTS:
        x = os.path.join(xdir, pid + '.xlsx')
        rows = from_xlsx(x) if os.path.exists(x) else from_compact(compact.get(pid, ''))
        if not rows: print('NO DATA', pid); continue
        D[pid], n = build(pid, rows)
        print(f'{pid}: {n} entries, {len(D[pid])} with player value')
    json.dump(D, open(dp, 'w'), separators=(',', ':'), sort_keys=True)
