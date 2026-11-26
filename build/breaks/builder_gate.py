"""Decides whether a page builder run should do any work (Daniel, Nov 25, 2026).

The page builder fires every 5 minutes. It works on every run during the first 4 hours of a breaker's stream, and
otherwise once every 30 minutes. The stream start is the moment the watcher saw the breaker's YouTube stream go live,
or, if it couldn't tell, the earliest estimated start time on that breaker's listings.

Prints one line: "RUN stream ...", "RUN half-hourly" or "SKIP ...".
"""
import json, os, sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
FAST = timedelta(hours=4)      # every 5 minutes for this long after the stream starts
EARLY = timedelta(minutes=15)  # and from a little before the scheduled start


def parse(s):
    try:
        return datetime.fromisoformat(s) if s else None
    except ValueError:
        return None


def main(now=None):
    now = now or datetime.now(timezone.utc)
    path = os.path.join(HERE, 'watch', 'streams.json')
    streams = json.load(open(path)) if os.path.exists(path) else {}
    for shop, st in streams.items():
        for anchor in (parse(st.get('started')), parse(st.get('first_start'))):
            if anchor and anchor - EARLY <= now <= anchor + FAST:
                return 'RUN stream ' + shop + ' (started ' + anchor.isoformat(timespec='minutes') + ')'
    if now.minute % 30 < 5:
        return 'RUN half-hourly'
    return 'SKIP no stream in its first 4 hours; next half-hourly check at :00 or :30'


if __name__ == '__main__':
    print(main())
