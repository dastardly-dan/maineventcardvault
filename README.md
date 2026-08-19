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
