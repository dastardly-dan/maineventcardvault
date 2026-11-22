"""Parser used on 2026-11-22 to turn official Topps checklist PDFs/xls into checklists/*.txt.
Turn official Topps checklists into Spot Builder library files.

Each source is first flattened to "layout lines" (code, 2+ spaces, name, 2+ spaces, team/brand,
2+ spaces, tag), the same shape pdftotext -layout gives, then one parser handles all of them.
"""
import re, sys, json, collections

GROUPS = {'BASE': 'base', 'INSERT': 'insert', 'INSERTS': 'insert', 'AUTOGRAPH': 'auto', 'AUTOGRAPHS': 'auto',
          'RELIC': 'insert', 'RELICS': 'insert', 'AUTOGRAPH RELIC': 'auto', 'AUTOGRAPH RELICS': 'auto'}
SKIP_SUBSETS = re.compile(r'SKETCH|PRINTING PLATE|REDEMPTION|BOOK CARD|MOMENTS|LOMBARDI TROPHY', re.I)
AUTO_WORDS = re.compile(r'AUTOGRAPH|SIGNATURE|\bINK\b|MARKS|CALLIGRAPHY|CHROMOGRAPH|SIGNED|TRACES|INKED', re.I)
TAGS = {'Rookie', 'RC', 'DEBUT', 'Debut', 'Rookie Debut', 'SP', 'SSP'}
WWE_BRANDS = ['Smackdown', 'SmackDown', 'Raw', 'NXT', 'Legend', 'WWE', 'Hall of Fame', 'AAA', 'TNA', 'Alumni']
NFL = ('Cardinals Falcons Ravens Bills Panthers Bears Bengals Browns Cowboys Broncos Lions Packers Texans Colts '
       'Jaguars Chiefs Raiders Chargers Rams Dolphins Vikings Patriots Saints Giants Jets Eagles Steelers 49ers '
       'Seahawks Buccaneers Titans Commanders Redskins Oilers').split()
NBA = ('Hawks Celtics Nets Hornets Bulls Cavaliers Mavericks Nuggets Pistons Warriors Rockets Pacers Clippers Lakers '
       'Grizzlies Heat Bucks Timberwolves Pelicans Knicks Thunder Magic 76ers Suns Kings Spurs Raptors Jazz Wizards '
       'SuperSonics Supersonics Bobcats Bullets').split() + ['Trail Blazers']
CITIES = ['Arizona', 'Atlanta', 'Baltimore', 'Buffalo', 'Carolina', 'Chicago', 'Cincinnati', 'Cleveland', 'Dallas', 'Denver',
          'Detroit', 'Green Bay', 'Houston', 'Indianapolis', 'Jacksonville', 'Kansas City', 'Las Vegas', 'Los Angeles', 'Miami',
          'Minnesota', 'New England', 'New Orleans', 'New York', 'Philadelphia', 'Pittsburgh', 'San Francisco', 'Seattle',
          'Tampa Bay', 'Tennessee', 'Washington', 'San Diego', 'St. Louis', 'Oakland', 'Boston', 'Brooklyn', 'Charlotte',
          'Golden State', 'Indiana', 'LA', 'Memphis', 'Milwaukee', 'New Jersey', 'Oklahoma City', 'Orlando', 'Phoenix',
          'Portland', 'Sacramento', 'San Antonio', 'Toronto', 'Utah', 'Vancouver', 'Houston']
CODE = re.compile(r'^([A-Z0-9][A-Za-z0-9\-\.]*)(\s+)(.*)$')


def clean(s):
    s = s.replace('™', '').replace('®', '').replace('“', '"').replace('”', '"').replace('’', "'")
    return re.sub(r'\s+', ' ', s).strip()


def peel_team(name, teams):
    """'Channing "Stacks" LorenzoNXT' or '"The American Nightmare" Smackdown' -> (name, team)."""
    for t in sorted(teams, key=len, reverse=True):
        prefix = '' if t in WWE_BRANDS else '(?:(?:' + '|'.join(re.escape(c) for c in CITIES) + r')\s)?'
        m = re.match(r'^(.*?)(?:\s+|(?<=[a-z\.]))(' + prefix + re.escape(t) + r')$', name)
        if m and m.group(1).strip():
            return m.group(1).strip(), m.group(2).strip()
    return name, ''


