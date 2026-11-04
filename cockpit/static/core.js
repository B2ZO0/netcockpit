/* NetCockpit : socle (thème, langue, API, navigation, composants, fiche équipement, IA) */
"use strict";
const App = (() => {
  const ICONS = {
    dashboard: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    network: '<rect x="9" y="2" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="16" y="16" width="6" height="6" rx="1"/><path d="M5 16v-3h14v3M12 8v5"/>',
    layers: '<path d="M12 2 2 7l10 5 10-5-10-5z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>',
    switch: '<rect x="2" y="7" width="20" height="10" rx="2"/><path d="M6 12h.01M10 12h.01M14 12h.01M18 12h.01"/>',
    list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    globe: '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20z"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    sparkle: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
    server: '<rect x="3" y="3" width="18" height="7" rx="2"/><rect x="3" y="14" width="18" height="7" rx="2"/><path d="M7 6.5h.01M7 17.5h.01"/>',
    vm: '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12h6M12 9v6"/>',
    router: '<circle cx="12" cy="12" r="9"/><path d="m8 10 4-4 4 4M12 6v12M8 14l4 4 4-4"/>',
    cloud: '<path d="M17.5 19H8a6 6 0 1 1 1.2-11.9A5 5 0 0 1 19 9.5a4.5 4.5 0 0 1-1.5 9.5z"/>',
    database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    printer: '<path d="M6 9V2h12v7"/><rect x="2" y="9" width="20" height="9" rx="2"/><rect x="6" y="14" width="12" height="8"/>',
    windows: '<rect x="3" y="3" width="8" height="8"/><rect x="13" y="3" width="8" height="8"/><rect x="3" y="13" width="8" height="8"/><rect x="13" y="13" width="8" height="8"/>',
    terminal: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m6 9 3 3-3 3M12 15h5"/>',
    camera: '<path d="m23 7-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/>',
    phone: '<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M10 6h4M9 11h.01M12 11h.01M15 11h.01M9 14h.01M12 14h.01M15 14h.01M9 17h.01M12 17h.01M15 17h.01"/>',
    monitor: '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
    wifi: '<path d="M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0M2 9a15 15 0 0 1 20 0M12 20h.01"/>',
    key: '<rect x="3" y="3" width="18" height="7" rx="2"/><rect x="3" y="14" width="18" height="7" rx="2"/><circle cx="16" cy="17.5" r="1.6"/><path d="M7 6.5h.01M7 17.5h.01"/>',
    building: '<rect x="4" y="2" width="16" height="20" rx="1.5"/><path d="M9 22v-4h6v4M8 6h.01M12 6h.01M16 6h.01M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M16 14h.01"/>',
    mobile: '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
    group: '<circle cx="8" cy="8" r="3"/><circle cx="16" cy="8" r="3"/><circle cx="8" cy="16" r="3"/><circle cx="16" cy="16" r="3"/>',
    alert: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
    check: '<path d="M20 6 9 17l-5-5"/>', clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><path d="M21 3v5h-5"/>',
    moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
  };
  const ROLE_ICON = { server: "server", dc: "key", vm: "vm", esxi: "layers", hypervisor: "layers", switch: "switch", network: "switch",
    firewall: "shield", router: "router", gateway: "router", internet: "globe", isp: "cloud", nas: "database", printer: "printer",
    windows: "windows", linux: "terminal", camera: "camera", phone: "phone", wifi: "wifi", subnet: "network", site: "building",
    device: "monitor", other: "monitor", mobile: "mobile", group: "group" };

  // ------------------------------------------------------------ couleurs : lues dans le thème CSS actif
  const TOKENS = ["bg", "surface", "raised", "sunken", "line", "line2", "text", "muted", "dim", "violet", "magenta",
    "up", "warning", "critical", "down", "off", "absent", "unknown", "info", "net"];
  const COLORS = {};
  function readColors() {
    const cs = getComputedStyle(document.documentElement);
    TOKENS.forEach((k) => { COLORS[k] = cs.getPropertyValue(`--${k}`).trim(); });
  }
  readColors();
  const LABELS = new Proxy({}, { get: (o, k) => t(`status.${String(k)}`) });

  const svg = (k, stroke = "currentColor", w = 1.8) =>
    `<svg viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round">${ICONS[k] || ICONS.monitor}</svg>`;
  const icon = (k) => `<i data-icon="${k}">${svg(k)}</i>`;
  const roleIcon = (role) => icon(ROLE_ICON[role] || "monitor");
  const iconUri = (role, stroke) => "data:image/svg+xml;utf8," + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="${stroke || COLORS.text}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${ICONS[ROLE_ICON[role] || role] || ICONS.monitor}</svg>`);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const roleLabel = (n) => I18n.role(n.role, n.role_label);
  const nm = (s) => I18n.name(s);

  function hydrateIcons(root = document) { $$("i[data-icon]:empty", root).forEach((el) => { el.innerHTML = svg(el.dataset.icon); }); }

  const store = {
    get(k, d) { try { const v = localStorage.getItem("cockpit." + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem("cockpit." + k, JSON.stringify(v)); } catch (e) { /* stockage indisponible */ } },
  };

  // ------------------------------------------------------------ formats
  const fmt = {
    pct: (v) => (v == null ? "—" : I18n.lang === "fr" ? `${Math.round(v)} %` : `${Math.round(v)}%`),
    ms: (v) => (v == null ? "—" : v < 10 ? `${v.toFixed(1)} ms` : `${Math.round(v)} ms`),
    ago(ts) {
      if (!ts) return "—";
      const s = Math.max(0, Date.now() / 1000 - ts);
      if (s < 60) return t("time.now");
      if (s < 3600) return t("time.min", { n: Math.round(s / 60) });
      if (s < 86400) return t("time.h", { h: Math.floor(s / 3600), m: String(Math.round((s % 3600) / 60)).padStart(2, "0") });
      return t("time.d", { n: Math.round(s / 86400) });
    },
    time: (ts) => (ts ? new Date(ts * 1000).toLocaleTimeString(I18n.locale, { hour: "2-digit", minute: "2-digit" }) : "—"),
    dt: (ts) => (ts ? new Date(ts * 1000).toLocaleString(I18n.locale, { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—"),
    dur(s) {
      if (s == null) return "—";
      const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600);
      return d ? t("dur.dh", { d, h }) : t("dur.hm", { h, m: Math.floor((s % 3600) / 60) });
    },
    bps(v) {
      if (v == null) return "—";
      const u = ["b/s", "kb/s", "Mb/s", "Gb/s"]; let i = 0;
      while (v >= 1000 && i < u.length - 1) { v /= 1000; i++; }
      return `${v.toFixed(v < 10 ? 1 : 0)} ${u[i]}`;
    },
    gb: (v) => (v == null ? "—" : v >= 1024 ? `${(v / 1024).toFixed(1)} ${t("unit.tb")}` : `${Math.round(v)} ${t("unit.gb")}`),
  };
  const pctColor = (v, warn = 80, crit = 90) => (v == null ? "var(--line2)" : v >= crit ? "var(--down)" : v >= warn ? "var(--warning)" : "var(--up)");
  const bar = (v, warn, crit) => `<div class="bar"><span style="width:${Math.min(100, Math.max(0, v || 0))}%;background:${pctColor(v, warn, crit)}"></span></div>`;
  const meter = (k, v, warn, crit) => `<div class="meter"><span class="k">${k}</span>${bar(v, warn, crit)}<span class="v">${fmt.pct(v)}</span></div>`;
  const lamp = (s) => `<span class="lamp ${esc(s)}"></span>`;
  const statusBadge = (s) => `<span class="badge b-${esc(s)}">${lamp(s)}${LABELS[s]}</span>`;
  const sevBadge = (s) => `<span class="badge b-${esc(s)}">${t(`sev.${s}`)}</span>`;
  const segBar = (parts) => `<div class="seg-bar">${parts.filter((p) => p.v > 0).map((p) => `<span style="flex:${p.v};background:${p.c}"></span>`).join("")}</div>`;

  function spark(points, { w = 120, h = 34, color = "var(--magenta)" } = {}) {
    if (!points || points.length < 2) return "";
    const ys = points.map((p) => p[1]); const min = Math.min(...ys), max = Math.max(...ys); const span = max - min || 1;
    const pts = points.map((p, i) => `${((i / (points.length - 1)) * w).toFixed(1)},${(h - 3 - ((p[1] - min) / span) * (h - 6)).toFixed(1)}`);
    return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${pts.join(" ")}" fill="none" style="stroke:${color}" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
  }

  function areaChart(points, { unit = "", color = "var(--magenta)", max = null } = {}) {
    if (!points || points.length < 2) return `<div class="muted">${t("chart.none")}</div>`;
    const w = 400, h = 80; const ys = points.map((p) => p[1]);
    const hi = max ?? (Math.max(...ys) * 1.15 || 1);
    const pts = points.map((p, i) => `${((i / (points.length - 1)) * w).toFixed(1)},${(h - (p[1] / hi) * h).toFixed(1)}`);
    const last = ys[ys.length - 1], avg = ys.reduce((a, b) => a + b, 0) / ys.length, mx = Math.max(...ys);
    const f = (v) => (unit === "ms" ? fmt.ms(v) : unit === "%" ? fmt.pct(v) : v.toFixed(1));
    return `<svg class="chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><path d="M0,${h} L${pts.join(" L")} L${w},${h} Z" style="fill:${color};fill-opacity:.14"/><polyline points="${pts.join(" ")}" fill="none" style="stroke:${color}" stroke-width="1.5" vector-effect="non-scaling-stroke"/></svg>
      <div class="chart-legend"><span>${t("chart.legend", { c: `<b style="color:var(--text)">${f(last)}</b>`, a: f(avg), m: f(mx) })}</span><span style="margin-left:auto">${t("chart.span")}</span></div>`;
  }

  function md(text) {
    const lines = esc(text || "").split("\n"); let html = "", list = null;
    const inline = (s) => s.replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/\*([^*]+)\*/g, "<i>$1</i>");
    const close = () => { if (list) { html += `</${list}>`; list = null; } };
    for (const raw of lines) {
      const l = raw.trimEnd();
      if (/^#{1,4}\s/.test(l)) { close(); html += `<h3>${inline(l.replace(/^#+\s/, ""))}</h3>`; }
      else if (/^\s*[-*]\s/.test(l)) { if (list !== "ul") { close(); html += "<ul>"; list = "ul"; } html += `<li>${inline(l.replace(/^\s*[-*]\s/, ""))}</li>`; }
      else if (/^\s*\d+[.)]\s/.test(l)) { if (list !== "ol") { close(); html += "<ol>"; list = "ol"; } html += `<li>${inline(l.replace(/^\s*\d+[.)]\s/, ""))}</li>`; }
      else if (!l.trim() || /^```/.test(l)) { close(); }
      else { close(); html += `<p>${inline(l)}</p>`; }
    }
    close(); return html;
  }

  // ------------------------------------------------------------ API
  async function api(path, opts) {
    const sep = path.includes("?") ? "&" : "?";
    const site = state.site && !/[?&]site=/.test(path) && !path.startsWith("api/node") && !path.startsWith("api/ai") ? `${sep}site=${encodeURIComponent(state.site)}` : "";
    const r = await fetch(path + site, Object.assign({ cache: "no-store" }, opts || {}));
    if (!r.ok) throw new Error(`${r.status}`);
    return r.json();
  }
  const post = (path, body) => api(path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body || {}) });

  // ------------------------------------------------------------ navigation
  const state = { site: store.get("site", ""), view: "overview", features: null, timer: null };
  const views = {};
  const title = (v) => (v === "vmware" ? t("title.vmware") : t(`nav.${v}`));

  function register(name, impl) { views[name] = impl; }

  async function route() {
    const name = (location.hash.replace(/^#\//, "").split("?")[0]) || "overview";
    const v = views[name] ? name : "overview";
    if (state.current && state.current.leave) state.current.leave();
    state.view = v; state.current = views[v];
    $$("#nav a").forEach((a) => { a.classList.toggle("active", a.dataset.view === v); a.toggleAttribute("aria-current", a.dataset.view === v); });
    $("#page-title").textContent = title(v);
    $("#page-sub").textContent = "";
    const el = $("#view"); el.className = views[v].full ? "full" : ""; el.innerHTML = `<div class="loading"><span class="spinner"></span>${t("loading")}</div>`;
    await refresh(true);
  }

  async function refresh(first) {
    try {
      if (state.current) await state.current.render($("#view"), first);
      $("#live-dot").classList.remove("stale"); $("#live-txt").textContent = t("top.live");
    } catch (e) {
      console.error(e);
      $("#live-dot").classList.add("stale"); $("#live-txt").textContent = t("top.lost");
    }
    hydrateIcons();
  }

  // textes fixes de l'interface (relancé à chaque changement de langue)
  function chrome() {
    $$("#nav a").forEach((a) => { a.dataset.tip = title(a.dataset.view); a.setAttribute("aria-label", title(a.dataset.view)); });
    const day = document.documentElement.dataset.theme === "day";
    const tips = { "btn-sources": t("rail.sources"), "btn-rescan": t("rail.rescan"), "btn-theme": t(day ? "rail.toNight" : "rail.toDay"), "btn-lang": t("rail.toLang") };
    Object.entries(tips).forEach(([id, txt]) => { const b = $(`#${id}`); b.dataset.tip = txt; b.setAttribute("aria-label", txt); });
    $("#btn-theme").innerHTML = icon(day ? "moon" : "sun");
    $("#btn-lang").textContent = I18n.lang === "fr" ? "EN" : "FR";
    $("#search").placeholder = t("top.search");
    $("#btn-ai-txt").textContent = t("top.ai");
    $("#sources-title").textContent = t("rail.sources");
    $("#drawer-close").setAttribute("aria-label", t("close")); $("#modal-close").setAttribute("aria-label", t("close"));
    $("#live-txt").textContent = t("top.live");
    if (state.features) setFeatures(state.features, true);
  }

  function setFeatures(f, force) {
    if (!f) return;
    state.features = f;
    const seg = $("#site-seg");
    const sites = ["", ...(f.sites || [])];
    const key = sites.join("|") + I18n.lang;
    if (force || seg.dataset.sites !== key) {
      seg.dataset.sites = key;
      seg.innerHTML = sites.map((s) => `<button data-site="${esc(s)}">${s ? esc(s) : t("top.allSites")}</button>`).join("");
      $$("button", seg).forEach((b) => b.addEventListener("click", () => { state.site = b.dataset.site; store.set("site", state.site); markSite(); refresh(true); }));
    }
    markSite();
    const src = [["Prometheus", true, true], [t("src.scan"), true, true],
      ["vCenter", f.vcenter && f.vcenter.up, !!f.vcenter], ["Zabbix", f.zabbix && f.zabbix.up, !!f.zabbix],
      ["SNMP", f.snmp, f.snmp], [t("src.ai"), !!f.ai, !!f.ai]];
    $("#sources").innerHTML = src.map(([n, ok, on]) => `<div>${lamp(!on ? "off" : ok ? "up" : "down")}<span>${esc(n)}</span><span>${t(on ? (ok ? "src.connected" : "src.error") : "src.off")}</span></div>`).join("");
    const broken = src.some(([, ok, on]) => on && !ok);
    $("#src-lamp").className = `lamp ${broken ? "warning" : "up"}`;
    $("#scan-info").textContent = f.scanning ? t("scan.running") : t("scan.last", { t: fmt.time(f.last_scan) });
    const ext = [];
    if (f.grafana_url) ext.push(`<a href="${esc(f.grafana_url)}" target="_blank" rel="noopener">Grafana</a>`);
    if (f.zabbix && f.zabbix.url) ext.push(`<a href="${esc(f.zabbix.url)}" target="_blank" rel="noopener">Zabbix</a>`);
    if (f.alertmanager_url) ext.push(`<a href="${esc(f.alertmanager_url)}" target="_blank" rel="noopener">Alertmanager</a>`);
    $("#ext-links").innerHTML = ext.join("");
    $("#ext-links").classList.toggle("hidden", !ext.length);
    $("#btn-ai").classList.toggle("hidden", !f.ai);
  }
  function markSite() { $$("#site-seg button").forEach((b) => b.classList.toggle("on", b.dataset.site === (state.site || ""))); }

  function setAlertCount(c) {
    const el = $("#nav-alerts"); const n = (c.critical || 0) + (c.warning || 0);
    el.textContent = n; el.classList.toggle("hidden", !n); el.classList.toggle("warn", !c.critical);
    document.title = (c.critical ? `(${c.critical}) ` : "") + "NetCockpit";
  }

  let toastT;
  function toast(msg) { const el = $("#toast"); el.textContent = msg; el.classList.remove("hidden"); clearTimeout(toastT); toastT = setTimeout(() => el.classList.add("hidden"), 2600); }

  // ------------------------------------------------------------ fiche équipement
  let drawerId = null;
  async function openNode(id) {
    if (!id) return;
    drawerId = id;
    $("#drawer").classList.remove("hidden");
    $("#drawer-body").innerHTML = '<span class="spinner"></span>';
    let n;
    try { n = await api(`api/node?id=${encodeURIComponent(id)}`); } catch (e) { $("#drawer-body").innerHTML = t("d.notFound"); return; }
    if (drawerId !== id) return;
    const rows = [];
    const add = (k, v) => { if (v != null && v !== "" && !(Array.isArray(v) && !v.length)) rows.push(`<div>${t(k)}</div><div>${v}</div>`); };
    add("d.ip", n.ip ? `<span class="mono">${esc(n.ip)}</span>` : null);
    add("d.dns", esc(n.details && n.details.fqdn || n.dns));
    add("d.netbios", esc(n.netbios));
    add("d.mac", n.mac ? `<span class="mono">${esc(n.mac)}</span>` : null);
    add("d.vendor", esc(n.vendor));
    add("d.type", esc(roleLabel(n)));
    add("d.os", esc(n.os));
    add("d.site", esc(n.site)); add("d.subnet", esc(n.subnet));
    if (n.parent_name) add(n.link ? "d.plugged" : "d.attached", `${esc(n.parent_name)}${n.link ? `, ${t("d.port")} <b>${esc(n.link)}</b>` : ""}`);
    if (n.vm) add("d.esxiHost", esc(n.vm.host));
    add("d.ports", (n.ports || []).join(", "));
    add("d.latency", n.latency_ms != null ? fmt.ms(n.latency_ms) : null);
    add("d.avail", n.availability_24h != null ? fmt.pct(n.availability_24h) : null);
    add("d.sources", esc((n.sources || []).join(", ")));
    add("d.first", n.first_seen ? fmt.dt(n.first_seen) : null);
    add("d.last", n.last_seen ? fmt.ago(n.last_seen) : null);
    add("d.otherIps", esc(n.details && n.details["autres IP"]));
    let res = "";
    if (n.metrics && (n.metrics.cpu != null || n.metrics.mem != null)) {
      res += `<div class="d-sec"><h4>${t("d.resources")}</h4>${meter("CPU", n.metrics.cpu, 75, 90)}${meter("RAM", n.metrics.mem, 85, 95)}${n.metrics.disk != null ? meter(t("d.disk"), n.metrics.disk, 80, 90) : ""}
        ${n.metrics.uptime ? `<div class="muted" style="font-size:12px;margin-top:6px">${t("d.uptime", { d: fmt.dur(n.metrics.uptime) })}</div>` : ""}</div>`;
    }
    if (n.vm) res += `<div class="d-sec"><h4>${t("d.vm")}</h4><div class="kv"><div>${t("d.resources")}</div><div>${t("d.vmRes", { c: n.vm.vcpu, m: n.vm.mem_gb, d: fmt.gb(n.vm.disk_gb) })}</div><div>${t("d.tools")}</div><div>${esc((n.vm.tools || "").replace("guestTools", ""))}</div><div>${t("d.vmUp")}</div><div>${fmt.dur(n.vm.uptime_s)}</div></div></div>`;
    if (n.esxi) res += `<div class="d-sec"><h4>${t("d.hyp")}</h4><div class="kv"><div>${t("d.model")}</div><div>${esc(n.esxi.model)}</div><div>${t("d.version")}</div><div>${esc(n.esxi.version)}</div><div>${t("d.cluster")}</div><div>${esc(n.esxi.cluster || "—")}</div><div>${t("d.cpu")}</div><div>${t("d.cores", { n: n.esxi.cores, p: fmt.pct(n.esxi.cpu_pct) })}</div><div>${t("d.mem")}</div><div>${n.esxi.mem_used_gb} / ${n.esxi.mem_gb} ${t("unit.gb")}</div><div>${t("d.state")}</div><div>${esc(n.esxi.state)}${n.esxi.maintenance ? `, ${t("d.maint")}` : ""}</div></div></div>`;
    if (n.disks && n.disks.length) res += `<div class="d-sec"><h4>${t("d.disks")}</h4>${n.disks.map((x) => meter(esc(x.name), x.pct, 80, 90)).join("")}</div>`;
    if (n.cpu_series && n.cpu_series.length) res += `<div class="d-sec"><h4>${t("d.cpu24")}</h4>${areaChart(n.cpu_series, { unit: "%", max: 100, color: "var(--violet)" })}</div>`;
    if (n.latency_series && n.latency_series.length) res += `<div class="d-sec"><h4>${t("d.lat24")}</h4>${areaChart(n.latency_series, { unit: "ms" })}</div>`;
    const alerts = (n.alerts || []).map((a) => `<div class="aitem" style="cursor:default"><span class="sev" style="background:var(--${a.severity === "critical" ? "down" : a.severity === "warning" ? "warning" : "info"})"></span><div><b>${esc(a.summary || a.name)}</b><div class="meta"><span>${esc(a.source || "")}</span><span>${esc(a.name)}</span></div></div><span></span></div>`).join("");
    const children = (n.children || []).length ? `<div class="d-sec"><h4>${t(n.role === "esxi" ? "d.vms" : "d.children")} (${n.children.length})</h4><div class="children">${n.children.map((c) =>
      `<div data-node="${esc(c.id)}">${lamp(c.status)}<b>${esc(c.name)}</b><span class="muted mono">${esc(c.ip || "")}</span><span class="muted" style="margin-left:auto">${c.link ? `${t("d.port")} ${esc(c.link)}` : esc(roleLabel(c))}</span></div>`).join("")}</div></div>` : "";
    const sw = n.switch ? `<div class="d-sec"><h4>${t("d.usedPorts")}</h4><div class="children">${n.switch.ports.filter((p) => p.devices.length || p.vms).map((p) =>
      `<div ${p.devices[0] ? `data-node="${esc(p.devices[0].id)}"` : ""}><b class="mono" style="min-width:64px">${esc(p.name)}</b>${p.devices.map((d) => `${lamp(d.status)}${esc(d.name)}`).join(", ")}${p.vms ? `<span class="muted">+${p.vms} VM</span>` : ""}</div>`).join("")}</div></div>` : "";
    const logs = n.logs && n.logs.length ? `<div class="d-sec"><h4>${t("d.logs")}${n.errors_24h != null ? `, ${t("d.errors", { n: Math.round(n.errors_24h) })}` : ""}</h4><div class="logs">${n.logs.slice(0, 25).map((l) =>
      `<div class="lv-${esc(l.level || "")}"><span>${new Date(l.ts * 1000).toLocaleTimeString(I18n.locale)}</span><span>${esc(l.line)}</span></div>`).join("")}</div></div>` : "";
    const ai = state.features && state.features.ai ? `<button class="ai" id="d-ai">${svg("sparkle")}${t("d.ai")}</button>` : "";
    $("#drawer-body").innerHTML = `
      <div class="d-head"><div class="tile-ic" style="--c:var(--${esc(n.status)})">${roleIcon(n.role)}</div>
        <div><h3>${esc(nm(n.name))}</h3><div class="muted">${esc(roleLabel(n))}${n.ip ? `, <span class="mono">${esc(n.ip)}</span>` : ""}</div><div style="margin-top:6px;display:flex;gap:6px">${statusBadge(n.status)}${n.new ? `<span class="badge b-info">${t("d.new")}</span>` : ""}</div></div></div>
      ${alerts ? `<div class="alist">${alerts}</div>` : ""}
      ${ai ? `<div class="d-actions">${ai}</div><div id="d-ai-out"></div>` : ""}
      <div class="d-sec"><h4>${t("d.identity")}</h4><div class="kv">${rows.join("")}</div></div>
      ${res}${sw}${children}${logs}
      ${n.links && n.links.length ? `<div class="d-sec"><h4>${t("d.open")}</h4><div class="d-actions">${n.links.map((l) => `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)} ↗</a>`).join("")}</div></div>` : ""}`;
    hydrateIcons($("#drawer"));
    $$("#drawer [data-node]").forEach((el) => el.addEventListener("click", () => openNode(el.dataset.node)));
    const b = $("#d-ai");
    if (b) b.addEventListener("click", async () => {
      b.disabled = true; $("#d-ai-out").innerHTML = `<div class="ai-box"><span class="spinner"></span>${t("d.aiRunning")}</div>`;
      try { const r = await post("api/ai/explain", { id, lang: I18n.lang }); $("#d-ai-out").innerHTML = aiBox(r); }
      catch (e) { $("#d-ai-out").innerHTML = `<div class="ai-box">${t("d.aiErr")}</div>`; }
      b.disabled = false;
    });
    if (window.Topo && Topo.highlight) Topo.highlight(id);
  }
  function aiBox(r) {
    if (r.error) return `<div class="ai-box">${esc(r.error)}</div>`;
    return `<div class="ai-box">${md(r.text)}<div class="ai-meta">${t("ai.meta", { p: esc(r.provider), m: esc(r.model), c: r.cached ? t("ai.cached") : "" })}</div></div>`;
  }
  function closeDrawer() { drawerId = null; $("#drawer").classList.add("hidden"); if (window.Topo && Topo.highlight) Topo.highlight(null); }

  async function aiSummary() {
    $("#modal").classList.remove("hidden");
    $("#modal-body").innerHTML = `<h2>${t("ai.title")}</h2><div class="muted">${t("ai.intro")}</div><div class="ai-box"><span class="spinner"></span>${t("d.aiRunning")}</div>`;
    try { const r = await post("api/ai/summary", { lang: I18n.lang }); $("#modal-body").innerHTML = `<h2>${t("ai.title")}</h2><div class="muted">${fmt.dt(Date.now() / 1000)}</div>${aiBox(r)}`; }
    catch (e) { $("#modal-body").innerHTML += `<div class="ai-box">${t("ai.err")}</div>`; }
  }

  // ------------------------------------------------------------ recherche globale
  let searchCache = { t: 0, rows: [] }, searchSel = 0;
  async function search(q) {
    const box = $("#search-results");
    if (!q) { box.classList.add("hidden"); return; }
    if (Date.now() - searchCache.t > 30000) { try { const r = await api("api/inventory?site="); searchCache = { t: Date.now(), rows: r.rows }; } catch (e) { return; } }
    const ql = q.toLowerCase();
    const hits = searchCache.rows.filter((r) => [r.name, r.ip, r.mac, r.dns, r.netbios, r.vendor, r.os].some((v) => v && String(v).toLowerCase().includes(ql))).slice(0, 12);
    searchSel = 0;
    box.innerHTML = hits.length ? hits.map((r, i) => `<div data-node="${esc(r.id)}" class="${i === 0 ? "sel" : ""}">${lamp(r.status)}<b>${esc(nm(r.name))}</b><span class="muted mono">${esc(r.ip || "")}</span><span class="muted" style="margin-left:auto">${esc(I18n.role(r.role, r.type))}</span></div>`).join("")
      : `<div class="muted" style="cursor:default">${t("search.none")}</div>`;
    box.classList.remove("hidden");
    $$("[data-node]", box).forEach((el) => el.addEventListener("mousedown", () => { openNode(el.dataset.node); box.classList.add("hidden"); }));
  }

  // ------------------------------------------------------------ thème et langue
  const listeners = [];
  const onRestyle = (fn) => listeners.push(fn);
  function setTheme(th) {
    document.documentElement.dataset.theme = th; store.set("theme", th);
    readColors(); listeners.forEach((fn) => fn()); chrome(); refresh(false);
  }

  function init() {
    hydrateIcons();
    chrome();
    window.addEventListener("hashchange", route);
    $("#drawer-close").addEventListener("click", closeDrawer);
    $("#modal-close").addEventListener("click", () => $("#modal").classList.add("hidden"));
    $("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") $("#modal").classList.add("hidden"); });
    const pop = $("#sources-pop");
    $("#btn-sources").addEventListener("click", (e) => { e.stopPropagation(); pop.classList.toggle("hidden"); });
    document.addEventListener("click", (e) => { if (!pop.contains(e.target)) pop.classList.add("hidden"); });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") { closeDrawer(); $("#modal").classList.add("hidden"); $("#search-results").classList.add("hidden"); pop.classList.add("hidden"); }
      if (e.key === "/" && !["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName)) { e.preventDefault(); $("#search").focus(); }
    });
    let tm; const s = $("#search");
    s.addEventListener("input", () => { clearTimeout(tm); tm = setTimeout(() => search(s.value.trim()), 150); });
    s.addEventListener("blur", () => setTimeout(() => $("#search-results").classList.add("hidden"), 150));
    s.addEventListener("keydown", (e) => {
      const items = $$("#search-results [data-node]");
      if (!items.length) return;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); searchSel = (searchSel + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length; items.forEach((x, i) => x.classList.toggle("sel", i === searchSel)); }
      if (e.key === "Enter" && items[searchSel]) { openNode(items[searchSel].dataset.node); $("#search-results").classList.add("hidden"); s.blur(); }
    });
    $("#btn-ai").addEventListener("click", aiSummary);
    $("#btn-rescan").addEventListener("click", async (e) => {
      const b = e.currentTarget; b.disabled = true;
      try { await post("api/rescan"); toast(t("rail.rescanStarted")); } catch (err) { /* le scan suivant passera de toute façon */ }
      setTimeout(() => { b.disabled = false; }, 20000);
    });
    $("#btn-theme").addEventListener("click", () => setTheme(document.documentElement.dataset.theme === "day" ? "night" : "day"));
    $("#btn-lang").addEventListener("click", () => { I18n.set(I18n.lang === "fr" ? "en" : "fr"); chrome(); route(); });
    api("api/features").then((f) => setFeatures(f)).catch(() => {});
    route();
    state.timer = setInterval(() => { if (!document.hidden) { refresh(false); api("api/features").then((f) => setFeatures(f)).catch(() => {}); } }, 20000);
  }

  return { ICONS, COLORS, LABELS, icon, roleIcon, roleLabel, nm, iconUri, svg, esc, $, $$, fmt, bar, meter, lamp, segBar, spark, areaChart, md,
    statusBadge, sevBadge, pctColor, api, post, register, state, store, setFeatures, setAlertCount, openNode, closeDrawer, hydrateIcons,
    aiBox, onRestyle, toast, init };
})();
