"""Turn an official Panini checklist CSV (SPORT, YEAR, BRAND, PROGRAM, CARD SET, ATHLETE, TEAM, POSITION,
CARD NUMBER, SEQUENCE; one row per card and parallel) into a Spot Builder library file.

  python3 build/breaks/panini_csv.py <file.csv> <id> "<name>" <sport> [--team] [--women "A;B"]

Rules: printing plates, mystery redemptions and mascot cards are skipped. A set is an autograph set when
its name says so (Signatures, Autographs, Ink, Marks, Initials, Pen Pals, Signing ...); "Base ..." and
PFL-style "... Ticket" sets are base; everything else (inserts and memorabilia) is insert. "A/B" athletes
are multi-person cards; "Bo Jackson/Bo Jackson" counts once.
"""
import csv, re, sys, collections

AUTO = re.compile(r'Signature|Autograph|\bAutos?\b|\bInk\b|\bMarks\b|Initials|Inscription|Signed|Penmanship|Script|'
                  r'Signing|\bSigs?\b|Pen Pals', re.I)
SKIP = re.compile(r'Printing Plate|Redemption|^Mascots', re.I)
TWO_WORD = ['Red Sox', 'White Sox', 'Blue Jays', 'Trail Blazers', 'Fighting Irish', 'Crimson Tide', 'Tar Heels',
            'Yellow Jackets', 'Blue Devils', 'Sun Devils', 'Golden Gophers', 'Nittany Lions', 'Red Raiders',
            'Horned Frogs', 'Demon Deacons', 'Golden Bears', 'Scarlet Knights', 'Mean Green', 'Rainbow Warriors',
            'Golden Hurricane', "Ragin' Cajuns", 'Green Wave', 'Black Knights', 'Golden Flashes', 'Thundering Herd',
            'Blue Hens', 'Fighting Illini', 'Golden Eagles', 'Red Wolves', 'Blue Raiders', 'Golden Knights']


# College teams that share a pro nickname (Daniel, Nov 24: Drew Mestemaker of Oklahoma State landed on the Dallas Cowboys).
# They keep the full school name so the Spot Builder treats them as college, not the pro team.
COLLEGE_SAME_NICK = {'Oklahoma State Cowboys', 'Wyoming Cowboys', 'Boston College Eagles', 'Eastern Washington Eagles',
                     'Eastern Michigan Eagles', 'Georgia Southern Eagles', 'Pittsburgh Panthers', 'Louisville Cardinals',
                     'Ball State Cardinals', 'Baylor Bears', 'Colorado State Rams', 'Air Force Falcons', 'Idaho State Bengals',
                     'Cal State Fullerton Titans', 'East Carolina Pirates', 'LSU Tigers', 'Auburn Tigers', 'Clemson Tigers',
                     'Missouri Tigers', 'Memphis Tigers', 'Virginia Cavaliers', 'Montana Grizzlies', 'Toledo Rockets',
                     'Buffalo Bulls', 'South Florida Bulls', 'Sacramento State Hornets', 'UT Arlington Mavericks',
                     'Rice Owls', 'Kent State Golden Flashes', 'Texas Southern Tigers', 'Grambling State Tigers', 'Jackson State Tigers'}

def nickname(team, full=False):
    team = team.strip()
    if not team or team in ('No Team',): return ''
    if full or team in COLLEGE_SAME_NICK: return team
    for t in TWO_WORD:
        if team.endswith(' ' + t) or team == t: return t
    return team.split()[-1]


def section(card_set):
    if AUTO.search(card_set): return 'auto'
    if card_set.startswith('Base') or re.search(r'\bTicket\b', card_set): return 'base'
    return 'insert'


def convert(path, pid, name, sport, team_mode=False, full_team=False, women=(), out_dir='.'):
    secs = collections.OrderedDict((k, collections.OrderedDict()) for k in ('base', 'auto', 'insert', 'multi'))
    meta = None
    with open(path, newline='', encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            meta = meta or r
            cs = (r['CARD SET'] or '').strip()
            if SKIP.search(cs) or (r.get('POSITION') or '').strip() == 'Mascot': continue
            names = [n.strip() for n in (r['ATHLETE'] or '').split('/')]
            teams = [t.strip() for t in (r['TEAM'] or '').split('/')]
            people = []
            for i, n in enumerate(names):
                if not n: continue
                t = teams[i] if i < len(teams) else (teams[0] if teams else '')
                people.append((n, nickname(t, full_team) if team_mode else ''))
            people = list(dict.fromkeys(people))
            if not people: continue
            if len({p[0] for p in people}) > 1:
                secs['multi'][tuple(people)] = 1
            else:
                secs[section(cs)][people[0]] = 1

    def fmt(p):
        s = p[0]
        if p[1]: s += ' | ' + p[1]
        if p[0] in women: s += ' | W'
        return s
    L = ['# name: ' + name, '# sport: ' + sport, '# added: 2026-11-22', '# source:',
         '# note: Official Panini checklist (' + (meta['BRAND'] + ' ' + meta['PROGRAM']).strip() + ' CSV)']
    for sec, items in secs.items():
        if not items: continue
        L += ['', '[' + sec + ']']
        if sec == 'multi':
            L += [' / '.join(fmt(p) for p in k) for k in items]
        else:
            L += sorted({fmt(p) for p in items}, key=lambda x: x.lower().lstrip('"'))
    out = '%s/%s.txt' % (out_dir, pid)
    open(out, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    return {k: len(v) for k, v in secs.items()}


if __name__ == '__main__':
    a = sys.argv[1:]
    team = '--team' in a; full = '--full-team' in a
    women = ()
    if '--women' in a: women = set(x.strip() for x in a[a.index('--women') + 1].split(';'))
    print(convert(a[0], a[1], a[2], a[3], team or full, full, women))
