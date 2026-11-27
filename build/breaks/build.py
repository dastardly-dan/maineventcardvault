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

def first_two(s, n=2):
    """first two letters (or n), for spots split on the second letter (CA-CH) or the third (JA-JAR); a leading 'The' doesn't count"""
    s = fold(s).strip().lstrip('"\'(').strip()
    s = re.sub(r'^(the)\s+', '', s, flags=re.I).lstrip('"\'(')
    return ''.join(ch for ch in s if ch.isalpha())[:n].upper()

def in_spot(s, L, key):
    """key is the name's first three letters; each bound is compared at its own length, so two-letter ranges behave as before"""
    return L in s['letters'] or any(lo <= key[:len(lo)] and key[:len(hi)] <= hi for lo, hi in s.get('pre', []))

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
    # Hybrid breaks sell some wrestlers on their own ('who'): all of that wrestler's cards go to their spot,
    # and the letter spots ('all others') skip them.
    named = {fold(key_of(w)).lower(): s['id'] for s in cfg['spots'] for w in s.get('who', [])}
    for box in cfg['boxes']:
        ents = entries_from_product(products[box['k']])
        for n, flags in sorted(ents.items(), key=lambda x: fold(x[0]).lower()):
            sid = named.get(fold(key_of(n)).lower())
            if sid:
                names[sid].setdefault(box['k'], []).append([n, ''.join(sorted(flags - {'B'})), 'B' in flags])
                continue
            p, a = letters(n)
            g = gender_of(n) if gender_of else None
            hit = False
            for L, extra, two in ((p, '', first_two(n.replace('"', ''), 3)), (a, '?', first_two(key_of(n), 3))):
                if not L or (extra and not alt): continue
                for s in cfg['spots']:
                    if (in_spot(s, L, two) and (s.get('g') is None or s['g'] == g)) or L in s.get('anyg', ''):
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
        nil_to_spot = {}
        for s in cfg['spots']:
            for l in (s.get('nil') or '').replace('/', ''): nil_to_spot[l] = s['id']
        for n, flags in sorted(prod.get('nil', {}).items(), key=lambda x: fold(x[0]).lower()):
            sid = nil_to_spot.get(first_char(n))
            if not sid:
                unmatched.append([n + ' (college, NIL ' + first_char(n) + ')', box['short']]); continue
            names[sid].setdefault(box['k'], []).append([n, ('A' if flags == {'A'} else '') + 'N', 'B' in flags])
    return names, unmatched

# Breaker pages: a plain white page so everything is easy to read, with the breaker's brand in the header
# band, the accent color (spot names, buttons, links) and a soft tint behind the title.
# Colors read from each store and logo (Nov 23, 2026): Acme Packs forest green and gold logo; JWJ leather
# brown, cream and rust; Colfax black site, red #c8102e buttons, purple #6420a0, purple-to-red logo.
# Open (green) and sold (red) keep their meaning on every page.
THEMES = {
    'acme': dict(hdr='#173d0e', accent='#2f6b1a', accentrgb='47,107,26', link='#2a5f16', hon='#f2c14a', honink='#1d2a08', tint='#edf5e8',
                 brandline='linear-gradient(90deg,#f2c14a,#f7d77f 50%,#f2c14a)'),
    'jwj': dict(hdr='#2e1d12', accent='#a63a1f', accentrgb='166,58,31', link='#8f3119', hon='#f0dcc0', honink='#2e1d12', tint='#f8efe4',
                brandline='linear-gradient(90deg,#ab2d1a,#f0dcc0 50%,#ab2d1a)'),
    'rgl': dict(hdr='#1d1f23', accent='#1f5fbf', accentrgb='31,95,191', link='#1a4fa0', hon='#ffffff', honink='#1d1f23', tint='#eef2f8',
                brandline='linear-gradient(90deg,#1f5fbf,#ffffff 50%,#1f5fbf)'),  # neutral until RGL's own colors are confirmed
    'colfax': dict(hdr='#000000', accent='#6420a0', accentrgb='100,32,160', link='#571c8c', hon='#c8102e', honink='#ffffff', tint='#f2ecfa',
                   brandline='linear-gradient(90deg,#6420a0,#c8102e)'),
}
LIGHT_CSS = """
:root { --bg: #ffffff; --bg-2: #f4f5f7; --panel: #ffffff; --panel-2: #f7f8fa; --line: #e2e5ea; --line-2: #cfd4db;
  --ink: #16191d; --ink-2: #3d434b; --ink-3: #69707a; --gold: %(accent)s; --gold-2: %(link)s; --gold-rgb: %(accentrgb)s; --on-gold: #ffffff;
  --hdr: %(hdr)s; --brandline: %(brandline)s; --hon: %(hon)s; --honink: %(honink)s; --tint: %(tint)s; }
body { background: linear-gradient(180deg, var(--tint) 0, #ffffff 420px) no-repeat, #ffffff; }
header.site { background: var(--hdr); backdrop-filter: none; border-bottom: 0;
  --ink: #ffffff; --ink-2: rgba(255,255,255,.82); --ink-3: rgba(255,255,255,.66); --line-2: rgba(255,255,255,.28); --bg-2: rgba(255,255,255,.1); --panel: rgba(255,255,255,.1); }
header.site .search input::placeholder { color: rgba(255,255,255,.6); }
header.site { color: #ffffff; }
header.site .search input { color: #ffffff; }
header.site .search input:focus { outline-color: var(--hon); }
header.site .bmenu > summary::after { border-color: var(--hon); }
.bmenu-list { color: #16191d; }
nav.tabs a.on { background: var(--hon); color: var(--honink); }
.bmenu-list { --ink: #16191d; --ink-2: #3d434b; --ink-3: #69707a; --line: #e2e5ea; --line-2: #cfd4db; --bg-2: #f4f5f7; background: #ffffff !important; box-shadow: 0 12px 32px rgba(0,0,0,.18); }
.bmenu-list a:hover { background: #f4f5f7; }
.tile, .box, .avail, .card, .res, table.rows { box-shadow: 0 1px 2px rgba(16,24,40,.05); }
.tile:hover { box-shadow: 0 6px 18px rgba(16,24,40,.08); }
.ended { background: #f4f5f7; }
.chip.on:not([style]) { color: #ffffff; }
.badge.open { background: #e7f6ed; color: #17663a; border-color: #9fd7b5; }
.badge.sold { background: #fdecee; color: #a3202d; border-color: #f1b3ba; }
.badge.price { background: rgba(var(--gold-rgb),.08); color: var(--gold); border-color: rgba(var(--gold-rgb),.35); }
.tag.m { color: #3557b7; } .tag.q { color: #a3202d; } .tag.i { color: #17663a; }
.tag.n { background: #e8f0fe; color: #1f4fa8; border-color: #b7cdf5; }
.ix .sp a.sold { color: #a3202d; border-color: #f1b3ba; }
.ix .sp a.open { color: #17663a; border-color: #9fd7b5; }
mark { background: #fff1a8; }
.dots i { box-shadow: inset 0 0 0 1px rgba(0,0,0,.14); }
.tile.sold { opacity: .6; }
"""
def breaker_of(cid): return 'acme' if cid.startswith('gb') else 'jwj' if cid.startswith('jwj') else 'colfax' if cid.startswith('cc') else 'rgl' if cid.startswith('rgl') else ''
def theme_css(key):
    t = THEMES.get(key)
    return LIGHT_CSS % t if t else ''

# Each breaker's title card image, saved by the watcher (watch/images.json), keyed by store and product handle.
SHOP_OF = {'acmepackscards.com': 'acme', 'jwjcollectorbreaks.com': 'jwj', 'colfaxcc.com': 'colfax', 'rungoodlife.com': 'rgl'}
_ip = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'watch', 'images.json')
IMAGES = json.load(open(_ip)) if os.path.exists(_ip) else {}
def image_of(url, width=800):
    m = re.match(r'https?://(?:www\.)?([^/]+)/products/([^/?#]+)', url or '')
    src = IMAGES.get(SHOP_OF.get(m.group(1), ''), {}).get(m.group(2), '') if m else ''
    return (src + ('&' if '?' in src else '?') + 'width=%d' % width) if src else ''

# Kaboom inserts (Daniel, Nov 24: "for the Panini breaks, make sure you list which cards are Kabooms"), from the official
# Panini CSVs' card set names, saved in kabooms.json. Box key -> checklist id.
KABOOMS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kabooms.json'), encoding='utf-8'))
KABOOM_BOX = {'absolute': '2026-panini-absolute-football'}
def mark_kabooms(cfg, names):
    """Adds K to each Kaboom name's flags and returns rule lines listing the Kabooms by spot."""
    lab = {s['id']: s['label'] for s in cfg['spots']}
    by_spot = {}
    spot = {s['id']: s for s in cfg['spots']}
    for b in cfg['boxes']:
        kd = KABOOMS.get(KABOOM_BOX.get(b['k'], ''), {})
        if not kd: continue
        # the team each Kaboom card goes to, resolved the way absolute_product sorts every card (None = NIL)
        home = {key_of(n): [nfl_team(t) or ABS_ROSTER.get(key_of(n)) for t in v['teams']] for n, v in kd.items()}
        for sid, boxes in names.items():
            for e in boxes.get(b['k'], []):
                h = home.get(key_of(e[0]))
                if h is None: continue
                if ('N' in e[1] and None in h) or any(t in spot[sid].get('teams', []) for t in h if t):
                    if 'K' not in e[1]: e[1] += 'K'
                    by_spot.setdefault(sid, []).append(e[0].strip())
    if not by_spot: return None
    order = [s['id'] for s in cfg['spots'] if s['id'] in by_spot]
    n = len({x for v in by_spot.values() for x in v})
    return ['Kabooms in this break', ['Kaboom is Panini\'s rare comic-style insert. ' + str(n) + ' players have one in the Absolute checklist; each is tagged KABOOM in the spot their Kaboom card goes to. Panini doesn\'t say how many are in a case, so a full case may have none or a few.']
            + [lab[sid] + ': ' + ', '.join(sorted(set(by_spot[sid]), key=lambda x: fold(x).lower())) for sid in order]]

# eBay asking prices (Daniel, Nov 24; changed Nov 25): prices.py looks up "<product> <player>" for every name in these
# breaks and saves watch/prices.json. Break pages never show them (Daniel's call after a breaker's concern); the Spot
# Builder (builder.py) reads them as an optional "Market prices" weighting instead. This only registers the targets.
PRICE_TARGETS = {}
def box_query(b):
    q = re.sub(r'\(.*?\)', '', b['full'])
    q = re.sub(r'\b(Hobby|Jumbo|Mega|Blaster|Value|Boxes|Box|Case|Breaker\'s Delight)\b', '', q)
    return ' '.join(q.split())
def add_prices(cfg, names):
    """registers each player for the daily eBay price job (nothing is added to the page)"""
    for b in cfg['boxes']:
        bq = box_query(b)
        for boxes in names.values():
            for e in boxes.get(b['k'], []):
                player = key_of(e[0]).strip()
                if not player: continue
                q = bq + ' ' + player
                PRICE_TARGETS[q] = {'q': q, 'player': player}

# Breaker streams (Daniel, Nov 25, 2026): the page shows the YouTube player in place of the title card.
# One stream covers a whole break night, so each video lists the pages it covers. After the stream ends the same link is the replay.
STREAMS = {
    'Ck782vibiC0': dict(title='RGL Pre-Thanksgiving Marathon Stream (RGL #6128 to #6143)',
                        pages=['rgl6128', 'rgl612xwwe2'] + ['rgl%d' % n for n in range(6129, 6144)]),
}
VIDEO_OF = {pid: (vid, v['title']) for vid, v in STREAMS.items() for pid in v['pages']}
# Run Good Life also posts one video per break on its second channel, @rungoodbreaks (Daniel, Nov 26, 2026). A page listed in
# break_videos.json shows its own break video instead of the night's marathon stream; pages not listed keep the stream.
_BV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'break_videos.json')
BREAK_VIDEOS = {k: v for k, v in json.load(open(_BV)).items() if not k.startswith('_')} if os.path.exists(_BV) else {}
def video_secs(t):
    """a start time as seconds: 4521, '1:15:21', '75:21', or '1h15m21s'"""
    if t in (None, ''): return 0
    if isinstance(t, (int, float)): return int(t)
    t = str(t).strip().lower()
    m = re.fullmatch(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?', t)
    if m and any(m.groups()): return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)
    secs = 0
    for part in t.split(':'): secs = secs * 60 + int(part)
    return secs
# The watcher also records each breaker's current stream (watch/streams.json). A page gets the stream from the same
# breaker on the same night, unless STREAMS already set one: RGL by the date in its product link (11-25-26, Pacific),
# and the others by the date in the page's "when" line. RGL pages titled JML use the JML Breaks stream.
_SP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'watch', 'streams.json')
AUTO_STREAM = {}
if os.path.exists(_SP):
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo as _Z
    for _key, _st in json.load(open(_SP)).items():
        _when = _st.get('started') or _st.get('first_start')
        if _st.get('video') and _when:
            _t = _dt.fromisoformat(_when)
            AUTO_STREAM[_key] = (_st['video'], _st.get('title') or 'Break stream', _t.astimezone(_Z('America/Los_Angeles')).strftime('%m-%d-%y'),
                                 _t.astimezone(_Z('America/New_York')).strftime('%B %-d, %Y'))
def auto_stream(cfg):
    shop = breaker_of(cfg['id'])
    key = ('jml' if 'jml' in (cfg.get('title') or '').lower() else 'rgl') if shop == 'rgl' else shop
    s = AUTO_STREAM.get(key)
    if not s:
        return None
    if shop == 'rgl':
        return s[:2] if s[2] in (cfg.get('url') or '') else None
    return s[:2] if s[3] in (cfg.get('when') or '') else None

# Wikipedia links beside names (Nov 26, 2026). Per page: [word Wikipedia's one-line description must contain, "(sport)" title suffix to try].
# Entertainment pages (Star Wars, Marvel, Disney, Marvel Rivals) are left out: those names are characters, not people.
_NFL, _MLB, _NBA = [['football', 'American football']], [['baseball', 'baseball']], [['basketball', 'basketball']]
_WWE, _UFC, _NASCAR = [['wrestl', 'wrestler']], [['martial', 'fighter']], [['racing', 'racing driver']]
WIKI_BY_ID = {}
for _ids, _h in ((('cc872', 'gb1037', 'gb1038a', 'gb1038b', 'gb1041', 'gb1043', 'gb1044', 'rgl6130', 'rgl6132', 'rgl6136', 'rgl6140', 'rgl6145'), _NFL),
                  (('gb1042', 'rgl6129', 'rgl6134', 'rgl6137', 'rgl6138', 'rgl6146', 'cc876'), _MLB), (('jwj0244', 'rgl6131', 'rgl6139', 'rgl6147'), _NBA),
                  (('cc871', 'cc878', 'rgl6144', 'jwj0246', 'jwj0247u', 'rgl6128', 'rgl612xwwe2'), _WWE), (('rgl6142',), _UFC), (('cc875', 'rgl6133'), _NASCAR),
                  (('gb1045',), _NFL + _NBA), (('rgl6148',), [['footballer', 'footballer']]), (('gb1040',), _NFL + _UFC + _NBA + _MLB + _WWE), (('rgl6141',), _NFL + _MLB + _NBA)):
    for _i in _ids: WIKI_BY_ID[_i] = _h

def write(cfg, names, unmatched):
    data = dict(cfg)
    if cfg['id'] in WIKI_BY_ID: data['wiki'] = WIKI_BY_ID[cfg['id']]
    add_prices(cfg, names)   # eBay prices feed the Spot Builder only; break pages never show them
    data['breakerName'] = cfg.get('kicker', '').split(' · ')[0]
    kr = mark_kabooms(cfg, names)
    if kr: data['rules'] = list(cfg.get('rules', [])) + [kr]
    if not data.get('image') and image_of(cfg.get('url')): data['image'] = image_of(cfg['url'])  # a config's own image wins
    if cfg['id'] in BREAK_VIDEOS:
        _bv = BREAK_VIDEOS[cfg['id']]
        data['video'], data['videoTitle'], data['videoKind'] = _bv['video'], _bv.get('title') or 'Break stream', _bv.get('kind', 'break')
        if _bv.get('start') not in (None, ''): data['videoStart'] = video_secs(_bv['start'])   # kind 'stream': one long stream, opened at this break
    elif cfg['id'] in VIDEO_OF: data['video'], data['videoTitle'] = VIDEO_OF[cfg['id']]
    elif auto_stream(cfg):
        data['video'], data['videoTitle'] = auto_stream(cfg)
    if cfg.get('ended'): data['spots'] = [{k: v for k, v in s.items() if k != 'status'} for s in cfg['spots']]
    data['names'] = names
    data['unmatched'] = unmatched
    th = breaker_of(cfg['id'])
    html = TPL.replace('__THEME__', theme_css(th)).replace('__THEMECOLOR__', THEMES[th]['hdr'] if th else '#081524').replace('__ICON__', ICON).replace('__TITLE__', cfg['title']).replace(
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
    'logo': dict(k='logo', short='LogoFractor', c='#f2c14e', full='2026 Topps Chrome WWE LogoFractor', kind='201-card LogoFractor base, 89 LogoFractor Autographs, 3 insert sets',
                 types='LogoFractor versions of the Chrome WWE base, Eras of Excellence, Focus Reel and WrestleMania Recall inserts, plus LogoFractor Autographs.'),
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
             ['Stadium Club WWE checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Stadium_Club_WWE_-_Checklist.pdf?v=1791221305'],
             ['Chrome WWE checklist', 'https://www.checklistcenter.com/2026-topps-chrome-wwe-wrestling-card-checklist/'],
             ['Cosmic Chrome WWE checklist (matches the official Topps list)', 'https://www.checklistcenter.com/2026-topps-cosmic-chrome-wwe-wrestling-card-checklist/'],
             ['Chrome WWE Sapphire checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/FINAL_CHECKLIST_2026TOPPSCHROMEWWE_SAPPHIRE_1.pdf?v=1777570435']],
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
    when='Monday, November 23, 2026, 8:00 pm Eastern on the JWJ Breaks YouTube channel',
    facts=['6 boxes', '27 letter spots'],
    live=dict(shop='jwj', handle='jwj-0246-exalted-space-club-pyl'),
    format='pyl', checked='Availability checked against JWJ\'s store data on November 22, 2026, around 12:20 pm Eastern. The page itself showed only 1 item left, so check it live before you buy.',
    boxes=[dict(WWE_BOX['sc'], full='2026 Topps Stadium Club WWE Hobby (2 boxes)'), WWE_BOX['cosmic'],
           dict(WWE_BOX['logo'], full='2026 Topps Chrome WWE LogoFractor (2 boxes)'), WWE_BOX['exalted']],
    spots=jwj0246_spots, rules=WWE_RULES,
    notes=['LogoFractor reuses the Chrome WWE base and inserts, so those lists stand in for it. Its own LogoFractor Autographs checklist isn\'t published.',
           'The listing says "2026 Topps Exalted WWE". The only Exalted WWE set out is the one Topps calls 2025 (released April 2026), so that checklist is used here.',
           'Here A Men and C Men are separate spots, so "The American Nightmare" Cody Rhodes matters: he shows under A, and under C with a "?" tag.'],
    sources=[['JWJ #0246 break page', 'https://jwjcollectorbreaks.com/products/jwj-0246-exalted-space-club-pyl'],
             ['Stadium Club WWE checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Stadium_Club_WWE_-_Checklist.pdf?v=1791221305'],
             ['Cosmic Chrome WWE checklist (matches the official Topps list)', 'https://www.checklistcenter.com/2026-topps-cosmic-chrome-wwe-wrestling-card-checklist/'],
             ['LogoFractor WWE checklist', 'https://www.checklistinsider.com/2026-topps-chrome-logofractor-wwe'],
             ['Exalted WWE checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/FINAL_CHECKLIST_2025EXALTEDWWE.pdf?v=1774986961']],
)

# ---------------- Star Wars random letter ----------------
def sw_spot(id, label, letters_):
    return dict(id=id, label=label, letters=list(letters_), g=None, price=None, status=None)
jwj0247_spots = [sw_spot(x.lower().replace('/', ''), x, x.replace('/', '')) for x in
                 ['A', 'B', 'C', 'D', 'E/F', 'G', 'H', 'I/N', 'J', 'K', 'L', 'M', 'O', 'P', 'Q/U', 'R', 'S', 'T/V/W/X/Y/Z']]
jwj0247 = dict(
    id='jwj0247', title='JWJ #0248 Chromed Up Galaxy', kicker='JWJ Collector Breaks · Random letter · Star Wars',
    url='https://jwjcollectorbreaks.com/products/jwj-0247-chromed-up-galaxy',
    when='Monday, November 23, 2026, 8:00 pm Eastern on the JWJ Breaks YouTube channel',
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
             ['Chrome Star Wars checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/CheckList_26SWCM4.pdf?v=1790785945'],
             ['Star Wars Galaxy Chrome checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/26SWCGCHECKLISTUPDATE.pdf?v=1786632392']],
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
             ['Topps Chrome Football checklist (official Topps)', 'https://cdn.sanity.io/files/hj34sz77/production/2cfae3dbb6d90c93d7a660bdf96b71cee1251349.pdf'],
             ['Topps Midnight Football checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Midnight_Football_checklist_ae614b15-64bd-4427-bebc-baa904c7368c.pdf?v=1791410806'],
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
    when='Running this week on the JWJ Breaks YouTube channel. It didn\'t run on November 16, the date still on the listing, so check JWJ for the time.',
    facts=['3 boxes', '26 team spots listed', '$68 per spot', 'Teams randomized live'],
    format='team', checked='Spots were still for sale when checked on November 23, 2026, around 5:00 pm Eastern (6 were left on November 22). It says 27 spots but lists 26 teams, and the Cleveland Cavaliers aren\'t on the list.',
    boxes=[dict(k='flag', short='Flagship', c='#f2c14e', full='2026-27 Topps Flagship Basketball (2 Hobby, 1 Jumbo)', kind='300-card base, autographs',
                types='300-card base with rookies and legends, base variations, inserts, autographs and relics (Jumbo adds an auto and a relic).')],
    spots=[team_spot(re.sub(r'[^a-z0-9]', '', l.lower()), l, t) for l, t in nba_spots],
    rules=[['Cards go to the team on the card', ['Legends count for the team printed on their card.', 'Seattle SuperSonics cards (Lenny Wilkens, Gary Payton) and every Cleveland Cavaliers card have no spot on JWJ\'s list. Ask JWJ where they go.']]],
    notes=['The autograph list is partial: the checklist page was too long to read in full, so some later autograph sets may be missing.',
           'Teams follow the checklist, which already reflects 2026-27 trades (Giannis shows up as both a Heat and a Bucks card, for example).'],
    sources=[['JWJ #0244 break page', 'https://jwjcollectorbreaks.com/products/jwj-0244-balling-on-a-budget-with-flagship-nba'],
             ['Topps Flagship Basketball checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/26TBSK_-_Topps_Flagship_Basketball_Checklist.xls.pdf?v=1793888934']],
)

