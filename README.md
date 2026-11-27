# Main Event Card Vault — Website

Static site for Main Event Card Vault LLC (WWE, Marvel, wrestling & sports trading cards).
Hosted on Cloudflare (Worker `maineventcardvault`), auto-deploys on every push to `main`.

- `index.html` — **generated.** The storefront, self-contained: CSS, JS and card data inlined.
- `assets/logo.png`, `assets/favicon.png` — brand marks, referenced by the page.
- `assets/cards/` — photos for cards that aren't on eBay (see *The collection* below).
- `listings.json` — the card feed, published for reference.
- `build/template.html` — the page itself (markup, CSS, JS) with a `__MECV_DATA__` placeholder.
  **This is the file to edit when changing how the site looks or behaves.**
- `build/raw_listings.tsv` — live active eBay listings.
- `build/collection.tsv` — cards not currently listed: owned-not-for-sale, and sold.
- `build/cdp_vault.tsv` — unlisted cards scanned in Card Dealer Pro; shown in the Collection with the CDP scan as the photo.
- `build/build_site.py` — the two TSVs + the template in, `index.html` + `listings.json` out.

Never hand-edit `index.html`. Edit the template or a TSV and rebuild:

```
python3 build/build_site.py
```

## Refreshing the inventory

The for-sale half of the site mirrors the **live active eBay listings** for seller
`feld-111937`. Card photos are hotlinked from `i.ebayimg.com`, so nothing needs
downloading — when a card sells and leaves the active list, it drops off the storefront.

1. Open Seller Hub active listings in a signed-in tab:
   `https://www.ebay.com/sh/lst/active?sort=price&order=desc&limit=200`
2. Run this in the page console:

```js
copy([...document.querySelectorAll('tr')].map(tr => {
  const t = tr.innerText || '';
  const id = (t.match(/\b(\d{12})\b/) || [])[1];
  if (!id) return null;
  const L = t.split('\n').map(s => s.trim());
  const i = L.findIndex(s => /Buy It Now · \d{12}/.test(s));
  const img = tr.querySelector('img');
  const key = img && img.src ? (img.src.match(/images\/g\/([^\/]+)\//) || [])[1] : '';
  const price = ((t.match(/\$[\d,]+\.\d{2}/) || [''])[0]).replace(/[$,]/g, '');
  const sku = (L[i + 2] && L[i + 2].length < 12) ? L[i + 2] : '';
  return [id, price, key, sku, L[i - 1]].join('\t');
}).filter(Boolean).join('\n'));
```

3. Paste over the body of `build/raw_listings.tsv`, keeping the header row.
4. `python3 build/build_site.py`
5. Commit and push. Cloudflare rebuilds on its own.

**When a card sells,** move its row out of `raw_listings.tsv` and into `collection.tsv`
with `status=sold` — otherwise the sale is only recorded in the deployed HTML and the
next rebuild puts the card back on the storefront.

## The collection — cards that aren't for sale

`build/collection.tsv` is the catalog of everything not currently listed. Nine
tab-separated columns; **a stray tab shifts every later column, so the build refuses to
run on a row with the wrong count** rather than producing a card labelled "Sold 1795.00".

| Column | Notes |
|---|---|
| `status` | `collection` (owned, not for sale) or `sold` (past sale) |
| `title` | Full card title. Category, year, set and the badges are all derived from it — write it like an eBay title. |
| `photo` | `ebay:<imageKey>` to hotlink an eBay photo, `assets/cards/<file>.jpg` for a photo committed here, or an absolute URL. Blank is fine — the card shows a "no photo" tile. |
| `estValue` | Card Ladder last-sold comp, for `collection` rows. Blank shows "Not for sale" with no number. |
| `compDate` | `YYYY-MM-DD` the comp was pulled — displayed, so a stale value is visible rather than silently wrong. |
| `soldPrice` | For `sold` rows. |
| `soldDate` | `YYYY-MM-DD`. Rendered as "Sold Aug 2026". |
| `sku` | Optional. Used as the card's id when present. |
| `notes` | Optional. Shows in the lightbox. |

