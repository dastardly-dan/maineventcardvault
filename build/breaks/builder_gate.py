"""Decides whether a page builder run should do any work (Daniel, Nov 25, 2026).

The page builder fires every 5 minutes. It works on every run during the first 4 hours of a breaker's stream, and
otherwise once every 30 minutes. Acme posts new breaks Tuesdays and Thursdays at 1:00 pm Eastern, so it also works
on every run from 1:03 to 1:45 pm Eastern on those days. JWJ posts Fridays at 6 pm Eastern (6:03 to 6:45 pm the same way).
Colfax posts Fridays (for Sunday) and Mondays (for Tuesday) at no set time, so the half-hourly checks cover it. The stream start is the moment the watcher saw the breaker's YouTube stream go live. The watcher starts looking
2 hours before the first scheduled break; if it never finds the stream, the first scheduled break time stands in.

Prints one line: "RUN stream ...", "RUN half-hourly" or "SKIP ...".
"""
import json, os, sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
FAST = timedelta(hours=4)      # every 5 minutes for this long after the stream starts


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
        started, first = parse(st.get('started')), parse(st.get('first_start'))
        # The fast checks start when the stream actually goes live (Daniel, Nov 25). Only if the watcher never found the
        # stream at all does the first scheduled break time stand in for it.
        stale = started and first and started < first - timedelta(hours=6)  # left over from an earlier night
        if started and not stale:
            anchor = started
        elif not st.get('video') or stale:
            anchor = first  # the watcher never found tonight's stream
        else:
            anchor = None   # stream found but not live yet: wait for it
        if anchor and anchor <= now <= anchor + FAST:
            return 'RUN stream ' + shop + ' (live since ' + anchor.isoformat(timespec='minutes') + ')'
    et = now.astimezone(ZoneInfo('America/New_York'))
    if et.weekday() in (1, 3) and et.hour == 13 and 3 <= et.minute <= 45:
        return 'RUN Acme posting window (Tuesday and Thursday, 1 pm Eastern)'
    if et.weekday() == 4 and et.hour == 18 and 3 <= et.minute <= 45:
        return 'RUN JWJ posting window (Friday, 6 pm Eastern)'
    if now.minute % 30 < 5:
        return 'RUN half-hourly'
    return 'SKIP no stream in its first 4 hours; next half-hourly check at :00 or :30'


if __name__ == '__main__':
    print(main())
