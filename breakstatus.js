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
const KEEP_SECONDS = 60;

const SHOPS = {
  acme: "https://acmepackscards.com",
  jwj: "https://jwjcollectorbreaks.com",
  colfax: "https://colfaxcc.com",
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
  const origin = Object.prototype.hasOwnProperty.call(SHOPS, shop) ? SHOPS[shop] : "";
  if (!origin || !/^[a-z0-9][a-z0-9-]{2,119}$/.test(handle)) return reply({ error: "bad_request" }, 400, "no-store");

  // One cache entry per break, whatever else is on the request.
  const key = new Request(url.origin + STATUS_API + "?shop=" + shop + "&handle=" + handle);
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
    variants: product.variants.map((v) => ({
      title: String(v.title || v.option1 || ""),
      price: Number(v.price) || 0, // cents, as the store sends it
      available: !!v.available,
    })),
  }, 200, "public, max-age=" + KEEP_SECONDS);

  if (cache && ctx && ctx.waitUntil) ctx.waitUntil(cache.put(key, out.clone()));
  return out;
}
