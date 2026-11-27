"""Pull and store the transcript of a breaker's YouTube stream or break video (Daniel, Nov 27, 2026).

Runs on GitHub (workflow "Stream transcript", .github/workflows/stream-transcript.yml), because this repo's other
tools can't reach YouTube. Give it one or more YouTube links (watch, live, youtu.be or shorts links). For each video
it downloads YouTube's captions (the uploader's if there are any, otherwise the automatic ones) with yt-dlp and saves:

  build/breaks/transcripts/<video id>.json  {"video", "title", "channel", "date", "url", "duration", "source",
                                             "fetched", "segments": [[seconds, "text"], ...]}
  build/breaks/transcripts/<video id>.txt   the same text, one line per caption with its [h:mm:ss] time
  build/breaks/transcripts/index.json       one entry per stored video (no text), newest first

A stream that's still live has no captions yet: run it again after the stream ends and YouTube finishes processing
(usually within a few hours). build/ is in .assetsignore, so none of this is served on the site.

  python3 build/breaks/transcripts.py "https://www.youtube.com/watch?v=..." [more links]
"""
import datetime, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'transcripts')
ID = re.compile(r'(?:v=|youtu\.be/|/live/|/shorts/|/embed/)([\w-]{11})')


def video_id(url):
    m = ID.search(url)
    if m: return m.group(1)
    if re.fullmatch(r'[\w-]{11}', url.strip()): return url.strip()
    return None


def clock(s):
    s = int(s); return '%d:%02d:%02d' % (s // 3600, s // 60 % 60, s % 60)


def parse_json3(path):
    segs = []
    for ev in json.load(open(path, encoding='utf-8')).get('events', []):
        if 'segs' not in ev: continue
        t = ''.join(s.get('utf8', '') for s in ev['segs']).replace('\n', ' ').strip()
        t = re.sub(r'\s+', ' ', t)
        if not t or t in ('[Music]', '[Applause]'): continue
        segs.append([round(ev.get('tStartMs', 0) / 1000, 1), t])
    return segs


def fetch(vid):
    url = 'https://www.youtube.com/watch?v=' + vid
    with tempfile.TemporaryDirectory() as tmp:
        meta = json.loads(subprocess.run(['yt-dlp', '-J', '--no-warnings', url], capture_output=True, text=True, check=True).stdout)
        if meta.get('is_live') or meta.get('live_status') in ('is_live', 'is_upcoming'):
            return None, '%s is still live or hasn\'t started, so YouTube has no captions for it yet. Run this again after it ends.' % vid
        manual = any(k.startswith('en') for k in (meta.get('subtitles') or {}))
        args = ['yt-dlp', '--skip-download', '--no-warnings', '--sub-format', 'json3', '--sub-langs', 'en.*,en',
                '--write-subs' if manual else '--write-auto-subs', '-o', os.path.join(tmp, '%(id)s.%(ext)s'), url]
        subprocess.run(args, capture_output=True, text=True, check=True)
        files = sorted(f for f in os.listdir(tmp) if f.endswith('.json3'))
        if not files:
            return None, '%s has no English captions on YouTube.' % vid
        pick = next((f for f in files if '.en.' in f or '.en-orig.' in f), files[0])
        segs = parse_json3(os.path.join(tmp, pick))
    d = meta.get('upload_date') or ''
    doc = {'video': vid, 'title': meta.get('title', ''), 'channel': meta.get('channel') or meta.get('uploader', ''),
           'date': '%s-%s-%s' % (d[:4], d[4:6], d[6:]) if len(d) == 8 else '', 'url': url,
           'duration': meta.get('duration'), 'source': 'uploader captions' if manual else 'YouTube automatic captions',
           'fetched': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), 'segments': segs}
    return doc, None


def main(urls):
    os.makedirs(OUT, exist_ok=True)
    ip = os.path.join(OUT, 'index.json')
    index = json.load(open(ip)) if os.path.exists(ip) else []
    problems, done = [], []
    for u in urls:
        for part in re.split(r'[\s,]+', u.strip()):
            if not part: continue
            vid = video_id(part)
            if not vid: problems.append('Not a YouTube video link: ' + part); continue
            try:
                doc, err = fetch(vid)
            except subprocess.CalledProcessError as e:
                problems.append('%s: YouTube refused or failed (%s)' % (vid, (e.stderr or '').strip().splitlines()[-1:] or 'no detail')); continue
            if err: problems.append(err); continue
            json.dump(doc, open(os.path.join(OUT, vid + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
            with open(os.path.join(OUT, vid + '.txt'), 'w', encoding='utf-8') as f:
                f.write('%s\n%s | %s | %s\n\n' % (doc['title'], doc['channel'], doc['date'], doc['url']))
                f.writelines('[%s] %s\n' % (clock(t), x) for t, x in doc['segments'])
            entry = {k: doc[k] for k in ('video', 'title', 'channel', 'date', 'url', 'duration', 'source', 'fetched')}
            entry['lines'] = len(doc['segments']); entry['words'] = sum(len(x.split()) for _, x in doc['segments'])
            index = [e for e in index if e['video'] != vid] + [entry]
            done.append('%s: %s (%d lines, %s words)' % (vid, doc['title'], entry['lines'], format(entry['words'], ',')))
    index.sort(key=lambda e: (e.get('date', ''), e.get('fetched', '')), reverse=True)
    json.dump(index, open(ip, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for d in done: print('Saved', d)
    for p in problems: print('Problem:', p)
    if problems and not done: sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(__doc__)
    main(sys.argv[1:])
