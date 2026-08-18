# Main Event Card Vault — Website

Static site for Main Event Card Vault LLC (WWE, Marvel, wrestling & sports trading cards).
Hosted on Cloudflare (Worker `maineventcardvault`), auto-deploys on every push to `main`.

- `index.html` — the storefront. Self-contained: CSS, JS and the card data are all inlined.
- `assets/logo.png`, `assets/favicon.png` — brand marks, referenced by the page.
- `listings.json` — the card feed, published for reference.
- `build/` — the generator. `raw_listings.tsv` in, `index.html` out.

## Refreshing the inventory

The storefront mirrors the **live active eBay listings** for seller `feld-111937`.
Card photos are hotlinked from `i.ebayimg.com`, so nothing needs downloading or hosting —
when a card sells and leaves the active list, it drops off the site.

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

Categories (WWE / Marvel / Baseball / Basketball / Football) and the badges
(Autograph, Numbered, Rookie, SSP, Refractor, Relic) are derived from listing titles
by keyword lists at the top of `build/build_site.py`. If a card lands in the wrong
bucket, edit those lists — never hand-edit `index.html`, it is generated.

## Note on image sizes

Use `s-l960` for thumbnails and `s-l1600` for the lightbox. eBay fits images inside the
requested box, so a portrait card at `s-l500` comes back only ~280–380px wide and looks soft.