# ---------------- library-based team data (Acme breaks, Nov 23) ----------------
LIB = os.path.join(os.path.dirname(__file__), 'checklists')
TEAM_FOLD = {'Redskins': 'Commanders', 'Football Team': 'Commanders', 'Oilers': 'Titans'}
def lib_team_product(pid):
    """A Topps team checklist from the library: base names by team, plus everyone in the autograph, insert and multi lists."""
    out = dict(base={}, other={})
    sec = None
    for line in open(os.path.join(LIB, pid + '.txt'), encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'): continue
        if line.startswith('['): sec = line.strip('[]'); continue
        for part in (line.split(' / ') if sec == 'multi' else [line]):
            if ' | ' not in part: continue
            n, team = [x.strip() for x in part.rsplit(' | ', 1)]
            team = TEAM_FOLD.get(team, team)
            bucket = out['base'] if sec == 'base' else out['other']
            if n not in bucket.setdefault(team, []): bucket[team].append(n)
    return out

NFL_CITIES = {'Arizona', 'Phoenix', 'St. Louis', 'Atlanta', 'Baltimore', 'Buffalo', 'Carolina', 'Chicago', 'Cincinnati', 'Cleveland', 'Dallas', 'Denver',
              'Detroit', 'Green Bay', 'Houston', 'Indianapolis', 'Jacksonville', 'Kansas City', 'Las Vegas', 'Oakland', 'Los Angeles', 'San Diego', 'Miami',
              'Minnesota', 'New England', 'Boston', 'New Orleans', 'New York', 'Philadelphia', 'Pittsburgh', 'San Francisco', 'Seattle', 'Tampa Bay',
              'Tennessee', 'Washington'}
NFL_NICK = set(TD.NFL_CHROME['base']) | {'Redskins', 'Oilers', 'Football Team'}
def nfl_team(full):
    """'Arizona Cardinals' -> 'Cardinals'; college teams ('Louisville Cardinals', 'Oklahoma State Cowboys') -> None."""
    for nick in NFL_NICK:
        if full.endswith(' ' + nick) and full[:-len(nick) - 1] in NFL_CITIES:
            return TEAM_FOLD.get(nick, nick)
    return None
ABS_ROSTER = {}  # name key -> NFL team from the Topps checklists, set by absolute_product (used for Kabooms)
def absolute_product(roster):
    """2026 Panini Absolute from the official CSV (absolute_2026.json). NFL players go to their team. A college player who is
    already on an NFL roster in the Topps checklists goes to that team (Acme's rule); everyone else is NIL, by first letter."""
    ABS_ROSTER.update(roster)
    out = dict(base={}, other={}, nil={})
    rows = json.load(open(os.path.join(os.path.dirname(__file__), 'absolute_2026.json'), encoding='utf-8'))
    for athletes, teams, f in rows:
        an, tn = athletes.split('/'), teams.split('/')
        for i, n in enumerate(an):
            n = n.strip(); full = (tn[i] if i < len(tn) else tn[-1]).strip()
            team = nfl_team(full) or roster.get(key_of(n))
            if team:
                bucket = out['base'] if f == 'B' else out['other']
                if n not in bucket.setdefault(team, []): bucket[team].append(n)
            else:
                out['nil'].setdefault(n, set()).add('B' if f == 'B' else 'A')
    return out

ACME_RULES = [['Cards go to the team on the card', ['Acme\'s rules: a card goes to the team listed on the front or back, not the jersey.', 'Retired players go to the team on their card; if that team moved, it goes to the team it became (Oilers to Titans, Redskins to Commanders, San Diego to the Chargers).']],
              ['College players', ['A player in a college uniform who\'s already in the NFL goes to his NFL team.', 'An NIL player (not in the NFL yet) is randomized to the group at the end of the break, unless the listing gives NIL letters.']],
              ['Multi-player cards', ['Cards with players from different teams are randomized between those teams with dice or random.org.']]]
ACME_TERMS = ['Acme Packs group break terms', 'https://acmepackscards.com/pages/terms-of-service']
SRC_CHROME = ['Topps Chrome Football checklist (official Topps)', 'https://cdn.sanity.io/files/hj34sz77/production/2cfae3dbb6d90c93d7a660bdf96b71cee1251349.pdf']
SRC_MIDNIGHT = ['Topps Midnight Football checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Midnight_Football_checklist_ae614b15-64bd-4427-bebc-baa904c7368c.pdf?v=1791410806']
SRC_INCEPTION = ['Topps Inception Football checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Inception_Football_CheckList_26TIFB_VERSION.pdf']
SRC_ABSOLUTE = ['Panini Absolute Football checklist (official Panini CSV)', 'https://www.paniniamerica.net/']
BOX_CHROME_J = dict(k='chrome', short='Chrome Jumbo', c='#5aa9ff', full='2026 Topps Chrome Football Jumbo (2 boxes)', kind='400-card base (300 veterans, 100 rookies), autographs',
                    types='Base and Refractors, rookie cards, autographs including legends, inserts. Jumbo boxes carry more autographs than Hobby.')
BOX_CHROME_H = dict(BOX_CHROME_J, short='Topps Chrome', full='2026 Topps Chrome Football Hobby (2 boxes)', types='Base and Refractors, rookie cards, autographs including legends, inserts.')
BOX_MIDNIGHT = dict(k='midnight', short='Midnight', c='#c86bff', full='2026 Topps Midnight Football Hobby (2 boxes)', kind='100-card base, 3 autographs per box, inserts',
                    types='Dark chrome base, rookie and veteran autographs (3 per hobby box), inserts like Night Night and Constellations.')
BOX_INCEPTION = dict(k='inception', short='Inception', c='#3ccf9a', full='2026 Topps Inception Football Hobby', kind='Rookie-focused, autographs and patches in every box',
                     types='Base, rookie autographs and patch autographs, inserts.')
BOX_ABSOLUTE = dict(k='absolute', short='Absolute', c='#e2545e', full='2026 Panini Absolute Football Hobby (12 boxes, full case)', kind='NFL veterans and legends plus college (NIL) players',
                    types='Base, Kaboom-style inserts, autographs and memorabilia of NFL players, retired greats and college players.')

def acme_url(h): return 'https://acmepackscards.com/products/' + h
gb1037_prices = [('49ers', 145, 1), ('Bears', 185, 0), ('Bengals', 125, 0), ('Bills', 125, 1), ('Broncos', 125, 1), ('Browns', 135, 1), ('Buccaneers', 115, 1),
                 ('Cardinals', 235, 1), ('Chargers', 60, 1), ('Chiefs', 285, 1), ('Colts', 65, 1), ('Commanders', 105, 1), ('Cowboys', 125, 1), ('Dolphins', 60, 1),
                 ('Eagles', 105, 1), ('Falcons', 65, 1), ('Giants', 140, 1), ('Jaguars', 85, 1), ('Jets', 95, 1), ('Lions', 85, 0), ('Packers', 75, 0), ('Panthers', 85, 1),
                 ('Patriots', 245, 1), ('Raiders', 350, 1), ('Rams', 185, 1), ('Ravens', 75, 1), ('Saints', 135, 1), ('Seahawks', 95, 0), ('Steelers', 105, 1),
                 ('Texans', 55, 1), ('Titans', 145, 1), ('Vikings', 75, 1)]
gb1037 = dict(
    id='gb1037', title='GB1037 Midnight Chrome PYT', kicker='Acme Packs · Pick your team · NFL',
    url=acme_url('gb1036-midnight-chrome-pyt-2-pick-your-team'),
    when='Tuesday, November 24, 2026, 5:00 pm Central (6:00 pm Eastern). If it doesn\'t fill, it rolls to the next break night.',
    facts=['4 boxes', '32 team spots', '$55 to $350 per team', 'Sold out'],
    format='pyt', checked='Sold out as of November 24, 2026, around 6:10 pm Eastern. The link says gb1036, but the listing is titled GB1037.',
    boxes=[BOX_CHROME_J, BOX_MIDNIGHT],
    spots=[dict(team_spot(t.lower(), t, [t]), price=p, status='sold') for t, p, a in gb1037_prices],  # all sold Nov 24 (Daniel); live status off so the store can't show leftover teams as open
    rules=ACME_RULES,
    notes=['Cards are listed with the team the official checklist gives them.'],
    sources=[['GB1037 break page (Acme Packs)', acme_url('gb1036-midnight-chrome-pyt-2-pick-your-team')], ACME_TERMS, SRC_CHROME, SRC_MIDNIGHT],
)
gb1038a_spots = [('49ers', ['49ers'], None), ('Bears + Eagles', ['Bears', 'Eagles'], None), ('Bengals', ['Bengals'], None), ('Bills', ['Bills'], None),
                 ('Browns', ['Browns'], 'E/I/N'), ('Buccaneers', ['Buccaneers'], 'M'), ('Cardinals + Vikings', ['Cardinals', 'Vikings'], None),
                 ('Chargers + Broncos', ['Chargers', 'Broncos'], None), ('Chiefs', ['Chiefs'], 'K'), ('Colts', ['Colts'], None), ('Commanders', ['Commanders'], 'G/S/Z/V/X'),
                 ('Cowboys', ['Cowboys'], None), ('Dolphins', ['Dolphins'], 'W/L/P'), ('Falcons', ['Falcons'], 'R'), ('Jaguars', ['Jaguars'], 'D'), ('Jets', ['Jets'], 'J'),
                 ('Lions', ['Lions'], None), ('Packers', ['Packers'], None), ('Panthers', ['Panthers'], None), ('Patriots', ['Patriots'], None),
                 ('Raiders + Giants', ['Raiders', 'Giants'], None), ('Rams', ['Rams'], None), ('Ravens', ['Ravens'], 'T'), ('Saints', ['Saints'], 'B'),
                 ('Seahawks', ['Seahawks'], None), ('Steelers', ['Steelers'], None), ('Texans', ['Texans'], 'A'), ('Titans', ['Titans'], 'C')]
gb1038a = dict(
    id='gb1038a', title='GB1038 Full Case Absolute Football', kicker='Acme Packs · Random team · NFL and NIL letters',
    url=acme_url('gb1038-full-case-absolute-football-random-team'),
    when='The listing says Friday, November 20, 2026, 8:00 pm Central, but it went up on November 23, so that date looks like a leftover. Check the live page for the real date.',
    facts=['12 boxes (full case)', '28 team spots', '$135 per spot', 'Teams randomized live'],
    format='team', checked='When checked on November 23, 2026, around 2:00 pm Eastern, spots were still for sale. Acme lists two different breaks as GB1038 (this one and Midnight Chrome Inception).',
    boxes=[BOX_ABSOLUTE],
    spots=[team_spot(re.sub(r'[^a-z0-9]', '', l.lower()), l + (' + NIL ' + n if n else ''), ts, n) for l, ts, n in gb1038a_spots],
    rules=[ACME_RULES[0], ['NIL letters cover the college cards', ['Absolute is full of college players. Thirteen spots also get NIL letters for players not in the NFL yet.', 'The listing doesn\'t say first or last name. This guide goes by first name, the way Acme\'s terms handle letters everywhere else, and the split fits: the busiest first-name letters (J, C, K, D, M) each get a spot, and the rare ones are grouped (G/S/Z/V/X).', 'No NIL player\'s first name starts with F, H, O, Q, U or Y, which is why no spot has those letters.']],
           ['College players already in the NFL', ['A college-uniform card of a player who\'s in the NFL now goes to his NFL team. This guide matches them by name against the 2026 Topps football checklists.']],
           ACME_RULES[2]],
    notes=['From the official Panini Absolute checklist. Players tagged NIL are college players; their spot comes from the NIL letter.'],
    sources=[['GB1038 Full Case Absolute break page (Acme Packs)', acme_url('gb1038-full-case-absolute-football-random-team')], ACME_TERMS, SRC_ABSOLUTE],
)
gb1038b_spots = [('49ers', ['49ers']), ('Bears', ['Bears']), ('Bengals', ['Bengals']), ('Bills', ['Bills']), ('Broncos', ['Broncos']), ('Browns', ['Browns']),
                 ('Buccaneers', ['Buccaneers']), ('Cardinals', ['Cardinals']), ('Chargers / Dolphins', ['Chargers', 'Dolphins']), ('Chiefs', ['Chiefs']),
                 ('Commanders', ['Commanders']), ('Cowboys', ['Cowboys']), ('Eagles', ['Eagles']), ('Falcons / Colts', ['Falcons', 'Colts']), ('Giants', ['Giants']),
                 ('Jets', ['Jets']), ('Lions', ['Lions']), ('Packers / Texans', ['Packers', 'Texans']), ('Panthers', ['Panthers']), ('Patriots', ['Patriots']),
                 ('Raiders', ['Raiders']), ('Rams', ['Rams']), ('Ravens', ['Ravens']), ('Saints', ['Saints']), ('Seahawks', ['Seahawks']), ('Steelers', ['Steelers']),
                 ('Titans', ['Titans']), ('Vikings / Jaguars', ['Vikings', 'Jaguars'])]
gb1038b = dict(
    id='gb1038b', title='GB1039 Midnight Chrome Inception', kicker='Acme Packs · Random team · NFL',
    url=acme_url('gb1038-midnight-chrome-inception-random-team'),
    when='Tuesday, November 24, 2026, 7:00 pm Central (8:00 pm Eastern). If it doesn\'t fill, it rolls to the next break night.',
    facts=['5 boxes', '28 team spots (24 teams, 4 combos)', '$132 per spot', 'Teams randomized live'],
    format='team', checked='When checked on November 23, 2026, around 2:00 pm Eastern, spots were still for sale. Acme lists two different breaks as GB1038 (this one and Full Case Absolute).',
    boxes=[BOX_INCEPTION, BOX_MIDNIGHT, BOX_CHROME_H],
    spots=[team_spot(re.sub(r'[^a-z0-9]', '', l.lower()), l, ts) for l, ts in gb1038b_spots],
    rules=ACME_RULES,
    notes=['Cards are listed with the team the official checklist gives them.'],
    sources=[['GB1038 Midnight Chrome Inception break page (Acme Packs)', acme_url('gb1038-midnight-chrome-inception-random-team')], ACME_TERMS, SRC_INCEPTION, SRC_MIDNIGHT, SRC_CHROME],
)

# ---------------- library-based letter data (Colfax NASCAR, Nov 23) ----------------
def lib_letter_product(pid):
    """A checklist from the library as a letter-break product: base / auto / insert / multi name lists."""
    out = dict(base=[], auto=[], insert=[], multi=[])
    sec = None
    for line in open(os.path.join(LIB, pid + '.txt'), encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'): continue
        if line.startswith('['): sec = line.strip('[]'); continue
        if sec in out: out[sec].append(line.split(' | ')[0] if sec != 'multi' else ' / '.join(x.split(' | ')[0] for x in line.split(' / ')))
    return {k: ';'.join(v) for k, v in out.items()}

def cc_spot(label, letters_='', pre=()):
    return dict(id=re.sub(r'[^a-z0-9]', '', label.lower().replace('-', 'to')), label=label, letters=list(letters_), pre=[list(r) for r in pre], g=None, price=None, status=None)
cc875_spots = [cc_spot('A / N', 'AN'), cc_spot('B', 'B'), cc_spot('CA-CH', pre=[('CA', 'CH')]), cc_spot('CI-CY', pre=[('CI', 'CY')]), cc_spot('D', 'D'),
               cc_spot('E / F / G / H', 'EFGH'), cc_spot('JA-JE', pre=[('JA', 'JE')]), cc_spot('JI-JY', pre=[('JI', 'JY')]), cc_spot('K', 'K'),
               cc_spot('L / M / W', 'LMW'), cc_spot('P / S / V / Z', 'PSVZ'), cc_spot('R', 'R'), cc_spot('T', 'T')]
SRC_PANINI = 'https://www.paniniamerica.net/'
cc875 = dict(
    id='cc875', title='CC875 Immaculate NASCAR (Random Letter)', kicker='Colfax Collectibles · Random letter · NASCAR',
    url='https://colfaxcc.com/products/cc875-immaculate-nascar-random-letter',
    when='Sunday, November 22, 2026, 5:00 pm Central (6:00 pm Eastern) on the Colfax YouTube channel',
    facts=['3 boxes', '13 letter spots', '$90 per spot, $22.50 for a 25% filler', 'Letters randomized live'],
    format='random', checked='',
    boxes=[dict(k='select', short='Select', c='#5aa9ff', full='2026 Panini Select Racing Hobby (2 boxes)', kind='100 drivers and crew in the base set, 96 with autographs, inserts',
                types='Base with Prizm parallels, inserts, driver autographs and dual autographs.'),
           dict(k='immaculate', short='Immaculate', c='#e2545e', full='2026 Panini Immaculate Collection Racing', kind='81 in the base set, 127 with autographs, memorabilia and patch cards',
                types='High-end numbered cards: autographs, memorabilia and patch cards, plus many dual and multi-driver cards.')],
    spots=cc875_spots,
    rules=[['First letter of the printed name', ['The spot goes by the first letter of the name printed on the card, which for drivers is the first name: Chase Elliott is C, Kyle Larson is K.', 'Colfax\'s listing doesn\'t spell out first or last name, but the C and J spots split on the second letter (CA-CH, JA-JE), which only fits first names.']],
           ['Two-letter spots split on the second letter', ['Chase Elliott and Christopher Bell are CH, so CA-CH. Cole Custer and Corey Heim are CO, so CI-CY.', 'Jesse Love is JE, so JA-JE. Joey Logano, Josh Berry and Justin Allgaier land in JI-JY.']],
           ['Letters with no spot', ['No spot lists I, O, Q, U, X or Y, and no one in these two checklists has a first name starting with those letters, so every card has a home.']],
           ['Multi-driver cards', ['Dual and multi-driver cards are tagged "multi", and each person is listed under their own letter.', 'Colfax rules: non-numbered multi cards go to the top or left name on odd-numbered breaks; numbered ones and case hits get a dice roll or random.org.']]],
    notes=['The listing says "2026 Select Hobby". This is a NASCAR break, so the 2026 Panini Select Racing checklist is used.',
           'Lists come from the official Panini checklists and include crew chiefs (like Chad Knaus and Cliff Daniels) and others who have cards, not just drivers.',
           'Filler spots were sold at a quarter of the price for a 25% chance at a spot.'],
    sources=[['CC875 break page (Colfax Collectibles)', 'https://colfaxcc.com/products/cc875-immaculate-nascar-random-letter'],
             ['Colfax group break rules', 'https://colfaxcc.com/pages/rules'],
             ['Panini Select Racing checklist (official Panini CSV)', SRC_PANINI],
             ['Panini Immaculate Collection Racing checklist (official Panini CSV)', SRC_PANINI]],
)

# ---------------- Run Good Life breaks (Nov 24, 2026) ----------------
def rgl_url(h): return 'https://rungoodlife.com/products/' + h
RGL_MULTI = ['Multi-player cards', ['RGL\'s listing: all dual, triple, quad and multi-way cards are randomized among the spots on the card, unless everyone who owns a piece of it makes a deal.']]
RGL_TEAM_RULE = ['Cards go to the team on the card', ['This guide files each card under the team the official checklist gives it. Retired players count for the team on their card; old franchises are filed with today\'s team here (for example Expos to Nationals).', 'RGL\'s Group Break Rules page has the full house rules, so check there if a card could go either way.']]

def lib_women(*pids):
    """names marked | W anywhere in these library checklists"""
    out = set()
    for pid in pids:
        for line in open(os.path.join(LIB, pid + '.txt'), encoding='utf-8'):
            for part in line.strip().split(' / '):
                if part.endswith(' | W'): out.add(part[:-4].strip())
    return out

def team_spots_from_variants(variants, fold_to, random_team=None):
    """PYT spots from the store's variant titles ('Arizona Cardinals\t$295'): label is the full team name, so live status lines up."""
    spots = []
    for full, price, avail in variants:
        if random_team and full == random_team:
            spots.append(dict(team_spot(re.sub(r'[^a-z0-9]', '', full.lower()), full + ' (random to all)', [fold_to(full)]), status='sold')); continue
        spots.append(dict(team_spot(re.sub(r'[^a-z0-9]', '', full.lower()), full, [fold_to(full)]), price=price, status='open' if avail else 'sold'))
    return spots

# RGL #6130 Chrome & Midnight PYT (Raiders random to all)
rgl6130_v = [('Arizona Cardinals', 295, 1), ('Atlanta Falcons', 70, 1), ('Baltimore Ravens', 105, 1), ('Buffalo Bills', 235, 1), ('Carolina Panthers', 90, 1),
             ('Chicago Bears', 215, 1), ('Cincinnati Bengals', 145, 0), ('Cleveland Browns', 170, 0), ('Dallas Cowboys', 140, 1), ('Denver Broncos', 110, 0),
             ('Detroit Lions', 110, 1), ('Green Bay Packers', 65, 0), ('Houston Texans', 45, 0), ('Indianapolis Colts', 70, 1), ('Jacksonville Jaguars', 85, 1),
             ('Kansas City Chiefs', 375, 1), ('Las Vegas Raiders', 0, 0), ('Los Angeles Chargers', 80, 1), ('Los Angeles Rams', 255, 1), ('Miami Dolphins', 65, 1),
             ('Minnesota Vikings', 85, 1), ('New England Patriots', 360, 1), ('New Orleans Saints', 145, 1), ('New York Giants', 175, 1), ('New York Jets', 105, 1),
             ('Philadelphia Eagles', 130, 1), ('Pittsburgh Steelers', 100, 1), ('San Francisco 49ers', 170, 0), ('Seattle Seahawks', 195, 1),
             ('Tampa Bay Buccaneers', 160, 1), ('Tennessee Titans', 155, 1), ('Washington Commanders', 95, 0)]
RGL6130_H = 'rgl-6130-chrome-midnight-pyt-11-25-26-raiders-random'
rgl6130 = dict(
    id='rgl6130', title='RGL #6130 Chrome & Midnight PYT', kicker='Run Good Life · Pick your team · NFL',
    url=rgl_url(RGL6130_H),
    when='Wednesday, November 25, 2026, around 3:45 pm Pacific (6:45 pm Eastern) on the Rungoodlife YouTube channel. Start times are estimates.',
    facts=['5 boxes', '32 team spots', '$45 to $375 per team', 'Raiders randomized to all'],
    live=dict(shop='rgl', handle=RGL6130_H),
    format='pyt', checked='Availability checked against Run Good Life\'s store data on November 24, 2026, around 1:10 pm Eastern: 24 of 31 teams open.',
    boxes=[dict(BOX_CHROME_H, short='Topps Chrome', full='2026 Topps Chrome Football (2 Hobby, 1 Jumbo)', types='Base and Refractors, rookie cards, autographs including legends, inserts. The Jumbo box carries more autographs.'),
           BOX_MIDNIGHT],
    spots=team_spots_from_variants(rgl6130_v, lambda f: f.split(' ')[-1], 'Las Vegas Raiders'),
    rules=[['Raiders are randomized to all spots', ['Before the break, RGL gives the Raiders to one buyer by random draw. You get one entry (a "duck") for every $50 your team cost, so the Chiefs and Patriots get 7 entries and the cheapest teams get 1.']],
           RGL_TEAM_RULE,
           ['College (NIL) cards', ['NIL stands for name, image and likeness: college players who aren\'t in the NFL yet. RGL randomizes all of those cards to all spots at the end of the break.', 'College players already in the NFL go to their NFL team, as the checklist lists them.']],
           RGL_MULTI],
    notes=['Cards are listed with the team the official checklist gives them.', 'The Raiders spot isn\'t for sale; its cards go to the winner of the Raiders draw.'],
    sources=[['RGL #6130 break page (Run Good Life)', rgl_url(RGL6130_H)], SRC_CHROME, SRC_MIDNIGHT],
)

# RGL #6129 Gilded Collection PYT (Dodgers random to all)
rgl6129_v = [('Arizona Diamondbacks', 55, 1), ('Atlanta Braves', 165, 0), ('Baltimore Orioles', 155, 1), ('Boston Red Sox', 225, 1), ('Chicago Cubs', 130, 0),
             ('Chicago White Sox', 250, 1), ('Cincinnati Reds', 165, 1), ('Cleveland Guardians', 145, 1), ('Colorado Rockies', 40, 1), ('Detroit Tigers', 185, 1),
             ('Houston Astros', 100, 1), ('Kansas City Royals', 235, 1), ('Los Angeles Angels', 115, 1), ('Los Angeles Dodgers', 0, 0), ('Miami Marlins', 60, 1),
             ('Milwaukee Brewers', 245, 1), ('Minnesota Twins', 60, 1), ('New York Mets', 170, 0), ('New York Yankees', 375, 1), ("Oakland A's", 105, 1),
             ('Philadelphia Phillies', 130, 1), ('Pittsburgh Pirates', 240, 1), ('San Diego Padres', 75, 1), ('San Francisco Giants', 165, 1),
             ('Seattle Mariners', 165, 1), ('St. Louis Cardinals', 190, 1), ('Tampa Bay Rays', 75, 1), ('Texas Rangers', 60, 1), ('Toronto Blue Jays', 135, 1),
             ('Washington Nationals', 85, 1)]
MLB_FOLD = {'Expos': 'Nationals', 'Cleveland': 'Guardians', 'Senators': 'Twins', 'Indians': 'Guardians', "A's": 'Athletics', 'Browns': 'Orioles'}
def mlb_team(full):
    if full == "Oakland A's": return 'Athletics'
    for two in ('Red Sox', 'White Sox', 'Blue Jays'):
        if full.endswith(two): return two
    return full.split(' ')[-1]
def lib_mlb_product(pid):
    p = lib_team_product(pid)
    for b in ('base', 'other'):
        for old, new in MLB_FOLD.items():
            if old in p[b]:
                for n in p[b].pop(old):
                    if n not in p[b].setdefault(new, []): p[b][new].append(n)
    return p
RGL6129_H = 'rgl-6129-gilded-collection-pyt-dodgers-random-11-25-26'
TOPPS_PDF = 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/'
rgl6129 = dict(
    id='rgl6129', title='RGL #6129 Gilded Collection PYT', kicker='Run Good Life · Pick your team · MLB',
    url=rgl_url(RGL6129_H),
    when='Wednesday, November 25, 2026, around 3:00 pm Pacific (6:00 pm Eastern) on the Rungoodlife YouTube channel. Start times are estimates.',
    facts=['6 boxes', '30 team spots', '$40 to $375 per team', 'Dodgers randomized to all'],
    live=dict(shop='rgl', handle=RGL6129_H),
    format='pyt', checked='Availability checked against Run Good Life\'s store data on November 24, 2026, around 1:10 pm Eastern: 26 of 29 teams open. The listing says 29 spots in one place and 30 in another; the 30th is the Dodgers, who go by random draw.',
    boxes=[dict(k='chrome', short='Topps Chrome', c='#5aa9ff', full='2026 Topps Chrome Baseball Hobby', kind='Base with rookies and legends, Refractors, autographs, inserts',
                types='Chrome base and Refractor parallels, rookie cards, autographs, inserts.'),
           dict(k='update', short='Update', c='#3ccf9a', full='2026 Topps Update Series Baseball Hobby', kind='Traded players, rookies and All-Star cards, autographs, inserts',
                types='Base with traded players and rookies, All-Star Game cards, inserts, autographs and relics.'),
           dict(k='gilded', short='Gilded', c='#f2c14e', full='2026 Topps Gilded Collection Baseball', kind='Gold-styled base, autographs in every box',
                types='High-end gold-styled cards, on-card and Chrome autographs, multi-player autographs.'),
           dict(k='museum', short='Museum', c='#c86bff', full='2026 Topps Museum Collection Baseball', kind='Numbered base, autographs and memorabilia',
                types='Numbered base, autographs, relic and patch cards, multi-player relics.'),
           dict(k='finest', short='Finest', c='#e2545e', full='2026 Topps Finest Baseball (2 Mega boxes)', kind='Base with Refractors, autographs, inserts',
                types='Finest base and Refractors, rookie cards, autographs, inserts. This guide uses the Finest checklist for the Mega boxes.')],
    spots=team_spots_from_variants(rgl6129_v, mlb_team, 'Los Angeles Dodgers'),
    rules=[['Dodgers are randomized to all spots', ['At the start of the break, RGL gives the Dodgers to one buyer by random draw. You get one entry (a "duck") for every $50 your team cost, so the Yankees get 7 entries and the cheapest teams get 1.']],
           RGL_TEAM_RULE, RGL_MULTI],
    notes=['Cards are listed with the team the official checklist gives them. Expos cards are filed with the Nationals, old Cleveland cards with the Guardians and Washington Senators cards (Walter Johnson) with the Twins.',
           'The Dodgers spot isn\'t for sale; its cards go to the winner of the Dodgers draw.',
           'Cards of people with no team on the checklist (celebrities, broadcasters, Sadaharu Oh) aren\'t listed. Ask RGL where those go.'],
    sources=[['RGL #6129 break page (Run Good Life)', rgl_url(RGL6129_H)],
             ['Topps Chrome Baseball checklist (official Topps)', TOPPS_PDF + '2026_Topps_Chrome_Baseball_Checklist_Final_7.22.pdf'],
             ['Topps Update Series Baseball checklist (official Topps)', TOPPS_PDF + '2026_Topps_Update_Series_Baseball_Checklist_10-12.pdf'],
             ['Topps Gilded Collection Baseball checklist (official Topps)', 'https://assets.contentstack.io/v3/assets/bltc7206971cb4b2bfc/blt65da9011233df00c/6afb19a4506dd7334571b8bb/2026_Topps_Gilded_Collection_Baseball_Checklist.pdf'],
             ['Topps Museum Collection Baseball checklist (official Topps)', TOPPS_PDF + '2026_Topps_Museum_Baseball_Checklist.pdf'],
             ['Topps Finest Baseball checklist (official Topps)', TOPPS_PDF + '2026_Finest_Baseball_FDI_Checklist.pdf']],
)

# RGL #6128 Chrome in the Club PYL (WWE, first name)
# Garbage Pail Kids cards in 2026 Topps Chrome WWE (25 cards, tradercracks.com GPK checklist): RGL sends them to the wrestler's spot.
GPK = {'unstitched bliss': 'Alexa Bliss', 'braid-est bianca': 'Bianca Belair', 'bad girl bayley': 'Bayley', 'chelsea shhhush!': 'Chelsea Green',
       'potty mouth punk': 'CM Punk', 'cody bomb': '"The American Nightmare" Cody Rhodes', 'dirty dominik': 'Dominik Mysterio', 'drafty drew': 'Drew McIntyre',
       'damaged damian': 'Damian Priest', 'soaring sky': 'Iyo Sky', 'john see? nah!': 'John Cena', 'feral fatu': 'Jacob Fatu', 'jey yeesh!': 'Jey Uso',
       'boogie knight': 'LA Knight', 'liv it up': 'Liv Morgan', 'ladybird lyra': 'Lyra Valkyria', 'disarm her becky': 'Becky Lynch', 'pop-out penta': 'Penta',
       'ripped rhea': 'Rhea Ripley', 'reptilian randy': 'Randy Orton', 'popped roxanne': 'Roxanne Perez', 'roman empire': 'Roman Reigns',
       'supersized seth': 'Seth Rollins', 'finally! the rock (has come back to gpk!)': 'The Rock', 'finally! the rock (has come back to gpk)': 'The Rock',
       'tiffany time': 'Tiffany Stratton'}
def gpk_fold(prod):
    out = dict(prod)
    for sec in ('insert', 'base', 'auto'):
        out[sec] = ';'.join(GPK.get(n.strip().lower(), n) for n in split(prod.get(sec, '')))
    return out
RGL_WOMEN = lib_women('2026-topps-stadium-club-wwe', '2026-topps-chrome-wwe', '2025-topps-finest-wwe')
# The National Convention box is multi-sport and has no | W marks: its women (actresses and Star Wars characters; the wrestlers are
# already marked in the WWE lists) go to the Women spots.
RGL_WOMEN |= {'Ahsoka Tano', 'Billie Lourd', 'Daisy Ridley', 'Emilia Clarke', 'Genevieve O\'Reilly', 'IYO SKY', 'Katee Sackhoff', 'Keri Russell', 'Laura Dern',
              'Leia Organa', 'Lupita Nyong\'o', 'Ming-Na Wen', 'Natalie Portman', 'Queen Amidala', 'Rosario Dawson', 'Sabine Wren', 'Shin Hati'}
NSCC_SPORTS = json.load(open(os.path.join(os.path.dirname(__file__), 'nscc_sports.json'), encoding='utf-8'))
def nscc_product(sport=None):
    """The 2026 National Convention box. It's multi-sport, so a break can keep only its own sport's cards
    (Daniel, Nov 24: a WWE break shows only the WWE cards). nscc_sports.json tags every name from the official
    checklist's set names (WWE, NBA, NFL, UEFA, Star Wars, Bowman U) and teams."""
    p = lib_letter_product('2026-national-sports-collectors-convention')
    keep = lambda n: sport is None or any(sport in NSCC_SPORTS.get(x.strip(), []) for x in n.split(' / '))
    return {k: ';'.join('Iyo Sky' if n == 'IYO SKY' else n for n in split(v) if keep(n)) for k, v in p.items()}
def rgl_wwe_gender(n):
    return 'F' if (n in RGL_WOMEN or key_of(n) in RGL_WOMEN or wwe_gender(n) == 'F') else 'M'
R = lambda *a: wwe_spot(*a)
rgl6128_spots = [
    R('a-w', 'A', 'A', 'F', 130, False), R('ac-m', 'A & C', 'AC', 'M', 170, True), R('b-m', 'B', 'B', 'M', 100, True), R('b-w', 'B', 'B', 'F', 120, True),
    R('c-w', 'C', 'C', 'F', 80, True), R('d', 'D', 'D', None, 115, False), R('ef', 'E / F', 'EF', None, 80, True), R('g', 'G', 'G', None, 115, True),
    R('h', 'H', 'H', None, 40, False), R('i', 'I', 'I', None, 65, True), R('j-m', 'J', 'J', 'M', 215, True), R('j-w', 'J', 'J', 'F', 65, False),
    R('k-m', 'K', 'K', 'M', 80, True), R('k-w', 'K', 'K', 'F', 130, True), R('l', 'L', 'L', None, 180, False), R('m', 'M', 'M', None, 50, True),
    R('n', 'N', 'N', None, 40, True), R('o', 'O', 'O', None, 70, True), R('pq', 'P-Q', 'PQ', None, 55, True), R('r-m', 'R', 'R', 'M', 235, True),
    R('r-w', 'R', 'R', 'F', 145, False), R('s-m', 'S', 'S', 'M', 135, False), R('s-w', 'S', 'S', 'F', 185, False), R('t-m', 'T', 'T', 'M', 80, True),
    R('t-w', 'T', 'T', 'F', 160, True), R('uvw', 'U-V-W', 'UVW', None, 100, True), R('xyz', 'X-Y-Z-123', 'XYZ#', None, 50, True),
]
RGL6128_H = 'rgl-6128-chrome-in-the-club-pyl-pick-your-letter-first-name-11-25-26'
rgl6128 = dict(
    id='rgl6128', title='RGL #6128 Chrome in the Club PYL', kicker='Run Good Life · Pick your letter · WWE',
    url=rgl_url(RGL6128_H),
    when='Wednesday, November 25, 2026, around 2:00 pm Pacific (5:00 pm Eastern) on the Rungoodlife YouTube channel. Start times are estimates.',
    facts=['6 boxes', '27 letter spots', '$40 to $235 per spot'],
    live=dict(shop='rgl', handle=RGL6128_H),
    format='pyl', checked='Availability checked against Run Good Life\'s store data on November 24, 2026, around 1:10 pm Eastern: 19 of 27 spots open.',
    boxes=[dict(WWE_BOX['sc'], full='2026 Topps Stadium Club WWE Hobby (2 boxes)'),
           dict(WWE_BOX['chrome'], full='2026 Topps Chrome WWE (1 Hobby, 1 Breaker\'s Delight)', types='Base and Refractor parallels, inserts like Signalz, Gamut and Helix, Garbage Pail Kids cards, autographs.'),
           dict(k='nscc', short='National Convention', c='#3ccf9a', full='2026 Topps National Sports Collectors Convention', kind='Multi-sport box; this guide lists only its WWE cards',
                types='WWE base refractors and their autograph parallels, plus the wrestlers in The National Collection set.'),
           dict(k='finest', short='Finest', c='#e2545e', full='2025 Topps Finest WWE Hobby', kind='300-card base (Common, Uncommon and Rare), autographs, inserts',
                types='Finest base and Refractor parallels, inserts like Finishers, Intimidators and Dark Energy, and autographs like Finest Autographs and Masters Autographs.')],
    spots=rgl6128_spots,
    rules=[['First letter of the first name on the card', ['RGL\'s listing says first name. A leading "The" doesn\'t count for the T Men spot ("no THE"), so The Rock is R and The Miz is M.', 'Men and Women spots split by who\'s on the card.']],
           WWE_RULES[1],
           ['Garbage Pail Kids cards go to the wrestler', ['RGL\'s rule: every Garbage Pail Kids card from 2026 Topps Chrome WWE goes to the wrestler\'s spot, not the name on the card. "Potty Mouth Punk" goes to A & C Men (CM Punk), not P-Q. This guide already files all 25 that way.']],
           RGL_MULTI],
    notes=['Only the WWE cards from the National Convention box are listed here: 50 wrestlers, base and autographs. The box also has football, basketball, baseball, soccer and Star Wars cards; ask RGL how they handle those.',
           'Breaker\'s Delight is a Topps Chrome WWE box, so it uses the same checklist as the Hobby box.',
           'Lists come from the official Topps checklists.'],
    sources=[['RGL #6128 break page (Run Good Life)', rgl_url(RGL6128_H)],
             ['Stadium Club WWE checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Stadium_Club_WWE_-_Checklist.pdf?v=1791221305'],
             ['Chrome WWE checklist (official Topps)', TOPPS_PDF + 'FINAL_CheckList_26CWWE_ChromeWWE.pdf'],
             ['National Sports Collectors Convention checklist (official Topps)', TOPPS_PDF + '2026_National_Sports_Collectors_Convention_26NSCC_-_Checklist_1.pdf'],
             ['Finest WWE checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2025_Topps_Finest_WWE_-_Checklist.pdf?v=1758820316'],
             ['Chrome WWE Garbage Pail Kids list', 'https://www.tradercracks.com/2026-topps-chrome-wwe-garbage-pail-kids-checklist-guide']],
)

# ---------------- finished breaks ----------------
# A break that has run keeps its guide, but loses the live sold/open status and buying prompts.
def close(cfg, ran, facts):
    cfg.update(ended='This break ran on ' + ran + '. Spots are closed, but the guide stays up so you can look back at who was in each spot.',
               when='Ran ' + ran, facts=facts, checked='')

close(cc871, 'Sunday, November 22, 2026', ['4 boxes', '27 letter spots'])
close(cc872, 'Sunday, November 22, 2026', ['5 boxes', '32 team spots', '$95 per spot, $23.75 filler'])
close(cc875, 'Sunday, November 22, 2026', ['3 boxes', '13 letter spots', '$90 per spot, $22.50 filler'])
close(jwj0246, 'Monday, November 23, 2026', ['6 boxes', '27 letter spots'])
close(jwj0247, 'Monday, November 23, 2026', ['2 boxes', '18 letter spots', '$66 per spot'])
close(jwj0244, 'the week of November 23, 2026', ['3 boxes', '26 team spots'])
close(gb1037, 'Tuesday, November 24, 2026', ['4 boxes', '32 team spots', '$55 to $350 per team'])
close(gb1038a, 'Tuesday, November 24, 2026', ['12 boxes (full case)', '28 team spots', '$135 per spot'])
close(gb1038b, 'Tuesday, November 24, 2026', ['5 boxes', '28 team spots (24 teams, 4 combos)', '$132 per spot'])
close(rgl6128, 'Wednesday, November 25, 2026', ['6 boxes', '27 letter spots', '$40 to $235 per spot'])
close(rgl6129, 'Wednesday, November 25, 2026', ['6 boxes', '30 team spots', '$40 to $375 per team', 'Dodgers randomized to all'])
close(rgl6130, 'Wednesday, November 25, 2026', ['5 boxes', '32 team spots', '$45 to $375 per team', 'Raiders randomized to all'])
jwj0244.update(ended='This break ran the week of November 23, 2026. Spots are closed, but the guide stays up so you can look back at who was in each spot.',
               when='Ran the week of November 23, 2026')


# ---------------- RGL #6131 to #6133 (Nov 24, 2026; built by hand after the page builder left them for missing spot lists) ----------------
# RGL doesn't post how its random breaks are grouped: teams are paired and letters grouped live on stream. So these
# pages list every team (or letter) on its own, and say how many spots RGL sells.
NBA_TEAMS = ['76ers', 'Bucks', 'Bulls', 'Cavaliers', 'Celtics', 'Clippers', 'Grizzlies', 'Hawks', 'Heat', 'Hornets', 'Jazz', 'Kings', 'Knicks', 'Lakers',
             'Magic', 'Mavericks', 'Nets', 'Nuggets', 'Pacers', 'Pelicans', 'Pistons', 'Raptors', 'Rockets', 'Spurs', 'Suns', 'Thunder', 'Timberwolves',
             'Trail Blazers', 'Warriors', 'Wizards']
NBA_FOLD = {'Trailblazers': 'Trail Blazers', 'Supersonics': 'Thunder', 'SuperSonics': 'Thunder', 'Bobcats': 'Hornets', 'New Jersey Nets': 'Nets', 'Bullets': 'Wizards'}
def lib_nba_product(pid):
    p = lib_team_product(pid)
    for b in ('base', 'other'):
        for old, new in NBA_FOLD.items():
            if old in p[b]:
                for n in p[b].pop(old):
                    if n not in p[b].setdefault(new, []): p[b][new].append(n)
    return p
def tid(l): return re.sub(r'[^a-z0-9]', '', l.lower())
RGL_LIVE_GROUPS = ['How RGL groups the spots', ['RGL sells fewer spots than there are teams, so some teams are paired up, and the pairings are set live on stream; they aren\'t posted on the listing.', 'This guide lists every team on its own, so once you know your team (or teams), look each one up here.']]

RGL6131_H = 'rgl-6131-joy-of-basketball-random-team-11-25-26'
rgl6131 = dict(
    id='rgl6131', title='RGL #6131 Joy of Five Star (Random Team)', kicker='Run Good Life · Random team · NBA',
    url=rgl_url(RGL6131_H),
    when='Wednesday, November 25, 2026, around 4:45 pm Pacific (7:45 pm Eastern) on the Rungoodlife YouTube channel. Start times are estimates.',
    facts=['5 boxes', '21 spots for 30 teams', '$290 per spot, fillers $29', 'Teams randomized live'],
    format='team', checked='When checked on November 24, 2026, around 2:00 pm Eastern, 6 of 21 spots were filled.',
    boxes=[dict(k='sc', short='Stadium Club', c='#5aa9ff', full='2025-26 Topps Stadium Club Basketball Hobby (2 boxes)', kind='Photo-driven base set, autographs and inserts',
                types='Base with photo variations, inserts, and autographs including rookies and legends.'),
           dict(k='five', short='Five Star', c='#e2545e', full='2025-26 Topps Five Star Basketball', kind='High-end, mostly autographs and patch cards',
                types='Numbered autographs, autographed patches and memorabilia of stars, rookies and legends.'),
           dict(k='joy', short='Joy of Basketball', c='#3ccf9a', full='2025-26 Topps x Bob Ross The Joy of Basketball', kind='Bob Ross themed base set, inserts and autographs',
                types='Painted-style base cards, themed inserts like Budding Talents and Over the Mountains, and autographs.'),
           dict(k='flag', short='Flagship', c='#f2c14e', full='2026-27 Topps Flagship Basketball Hobby', kind='300-card base, autographs',
                types='300-card base with rookies and legends, variations, inserts, autographs and relics.')],
    spots=[team_spot(tid(t), t, [t]) for t in NBA_TEAMS],
    rules=[RGL_LIVE_GROUPS, RGL_TEAM_RULE, RGL_MULTI],
    notes=['The title says "Joy of Five Star": the break has both 2025-26 Five Star and the Bob Ross Joy of Basketball box.',
           'Seattle SuperSonics legends are filed with the Thunder here, since that\'s the same franchise today. Ask RGL if it matters to you.',
           'Filler entries are sold too ($29 each, 60 of them); see RGL\'s listing for how fillers work.'],
    sources=[['RGL #6131 break page (Run Good Life)', rgl_url(RGL6131_H)],
             ['Topps Stadium Club Basketball, Five Star Basketball, Joy of Basketball and Flagship Basketball checklists (official Topps)', 'https://www.topps.com/pages/checklists']],
)
close(rgl6131, 'Wednesday, November 25, 2026', ['5 boxes', '21 spots for 30 teams', '$290 per spot'])

RGL6132_H = 'rgl-6132-absolute-finish-the-case-random-team-11-25-26'
rgl6132 = dict(
    id='rgl6132', title='RGL #6132 Absolute Finish the Case (Random Team)', kicker='Run Good Life · Random team · NFL',
    url=rgl_url(RGL6132_H),
    when='Wednesday, November 25, 2026, around 5:30 pm Pacific (8:30 pm Eastern) on the Rungoodlife YouTube channel. Start times are estimates.',
    facts=['7 boxes', '24 spots for 32 teams', '$132 per spot, fillers $33', 'Teams and NIL letters set on stream'],
    format='team', checked='When checked on November 24, 2026, around 2:00 pm Eastern, none of the 24 spots had sold yet.',
    boxes=[dict(BOX_CHROME_J, full='2026 Topps Chrome Football Jumbo (1 box)'),
           dict(BOX_ABSOLUTE, full='2026 Panini Absolute Football Hobby (6 boxes, finishing a case)')],
    spots=[team_spot(tid(t), t, [t], nil=(l or '').replace('/', '') or None) for t, l in cc872_teams],  # RGL's board on stream (Nov 25): every team has its NIL letters
    rules=[['How the spots were set', ['RGL sold 24 spots for 32 teams and set who gets which team live on stream. This guide follows the board RGL showed: each team spot also carries its college (NIL) letters.']],
           ['College (NIL) cards go by letter', ['NIL stands for name, image and likeness: college players who aren\'t in the NFL yet. Each one goes to the team holding the first letter of the player\'s name, as on RGL\'s board (for example Bengals get E, Packers get A, Browns get U, V, X and Y).', 'College players already in the NFL go to their NFL team.']],
           RGL_TEAM_RULE,
           RGL_MULTI],
    notes=['"Finish the Case" means these 6 Absolute boxes complete a case RGL started in an earlier break.', 'Filler entries are sold too ($33 each); see RGL\'s listing for how fillers work.'],
    sources=[['RGL #6132 break page (Run Good Life)', rgl_url(RGL6132_H)], SRC_CHROME, SRC_ABSOLUTE],
)
close(rgl6132, 'Wednesday, November 25, 2026', ['7 boxes', '24 spots for 32 teams', '$132 per spot'])  # stream showed #6133 running (Nov 25, 8:48 pm Eastern)

RGL6133_H = 'rgl-6133-immaculate-nascar-random-letter-11-25-26'
rgl6133 = dict(
    id='rgl6133', title='RGL #6133 Immaculate NASCAR (Random Letter)', kicker='Run Good Life · Random letter · NASCAR',
    url=rgl_url(RGL6133_H),
    when='Wednesday, November 25, 2026, around 6:30 pm Pacific (9:30 pm Eastern) on the Rungoodlife YouTube channel. Start times are estimates.',
    facts=['4 boxes', '13 letter groups', '$138 per spot, fillers $34.50', 'Letters randomized live'],
    format='random', checked='When checked on November 24, 2026, around 2:00 pm Eastern, the listing showed 9 spots and none had sold yet. RGL then set 13 letter groups live on stream.',
    boxes=[dict(cc875['boxes'][0], full='2026 Panini Select Racing Hobby (1 box)'),
           dict(k='prizm', short='Prizm', c='#f2c14e', full='2025 Panini Prizm Racing Hobby (1 box)', kind='About 100 drivers in the base set, autographs, inserts',
                types='Base with Prizm parallels, inserts, and driver autographs.'),
           dict(cc875['boxes'][1], full='2026 Panini Immaculate Collection Racing (2 boxes)')],
    spots=[],  # filled in below from the letters that have names
    rules=[['How the spots were set', ['RGL set the letter groups live on stream. This guide follows the board RGL showed: 13 groups, with C and J split on the second letter (CA-CH and CI-CY, JA-JE and JI-JY).']],
           ['First letter of the first name', ['RGL\'s board says first name, so Chase Elliott is C (CA-CH) and Joey Logano is J (JI-JY).']],
           ['Multi-driver cards', ['Each person on a dual or multi-driver card is listed under their own letter.', RGL_MULTI[1][0]]]],
    notes=['The listing says "2026 Select Hobby" and "2025 Prizm Hobby"; in a NASCAR break these are Panini Select Racing and Prizm Racing.',
           'Filler entries are sold too ($34.50 each); see RGL\'s listing for how fillers work.'],
    sources=[['RGL #6133 break page (Run Good Life)', rgl_url(RGL6133_H)],
             ['Panini Select Racing checklist (official Panini CSV)', SRC_PANINI],
             ['Panini Prizm Racing checklist (official Panini CSV)', SRC_PANINI],
             ['Panini Immaculate Collection Racing checklist (official Panini CSV)', SRC_PANINI]],
)
close(rgl6133, 'Wednesday, November 25, 2026', ['4 boxes', '13 letter groups', '$138 per spot, fillers $34.50'])  # stream showed #6134 running (Nov 25, 9:08 pm Eastern)

# GB1040 (Daniel, Nov 24): built from Acme's title card before the listing was posted. When the listing shows up in the
# watcher queue, update url, when, facts and checked here instead of building a second page; the image fills in once url
# is the product link.
ACME_BREAKS = 'https://acmepackscards.com/collections/group-breaks'
def _src(pid, label):
    u = next((l.split('source:', 1)[1].strip() for l in open(os.path.join(LIB, pid + '.txt'), encoding='utf-8') if l.startswith('# source:')), '')
    return [label + ' checklist (official Topps)', u]
# Finds the real listing by name, whatever number Acme puts in the link; the watcher workflow rebuilds the pages after each check.
GB1040_H = 'gb1040-dual-year-football-finale-random-team'  # posted Nov 24, 6:22 pm Central; Acme reused an old link
GB1040_LIB = dict(chrome='2026-topps-chrome-football', ufc='2026-topps-midnight-ufc', pristine='2025-26-topps-pristine-basketball',
                  platinum='2025-topps-chrome-platinum-baseball', sc='2026-topps-stadium-club-wwe')
gb1040 = dict(
    id='gb1040', title='GB1040 Multi Product Madness', kicker='Acme Packs · Random letter · NFL, UFC, NBA, MLB and WWE',
    url=acme_url(GB1040_H),  # Daniel's screenshot of Acme's title card; remove once the listing's own image is in images.json
    when='Tuesday, November 24, 2026, 8:00 pm Central (9:00 pm Eastern). If it doesn\'t fill, it rolls to the next break night.',
    facts=['5 boxes', '21 letter spots', '$135 per spot, $33.75 for a 25% filler', 'Letters randomized live'],
    format='random', checked='Letter spots are the ones on Acme\'s listing, posted November 24, 2026.',
    boxes=[dict(k='chrome', short='Chrome Football', c='#e2545e', full='2026 Topps Chrome Football Hobby', kind='NFL veterans and rookies, autographs, inserts',
                types='Chrome base with refractor parallels, inserts, and rookie and veteran autographs.'),
           dict(k='ufc', short='Midnight UFC', c='#8a6be0', full='2026 Topps Midnight UFC', kind='UFC fighters, autographs, inserts',
                types='Base with numbered parallels, inserts, and fighter autographs.'),
           dict(k='pristine', short='Pristine Basketball', c='#5aa9ff', full='2025-26 Topps Pristine Basketball', kind='NBA players and rookies, autographs, relics',
                types='Encased cards: base, autographs, relics and inserts.'),
           dict(k='platinum', short='Chrome Platinum', c='#4c9a2a', full='2025 Topps Chrome Platinum Baseball', kind='MLB players in the classic 1998 design, autographs, inserts',
                types='Chrome base with parallels, inserts and autographs.'),
           dict(k='sc', short='Stadium Club WWE', c='#f2c14e', full='2026 Topps Stadium Club WWE Hobby', kind='WWE Superstars and Legends, 2 autographs per box, inserts',
                types='Photo-driven base, inserts and autographs.')],
    spots=[],  # filled in below from the letters that have names
    rules=[['How the 21 spots work', ['Acme sells 21 spots and randomizes them live. Most letters have their own spot; the light ones share (E / F, H / I, N / O, P / U, V / Q / W, X / Y / Z).',
                                      'C, J and S are split on the second letter: CA-CH and CI-CZ, JA-JE and JF-JZ, SA-SH and SI-SZ. Cooper Flagg is CO, so CI-CZ; Josh Allen is JO, so JF-JZ.']],
           ['First letter of the name on the card', ['Acme\'s rules go by the first letter of the first name: Josh Allen is J, Shai Gilgeous-Alexander is S.', 'Ring names count as printed. Acme\'s list puts American Nightmare Cody Rhodes under A, Stone Cold under S, and The Rock under R (a leading "The" doesn\'t count).']],
           ['Cards with more than one name', ['Each person on a dual or multi-player card is listed under their own letter here. Acme randomizes cards like that between the spots involved.', 'Anything the rules don\'t cover is up to the breaker.']]],
    notes=['One box of each product. Filler entries are sold too ($33.75 for a 25% chance at a spot); see Acme\'s filler listing for how they work.',
           'The link says "dual-year-football-finale" because Acme reused an older listing; the break is GB1040 Multi Product Madness.'],
    sources=[['GB1040 break page (Acme Packs)', acme_url(GB1040_H)], ACME_TERMS, _src(GB1040_LIB['chrome'], 'Topps Chrome Football'), _src(GB1040_LIB['ufc'], 'Topps Midnight UFC'),
             _src(GB1040_LIB['pristine'], 'Topps Pristine Basketball'), _src(GB1040_LIB['platinum'], 'Topps Chrome Platinum Baseball'), _src(GB1040_LIB['sc'], 'Topps Stadium Club WWE')],
)

# ---------------- RGL #6134 to #6143 drafts (Daniel, Nov 25, 2026) ----------------
# No more drafts (Daniel, Nov 25, 2026): pages are built only from posted listings, with no guessed setups. The draft
# machinery below is kept but its list is empty. Set up from Daniel's list of tonight's break titles before RGL posted the listings. A draft stays off the site until
# the watcher sees an RGL product whose link starts with rgl-<number>-; then the page goes live with that link (and live
# sold tracking for pick-your-team breaks). The box lists are guesses from the titles: when the listing shows up in the
# queue, check boxes, spot count, prices and randomized teams against it and drop DRAFT_NOTE from the page.
# Not prepped (no way to tell the boxes from the title, or no team data): #6135 Oops All Animation, #6136 Pass the
# Turkey NFL, #6137 4 Box Pro Debut, #6141 Peak Degeneracy #6, #6142 UFC Royalty Mixer.
SEEN = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'watch', 'seen.json'), encoding='utf-8'))
def rgl_posted(num):
    return next((h for h in SEEN.get('rgl', []) if h.startswith('rgl-%d-' % num)), None)
