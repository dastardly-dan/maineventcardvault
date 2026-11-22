"""Hit depth: how many different autograph / insert / multi-person sets each player appears in, per product.

Card makers put their stars and top rookies into far more hit sets than role players, so this count is a
value signal that comes straight from the checklist. Output: depth.json {product_id: {name_key: [A, I, M]}}
(only players with a count above 1). builder.py attaches it to each checklist row.

  python3 build/breaks/depth.py <cards_dir> [<cards_dir> ...] [--panini <csv> <id> ...]

cards_dir holds <id>.cards.json files written by checklist_parse.parse_lines (one dict per card row with
group, subset, code, name). Panini CSVs are read directly; parallels are folded into their root set.
"""
import json, os, re, sys, glob, unicodedata, collections, csv

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checklist_parse as P
import panini_csv as PC

def key(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z]', '', n)

def from_cards(cards):
    sets = collections.defaultdict(lambda: [set(), set(), set()])
    i = 0
    while i < len(cards):
        c = cards[i]; grp = [c]
        while c['code'] and i + len(grp) < len(cards):
            n = cards[i + len(grp)]
            if n['code'] == c['code'] and n['subset'] == c['subset'] and not c['code'].isdigit(): grp.append(n)
            else: break
        i += len(grp)
        sub = c['subset']
        if P.SKIP_SUBSETS.search(sub) or re.match(r'^(ERAS|FACTIONS)$', sub): continue
        sec = c['group']
        if sec != 'auto' and (re.search(r'AUTOGRAPH|SIGNATURE', sub, re.I) or (sec == 'base' and P.AUTO_WORDS.search(sub))): sec = 'auto'
        names = []
        for g in grp:
            for nm in re.split(r'\s*(?:&|/)\s*(?=[A-Z"])', g['name']):
                if nm.strip(): names.append(nm.strip())
        multi = len({key(n) for n in names}) > 1
        idx = 2 if multi else {'auto': 0, 'insert': 1}.get(sec)
        if idx is None: continue
        for n in names: sets[key(n)][idx].add(sub or '(none)')
    return sets

def from_panini(path):
    rows = list(csv.DictReader(open(path, newline='', encoding='utf-8-sig')))
    allsets = sorted({(r['CARD SET'] or '').strip() for r in rows})
    root = {}
    for s in allsets:
        cands = [o for o in allsets if o != s and s.startswith(o + ' ')]
        root[s] = min(cands, key=len) if cands else s
    sets = collections.defaultdict(lambda: [set(), set(), set()])
    for r in rows:
        cs = (r['CARD SET'] or '').strip()
        if PC.SKIP.search(cs) or (r.get('POSITION') or '').strip() == 'Mascot': continue
        names = list(dict.fromkeys(n.strip() for n in (r['ATHLETE'] or '').split('/') if n.strip()))
        if not names: continue
        multi = len({key(n) for n in names}) > 1
        sec = PC.section(cs)
        idx = 2 if multi else {'auto': 0, 'insert': 1}.get(sec)
        if idx is None: continue
        for n in names: sets[key(n)][idx].add(root[cs])
    return sets

def pack(sets):
    out = {}
    for k, v in sets.items():
        c = [len(x) for x in v]
        if max(c) > 1: out[k] = c
    return out

if __name__ == '__main__':
    args = sys.argv[1:]
    out_path = os.path.join(HERE, 'depth.json')
    D = json.load(open(out_path)) if os.path.exists(out_path) else {}
    lib = {os.path.basename(f)[:-4] for f in glob.glob(os.path.join(HERE, 'checklists', '*.txt'))}
    if '--panini' in args:
        i = args.index('--panini'); pan = args[i + 1:]; args = args[:i]
        for csvp, pid in zip(pan[::2], pan[1::2]):
            D[pid] = pack(from_panini(csvp))
    for d in args:
        for f in sorted(glob.glob(os.path.join(d, '*.cards.json'))):
            pid = os.path.basename(f)[:-11]
            if pid in lib: D[pid] = pack(from_cards(json.load(open(f))))
    D = {k: v for k, v in D.items() if k in lib}
    json.dump(D, open(out_path, 'w'), separators=(',', ':'), sort_keys=True)
    print(len(D), 'products,', sum(len(v) for v in D.values()), 'players with depth > 1; missing:', sorted(lib - set(D)))