def is_team(x, teams):
    return bool(teams) and any(x == t or x.endswith(' ' + t) for t in teams)


def nickname(team):
    if not team: return ''
    if team.endswith('Trail Blazers'): return 'Trail Blazers'
    return team.split()[-1]


def parse_lines(lines, cfg):
    teams = cfg.get('teams', [])
    group, subset = None, ''
    cards = []          # dicts: group, subset, code, name, team, tag
    gap = True
    last_card = False
    for raw in lines:
        if not raw.strip():
            gap = True; continue
        s = raw.rstrip()
        st = s.strip()
        if st.startswith('Checklists provided') or 'actual contents and odds' in st or 'production, but' in st \
                or st in ('vary.', 'he time of production, but actual contents and odds may vary.'):
            continue
        indent = len(s) - len(s.lstrip())
        up = st.upper() == st and re.search(r'[A-Z]', st)
        if st.upper() in GROUPS and indent < 10:
            group = GROUPS[st.upper()]; subset = ''; continue
        m = CODE.match(st)
        is_card = False
        if m:
            code, sp, rest = m.groups()
            if len(sp) >= 2 and rest:
                is_card = True
            elif code.isdigit() and (re.search(r'[a-z]', rest) or indent >= 3 or
                                     (len(rest.split()) == 1 and not re.search('TOPPS|AUTOGRAPH', rest))):
                is_card = True
        if not is_card and up and indent < 10 and not cfg.get('nocode_names'):
            subset = st; continue
        if not is_card and up and indent < 10 and cfg.get('nocode_names') and len(st.split()) > 1 and '  ' not in st:
            subset = st; continue
        was_gap, gap = gap, False
        if is_card and re.fullmatch(r'(19|20)\d\d', code) and rest.startswith('Topps'):
            continue
        if is_card:
            last_card = True
            cells = [clean(c) for c in re.split(r'\s{2,}', rest) if clean(c)]
            tagc = [x for x in cells[1:] if x in TAGS]
            cells = [cells[0]] + [x for x in cells[1:] if x not in TAGS] if cells else cells
        else:
            # continuation of the card above (wrapped name, team or tag), or a code-less row
            cells = [clean(c) for c in re.split(r'\s{2,}', st) if clean(c)]
            if indent >= 10 and cards and len(cells) == 1 and not was_gap and last_card:
                c = cards[-1]; txt = cells[0]
                if txt in TAGS: c['tag'] = c['tag'] or txt
                elif is_team(txt, teams) and not c['team']: c['team'] = txt
                else:
                    n2, t2 = peel_team(txt, teams)
                    c['name'] = clean(c['name'] + ' ' + n2)
                    if t2 and not c['team']: c['team'] = t2
                continue
            last_card = False
            if st in TAGS: continue
            if not cfg.get('nocode_names'): continue
            code = ''
        if group is None: group = 'base'
        cards.append(dict(group=group, subset=subset, code=code if is_card else '', cells=cells,
                          name='', team='', tag=''))
        c = cards[-1]
        col = cfg.get('name_col', {}).get(group, 0)
        if cfg.get('auto_name_col') is not None and (group == 'auto' or AUTO_WORDS.search(subset)):
            col = cfg['auto_name_col']
        name = cells[col] if len(cells) > col else (cells[0] if cells else '')
        rest_cells = [x for i, x in enumerate(cells) if i != col and i != 0 or (i == 0 and col != 0 and False)]
        rest_cells = cells[1:] if col == 0 else cells[col + 1:]
        for x in rest_cells:
            if x in TAGS: c['tag'] = c['tag'] or x
            elif not c['team'] and (is_team(x, teams) or not teams): c['team'] = x
        if teams and not c['team']:
            name, t = peel_team(name, teams)
            c['team'] = t
        c['name'] = name
    return cards


