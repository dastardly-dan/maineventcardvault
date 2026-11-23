// Live open/sold status for the break guide pages.
//
// A break page asks /api/break-status?shop=<shop>&handle=<product handle>. This reads
// the store's public product feed (<shop>/products/<handle>.js, the same data the store's
// own buy buttons use) on the server side, so the browser never has to reach the store
// itself, and answers with every variant's title, price and whether it can still be bought.
//
// Answers are kept at the edge for 60 seconds, so no matter how many people have a page
// open, each break is looked up at most about once a minute.
//
// Only the shops listed below can be asked about, and only for /products/<handle>.js,
// so this can't be used to fetch anything else.

export const STATUS_API = "/api/break-status";
export const LIST_API = "/api/break-list";
const KEEP_SECONDS = 60;

const SHOPS = {
  acme: "https://acmepackscards.com",
  jwj: "https://jwjcollectorbreaks.com",
  colfax: "https://colfaxcc.com",
  rgl: "https://rungoodlife.com",
};

function reply(obj, status, cacheControl) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": cacheControl },
  });
}

// `cache` and `fetchFn` are parameters so the logic can be tested outside Cloudflare.
export async function breakStatus(request, ctx, cache = globalThis.caches && globalThis.caches.default, fetchFn = fetch) {
  if (request.method !== "GET") return reply({ error: "method" }, 405, "no-store");
  const url = new URL(request.url);
  const shop = url.searchParams.get("shop") || "";
  const handle = url.searchParams.get("handle") || "";
  const full = url.searchParams.get("full") === "1";
  const origin = Object.prototype.hasOwnProperty.call(SHOPS, shop) ? SHOPS[shop] : "";
  if (!origin || !/^[a-z0-9][a-z0-9-]{2,119}$/.test(handle)) return reply({ error: "bad_request" }, 400, "no-store");

  // One cache entry per break, whatever else is on the request.
  const key = new Request(url.origin + STATUS_API + "?shop=" + shop + "&handle=" + handle + (full ? "&full=1" : ""));
  if (cache) {
    const hit = await cache.match(key);
    if (hit) return hit;
  }

  let upstream;
  try {
    upstream = await fetchFn(origin + "/products/" + handle + ".js", {
      headers: { accept: "application/json", "user-agent": "MainEventCardVault/1.0 (+https://maineventcardvault.com)" },
    });
  } catch (e) {
    return reply({ error: "upstream_unreachable" }, 502, "no-store");
  }
  if (!upstream.ok) return reply({ error: "upstream_status", status: upstream.status }, 502, "no-store");

  let product;
  try { product = await upstream.json(); } catch (e) { return reply({ error: "upstream_not_json" }, 502, "no-store"); }
  if (!product || !Array.isArray(product.variants)) return reply({ error: "upstream_shape" }, 502, "no-store");

  const out = reply({
    shop,
    handle,
    title: String(product.title || ""),
    checked: new Date().toISOString(),
    ...(full ? { url: origin + "/products/" + handle, published_at: product.published_at || "", created_at: product.created_at || "", text: plain(product.description) } : {}),
    variants: product.variants.map((v) => ({
      title: String(v.title || v.option1 || ""),
      price: Number(v.price) || 0, // cents, as the store sends it
      available: !!v.available,
    })),
  }, 200, "public, max-age=" + KEEP_SECONDS);

  if (cache && ctx && ctx.waitUntil) ctx.waitUntil(cache.put(key, out.clone()));
  return out;
}

// HTML listing text to plain text, keeping line breaks, so a reader gets the break details.
function plain(html) {
  return String(html || "")
    .replace(/<\s*(br|\/p|\/div|\/li|\/h[1-6]|\/tr)\b[^>]*>/gi, "\n")
    .replace(/<li\b[^>]*>/gi, "- ")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&#39;|&rsquo;|&lsquo;/g, "'").replace(/&quot;|&ldquo;|&rdquo;/g, '"').replace(/&ndash;|&mdash;/g, "-")
    .replace(/[ \t]+/g, " ").replace(/\n\s*\n+/g, "\n").trim();
}

// Every product a store has published, newest first: /api/break-list?shop=<shop>[&page=N][&format=text]
// Used to spot new breaks. Kept 5 minutes at the edge. format=text gives one line per product:
// published (UTC) | handle | title | open variants / all variants | lowest price
export async function breakList(request, ctx, cache = globalThis.caches && globalThis.caches.default, fetchFn = fetch) {
  if (request.method !== "GET") return reply({ error: "method" }, 405, "no-store");
  const url = new URL(request.url);
  const shop = url.searchParams.get("shop") || "";
  const page = Math.max(1, Math.min(10, parseInt(url.searchParams.get("page") || "1", 10) || 1));
  const text = url.searchParams.get("format") === "text";
  const origin = Object.prototype.hasOwnProperty.call(SHOPS, shop) ? SHOPS[shop] : "";
  if (!origin) return reply({ error: "bad_request" }, 400, "no-store");
  const key = new Request(url.origin + LIST_API + "?shop=" + shop + "&page=" + page + (text ? "&format=text" : ""));
  if (cache) { const hit = await cache.match(key); if (hit) return hit; }
  let upstream;
  try {
    upstream = await fetchFn(origin + "/products.json?limit=250&page=" + page, {
      headers: { accept: "application/json", "user-agent": "MainEventCardVault/1.0 (+https://maineventcardvault.com)" },
    });
  } catch (e) { return reply({ error: "upstream_unreachable" }, 502, "no-store"); }
  if (!upstream.ok) return reply({ error: "upstream_status", status: upstream.status }, 502, "no-store");
  let data;
  try { data = await upstream.json(); } catch (e) { return reply({ error: "upstream_not_json" }, 502, "no-store"); }
  if (!data || !Array.isArray(data.products)) return reply({ error: "upstream_shape" }, 502, "no-store");
  const items = data.products.map((p) => {
    const vs = Array.isArray(p.variants) ? p.variants : [];
    const prices = vs.map((v) => Math.round(parseFloat(v.price) * 100)).filter((n) => n > 0);
    return {
      handle: String(p.handle || ""), title: String(p.title || ""), type: String(p.product_type || ""),
      tags: Array.isArray(p.tags) ? p.tags : String(p.tags || "").split(/,\s*/).filter(Boolean),
      published_at: p.published_at || "", created_at: p.created_at || "",
      variants: vs.length, open: vs.filter((v) => v.available).length, min_price: prices.length ? Math.min(...prices) : 0,
    };
  }).sort((a, b) => (b.published_at || "").localeCompare(a.published_at || ""));
  const checked = new Date().toISOString();
  const cc = "public, max-age=300";
  const out = text
    ? new Response(["# " + shop + " " + origin + " page " + page + ", " + items.length + " products, checked " + checked,
        ...items.map((i) => [i.published_at, i.handle, i.title, i.open + "/" + i.variants + " open", "$" + (i.min_price / 100).toFixed(2)].join(" | "))].join("\n"),
        { status: 200, headers: { "content-type": "text/plain; charset=utf-8", "cache-control": cc } })
    : reply({ shop, origin, page, checked, products: items }, 200, cc);
  if (cache && ctx && ctx.waitUntil) ctx.waitUntil(cache.put(key, out.clone()));
  return out;
}