DRAFT_NOTE = ('This guide was set up from the break title before Run Good Life posted the listing, so the box list and format are our best guess. '
              'Check the listing for the exact boxes and spots.')
def rgl_draft(cfg, num, pick=False):
    """True once RGL has posted the listing; fills in its link and live tracking."""
    h = rgl_posted(num)
    if not h: return False
    cfg['url'] = rgl_url(h)
    cfg['sources'] = [['RGL #%d break page (Run Good Life)' % num, rgl_url(h)]] + cfg['sources']
    if pick: cfg['live'] = dict(shop='rgl', handle=h)
    return True
MLB_FULL = [f for f, _, _ in rgl6129_v]
SRC_TOPPS_LIST = ['Official Topps checklists', 'https://www.topps.com/pages/checklists']
def _when(day, pt, et):
    return day + ', around ' + pt + ' Pacific (' + et + ' Eastern) on the Rungoodlife YouTube channel. Start times are estimates.'
WED, THU = 'Wednesday, November 25, 2026', 'Thursday, November 26, 2026'
MLB_RANDOM_SPOTS = [team_spot(tid(mlb_team(f)), mlb_team(f), [mlb_team(f)]) for f in MLB_FULL]

RGL6134_H = 'rgl-6134-gilded-collection-pyt-2-dodgers-random-11-25-26'  # posted Nov 25, 4:38 pm Eastern
rgl6134_v = [['Arizona Diamondbacks', 55, 0], ['Atlanta Braves', 165, 1], ['Baltimore Orioles', 155, 1], ['Boston Red Sox', 225, 1], ['Chicago Cubs', 130, 1], ['Chicago White Sox', 250, 1], ['Cincinnati Reds', 165, 1], ['Cleveland Guardians', 145, 1], ['Colorado Rockies', 40, 1], ['Detroit Tigers', 185, 1], ['Houston Astros', 100, 1], ['Kansas City Royals', 235, 0], ['Los Angeles Angels', 115, 1], ['Los Angeles Dodgers', 0, 0], ['Miami Marlins', 60, 1], ['Milwaukee Brewers', 245, 1], ['Minnesota Twins', 60, 1], ['New York Mets', 170, 1], ['New York Yankees', 375, 1], ["Oakland A's", 105, 1], ['Philadelphia Phillies', 130, 1], ['Pittsburgh Pirates', 240, 1], ['San Diego Padres', 75, 1], ['San Francisco Giants', 165, 1], ['Seattle Mariners', 165, 1], ['St. Louis Cardinals', 190, 1], ['Tampa Bay Rays', 75, 1], ['Texas Rangers', 60, 1], ['Toronto Blue Jays', 135, 1], ['Washington Nationals', 85, 1]]
rgl6134 = dict(
    id='rgl6134', title='RGL #6134 Gilded Collection PYT #2', kicker='Run Good Life · Pick your team · MLB',
    url=rgl_url(RGL6134_H),
    when=_when(WED, '7:15 pm', '10:15 pm'),
    facts=['6 boxes', '29 team spots', '$40 to $375 per team', 'Dodgers randomized to all'],
    live=dict(shop='rgl', handle=RGL6134_H),
    format='pyt', checked='Availability checked against Run Good Life\'s store data on November 25, 2026, around 4:50 pm Eastern: 27 of 29 teams open.',
    boxes=[dict(b) for b in rgl6129['boxes']],
    spots=team_spots_from_variants(rgl6134_v, mlb_team, 'Los Angeles Dodgers'),
    rules=[['Dodgers are randomized to all spots', ['At the start of the break, RGL gives the Dodgers to one buyer by random draw. You get one entry (a "duck") for every $50 your team cost, so the Yankees get 7 entries and the cheapest teams get 1.']],
           RGL_TEAM_RULE, RGL_MULTI],
    notes=['Same boxes as the first Gilded Collection PYT tonight (#6129): Chrome, Update, Gilded, Museum and two Finest Mega boxes.',
           'Cards are listed with the team the official checklist gives them. Expos cards are filed with the Nationals, old Cleveland cards with the Guardians and Washington Senators cards with the Twins.',
           'The Dodgers spot isn\'t for sale; its cards go to the winner of the Dodgers draw.'],
    sources=[['RGL #6134 break page (Run Good Life)', rgl_url(RGL6134_H)]] + list(rgl6129['sources'][1:]),
)
close(rgl6134, 'Wednesday, November 25, 2026', ['6 boxes', '29 team spots', '$40 to $375 per team', 'Dodgers randomized to all'])  # stream showed #6135 running (Nov 25, 10:17 pm Eastern)

