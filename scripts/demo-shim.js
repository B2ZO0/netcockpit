// Online demo (GitHub Pages): answers the interface's API calls from recorded files.
// Recorded from demo/demo.py: a simulated network with fictitious names and addresses.
(function () {
  const realFetch = window.fetch.bind(window);
  let meta = null;
  const metaReady = realFetch("data/meta.json").then((r) => r.json()).then((m) => { meta = m; }).catch(() => { meta = { snapshot: 0 }; });

  function fnv(s) {
    let h = 0x811c9dc5;
    for (const b of new TextEncoder().encode(s)) { h ^= b; h = Math.imul(h, 0x01000193) >>> 0; }
    return h.toString(16).padStart(8, "0");
  }
  // shifts recorded dates so the demo always looks "live"
  function shift(v, off, lo, hi) {
    if (typeof v === "number") return v > lo && v < hi ? v + off : v;
    if (Array.isArray(v)) return v.map((x) => shift(x, off, lo, hi));
    if (v && typeof v === "object") { const o = {}; for (const k in v) o[k] = shift(v[k], off, lo, hi); return o; }
    return v;
  }
  const json = (obj, status) => new Response(JSON.stringify(obj), { status: status || 200, headers: { "content-type": "application/json" } });

  window.fetch = async function (input, opts) {
    const raw = typeof input === "string" ? input : input.url;
    const u = new URL(raw, location.href);
    const i = u.pathname.indexOf("/api/");
    if (i < 0 || u.origin !== location.origin || u.pathname.endsWith(".csv")) return realFetch(input, opts);
    const name = u.pathname.slice(i + 5);
    if (name === "rescan") return json({ ok: true }, 202);
    let lang = "";
    if (opts && opts.body) { try { lang = JSON.parse(opts.body).lang || ""; } catch (e) { /* ignore */ } }
    const site = name.startsWith("ai/") ? "" : (u.searchParams.get("site") || "");
    const id = u.searchParams.get("id") || "";
    await metaReady;
    const r = await realFetch(`data/${fnv(`${name}|${site}|${id}|${name.startsWith("ai/") ? lang : ""}`)}.json`);
    if (!r.ok) return json({ error: "not in the online demo" }, 404);
    const snap = meta.snapshot || 0;
    const off = snap ? Date.now() / 1000 - snap : 0;
    return json(shift(await r.json(), off, snap - 40 * 86400, snap + 2 * 86400));
  };

  // banner: this is a demo, here is how to install it
  document.addEventListener("DOMContentLoaded", () => {
    const fr = (window.I18n && window.I18n.lang ? window.I18n.lang : navigator.language || "").startsWith("fr");
    const b = document.createElement("a");
    b.href = "https://github.com/B2ZO0/netcockpit";
    b.target = "_blank"; b.rel = "noopener";
    b.textContent = fr ? "Démo en ligne · réseau simulé  —  Installer NetCockpit ★ GitHub"
                       : "Live demo · simulated network  —  Get NetCockpit ★ GitHub";
    b.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:9999;padding:8px 14px;border-radius:999px;" +
      "background:linear-gradient(90deg,#7c3aed,#c026d3);color:#fff;font:600 13px/1.2 system-ui,sans-serif;" +
      "text-decoration:none;box-shadow:0 6px 20px rgba(124,58,237,.35)";
    document.body.appendChild(b);
  });
})();
