"""Topps pack odds for the Spot Builder's Player value setting.

topps.com/pages/odds links one odds PDF per product. Convert each with `pdftotext -layout` into
<txt_dir>/<product_id>.txt, then:

  python3 build/breaks/odds_parse.py <txt_dir> <cards_dir> [<cards_dir> ...]

That writes build/breaks/odds.json {product_id: {SUBSET NAME: packs per hit}}, using the first pack type
listed on the row (normally hobby) and the most common version of each set (its base or most plentiful
parallel). depth.py reads odds.json; sets with no odds row count as average.
"""
import re, json, glob, os, collections
TOK = re.compile(r'^(?:-|1:[\d,]+(?:\.\d+)?|\d+:\d[\d,]*)$')
def words(s):
    s = re.sub(r'[^A-Z0-9 ]', ' ', s.upper().replace('&', ' AND '))
    out = []
    for w in s.split():
        if len(w) > 3 and w.endswith('S') and not w.endswith('SS'): w = w[:-1]
        out.append(w)
    return out
def rows(txt):
    R = []
    for line in txt.split('\n'):
        parts = re.split(r'\s{2,}|\s(?=1:\d)|\s(?=-\s)', line.strip())
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < 2: continue
        i = 0
        while i < len(parts) and not TOK.match(parts[i]): i += 1
        if i == 0 or i == len(parts): continue
        label = ' '.join(parts[:i]); vals = parts[i:]
        odds = []
        for v in vals:
            m = re.match(r'^(\d+):([\d,]+(?:\.\d+)?)$', v)
            if m and m.group(2).replace(',', ''): odds.append(float(m.group(2).replace(',', '')) / float(m.group(1)))
        odds = [o for o in odds if o > 0]
        if not odds: continue
        R.append((words(label), odds[0], label))
    return R
NOISE = {'I', 'II', 'III', 'IV', 'CARD', 'SET', 'THE'}
def find(R, subset):
    sw = words(subset)
    if not sw: return None
    m = [o for w, o, _ in R if w[:len(sw)] == sw]
    if m: return min(m)
    core = [w for w in sw if w not in NOISE]
    if core and core != sw:
        m = [o for w, o, _ in R if [x for x in w if x not in NOISE][:len(core)] == core]
        if m: return min(m)
    s = set(core)
    if len(s) >= 2:
        m = [o for w, o, _ in R if s <= set(w)]
        if m: return min(m)
    return None


if __name__ == '__main__':
    import sys
    HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
    import checklist_parse as P
    txt_dir, cdirs = sys.argv[1], sys.argv[2:]
    out_path = os.path.join(HERE, 'odds.json')
    OD = json.load(open(out_path)) if os.path.exists(out_path) else {}
    cf = {os.path.basename(f)[:-11]: f for d in cdirs for f in glob.glob(os.path.join(d, '*.cards.json'))}
    for t in sorted(glob.glob(os.path.join(txt_dir, '*.txt'))):
        pid = os.path.basename(t)[:-4]
        if pid not in cf: continue
        R = rows(open(t).read()); d = {}
        for c in json.load(open(cf[pid])):
            sub, sec = c['subset'], c['group']
            if sec == 'base' and not (re.search(r'AUTOGRAPH|SIGNATURE', sub, re.I) or P.AUTO_WORDS.search(sub)): continue
            if sub not in d: d[sub] = find(R, sub)
        OD[pid] = {k: round(v, 1) for k, v in d.items() if v}
    json.dump(OD, open(out_path, 'w'), indent=0, sort_keys=True)
    print(len(OD), 'products,', sum(len(v) for v in OD.values()), 'sets with odds')