# RGL #6136 Pass the Turkey NFL (Random Team), posted Nov 25. Two of its seven boxes (2025 Panini Prizm International and
# 2025 Panini Revolution Premium) have no checklist in the library yet, so the page lists the other five and says so.
RGL6136_H = 'rgl-6136-pass-the-turkey-nfl-random-team-11-25-26'
NFL_NICKS = {t for t, _ in cc872_teams}
def nfl_split(p, roster):
    """A football checklist with NFL and college teams: NFL players by team nickname; college players on an NFL roster in
    the Topps checklists go to that team, everyone else is NIL."""
    out = dict(base={}, other={}, nil={})
    for b in ('base', 'other'):
        for team, ns in p[b].items():
            t = team if team in NFL_NICKS else nfl_team(team)
            for n in ns:
                tt = t or roster.get(key_of(n))
                if tt:
                    if n not in out[b].setdefault(tt, []): out[b][tt].append(n)
                else:
                    out['nil'].setdefault(n, set()).add('B' if b == 'base' else 'A')
    return out
rgl6136 = dict(
    id='rgl6136', title='RGL #6136 Pass the Turkey NFL (Random Team)', kicker='Run Good Life · Random team · NFL',
    url=rgl_url(RGL6136_H),
    when=_when(WED, '8:45 pm', '11:45 pm'),
    facts=['7 boxes', '24 spots for 32 teams', '$194 per spot, fillers $48.50', 'Teams randomized live', '$1,000 turkey prize'],
    format='team', checked='Spots were still for sale when checked on November 25, 2026, around 4:50 pm Eastern.',
    boxes=[dict(BOX_CHROME_H, full='2026 Topps Chrome Football Hobby (1 box)'),
           dict(k='donruss', short='Donruss', c='#f2c14e', full='2026 Panini Donruss Football Hobby', kind='Base with Rated Rookies, autographs, inserts',
                types='Base with Rated Rookies, parallels, inserts, and autographs, plus college (NIL) players.'),
           dict(k='obsidian', short='Obsidian', c='#8a6be0', full='2026 Panini Obsidian Football (First Off The Line)', kind='Dark-themed base, autographs and patches',
                types='Numbered base with Electric Etch parallels, autographs and patch cards, plus college (NIL) players.'),
           dict(k='bowman', short='Bowman Sapphire', c='#5aa9ff', full='2026 Bowman Football Sapphire Edition', kind='Mostly college (NIL) players, plus NFL rookies',
                types='Sapphire parallels of the Bowman base, prospects and rookies, inserts and autographs.'),
           dict(BOX_INCEPTION, full='2026 Topps Inception Football Hobby (1 box)')],
    spots=[team_spot(tid(t), t, [t]) for t, _ in cc872_teams] + [team_spot('college', 'College (NIL) cards', [], nil='ABCDEFGHIJKLMNOPQRSTUVWXYZ')],
    rules=[RGL_LIVE_GROUPS,
           ['Pass the Turkey', ['At the start of the break, one team gets the "turkey" and a target number from 1 to 32.',
                                'A team takes the turkey when it pulls a serial-numbered card whose number (the left side, like the 26 in 26/99) starts or ends with either digit of the target. The target then becomes that card\'s number. For example, with a target of 6, cards numbered 6, 63 or 26 take it.',
                                'Whoever holds the turkey at the end of the break gets $1,000 in RGL store credit.']],
           RGL_TEAM_RULE,
           ['College (NIL) cards', ['NIL stands for name, image and likeness: college players who aren\'t in the NFL yet. In its NFL team breaks RGL randomizes those cards to all spots at the end of the break, so they\'re listed together here.', 'College players already in the NFL go to their NFL team.']],
           RGL_MULTI],
    notes=['Two boxes aren\'t in this guide yet: 2025 Panini Prizm International and 2025 Panini Revolution Premium. We don\'t have their official checklists, so check those cards with RGL.',
           'Filler entries are sold too ($48.50 each); see RGL\'s listing for how fillers work.'],
    sources=[['RGL #6136 break page (Run Good Life)', rgl_url(RGL6136_H)], SRC_CHROME,
             ['Panini Donruss Football checklist (official Panini CSV)', SRC_PANINI], ['Panini Obsidian Football checklist (official Panini CSV)', SRC_PANINI],
             _src('2026-bowman-football-sapphire-edition', 'Bowman Football Sapphire Edition'), SRC_INCEPTION],
)
close(rgl6136, 'Wednesday, November 25, 2026', ['7 boxes', '24 spots for 32 teams', '$194 per spot, fillers $48.50', 'Teams randomized live', '$1,000 turkey prize'])  # stream showed #6140 running (Nov 26, 2:08 am Eastern)

RGL6138_H = 'rgl-6138-gilded-cosmic-random-team-11-25-26'
rgl6138 = dict(
    id='rgl6138', title='RGL #6138 Gilded & Cosmic (Random Team)', kicker='Run Good Life · Random team · MLB',
    url=rgl_url(RGL6138_H),
    when=_when(WED, '10:30 pm', '1:30 am Thursday'),
    facts=['6 boxes (4 listed here)', '20 spots for 30 teams', '$176 per spot, fillers $44', 'Teams randomized live'],
    format='team', checked='Spots were still for sale when checked on November 25, 2026, around 6:15 pm Eastern.',
    boxes=[dict(rgl6129['boxes'][4], full='2026 Topps Finest Baseball (1 Mega box)'),
           dict(rgl6129['boxes'][2]),
           dict(k='cosmic', short='Cosmic Chrome', c='#8a6be0', full='2026 Topps Cosmic Chrome Baseball Hobby', kind='Space-themed Chrome base, autographs, inserts',
                types='Cosmic-themed Chrome base and Refractor parallels, inserts, and autographs.'),
           dict(rgl6129['boxes'][1])],
    spots=list(MLB_RANDOM_SPOTS),
    rules=[RGL_LIVE_GROUPS, RGL_TEAM_RULE, RGL_MULTI],
    notes=['Two boxes aren\'t in this guide yet because we don\'t have their checklists: 2026 Topps Pristine and 2026 Topps Chrome Black. Check those cards with RGL.',
           'Cards are listed with the team the official checklist gives them. Expos cards are filed with the Nationals, old Cleveland cards with the Guardians and Washington Senators cards with the Twins.',
           'Filler entries are sold too ($44 each); see RGL\'s listing for how fillers work.'],
    sources=[['RGL #6138 break page (Run Good Life)', rgl_url(RGL6138_H)], rgl6129['sources'][5], rgl6129['sources'][3],
             _src('2026-topps-cosmic-chrome-baseball', 'Topps Cosmic Chrome Baseball'), rgl6129['sources'][2]],
)
close(rgl6138, 'Wednesday, November 25, 2026', ['6 boxes (4 listed here)', '20 spots for 30 teams', '$176 per spot, fillers $44', 'Teams randomized live'])  # stream showed #6140 running (Nov 26, 2:08 am Eastern)

RGL6139_H = 'rgl-6139-joy-of-five-star-2-random-team-11-25-26'
rgl6139 = dict(
    id='rgl6139', title='RGL #6139 Joy of Five Star #2 (Random Team)', kicker='Run Good Life · Random team · NBA',
    url=rgl_url(RGL6139_H),
    when=_when(WED, '11:15 pm', '2:15 am Thursday'),
    facts=['5 boxes', '21 spots for 30 teams', '$290 per spot, fillers $29', 'Teams randomized live'],
    format='team', checked='Spots were still for sale when checked on November 25, 2026, around 6:15 pm Eastern.',
    boxes=[dict(b) for b in rgl6131['boxes']],
    spots=[team_spot(tid(t), t, [t]) for t in NBA_TEAMS],
    rules=[RGL_LIVE_GROUPS, RGL_TEAM_RULE, RGL_MULTI],
    notes=['Same boxes as the first Joy of Five Star tonight (#6131): 2 Stadium Club boxes, Five Star, the Bob Ross Joy of Basketball box and Flagship.',
           'Seattle SuperSonics legends are filed with the Thunder here, since that\'s the same franchise today.',
           'Filler entries are sold too ($29 each); see RGL\'s listing for how fillers work.'],
    sources=[['RGL #6139 break page (Run Good Life)', rgl_url(RGL6139_H)]] + list(rgl6131['sources'][1:]),
)
close(rgl6139, 'Wednesday, November 25, 2026', ['5 boxes', '21 spots for 30 teams', '$290 per spot, fillers $29', 'Teams randomized live'])  # stream showed #6140 running (Nov 26, 2:08 am Eastern)

RGL6140_H = 'rgl-6140-half-case-delight-degen-random-team-11-25-26'
rgl6140 = dict(
    id='rgl6140', title='RGL #6140 Half Case Delight Degen (Random Team)', kicker='Run Good Life · Random team · NFL',
    url=rgl_url(RGL6140_H),
    when=_when(THU, '12:00 am', '3:00 am'),
    facts=['5 boxes', '22 spots for 32 teams', '$260 per spot, fillers $26', 'Teams randomized live'],
    format='team', checked='Spots were still for sale when checked on November 25, 2026, around 7:45 pm Eastern.',
    boxes=[dict(BOX_CHROME_J, full='2026 Topps Chrome Football Jumbo (1 box)'),
           dict(BOX_CHROME_H, k='chromeh', short='Chrome Hobby', c='#3ccf9a', full='2026 Topps Chrome Football Hobby (1 box)'),
           dict(BOX_CHROME_H, k='delight', short='Chrome Delight', c='#f2c14e', full='2026 Topps Chrome Football Breaker\'s Delight (3 boxes)',
                types='Chrome base and Refractors, rookie cards, autographs, inserts.')],
    spots=[team_spot(tid(t), t, [t]) for t, _ in cc872_teams] + [team_spot('college', 'College (NIL) cards', [], nil='ABCDEFGHIJKLMNOPQRSTUVWXYZ')],
    rules=[RGL_LIVE_GROUPS, RGL_TEAM_RULE,
           ['College (NIL) cards', ['NIL stands for name, image and likeness: college players who aren\'t in the NFL yet. In its NFL team breaks RGL randomizes those cards to all spots at the end of the break, so they\'re listed together here.']],
           RGL_MULTI],
    notes=['All five boxes are 2026 Topps Chrome Football (Jumbo, Hobby and Breaker\'s Delight), so they share one checklist.',
           'RGL\'s listing says Wednesday at 12 am Pacific; that\'s the overnight slot after Wednesday\'s stream, early Thursday.',
           'Filler entries are sold too ($26 each); see RGL\'s listing for how fillers work.'],
    sources=[['RGL #6140 break page (Run Good Life)', rgl_url(RGL6140_H)], SRC_CHROME],
)
close(rgl6140, 'Thursday, November 26, 2026', ['5 boxes', '22 spots for 32 teams', '$260 per spot, fillers $26', 'Teams randomized live'])  # Daniel said the night was done (Nov 26, 8:18 am Eastern)

# RGL #6141 Peak Degeneracy #6 (Random Letter), multi-sport, posted Nov 25. All 10 products listed (Obsidian Soccer, Select Basketball and Pokemon added from Daniel's files).
RGL6141_H = 'rgl-6141-peak-degeneracy-6-random-letter-11-25-26'
RGL6141_LIB = dict(leaf='2026-leaf-originals-multi-sport', donruss='2026-donruss-football', finest='2026-topps-finest-baseball',
                   inception='2026-topps-inception-football', samurai='2026-topps-chrome-baseball-team-samurai-japan-collection',
                   sc='2025-26-topps-stadium-club-basketball', neon='2026-topps-neon-marvel', obsidian='2025-26-panini-obsidian-soccer',
                   select='2025-26-panini-select-basketball', pokemon='2026-pokemon-30th-celebration')