### Card Dealer Pro vault (`build/cdp_vault.tsv`)

Everything in Card Dealer Pro that is *not* listed on eBay lands in the Collection from this
file, so the site mirrors the vault without hand-entering 500+ rows. Six columns: `cardId`,
`batchId`, `price`, `sku`, `tag`, `title`. `price` is the CDP list price, shown with a `*`
(estimate); `tag` is the CDP category tag and overrides keyword matching; the photo is the CDP
front scan, built as `https://storage.googleapis.com/cdp-batches-prod/74399-<batchId>/<cardId>-front-md.jpg`
and hotlinked (nothing is stored in this repo). To refresh: export the unlisted cards from CDP
(`/api/v2/inventory/59432`, minus anything already on eBay or sold), rewrite the file, rebuild.
When a vault card gets listed on eBay, drop its row from here and add it to `raw_listings.tsv`.

On the site these appear in the same grid as the store inventory, with a **Not for sale**
or **Sold** badge and no buy button. The `Show` chips switch between For sale / Collection /
Sold / Everything, and the whole row only renders once there is more than one kind of card
— so a repo with an empty `collection.tsv` looks exactly like the old storefront.

**The page opens on "For sale"** so a buyer sees the store first. To open on the full
catalog instead, change `avail: "forsale"` to `avail: "all"` in `build/template.html`.

Category and tag chip counts follow the availability filter, so a chip never advertises
cards the current view can't show.

## Note on image sizes

Use `s-l960` for thumbnails and `s-l1600` for the lightbox. eBay fits images inside the
requested box, so a portrait card at `s-l500` comes back only ~280–380px wide and looks soft.

Photos committed to `assets/cards/` are used at one size for both the tile and the
lightbox — resize to roughly 1200px on the long edge before committing.

## Break guides

`/breaks/` is a hub of reference pages for group breaks: who could land in each letter or
team spot, box by box. Linked from the storefront's Breaks menu; every page carries `noindex`.

- `breaks/index.html` is the hub. `breaks/<id>.html` is one break (served at `/breaks/<id>`).
- `build/breaks/build.py` generates every break page except `cc874` from the data files next
  to it (`wwe_data.py`, `team_data.py`) and `template.html`. To add a break, add its config
  and spots in `build.py`, then run `python3 build/breaks/build.py && python3 build/breaks/hub.py`.
- Pick-your-letter breaks carry price and open/sold per spot, copied from the breaker's store
  data on the day the page was built. They don't update on their own.
- `breaks/cc874.html` was built separately; replace the whole file to update it.
- The **Breaks** menu (storefront nav, hub, every break page) is written by `hub.py` between
  `<!--BMENU-->` markers, including into `build/template.html`. After adding a break, run
  `build.py`, then `hub.py`, then `python3 build/build_site.py` so the storefront picks it up.

### Spot builder and the checklist library

- `breaks/builder.html` (served at `/breaks/builder`) is the Spot Builder: pick checklists and box
  counts, set a spot count, and it balances letters into that many spots. Heavy letters get split
  into two-letter ranges or Men / Women. It also offers an optional sales goal for pricing, and
  copy and CSV export. Settings save in the visitor's browser.
- **Checklist library:** `build/breaks/checklists/*.txt`, one plain text file per product. The format
  is documented at the top of `build/breaks/builder.py` (`[base]` / `[auto]` / `[insert]` /
  `[multi]` sections, `| W` marks women, `| Team` for team products).
- **Weekly routine when Daniel sends new checklists:** add one `.txt` per product, then run
  `python3 build/breaks/builder.py && python3 build/breaks/hub.py`, check the Checklist library
  tab, and push. Break guide pages built by `build.py` still read `wwe_data.py` / `team_data.py`.
