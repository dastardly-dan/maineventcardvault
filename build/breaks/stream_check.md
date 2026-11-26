# Stream check: what each scheduled run does

Two scheduled tasks (:15 and :45 each hour, Sonnet, on Daniel's computer) follow this file. Change the procedure here.
Goal (Daniel, Nov 25, 2026): while a breaker's YouTube stream is live, read the break number on screen and close the
pages for breaks that have already run; when the stream ends, close that night's pages.

1. Call add_repo for owner dastardly-dan, repo maineventcardvault, access push. Clone it (or reuse
   /home/claude/maineventcardvault) and git pull --rebase.
2. Run: python3 build/breaks/stream_gate.py
   - SKIP: stop. No commit. End with the single line "No stream to check."
   - RUN ended <stream> <ids>: the stream is over. Close every listed page (step 5) and publish (step 6).
   - RUN live <stream> <url> <ids>: go on to step 3.
3. Read the break number. Use the browser on Daniel's computer (Claude in Chrome if it's there, otherwise the built-in
   browser). Open <url> in a new tab (it's one of our own break pages; the stream is embedded there, which avoids
   YouTube's robot check). Take a screenshot first and find the video player in it; the browser window size changes from
   run to run, so never reuse click coordinates from an earlier run. Click the middle of the player to play it, wait about
   8 seconds, then take a zoomed screenshot of the player (if the zoom shows the page text instead of the stream, the
   click missed: look again and click the player). RGL's overlay shows the current break as "BREAK #6133" at the top left, a schedule list,
   and a board of spots. Then close the tab right away so nothing keeps playing.
   - Never click an "I'm not a robot" or any CAPTCHA check. If one appears, close the tab, make no changes, and end
     with one line saying the stream couldn't be read because of a robot check.
   - If the computer or browser can't be reached, end with one line saying so. The close-at-stream-end step on a later
     run still covers the night.
4. With break number N read clearly:
   - Close every listed page whose break number (the 4 digits in rgl6134) is lower than N. Pages without a number
     (rgl612xwwe2, rgl612xmarvel) close only when the stream ends.
   - If the board on screen clearly shows the spot groups for break N (letter groups like "A & N, B, CA-CH", or teams
     with NIL letters) and that page is a random break whose spots aren't set yet, update its spots to match, the way
     rgl6133 and rgl6132 were done in build/breaks/build.py. Never put buyer names on the page. If anything is hard to
     read, leave it alone.
5. Closing a page: add close(<id>, '<Weekday, Month D, YYYY of the stream night>', [its facts]) right after that
   page's config in build/breaks/build.py, like close(rgl6132, ...). Never delete a page.
6. Publish: python3 build/breaks/build.py, then python3 build/breaks/hub.py, add one release note line in
   build/breaks/release_notes.json, commit ("Stream check: ..."), git pull --rebase, git push origin main.
   If nothing changed, make no commit.
7. Finish with one or two plain lines for Daniel: the break number you read and which pages you closed or updated,
   or "Break #N running; nothing to close."

Writing rules for any page text: US dates, no em dashes, en dashes or arrows, plain wording. Never print secrets.