rgl6141 = dict(
    id='rgl6141', title='RGL #6141 Peak Degeneracy #6 (Random Letter)', kicker='Run Good Life · Random letter · Multi-sport',
    url=rgl_url(RGL6141_H),
    when=_when(THU, '12:45 am', '3:45 am'),
    facts=['11 boxes', '21 letter groups', '$188 per spot, fillers $47', 'Letters randomized live'],
    format='random', checked='Spots were still for sale when checked on November 25, 2026, around 7:45 pm Eastern. RGL then set 21 letter groups live on stream.',
    boxes=[dict(k='leaf', short='Leaf Originals', c='#3ccf9a', full='2026 Leaf Originals', kind='Multi-sport autographs', types='Autographs of athletes across sports.'),
           dict(k='donruss', short='Donruss NFL', c='#f2c14e', full='2026 Panini Donruss Football Hobby', kind='Base with Rated Rookies, autographs, inserts', types='Base with Rated Rookies, parallels, inserts and autographs.'),
           dict(k='finest', short='Finest MLB', c='#e2545e', full='2026 Topps Finest Baseball (1 Mega box)', kind='Base with Refractors, autographs, inserts', types='Finest base and Refractors, rookie cards, autographs, inserts.'),
           dict(BOX_INCEPTION, full='2026 Topps Inception Football Hobby (1 box)'),
           dict(k='samurai', short='Samurai Japan', c='#5aa9ff', full='2026 Topps Chrome Baseball Team Samurai Japan Collection (2 boxes)', kind='Japan national team players', types='Chrome cards of Team Samurai Japan players, parallels and autographs.'),
           dict(k='sc', short='Stadium Club NBA', c='#c86bff', full='2025-26 Topps Stadium Club Basketball Hobby (1 box)', kind='Photo-driven base set, autographs and inserts', types='Base with photo variations, inserts, and autographs.'),
           dict(k='neon', short='Marvel Neon', c='#8a6be0', full='2026 Topps Marvel Neon Hobby (1 box)', kind='Marvel characters, neon-style parallels, inserts', types='Base with neon parallels, inserts and autographs.'),
           dict(k='obsidian', short='Obsidian Soccer', c='#7a8494', full='2025-26 Panini Obsidian Soccer (1 box)', kind='Soccer players, autographs and memorabilia', types='Numbered base with Electric Etch parallels, autographs and patch cards.'),
           dict(k='select', short='Select NBA', c='#e07a2e', full='2025-26 Panini Select Basketball Hobby (1 box)', kind='Concourse, Premier and Courtside tiers, autographs, inserts', types='Tiered base with Prizm parallels, inserts and autographs.'),
           dict(k='pokemon', short='Pokemon', c='#f5d000', full='2026 Pokemon TCG 30th Celebration Elite Trainer Box (1 box)', kind='Pokemon cards, plus a classic collection', types='Pokemon, trainer and item cards from the 30th Celebration set, and classic cards from past sets. Listed by the name on the card.')],
    spots=[],  # filled in below from the letters that have names
    rules=[['How the spots were set', ['RGL set the letter groups live on stream. This guide follows the board RGL showed: 21 groups, with C, J and S split on the second letter (CA-CH and CI-CZ, JA-JE and JF-JZ, SA-SH and SI-SZ) and several groups that bundle more than one letter (E / F, H / I, N / O, P / U, V / Q / W and X / Y / Z).', 'The listing said 16 spots, but the board has 21 groups.', 'The board has no group for numbers, and none of the names in these boxes start with one.']],
           ['First letter of the first name', ['RGL\'s board says first name, so Josh Allen is J (JF-JZ) and Chase Elliott is C (CA-CH). For Marvel cards, it\'s the character\'s name as printed.', 'The board says T (No The), so a leading "The" doesn\'t count: The Thing is T and The Maker is M.']],
           ['Cards with more than one name', ['Each person on a dual or multi-person card is listed under their own letter.', RGL_MULTI[1][0]]]],
    notes=['Pokemon cards are listed by the name on the card (Pikachu is P, Alolan Exeggutor is A). Ask RGL how they letter Pokemon, trainer and item cards.',
           'RGL\'s listing says Wednesday at 12:45 am Pacific; that\'s the overnight slot after Wednesday\'s stream, early Thursday.',
           'Filler entries are sold too ($47 each); see RGL\'s listing for how fillers work.'],
    sources=[['RGL #6141 break page (Run Good Life)', rgl_url(RGL6141_H)]] + [_src(v, n) for v, n in (
        ('2026-leaf-originals-multi-sport', 'Leaf Originals'), ('2026-topps-finest-baseball', 'Topps Finest Baseball'),
        ('2026-topps-chrome-baseball-team-samurai-japan-collection', 'Topps Chrome Team Samurai Japan'),
        ('2025-26-topps-stadium-club-basketball', 'Topps Stadium Club Basketball'), ('2026-topps-neon-marvel', 'Topps Neon Marvel'))]
        + [['Panini Donruss Football checklist (official Panini CSV)', SRC_PANINI], SRC_INCEPTION,
           ['Panini Obsidian Soccer and Select Basketball checklists (official Panini CSVs)', SRC_PANINI],
           ['Pokemon TCG 30th Celebration card list (official Pokemon PDF)', 'https://www.pokemon.com/us/pokemon-tcg']],
)
close(rgl6141, 'Thursday, November 26, 2026', ['11 boxes', '21 letter groups', '$188 per spot, fillers $47', 'Letters randomized live'])  # Daniel said the night was done (Nov 26, 8:18 am Eastern)

# rgl6143 draft removed (Daniel, Nov 25): no guessed setups; the page builder builds #6143 from RGL's listing.

# RGL #6135 Oops All Animation (Random Letter), posted Nov 25. 5 of its 7 boxes have checklists (X-Men '97 and Pixar Gold added Nov 25 from Daniel's links).
RGL6135_H = 'rgl-6135-oops-all-animation-random-letter-11-25-26'
RGL6135_LIB = dict(neon='2026-topps-neon-marvel', mintm='2026-topps-mint-marvel', mintd='2026-topps-mint-disney', xmen='2025-topps-finest-x-men-97', pixar='2025-topps-pixar-gold')
rgl6135 = dict(
    id='rgl6135', title='RGL #6135 Oops All Animation (Random Letter)', kicker='Run Good Life · Random letter · Marvel, DC and Disney',
    url=rgl_url(RGL6135_H),
    when=_when(WED, '8:00 pm', '11:00 pm'),
    facts=['7 boxes (5 listed here)', '15 spots', '$156 per spot, fillers $39', 'Letters randomized live'],
    format='random', checked='Spots were still for sale when checked on November 25, 2026, around 4:50 pm Eastern.',
    boxes=[dict(k='neon', short='Marvel Neon', c='#c86bff', full='2026 Topps Marvel Neon Hobby', kind='Marvel characters, neon-style parallels, inserts',
                types='Base with neon parallels, inserts, and autographs.'),
           dict(k='mintm', short='Marvel Mint', c='#e2545e', full='2026 Topps Marvel Mint', kind='Marvel characters, Chrome cards and an encased hit',
                types='Chrome base and parallels, inserts, encased hits and autographs.'),
           dict(k='mintd', short='Disney Mint', c='#5aa9ff', full='2026 Topps Disney Mint', kind='Disney characters, Chrome cards and an encased hit',
                types='Chrome base and parallels, inserts, encased hits and autographs.'),
           dict(k='xmen', short='Finest X-Men \'97', c='#f2c14e', full='2025 Topps Finest X-Men \'97 Hobby', kind='X-Men \'97 cartoon characters, Refractors, voice actor autographs',
                types='Common, Uncommon and Rare base with Refractor parallels, inserts like Previously On X-Men and Children of the Atom, and voice actor autographs.'),
           dict(k='pixar', short='Pixar Gold', c='#3ccf9a', full='Topps Pixar Gold', kind='Pixar characters, Chrome cards and an encased hit',
                types='Gilded Pixar base with gold parallels, inserts like Pixar Perfection and Animated Aura, and voice actor autographs (single and dual).')],
    spots=[],  # filled in below from the letters that have names
    rules=[['How RGL groups the letters', ['RGL sells 15 spots, and how the letters are grouped into them is set live on stream; the listing doesn\'t post it.', 'This guide lists every letter on its own, so once you know your letters, look each one up here.']],
           ['First letter of the name on the card', ['Letters here go by the first letter of the character\'s name as printed (Spider-Man is S, Captain America is C). RGL\'s listing doesn\'t say how it handles characters, so check with RGL.']],
           ['Cards with more than one character', ['Each character on a dual or multi-character card is listed under their own letter.', RGL_MULTI[1][0]]]],
    notes=['Two boxes aren\'t in this guide yet because we don\'t have their checklists: 2025 Kakawow DC Aura and 2026 Card Fun Disney Chronoz. Check those cards with RGL.',
           'The listing says 2026 Topps Pixar Gold; the set Topps sells is 2025 Pixar Gold (released January 2026), so this guide uses that checklist.',
           'Voice actor autographs: Pixar Gold cards name the character, so they\'re listed under the character. X-Men \'97 autographs are listed under the actor\'s name (the checklist doesn\'t name the character). Ask RGL which letter they count under.',
           'Scene cards that name no single character (X-Men \'97 Greatest Hits, Pixar Gold Golden Moments and Wall Art) aren\'t listed.',
           'Filler entries are sold too ($39 each); see RGL\'s listing for how fillers work.'],
    sources=[['RGL #6135 break page (Run Good Life)', rgl_url(RGL6135_H)], _src(RGL6135_LIB['neon'], 'Topps Neon Marvel'),
             _src(RGL6135_LIB['mintm'], 'Topps Mint Marvel'), _src(RGL6135_LIB['mintd'], 'Topps Mint Disney'),
             _src(RGL6135_LIB['xmen'], 'Topps Finest X-Men \'97'), _src(RGL6135_LIB['pixar'], 'Topps Pixar Gold')],
)
close(rgl6135, 'Wednesday, November 25, 2026', ['7 boxes (5 listed here)', '15 spots', '$156 per spot, fillers $39', 'Letters randomized live'])  # stream showed #6140 running (Nov 26, 2:08 am Eastern)

# RGL #6137 Pro Debut Half Case (Random Letter), posted Nov 25.
RGL6137_H = 'rgl-6137-pro-debut-half-case-random-letter-11-25-26'
rgl6137 = dict(
    id='rgl6137', title='RGL #6137 Pro Debut Half Case (Random Letter)', kicker='Run Good Life · Random letter · MLB prospects',
    url=rgl_url(RGL6137_H),
    when=_when(WED, '9:45 pm', '12:45 am Thursday'),
    facts=['4 boxes (half case)', '10 spots', '$98 per spot, fillers $24.50', 'Letters randomized live'],
    format='random', checked='Spots were still for sale when checked on November 25, 2026, around 5:35 pm Eastern.',
    boxes=[dict(k='prodebut', short='Pro Debut', c='#3ccf9a', full='2026 Topps Pro Debut Baseball Hobby (4 boxes)', kind='Minor league prospects, autographs, inserts',
                types='Base cards of minor league prospects in their pro debut uniforms, parallels, inserts, and autographs.')],
    spots=[],  # filled in below from the letters that have names
    rules=[['How RGL groups the letters', ['RGL sells 10 spots, and how the letters are grouped into them is set live on stream; the listing doesn\'t post it.', 'This guide lists every letter on its own, so once you know your letters, look each one up here.']],
           ['First letter of the name on the card', ['Letters here go by the first letter of the first name on the card (Aidan Miller is A). RGL\'s listing doesn\'t say first or last name, so check with RGL.']],
           ['Cards with more than one player', ['Each person on a dual or multi-player card is listed under their own letter.', RGL_MULTI[1][0]]]],
    notes=['Filler entries are sold too ($24.50 each); see RGL\'s listing for how fillers work.'],
    sources=[['RGL #6137 break page (Run Good Life)', rgl_url(RGL6137_H)], _src('2026-topps-pro-debut-baseball', 'Topps Pro Debut Baseball')],
)
close(rgl6137, 'Wednesday, November 25, 2026', ['4 boxes (half case)', '10 spots', '$98 per spot, fillers $24.50', 'Letters randomized live'])  # stream showed #6140 running (Nov 26, 2:08 am Eastern)

# RGL "#612xMarvel" Marvel Neon & Mint (Random Letter), posted Nov 25 with a placeholder break number. The listing's body text
# still shows RGL #6123 and a November 21 start, so no current start time is posted. Boxes come from the listing's product list.
RGL612XMARVEL_H = 'rgl-612xmarvel-marvel-neon-mint-random-letter-11-25-26'
RGL612XMARVEL_LIB = dict(neon='2026-topps-neon-marvel', mintm='2026-topps-mint-marvel', aura='2025-kakawow-aura-marvel')
rgl612xmarvel = dict(
    id='rgl612xmarvel', title='RGL Marvel Neon & Mint (Random Letter)', kicker='Run Good Life · Random letter · Marvel',
    url=rgl_url(RGL612XMARVEL_H),
    when='Wednesday, November 25, 2026, on the Rungoodlife YouTube channel. RGL hasn\'t posted a current start time.',
    facts=['4 boxes', '13 spots', '$122 per spot, fillers $30.50', 'Letters randomized live'],
    format='random', checked='Spots were still for sale when checked on November 25, 2026, around 8:40 pm Eastern.',
    boxes=[dict(k='neon', short='Marvel Neon', c='#c86bff', full='2026 Topps Marvel Neon Hobby (2 boxes)', kind='Marvel characters, neon-style parallels, inserts',
                types='Base with neon parallels, inserts, and autographs.'),
           dict(k='mintm', short='Marvel Mint', c='#e2545e', full='2026 Topps Marvel Mint (1 box)', kind='Marvel characters, Chrome cards and an encased hit',
                types='Chrome base and parallels, inserts, encased hits and autographs.'),
           dict(k='aura', short='Kakawow Aura', c='#f2c14e', full='2025 Kakawow Marvel Aura (1 box)', kind='Marvel characters, Aura parallels, Script Art cards',
                types='Base characters with parallels, inserts, and Script Art cards (facsimile signatures, counted as autographs).')],
    spots=[],  # filled in below from the letters that have names
    rules=[['How RGL groups the letters', ['RGL sells 13 spots, and how the letters are grouped into them is set live on stream; the listing doesn\'t post it.', 'This guide lists every letter on its own, so once you know your letters, look each one up here.']],
           ['First letter of the name on the card', ['Letters here go by the first letter of the character\'s name as printed (Spider-Man is S, Captain America is C). RGL\'s listing doesn\'t say how it handles characters, so check with RGL.']],
           ['Cards with more than one character', ['Each character on a dual or multi-character card is listed under their own letter.', RGL_MULTI[1][0]]]],
    notes=['RGL listed this one as "#612xMarvel" with no real break number. The text inside the listing still says RGL #6123 and a November 21 start, so it looks copied from an older break. The boxes here follow the listing\'s product list; check the number, date and boxes with RGL.',
           'Filler entries are sold too ($30.50 each); see RGL\'s listing for how fillers work.'],
    sources=[['RGL Marvel Neon & Mint break page (Run Good Life)', rgl_url(RGL612XMARVEL_H)], _src(RGL612XMARVEL_LIB['neon'], 'Topps Neon Marvel'),
             _src(RGL612XMARVEL_LIB['mintm'], 'Topps Mint Marvel'), _src(RGL612XMARVEL_LIB['aura'], 'Kakawow Aura Marvel')],
)
close(rgl612xmarvel, 'Wednesday, November 25, 2026', ['4 boxes', '13 spots', '$122 per spot, fillers $30.50', 'Letters randomized live'])  # Daniel said the night was done (Nov 26, 8:18 am Eastern)

# RGL #6142 UFC Royalty Mixer (Random Letter), posted Nov 25. Only the 2026 Topps Chrome UFC checklist is in the library; the
# listing's other three boxes (Stadium Club, Finest, Royalty) have no checklist here yet.
RGL6142_H = 'rgl-6141-royalty-half-case-2-random-letter-11-25-26'
rgl6142 = dict(
    id='rgl6142', title='RGL #6142 UFC Royalty Mixer (Random Letter)', kicker='Run Good Life · Random letter · UFC',
    url=rgl_url(RGL6142_H),
    when=_when(THU, '1:30 am', '4:30 am'),
    facts=['4 boxes (1 listed here)', '15 spots', '$128 per spot, fillers $32', 'Letters randomized live'],
    format='random', checked='Spots were still for sale when checked on November 25, 2026, around 8:40 pm Eastern.',
    boxes=[dict(k='chrome', short='Chrome UFC', c='#e2545e', full='2026 Topps Chrome UFC Hobby (1 box)', kind='UFC fighters, Chrome base, Refractors, autographs',
                types='Chrome base and parallels, inserts, and autographs.')],
    spots=[],  # filled in below from the letters that have names
    rules=[['How RGL groups the letters', ['RGL sells 15 spots, and how the letters are grouped into them is set live on stream; the listing doesn\'t post it.', 'This guide lists every letter on its own, so once you know your letters, look each one up here.']],
           ['First letter of the name on the card', ['Letters here go by the first letter of the first name on the card (Alex Pereira is A). RGL\'s listing doesn\'t say first or last name, so this guide sorts by first name; check with RGL.']],
           ['Cards with more than one fighter', ['Each person on a dual or multi-fighter card is listed under their own letter.', RGL_MULTI[1][0]]]],
    notes=['Three of the four boxes are not in this guide yet because we don\'t have their checklists: Topps Stadium Club, Topps Finest and Topps Royalty. The listing doesn\'t name the sport for its boxes; the title says UFC. The listing says 2026 Topps Royalty, and the only Royalty UFC list we have is the 2025 one, so it isn\'t used here. Check those cards with RGL.',
           'RGL\'s listing says Wednesday, November 25 at 1:30 am Pacific, which had already passed when it was posted; this guide treats it as the overnight slot after Wednesday\'s stream, early Thursday, like #6141. Check with RGL.',
           'RGL reused the link from an earlier draft of this product, so the link says 6141.',
           'Filler entries are sold too ($32 each); see RGL\'s listing for how fillers work.'],
    sources=[['RGL #6142 break page (Run Good Life)', rgl_url(RGL6142_H)], _src('2026-topps-chrome-ufc', 'Topps Chrome UFC')],
)
close(rgl6142, 'Thursday, November 26, 2026', ['4 boxes (1 listed here)', '15 spots', '$128 per spot, fillers $32', 'Letters randomized live'])  # Daniel said the night was done (Nov 26, 8:18 am Eastern)

# RGL "#612XWWE2" Chrome in the Club PYL #2, posted Nov 25 without a real break number or start time. Same letters and
# prices as #6128; boxes are #6128's minus the Chrome Hobby box. If RGL renumbers it, update the id note and title here.
RGL612XWWE2_H = 'rgl-612xwwe2-chrome-in-the-club-pyl-2-pick-your-letter-first-name-11-25-26'
rgl612xwwe2_avail = [1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1]
rgl612xwwe2 = dict(
    id='rgl612xwwe2', title='RGL Chrome in the Club PYL #2', kicker='Run Good Life · Pick your letter · WWE',
    url=rgl_url(RGL612XWWE2_H),
    when='Wednesday, November 25, 2026, on the Rungoodlife YouTube channel. RGL hasn\'t posted a start time yet.',
    facts=['5 boxes', '27 letter spots', '$40 to $235 per spot'],
    live=dict(shop='rgl', handle=RGL612XWWE2_H),
    format='pyl', checked='Availability checked against Run Good Life\'s store data on November 25, 2026, around 6:15 pm Eastern: 21 of 27 spots open.',
    boxes=[dict(rgl6128['boxes'][0]),
           dict(rgl6128['boxes'][1], full='2026 Topps Chrome WWE Breaker\'s Delight (1 box)'),
           rgl6128['boxes'][2], rgl6128['boxes'][3]],
    spots=[dict(sp, status='open' if a else 'sold') for sp, a in zip(rgl6128_spots, rgl612xwwe2_avail)],
    rules=list(rgl6128['rules']),
    notes=['RGL listed this one as "#612XWWE2" with no start time yet; it will most likely get a real break number later.',
           'Same letters and prices as the first Chrome in the Club PYL tonight (#6128), with one Chrome box (Breaker\'s Delight) instead of two.'] + list(rgl6128['notes']),
    sources=[['RGL Chrome in the Club PYL #2 break page (Run Good Life)', rgl_url(RGL612XWWE2_H)]] + list(rgl6128['sources'][1:]),
)
close(rgl612xwwe2, 'Wednesday, November 25, 2026', ['5 boxes', '27 letter spots', '$40 to $235 per spot'])  # Daniel said WWE was done (Nov 26, 2:08 am Eastern)

# ---------------- JWJ #0247 Exalted Universe Club (random letters; ran Nov 23, built later at Daniel's request, Nov 26) ----------------
def rl_spot(id, label, letters_, g=None, anyg=''):
    return dict(id=id, label=label, letters=list(letters_), g=g, anyg=anyg, price=None, status=None)
jwj0247u_spots = [
    rl_spot('a-m', 'A', 'A', 'M'), rl_spot('a-w', 'A', 'A', 'F'), rl_spot('b-m', 'B', 'B', 'M'), rl_spot('b-w', 'B', 'B', 'F'),
    rl_spot('c', 'C', 'C'), rl_spot('def', 'D / E / F', 'DEF'), rl_spot('ghi', 'G / H / I', 'GHI'), rl_spot('j-m', 'J', 'J', 'M'),
    rl_spot('j-w', 'J / W', 'J', 'F', anyg='W'), rl_spot('k', 'K', 'K'), rl_spot('l', 'L', 'L'), rl_spot('mn', 'M / N', 'MN'),
    rl_spot('opq', 'O / P / Q', 'OPQ'), rl_spot('r-m', 'R', 'R', 'M'), rl_spot('r-w', 'R / Z', 'R', 'F', anyg='Z'),
    rl_spot('s-m', 'S', 'S', 'M'), rl_spot('s-w', 'S', 'S', 'F'), rl_spot('t-m', 'T', 'T', 'M'), rl_spot('t-w', 'T', 'T', 'F'),
    rl_spot('uvxy', 'U / V / X / Y / 1', 'UVXY#'),
]
JWJ_WOMEN = RGL_WOMEN | lib_women('2026-topps-universe-wwe', '2025-topps-exalted-wwe')
def jwj_wwe_gender(n):
    return 'F' if (n in JWJ_WOMEN or key_of(n) in JWJ_WOMEN or wwe_gender(n) == 'F') else 'M'
jwj0247u = dict(
    id='jwj0247u', title='JWJ #0247 Exalted Universe Club', kicker='JWJ Collector Breaks \u00b7 Random letter \u00b7 WWE',
    url='https://jwjcollectorbreaks.com/products/jwj-0247-exalted-universe-club',
    when='Monday, November 23, 2026 on the JWJ Breaks YouTube channel',
    facts=['5 boxes', '20 letter spots', '$85 per spot', 'Letters randomized live'],
    format='random', checked='',
    boxes=[dict(WWE_BOX['sc'], full='2026 Topps Stadium Club WWE Hobby (2 boxes)'),
           dict(k='universe', short='Universe', c='#5ad1c8', full='2026 Topps Universe WWE Hobby (2 boxes)', kind='base set, autographs, inserts',
                types='Base cards, autographs and inserts, taken from the official Topps checklist. The checklist file here lists names only, so card types aren\'t broken out.'),
           WWE_BOX['exalted']],
    spots=jwj0247u_spots, rules=WWE_RULES,
    notes=['JWJ\'s listing was posted late and sold out quickly, so this guide was built after the break ran. There is no sold or open status on the spots.',
           'The listing says "J - Women / W" and "R - Women / Z". This guide assumes every W and every Z name (men and women) goes to those spots, since no other spot has a W or a Z.',
           'U, V, X, Y and anyone whose name starts with a number share the last spot.',
           'The listing says "2025 Topps Exalted WWE". That is the Exalted WWE set Topps released in April 2026, so that checklist is used here.'],
    sources=[['JWJ #0247 break page', 'https://jwjcollectorbreaks.com/products/jwj-0247-exalted-universe-club'],
             ['Stadium Club WWE checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Stadium_Club_WWE_-_Checklist.pdf?v=1791221305'],
             ['Universe WWE checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/26UWWE_-_2026_Topps_Universe_WWE_Checklist_1_.xls_-_Compatibility_Mode.pdf?v=1792698807'],
             ['Exalted WWE checklist (official Topps)', 'https://cdn.shopify.com/s/files/1/0662/9749/5709/files/FINAL_CHECKLIST_2025EXALTEDWWE.pdf?v=1774986961']],
)
close(jwj0247u, 'Monday, November 23, 2026', ['5 boxes', '20 letter spots', '$85 per spot', 'Letters randomized live'])

# ---------------- CC873 Marvel Rivals PYC (pick your character; ran Nov 22, built later at Daniel's request, Nov 26) ----------------
# No published checklist for 2026 Card.Fun Marvel Rivals Eternal Glory was found (checked Nov 26), so the box has no names yet.
# Spots and prices are the 41 variants on Colfax's listing.
CC873_V = [('Adam Warlock', 10), ('Black Panther', 20), ('Black Widow', 20), ('Blade', 20), ('Captain America', 30), ('Cloak & Dagger', 15), ('Doctor Strange', 20),
           ('Emma Frost', 25), ('Groot', 20), ('Hawkeye', 10), ('Hela', 10), ('Hulk', 30), ('Human Torch', 20), ('Invisible Woman', 20), ('Iron Fist', 10),
           ('Iron Man', 30), ('Jeff the Land Shark', 30), ('Loki', 20), ('Luna Snow', 25), ('Magik', 25), ('Magneto', 20), ('Mantis', 15), ('Mister Fantastic', 15),
           ('Moon Knight', 20), ('Namor', 10), ('Peni Parker', 10), ('Phoenix', 20), ('Psylocke', 25), ('Rocket Raccoon', 20), ('Scarlet Witch', 25),
           ('Spider-Man', 40), ('Squirrel Girl', 25), ('Star-Lord', 20), ('Storm', 20), ('The Punisher', 20), ('The Thing', 10), ('Thor', 30), ('Ultron', 20),
           ('Venom', 40), ('Winter Soldier', 15), ('Wolverine', 40)]