- **Official sources (Nov 22, 2026):** every library file except 2026 Topps Chrome WWE now comes from
  the official Topps checklist (PDF or .xls) or, for LogoFractor, Checklist Insider; each file's
  `# source:` line has the link. `build/breaks/checklist_parse.py` is the parser used: flatten the
  PDF with `pdftotext -layout`, then `parse_lines()` + `bucket()` + `write()`. It rejoins wrapped
  names, groups dual/triple/quad cards that share a card code into `[multi]`, files relics with
  inserts, skips sketch, printing plate, redemption and "Moments" subsets, and keys Star Wars
  autographs by character, not actor. WWE names are aliased to one spelling across products
  (e.g. Nattie to Natalya, Rob VAN Dam to Rob Van Dam) so the builder merges them.
- **Panini / Donruss CSVs:** Panini's official checklist export (one row per card and parallel) converts
  with `python3 build/breaks/panini_csv.py <file.csv> <id> "<name>" <sport> [--team] [--women "A;B"]`.
  Set names decide the section (Signatures/Autographs/Ink/Marks/Pen Pals = auto, Base/Ticket = base,
  the rest = insert); "A/B" athletes become multi cards. Sports in the Add a box dropdown follow the
  `order` list in `builder.py` (WWE, MLW, NFL, NBA, WNBA, EuroLeague, MLB, USA Baseball, MMA, ...).
- **Topps 2026 batch (Nov 22, 2026):** 97 products from the 2026 section of topps.com/pages/checklists were
  added and Chrome WWE was swapped to its official list (`build/breaks/topps_manifest_2026-11-22.py` lists
  each product, its Shopify file, sport group and team mode; `topps_batch_2026-11-22.py` is the run script,
  for reference only since it points at session paths). topps.com shows a bot check that the person has to
  click; the PDFs themselves on cdn.shopify.com download fine in the browser. 2026 Topps Update Series
  Baseball was skipped: its link on the Topps page returns 404.
- **Topps pack odds:** `build/breaks/odds_parse.py` reads the odds PDFs linked from topps.com/pages/odds
  (converted with `pdftotext -layout`, one `<product_id>.txt` each; links in `build/breaks/odds_sources.json`)
  and writes `build/breaks/odds.json` (packs per hit for each checklist set, 81 products, about 1,230 sets).
  `depth.py` then scores each set against the product's typical set of that kind: (odds / median) ^ 0.4,
  kept between 0.4 and 5. Not on the odds page yet: 2026 Topps Universe WWE (its link is broken), the 2026
  Chrome / Stadium Club / Cosmic WWE products and the Panini CSV products; those sets count as typical.
- **How it works guides:** the How it works tab has a "Section by section" guide (`#/how/boxes`, `spots`,
  `letters`, `points`, `pricing`, `results`) explaining every setting with examples. Each builder section has a
  "How this works" link to its guide, and each guide links back to its section (`#/build/at/<key>`).
- **Box search:** section 1 has a "Search boxes" field: any words in any order matched against product name,
  sport and plain sport words (football, wrestling, baseball...), newest years first. Click or Enter adds a box
  (again adds another); arrows move the highlight. The grouped dropdown below is "Or browse by sport".
