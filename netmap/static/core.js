/* Cockpit de supervision : socle (API, navigation, composants, fiche équipement, IA) */
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
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
  };
  const ROLE_ICON = { server: "server", dc: "key", vm: "vm", esxi: "layers", hypervisor: "layers", switch: "switch", network: "switch",
    firewall: "shield", router: "router", gateway: "router", internet: "globe", isp: "cloud", nas: "database", printer: "printer",
    windows: "windows", linux: "terminal", camera: "camera", phone: "phone", wifi: "wifi", subnet: "network", site: "building",
    device: "monitor", other: "monitor", mobile: "mobile", group: "group" };
  const COLORS = { up: "#22c55e", warning: "#f5a524", critical: "#ef4444", down: "#ef4444", off: "#64748b", absent: "#475569",
    unknown: "#94a3b8", net: "#4f8cff", info: "#38bdf8" };
  const LABELS = { up: "OK", warning: "Alerte", critical: "Critique", down: "En panne", off: "Éteint", absent: "Absent",
    unknown: "Inconnu", net: "Réseau", info: "Info" };
  const SEV = { critical: "Critique", warning: "Attention", info: "Info" };

  const svg = (k, stroke = "currentColor", w = 1.8) =>
    `<svg viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round">${ICONS[k] || ICONS.monitor}</svg>`;
  const icon = (k) => `<i data-icon="${k}">${svg(k)}</i>`;
  const roleIcon = (role) => icon(ROLE_ICON[role] || "monitor");
  const iconUri = (role, stroke = "#e2e8f0") => "data:image/svg+xml;utf8," + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${ICONS[ROLE_ICON[role] || role] || ICONS.monitor}</svg>`);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];

  function hydrateIcons(root = document) { $$("i[data-icon]:empty", root).forEach((el) => { el.innerHTML = svg(el.dataset.icon); }); }

  const store = {
    get(k, d) { try { const v = localStorage.getItem("cockpit." + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem("cockpit." + k, JSON.stringify(v)); } catch (e) { /* ignoré */ } },
  };

  // ------------------------------------------------------------ formats
  const fmt = {
    pct: (v) => (v == null ? "—" : `${Math.round(v)} %`),
    ms: (v) => (v == null ? "—" : v < 10 ? `${v.toFixed(1)} ms` : `${Math.round(v)} ms`),
    ago(ts) {
      if (!ts) return "—";
      const s = Math.max(0, Date.now() / 1000 - ts);
      if (s < 60) return "à l'instant";
      if (s < 3600) return `il y a ${Math.round(s / 60)} min`;
      if (s < 86400) return `il y a ${Math.floor(s / 3600)} h ${String(Math.round((s % 3600) / 60)).padStart(2, "0")}`;
      return `il y a ${Math.round(s / 86400)} j`;
    },
    time: (ts) => (ts ? new Date(ts * 1000).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }) : "—"),
    dt: (ts) => (ts ? new Date(ts * 1000).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—"),
    dur(s) {
      if (s == null) return "—";
      const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600);
      return d ? `${d} j ${h} h` : `${h} h ${Math.floor((s % 3600) / 60)} min`;
    },
    bps(v) {
      if (v == null) return "—";
      const u = ["b/s", "kb/s", "Mb/s", "Gb/s"]; let i = 0;
      while (v >= 1000 && i < u.length - 1) { v /= 1000; i++; }
      return `${v.toFixed(v < 10 ? 1 : 0)} ${u[i]}`;
    },
    gb: (v) => (v == null ? "—" : v >= 1024 ? `${(v / 1024).toFixed(1)} To` : `${Math.round(v)} Go`),
  };
  const pctColor = (v, warn = 80, crit = 90) => (v == null ? "#334155" : v >= crit ? COLORS.down : v >= warn ? COLORS.warning : COLORS.up);
  const bar = (v, warn, crit) => `<div class="bar"><span style="width:${Math.min(100, Math.max(0, v || 0))}%;background:${pctColor(v, warn, crit)}"></span></div>`;
  const meter = (k, v, warn, crit) => `<div class="meter"><span class="k">${k}</span>${bar(v, warn, crit)}<span class="v">${fmt.pct(v)}</span></div>`;
  const statusBadge = (s) => `<span class="badge b-${s}"><span class="sdot s-${s}"></span>${LABELS[s] || s}</span>`;
  const sevBadge = (s) => `<span class="badge b-${s}">${SEV[s] || s}</span>`;

  function spark(points, { w = 120, h = 34, color = "#4f8cff", fill = true } = {}) {
    if (!points || points.length < 2) return "";
    const ys = points.map((p) => p[1]); const min = Math.min(...ys), max = Math.max(...ys); const span = max - min || 1;
    const xs = points.map((p, i) => (i / (points.length - 1)) * w);
    const pts = points.map((p, i) => `${xs[i].toFixed(1)},${(h - 3 - ((p[1] - min) / span) * (h - 6)).toFixed(1)}`);
    const id = "g" + Math.random().toString(36).slice(2, 8);
    return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><defs><linearGradient id="${id}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".35"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs>${fill ? `<path d="M0,${h} L${pts.join(" L")} L${w},${h} Z" fill="url(#${id})"/>` : ""}<polyline points="${pts.join(" ")}" fill="none" stroke="${color}" stroke-width="1.6"/></svg>`;
  }

  function areaChart(points, { unit = "", color = "#4f8cff", max = null } = {}) {
    if (!points || points.length < 2) return '<div class="muted">Pas encore d\'historique.</div>';
    const w = 400, h = 80; const ys = points.map((p) => p[1]);
    const hi = max ?? (Math.max(...ys) * 1.15 || 1); const lo = 0;
    const pts = points.map((p, i) => `${((i / (points.length - 1)) * w).toFixed(1)},${(h - ((p[1] - lo) / (hi - lo)) * h).toFixed(1)}`);
    const last = ys[ys.length - 1], avg = ys.reduce((a, b) => a + b, 0) / ys.length, mx = Math.max(...ys);
    const id = "a" + Math.random().toString(36).slice(2, 8);
    const f = (v) => (unit === "ms" ? fmt.ms(v) : unit === "%" ? fmt.pct(v) : v.toFixed(1));
    return `<svg class="chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><defs><linearGradient id="${id}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".4"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs><path d="M0,${h} L${pts.join(" L")} L${w},${h} Z" fill="url(#${id})"/><polyline points="${pts.join(" ")}" fill="none" stroke="${color}" stroke-width="1.5" vector-effect="non-scaling-stroke"/></svg>
      <div class="muted" style="font-size:11.5px;display:flex;gap:14px">Actuel <b style="color:var(--text)">${f(last)}</b> · moyenne ${f(avg)} · max ${f(mx)} <span style="margin-left:auto">24 h</span></div>`;
  }

  function donut(parts, size = 64, stroke = 9) {
    const total = parts.reduce((a, p) => a + p.v, 0) || 1; const r = (size - stroke) / 2, c = 2 * Math.PI * r; let off = 0;
    const segs = parts.filter((p) => p.v > 0).map((p) => {
      const len = (p.v / total) * c; const s = `<circle r="${r}" cx="${size / 2}" cy="${size / 2}" fill="none" stroke="${p.c}" stroke-width="${stroke}" stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-off}"/>`;
      off += len; return s;
    }).join("");
    return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" style="transform:rotate(-90deg)"><circle r="${r}" cx="${size / 2}" cy="${size / 2}" fill="none" stroke="#1a2440" stroke-width="${stroke}"/>${segs}</svg>`;
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
  const TITLES = { overview: "Vue d'ensemble", topology: "Topologie", vmware: "VMware vSphere", switches: "Switchs", inventory: "Inventaire",
    alerts: "Alertes", services: "Services" };

  function register(name, impl) { views[name] = impl; }

  async function route() {
    const name = (location.hash.replace(/^#\//, "").split("?")[0]) || "overview";
    const v = views[name] ? name : "overview";
    if (state.current && state.current.leave) state.current.leave();
    state.view = v; state.current = views[v];
    $$("#nav a").forEach((a) => a.classList.toggle("active", a.dataset.view === v));
    $("#page-title").textContent = TITLES[v];
    $("#page-sub").textContent = "";
    const el = $("#view"); el.className = views[v].full ? "full" : ""; el.innerHTML = '<div class="muted" style="padding:20px"><span class="spinner"></span> Chargement…</div>';
    await refresh(true);
  }

  async function refresh(first) {
    try {
      if (state.current) await state.current.render($("#view"), first);
      $("#live-dot").classList.remove("stale"); $("#live-txt").textContent = "en direct";
    } catch (e) {
      console.error(e);
      $("#live-dot").classList.add("stale"); $("#live-txt").textContent = "connexion perdue";
    }
    hydrateIcons();
  }

  function setFeatures(f) {
    if (!f) return;
    state.features = f;
    const seg = $("#site-seg");
    const sites = ["", ...(f.sites || [])];
    if (seg.dataset.sites !== sites.join("|")) {
      seg.dataset.sites = sites.join("|");
      seg.innerHTML = sites.map((s) => `<button data-site="${esc(s)}">${s ? esc(s) : "Tous les sites"}</button>`).join("");
      $$("button", seg).forEach((b) => b.addEventListener("click", () => { state.site = b.dataset.site; store.set("site", state.site); markSite(); refresh(true); }));
    }
    markSite();
    const dot = (ok, on = true) => `<span class="sdot ${!on ? "s-off" : ok ? "s-up" : "s-down"}"></span>`;
    const src = [["Prometheus", true, true], ["Scan réseau", true, true],
      ["vCenter", f.vcenter && f.vcenter.up, !!f.vcenter], ["Zabbix", f.zabbix && f.zabbix.up, !!f.zabbix],
      ["SNMP", f.snmp, f.snmp], ["IA", !!f.ai, !!f.ai]];
    $("#sources").innerHTML = src.map(([n, ok, on]) => `<span title="${on ? (ok ? "connecté" : "erreur") : "non configuré"}">${dot(ok, on)}${n}</span>`).join("");
    $("#scan-info").textContent = f.scanning ? "Scan en cours…" : `Scan ${fmt.time(f.last_scan)}`;
    const ext = [];
    if (f.grafana_url) ext.push(`<a href="${esc(f.grafana_url)}" target="_blank">Grafana</a>`);
    if (f.zabbix && f.zabbix.url) ext.push(`<a href="${esc(f.zabbix.url)}" target="_blank">Zabbix</a>`);
    if (f.alertmanager_url) ext.push(`<a href="${esc(f.alertmanager_url)}" target="_blank">Alertmanager</a>`);
    $("#ext-links").innerHTML = ext.join("");
    $("#btn-ai").classList.toggle("hidden", !f.ai);
  }
  function markSite() { $$("#site-seg button").forEach((b) => b.classList.toggle("on", b.dataset.site === (state.site || ""))); }

  function setAlertCount(c) {
    const el = $("#nav-alerts"); const n = (c.critical || 0) + (c.warning || 0);
    el.textContent = n; el.classList.toggle("hidden", !n); el.classList.toggle("warn", !c.critical);
    document.title = (c.critical ? `(${c.critical}) ` : "") + "NetCockpit";
  }

  // ------------------------------------------------------------ fiche équipement
  let drawerId = null;
  async function openNode(id) {
    if (!id || /^(net|site):/.test(id) && false) return;
    drawerId = id;
    const d = $("#drawer"); d.classList.remove("hidden");
    $("#drawer-body").innerHTML = '<span class="spinner"></span>';
    let n;
    try { n = await api(`api/node?id=${encodeURIComponent(id)}`); } catch (e) { $("#drawer-body").innerHTML = "Équipement introuvable."; return; }
    if (drawerId !== id) return;
    const rows = [];
    const add = (k, v) => { if (v != null && v !== "" && !(Array.isArray(v) && !v.length)) rows.push(`<div>${k}</div><div>${v}</div>`); };
    add("Adresse IP", n.ip ? `<span class="mono">${esc(n.ip)}</span>` : null);
    add("Nom DNS", esc(n.details && n.details.fqdn || n.dns));
    add("Nom NetBIOS", esc(n.netbios));
    add("Adresse MAC", n.mac ? `<span class="mono">${esc(n.mac)}</span>` : null);
    add("Constructeur", esc(n.vendor));
    add("Type", esc(n.role_label));
    add("Système", esc(n.os));
    add("Site", esc(n.site)); add("Réseau", esc(n.subnet));
    if (n.parent_name) add(n.link ? "Branché sur" : "Rattaché à", `${esc(n.parent_name)}${n.link ? ` · port <b>${esc(n.link)}</b>` : ""}`);
    if (n.vm) add("Hôte ESXi", esc(n.vm.host));
    add("Ports ouverts", (n.ports || []).join(", "));
    add("Latence", n.latency_ms != null ? fmt.ms(n.latency_ms) : null);
    add("Disponibilité 24 h", n.availability_24h != null ? `${n.availability_24h} %` : null);
    add("Découvert par", esc((n.sources || []).join(", ")));
    add("Première détection", n.first_seen ? fmt.dt(n.first_seen) : null);
    add("Dernière détection", n.last_seen ? fmt.ago(n.last_seen) : null);
    add("Autres IP", esc(n.details && n.details["autres IP"]));
    const color = COLORS[n.status] || COLORS.unknown;
    let res = "";
    if (n.metrics && (n.metrics.cpu != null || n.metrics.mem != null)) {
      res += `<div class="d-sec"><h4>Ressources</h4>${meter("CPU", n.metrics.cpu, 75, 90)}${meter("RAM", n.metrics.mem, 85, 95)}${n.metrics.disk != null ? meter("Disque", n.metrics.disk, 80, 90) : ""}
        ${n.metrics.uptime ? `<div class="muted" style="font-size:12px;margin-top:6px">Allumé depuis ${fmt.dur(n.metrics.uptime)}</div>` : ""}</div>`;
    }
    if (n.vm) res += `<div class="d-sec"><h4>Machine virtuelle</h4><div class="kv"><div>Ressources</div><div>${n.vm.vcpu} vCPU · ${n.vm.mem_gb} Go RAM · ${fmt.gb(n.vm.disk_gb)} disque</div><div>VMware Tools</div><div>${esc((n.vm.tools || "").replace("guestTools", ""))}</div><div>Allumée depuis</div><div>${fmt.dur(n.vm.uptime_s)}</div></div></div>`;
    if (n.esxi) res += `<div class="d-sec"><h4>Hyperviseur</h4><div class="kv"><div>Modèle</div><div>${esc(n.esxi.model)}</div><div>Version</div><div>${esc(n.esxi.version)}</div><div>Cluster</div><div>${esc(n.esxi.cluster || "—")}</div><div>Processeur</div><div>${n.esxi.cores} cœurs · ${fmt.pct(n.esxi.cpu_pct)} utilisé</div><div>Mémoire</div><div>${n.esxi.mem_used_gb} / ${n.esxi.mem_gb} Go</div><div>État</div><div>${esc(n.esxi.state)}${n.esxi.maintenance ? " · maintenance" : ""}</div></div></div>`;
    if (n.disks && n.disks.length) res += `<div class="d-sec"><h4>Disques</h4>${n.disks.map((x) => meter(esc(x.name), x.pct, 80, 90)).join("")}</div>`;
    if (n.cpu_series && n.cpu_series.length) res += `<div class="d-sec"><h4>CPU · 24 h</h4>${areaChart(n.cpu_series, { unit: "%", max: 100, color: "#7c5cff" })}</div>`;
    if (n.latency_series && n.latency_series.length) res += `<div class="d-sec"><h4>Latence · 24 h</h4>${areaChart(n.latency_series, { unit: "ms", color: "#4f8cff" })}</div>`;
    const alerts = (n.alerts || []).map((a) => `<div class="aitem" style="cursor:default"><span class="sev" style="background:${COLORS[a.severity] || COLORS.info}"></span><div><b>${esc(a.summary || a.name)}</b><div class="meta"><span>${esc(a.source || "")}</span><span>${esc(a.name)}</span></div></div><span></span></div>`).join("");
    const children = (n.children || []).length ? `<div class="d-sec"><h4>${n.role === "esxi" ? "Machines virtuelles" : "Équipements rattachés"} (${n.children.length})</h4><div class="children">${n.children.map((c) =>
      `<div data-node="${esc(c.id)}"><span class="sdot s-${c.status}"></span><b>${esc(c.name)}</b><span class="muted">${esc(c.ip || "")}</span><span class="muted" style="margin-left:auto">${c.link ? "port " + esc(c.link) : esc(c.role_label)}</span></div>`).join("")}</div></div>` : "";
    const sw = n.switch ? `<div class="d-sec"><h4>Ports utilisés</h4><div class="children">${n.switch.ports.filter((p) => p.devices.length || p.vms).map((p) =>
      `<div ${p.devices[0] ? `data-node="${esc(p.devices[0].id)}"` : ""}><b class="mono" style="min-width:64px">${esc(p.name)}</b>${p.devices.map((d) => `<span class="sdot s-${d.status}"></span>${esc(d.name)}`).join(", ")}${p.vms ? `<span class="muted">+${p.vms} VM</span>` : ""}</div>`).join("")}</div></div>` : "";
    const logs = n.logs && n.logs.length ? `<div class="d-sec"><h4>Derniers logs${n.errors_24h != null ? ` · ${Math.round(n.errors_24h)} erreur(s) en 24 h` : ""}</h4><div class="logs">${n.logs.slice(0, 25).map((l) =>
      `<div class="lv-${esc(l.level || "")}"><span>${new Date(l.ts * 1000).toLocaleTimeString("fr-FR")}</span><span>${esc(l.line)}</span></div>`).join("")}</div></div>` : "";
    const ai = state.features && state.features.ai ? `<button class="ai" id="d-ai">${svg("sparkle")}Analyser avec l'IA</button>` : "";
    $("#drawer-body").innerHTML = `
      <div class="d-head"><div class="host-ic" style="border-color:${color}">${roleIcon(n.role)}</div>
        <div><h3>${esc(n.name)}</h3><div class="muted">${esc(n.role_label)}${n.ip ? " · " + esc(n.ip) : ""}</div><div style="margin-top:6px">${statusBadge(n.status)}${n.new ? ' <span class="badge b-info">Nouveau</span>' : ""}</div></div></div>
      ${alerts ? `<div class="alist">${alerts}</div>` : ""}
      ${ai ? `<div class="d-actions">${ai}</div><div id="d-ai-out"></div>` : ""}
      <div class="d-sec"><h4>Identité</h4><div class="kv">${rows.join("")}</div></div>
      ${res}${sw}${children}${logs}
      ${n.links && n.links.length ? `<div class="d-sec"><h4>Ouvrir</h4><div class="d-actions">${n.links.map((l) => `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)} ↗</a>`).join("")}</div></div>` : ""}`;
    hydrateIcons($("#drawer"));
    $$("#drawer [data-node]").forEach((el) => el.addEventListener("click", () => openNode(el.dataset.node)));
    const b = $("#d-ai");
    if (b) b.addEventListener("click", async () => {
      b.disabled = true; $("#d-ai-out").innerHTML = '<div class="ai-box"><span class="spinner"></span> Analyse en cours…</div>';
      try { const r = await post("api/ai/explain", { id }); $("#d-ai-out").innerHTML = aiBox(r); }
      catch (e) { $("#d-ai-out").innerHTML = '<div class="ai-box">Erreur de l\'analyse IA.</div>'; }
      b.disabled = false;
    });
    if (window.Topo && Topo.highlight) Topo.highlight(id);
  }
  function aiBox(r) {
    if (r.error) return `<div class="ai-box">${esc(r.error)}</div>`;
    return `<div class="ai-box">${md(r.text)}<div class="ai-meta">Analyse générée par ${esc(r.provider)} · ${esc(r.model)}${r.cached ? " · résultat récent réutilisé" : ""}. À vérifier avant d'agir.</div></div>`;
  }
  function closeDrawer() { drawerId = null; $("#drawer").classList.add("hidden"); if (window.Topo && Topo.highlight) Topo.highlight(null); }

  async function aiSummary() {
    $("#modal").classList.remove("hidden");
    $("#modal-body").innerHTML = '<h2 style="margin:0 0 6px">Analyse de la situation</h2><div class="muted">Toutes les alertes, l\'état des sites et le chemin Internet sont envoyés à l\'IA.</div><div class="ai-box"><span class="spinner"></span> Analyse en cours…</div>';
    try { const r = await post("api/ai/summary", {}); $("#modal-body").innerHTML = `<h2 style="margin:0 0 6px">Analyse de la situation</h2><div class="muted">${fmt.dt(Date.now() / 1000)}</div>${aiBox(r)}`; }
    catch (e) { $("#modal-body").innerHTML += '<div class="ai-box">Erreur.</div>'; }
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
    box.innerHTML = hits.length ? hits.map((r, i) => `<div data-node="${esc(r.id)}" class="${i === 0 ? "sel" : ""}"><span class="sdot s-${r.status}"></span><b>${esc(r.name)}</b><span class="muted mono">${esc(r.ip || "")}</span><span class="muted" style="margin-left:auto">${esc(r.type)}</span></div>`).join("")
      : '<div class="muted" style="cursor:default">Aucun résultat</div>';
    box.classList.remove("hidden");
    $$("[data-node]", box).forEach((el) => el.addEventListener("mousedown", () => { openNode(el.dataset.node); box.classList.add("hidden"); }));
  }

  function init() {
    hydrateIcons();
    window.addEventListener("hashchange", route);
    $("#drawer-close").addEventListener("click", closeDrawer);
    $("#modal-close").addEventListener("click", () => $("#modal").classList.add("hidden"));
    $("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") $("#modal").classList.add("hidden"); });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") { closeDrawer(); $("#modal").classList.add("hidden"); $("#search-results").classList.add("hidden"); }
      if (e.key === "/" && document.activeElement.tagName !== "INPUT") { e.preventDefault(); $("#search").focus(); }
    });
    let t; const s = $("#search");
    s.addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => search(s.value.trim()), 150); });
    s.addEventListener("blur", () => setTimeout(() => $("#search-results").classList.add("hidden"), 150));
    s.addEventListener("keydown", (e) => {
      const items = $$("#search-results [data-node]");
      if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); searchSel = (searchSel + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length; items.forEach((x, i) => x.classList.toggle("sel", i === searchSel)); }
      if (e.key === "Enter" && items[searchSel]) { openNode(items[searchSel].dataset.node); $("#search-results").classList.add("hidden"); s.blur(); }
    });
    $("#btn-ai").addEventListener("click", aiSummary);
    $("#btn-rescan").addEventListener("click", async (e) => {
      e.target.disabled = true; e.target.textContent = "Lancé…";
      try { await post("api/rescan"); } catch (err) { /* ignoré */ }
      setTimeout(() => { e.target.disabled = false; e.target.textContent = "Rescanner"; }, 20000);
    });
    api("api/features").then(setFeatures).catch(() => {});
    route();
    state.timer = setInterval(() => { if (!document.hidden) { refresh(false); api("api/features").then(setFeatures).catch(() => {}); } }, 20000);
  }

  return { ICONS, COLORS, LABELS, SEV, icon, roleIcon, iconUri, svg, esc, $, $$, fmt, bar, meter, spark, areaChart, donut, md, statusBadge, sevBadge,
    pctColor, api, post, register, state, store, setFeatures, setAlertCount, openNode, closeDrawer, hydrateIcons, aiBox, init };
})();
