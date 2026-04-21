/**
 * Cloudflare Worker giriş noktası (wrangler.toml main).
 * D1: env.DB — [[d1_databases]] binding = "DB"
 */

/** Fiyatları D1'den çeker (pricing_plans). */
async function getPricing(env) {
  if (!env.DB) return [];
  const { results } = await env.DB.prepare(
    "SELECT * FROM pricing_plans ORDER BY price_usd ASC"
  ).all();
  return results ?? [];
}

async function readIyzicoToken(request) {
  const ct = (request.headers.get("content-type") || "").toLowerCase();
  if (ct.includes("application/x-www-form-urlencoded")) {
    const text = await request.text();
    return new URLSearchParams(text).get("token") || "";
  }
  if (ct.includes("multipart/form-data")) {
    const form = await request.formData();
    return String(form.get("token") || "");
  }
  if (ct.includes("application/json")) {
    try {
      const j = await request.json();
      return String(j.token || "");
    } catch {
      return "";
    }
  }
  const text = await request.text();
  return new URLSearchParams(text).get("token") || "";
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/health") {
      return Response.json({ ok: true, service: "dressifye" });
    }

    const pathNorm = url.pathname.replace(/\/+$/, "") || "/";

    const jsonCorsHeaders = {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
    };

    if (pathNorm === "/api/pricing") {
      if (request.method === "OPTIONS") {
        return new Response(null, {
          status: 204,
          headers: {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "86400",
          },
        });
      }
      if (request.method !== "GET") {
        return new Response(JSON.stringify({ error: "Method not allowed" }), {
          status: 405,
          headers: jsonCorsHeaders,
        });
      }
      if (!env.DB) {
        return new Response(JSON.stringify([]), { headers: jsonCorsHeaders });
      }
      try {
        const results = await getPricing(env);
        return new Response(JSON.stringify(results), {
          headers: jsonCorsHeaders,
        });
      } catch (err) {
        const msg = err && err.message ? err.message : String(err);
        return new Response(JSON.stringify({ error: msg }), {
          status: 500,
          headers: jsonCorsHeaders,
        });
      }
    }

    if (pathNorm === "/odeme/abonelik-callback" && request.method === "POST") {
      const base = (env.GARMENT_CORE_API_URL || "").replace(/\/+$/, "");
      if (!base) {
        return new Response("Worker: GARMENT_CORE_API_URL tanımlı değil", {
          status: 500,
        });
      }
      const token = await readIyzicoToken(request);
      if (!token) {
        return new Response("token eksik", { status: 400 });
      }
      const cb = new URL(
        "/api/v1/payments/dressifye/subscription/callback/",
        base + "/"
      );
      const upstream = await fetch(cb.toString(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
      if (!upstream.ok) {
        return new Response(await upstream.text(), { status: 502 });
      }
      return Response.redirect(
        new URL("/odeme/basarili/?subscription=1", request.url).toString(),
        302
      );
    }

    if (env.ASSETS) {
      return env.ASSETS.fetch(request);
    }
    return new Response("Dressifye Worker — ASSETS binding yok.", {
      status: 503,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  },
};
