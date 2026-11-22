import json, re, base64, os, sys, unicodedata
sys.path.insert(0, os.path.dirname(__file__))
import wwe_data as W
import team_data as TD

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'breaks')
ICON = 'data:image/png;base64,' + base64.b64encode(open(os.path.join(ROOT, 'assets', 'favicon.png'), 'rb').read()).decode()
TPL = open(os.path.join(os.path.dirname(__file__), 'template.html')).read()

def fold(s):
    return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode()

def split(s):
    return [x.strip() for x in s.split(';') if x.strip()]

# ---------------- letter helpers ----------------
ALIAS = {'Zelina': 'Zelina Vega', 'Nattie': 'Natalya', 'Hollywood Hulk Hogan': 'Hulk Hogan', '"Hollywood" Hulk Hogan': 'Hulk Hogan',
         'Iron Sheik': 'The Iron Sheik', 'Roddy Piper': '"Rowdy" Roddy Piper', 'Steve Austin': '"Stone Cold" Steve Austin',
         'Cody Rhodes': '"The American Nightmare" Cody Rhodes', 'Ted DiBiase': '"Million Dollar Man" Ted DiBiase',
         'Road Dogg Jesse James': '"Road Dogg" Jesse James', 'Kaydel Ko Connix': 'Kaydel Connix', 'Lieutenant Connix': 'Kaydel Connix',
         'Ranzar "Ran" Malk': 'Ranzar Malk', 'Brutus Beefcake': 'Brutus "The Barber" Beefcake'}

def key_of(name):
    n = re.sub(r'"[^"]*"', '', name)
    return ' '.join(n.split())

def first_char(s):
    s = fold(s).strip().lstrip('"\'(').strip()
    s = re.sub(r'^(the)\s+', '', s, flags=re.I).lstrip('"\'(')
    for ch in s:
        if ch.isalpha(): return ch.upper()
        if ch.isdigit(): return '#'
    return '?'

def letters(name):
    """printed letter (nickname counts, a leading 'The' doesn't), and the letter by real name if different"""
    p = first_char(name.replace('"', ''))
    a = first_char(key_of(name))
    return p, (a if a != p else None)

# ---------------- generic builder ----------------
def entries_from_product(prod, alias=True):
    """returns dict display_name -> set(flags) for one product (base/auto/insert/multi)"""
    out = {}
    def add(n, f):
        n = n.strip()
        if alias: n = ALIAS.get(n, n)
        out.setdefault(n, set())
        if f: out[n].add(f)
    for n in split(prod.get('base', '')): add(n, 'B')
    for n in split(prod.get('auto', '')): add(n, 'A')
    for n in split(prod.get('insert', '')): add(n, 'I')
    for card in split(prod.get('multi', '')):
        for n in card.split(' / '): add(n, 'M')
    return out

def letter_break(cfg, products, gender_of=None, alt=True):
    names = {s['id']: {} for s in cfg['spots']}
    unmatched = []
    for box in cfg['boxes']:
        ents = entries_from_product(products[box['k']])
        for n, flags in sorted(ents.items(), key=lambda x: fold(x[0]).lower()):
            p, a = letters(n)
            g = gender_of(n) if gender_of else None
            hit = False
            for L, extra in ((p, ''), (a, '?')):
                if not L or (extra and not alt): continue
                for s in cfg['spots']:
                    if L in s['letters'] and (s.get('g') is None or s['g'] == g):
                        f = ''.join(sorted(flags - {'B'})) + extra
                        if 'B' not in flags and not flags & {'A', 'I', 'M'}: f += ''
                        names[s['id']].setdefault(box['k'], []).append([n, f, 'B' in flags])
                        hit = True
            if not hit:
                unmatched.append([n, box['short']])
    return names, unmatched

