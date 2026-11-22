import sys, json, os, re, collections
sys.path.insert(0, '/home/claude/work/cl')
os.chdir('/home/claude/work/cl'); sys.argv = ['x', 'none']
import parse as P, run as R
os.chdir('/home/claude/work/topps')
from manifest import M, STORE
R.women |= {'Alicia Taylor', 'Brie Bella'}
R.WWE['alias'].update({'"The Fiend" Bray Wyatt': 'Bray Wyatt', 'IYO SKY': 'Iyo Sky', '"The Million Dollar Man" Ted DiBiase': '"Million Dollar Man" Ted DiBiase'})
R.WWE['alias'].update({'"The Demon" Finn Bálor': 'Finn Bálor', '"Demon" Finn Bálor': 'Finn Bálor', 'The Demon Finn Bálor': 'Finn Bálor',
    'Seth "Freakin" Rollins': 'Seth Rollins', 'Mr. Perfect': '"Mr. Perfect" Curt Hennig', 'The Ultimate Warrior': 'Ultimate Warrior',
    'Edris Enofe': 'Edris Enofé', 'The Great Muta': 'Great Muta'})
R.women |= {'Shotzi', 'Scarlett', 'Jakara Jackson', 'Bad Girl Bayley', 'Braid-est Bianca', 'Chelsea Shhhush!', 'Disarm Her Becky',
            'Ladybird Lyra', 'Liv It Up', 'Popped Roxanne', 'Ripped Rhea', 'Soaring Sky', 'Tiffany Time', 'Unstitched Bliss'}
UFC_W = set('''Ailin Perez;Alexa Grasso;Alexia Thainara;Amanda Lemos;Amanda Nunes;Amanda Ribas;Angela Hill;Ariane da Silva;Bruna Brasil;Casey O'Neill;Chelsea Chandler;Dione Barbosa;Eduarda Moura;Erin Blanchfield;Fatima Kline;Gillian Robertson;Iasmin Lucindo;Irene Aldana;JJ Aldrich;Jacqueline Cavalcanti;Jaqueline Amorim;Jasmine Jasudavicius;Jessica Andrade;Joanna Jędrzejczyk;Julianna Peña;Karine Silva;Karol Rosa;Karolina Kowalkiewicz;Katlyn Cerminara;Kayla Harrison;Ketlen Vieira;Luana Pinheiro;Luana Santos;Mackenzie Dern;Macy Chiasson;Manon Fiorot;Maria Godinez Gonzalez;Marina Rodriguez;Maycee Barber;Mayra Bueno;Melissa Mullins;Miesha Tate;Miranda Maverick;Molly McCann;Natalia Cristina da Silva;Nora Cornolle;Norma Dumont;Piera Rodriguez;Raquel Pennington;Rose Namajunas;Shi Ming;Tabatha Ricci;Talita Alencar;Tatiana Suarez;Tracy Cortez;Valentina Shevchenko;Viktoriia Dudakova;Virna Jandiroba;Wang Cong;Yan Xiaonan;Yazmin Jauregui;Zhang Weili'''.split(';'))
UFC_ALIAS = {'Dricus du Plessis': 'Dricus Du Plessis', 'JeongYeong Lee': 'Jeong Yeong Lee', 'Marquel Mederos': 'MarQuel Mederos',
             'Reinier de Ridder': 'Reinier De Ridder', 'Ateba Gautier': 'Gautier Ateba'}
ALLTEAMS = list(P.NFL) + list(P.NBA) + list(P.MLB)

def pre(lines):
    out = []
    i = 0
    while i < len(lines):
        l = lines[i]
        s = l.strip()
        # "2026 Bowman Baseball Checklist" style title rows
        if re.match(r'^(19|20)\d\d\b.*Checklist\s*$', s, re.I): i += 1; continue
        # code glued to name: HRS-ABAce Bailey
        l = re.sub(r'^(\s*[A-Z0-9]+-[A-Z0-9]*?)([A-Z][a-z])', r'\1  \2', l)
        # code alone on a line, name on the next (indented) line
        if re.fullmatch(r'[A-Z0-9]+-[A-Z0-9]+', s) and i + 1 < len(lines) and lines[i + 1].startswith(' ') and re.search('[a-z]', lines[i + 1]):
            out.append(s + '  ' + lines[i + 1].strip()); i += 2; continue
        l = l.replace('SUBJECT TO CHANGE*', '')
        out.append(l); i += 1
    return out

JUNK = re.compile(r'SLIME BASE PARALLELS|^\$|Tickets to|of Your Choice|Graded|Custom Batting|^ACE$|^Checklist$|SKETCH CARD ARTIST')

def fix_glued(cards):
    known = {c['name'] for c in cards if len(c['cells']) >= 2}
    kl = sorted(known, key=len, reverse=True)
    for c in cards:
        n = c['name']
        if n in known or len(n.split()) < 3: continue
        for k in kl:
            if n.startswith(k + ' ') and len(k.split()) >= 2:
                c['name'] = k; break
    for c in cards:
        if c['name'] == 'Eric Maxim Choupo-Moting New York Red Bulls': c['name'] = 'Eric Maxim Choupo-Moting'
    return [c for c in cards if not JUNK.search(c['name'])]
CFG = {
 'mlb': lambda: dict(teams=P.MLB, team_mode=True),
 'nba': lambda: dict(teams=list(P.NBA), team_mode=True, alias={'Manu Ginobili': 'Manu Ginóbili'}),
 'nfl': lambda: dict(teams=list(P.NFL), team_mode=True),
 'college': lambda: dict(teams=[], team_mode=True, full_team=True),
 'wwe': lambda: R.WWE,
 'sw': lambda: dict(auto_name_col=1, skip_subsets=r'^(ERAS|FACTIONS)$', drop_names=('Solo: A Star Wars Story', 'Director')),
 '': lambda: dict(teams=[]),
 'ufc': lambda: dict(teams=[], alias=UFC_ALIAS),
 'mixed': lambda: dict(teams=ALLTEAMS),
 'gpk': lambda: dict(teams=[], name_col={'base': 1, 'auto': 1, 'insert': 1, 'multi': 1}),
}
def slug(s): return re.sub(r'[^a-z0-9]+', '-', s.lower().replace('&', 'and').replace("'", '')).strip('-')
os.makedirs('out', exist_ok=True)
rep = {}
for k, name, st, f, sport, mode in M:
    p = 'txt/%d.txt' % k
    if not os.path.exists(p): continue
    cfg = CFG[mode]()
    cards = fix_glued(P.parse_lines(pre(open(p, encoding='utf-8').read().splitlines()), cfg))
    out = P.bucket(cards, cfg)
    pid = slug(name)
    src = 'https://cdn.shopify.com' + STORE[st] + f
    P.write('out/%s.txt' % pid, dict(name=name, sport=sport, added='2026-11-22', source=src, note=''), out, cfg,
            R.women if sport == 'WWE' else (UFC_W if sport == 'UFC' else frozenset()))
    json.dump(cards, open('out/%s.cards.json' % pid, 'w'), ensure_ascii=False)
    names = {p_[0] for v in out.values() for e in v for p_ in e}
    odd = [n for n in names if len(n) > 34 or re.search(r'\d{2}|Rookie|Checklist|Topps|\s{2}', n) or not re.search('[a-z]', n)]
    rep[k] = (pid, {s: len(v) for s, v in out.items()}, len(cards), len(names), sorted(odd)[:6])
for k, v in rep.items(): print(k, *v)
