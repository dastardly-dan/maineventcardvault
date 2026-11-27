"""Special hits (Daniel, Nov 27, 2026: "they pulled a Browns WR dual auto, we should list those types of hits as well").

The checklist files keep each player's kinds of cards (base, auto, insert, multi) but not the set names, so a dual
autograph showed up only as two "multi" tags. This keeps every multi-player card by its set name in hits.json:

  {library id: [[set name, "auto" or "insert", [[name, team], ...]], ...]}

build.py then lists each card under the spots its players land in ("Special hits" on the guide and the Watch page).

  python3 build/breaks/hits.py --topps <file.cards.json> ...      Topps checklists flattened by checklist_parse.py
  python3 build/breaks/hits.py --panini <file.csv> <library id>   official Panini checklist CSV
Existing products are replaced, the rest kept.
"""
import csv, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'hits.json')
AUTO = re.compile(r'Signature|Autograph|\bAutos?\b|\bInk\b|\bMarks\b|Initials|Inscription|Signed|Penmanship|Script|Signing|\bSigs?\b|Pen Pals|Chromograph', re.I)
SKIP = re.compile(r'Printing Plate|Redemption|Sketch|Mascot', re.I)
# Panini lists every parallel as its own set ("Dual Autographs Prizms Gold"); keep the set it comes from
PARALLEL = re.compile(r'\s+(Prizms?|Holo|Refractors?|Parallel|Shimmer|Gold|Silver|Black|Blue|Red|Green|Orange|Purple|Pink|Bronze|Platinum|Choice|Mojo|Wave|Scope|Disco|Lazer|Pulsar|Ice|Velocity|Cracked|Zebra|Tiger|Camo|Celestial|Lattice|Breakaway|FOTL|Vinyl|Circles|Snakeskin|Neon|Tie-Dye|Die-Cut).*$', re.I)


def title(s):
    s = ' '.join(s.split())
    if not s.isupper(): return s
    t = s.title().replace("'S ", "'s ")
    for ab in ('FDI', 'RC', 'WWE', 'NFL', 'MLB', 'NBA', 'NXT', 'UFC', 'DC', 'USA', 'II', 'III', 'IV', 'MVP', 'HOF', 'ROY', '1/1', 'NIL', 'F1'):
        t = re.sub(r'\b' + re.escape(ab.title()) + r'\b', ab, t)
    return t


def from_topps(path):
    cards = json.load(open(path, encoding='utf-8'))
    by = {}
    for c in cards:
        if c['group'] == 'base' or SKIP.search(c['subset']): continue
        k = (c['subset'], c['code'])
        if '/' in c['name']:   # one row for the whole card: "Josh Allen/Jim Kelly", team "Buffalo Bills" or "Houston Oilers/Tennessee Titans"
            ns, ts = [x.strip() for x in c['name'].split('/')], [x.strip() for x in (c.get('team') or '').split('/')]
            for j, n in enumerate(ns):
                by.setdefault(k, []).append([n, ts[j] if j < len(ts) else ts[0] if ts else ''])
        else:
            by.setdefault(k, []).append([c['name'], c.get('team', '')])
    out, seen = [], set()
    for (sub, code), ps in by.items():
        ps = [p for i, p in enumerate(ps) if p[0] not in [q[0] for q in ps[:i]]]
        if len(ps) < 2: continue
        grp = next(c['group'] for c in cards if c['subset'] == sub)
        kind = 'auto' if grp == 'auto' or AUTO.search(sub) else 'insert'
        key = (title(sub), tuple(p[0] for p in ps))
        if key in seen: continue
        seen.add(key); out.append([title(sub), kind, ps])
    return out


def from_panini(path):
    rows = list(csv.DictReader(open(path, encoding='utf-8-sig')))
    out, seen = [], {}
    for r in rows:
        a = r.get('ATHLETE') or ''
        if '/' not in a or SKIP.search(r['CARD SET']): continue
        names = [x.strip() for x in a.split('/')]
        teams = [x.strip() for x in (r.get('TEAM') or '').split('/')]
        if len(set(names)) < 2: continue
        base = PARALLEL.sub('', r['CARD SET']).strip() or r['CARD SET']
        key = tuple(names)
        if key in seen and len(seen[key][0]) <= len(base): continue   # the shortest set name is the one the parallels come from
        ps = [[n, teams[i] if i < len(teams) else ''] for i, n in enumerate(names)]
        seen[key] = [base, 'auto' if AUTO.search(base) else 'insert', ps]
    return list(seen.values())


def main(args):
    H = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    lib = {f[:-4] for f in os.listdir(os.path.join(HERE, 'checklists')) if f.endswith('.txt')}
    mode, i = None, 0
    while i < len(args):
        a = args[i]
        if a in ('--topps', '--panini'): mode = a; i += 1; continue
        if mode == '--topps':
            pid = os.path.basename(a)[:-len('.cards.json')]
            if pid in lib:
                H[pid] = from_topps(a)
            i += 1
        elif mode == '--panini':
            pid = args[i + 1]
            H[pid] = from_panini(a); i += 2
        else:
            i += 1
    H = {k: v for k, v in H.items() if k in lib}
    json.dump(H, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    print(len(H), 'products,', sum(len(v) for v in H.values()), 'multi-player cards,',
          sum(1 for v in H.values() for c in v if c[1] == 'auto'), 'of them autographs')


if __name__ == '__main__':
    main(sys.argv[1:])