cc873 = dict(
    id='cc873', title='CC873 Marvel Rivals PYC (Pick Your Character)', unit='character', kicker='Colfax Collectibles \u00b7 Pick your character \u00b7 Marvel Rivals',
    url='https://colfaxcc.com/products/cc873-marvel-rivals-pyc-pick-your-character',
    when='Sunday, November 22, 2026, 5:00 pm Central (6:00 pm Eastern)',
    facts=['5 boxes (half case)', '41 character spots', '$10 to $40 per spot'],
    format='pyt', checked='',
    boxes=[dict(k='rivals', short='Eternal Glory', c='#e2545e', full='2026 Card.Fun Marvel Rivals Eternal Glory Hobby (5 boxes, half case)',
                kind='Marvel Rivals game cards, 10 packs per box, 5 cards per pack. Checklist not found.',
                types='Series like Hero Debut, Team Up, Art Gallery, Hero Positioning and X Evolution, plus Glory MVP and Perfection MVP one-of-ones and Hero Signature autographs. Retailers describe 17 themed series and over 1,800 cards, and say a box has 2 to 4 limited-edition cards on average.')],
    spots=team_spots_from_variants([(n, pr, 0) for n, pr in CC873_V], lambda x: x),
    rules=[['One spot per character', ['Each spot is a single Marvel Rivals character, and you can buy as many spots as you like while they last.', 'Prices run from $10 to $40 by character: Spider-Man, Venom and Wolverine are $40, and the least expensive characters are $10.']],
           ['Cards with two characters', ['Team Up cards show more than one character. Colfax\'s listing doesn\'t say how those are split, so ask Colfax.', 'Colfax\'s general rules for cards with more than one team are on its rules page.']]],
    notes=['No checklist for this set was found, so this guide shows the spots and prices but not the individual cards in each one.',
           'The listing says "2025 Marvel Rivals Eternal Glory Hobby". Retailers sell it as the 2026 Card.Fun Marvel Rivals Eternal Glory Hobby, released in April 2026, so this guide treats them as the same product.'],
    sources=[['CC873 break page (Colfax Collectibles)', 'https://colfaxcc.com/products/cc873-marvel-rivals-pyc-pick-your-character'],
             ['Colfax group break rules', 'https://colfaxcc.com/pages/rules'],
             ['Eternal Glory hobby box description (DA Card World)', 'https://www.dacardworld.com/entertainment/marvel-rivals-eternal-glory-hobby-box-card-fun-2026'],
             ['Eternal Glory series and variants (Cardbot)', 'https://cardbot.com.au/products/2026-marvel-rivals-eternal-glory-hobby-box']],
)
close(cc873, 'Sunday, November 22, 2026', ['5 boxes (half case)', '41 character spots', '$10 to $40 per spot'])

# ---------------- Acme Packs breaks for Friday, November 27, 2026 (GB1041 to GB1045) ----------------
ACME_FRI = 'Friday, November 27, 2026, %s Central (%s Eastern). If it doesn\'t fill, it rolls to the next break night.'
ACME_CHK = 'When checked on November 26, 2026, around 1:40 pm Eastern, the break was listed and spots were for sale.'
def _srcx(pid, label, by='official Topps'):
    u = next((l.split('source:', 1)[1].strip() for l in open(os.path.join(LIB, pid + '.txt'), encoding='utf-8') if l.startswith('# source:')), '')
    return [label + ' checklist (' + by + ')', u]
ACME_FILLER = 'Filler entries are sold too (%s for a 25%% chance at a spot); see Acme\'s filler listing for how they work.'
GB_LETTER_FIRST = ['First letter of the first name', ['Acme\'s listing: every card goes to the first letter of the first name of the athlete on the card. Arch Manning goes to the "A" spot.']]
GB_LETTER_MULTI = ['Cards with more than one name', ['Each person on a dual or multi-player card is listed under their own letter here. Acme randomizes cards like that between the spots involved.', 'Anything the rules don\'t cover is up to the breaker.']]

# GB1041: Midnight Chrome Inception (random team, NFL)
GB1041_H = 'gb1041-midnight-chrome-inception-random-team'
gb1041 = dict(
    id='gb1041', title='GB1041 Midnight Chrome Inception', kicker='Acme Packs · Random team · NFL',
    url=acme_url(GB1041_H), when=ACME_FRI % ('5:00 pm', '6:00 pm'),
    facts=['5 boxes', '28 team spots (24 teams, 4 combos)', '$120 per spot, $30 for a 25% filler', 'Teams randomized live'],
    format='team', checked=ACME_CHK,
    boxes=[BOX_INCEPTION, BOX_MIDNIGHT, BOX_CHROME_H],
    spots=[team_spot(re.sub(r'[^a-z0-9]', '', l.lower()), l, ts) for l, ts in gb1038b_spots],
    rules=ACME_RULES,
    notes=['Cards are listed with the team the official checklist gives them.', ACME_FILLER % '$30'],
    sources=[['GB1041 break page (Acme Packs)', acme_url(GB1041_H)], ACME_TERMS, SRC_INCEPTION, SRC_MIDNIGHT, SRC_CHROME],
)

# GB1042: Chrome At The Museum (random team, MLB)
GB1042_H = 'gb1042-chrome-at-the-museum-random-teams'
gb1042_spots = [('Athletics', ['Athletics']), ('Atlanta Braves', ['Braves']), ('Arizona Diamondbacks / Tampa Bay Rays', ['Diamondbacks', 'Rays']),
                ('Baltimore Orioles', ['Orioles']), ('Boston Red Sox', ['Red Sox']), ('Chicago Cubs', ['Cubs']), ('Chicago White Sox', ['White Sox']),
                ('Cincinnati Reds', ['Reds']), ('Cleveland Guardians', ['Guardians']), ('Colorado Rockies', ['Rockies']), ('Detroit Tigers', ['Tigers']),
                ('Houston Astros', ['Astros']), ('Kansas City Royals', ['Royals']), ('Los Angeles Angels', ['Angels']), ('Los Angeles Dodgers', ['Dodgers']),
                ('Miami Marlins / Minnesota Twins', ['Marlins', 'Twins']), ('Milwaukee Brewers', ['Brewers']), ('New York Mets', ['Mets']),
                ('New York Yankees', ['Yankees']), ('Philadelphia Phillies', ['Phillies']), ('Pittsburgh Pirates', ['Pirates']),
                ('San Diego Padres / Texas Rangers', ['Padres', 'Rangers']), ('San Francisco Giants', ['Giants']), ('Seattle Mariners', ['Mariners']),
                ('St. Louis Cardinals', ['Cardinals']), ('Toronto Blue Jays', ['Blue Jays']), ('Washington Nationals', ['Nationals'])]
BOX_MUSEUM_B = dict(next(b for b in rgl6129['boxes'] if b['k'] == 'museum'), full='2026 Topps Museum Collection Baseball Hobby (2 boxes)')
gb1042 = dict(
    id='gb1042', title='GB1042 Chrome At The Museum', kicker='Acme Packs · Random team · MLB',
    url=acme_url(GB1042_H), when=ACME_FRI % ('6:00 pm', '7:00 pm'),
    facts=['6 boxes', '27 team spots (24 teams, 3 combos)', '$105 per spot, $26.25 for a 25% filler', 'Teams randomized live'],
    format='team', checked=ACME_CHK,
    boxes=[dict(k='logo', short='Chrome Logofractor', c='#5aa9ff', full='2026 Topps Chrome Baseball Logofractor Edition (2 boxes)', kind='300-card base, autographs, inserts',
                types='Chrome base with Logofractor parallels, autographs and inserts.'),
           dict(k='black', short='Chrome Black', c='#8a93a0', full='2026 Topps Chrome Black Baseball Hobby (1 box)', kind='200-card base, autographs, inserts',
                types='Dark Chrome base, Chrome Black, Ivory, Paint It and Super Futures autographs, Pitch Black Pairings dual autographs, and Damascus, Depth of Darkness, Home Field and Nocturnal inserts.'),
           dict(k='prizm', short='Prizm', c='#e2545e', full='2026 Panini Prizm Baseball Hobby (1 box)', kind='300-card base, autographs, inserts',
                types='Base with Prizm parallels, autographs, inserts and multi-player cards.'),
           BOX_MUSEUM_B],
    spots=[team_spot(re.sub(r'[^a-z0-9]', '', l.lower()), l, ts) for l, ts in gb1042_spots],
    rules=[['Cards go to the team on the card', ['Acme\'s rules: a card goes to the team listed on the front or back, not the jersey.', 'Retired players go to the team on their card; if that team moved, it goes to the team it became (the Montreal Expos to the Washington Nationals and the St. Louis Browns to the Baltimore Orioles, for example).']],
           ACME_RULES[2]],
    notes=['Cards are listed with the team the checklist gives them.',
           'The Chrome Black checklist comes from Beckett (base set) and Checklist Center (autographs and inserts), because Topps\'s own PDF wasn\'t available. It lists names and teams only.',
           'Six Prizm cards are for players with no MLB team on the checklist (Grady Emerson, Josh Gibson, Kelsie Whitmore, Mo\'ne Davis, NiJaree Canady and Roch Cholowsky). Acme\'s listing doesn\'t say where those go, so they aren\'t in any spot here.',
           ACME_FILLER % '$26.25'],
    sources=[['GB1042 break page (Acme Packs)', acme_url(GB1042_H)], ACME_TERMS,
             _srcx('2026-topps-chrome-baseball-logofractor-edition', 'Topps Chrome Logofractor Baseball'),
             ['Topps Chrome Black Baseball base set (Beckett)', 'https://www.beckett.com/news/2026-topps-chrome-black-baseball-cards/'],
             ['Topps Chrome Black Baseball autographs and inserts (Checklist Center)', 'https://www.checklistcenter.com/2026-topps-chrome-black-baseball-card-checklist/'],
             ['Panini Prizm Baseball checklist (official Panini CSV)', SRC_PANINI],
             _srcx('2026-topps-museum-collection-baseball', 'Topps Museum Collection Baseball')],
)

# GB1043: Multi Product Football (random letter)
GB1043_H = 'gb1043-multi-product-football-random-letters'
gb1043 = dict(
    id='gb1043', title='GB1043 Multi Product Football', kicker='Acme Packs · Random letter · NFL and college',
    url=acme_url(GB1043_H), when=ACME_FRI % ('7:00 pm', '8:00 pm'),
    facts=['4 boxes', '20 letter spots', '$115 per spot, $28.75 for a 25% filler', 'Letters randomized live'],
    format='random', checked=ACME_CHK,
    boxes=[dict(k='best', short='Bowman U Best', c='#3ccf9a', full='2026 Topps Bowman Best Football Hobby (1 box)', kind='Base, autographs, inserts',
                types='Base, autographs, inserts and multi-player cards from the Bowman U Best checklist.'),
           dict(BOX_CHROME_H, full='2026 Topps Chrome Football Hobby (1 box)'),
           dict(k='obsidian', short='Obsidian', c='#8a6be0', full='2026 Panini Obsidian Football FOTL (1 box)', kind='Base, autographs, inserts',
                types='Base, autographs, memorabilia, inserts and multi-player cards from the Obsidian checklist.'),
           dict(k='bowman', short='Bowman Jumbo', c='#f2c14e', full='2026 Topps Bowman Football Jumbo (1 box)', kind='Base, autographs, inserts',
                types='Base with parallels, autographs and inserts from the Bowman Football checklist.')],
    spots=[cc_spot('A', 'A'), cc_spot('B', 'B'), cc_spot('CA-CG', pre=[('CA', 'CG')]), cc_spot('CH-CZ', pre=[('CH', 'CZ')]),
           cc_spot('DA-DL', pre=[('DA', 'DL')]), cc_spot('DM-DZ', pre=[('DM', 'DZ')]), cc_spot('E', 'E'), cc_spot('F / G / H', 'FGH'),
           cc_spot('JA-JAR', pre=[('JA', 'JAR')]), cc_spot('JAS-JM', pre=[('JAS', 'JM')]), cc_spot('JN-JZ', pre=[('JN', 'JZ')]),
           cc_spot('K', 'K'), cc_spot('L', 'L'), cc_spot('M', 'M'), cc_spot('N / O', 'NO'), cc_spot('P / Q', 'PQ'), cc_spot('R', 'R'),
           cc_spot('S', 'S'), cc_spot('T', 'T'), cc_spot('U / V / W / X / Y / Z / I', 'UVWXYZI')],
    rules=[GB_LETTER_FIRST,
           ['How the 20 spots work', ['C, D and J are split on the next letters: CA-CG and CH-CZ, DA-DL and DM-DZ, and J in three parts (JA-JAR, JAS-JM and JN-JZ).',
                                      'Cam Coleman is CA, so CA-CG. CJ Carr is CJ, so CH-CZ. Jared Allen is JAR, so JA-JAR. Jayden Maiava is JAY, so JAS-JM. Josh Hoover is JO, so JN-JZ.',
                                      'F, G and H share a spot, as do N and O, and P and Q. The last spot holds U, V, W, X, Y, Z and I.']],
           GB_LETTER_MULTI],
    notes=['The listing says "2026 Topps Bowman Best Football". Acme calls GB1044 "Bowman U Best", so this guide treats them as the same product and uses the Bowman U Best Football checklist.',
           'FOTL stands for First Off The Line. This guide uses the standard Obsidian Football checklist, so any cards that are only in FOTL boxes may be missing. The Bowman Jumbo box uses the standard Bowman Football checklist the same way.',
           ACME_FILLER % '$28.75'],
    sources=[['GB1043 break page (Acme Packs)', acme_url(GB1043_H)], ACME_TERMS,
             _srcx('2026-bowman-u-best-football', 'Bowman U Best Football'), SRC_CHROME,
             ['Panini Obsidian Football checklist (official Panini CSV)', SRC_PANINI],
             _srcx('2026-bowman-football', 'Bowman Football')],
)

# GB1044: The Best of Bowman (random letter)
GB1044_H = 'gb1044-the-best-of-bowman-random-letters'
gb1044 = dict(
    id='gb1044', title='GB1044 The Best of Bowman', kicker='Acme Packs · Random letter · College football',
    url=acme_url(GB1044_H), when=ACME_FRI % ('8:00 pm', '9:00 pm'),
    facts=['4 boxes', '16 letter spots', '$105 per spot, $26.25 for a 25% filler', 'Letters randomized live'],
    format='random', checked=ACME_CHK,
    boxes=[dict(k='best', short='Bowman U Best', c='#3ccf9a', full='2026 Topps Bowman U Best Football Hobby (4 boxes)', kind='Base, autographs, inserts',
                types='Base, autographs, inserts and multi-player cards from the Bowman U Best checklist.')],
    spots=[cc_spot('A', 'A'), cc_spot('B (BA-BO)', pre=[('BA', 'BO')]), cc_spot('B (BR-BZ)', pre=[('BR', 'BZ')]),
           cc_spot('C (CA-CE)', pre=[('CA', 'CE')]), cc_spot('C (CF-CZ)', pre=[('CF', 'CZ')]),
           cc_spot('D (DA-DE)', pre=[('DA', 'DE')]), cc_spot('D (DF-DZ)', pre=[('DF', 'DZ')]),
           cc_spot('E / F / G / H / I / P', 'EFGHIP'), cc_spot('J (JA-JAR)', pre=[('JA', 'JAR')]), cc_spot('J (JAS-JZ)', pre=[('JAS', 'JZ')]),
           cc_spot('K', 'K'), cc_spot('L', 'L'), cc_spot('M', 'M'), cc_spot('N / O / V / W / Y / Z', 'NOVWYZ'), cc_spot('R / S', 'RS'), cc_spot('T', 'T')],
    rules=[GB_LETTER_FIRST,
           ['How the 16 spots work', ['B, C, D and J are split on the next letters: BA-BO and BR-BZ, CA-CE and CF-CZ, DA-DE and DF-DZ, and JA-JAR and JAS-JZ.',
                                      'No spot lists Q, U or X, and no one in this checklist has a first name that starts with those letters.',
                                      'Bo Jackson is BO, so BA-BO. Bryce Underwood is BR, so BR-BZ. Caden Durham is CA, so CA-CE. CJ Carr is CJ, so CF-CZ. Jared Curtis is JAR, so JA-JAR. Jayden Maiava is JAY, so JAS-JZ.']],
           GB_LETTER_MULTI],
    notes=['Acme calls this product "Bowman U Best" here and "Bowman Best" on GB1043. This guide uses the Bowman U Best Football checklist for both.',
           'Topps notes on its own checklist that it reflects the planned product setup at production time, and that actual contents and odds may vary.',
           ACME_FILLER % '$26.25'],
    sources=[['GB1044 break page (Acme Packs)', acme_url(GB1044_H)], ACME_TERMS, _srcx('2026-bowman-u-best-football', 'Bowman U Best Football')],
)

# GB1045: Leaf Optichrome Football Fire Sale (random letter)
GB1045_H = 'gb1045-leaf-optichrome-football-fire-sale-random-letters'
gb1045 = dict(
    id='gb1045', title='GB1045 Leaf Optichrome Football Fire Sale', kicker='Acme Packs · Random letter · Football',
    url=acme_url(GB1045_H), when=ACME_FRI % ('9:00 pm', '10:00 pm'),
    facts=['8 boxes', '12 letter spots (the listing says 16)', '$175 per spot', 'Letters randomized live'],
    format='random', checked=ACME_CHK,
    boxes=[dict(k='lf25', short='2025 Optichrome', c='#5aa9ff', full='2025 Leaf Optichrome Football Jumbo (4 boxes)', kind='Base, autographs, inserts, memorabilia',
                types='Optichrome base, many autograph sets (including multi-signed cards and a basketball autograph set), inserts and Battle Worn memorabilia.'),
           dict(k='lf26', short='2026 Optichrome', c='#e2545e', full='2026 Leaf Optichrome Football (1 Jumbo, 3 Hobby)', kind='Base, autographs, inserts',
                types='Optichrome base, autographs, inserts and multi-player cards.')],
    spots=[cc_spot('A', 'A'), cc_spot('B', 'B'), cc_spot('C', 'C'), cc_spot('D', 'D'), cc_spot('E / F / I', 'EFI'), cc_spot('G / H / O', 'GHO'),
           cc_spot('J', 'J'), cc_spot('K / L', 'KL'), cc_spot('M', 'M'), cc_spot('N / P / Q', 'NPQ'), cc_spot('R / S', 'RS'),
           cc_spot('T / U / V / W / X / Y / Z', 'TUVWXYZ')],
    rules=[GB_LETTER_FIRST,
           ['How the spots work', ['The spots are the 12 letter groups on Acme\'s listing. Together they cover every letter from A to Z.']],
           GB_LETTER_MULTI],
    notes=['Acme\'s listing says 16 spots, but the board on the listing shows 12 letter groups. This guide shows the 12 groups. Check Acme\'s listing for the final board.',
           'Leaf cards don\'t carry team names, so there is no team view for this set.'],
    sources=[['GB1045 break page (Acme Packs)', acme_url(GB1045_H)], ACME_TERMS,
             ['2025 Leaf Optichrome Football checklist (Checklist Center)', 'https://www.checklistcenter.com/2025-leaf-optichrome-football-card-checklist/'],
             ['2026 Leaf Optichrome Football checklist (Leaf Trading Cards)', 'https://www.leaftradingcards.com/products/2026-leaf-optichrome-football']],
)

ACME_CL_NOTE = ('Checklists show what the maker planned for a product when it was made. The boxes opened on the stream can differ, for example a '
                'FOTL (First Off The Line), Jumbo or other version, or a late change by the maker, so a card that isn\'t listed here can still turn up. '
                'It goes to whichever spot its name or team matches, under Acme\'s rules.')
for _c in (gb1041, gb1042, gb1043, gb1044, gb1045): _c['notes'].append(ACME_CL_NOTE)

# ---------------- Nov 27 check: Colfax CC876 to CC879 (Sunday Nov 29) and RGL #6145 to #6147 (Saturday Nov 28) ----------------
SAT = 'Saturday, November 28, 2026'
CC_SUN = 'Sunday, November 29, 2026, 5:00 pm Central (6:00 pm Eastern)'
def colfax_url(h): return 'https://colfaxcc.com/products/' + h
CC_CHK = 'When checked on November 27, 2026, around 1:15 pm Eastern, the listing\'s tags showed %d break spots and %d filler spots, but the description lists %d spots, so the counts don\'t match; ask Colfax.'
CC_FILLER = 'Filler entries are sold too (%s for a 25%% chance at a spot); see Colfax\'s listing for how fillers work.'
CC_MULTI = cc872['rules'][2]
CC_TEAM_RULE = ['Cards go to the team on the card', ['Colfax\'s rules: a card goes to the team listed on the front or back, not the jersey.',
                'Retired players go to the team listed on their card. This guide files old franchises with today\'s team (Expos to the Nationals, old Cleveland to the Guardians, Washington Senators to the Twins and Browns to the Orioles).']]
