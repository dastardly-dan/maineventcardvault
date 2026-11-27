// The owner dashboard at /owner (Daniel, Nov 27, 2026): a private page only Daniel can open.
//
// The password lives in a Cloudflare secret named OWNER_PASSWORD (Workers > maineventcardvault > Settings >
// Variables and Secrets), never in this repository. Signing in sets a cookie that's good for 30 days; it's signed
// with the password, so changing the password signs every device out. The dashboard itself is built by
// build/breaks/owner.py into owner/dashboard.js, and .assetsignore keeps that folder from being served as a file.

import { DASHBOARD } from "./owner/dashboard.js";

export const OWNER = "/owner";
const COOKIE = "mecv_owner";
const DAYS = 30;
const HEAD = { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow",
  "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY", "X-Content-Type-Options": "nosniff" };
const enc = new TextEncoder();

async function hmac(key, msg) {
  const k = await crypto.subtle.importKey("raw", enc.encode(key), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return [...new Uint8Array(await crypto.subtle.sign("HMAC", k, enc.encode(msg)))].map((b) => b.toString(16).padStart(2, "0")).join("");
}
function same(a, b) {   // compares in the same time whatever the text, so timing doesn't give anything away
  if (a.length !== b.length) return false;
  let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
function cookie(request) {
  const m = (request.headers.get("Cookie") || "").match(new RegExp("(?:^|;\\s*)" + COOKIE + "=([^;]+)"));
  return m ? m[1] : "";
}
function page(title, inner, status) {
  return new Response(`<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>${title} | Main Event Card Vault</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#14202e;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#14202e}
.box{background:#fff;border-radius:14px;padding:26px;width:min(360px,92vw);box-shadow:0 10px 40px rgba(0,0,0,.3)}h1{font-size:20px;margin:0 0 6px}p{color:#46505c;margin:0 0 14px}
input{width:100%;padding:10px 12px;border:1px solid #cfc8b8;border-radius:10px;font:inherit;margin-bottom:10px;box-sizing:border-box}button{width:100%;padding:10px;border:0;border-radius:10px;background:#b8902c;color:#fff;font:inherit;font-weight:700;cursor:pointer}
.err{color:#b5543c;font-weight:600}</style></head><body><div class="box">${inner}</div></body></html>`, { status, headers: HEAD });
}
function login(msg) {
  return page("Sign in", `<h1>Owner dashboard</h1><p>${msg ? `<span class="err">${msg}</span>` : "This page is private."}</p>
<form method="post" action="${OWNER}"><input type="password" name="pw" autocomplete="current-password" placeholder="Password" autofocus required><button>Sign in</button></form>`, msg ? 401 : 200);
}

export async function owner(request, env) {
  const pw = env.OWNER_PASSWORD;
  if (!pw) return page("Not set up", "<h1>Not set up yet</h1><p>The password hasn't been added in Cloudflare yet, so this page stays locked.</p>", 503);
  const { pathname } = new URL(request.url);
  if (pathname === OWNER + "/logout") {
    return new Response(null, { status: 303, headers: { Location: OWNER, "Cache-Control": "no-store",
      "Set-Cookie": `${COOKIE}=; Path=${OWNER}; Max-Age=0; HttpOnly; Secure; SameSite=Strict` } });
  }
  if (request.method === "POST") {
    let given = "";
    try { given = String((await request.formData()).get("pw") || ""); } catch (e) {}
    if (given && same(await hmac("check", given), await hmac("check", pw))) {
      const exp = Date.now() + DAYS * 864e5, tok = exp + "." + (await hmac(pw, "owner|" + exp));
      return new Response(null, { status: 303, headers: { Location: OWNER, "Cache-Control": "no-store",
        "Set-Cookie": `${COOKIE}=${tok}; Path=${OWNER}; Max-Age=${DAYS * 86400}; HttpOnly; Secure; SameSite=Strict` } });
    }
    await new Promise((r) => setTimeout(r, 1500));   // slows down guessing
    return login("That password didn't work.");
  }
  const [exp, sig] = cookie(request).split(".");
  if (exp && sig && +exp > Date.now() && same(sig, await hmac(pw, "owner|" + exp))) {
    return new Response(DASHBOARD, { status: 200, headers: HEAD });
  }
  return login("");
}