- **Box types:** `odds_columns.py` (pdfplumber) reads every box-type column of each Topps odds PDF;
  `boxtypes_build.py` maps them to Hobby / Jumbo / Jumbo (HTA) / Breaker's Delight / First Day Issue / Sapphire /
  LogoFractor / Mega Box / Value Box / Hanger / Fat Pack (store exclusives and regional boxes dropped), keeps a
  product only if its columns check out against odds.json, and writes `boxtypes.json` (27 products; a hand fix for
  2026 Flagship Football's stacked headings). `depth.py` then writes `typedrows.json` (each player's sets plus each
  set's odds per type) and the browser scores the chosen box type; sets not in that box count 0. A picked box is
  `S.qty["<id>"]` (main type) or `S.qty["<id>@<type index>"]`, and prices are keyed the same way.
- **Leaf (Nov 22, 2026):** 49 products dated 2026 from leaftradingcards.com/releases (web-only singles skipped,
  5 upcoming ones had no checklist yet). Each product page links a Google Sheet (CSV export, read in the browser
  and shrunk to one line per set / name / card type) or an .xlsx; `build/breaks/leaf_convert.py` writes the
  library files into "Leaf ..." sport groups (Leaf is unlicensed, no team names) and adds print-run rarity to
  depth.json the same way as Panini. 2026 Leaf Metal Women of Sport is marked all women.
- **Store embed:** "Embed in your store" in the results gives a plain HTML table (spot, price, two per row, optional
  names list) and an iframe pointing at `/breaks/embed#<data>`. `breaks/embed.html` (copied from
  `build/breaks/embed_template.html` by builder.py) decodes the break from the hash (JSON, deflate-raw, base64url;
  prefix z, or j for uncompressed) and shows a searchable spot list, light or dark. Nothing is stored on the server.
- **Find a spot:** search box above the spot list filters to the spots holding a name or team (one or two
  letters match by letter range); the header search results link to `#/build/find/<name>`.
- **Acme Packs pages (Nov 23, 2026):** gb1037 (Midnight Chrome PYT), gb1038a (Full Case Absolute) and gb1038b (Midnight
  Chrome Inception) in `build/breaks/build.py`. Topps team data comes straight from the library checklists
  (`lib_team_product`), Absolute from the official Panini CSV (`absolute_2026.json`). Format "pyt" = pick your team with
  prices and open/sold. NIL letters go by first letter of the first name; college players already on an NFL roster in
  the Topps checklists go to that team (Acme's rule).
- **Break watcher and automatic pages (Nov 23, 2026):** `.github/workflows/break-watch.yml` runs `build/breaks/watch.py`
  every 15 minutes on GitHub (free, the repo is public). It reads the public Shopify product lists of Acme Packs (acme),
  JWJ (jwj), Colfax (colfax) and Run Good Life (rgl), plus their breaks collections, and commits to `build/breaks/watch/`
  only when a product is added or removed: `queue.json` (new or removed products with listing text, price options and
  dates), `images.json` (each product's title card image, shown on the Break guides cards by hub.py), `seen.json` (handles already known), `posts.json` and `stats.md` (when each breaker publishes). A scheduled
  Claude task ("Break page builder") works the queue; its runbook is the next item.
- **Breaks menu (Nov 24, 2026):** Daniel wants it short: All break guides, Spot builder, Main Event Card Vault (the shop at /) and Iron Ledger (/iron-ledger.html, his workout program). Individual breaks are listed only on the Break guides page; don't add them back to the menu. hub.py also puts a Release notes link at the bottom of every page it fills (footer_link, <!--RNLINK--> marker). Iron Ledger (iron-ledger.html) is a packed single-file app, so hub.py's fill_bundled() writes the menu as a slim bar (#mecv-bar) into its JSON template; if Iron Ledger is re-exported, rerun hub.py to put the bar back.
- **Break page builder runbook (for the scheduled task):**
  1. Start a fresh store check first, because GitHub often skips the timed runs: `gh api -X POST
     repos/dastardly-dan/maineventcardvault/actions/workflows/break-watch.yml/dispatches -f ref=main`, then wait (poll
     `git fetch` for up to 3 minutes) for the "Break watcher" commit if anything changed. Then `git pull --rebase` and
     read `build/breaks/watch/queue.json`. If it's empty and no listed break is more than 10 hours past
     its scheduled start, stop with no changes and no message.
  2. For each `added` item, decide whether it's a group break (break number like GB1039, JWJ #0248, CC875, RGL #6124, or
     the listing describes a group break). Skip merch, fees, giveaway winners and mystery packs. A "25% chance filler"
     listing isn't its own page: note it on the main break's page. If the break number or handle already has a page
     (search `build.py` and `breaks/cc874.html`), update what changed (title or renumbering, date, price) instead.
     Old listings (Daniel, Nov 23, 2026): if an added break's scheduled start is already more than 10 hours past when the run
     sees it, don't build a page; just remove it from the queue and mention it in the message.
  3. New break: add a config to `build/breaks/build.py` modeled on the closest existing one (gb1037 pick your team,
     jwj0246 pick your letter, gb1038b random team with combos, gb1038a NIL letters, cc872 random team, jwj0247 random
     letter). Spots come from the variant titles; prices from the variants; `format` pyl / pyt / team / random; add
     `live=dict(shop=..., handle=...)` for pyl and pyt. Use the breaker's house rules from the listing text and keep the
     breaker's own wording for dates. The id prefix picks the breaker's colors (gb, jwj, cc, rgl; ids like gb1040, jwj0249, cc876, rgl6128). Multi-sport breaks: CC874
     is the model.
  3b. Random breaks whose spot groupings aren't posted (Run Good Life sets team pairings and letter groups live): don't
     skip them. Build one spot per team or letter and say how many spots the breaker sells, like rgl6131, rgl6132
     (college cards in one "College (NIL) cards" spot) and rgl6133 (spots made from the letters that have names).
  3b2. Straight A to Z until the setup is known (Daniel, Nov 27, 2026): for a random-letter break whose real setup isn't known
     (Run Good Life sets letter groups live; Colfax tags that disagree with the listing's spot list), build one spot per
     letter A to Z plus a number spot with `cc_az()` in build.py, and say plainly on the page what the listing says (and
     the groups it lists, so they aren't lost). When the breaker confirms the setup or shows the board, update the spots
     to match, like rgl6141.
  3i. No guessed setups (Daniel, Nov 25, 2026, after a breaker raised concerns): build pages only from posted listings.
      Never post letter groupings, team pairings, formats, first-or-last-name rules or box lists before the breaker
      posts them. If a listing leaves something out, say plainly that the breaker hasn't posted it and point to the
      breaker; letter pages may sort by first name but must say the listing doesn't say which the breaker uses.
      No drafts: the old draft machinery in build.py has an empty list. Every break page shows "A guide, not a
      guarantee" (template.html). eBay asking prices are never shown on break pages (Daniel, Nov 25); they only
      feed the Spot Builder's Market prices setting (3g).
  3l. Stream check (Daniel, Nov 25, 2026): two scheduled tasks on Daniel's computer (:15 and :45) run
      `build/breaks/stream_gate.py`. While a stream is live they open one of our break pages, play the embedded stream,
      read the break number on RGL's overlay and close earlier breaks; when the stream ends they close that night's
      pages. Procedure: `build/breaks/stream_check.md`. Never click a robot check.
  3j. Streams (Daniel, Nov 25, 2026): when Daniel sends a breaker's YouTube link, add it to `STREAMS` in `build.py`
      with the page ids for that break night. Those pages show the YouTube player instead of the title card; the same
      link becomes the replay after the stream. Pages without a stream keep the title card.
  3o. Value per spot (Daniel, Nov 27, 2026): the Spot Builder shows each spot's share of the break's value (each name's
      odds-weighted points times its typical eBay asking price; unpriced names count at the typical price) once priced
      names hold half the points, and with pricing on, "by value" (the spot's price if the total were split by value;
      green above its price, red below). Builder only: break pages never show prices or values (Nov 25 rule stands).
  3p. Owner dashboard (Daniel, Nov 27, 2026): maineventcardvault.com/owner, for Daniel only. worker.js sends /owner to
      owner.js, which checks the OWNER_PASSWORD secret set in Cloudflare (Workers > maineventcardvault > Settings >
      Variables and Secrets) and keeps him signed in for 30 days with a signed cookie. Without the secret the page stays
      locked. The page is built by `build/breaks/owner.py` (run at the end of hub.py) into owner/dashboard.js;
      .assetsignore keeps owner/ and owner.js from being served as files. It shows value for cost per spot for every
      current break, price data status, and a Pulls section for the stream transcripts work that comes next. The repo is
      public, so the numbers behind it can be worked out from prices.json; the password protects the page, not the data.
  3n. Friday checks (Daniel, Nov 27, 2026): two scheduled tasks, "Friday check: all breakers" at 1:00 pm Eastern and
      "Friday check: JWJ" at 6:00 pm Eastern (CRON_TZ America/New_York, so they stay at 1 and 6 pm through daylight saving).
      They don't run the builder gate. Each starts a fresh store check, works the queue by `build/breaks/page_builder.md`
      and tells Daniel what's new, or that nothing is up. The Break guides page says so (hub.py intro).
  3k. Page builder timing (Daniel, Nov 25, 2026): the scheduled task fires every 5 minutes (at :03, :08, ...) on Sonnet and
      first runs `python3 build/breaks/builder_gate.py`. It works only when that prints RUN: during the first 4 hours of a
      breaker's stream (the watcher starts looking for the YouTube stream 2 hours before the first scheduled break and
      records the moment it goes live in `watch/streams.json`; only if it never finds the stream does the first
      scheduled break time stand in), from 1:03 to 1:45 pm Eastern on Tuesdays and Thursdays (Acme posts at 1 pm Eastern), and
      once every 30 minutes otherwise. Also from 6:03 to 6:45 pm Eastern on Fridays (JWJ posts at 6 pm Eastern), and from 10:03 to 10:45 am and 1:03 to
      1:45 pm Eastern on Tuesdays, Thursdays and Fridays (the usual drop days). Dated break nights and their posting
      times (the day before) go in `build/breaks/watch/schedule.json`; add new ones when Daniel sends a schedule. Weekly
      stream times: Colfax Sundays 5 pm and Tuesdays 6 pm Central, JWJ Mondays 8 pm Eastern (`WEEKLY` in `watch.py`);
      RGL's come from its listings. Channels: RGL @RunGoodLife, JML @THEJMLEXPERIENCE, Acme @AcmePacks, JWJ @JWJBreaks (Daniel, Nov 25), Colfax read from its homepage (@ColfaxCC). Procedure for
      each run: `build/breaks/page_builder.md`. On SKIP it ends with "No new breaks." and nothing else. The watcher runs every 5 minutes.
  3e. The watcher workflow now rebuilds the break pages and the Break guides page after every check, so new title card
      images show up without a builder run. A page picks up its breaker's title card from `images.json`
      as long as its `url` is the product link.
  3f. Panini breaks: tag the Kabooms (Daniel, Nov 24). `kabooms.json` holds every Kaboom subject and card team from the
      official Panini CSVs (Absolute Football, Donruss Elite Baseball so far); add new Panini products there and map the
      box key in `KABOOM_BOX`. `mark_kabooms` tags each name KABOOM only in the spot its Kaboom card goes to and adds a
      "Kabooms in this break" list to the rules.
  3g. eBay prices (Daniel, Nov 24): `build/breaks/prices.py` (workflow `break-prices.yml`, daily and on demand) looks up
      eBay Buy It Now asking prices through the Browse API for every "<product> <player>" in `watch/price_targets.json`
      (written by build.py for breaks that haven't run) and saves the median of raw single-card listings to
      `watch/prices.json`. Break pages do not show prices (changed Nov 25, 2026, after a breaker's concern). `builder.py`
      reads prices.json and embeds a whole-dollar price per name (`px`, matched to a checklist by the product name with box
      words removed, same as build.py's box_query) into builder.html; the Spot Builder's "Market prices" setting (Off by
      default; Light, Normal, Strong) uses it only as a boost: a name priced above the typical priced name in the chosen boxes
      gets (price / typical) ^ 0.25, 0.5 or 0.8 times its points, capped at 3x, and unpriced or cheaper names are left alone.
      The builder shows how many names have a price but never the prices. A price is refreshed every 14 days (KEEP_DAYS).
      Only products that appear in a built break page have targets so far, so other checklists have no prices yet.
      Needs repository secrets EBAY_CLIENT_ID and EBAY_CLIENT_SECRET. Market Movers is off limits: its terms ban scraping
      and reposting.
  3h. Past breaks (Daniel, Nov 24): closed breaks drop off the hub but are listed on `breaks/past.html` (hub.py), newest
      first by the date in `when`, with search, breaker and month filters. The footer link sits next to Release notes.
  3d. Early pages (Daniel, Nov 24): a break can be built from a title card before the listing is posted (gb1040 was).
      When the listing shows up, update that config (url, when, facts, real spots) instead of building a second page.
      Acme sometimes reuses an old link: GB1040 lives at gb1040-dual-year-football-finale-random-team.
  3c. Multi-sport boxes in a one-sport break (like the 2026 National Convention box in a WWE break): list only the
     featured sport's cards (Daniel, Nov 24). `nscc_product('WWE')` filters by `nscc_sports.json` (every name tagged
     WWE, NBA, NFL, MLB, Soccer, Star Wars or College from the official checklist's set names and teams); say so in
     the page notes.
  4. Checklists come only from `build/breaks/checklists/`. If a box isn't in the library, try the official list through
     WebFetch (Topps, Panini, checklistinsider); if a full official list can't be had, don't guess: skip that page and
     say what's needed in the message (the shell can't reach cdn.shopify.com, so Daniel may have to paste a link).
  5. `removed` items, or a break more than 10 hours past its scheduled start (Daniel, Nov 23, 2026): close it with `close(cfg, ran, facts)` (cc874 by
     hand, `ended='yes'` in hub.py). Never delete a page.
  6. Run `python3 build/breaks/build.py`, `builder.py` if checklists changed, `hub.py`, then `python3 build/build_site.py`
     so the storefront's Breaks menu matches. Add new break ids to `order` in hub.py.
  7. Add a line per change to `build/breaks/release_notes.json` (today's release; start a new one if the date changed),
     rerun hub.py.
  8. Remove handled items from queue.json; leave anything unresolved with a `note` field saying why. Commit, `git pull
     --rebase`, then `git -c push.negotiate=true push origin main`.
  9. Finish with a short message: new pages with their links, pages closed, anything Daniel needs to do.
  House style for page text: US dates (November 24, 2026), no em or en dashes, no arrows, plain friendly wording,
  spell out acronyms on first use. The shell can't reach the stores or maineventcardvault.com; queue.json has the
  listing data, and WebFetch works for anything else.
- **Breaker look (Nov 23, 2026):** break pages are white with the breaker's brand in the header band, the accent color
  (spot names, buttons, links) and a soft tint behind the title (`THEMES` and `LIGHT_CSS` in `build.py`, picked by id
  prefix: gb = Acme Packs green and gold, jwj = JWJ brown, cream and rust, cc = Colfax black, purple and red). The
  template's colors are CSS variables and `__THEME__` gets the override block. cc874.html carries the Colfax block by
  hand. Open and sold use readable green and red on white. The hub, builder and release notes keep the navy site look.
- **Release notes (Nov 23, 2026):** `build/breaks/release_notes.json` (newest first; tag New / Improved / Fixed; area
  Break guides / Spot Builder / Site). `hub.py` writes `breaks/release-notes.html` from it and links it in the Breaks
  menu and the hub footer. Add a line there with every change worth telling breakers about, then run hub.py.
- **Leave teams out (Nov 23, 2026):** builder team mode, for giveaway teams. `S.excl` holds the team names; `teamBins`
  drops them before grouping, so they're out of the spots and the pricing. Results show a "Left out" line; Copy, CSV,
  the HTML table and the iframe (`x` in the embed data) carry it too. Teams no longer in the picked boxes drop off the
  list.
- **Live open/sold status (Nov 23, 2026):** pick-your-team and pick-your-letter pages whose config has
  `live=dict(shop=..., handle=...)` (gb1037 and jwj0246 so far) refresh themselves. On load and about once a minute
  while the page is showing, the page asks `/api/break-status?shop=<shop>&handle=<product handle>`. The Worker
  (`breakstatus.js`) reads the store's public `/products/<handle>.js` feed (Shopify), keeps the answer at the edge for 60
  seconds, and returns every variant's title, price (cents) and `available`. The page matches variants to spots by
  title (`nk()` in the template drops punctuation and parentheses, and adds "men" or "women" from the spot's gender, so
  "T - Men (no the)" matches the T Men spot), updates open/sold and price, redraws, and shows a live count under the
  header. If the Worker or the store can't be reached, or the feed doesn't match at least half the spots, the status saved
  at build time stays on screen. Ended breaks never call it. To add a break: add `live=` to its config in `build.py`
  (shop keys are in `SHOPS` in `breakstatus.js`: acme, jwj, colfax) and rebuild. Variant titles must match the spot
  labels; check with the store's `.js` feed. The shell here can't reach the stores, so read the feed in a browser tab or
  WebFetch.
- **Breakninja lists (Nov 22, 2026):** when the maker hasn't posted a checklist, breakninja.com's card-by-card tables
  (name, number, set, print run, team) are scraped in the built-in browser, turned into a Panini-style CSV (multi-person
  sets regrouped, sketch cards dropped) and run through `panini_csv.py` and `depth.py --panini`, so print runs drive
  Player value. Fallback only: as of Nov 22 night every product is back on an official list (Topps PDFs, Panini
  CSVs, the Kakawow spreadsheet posted by GTS Distribution).
- **Panini print runs:** Panini publishes no pack odds. `depth.py --panini` reads each CSV's SEQUENCE column:
  per root set, each player's most plentiful version (unnumbered = 1,000 copies), median across players,
  scored like odds (fewer copies = rarer). Mass products (Donruss) are mostly unnumbered so little changes;
  high-end ones (Immaculate, Impeccable) spread out a lot.
- **Player value (hit depth):** `build/breaks/depth.py` counts, per product, how many different autograph,
  insert and multi-person sets each player is in (parallels folded into their root set) and writes
  `build/breaks/depth.json`; `builder.py` appends `[autoSets, insertSets, multiSets]` to rows where any is above 1.
  The builder's Player value setting scales auto/insert/multi points by count^0.5 (Normal, default) or
  count^0.8 (Strong). Rerun depth.py with the cards.json folder (and any Panini CSVs) when adding checklists.
- **Boxes UI:** the builder lists only the boxes picked for the break; everything else is in the grouped
  "Add a box" dropdown, so the library can grow without the panel getting longer.

## Iron Ledger and worker.js

- `iron-ledger.html` is Daniel's personal workout tracker, served at `/iron-ledger`.
  It isn't linked from the storefront and carries `noindex`, like `shoot/`. It's a
  self-contained bundle, so replace the whole file to update it.
- `worker.js` and `wrangler.jsonc` turned this from a static-only Worker into a Worker
  with static assets. Files are still served straight from the repo root without
  running any code; `worker.js` only runs for URLs that don't match a file, and the only
  things it handles are the Iron Ledger sync API at `/api/ironledger` and the live break
  status lookup at `/api/break-status` (`breakstatus.js`, listed in `.assetsignore` so it isn't
  served as a file); everything else falls through to the normal asset 404). The log lives in one Durable Object,
  `IronLedgerStore`, and is locked by a passphrase: the first device to connect sets it.
- `wrangler.jsonc` keeps the settings Cloudflare used to generate on its own during each
  build (name `maineventcardvault`, observability on, assets directory `.`). Keep
  `worker.js`, `wrangler.jsonc` and `.wrangler` in `.assetsignore` so they're never
  published as files.
