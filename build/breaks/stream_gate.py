"""Decides whether the stream check should look at a breaker's stream (Daniel, Nov 25, 2026).

Prints one line:
  RUN live <stream> <page url to open> <open page ids...>   the stream is live: read the break number on screen
  RUN ended <stream> <open page ids...>                      the stream is over: close that night's open pages
  SKIP <reason>
"""
import json, os
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = 'https://maineventcardvault.com/breaks/'


def main(now=None):
    now = now or datetime.now(timezone.utc)
    streams = json.load(open(os.path.join(HERE, 'watch', 'streams.json')))
    pages = [i for i in json.load(open(os.path.join(HERE, 'index.json'))) if i.get('video') and not i.get('ended')]
    for key, st in streams.items():
        mine = [p['id'] for p in pages if p['video'] == st.get('video')]
        if not mine:
            continue
        if st.get('live'):
            return ' '.join(['RUN live', key, SITE + mine[0]] + mine)
        started = datetime.fromisoformat(st['started']) if st.get('started') else None
        if started and now - started > timedelta(hours=1):
            return ' '.join(['RUN ended', key] + mine)
    return 'SKIP no live stream with open break pages'


if __name__ == '__main__':
    print(main())
