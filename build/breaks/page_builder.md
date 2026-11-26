# Break page builder: what each scheduled run does

There are 12 copies of the Break page builder scheduled task, one at each 5-minute mark (:03, :08 ... :58), all on
Sonnet. Change the procedure here, not in the tasks: each task only clones the repo, runs the gate and follows this file.

You maintain the break guide pages on Daniel Feldbusch's site, Main Event Card Vault (maineventcardvault.com). A GitHub
Action watches four card breakers' Shopify stores (Acme Packs, JWJ Collector Breaks, Colfax Collectibles, Run Good Life)
every 5 minutes and writes new or removed products to build/breaks/watch/queue.json. It also records when the
breakers' YouTube streams go live in build/breaks/watch/streams.json. Your job is to turn that queue into break guide pages.

The gate (build/breaks/builder_gate.py) already said RUN when you get here. It says RUN during the first 4 hours of a
breaker's stream, from 1:03 to 1:45 pm Eastern on Tuesdays and Thursdays (when Acme posts new breaks), and once every
30 minutes otherwise.

1. Start a fresh store check: gh api -X POST repos/dastardly-dan/maineventcardvault/actions/workflows/break-watch.yml/dispatches -f ref=main,
   then poll git fetch for up to 90 seconds until a new "Break watcher" commit lands (if nothing changed in the stores
   there won't be one; then just go on). Then git pull --rebase.
2. Quick exit: if build/breaks/watch/queue.json is empty ([]) and no open break on the hub (the order list in
   build/breaks/hub.py) is more than a day past its date, stop. Make no commit and end with the single line "No new breaks."
3. Otherwise read README.md, in particular "Break watcher and automatic pages", "Break page builder runbook" (including
   items 3i, 3j and 3k), "Breaks menu", and the notes on break guide pages, Acme pages, live open/sold status, finished
   breaks and release notes. The runbook is your procedure; follow it step by step.

Work the queue as the runbook says:
- Decide which added products are real group breaks. Skip merch, fees, giveaway winners and mystery packs. A "Filler" or
  "25% chance filler" option belongs on its main break's page, not its own page.
- Another copy may have built the page minutes ago: git pull --rebase right before editing, and search
  build/breaks/build.py for a config with that break number. If one exists, update it instead.
- Build a page for each new break from the checklist library in build/breaks/checklists/, modeled on the closest
  existing config in build/breaks/build.py (rgl6134 pick your team, rgl6128 pick your letter, rgl6136 random team,
  rgl6137 random letter, gb1040 multi-sport letters). Page ids use the breaker prefix and number: gb1040, jwj0249,
  cc876, rgl6128. Turn on live sold tracking (live=dict(shop=..., handle=...)) for pick-your-letter and pick-your-team
  breaks; shop keys are acme, jwj, colfax, rgl. Note giveaway or randomized teams (for example "Dodgers random to all").
- No guessed setups (Daniel, Nov 25, 2026): build only from what the listing says. Never guess letter groupings, team
  pairings, the format, or first-or-last-name rules. If the listing leaves something out, say plainly that the
  breaker hasn't posted it and to check with them. Letter pages may sort by first name, but must say the listing
  doesn't say which the breaker uses. Never build a page before the listing is posted.
- Never guess at a checklist: if a box isn't in the library and you can't get the official list through WebFetch, build
  the page from the boxes you do have and say on the page which boxes are missing. Tell Daniel which checklist links
  are needed.
- Update pages whose break was renumbered or changed. Close pages for removed products or breaks more than a day past
  their date with close(); never delete a page.
- Rebuild (build.py, builder.py if checklists changed, hub.py), add release note lines, clear handled queue items,
  commit with a clear message, git pull --rebase, then git -c push.negotiate=true push origin main. If
  build/build_site.py was run and only touched index.html or listings.json with unrelated churn, discard those two files.
- Check your work before pushing: the build scripts run without errors, each new page exists in breaks/, and the Break
  guides page (breaks/index.html) lists it. The Breaks menu itself stays short (four links) and doesn't list breaks.

Rules: the cloud shell cannot reach the stores or maineventcardvault.com; use the data in queue.json and WebFetch for
anything else. Page text uses US dates (November 24, 2026), plain friendly wording, no em dashes, en dashes or arrows,
and spells out acronyms on first use. Don't change unrelated parts of the site. Don't use a browser. Never print or
paste secrets.

Finish with a short message for Daniel: each new page with its link (https://maineventcardvault.com/breaks/<id>), its
format, spots and price, pages updated or closed, boxes that are missing, and anything he needs to do, such as sending
a checklist link.
