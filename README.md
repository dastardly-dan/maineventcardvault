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
- **Find a spot:** search box above the spot list filters to the spots holding a name or team (one or two
  letters match by letter range); the header search results link to `#/build/find/<name>`.
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
  thing it handles is the Iron Ledger sync API at `/api/ironledger` (everything else
  falls through to the normal asset 404). The log lives in one Durable Object,
  `IronLedgerStore`, and is locked by a passphrase: the first device to connect sets it.
- `wrangler.jsonc` keeps the settings Cloudflare used to generate on its own during each
  build (name `maineventcardvault`, observability on, assets directory `.`). Keep
  `worker.js`, `wrangler.jsonc` and `.wrangler` in `.assetsignore` so they're never
  published as files.