def team_break(cfg, products):
    names = {s['id']: {} for s in cfg['spots']}
    unmatched = []
    team_to_spot = {}
    for s in cfg['spots']:
        for t in s['teams']: team_to_spot[t] = s['id']
    for box in cfg['boxes']:
        prod = products[box['k']]
        per = {}
        for team, ns in prod['base'].items():
            for n in ns: per.setdefault((team, n), set()).add('B')
        for team, ns in prod.get('other', {}).items():
            for n in ns: per.setdefault((team, n), set()).add('A')
        for (team, n), flags in sorted(per.items(), key=lambda x: fold(x[0][1]).lower()):
            sid = team_to_spot.get(team)
            if not sid:
                unmatched.append([n + ' (' + team + ')', box['short']]); continue
            names[sid].setdefault(box['k'], []).append([n, 'A' if flags == {'A'} else '', 'B' in flags])
    return names, unmatched

def write(cfg, names, unmatched):
    data = dict(cfg)
    data['names'] = names
    data['unmatched'] = unmatched
    html = TPL.replace('__ICON__', ICON).replace('__TITLE__', cfg['title']).replace(
        '__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, cfg['id'] + '.html')
    open(path, 'w').write(html)
    total = sum(len(v) for s in names.values() for v in s.values())
    print(cfg['id'], 'spots', len(cfg['spots']), 'entries', total, 'unmatched', len(unmatched), len(html))
    return data

# ---------------- WWE breaks ----------------
WOMEN = {key_of(ALIAS.get(n, n)) for n in W.WOMEN} | set(W.WOMEN)
def wwe_gender(n):
    k = key_of(n)
    return 'F' if (k in WOMEN or n in W.WOMEN) else 'M'

WWE_PRODUCTS = {'sc': W.SC, 'chrome': W.CHROME, 'cosmic': W.COSMIC, 'sapphire': W.SAPPHIRE, 'logo': W.LOGO, 'exalted': W.EXALTED}
WWE_BOX = {
    'sc': dict(k='sc', short='Stadium Club', c='#5aa9ff', full='2026 Topps Stadium Club WWE Hobby', kind='200-card base, autographs (hard-signed and Chrome), inserts',
               types='Base, Chrome parallels, Photographer\'s Proof and Gold Minted parallels, inserts like Beam Team and Main Stage, autographs (2 per hobby box).'),
    'chrome': dict(k='chrome', short='Chrome', c='#f2c14e', full='2026 Topps Chrome WWE Hobby', kind='201-card base, autographs, inserts',
                   types='Base and Refractor parallels, inserts like Signalz, Gamut and Helix, autographs (2 per hobby box).'),
    'cosmic': dict(k='cosmic', short='Cosmic Chrome', c='#c86bff', full='2026 Topps Cosmic Chrome WWE Hobby', kind='200-card base, autographs, inserts',
                   types='Base with space-themed Refractors, inserts like Galaxy Greats and Planetary Pursuit, case hits like Cosmic Dust, autographs.'),
    'sapphire': dict(k='sapphire', short='Sapphire', c='#4fd1a5', full='2026 Topps Chrome WWE Sapphire', kind='201-card Sapphire base, autographs, inserts',
                     types='Sapphire versions of the Chrome base, Infinite Sapphire and Sapphire Selections inserts, 1 autograph per box.'),
    'logo': dict(k='logo', short='LogoFractor', c='#f2c14e', full='2026 Topps Chrome WWE LogoFractor', kind='Chrome base and inserts (LogoFractor autograph list not published)',
                 types='LogoFractor versions of the Chrome WWE base and inserts, plus LogoFractor Autographs (checklist not published yet).'),
    'exalted': dict(k='exalted', short='Exalted', c='#e2545e', full='Topps Exalted WWE (the "2025" set, released April 2026)', kind='100-card base, autographs, relics',
                    types='100-card foil base, several autograph sets and relics (multi-person relics included).'),
}
WWE_RULES = [
    ['First letter of the name printed on the card', ['A leading "The" doesn\'t count. The listing says so for the T spots, so The Rock is R and The Miz is M.', 'Men and Women spots split by who\'s on the card.']],
    ['Nicknames are the gray area', ['Some cards print a nickname first, like "The American Nightmare" Cody Rhodes or "Million Dollar Man" Ted DiBiase.', 'This guide files those under the printed nickname, and also lists them under the real-name letter with a "?" tag.', 'Ask the breaker which way they go before you buy on a nickname.']],
    ['Multi-person cards', ['Cards with two or more people (dual autos, tag team inserts, relics) are tagged "multi".', 'Breakers usually split these by rule or random draw, so check their house rules.']],
]
def wwe_spot(id, label, letters_, g=None, price=None, avail=None):
    return dict(id=id, label=label, letters=list(letters_), g=g, price=price, status=None if avail is None else ('open' if avail else 'sold'))

# CC871 Colfax Club & Chrome PYL
cc871_spots = [
    wwe_spot('ac-m', 'A & C', 'AC', 'M', 115, False), wwe_spot('a-w', 'A', 'A', 'F', 90, True),
    wwe_spot('b-m', 'B', 'B', 'M', 70, True), wwe_spot('b-w', 'B', 'B', 'F', 80, False),
    wwe_spot('c-w', 'C', 'C', 'F', 55, False), wwe_spot('d', 'D', 'D', None, 75, True),
    wwe_spot('ef', 'E & F', 'EF', None, 55, True), wwe_spot('g', 'G', 'G', None, 75, True),
    wwe_spot('h', 'H', 'H', None, 30, False), wwe_spot('i', 'I', 'I', None, 40, False),
    wwe_spot('j-m', 'J', 'J', 'M', 145, True), wwe_spot('j-w', 'J', 'J', 'F', 40, False),
    wwe_spot('k-m', 'K', 'K', 'M', 55, True), wwe_spot('k-w', 'K', 'K', 'F', 90, True),
    wwe_spot('l', 'L', 'L', None, 120, False), wwe_spot('m', 'M', 'M', None, 35, True),
    wwe_spot('n', 'N', 'N', None, 30, True), wwe_spot('o', 'O', 'O', None, 50, False),
    wwe_spot('pq', 'P & Q', 'PQ', None, 35, False), wwe_spot('r-m', 'R', 'R', 'M', 155, True),
    wwe_spot('r-w', 'R', 'R', 'F', 95, True), wwe_spot('s-m', 'S', 'S', 'M', 90, True),
    wwe_spot('s-w', 'S', 'S', 'F', 125, False), wwe_spot('t-m', 'T', 'T', 'M', 55, True),
    wwe_spot('t-w', 'T', 'T', 'F', 105, False), wwe_spot('uvw', 'U-V-W', 'UVW', None, 70, True),
    wwe_spot('xyz', 'X-Y-Z-123', 'XYZ#', None, 35, False),
]
cc871 = dict(
    id='cc871', title='CC871 Club & Chrome PYL', kicker='Colfax Collectibles · Pick your letter · WWE',
    url='https://colfaxcc.com/products/cc871-club-chrome-pyl-pick-your-letter',
    when='Sunday, November 22, 2026, 5:00 pm Central (6:00 pm Eastern)',
    facts=['4 boxes', '27 letter spots', '15 open, 12 sold as of 12:20 pm Eastern'],
    format='pyl', checked='Availability checked against Colfax\'s store data on November 22, 2026, around 12:20 pm Eastern. Spots sell fast, so check the live page before you buy.',
    boxes=[WWE_BOX[k] for k in ('sc', 'chrome', 'cosmic', 'sapphire')],
    spots=cc871_spots, rules=WWE_RULES,
    notes=['Sapphire uses the same 201 base subjects as Chrome, so most base names show up in both.',
           'Autograph and insert lists come from the published checklists. A name only in an autograph set is much harder to pull than a base card.'],
    sources=[['CC871 break page (Colfax Collectibles)', 'https://colfaxcc.com/products/cc871-club-chrome-pyl-pick-your-letter'],
             ['Stadium Club WWE checklist', 'https://www.checklistcenter.com/?p=63880'],
             ['Chrome WWE checklist', 'https://www.checklistcenter.com/2026-topps-chrome-wwe-wrestling-card-checklist/'],
             ['Cosmic Chrome WWE checklist', 'https://www.checklistcenter.com/2026-topps-cosmic-chrome-wwe-wrestling-card-checklist/'],
             ['Chrome WWE Sapphire checklist', 'https://www.checklistcenter.com/2026-topps-chrome-sapphire-wwe-wrestling-card-checklist/']],
)

# JWJ #0246 Cosmic Exalted Logo Club PYL
J = lambda *a: wwe_spot(*a)
jwj0246_spots = [
    J('a-m', 'A', 'A', 'M', 70, True), J('a-w', 'A', 'A', 'F', 95, False), J('b-m', 'B', 'B', 'M', 70, True), J('b-w', 'B', 'B', 'F', 90, False),
    J('c-m', 'C', 'C', 'M', 90, True), J('c-w', 'C', 'C', 'F', 60, False), J('d', 'D', 'D', None, 85, True), J('ef', 'E / F', 'EF', None, 60, True),
    J('g', 'G', 'G', None, 85, True), J('h', 'H', 'H', None, 35, False), J('i', 'I', 'I', None, 45, False), J('j-m', 'J', 'J', 'M', 155, True),
    J('j-w', 'J', 'J', 'F', 45, False), J('k-m', 'K', 'K', 'M', 60, False), J('k-w', 'K', 'K', 'F', 95, False), J('l', 'L', 'L', None, 130, False),
    J('m', 'M', 'M', None, 45, True), J('no', 'N / O', 'NO', None, 50, False), J('pq', 'P / Q', 'PQ', None, 50, True), J('r-m', 'R', 'R', 'M', 175, True),
    J('r-w', 'R', 'R', 'F', 105, False), J('s-m', 'S', 'S', 'M', 100, False), J('s-w', 'S', 'S', 'F', 135, False), J('t-m', 'T', 'T', 'M', 60, True),
    J('t-w', 'T', 'T', 'F', 115, False), J('uvw', 'U-V-W', 'UVW', None, 70, True), J('xyz', 'X / Y / Z / 123', 'XYZ#', None, 40, False),
]
jwj0246 = dict(
    id='jwj0246', title='JWJ #0246 Cosmic Exalted Logo Club PYL', kicker='JWJ Collector Breaks · Pick your letter · WWE',
    url='https://jwjcollectorbreaks.com/products/jwj-0246-exalted-space-club-pyl',
    when='Monday, November 23, 2026 (time not listed) on the JWJ Breaks YouTube channel',
    facts=['6 boxes', '27 letter spots', '13 open, 14 sold as of 12:20 pm Eastern'],
    format='pyl', checked='Availability checked against JWJ\'s store data on November 22, 2026, around 12:20 pm Eastern. The page itself showed only 1 item left, so check it live before you buy.',
    boxes=[dict(WWE_BOX['sc'], full='2026 Topps Stadium Club WWE Hobby (2 boxes)'), WWE_BOX['cosmic'],
           dict(WWE_BOX['logo'], full='2026 Topps Chrome WWE LogoFractor (2 boxes)'), WWE_BOX['exalted']],
    spots=jwj0246_spots, rules=WWE_RULES,
    notes=['LogoFractor reuses the Chrome WWE base and inserts, so those lists stand in for it. Its own LogoFractor Autographs checklist isn\'t published.',
           'The listing says "2026 Topps Exalted WWE". The only Exalted WWE set out is the one Topps calls 2025 (released April 2026), so that checklist is used here.',
           'Here A Men and C Men are separate spots, so "The American Nightmare" Cody Rhodes matters: he shows under A, and under C with a "?" tag.'],
    sources=[['JWJ #0246 break page', 'https://jwjcollectorbreaks.com/products/jwj-0246-exalted-space-club-pyl'],
             ['Stadium Club WWE checklist', 'https://www.checklistcenter.com/?p=63880'],
             ['Cosmic Chrome WWE checklist', 'https://www.checklistcenter.com/2026-topps-cosmic-chrome-wwe-wrestling-card-checklist/'],
             ['Chrome WWE checklist (LogoFractor base)', 'https://www.checklistcenter.com/2026-topps-chrome-wwe-wrestling-card-checklist/'],
             ['Exalted WWE checklist', 'https://www.diamondcardsonline.com/blog/2025-topps-exalted-wwe-wrestling-cards-checklist/']],
)

# ---------------- Star Wars random letter ----------------
def sw_spot(id, label, letters_):
    return dict(id=id, label=label, letters=list(letters_), g=None, price=None, status=None)
jwj0247_spots = [sw_spot(x.lower().replace('/', ''), x, x.replace('/', '')) for x in
                 ['A', 'B', 'C', 'D', 'E/F', 'G', 'H', 'I/N', 'J', 'K', 'L', 'M', 'O', 'P', 'Q/U', 'R', 'S', 'T/V/W/X/Y/Z']]
jwj0247 = dict(
    id='jwj0247', title='JWJ #0247 Chromed Up Galaxy', kicker='JWJ Collector Breaks · Random letter · Star Wars',
    url='https://jwjcollectorbreaks.com/products/jwj-0247-chromed-up-galaxy',
    when='Monday, November 23, 2026 (time not listed) on the JWJ Breaks YouTube channel',
    facts=['2 boxes', '18 letter spots', '$66 per spot', 'Letters randomized live'],
    format='random', checked='Spots were still available when checked on November 22, 2026. The store data titles this break "#0248", but the page and link say #0247.',
    boxes=[dict(k='swc', short='Chrome Star Wars', c='#f2c14e', full='2026 Topps Chrome Star Wars Hobby', kind='200 characters, autographs, inserts',
                types='200-character base with Refractors, inserts like Cosmic Crystals and Oblivion, cast autographs (1 per hobby box).'),
           dict(k='swg', short='Galaxy Chrome', c='#5aa9ff', full='2026 Topps Star Wars Galaxy Chrome', kind='100 art cards (by title), autographs, inserts',
                types='100 art cards filed by card title, inserts like Art of the Dark Side, autographs and sketch cards (about 1 per case).')],
    spots=jwj0247_spots,
    rules=[['First letter of the name on the card', ['A leading "The" is skipped here, so The Mandalorian is M. JWJ\'s page doesn\'t say how it handles "The", so ask.', 'Titles count as printed: General Grievous is G, Darth Vader is D, Jedi Master Sol is J.']],
           ['Galaxy Chrome base cards are art titles', ['Its base cards carry titles like "The Mandalorian\'s Escape", not just a character name. They\'re filed by title here, which is the shakiest part of this guide.']],
           ['Multi-character cards', ['Dual, triple and quad autos are tagged "multi". Each character is listed under their own letter.']]],
    notes=['Autographs list the character, not the actor.', 'Characters starting with a number (8D8) don\'t fit any letter here; see the list below.'],
    sources=[['JWJ #0247 break page', 'https://jwjcollectorbreaks.com/products/jwj-0247-chromed-up-galaxy'],
             ['Chrome Star Wars checklist', 'https://www.checklistcenter.com/2026-topps-chrome-star-wars-entertainment-card-checklist/'],
             ['Star Wars Galaxy Chrome checklist', 'https://www.checklistcenter.com/2026-topps-star-wars-galaxy-chrome-entertainment-card-checklist/']],
)

# ---------------- team breaks ----------------
def team_spot(id, label, teams, nil=None):
    return dict(id=id, label=label, teams=teams, nil=nil, price=None, status=None)
cc872_teams = [('49ers', None), ('Bears', None), ('Bengals', 'E'), ('Bills', 'I'), ('Broncos', 'T'), ('Browns', 'U/V/X/Y'), ('Buccaneers', None),
               ('Cardinals', None), ('Chargers', 'K'), ('Chiefs', 'G'), ('Colts', 'L'), ('Commanders', 'P'), ('Cowboys', None), ('Dolphins', 'B'),
               ('Eagles', 'R'), ('Falcons', 'J'), ('Giants', None), ('Jaguars', 'D'), ('Jets', None), ('Lions', 'W'), ('Packers', 'A'), ('Panthers', 'F'),
               ('Patriots', None), ('Raiders', None), ('Rams', None), ('Ravens', 'M'), ('Saints', 'O/Q/Z'), ('Seahawks', 'S'), ('Steelers', 'H'),
               ('Texans', 'C'), ('Titans', None), ('Vikings', 'N')]
cc872 = dict(
    id='cc872', title='CC872 Chrome, Absolute & Midnight (Random Team)', kicker='Colfax Collectibles · Random team · NFL',
    url='https://colfaxcc.com/products/cc872-chrome-absolute-midnight-random-team',
    when='Sunday, November 22, 2026, 5:00 pm Central (6:00 pm Eastern)',
    facts=['5 boxes', '32 team spots', '$95 per spot, $23.75 filler', 'Teams randomized live'],
    format='team', checked='When checked on November 22, 2026, the page showed 10 of 25 break spots and 3 of 28 filler spots filled. The description says 32 spots, so the counts don\'t match; ask Colfax.',
    boxes=[dict(k='chrome', short='Topps Chrome', c='#5aa9ff', full='2026 Topps Chrome Football Hobby (2 boxes)', kind='400-card base (300 veterans, 100 rookies), autographs',
                types='Base and Refractors, rookie cards, autographs including legends, inserts.'),
           dict(k='midnight', short='Midnight', c='#c86bff', full='2026 Topps Midnight Football Hobby', kind='100-card base, 3 autographs per box, inserts',
                types='Dark chrome base, rookie and veteran autographs (3 per hobby box), inserts like Night Night and Constellations.'),
           dict(k='absolute', short='Absolute', c='#e2545e', full='2026 Panini Absolute Football Hobby (2 boxes)', kind='College (NIL) players and retired legends, no NFL logos. Checklist not released yet.',
                types='Autographs and memorabilia of college players and retired greats, no NFL team logos. Panini hasn\'t published the full checklist.')],
    spots=[team_spot(t.lower(), t + (' + NIL ' + n if n else ''), [t], n) for t, n in cc872_teams],
    rules=[['Cards go to the team on the card', ['Colfax\'s rules: a card goes to the team listed on the front or back, not the jersey.', 'Retired players go to the team listed on their card. This guide files old franchises with today\'s team (Oilers to Titans, Redskins to Commanders, San Diego to the Chargers).']],
           ['NIL letters cover the college cards', ['Panini Absolute has no NFL logos, so its college players go by letter. 18 teams come with a letter; the other 14 don\'t.', 'The listing doesn\'t say whether that\'s first or last name. Ask Colfax.']],
           ['Multi-player cards', ['Colfax rules: non-numbered multi-team cards go to the top or left team on odd-numbered breaks; numbered ones and case hits get a dice roll or random.org.']]],
    notes=['Absolute\'s checklist isn\'t out, so its names aren\'t listed. NIL spots only show the letter they cover.',
           'Topps Chrome and Midnight cards are listed with the team the checklist gives them.'],
    sources=[['CC872 break page (Colfax Collectibles)', 'https://colfaxcc.com/products/cc872-chrome-absolute-midnight-random-team'],
             ['Colfax group break rules', 'https://colfaxcc.com/pages/rules'],
             ['Topps Chrome Football checklist', 'https://www.checklistcenter.com/?p=64386'],
             ['Topps Midnight Football checklist', 'https://www.checklistcenter.com/?p=64273'],
             ['Panini Absolute Football overview', 'https://www.checklistinsider.com/2026-panini-absolute-football']],
)
nba_spots = [('Hawks / Trail Blazers', ['Hawks', 'Trail Blazers']), ('Nets', ['Nets']), ('Celtics', ['Celtics']), ('Hornets', ['Hornets']),
             ('Bulls / Pacers', ['Bulls', 'Pacers']), ('Mavericks', ['Mavericks']), ('Nuggets', ['Nuggets']), ('Pistons', ['Pistons']),
             ('Warriors', ['Warriors']), ('Rockets', ['Rockets']), ('Clippers', ['Clippers']), ('Lakers', ['Lakers']), ('Grizzlies', ['Grizzlies']),
             ('Bucks', ['Bucks']), ('Timberwolves', ['Timberwolves']), ('Pelicans', ['Pelicans']), ('Knicks', ['Knicks']), ('Thunder', ['Thunder']),
             ('Magic', ['Magic']), ('76ers', ['76ers']), ('Suns / Heat', ['Suns', 'Heat']), ('Kings', ['Kings']), ('Spurs', ['Spurs']),
             ('Raptors', ['Raptors']), ('Jazz', ['Jazz']), ('Wizards', ['Wizards'])]
jwj0244 = dict(
    id='jwj0244', title='JWJ #0244 Balling on a Budget with Flagship NBA', kicker='JWJ Collector Breaks · Random team · NBA',
    url='https://jwjcollectorbreaks.com/products/jwj-0244-balling-on-a-budget-with-flagship-nba',
    when='Listed for November 16 on the JWJ Breaks YouTube channel (no time listed). That date has passed, so check whether it already ran.',
    facts=['3 boxes', '26 team spots listed', '$68 per spot', 'Teams randomized live'],
    format='team', checked='When checked on November 22, 2026, the page showed 6 spots left. It says 27 spots but lists 26 teams, and the Cleveland Cavaliers aren\'t on the list.',
    boxes=[dict(k='flag', short='Flagship', c='#f2c14e', full='2026-27 Topps Flagship Basketball (2 Hobby, 1 Jumbo)', kind='300-card base, autographs',
                types='300-card base with rookies and legends, base variations, inserts, autographs and relics (Jumbo adds an auto and a relic).')],
    spots=[team_spot(re.sub(r'[^a-z0-9]', '', l.lower()), l, t) for l, t in nba_spots],
    rules=[['Cards go to the team on the card', ['Legends count for the team printed on their card.', 'Seattle SuperSonics cards (Lenny Wilkens, Gary Payton) and every Cleveland Cavaliers card have no spot on JWJ\'s list. Ask JWJ where they go.']]],
    notes=['The autograph list is partial: the checklist page was too long to read in full, so some later autograph sets may be missing.',
           'Teams follow the checklist, which already reflects 2026-27 trades (Giannis shows up as both a Heat and a Bucks card, for example).'],
    sources=[['JWJ #0244 break page', 'https://jwjcollectorbreaks.com/products/jwj-0244-balling-on-a-budget-with-flagship-nba'],
             ['Topps Flagship Basketball checklist', 'https://www.checklistcenter.com/?p=64137']],
)

if __name__ == '__main__':
    built = []
    n, u = letter_break(cc871, WWE_PRODUCTS, wwe_gender); built.append(write(cc871, n, u))
    n, u = letter_break(jwj0246, WWE_PRODUCTS, wwe_gender); built.append(write(jwj0246, n, u))
    n, u = letter_break(jwj0247, {'swc': TD.SW_CHROME, 'swg': TD.SW_GALAXY}, None, alt=False); built.append(write(jwj0247, n, u))
    n, u = team_break(cc872, {'chrome': TD.NFL_CHROME, 'midnight': TD.NFL_MIDNIGHT, 'absolute': dict(base={}, other={})}); built.append(write(cc872, n, u))
    n, u = team_break(jwj0244, {'flag': TD.NBA_FLAGSHIP}); built.append(write(jwj0244, n, u))
    json.dump([{k: b[k] for k in ('id', 'title', 'kicker', 'when', 'facts')} for b in built], open(os.path.join(os.path.dirname(__file__), 'index.json'), 'w'))
    for b in built:
        if b['unmatched']: print(b['id'], 'UNMATCHED', b['unmatched'][:40])