def bucket(cards, cfg):
    """-> ordered dict section -> list of entries (each entry a list of (name, team))."""
    out = collections.OrderedDict((k, []) for k in ('base', 'auto', 'insert', 'multi'))
    seen = {k: set() for k in out}
    # group multi-person cards: consecutive rows sharing a code inside one subset
    i = 0
    while i < len(cards):
        c = cards[i]; grp = [c]
        while c['code'] and i + len(grp) < len(cards):
            n = cards[i + len(grp)]
            if n['code'] == c['code'] and n['subset'] == c['subset'] and not c['code'].isdigit():
                grp.append(n)
            else: break
        i += len(grp)
        if SKIP_SUBSETS.search(c['subset']): continue
        if cfg.get('skip_subsets') and re.search(cfg['skip_subsets'], c['subset']): continue
        sec = c['group']
        if sec != 'auto' and AUTO_WORDS.search(c['subset']): sec = 'auto'
        people = []
        for g in grp:
            for nm in re.split(r'\s*(?:&|/)\s*(?=[A-Z"])', g['name']) if (' & ' in g['name'] or re.search(r'[A-Za-z\.]\s*/\s*[A-Z"]', g['name'])) and cfg.get('split_amp', True) else [g['name']]:
                nm = clean(nm)
                if nm and nm not in cfg.get('drop_names', ()) and not re.match(r'QB [A-Z]', nm):
                    people.append((cfg.get('alias', {}).get(nm, nm), g['team']))
        people = list(dict.fromkeys(people))
        if not people: continue
        if len(people) > 1 and len({p[0] for p in people}) > 1:
            key = tuple(p[0] for p in people)
            if key not in seen['multi']: seen['multi'].add(key); out['multi'].append(people)
            continue
        p = people[0]
        key = p
        if key not in seen[sec]: seen[sec].add(key); out[sec].append([p])
    # merge spelling variants (accents, Jr./II suffixes) to the most common form
    import unicodedata
    def k(n):
        n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower()
        n = re.sub(r'\b(jr|sr|ii|iii|iv)\b\.?', '', n)
        return re.sub(r'[^a-z0-9]', '', n)
    cnt = collections.Counter(p[0] for v in out.values() for e in v for p in e)
    teams_of = collections.defaultdict(set)
    for v in out.values():
        for e in v:
            for p in e: teams_of[p[0]].add(nickname(p[1]))
    def k2(n):
        base = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower()
        return re.sub(r'[^a-z0-9]', '', base)
    canon = {}
    for n in cnt:
        canon.setdefault(k2(n), []).append(n)
    # suffix-only differences (Kevin Porter / Kevin Porter Jr.) merge only when they share a team
    for n in cnt:
        for m in cnt:
            if n < m and k(n) == k(m) and k2(n) != k2(m) and (teams_of[n] & teams_of[m] - {''}):
                a, b = canon[k2(n)], canon[k2(m)]
                if a is not b:
                    a.extend(b)
                    for x in b: canon[k2(x)] = a
    best = {n: max(v, key=lambda x: (cnt[x], len(x))) for v in canon.values() for n in v}
    for sec, v in out.items():
        new, s2 = [], set()
        for e in v:
            e2 = [(best[p[0]], p[1]) for p in e]
            key = tuple(e2)
            if key not in s2: s2.add(key); new.append(e2)
        out[sec] = new
    return out


def write(path, meta, out, cfg, women=frozenset()):
    team_mode = cfg.get('team_mode')
    def fmt(p):
        n, t = p
        s = n
        if team_mode and t: s += ' | ' + nickname(t)
        if n in women: s += ' | W'
        return s
    L = ['# name: ' + meta['name'], '# sport: ' + meta['sport'], '# added: ' + meta['added'],
         '# source: ' + meta['source']]
    if meta.get('note'): L.append('# note: ' + meta['note'])
    for sec, ents in out.items():
        if not ents: continue
        L.append(''); L.append('[' + sec + ']')
        if sec == 'multi':
            L += [' / '.join(fmt(p) for p in e) for e in ents]
        else:
            L += sorted({fmt(e[0]) for e in ents}, key=lambda x: x.lower().lstrip('"'))
    open(path, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
