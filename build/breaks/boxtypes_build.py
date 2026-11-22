import json, re, sys
sys.path.insert(0, '.'); import oddsparse as O
CANON = [('Sapphire', r'SAPPHIRE'), ('LogoFractor', r'LOGOFRACTOR'), ("Breaker's Delight", r'BREAKER|DELIGHT'),
         ('First Day Issue', r'\bFDI\b|DAY ISSUE'), ('Jumbo (HTA)', r'\bHTA\b'), ('Jumbo', r'JUMBO'), ('Hobby', r'HOBBY'),
         ('Mega Box', r'\bMEGA\b'), ('Value Box', r'VALUE|BLASTER'), ('Hanger', r'HANGER'), ('Fat Pack', r'\bFAT\b')]
BAD = re.compile(r'SILVER|CHINA|PROMO|LONDON|EXCLUSIV|KIDS|SAMS|COSTCO|BLACK FRIDAY|ALL STAR|BULK|JAPAN|FANATICS|TARGET|CLUB|OVERSIZED|\bEA\b|\bSE\b|WAVE|TIN|COLLECTOR', re.I)
def canon(name):
    u = name.upper()
    if not u or BAD.search(u): return None
    for c, rx in CANON:
        if re.search(rx, u): return c
    return None
cols = json.load(open('cols.json')); old = json.load(open('/home/claude/maineventcardvault/build/breaks/odds.json'))
OUT = {}; rep = []
for pid, d in sorted(cols.items()):
    T = d['types']; n = len(T)
    rows = [(O.words(lab), od) for lab, od, k in d['rows'] if k == n and n]
    seen = {}; types = []
    for i, t in enumerate(T):
        c = canon(t)
        if c and c not in seen: seen[c] = i; types.append((c, i))
    # headings checked by hand against the PDF where the auto read is off
    FIX = {'2026-topps-flagship-football': [('Hobby', 1), ('Jumbo', 3), ('Hanger', 4), ('Fat Pack', 5), ('Value Box', 6), ('Mega Box', 7)]}
    if pid in FIX: types = FIX[pid]; seen = {c: i for c, i in types}
    # per set, per type
    sets = {}
    for sub in old.get(pid, {}):
        sw = O.words(sub)
        m = [od for w, od in rows if w[:len(sw)] == sw]
        if not m:
            core = [x for x in sw if x not in O.NOISE]
            m = [od for w, od in rows if [x for x in w if x not in O.NOISE][:len(core)] == core]
        if not m:
            s = set(x for x in sw if x not in O.NOISE)
            if len(s) >= 2: m = [od for w, od in rows if s <= set(w)]
        if not m: continue
        v = []
        for c, i in types:
            pos = [od[i] for od in m if od[i]]
            v.append(round(min(pos), 1) if pos else 0)
        sets[sub] = v
    # validate: the first odds value on each matched row (what odds.json used) must match
    main = seen.get('Hobby', types[0][1] if types else None)
    mi = [i for c, i in types].index(main) if types else None
    agree = tot = 0
    for sub, o in old.get(pid, {}).items():
        sw = O.words(sub)
        m = [od for w, od in rows if w[:len(sw)] == sw]
        if not m: continue
        firsts = [next((x for x in od if x), None) for od in m]
        firsts = [x for x in firsts if x]
        if not firsts: continue
        tot += 1
        if abs(min(firsts) - o) / o < 0.02: agree += 1
    ok = len(types) >= 2 and tot >= 3 and agree / tot >= 0.85
    rep.append((pid, ok, f'{agree}/{tot}', [c for c, i in types]))
    if ok: OUT[pid] = {'types': [c for c, i in types], 'main': mi, 'sets': sets}
json.dump(OUT, open('/home/claude/maineventcardvault/build/breaks/boxtypes.json', 'w'), indent=0, sort_keys=True)
for r in rep: print(*r)
print(len(OUT), 'products with box types')
