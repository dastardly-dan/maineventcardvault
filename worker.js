// Main Event Card Vault Worker.
//
// Everything in the repo that isn't listed in .assetsignore is a static asset, and
// Cloudflare serves those directly without running this file: the storefront,
// ratings.html, the Shoot tool, iron-ledger.html and so on. This code only runs
// for requests that don't match a file, and the only thing it handles itself is
// the Iron Ledger sync API at /api/ironledger and the live open/sold lookup for the
// break guides at /api/break-status (breakstatus.js). Anything else goes back to the
// asset handler, so 404s behave exactly as they did before.

import { DurableObject } from "cloudflare:workers";
import { breakStatus, STATUS_API } from "./breakstatus.js";

const API = "/api/ironledger";
const MAX_BODY = 1_000_000;          // a few years of workouts is well under this
const MAX_FAILS = 10;                // wrong passphrases allowed per window
const FAIL_WINDOW_MS = 15 * 60 * 1000;

export default {
  async fetch(request, env, ctx) {
    const { pathname } = new URL(request.url);
    if (pathname === STATUS_API) return breakStatus(request, ctx);
    if (pathname === API || pathname.startsWith(API + "/")) {
      // One store for one person: every request goes to the same Durable Object,
      // which keeps reads and writes in order (no stale reads between devices).
      const store = env.IRONLEDGER.get(env.IRONLEDGER.idFromName("main"));
      return store.fetch(request);
    }
    return env.ASSETS.fetch(request);
  },
};

export class IronLedgerStore extends DurableObject {
  async fetch(request) {
    const { pathname } = new URL(request.url);
    const method = request.method;
    const keyHash = await this.ctx.storage.get("keyHash");

    // Lets a new device know whether to say "pick a passphrase" or "enter yours".
    if (pathname === API + "/status" && method === "GET") {
      return json({ claimed: !!keyHash });
    }
    if (pathname !== API) return json({ error: "not_found" }, 404);
    if (method !== "GET" && method !== "PUT") return json({ error: "method" }, 405);

    const locked = await this.lockedFor();
    if (locked) return json({ error: "locked", retryInSeconds: Math.ceil(locked / 1000) }, 429);

    const token = request.headers.get("X-IronLedger-Key") || "";
    if (!/^[0-9a-f]{64}$/.test(token)) return json({ error: "no_key" }, 401);
    const tokenHash = await sha256(token);

    if (keyHash && !sameText(keyHash, tokenHash)) {
      await this.noteFailure();
      return json({ error: "wrong_key" }, 401);
    }

    if (method === "GET") {
      if (!keyHash) return json({ error: "unclaimed" }, 404);
      return json(await this.readDoc());
    }

    // PUT: merge what this device has with what's stored, save, send the result back.
    const raw = await request.text();
    if (raw.length > MAX_BODY) return json({ error: "too_big" }, 413);
    let body;
    try { body = JSON.parse(raw); } catch (e) { return json({ error: "bad_json" }, 400); }

    if (!keyHash) await this.ctx.storage.put("keyHash", tokenHash); // first device claims the log
    const current = await this.readDoc();
    const data = merge(current.data, body && body.data);
    const doc = { data, rev: current.rev + 1, savedAt: Date.now() };
    await this.ctx.storage.put("doc", doc);
    await this.ctx.storage.delete("fails");
    return json(doc);
  }

  async readDoc() {
    return (await this.ctx.storage.get("doc")) || { data: merge({}, {}), rev: 0, savedAt: 0 };
  }

  async lockedFor() {
    const f = await this.ctx.storage.get("fails");
    if (!f || f.count < MAX_FAILS) return 0;
    const left = f.since + FAIL_WINDOW_MS - Date.now();
    return left > 0 ? left : 0;
  }

  async noteFailure() {
    const now = Date.now();
    let f = await this.ctx.storage.get("fails");
    if (!f || now - f.since > FAIL_WINDOW_MS) f = { count: 0, since: now };
    f.count += 1;
    await this.ctx.storage.put("fails", f);
  }
}

// Same merge the page runs. Logged sessions are never edited after they're saved,
// so history is a union by id (minus anything deleted on any device). Plan weights
// are per workout, and the most recently finished session for that workout wins.
export function merge(a, b) {
  a = clean(a);
  b = clean(b);
  const deleted = [...new Set([...a.deleted, ...b.deleted])];
  const gone = new Set(deleted);
  const byId = new Map();
  for (const h of [...a.history, ...b.history]) {
    if (!gone.has(h.id) && !byId.has(h.id)) byId.set(h.id, h);
  }
  const history = [...byId.values()].sort((x, y) => (Number(y.at) || 0) - (Number(x.at) || 0));
  const plan = {};
  const planAt = {};
  for (const id of new Set([...Object.keys(a.plan), ...Object.keys(b.plan)])) {
    const ta = Number(a.planAt[id]) || 0;
    const tb = Number(b.planAt[id]) || 0;
    const useB = !(id in a.plan) || ((id in b.plan) && tb >= ta);
    plan[id] = useB ? b.plan[id] : a.plan[id];
    planAt[id] = Math.max(ta, tb);
  }
  return { history, deleted, plan, planAt };
}

function clean(d) {
  const o = d && typeof d === "object" ? d : {};
  const obj = (v) => (v && typeof v === "object" && !Array.isArray(v) ? v : {});
  return {
    history: Array.isArray(o.history) ? o.history.filter((h) => h && typeof h.id === "string") : [],
    deleted: Array.isArray(o.deleted) ? o.deleted.filter((x) => typeof x === "string") : [],
    plan: obj(o.plan),
    planAt: obj(o.planAt),
  };
}

async function sha256(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((x) => x.toString(16).padStart(2, "0")).join("");
}

function sameText(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}