def cc_az():
    """Straight A to Z, one spot per letter, plus a number spot. Used while a random-letter break's real setup isn't known (Daniel, Nov 27, 2026)."""
    return [cc_spot('T (No The)', 'T') if c == 'T' else cc_spot(c, c) for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'] + [cc_spot('# (numbers)', '#')]
CC_LETTER_THE = 'A leading "The" doesn\'t count (Colfax\'s listing says "T (No The)"), so The Thing is T and The Maker is M.'

# CC876 Cosmic & Museum X (Random Team)
CC876_H = 'cc876-cosmic-museum-x-random-team'
_cc876_teams = ['Angels', 'Astros', 'Athletics', 'Blue Jays', 'Braves', 'Brewers', 'Cardinals', 'Cubs', None, 'Dodgers', 'Giants', 'Guardians', 'Mariners', None, 'Mets',
                'Nationals', 'Orioles', None, 'Phillies', 'Pirates', 'Rays', 'Red Sox', 'Reds', 'Royals', 'Tigers', 'White Sox', 'Yankees']
_cc876_pairs = iter([("D'Backs / Rockies", ['Diamondbacks', 'Rockies']), ('Marlins / Twins', ['Marlins', 'Twins']), ('Padres / Rangers', ['Padres', 'Rangers'])])
def _cc876_spot(t):
    if t is None:
        lab, ts = next(_cc876_pairs); return team_spot(tid(lab), lab, ts)
    return team_spot(tid(t), t, [t])
cc876 = dict(
    id='cc876', title='CC876 Cosmic & Museum X (Random Team)', kicker='Colfax Collectibles · Random team · MLB',
    url=colfax_url(CC876_H), when=CC_SUN,
    facts=['4 boxes', '27 team spots', '$100 per spot, $25 filler', 'Teams randomized live'],
    format='team', checked=CC_CHK % (21, 24, 27),
    boxes=[dict(k='ginter', short='Allen & Ginter X', c='#f2c14e', full='2026 Topps Allen & Ginter X Baseball Hobby (1 box)', kind='Base, autographs, inserts, multi-player cards',
                types='Base cards, autographs, inserts and multi-player cards from the Allen & Ginter checklist.'),
           dict(next(b for b in gb1042['boxes'] if b['k'] == 'logo'), full='2026 Topps Chrome Baseball Logofractor Edition (1 box)'),
           dict(next(b for b in rgl6138['boxes'] if b['k'] == 'cosmic'), full='2026 Topps Cosmic Chrome Baseball Hobby (1 box)'),
           dict(next(b for b in gb1042['boxes'] if b['k'] == 'museum'), full='2026 Topps Museum Collection Baseball Hobby (1 box)')],
    spots=[_cc876_spot(t) for t in _cc876_teams],
    rules=[['How the 27 spots work', ['Colfax\'s listing sets 27 spots: 24 single teams and three pairs (D\'Backs and Rockies, Marlins and Twins, Padres and Rangers). Teams are randomized live on stream.']],
           CC_TEAM_RULE, CC_MULTI],
    notes=['The listing says "Allen & Ginter X". This guide uses the 2026 Topps Allen & Ginter Baseball checklist for that box.',
           'The listing says "2026 Topps Chrome Logofractor" and "2026 Topps Cosmic". This guide uses the Chrome Baseball Logofractor Edition and Cosmic Chrome Baseball checklists.',
           'Cards are listed with the team the official checklist gives them.',
           CC_FILLER % '$25'],
    sources=[['CC876 break page (Colfax Collectibles)', colfax_url(CC876_H)],
             _src('2026-topps-allen-and-ginter-baseball', 'Topps Allen & Ginter Baseball'), _src('2026-topps-chrome-baseball-logofractor-edition', 'Topps Chrome Baseball Logofractor Edition'),
             _src('2026-topps-cosmic-chrome-baseball', 'Topps Cosmic Chrome Baseball'), _src('2026-topps-museum-collection-baseball', 'Topps Museum Collection Baseball')],
)

# CC879 Finest Neon Mint (Random Letter)
CC879_H = 'cc879-finest-neon-mint-random-letter'
BOX_NEON = dict(k='neon', short='Marvel Neon', c='#8a6be0', full='2026 Topps Marvel Neon Hobby (1 box)', kind='Marvel characters, neon-style parallels, inserts',
                types='Base with neon parallels, inserts and autographs.')
BOX_MINT_M = dict(k='mintm', short='Marvel Mint', c='#3ccf9a', full='2026 Topps Marvel Mint (1 box)', kind='Marvel characters, base, autographs, inserts',
                  types='Base, autographs and inserts from the Marvel Mint checklist.')
BOX_FINEST_FF = dict(k='finestff', short='Finest Fantastic Four', c='#e2545e', full='2026 Topps Finest Fantastic Four Hobby (1 box)', kind='Base, autographs, inserts, multi-character cards',
                     types='Finest base and Refractor parallels, autographs, inserts and multi-character cards from the Fantastic Four checklist.')
cc879 = dict(
    id='cc879', title='CC879 Finest Neon Mint (Random Letter)', kicker='Colfax Collectibles · Random letter · Marvel',
    url=colfax_url(CC879_H), when=CC_SUN,
    facts=['4 boxes', 'Letters A to Z for now', '$105 per spot, $26.25 filler', 'Letters randomized live'],
    format='random', checked=CC_CHK % (14, 16, 18) + ' Until Colfax confirms the setup, this guide shows each letter on its own, A to Z.',
    boxes=[dict(BOX_NEON, full='2026 Topps Marvel Neon Hobby (2 boxes)'), BOX_FINEST_FF, BOX_MINT_M],
    spots=cc_az(),
    rules=[['How the spots work', ['Colfax\'s listing text lists 18 spots, but its tags say 14 break spots and 16 filler spots, so the real setup isn\'t clear. Until Colfax confirms it, this guide shows each letter on its own, A to Z. Letters are randomized live on stream.',
                                    'The listing text groups them like this: A, B, C, D, E / F / U, G, H, I, J / N, K / L, M, O / Q / Y, P / X / Z, R, S, T (No The), V and W. This guide will switch to the real groups once they\'re confirmed.']],
           ['First letter of the name on the card', ['The spot goes by the first letter of the name printed on the card: Spider-Man is S, Captain America is C. For a person, that\'s the first name.', CC_LETTER_THE,
                                                     'Colfax\'s listing doesn\'t say how it handles characters, so check with Colfax.']],
           ['Cards with more than one character', ['Each character on a dual or multi-character card is listed under their own letter.', CC_MULTI[1][0]]]],
    notes=['The Finest Fantastic Four decade cards (1960s, 1970s and so on) start with a number, and the listing has no letter for them. They show under a number spot here; ask Colfax who gets them.',
           'Lists come from the official Topps checklists.', CC_FILLER % '$26.25'],
    sources=[['CC879 break page (Colfax Collectibles)', colfax_url(CC879_H)], _src('2026-topps-neon-marvel', 'Topps Marvel Neon'),
             _src('2026-topps-finest-fantastic-four', 'Topps Finest Fantastic Four'), _src('2026-topps-mint-marvel', 'Topps Marvel Mint')],
)

# CC877 Amy's Birthday Break (Random Letter)
CC877_H = 'cc877-amys-birthday-break-random-letter'
cc877 = dict(
    id='cc877', title="CC877 Amy's Birthday Break (Random Letter)", kicker='Colfax Collectibles · Random letter · Multi-theme',
    url=colfax_url(CC877_H), when=CC_SUN,
    facts=['6 boxes (4 listed here)', 'Letters A to Z for now', '$105 per spot, $26.25 filler', 'Letters randomized live'],
    format='random', checked=CC_CHK % (15, 20, 20) + ' Until Colfax confirms the setup, this guide shows each letter on its own, A to Z.',
    boxes=[dict(BOX_FINEST_FF), 
           dict(k='pop', short='Leaf Pop Century', c='#f2c14e', full='2026 Leaf Pop Century (1 box)', kind='Autographs and multi-signature cards',
                types='Autographs and multi-signature cards from the Leaf Pop Century checklist.'),
           dict(BOX_NEON),
           dict(k='deadpool', short='Chrome Deadpool', c='#e2545e', full='2025 Topps Chrome Deadpool Hobby (1 box)', kind='Base, autographs, inserts, multi-character cards',
                types='Chrome base and Refractor parallels, autographs, inserts and multi-character cards from the Deadpool checklist.')],
    spots=cc_az(),
    rules=[['How the spots work', ['Colfax\'s listing text lists 20 spots, but its tags say 15 break spots and 20 filler spots, so the real setup isn\'t clear. Until Colfax confirms it, this guide shows each letter on its own, A to Z. Letters are randomized live on stream.',
                                    'The listing text groups them like this: A, B, C, D, E, F / Z, G, H / Y, I, J, K, L / O, M, N, P, Q / R / X, S split as SA-SH and SI-SY, T (No The), and U / V / W. This guide will switch to the real groups once they\'re confirmed.']],
           ['First letter of the name on the card', ['The spot goes by the first letter of the name printed on the card. For a person, that\'s the first name; for a character, the name as printed.', CC_LETTER_THE,
                                                     'Colfax\'s listing doesn\'t say whether it means first or last name for people, so check with Colfax.']],
           ['Cards with more than one name', ['Each person or character on a dual or multi-person card is listed under their own letter.', CC_MULTI[1][0]]]],
    notes=['Two boxes aren\'t in this guide yet because we don\'t have their checklists: 2025 Kakawow DC Aura and 2026 Card Fun Disney Chronoz. Check those cards with Colfax.',
           'The Finest Fantastic Four decade cards (1960s, 1970s and so on) and 42 Dugg start with a number, and the listing has no letter for them. They show under a number spot here; ask Colfax who gets them.',
           'Lists come from the official Topps checklists and the Leaf checklist.', CC_FILLER % '$26.25'],
    sources=[['CC877 break page (Colfax Collectibles)', colfax_url(CC877_H)], _src('2026-topps-finest-fantastic-four', 'Topps Finest Fantastic Four'),
             _src('2026-topps-neon-marvel', 'Topps Marvel Neon'), _src('2025-topps-chrome-deadpool', 'Topps Chrome Deadpool'),
             ['2026 Leaf Pop Century checklist (Leaf Trading Cards)', 'https://www.leaftradingcards.com/products/2026-leaf-pop-century']],
)

# CC878 2 Year Chrome PYL (WWE)
CC878_H = 'cc878-2-year-chrome-pyl-pick-your-letter'
_cc878_avail = [1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0]
_cc878_base = [('ac-m', 'A & C', 'AC', 'M', 145), ('a-w', 'A', 'A', 'F', 115), ('b-m', 'B', 'B', 'M', 90), ('b-w', 'B', 'B', 'F', 105), ('c-w', 'C', 'C', 'F', 70),
               ('d', 'D', 'D', None, 100), ('ef', 'E & F', 'EF', None, 70), ('g', 'G', 'G', None, 100), ('h', 'H', 'H', None, 35), ('i', 'I', 'I', None, 55),
               ('j-m', 'J', 'J', 'M', 185), ('j-w', 'J', 'J', 'F', 55), ('k-m', 'K', 'K', 'M', 70), ('k-w', 'K', 'K', 'F', 115), ('l', 'L', 'L', None, 155),
               ('m', 'M', 'M', None, 45), ('n', 'N', 'N', None, 35), ('o', 'O', 'O', None, 60), ('pq', 'P & Q', 'PQ', None, 50), ('r-m', 'R', 'R', 'M', 200),
               ('r-w', 'R', 'R', 'F', 125), ('s-m', 'S', 'S', 'M', 120), ('s-w', 'S', 'S', 'F', 160), ('t-m', 'T', 'T', 'M', 70), ('t-w', 'T', 'T', 'F', 140),
               ('uvw', 'U-V-W', 'UVW', None, 90), ('xyz', 'X-Y-Z-123', 'XYZ#', None, 45)]
cc878_spots = [wwe_spot(i, lab, ls, g, pr, bool(a)) for (i, lab, ls, g, pr), a in zip(_cc878_base, _cc878_avail)]
CC878_WOMEN = lib_women('2025-topps-chrome-wwe')
def cc878_gender(n):
    return 'F' if (n in CC878_WOMEN or key_of(n) in CC878_WOMEN or rgl_wwe_gender(n) == 'F') else 'M'
cc878 = dict(
    id='cc878', title='CC878 2 Year Chrome PYL', kicker='Colfax Collectibles · Pick your letter · WWE',
    url=colfax_url(CC878_H), when=CC_SUN,
    facts=['4 boxes', '27 letter spots', '$35 to $200 per spot', '22 open, 5 sold as of 1:15 pm Eastern'],
    format='pyl', checked='Availability checked against Colfax\'s store data on November 27, 2026, around 1:15 pm Eastern. Spots sell fast, so check the live page before you buy.',
    boxes=[dict(WWE_BOX['chrome'], k='chrome25', short='2025 Chrome', c='#5aa9ff', full='2025 Topps Chrome WWE (1 Hobby, 1 Chrome Delight)', kind='200-card base, 100 image variations, autographs, inserts',
                types='Base, the Image Variations set, autographs (Gold Refractor base autographs plus Red Brand, Blue Brand and NXT sets, Hall of Fame, Legendary, Main Event and more) and inserts like Helix, Mania, Persona and Slammy.'),
           dict(WWE_BOX['chrome'], full='2026 Topps Chrome WWE (1 Hobby, 1 Chrome Delight)')],
    spots=cc878_spots, rules=WWE_RULES,
    notes=['The break has four boxes: a Hobby and a Chrome Delight box from 2025 Topps Chrome WWE and from 2026 Topps Chrome WWE. Each year\'s pair is shown as one box here.',
           'Chrome Delight is a Topps Chrome WWE box, so it uses the same checklist as the Hobby box.',
           'The 2025 Chrome WWE list comes from Checklist Center, not from a Topps file. Its Image Variations set (cards 201 to 300) reuses the base names, so it adds no new names.',
           'Autograph and insert lists come from the published checklists. A name only in an autograph set is much harder to pull than a base card.'],
    sources=[['CC878 break page (Colfax Collectibles)', colfax_url(CC878_H)],
             ['2025 Topps Chrome WWE checklist (Checklist Center)', 'https://www.checklistcenter.com/2025-topps-chrome-wwe-wrestling-card-checklist/'],
             ['2026 Topps Chrome WWE checklist (Checklist Center)', 'https://www.checklistcenter.com/2026-topps-chrome-wwe-wrestling-card-checklist/']],
)

# RGL #6145 Chrome & Midnight PYT #2 (Raiders random to all)
rgl6145_v = [('Arizona Cardinals', 260, 1), ('Atlanta Falcons', 70, 1), ('Baltimore Ravens', 105, 1), ('Buffalo Bills', 235, 1), ('Carolina Panthers', 90, 1),
             ('Chicago Bears', 215, 1), ('Cincinnati Bengals', 145, 1), ('Cleveland Browns', 170, 1), ('Dallas Cowboys', 140, 1), ('Denver Broncos', 110, 1),
             ('Detroit Lions', 110, 1), ('Green Bay Packers', 65, 1), ('Houston Texans', 45, 0), ('Indianapolis Colts', 70, 1), ('Jacksonville Jaguars', 85, 1),
             ('Kansas City Chiefs', 375, 1), ('Las Vegas Raiders', 0, 0), ('Los Angeles Chargers', 80, 1), ('Los Angeles Rams', 255, 0), ('Miami Dolphins', 65, 0),
             ('Minnesota Vikings', 85, 0), ('New England Patriots', 360, 1), ('New Orleans Saints', 145, 1), ('New York Giants', 175, 1), ('New York Jets', 105, 1),
             ('Philadelphia Eagles', 130, 1), ('Pittsburgh Steelers', 100, 1), ('San Francisco 49ers', 170, 0), ('Seattle Seahawks', 195, 1),
             ('Tampa Bay Buccaneers', 160, 1), ('Tennessee Titans', 155, 1), ('Washington Commanders', 95, 1)]
RGL6145_H = 'rgl-6145-chrome-midnight-pyt-11-28-26-raiders-random'
rgl6145 = dict(
    id='rgl6145', title='RGL #6145 Chrome & Midnight PYT', kicker='Run Good Life · Pick your team · NFL',
    url=rgl_url(RGL6145_H), when=_when(SAT, '6:15 pm', '9:15 pm'),
    facts=['5 boxes', '32 team spots', '$45 to $375 per team', 'Raiders randomized to all'],
    live=dict(shop='rgl', handle=RGL6145_H),
    format='pyt', checked='Availability checked against Run Good Life\'s store data on November 27, 2026, around 1:15 pm Eastern: 26 of 31 teams open.',
    boxes=[dict(b) for b in rgl6130['boxes']],
    spots=team_spots_from_variants(rgl6145_v, lambda f: f.split(' ')[-1], 'Las Vegas Raiders'),
    rules=list(rgl6130['rules']),
    notes=list(rgl6130['notes']) + ['Same boxes as the Chrome & Midnight PYT on November 25 (#6130): 2 Chrome Hobby, 1 Chrome Jumbo and 2 Midnight.',
           'RGL\'s store lists the Cardinals at $260, while the variant title says $295. Check the price at checkout.'],
    sources=[['RGL #6145 break page (Run Good Life)', rgl_url(RGL6145_H)]] + list(rgl6130['sources'][1:]),
)

# RGL #6146 Half Case Gilded Collection (Random Team)
RGL6146_H = 'rgl-6146-half-case-gilded-collection-random-team-11-28-26'
rgl6146 = dict(
    id='rgl6146', title='RGL #6146 Half Case Gilded Collection (Random Team)', kicker='Run Good Life · Random team · MLB',
    url=rgl_url(RGL6146_H), when=_when(SAT, '7:00 pm', '10:00 pm'),
    facts=['5 boxes', '20 spots for 30 teams', '$208 per spot, fillers $52', 'Teams randomized live'],
    format='team', checked='Spots were still for sale when checked on November 27, 2026, around 1:15 pm Eastern.',
    boxes=[dict(next(b for b in rgl6138['boxes'] if b['k'] == 'cosmic'), full='2026 Topps Cosmic Chrome Baseball Hobby (1 box)'),
           dict(next(b for b in rgl6138['boxes'] if b['k'] == 'finest'), full='2026 Topps Finest Baseball (1 Mega box)'),
           dict(next(b for b in rgl6138['boxes'] if b['k'] == 'gilded'), full='2026 Topps Gilded Collection Baseball Hobby (2 boxes)'),
           dict(next(b for b in rgl6129['boxes'] if b['k'] == 'chrome'), full='2026 Topps Chrome Baseball Jumbo (1 box)')],
    spots=list(MLB_RANDOM_SPOTS),
    rules=[RGL_LIVE_GROUPS, RGL_TEAM_RULE, RGL_MULTI],
    notes=['Cards are listed with the team the official checklist gives them. Expos cards are filed with the Nationals, old Cleveland cards with the Guardians and Washington Senators cards with the Twins.',
           'The Chrome box is a Jumbo, and this guide uses the standard Chrome Baseball checklist for it, so any Jumbo-only cards may be missing.',
           'Filler entries are sold too ($52 each); see RGL\'s listing for how fillers work.'],
    sources=[['RGL #6146 break page (Run Good Life)', rgl_url(RGL6146_H)], _src('2026-topps-cosmic-chrome-baseball', 'Topps Cosmic Chrome Baseball'),
             rgl6129['sources'][5], rgl6129['sources'][3], rgl6129['sources'][1]],
)

# RGL #6147 Joy of Stadium Club (Random Team)
RGL6147_H = 'rgl-6147-joy-of-stadium-club-random-team-11-28-26'
rgl6147 = dict(
    id='rgl6147', title='RGL #6147 Joy of Stadium Club (Random Team)', kicker='Run Good Life · Random team · NBA',
    url=rgl_url(RGL6147_H), when=_when(SAT, '8:00 pm', '11:00 pm'),
    facts=['4 boxes', '20 spots for 30 teams', '$162 per spot, fillers $40.50', 'Teams randomized live'],
    format='team', checked='Spots were still for sale when checked on November 27, 2026, around 1:15 pm Eastern.',
    boxes=[dict(next(b for b in rgl6131['boxes'] if b['k'] == 'sc')),
           dict(next(b for b in rgl6131['boxes'] if b['k'] == 'joy')),
           dict(next(b for b in rgl6131['boxes'] if b['k'] == 'flag'), full='2026-27 Topps Flagship Basketball Jumbo (1 box)')],
    spots=[team_spot(tid(t), t, [t]) for t in NBA_TEAMS],
    rules=[RGL_LIVE_GROUPS, RGL_TEAM_RULE, RGL_MULTI],
    notes=['Same Stadium Club, Joy of Basketball and Flagship boxes as the Joy of Basketball breaks on November 25, with a Flagship Jumbo this time.',
           'The Flagship box is a Jumbo, and this guide uses the standard Flagship Basketball checklist for it, so any Jumbo-only cards may be missing.',
           'Seattle SuperSonics legends are filed with the Thunder here, since that\'s the same franchise today.',
           'Filler entries are sold too ($40.50 each); see RGL\'s listing for how fillers work.'],
    sources=[['RGL #6147 break page (Run Good Life)', rgl_url(RGL6147_H)]] + list(rgl6131['sources'][1:]),
)


# RGL #6148 World Cup Treasures (Random Team), soccer by national team (Daniel sent the Prizm World Cup CSV; the other two
# checklists were copied from Diamond Cards Online, Nov 27, 2026)
RGL6148_H = 'rgl-6148-world-cup-treasures-random-team-11-28-26'
def rgl6148_product(pid):
    """a soccer checklist by national team; Prizm World Cup's team logo cards ("Argentina | Team Logo") go to that team"""
    out = dict(base={}, other={})
    sec = None
    for line in open(os.path.join(LIB, pid + '.txt'), encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'): continue
        if line.startswith('['): sec = line.strip('[]'); continue
        for part in line.split(' / '):
            if ' | ' not in part: continue
            n, team = [x.strip() for x in part.rsplit(' | ', 1)]
            if team == 'Team Logo': n, team = n + ' team logo', n
            bucket = out['base'] if sec == 'base' else out['other']
            if n not in bucket.setdefault(team, []): bucket[team].append(n)
    return out
WC_TEAMS = ['Algeria', 'Argentina', 'Australia', 'Austria', 'Belgium', 'Bosnia-Herzegovina', 'Brazil', 'Canada', 'Cape Verde', 'Colombia', 'Croatia',
            'Curacao', 'Czechia', 'DR Congo', 'Ecuador', 'Egypt', 'England', 'France', 'Germany', 'Ghana', 'Haiti', 'IR Iran', 'Iraq', 'Ivory Coast', 'Japan',
            'Jordan', 'Korea Republic', 'Mexico', 'Morocco', 'Netherlands', 'New Zealand', 'Norway', 'Panama', 'Paraguay', 'Portugal', 'Qatar',
            'Saudi Arabia', 'Scotland', 'Senegal', 'South Africa', 'Spain', 'Sweden', 'Switzerland', 'Tunisia', 'Turkey', 'United States', 'Uruguay', 'Uzbekistan']
RTWC_ONLY = ['Denmark', 'Italy', 'Nigeria', 'Poland', 'Serbia', 'Slovakia', 'Slovenia', 'Wales']   # in the Road to World Cup boxes, not in the 48-team field
rgl6148 = dict(
    id='rgl6148', title='RGL #6148 World Cup Treasures (Random Team)', kicker='Run Good Life · Random team · Soccer',
    url=rgl_url(RGL6148_H), when=_when(SAT, '8:45 pm', '11:45 pm'),
    facts=['4 boxes', '19 spots for 56 teams', '$186 per spot, fillers $18.60', 'Teams randomized live'],
    format='team', checked='Spots were still for sale when checked on November 27, 2026, around 1:15 pm Eastern.',
    boxes=[dict(k='pwc', short='Prizm World Cup', c='#2e86de', full='2026 Panini Prizm FIFA World Cup Hobby (1 box)', kind='500-card base, autographs, inserts, multi-player cards',
                types='Base for all 48 World Cup teams with Prizm parallels, autographs, inserts and multi-player cards.'),
           dict(k='nt', short='National Treasures', c='#b7950b', full='2025-26 Panini National Treasures Road to FIFA World Cup 2026 (1 box)', kind='150-card base, autographs, memorabilia',
                types='Base numbered to 99 or less, autographs, memorabilia and autograph memorabilia cards, dual and triple booklets.'),
           dict(k='sel', short='Select Road to World Cup', c='#c0392b', full='2025-26 Panini Select Road to FIFA World Cup 2026 Hobby (2 boxes)', kind='Tiered base, autographs, memorabilia, inserts',
                types='Terrace, Mezzanine and Field Level base with parallels, autographs, memorabilia and inserts.')],
    spots=[team_spot(tid(t), t, [t]) for t in sorted(WC_TEAMS + RTWC_ONLY)],
    rules=[['How RGL groups the spots', ['RGL sells 19 spots, and these boxes have 56 national teams, so teams are grouped together, and the groups are set live on stream. They aren\'t posted on the listing.',
                                         'This guide lists every team on its own, so once you know your teams, look each one up here.']],
           ['Cards go to the national team on the card', ['This guide files each card under the national team the checklist gives it. Retired legends count for the team on their card.',
                                                           'RGL\'s Group Break Rules page has the full house rules, so check there if a card could go either way.']],
           RGL_MULTI],
    notes=['Eight teams in the two Road to World Cup boxes aren\'t in the 48-team World Cup: Denmark, Italy, Nigeria, Poland, Serbia, Slovakia, Slovenia and Wales. The listing doesn\'t say how RGL handles them, so they\'re listed here as their own teams. Ask RGL where those cards go.',
           'Prizm World Cup has a team logo card for each country; those are listed under that team.',
           'The checklists call Wales "Cymru"; it\'s listed as Wales here.',
           'The Prizm World Cup list comes from Panini\'s official checklist. The National Treasures and Select lists were copied from Diamond Cards Online\'s checklist pages, not Panini\'s own files, so a card or two could be off.',
           'Filler entries are sold too ($18.60 each); see RGL\'s listing for how fillers work.'],
    sources=[['RGL #6148 break page (Run Good Life)', rgl_url(RGL6148_H)], ['2026 Panini Prizm FIFA World Cup checklist (official Panini CSV)', SRC_PANINI],
             ['2025-26 National Treasures Road to FIFA World Cup checklist (Diamond Cards Online)', 'https://www.diamondcardsonline.com/blog/2025-26-panini-national-treasures-road-to-fifa-world-cup-2026-soccer-cards-checklist/'],
             ['2025-26 Select Road to FIFA World Cup checklist (Diamond Cards Online)', 'https://www.diamondcardsonline.com/blog/2025-26-panini-select-road-to-fifa-world-cup-2026-soccer-cards-checklist/']],
)

# RGL #6144 Survivor Series Multi-Year PYL-W (pick your wrestler or letter, first name)
RGL6144_H = 'rgl-6144-survivor-series-multi-year-pyl-w-pick-your-wrestler-letter-first-name-11-28-26'
# store variant title | price | open on Nov 27, 2026, 1:15 pm Eastern
_rgl6144_v = """A (all others)|155|1
Alexa Bliss|70|0
B (all others)|210|1
Bayley|70|1
Becky Lynch|90|1
Bianca Belair|90|1
Bray Wyatt / The Fiend|135|1
Bret "Hit Man" Hart|95|1
Brock Lesnar|80|1
Bron Breakker|125|1
C (all others)|145|0
Charlotte Flair|85|0
CM Punk|185|1
Cody Rhodes|205|1
D (all others)|125|1
Dominik Mysterio|85|1
Drew McIntyre|65|1
E / F (all others)|135|1
G (all others)|70|0
Gunther|115|0
H (all others)|30|0
Hulk Hogan|150|0
I (all others)|45|0
Iyo Sky|85|0
J (all others)|105|0
Jey & Jimmie Uso|100|1
John Cena|195|1
K (all others)|105|1
Kevin Owens|55|1
L (all others)|95|1
LA Knight|125|1
Liv Morgan|130|0
M (all others)|85|0
Mick Foley (all)|70|0
N (all others)|35|1
O (all others)|20|0
P / Q (all others)|45|1
R (all others)|165|1
Randy Orton|110|0
Rey Mysterio|80|0
Rhea Ripley|180|0
Roman Reigns|205|1
Rowdy Roddy Piper|45|1
Roxanne Perez|65|0
S (all others)|175|0
Sami Zayn|50|1
Seth "Freakin" Rollins|90|0
Shawn Michaels (HBK)|95|1
Sol Ruca|105|0
Stephanie Vaquer|105|0
Stone Cold Steve Austin|215|0
T (all others)|100|1
The Rock|240|1
Tiffany Stratton|145|0
Triple H|95|0
Trish Stratus|60|0
U / V / W (all others)|70|1
Ultimate Warrior|65|1
Undertaker|165|1
X / Y / Z (all others)|30|0""".split('\n')
# who a named spot covers (matched on the name without nicknames in quotes); the rest is just the one wrestler
_rgl6144_who = {'Bray Wyatt / The Fiend': ['Bray Wyatt', 'The Fiend'], 'Jey & Jimmie Uso': ['Jey Uso', 'Jimmy Uso', 'Jimmie Uso'],
                'Mick Foley (all)': ['Mick Foley', 'Mankind', 'Cactus Jack', 'Dude Love'], 'Hulk Hogan': ['Hulk Hogan', 'Hollywood Hogan'],
                'Bret "Hit Man" Hart': ['Bret Hart'], 'Rowdy Roddy Piper': ['Roddy Piper'], 'Stone Cold Steve Austin': ['Steve Austin'],
                'Seth "Freakin" Rollins': ['Seth Rollins'], 'Shawn Michaels (HBK)': ['Shawn Michaels']}
def _rgl6144_spots():
    out = []
    for line in _rgl6144_v:
        t, pr, op = line.split('|')
        if t.endswith('(all others)'):
            lab = t
            sp = wwe_spot(tid(t.replace(' (all others)', '')), lab, ''.join(c for c in t.replace('(all others)', '') if c.isalpha()) + ('#' if t.startswith('X / Y / Z') else ''), None, int(pr), op == '1')
        else:
            sp = dict(wwe_spot(tid(t), t, '', None, int(pr), op == '1'), who=_rgl6144_who.get(t, [t]))
        out.append(sp)
    return out
rgl6144_spots = _rgl6144_spots()
assert len(rgl6144_spots) == 60 and len({s['id'] for s in rgl6144_spots}) == 60
rgl6144 = dict(
    id='rgl6144', title='RGL #6144 Survivor Series Multi-Year PYL-W', kicker='Run Good Life · Pick your wrestler or letter · WWE',
    url=rgl_url(RGL6144_H), when=_when(SAT, '5:00 pm', '8:00 pm'),
    facts=['11 boxes (9 listed here)', '60 spots: 40 wrestlers, 20 letter groups', '$20 to $240 per spot', 'First name, no "The"'],
    live=dict(shop='rgl', handle=RGL6144_H),
    format='pyl', checked='Availability checked against Run Good Life\'s store data on November 27, 2026, around 1:15 pm Eastern: %d of 60 spots open.' % sum(1 for s in rgl6144_spots if s['status'] == 'open'),
    boxes=[dict(next(b for b in rgl6128['boxes'] if b['k'] == 'finest'), full='2025 Topps Finest WWE Hobby (1 box)'),
           dict(WWE_BOX['exalted'], full='2025 Topps Exalted WWE (1 box)'),
           dict(WWE_BOX['sapphire'], full='2026 Topps Chrome WWE Sapphire (1 box)'),
           dict(WWE_BOX['sc'], full='2026 Topps Stadium Club WWE Hobby (1 box)'),
           dict(WWE_BOX['chrome'], full='2026 Topps Chrome WWE Delight (1 box)', types='Base and Refractor parallels, inserts like Signalz, Gamut and Helix, Garbage Pail Kids cards, autographs.'),
           dict(k='select22', short='Select 2022', c='#c0392b', full='2022 Panini Select WWE Hobby (1 box)', kind='Tiered base, autographs, memorabilia, inserts', types='Concourse, Premier and Ringside base with Prizm parallels, autographs, memorabilia and inserts.'),
           dict(k='prizm23', short='Prizm 2023', c='#8e44ad', full='2023 Panini Prizm WWE Hobby and Lucky Envelope (2 boxes)', kind='Base, autographs, inserts, multi-wrestler cards', types='Base with Prizm parallels (Lucky Envelope boxes have their own Prizm parallels), autographs, inserts and dual cards. Both boxes use the same checklist.'),
           dict(k='photo24', short='PhotoGenic 2024', c='#16a085', full='2024 Panini PhotoGenic WWE Hobby (1 box)', kind='Base, autographs, inserts, multi-wrestler cards', types='Base with parallels, autographs, inserts and multi-wrestler cards.')],
    spots=rgl6144_spots,
    rules=[['Pick a wrestler or a letter', ['RGL sells 40 popular wrestlers on their own and 20 "all others" letter spots for everyone else. Buy a wrestler and you get only that wrestler\'s cards. Buy a letter and you get every card for that first letter except the wrestlers sold on their own.',
                                          'It goes by first name, and a leading "The" doesn\'t count, so The Miz is M. The Rock is sold on his own.']],
           WWE_RULES[1],
           ['Garbage Pail Kids cards go to the wrestler', ['RGL\'s rule: every Garbage Pail Kids card from 2026 Topps Chrome WWE goes to the wrestler\'s spot, not the name on the card. "Potty Mouth Punk" goes to CM Punk, who has his own spot. This guide files all of them that way.']],
           RGL_MULTI],
    notes=['Two of the eleven boxes aren\'t in this guide yet because we don\'t have their checklists: 2021 Topps Finest and 2024 Select Hobby. Check those cards with RGL.',
           'Panini\'s checklists put some nicknames in front of the name, like "The American Nightmare" Cody Rhodes. Those cards show under the first-name letter with a question mark, and under the nickname\'s letter too, so check with RGL which one counts.',
           'Alternate names go with the spot: Mankind, Cactus Jack and Dude Love count as Mick Foley (the spot says "all"), Hollywood Hogan counts as Hulk Hogan, The Fiend is in the Bray Wyatt spot, and the Uso spot has both Jey and Jimmy. Ask RGL if you need a ruling.',
           'The listing\'s Garbage Pail Kids example says "C-Men", which looks copied from an earlier break. CM Punk has his own spot here.',
           'The listing doesn\'t say where a name that starts with a number goes. This guide puts 1-2-3 Kid in X / Y / Z, the way RGL\'s Chrome in the Club break (#6128) lists numbers with those letters.',
           'RGL says every spot is entered in a $600 store credit giveaway, drawn among everyone in all of its #6000 breaks after all six have run.',
           'Chrome Delight is a Topps Chrome WWE box, so it uses the same checklist as the Hobby box.',
           'Lists come from the official Topps and Panini checklists.'],
    sources=[['RGL #6144 break page (Run Good Life)', rgl_url(RGL6144_H)], ['Panini Select 2022, Prizm 2023 and PhotoGenic 2024 WWE checklists (official Panini CSVs)', SRC_PANINI], rgl6128['sources'][1], rgl6128['sources'][2], rgl6128['sources'][4], rgl6128['sources'][5],
             _src('2026-topps-chrome-wwe-sapphire', 'Topps Chrome WWE Sapphire'), _src('2025-topps-exalted-wwe', 'Topps Exalted WWE')],
)


if __name__ == '__main__':
    built = []
    n, u = letter_break(cc871, WWE_PRODUCTS, wwe_gender); built.append(write(cc871, n, u))
    n, u = letter_break(jwj0246, WWE_PRODUCTS, wwe_gender); built.append(write(jwj0246, n, u))
    n, u = letter_break(jwj0247, {'swc': TD.SW_CHROME, 'swg': TD.SW_GALAXY}, None, alt=False); built.append(write(jwj0247, n, u))
    n, u = letter_break(jwj0247u, {'sc': W.SC, 'universe': lib_letter_product('2026-topps-universe-wwe'), 'exalted': W.EXALTED}, jwj_wwe_gender); built.append(write(jwj0247u, n, u))
    n, u = team_break(cc873, {'rivals': dict(base={}, other={})}); built.append(write(cc873, n, u))
    n, u = team_break(cc872, {'chrome': TD.NFL_CHROME, 'midnight': TD.NFL_MIDNIGHT, 'absolute': dict(base={}, other={})}); built.append(write(cc872, n, u))
    n, u = team_break(jwj0244, {'flag': TD.NBA_FLAGSHIP}); built.append(write(jwj0244, n, u))
    CH, MN, IN = lib_team_product('2026-topps-chrome-football'), lib_team_product('2026-topps-midnight-football'), lib_team_product('2026-topps-inception-football')
    roster = {key_of(n): t for p_ in (CH, MN, IN) for b_ in ('base', 'other') for t, ns in p_[b_].items() for n in ns}
    n, u = team_break(gb1037, {'chrome': CH, 'midnight': MN}); built.append(write(gb1037, n, u))
    n, u = team_break(gb1038a, {'absolute': absolute_product(roster)}); built.append(write(gb1038a, n, u))
    n, u = team_break(gb1038b, {'chrome': CH, 'midnight': MN, 'inception': IN}); built.append(write(gb1038b, n, u))
    n, u = letter_break(cc875, {'select': lib_letter_product('2026-panini-select-nascar'), 'immaculate': lib_letter_product('2026-panini-immaculate-collection-nascar')}, None, alt=False); built.append(write(cc875, n, u))
    n, u = team_break(rgl6130, {'chrome': CH, 'midnight': MN}); built.append(write(rgl6130, n, u))
    n, u = team_break(rgl6129, {k: lib_mlb_product(v) for k, v in (('chrome', '2026-topps-chrome-baseball'), ('update', '2026-topps-update-series-baseball'),
        ('gilded', '2026-topps-gilded-collection-baseball'), ('museum', '2026-topps-museum-collection-baseball'), ('finest', '2026-topps-finest-baseball'))}); built.append(write(rgl6129, n, u))
    n, u = letter_break(rgl6128, {'sc': gpk_fold(lib_letter_product('2026-topps-stadium-club-wwe')), 'chrome': gpk_fold(lib_letter_product('2026-topps-chrome-wwe')), 'nscc': nscc_product('WWE'), 'finest': lib_letter_product('2025-topps-finest-wwe')}, rgl_wwe_gender); built.append(write(rgl6128, n, u))
    n, u = team_break(rgl6131, {'sc': lib_nba_product('2025-26-topps-stadium-club-basketball'), 'five': lib_nba_product('2025-26-topps-five-star-basketball'),
        'joy': lib_nba_product('2025-26-topps-x-bob-ross-the-joy-of-basketball'), 'flag': lib_nba_product('2026-27-topps-flagship-basketball')}); built.append(write(rgl6131, n, u))
    n, u = team_break(rgl6132, {'chrome': CH, 'absolute': absolute_product(roster)}); built.append(write(rgl6132, n, u))
    nas = {'select': lib_letter_product('2026-panini-select-nascar'), 'prizm': lib_letter_product('2025-panini-prizm-racing'), 'immaculate': lib_letter_product('2026-panini-immaculate-collection-nascar')}
    have = sorted({letters(n)[0] for p_ in nas.values() for n in entries_from_product(p_) if letters(n)[0]})
    # RGL's board on stream (Nov 25, 8:48 pm Eastern), first name; C and J split on the second letter
    rgl6133['spots'] = [cc_spot('A & N', 'AN'), cc_spot('B', 'B'), cc_spot('CA-CH', pre=[('CA', 'CH')]), cc_spot('CI-CY', pre=[('CI', 'CY')]),
        cc_spot('D', 'D'), cc_spot('E-F-G-H', 'EFGH'), cc_spot('JA-JE', pre=[('JA', 'JE')]), cc_spot('JI-JY', pre=[('JI', 'JY')]),
        cc_spot('K', 'K'), cc_spot('L-M-W', 'LMW'), cc_spot('R', 'R'), cc_spot('S-P-V-Z', 'SPVZ'), cc_spot('T', 'T')]
    n, u = letter_break(rgl6133, nas, None, alt=False); built.append(write(rgl6133, n, u))
    g40 = {k: (gpk_fold(lib_letter_product(v)) if k == 'sc' else lib_letter_product(v)) for k, v in GB1040_LIB.items()}
    have = sorted({letters(n)[0] for p_ in g40.values() for n in entries_from_product(p_) if letters(n)[0].isalpha()})
    # Acme's posted letter spots (listing, Nov 24)
    gb1040['spots'] = [cc_spot('A', 'A'), cc_spot('B', 'B'), cc_spot('CA-CH', pre=[('CA', 'CH')]), cc_spot('CI-CZ', pre=[('CI', 'CZ')]), cc_spot('D', 'D'),
        cc_spot('E / F', 'EF'), cc_spot('G', 'G'), cc_spot('H / I', 'HI'), cc_spot('JA-JE', pre=[('JA', 'JE')]), cc_spot('JF-JZ', pre=[('JF', 'JZ')]),
        cc_spot('K', 'K'), cc_spot('L', 'L'), cc_spot('M', 'M'), cc_spot('N / O', 'NO'), cc_spot('P / U', 'PU'), cc_spot('R', 'R'),
        cc_spot('SA-SH', pre=[('SA', 'SH')]), cc_spot('SI-SZ', pre=[('SI', 'SZ')]), cc_spot('T', 'T'), cc_spot('V / Q / W', 'VQW'), cc_spot('X / Y / Z', 'XYZ')]
    close(gb1040, 'Tuesday, November 24, 2026', ['5 boxes', '21 letter spots', '$135 per spot'])  # ran Nov 24 (Daniel)
    n, u = letter_break(gb1040, g40, None, alt=False); built.append(write(gb1040, n, u))
    n, u = team_break(gb1041, {'chrome': CH, 'midnight': MN, 'inception': IN}); built.append(write(gb1041, n, u))
    n, u = team_break(gb1042, {'logo': lib_mlb_product('2026-topps-chrome-baseball-logofractor-edition'), 'black': lib_mlb_product('2026-topps-chrome-black-baseball'),
        'prizm': lib_mlb_product('2026-panini-prizm-baseball'), 'museum': lib_mlb_product('2026-topps-museum-collection-baseball')}); built.append(write(gb1042, n, u))
    n, u = letter_break(gb1043, {'best': lib_letter_product('2026-bowman-u-best-football'), 'chrome': lib_letter_product('2026-topps-chrome-football'),
        'obsidian': lib_letter_product('2026-panini-obsidian-football'), 'bowman': lib_letter_product('2026-bowman-football')}, None, alt=False); built.append(write(gb1043, n, u))
    n, u = letter_break(gb1044, {'best': lib_letter_product('2026-bowman-u-best-football')}, None, alt=False); built.append(write(gb1044, n, u))
    n, u = letter_break(gb1045, {'lf25': lib_letter_product('2025-leaf-optichrome-football'), 'lf26': lib_letter_product('2026-leaf-optichrome-football')}, None, alt=False); built.append(write(gb1045, n, u))
    # Nov 27 check: Colfax CC876 to CC879 and RGL #6145 to #6147
    n, u = team_break(cc876, {'ginter': lib_mlb_product('2026-topps-allen-and-ginter-baseball'), 'logo': lib_mlb_product('2026-topps-chrome-baseball-logofractor-edition'),
        'cosmic': lib_mlb_product('2026-topps-cosmic-chrome-baseball'), 'museum': lib_mlb_product('2026-topps-museum-collection-baseball')}); built.append(write(cc876, n, u))
    n, u = letter_break(cc877, {'finestff': lib_letter_product('2026-topps-finest-fantastic-four'), 'pop': lib_letter_product('2026-leaf-pop-century'),
        'neon': lib_letter_product('2026-topps-neon-marvel'), 'deadpool': lib_letter_product('2025-topps-chrome-deadpool')}, None, alt=False); built.append(write(cc877, n, u))
    n, u = letter_break(cc878, {'chrome25': lib_letter_product('2025-topps-chrome-wwe'), 'chrome': W.CHROME}, cc878_gender); built.append(write(cc878, n, u))
    n, u = letter_break(cc879, {'neon': lib_letter_product('2026-topps-neon-marvel'), 'finestff': lib_letter_product('2026-topps-finest-fantastic-four'),
        'mintm': lib_letter_product('2026-topps-mint-marvel')}, None, alt=False); built.append(write(cc879, n, u))
    n, u = team_break(rgl6145, {'chrome': CH, 'midnight': MN}); built.append(write(rgl6145, n, u))
    n, u = team_break(rgl6146, {'cosmic': lib_mlb_product('2026-topps-cosmic-chrome-baseball'), 'finest': lib_mlb_product('2026-topps-finest-baseball'),
        'gilded': lib_mlb_product('2026-topps-gilded-collection-baseball'), 'chrome': lib_mlb_product('2026-topps-chrome-baseball')}); built.append(write(rgl6146, n, u))
    n, u = team_break(rgl6147, {'sc': lib_nba_product('2025-26-topps-stadium-club-basketball'), 'joy': lib_nba_product('2025-26-topps-x-bob-ross-the-joy-of-basketball'),
        'flag': lib_nba_product('2026-27-topps-flagship-basketball')}); built.append(write(rgl6147, n, u))
    n, u = letter_break(rgl6144, {'finest': lib_letter_product('2025-topps-finest-wwe'), 'exalted': lib_letter_product('2025-topps-exalted-wwe'), 'sapphire': lib_letter_product('2026-topps-chrome-wwe-sapphire'),
        'sc': lib_letter_product('2026-topps-stadium-club-wwe'), 'chrome': gpk_fold(lib_letter_product('2026-topps-chrome-wwe')),
        'select22': lib_letter_product('2022-panini-select-wwe'), 'prizm23': lib_letter_product('2023-panini-prizm-wwe'), 'photo24': lib_letter_product('2024-panini-photogenic-wwe')}, None); built.append(write(rgl6144, n, u))
    n, u = team_break(rgl6148, {'pwc': rgl6148_product('2026-panini-prizm-world-cup-soccer'), 'nt': rgl6148_product('2025-26-panini-national-treasures-road-to-world-cup-soccer'),
        'sel': rgl6148_product('2025-26-panini-select-road-to-world-cup-soccer')}); built.append(write(rgl6148, n, u))
    # RGL drafts: built only once RGL posts the listing (RGL_DRAFT_PREVIEW=<folder> writes previews there instead)
    PREVIEW = os.environ.get('RGL_DRAFT_PREVIEW')
    MLB6129 = lambda: {k: lib_mlb_product(v) for k, v in (('chrome', '2026-topps-chrome-baseball'), ('update', '2026-topps-update-series-baseball'),
        ('gilded', '2026-topps-gilded-collection-baseball'), ('museum', '2026-topps-museum-collection-baseball'), ('finest', '2026-topps-finest-baseball'))}
    NBA6131 = lambda: {'sc': lib_nba_product('2025-26-topps-stadium-club-basketball'), 'five': lib_nba_product('2025-26-topps-five-star-basketball'),
        'joy': lib_nba_product('2025-26-topps-x-bob-ross-the-joy-of-basketball'), 'flag': lib_nba_product('2026-27-topps-flagship-basketball')}
    n, u = team_break(rgl6134, MLB6129()); built.append(write(rgl6134, n, u))
    n, u = team_break(rgl6136, {'chrome': CH, 'donruss': nfl_split(lib_team_product('2026-donruss-football'), roster),
        'obsidian': nfl_split(lib_team_product('2026-panini-obsidian-football'), roster),
        'bowman': nfl_split(lib_team_product('2026-bowman-football-sapphire-edition'), roster), 'inception': IN}); built.append(write(rgl6136, n, u))
    p35 = {k: lib_letter_product(v) for k, v in RGL6135_LIB.items()}
    have = sorted({letters(n)[0] for p_ in p35.values() for n in entries_from_product(p_) if letters(n)[0].isalpha()})
    rgl6135['spots'] = [cc_spot(L, L) for L in have] + [cc_spot('# (numbers)', '#')]
    n, u = letter_break(rgl6135, p35, None, alt=False); built.append(write(rgl6135, n, u))
    p37 = {'prodebut': lib_letter_product('2026-topps-pro-debut-baseball')}
    have = sorted({letters(n)[0] for p_ in p37.values() for n in entries_from_product(p_) if letters(n)[0].isalpha()})
    rgl6137['spots'] = [cc_spot(L, L) for L in have]
    n, u = letter_break(rgl6137, p37, None, alt=False); built.append(write(rgl6137, n, u))
    n, u = team_break(rgl6138, {'finest': lib_mlb_product('2026-topps-finest-baseball'), 'gilded': lib_mlb_product('2026-topps-gilded-collection-baseball'),
        'cosmic': lib_mlb_product('2026-topps-cosmic-chrome-baseball'), 'update': lib_mlb_product('2026-topps-update-series-baseball')}); built.append(write(rgl6138, n, u))
    n, u = team_break(rgl6139, NBA6131()); built.append(write(rgl6139, n, u))
    n, u = letter_break(rgl612xwwe2, {'sc': gpk_fold(lib_letter_product('2026-topps-stadium-club-wwe')), 'chrome': gpk_fold(lib_letter_product('2026-topps-chrome-wwe')), 'nscc': nscc_product('WWE'), 'finest': lib_letter_product('2025-topps-finest-wwe')}, rgl_wwe_gender); built.append(write(rgl612xwwe2, n, u))
    n, u = team_break(rgl6140, {'chrome': CH, 'chromeh': CH, 'delight': CH}); built.append(write(rgl6140, n, u))
    p41 = {k: lib_letter_product(v) for k, v in RGL6141_LIB.items()}
    have = sorted({letters(n)[0] for p_ in p41.values() for n in entries_from_product(p_) if letters(n)[0].isalpha()})
    # RGL's board on stream (Nov 26), first name; C, J and S split on the second letter, "T (No The)"
    rgl6141['spots'] = [cc_spot('A', 'A'), cc_spot('B', 'B'), cc_spot('CA-CH', pre=[('CA', 'CH')]), cc_spot('CI-CZ', pre=[('CI', 'CZ')]), cc_spot('D', 'D'),
        cc_spot('E / F', 'EF'), cc_spot('G', 'G'), cc_spot('H / I', 'HI'), cc_spot('JA-JE', pre=[('JA', 'JE')]), cc_spot('JF-JZ', pre=[('JF', 'JZ')]),
        cc_spot('K', 'K'), cc_spot('L', 'L'), cc_spot('M', 'M'), cc_spot('N / O', 'NO'), cc_spot('P / U', 'PU'), cc_spot('R', 'R'),
        cc_spot('SA-SH', pre=[('SA', 'SH')]), cc_spot('SI-SZ', pre=[('SI', 'SZ')]), cc_spot('T (No The)', 'T'), cc_spot('V / Q / W', 'VQW'), cc_spot('X / Y / Z', 'XYZ')]
    assert len({sp['id'] for sp in rgl6141['spots']}) == 21
    n, u = letter_break(rgl6141, p41, None, alt=False); built.append(write(rgl6141, n, u))
    p612 = {k: lib_letter_product(v) for k, v in RGL612XMARVEL_LIB.items()}
    have = sorted({letters(n)[0] for p_ in p612.values() for n in entries_from_product(p_) if letters(n)[0].isalpha()})
    rgl612xmarvel['spots'] = [cc_spot(L, L) for L in have] + [cc_spot('# (numbers)', '#')]
    n, u = letter_break(rgl612xmarvel, p612, None, alt=False); built.append(write(rgl612xmarvel, n, u))
    p42 = {'chrome': lib_letter_product('2026-topps-chrome-ufc')}
    have = sorted({letters(n)[0] for p_ in p42.values() for n in entries_from_product(p_) if letters(n)[0].isalpha()})
    rgl6142['spots'] = [cc_spot(L, L) for L in have]
    n, u = letter_break(rgl6142, p42, None, alt=False); built.append(write(rgl6142, n, u))
    for cfg, num, pick, prods in [
            ]:
        posted = rgl_draft(cfg, num, pick)
        if not posted and not PREVIEW:
            print(cfg['id'], 'draft: waiting for RGL to post the listing'); continue
        n, u = team_break(cfg, prods())
        if posted: built.append(write(cfg, n, u))
        else:
            OUT_LIVE, OUT = OUT, PREVIEW
            write(cfg, n, u)
            OUT = OUT_LIVE
    json.dump(sorted(PRICE_TARGETS.values(), key=lambda t: t['q']), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'watch', 'price_targets.json'), 'w'), indent=0, ensure_ascii=False)
    json.dump([{k: b[k] for k in ('id', 'title', 'kicker', 'when', 'facts', 'ended', 'url', 'image', 'video') if k in b} for b in built], open(os.path.join(os.path.dirname(__file__), 'index.json'), 'w'))
    for b in built:
        if b['unmatched']: print(b['id'], 'UNMATCHED', b['unmatched'][:40])
