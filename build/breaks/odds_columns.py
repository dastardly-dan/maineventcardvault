import pdfplumber, re, json, sys, statistics
VAL = re.compile(r'^(?:-|\d+:[\d,]+(?:\.\d+)?)$')
VOCAB = set('''HOBBY JUMBO BREAKER BREAKERS DELIGHT SAPPHIRE MEGA BOX BOXES VALUE HANGER FAT BLASTER RETAIL SUPER FANATICS SILVER
CELLO COSTCO SAMS SAM'S CLUB WALMART WM TARGET COLLECTOR KIT HTA CHOICE FDI FIRST DAY ISSUE LITE COMPLETE SET EXCLUSIVE EXCLUSIV EX CHINA
WAVE 1 2 3 ALL STAR GAME PROMO BLACK FRIDAY VB OVERSIZED BULK LONDON GAMES KIDS EA SE MONSTER TIN TINS ASIA JAPAN INTERNATIONAL INT'L
LOGOFRACTOR GIANT GRAVITY TRAINING CAMP AUTO MINI QUAD TRIPLE DOUBLE FACTORY STARTER BUNDLE GIFT HOLIDAY CHROME JUMBOS PACKAGE
BREAKERS' DELUXE ULTRA HYBRID PREMIUM EDITION'''.split())
def lines_of(words, tol=3):
    L = []
    for w in sorted(words, key=lambda w: (round(w['top']), w['x0'])):
        for l in L:
            if abs(l['top'] - w['top']) <= tol: l['w'].append(w); break
        else: L.append({'top': w['top'], 'w': [w]})
    for l in L: l['w'].sort(key=lambda w: w['x0'])
    return sorted(L, key=lambda l: l['top'])
def cluster(xs, tol=14):
    xs = sorted(xs); C = []
    for x in xs:
        if C and x - C[-1][-1] <= tol: C[-1].append(x)
        else: C.append([x])
    return [statistics.median(c) for c in C if len(c) >= 2]
def parse(path):
    types = None; rows = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(keep_blank_chars=False, use_text_flow=False, x_tolerance=1.5)
            L = lines_of(words)
            vals = [w for w in words if VAL.match(w['text'])]
            if not vals: continue
            import collections as _c
            cnt = _c.Counter(sum(1 for w in l['w'] if VAL.match(w['text'])) for l in L if sum(1 for w in l['w'] if ':' in w['text'] and VAL.match(w['text'])) >= 1)
            K = max(cnt.items(), key=lambda kv: (kv[1], kv[0]))[0] if cnt else 0
            opts = []
            for mode in ('c', 'r', 'l'):
                f = (lambda w: (w['x0'] + w['x1']) / 2) if mode == 'c' else (lambda w: w['x1']) if mode == 'r' else (lambda w: w['x0'])
                cl = cluster([f(w) for w in vals], tol=10)
                if cl: opts.append((abs(len(cl) - K), {'c': 0, 'r': 1, 'l': 2}[mode], cl, mode))
            if not opts: continue
            _, _, cols, mode = min(opts)
            def pos(w): return (w['x0'] + w['x1']) / 2 if mode == 'c' else w['x1'] if mode == 'r' else w['x0']
            left = min(cols) - 30
            first = None
            for i, l in enumerate(L):
                if any(':' in w['text'] and VAL.match(w['text']) for w in l['w']) and any(not VAL.match(w['text']) and w['x1'] < left for w in l['w']): first = i; break
            if first is None: continue
            # header words go to the column whose values sit under them (by value centers)
            byc = [[] for _ in cols]
            for w in vals:
                j = min(range(len(cols)), key=lambda j: abs(cols[j] - pos(w)))
                if abs(cols[j] - pos(w)) <= 12: byc[j].append((w['x0'] + w['x1']) / 2)
            cen = [statistics.median(b) if b else cols[j] for j, b in enumerate(byc)]
            hdr = [[] for _ in cols]
            for l in L[max(0, first - 10):first]:
                for w in l['w']:
                    cx = (w['x0'] + w['x1']) / 2
                    if w['x1'] < left: continue
                    cx = cx if mode == 'c' else (w['x1'] if mode == 'r' else w['x0']) if False else cx
                    j = min(range(len(cen)), key=lambda j: abs(cen[j] - cx))
                    if abs(cen[j] - cx) < 45: hdr[j].append(w['text'])
            names = []
            for h in hdr:
                ws = [x for x in h if x.upper().strip('.,:;()') in VOCAB]
                out = []
                for x in ws:
                    if not out or out[-1].upper() != x.upper(): out.append(x)
                names.append(' '.join(out).strip())
            if any(names) and (types is None or len(names) >= len(types)): types = names
            for l in L[first:]:
                lab = ' '.join(w['text'] for w in l['w'] if w['x1'] < left and not VAL.match(w['text']))
                vs = [w for w in l['w'] if VAL.match(w['text']) and w['x0'] >= left - 5]
                if not lab or not vs: continue
                od = [None] * len(cols)
                for w in vs:
                    cx = pos(w)
                    j = min(range(len(cols)), key=lambda j: abs(cols[j] - cx))
                    if abs(cols[j] - cx) > 40: continue
                    t = w['text']
                    if t == '-': od[j] = 0
                    else:
                        a, b = t.split(':'); b = b.replace(',', '')
                        od[j] = float(b) / float(a) if b and float(a) else None
                rows.append((lab, od, len(cols)))
    return types or [], rows
if __name__ == '__main__':
    t, R = parse(sys.argv[1]); print(t); print(len(R)); [print(r) for r in R[:4]]
