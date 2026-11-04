/* Vues : vue d'ensemble, VMware, switchs, inventaire, alertes, services */
"use strict";
(() => {
  const { icon, roleIcon, roleLabel, esc, $, $$, fmt, bar, meter, lamp, segBar, spark, statusBadge, sevBadge, api } = App;
  const CAT_ICON = { servers: "server", workstations: "windows", printers: "printer", phones: "phone", cameras: "camera", network: "switch", mobile: "mobile", other: "monitor" };
  const sevVar = (s) => `var(--${s === "critical" ? "down" : s === "warning" ? "warning" : "info"})`;

  function bindNodes(root) { $$("[data-node]", root).forEach((el) => el.addEventListener("click", (e) => { e.stopPropagation(); App.openNode(el.dataset.node); })); }

  function alertItem(a, withDesc) {
    return `<div class="aitem" ${a.node ? `data-node="${esc(a.node)}"` : ""}><span class="sev" style="background:${sevVar(a.severity)}"></span>
      <div><b>${esc(a.summary || a.name)}</b><div class="meta">${sevBadge(a.severity)}${a.node_name ? `<span>${esc(a.node_name)}${a.node_ip ? ` <span class="mono">${esc(a.node_ip)}</span>` : ""}</span>` : ""}
      ${a.site ? `<span>${esc(a.site)}</span>` : ""}<span class="badge b-src">${esc(a.source)}</span></div>
      ${withDesc && a.description ? `<div class="muted" style="font-size:12px;margin-top:4px">${esc(a.description)}</div>` : ""}</div>
      <div class="when">${a.since ? fmt.ago(a.since) : ""}</div></div>`;
  }
  const calm = (txt) => `<div class="calm">${icon("check")}<b>${txt}</b></div>`;

  // ================================================================ VUE D'ENSEMBLE
  let graphCache = { t: 0, site: null, d: null };
  App.register("overview", {
    async render(el) {
      const d = await api("api/overview");
      App.setFeatures(d.features); App.setAlertCount(d.alerts_count);
      const s = d.stats, ac = d.alerts_count;
      $("#page-sub").textContent = App.state.site || t("top.allSites");
      const inetHop = d.internet_path.find((h) => h.role === "isp") || d.internet_path[d.internet_path.length - 2];
      const inetUp = (d.internet_path.find((h) => h.role === "internet") || {}).status;
      const ok = s.up + s.warning;
      const nSites = d.sites.filter((x) => !App.state.site || x.name === App.state.site).length;

      // 1. verdict
      const problems = ac.critical + ac.warning;
      const mood = inetUp === "down" || ac.critical ? "bad" : problems ? "warn" : "ok";
      const headline = inetUp === "down" ? t("ov.outage") : problems ? t("ov.problems", { n: problems }) : t("ov.nominal");
      const verdict = `<div class="verdict ${mood}"><span class="beacon"></span><div><h2>${esc(headline)}</h2>
        <div class="facts">${t("ov.facts", { total: s.total, n: nSites, t: fmt.time(d.features.last_scan) })}</div></div></div>`;

      // 2. route vers Internet (la « magenta line »)
      const path = d.internet_path.slice();
      const route = path.map((h, i) => {
        const hop = `<div class="hop" data-node="${esc(h.id)}"><div class="ring" style="--c:var(--${esc(h.status || "unknown")})">${roleIcon(h.role)}</div><b>${esc(App.nm(h.name))}</b><small class="mono">${esc(h.ip || roleLabel(h))}</small></div>`;
        if (i === path.length - 1) return hop;
        const next = path[i + 1];
        const lat = next.role === "internet" ? (d.internet_series.length ? d.internet_series[d.internet_series.length - 1][1] : null) : next.latency_ms;
        return hop + `<div class="leg ${h.status === "down" || next.status === "down" ? "down" : ""}"><span>${lat != null ? fmt.ms(lat) : ""}</span></div>`;
      }).join("");

      // 3. bande d'instruments
      const g = (cls, lab, ic, val, sub, extra = "", attrs = "") => `<div class="gauge ${cls}" ${attrs}><div class="lab">${icon(ic)}${lab}</div><div class="val">${val}</div><div class="sub">${sub}</div>${extra}</div>`;
      const gauges = [
        g(s.down ? "bad calm-val" : "", t("g.devices"), "network", `${ok}<small>${t("g.online", { n: s.total })}</small>`,
          s.down ? `<b style="color:var(--down)">${t("g.down", { n: s.down })}</b>, ${t("g.absentOff", { a: s.absent, o: s.off })}` : t("g.absentOff", { a: s.absent, o: s.off }),
          segBar([{ v: s.up, c: "var(--up)" }, { v: s.warning, c: "var(--warning)" }, { v: s.down, c: "var(--down)" }, { v: s.absent + s.off, c: "var(--line2)" }])),
        g(`click ${ac.critical ? "bad" : ac.warning ? "warn" : ""}`, t("g.alerts"), "bell", problems,
          t("g.alertsSub", { c: ac.critical, w: ac.warning, i: ac.info }), "", `data-go="#/alerts"`),
        g(inetUp === "down" ? "bad" : "", t("g.internet"), "globe", inetUp === "down" ? t("g.cut") : inetHop && inetHop.latency_ms != null ? fmt.ms(inetHop.latency_ms) : "OK",
          inetHop ? esc(App.nm(inetHop.name)) : t("g.noPath"), spark(d.internet_series, { w: 90, h: 26 })),
        g(d.agents.total && d.agents.alive < d.agents.total ? "bad" : "", t("g.agents"), "server", `${d.agents.alive}<small>/ ${d.agents.total}</small>`,
          d.agents.total ? (d.agents.alive < d.agents.total ? t("g.silent", { n: d.agents.total - d.agents.alive }) : t("g.allReport")) : t("g.noAgent")),
        d.vmware ? g(`click calm-val ${d.vmware.hosts_ok < d.vmware.hosts ? "bad" : d.vmware.alarms ? "warn" : ""}`, t("g.vmware"), "layers", `${d.vmware.vms_on}<small>${t("g.vmOn", { n: d.vmware.vms })}</small>`,
          t("g.vmSub", { ok: d.vmware.hosts_ok, h: d.vmware.hosts, ds: fmt.pct(d.vmware.datastore_max) }) + (d.vmware.alarms ? `, <b style="color:var(--warning)">${t("g.vmAlarms", { n: d.vmware.alarms })}</b>` : ""), "", `data-go="#/vmware"`)
          : g("", t("g.vmware"), "layers", `<span style="font-size:17px">${t("g.vmOff")}</span>`, t("g.vmHint")),
        d.zabbix ? g(d.zabbix.problems ? "warn" : "", t("g.zabbix"), "alert", d.zabbix.up ? `${d.zabbix.problems}<small>${t("g.zProblems")}</small>` : "—", d.zabbix.up ? t("g.zSub") : t("g.zDown"))
          : g("", t("g.lastScan"), "clock", fmt.time(d.features.last_scan), t("g.scanDur", { n: Math.round(d.features.scan_duration || 0) })),
      ].join("");

      // 4. contenu
      const sites = d.sites.filter((x) => !App.state.site || x.name === App.state.site).map((st) => {
        const tt = st.stats;
        const cats = st.categories.map((c) => `<div class="cat">${icon(CAT_ICON[c.key] || "monitor")}<div><b>${c.total}</b><small>${esc(t(`cat.${c.key}`) || c.label)}</small>${c.down ? `<span class="warnc">${t("cat.down", { n: c.down })}</span>` : c.warning ? `<span class="warnc" style="color:var(--warning)">${t("cat.warn", { n: c.warning })}</span>` : c.absent ? `<small>${t("cat.absent", { n: c.absent })}</small>` : ""}</div></div>`).join("");
        return `<div class="site" data-site="${esc(st.name)}" title="${esc(t("site.open"))}"><div class="site-head">${roleIcon("site")}
          <div style="min-width:0"><h3>${esc(st.name)}</h3><div class="nets mono">${st.subnets.map(esc).join("  ") || t("site.noNets")}</div></div>
          <div class="right"><span class="badge b-up">${lamp("up")}${t("site.online", { n: tt.up + tt.warning })}</span>${tt.down ? `<span class="badge b-down">${t("site.down", { n: tt.down })}</span>` : ""}${st.alerts ? `<span class="badge b-warning">${t("site.alerts", { n: st.alerts })}</span>` : ""}</div></div>
          <div class="cats">${cats}</div></div>`;
      }).join("");
      const servers = d.servers.slice().sort((a, b) => Math.max(b.cpu || 0, b.mem || 0, b.disk || 0) - Math.max(a.cpu || 0, a.mem || 0, a.disk || 0)).slice(0, 8);
      const cell = (v, w, c) => `<td style="width:21%">${bar(v, w, c)}<span class="muted" style="font-size:11px">${fmt.pct(v)}</span></td>`;
      const srvHtml = servers.length ? `<table class="t"><thead><tr><th>${t("col.server")}</th><th>CPU</th><th>RAM</th><th>${t("col.disk")}</th></tr></thead><tbody>${servers.map((x) =>
        `<tr class="row" data-node="${esc(x.id)}"><td><div class="namecell">${lamp(x.status)}<b>${esc(x.name)}</b></div></td>${cell(x.cpu, 75, 90)}${cell(x.mem, 85, 95)}${cell(x.disk, 80, 90)}</tr>`).join("")}</tbody></table>`
        : `<div class="notice">${t("ov.noAgent")}</div>`;
      const alerts = d.alerts.length ? `<div class="alist">${d.alerts.slice(0, 7).map((a) => alertItem(a)).join("")}</div>` : calm(t("ov.noProblem"));
      const news = d.new_devices.length ? `<div class="alist">${d.new_devices.slice(0, 6).map((n) => `<div class="aitem" data-node="${esc(n.id)}"><span class="sev" style="background:var(--info)"></span><div><b>${esc(n.name)}</b><div class="meta"><span class="mono">${esc(n.ip)}</span><span>${esc(roleLabel(n))}</span><span>${esc(n.site || "")}</span></div></div><span></span></div>`).join("")}</div>`
        : `<div class="muted">${t("ov.noNew")}</div>`;
      const svc = d.services.length ? d.services.map((x) => `<div class="meter" style="grid-template-columns:1fr auto auto"><span>${lamp(x.up === 1 ? "up" : x.up === 0 ? "down" : "unknown")} ${esc(x.name)}</span>
        <span class="muted">${x.duration_ms != null ? x.duration_ms + " ms" : ""}</span><span class="${x.cert_days != null && x.cert_days < 15 ? "badge b-warning" : "muted"}">${x.cert_days != null ? t("ov.cert", { n: x.cert_days }) : ""}</span></div>`).join("")
        : `<div class="muted">${t("ov.noWeb")}</div>`;

      el.innerHTML = `${verdict}
        <div class="hero">
          <div class="panel"><h2>${t("ov.route")}<span class="hint">${t("ov.routeHint")}</span></h2><div class="route">${route}</div></div>
          <div class="panel"><h2>${t("ov.mini")}<span class="right"><a href="#/topology">${t("ov.openTopo")}</a></span></h2><div class="mini-wrap"><div id="mini"></div></div></div>
        </div>
        <div class="gauges">${gauges}</div>
        <div class="grid g-main mt">
          <div class="stack">
            <div class="panel"><h2>${t("ov.problemsTitle")}<span class="right"><a href="#/alerts">${t("ov.seeAll")}</a></span></h2>${alerts}</div>
            <div class="panel"><h2>${t("ov.busiest")}<span class="right"><a href="#/inventory">${t("ov.inventory")}</a></span></h2>${srvHtml}</div>
          </div>
          <div class="stack">
            <div class="panel"><h2>${t("ov.sites")}</h2>${sites}</div>
            <div class="panel"><h2>${t("ov.new")}</h2>${news}</div>
            <div class="panel"><h2>${t("ov.web")}</h2>${svc}</div>
          </div>
        </div>`;
      bindNodes(el);
      $$("[data-go]", el).forEach((c) => c.addEventListener("click", () => { location.hash = c.dataset.go; }));
      $$(".site", el).forEach((c) => c.addEventListener("click", () => { App.state.site = c.dataset.site; App.store.set("site", c.dataset.site); location.hash = "#/topology"; }));
      // mini-topologie (graphe rechargé au plus toutes les 60 s)
      try {
        if (!graphCache.d || Date.now() - graphCache.t > 60000 || graphCache.site !== App.state.site) graphCache = { t: Date.now(), site: App.state.site, d: await api("api/graph") };
        Topo.drawMini($("#mini"), graphCache.d);
      } catch (e) { /* la mini-carte est un bonus : la vue reste utilisable sans */ }
    },
    leave() { Topo.dropMini(); },
  });

  // ================================================================ VMWARE
  App.register("vmware", {
    async render(el) {
      const d = await api("api/vmware");
      if (!d.configured) { el.innerHTML = `<div class="notice"><h3>${t("vm.notTitle")}</h3>${t("vm.notBody")}</div>`; return; }
      const tot = d.hosts.reduce((a, h) => ({ vms: a.vms + h.vms.length, on: a.on + h.vms_on }), { vms: 0, on: 0 });
      $("#page-sub").textContent = t("vm.sub", { h: d.hosts.length, on: tot.on, n: tot.vms }) + (d.up ? "" : t("vm.unreach", { e: d.error }));
      const hosts = d.hosts.map((h) => {
        const vms = h.vms.map((v) => {
          const on = v.power === "poweredOn";
          return `<div class="vm ${on ? "" : "off"}" ${v.id ? `data-node="${esc(v.id)}"` : ""} title="${esc(v.os || "")}">
          <b>${lamp(on ? v.status : "off")}${esc(v.name)}</b>
          <small>${t("vm.line", { ip: esc(v.ip || (on ? t("vm.noIp") : t("vm.off"))), c: v.vcpu, m: v.mem_gb })}</small>
          ${on ? `<div class="mini"><div title="CPU ${fmt.pct(v.cpu_pct)}">${bar(v.cpu_pct, 75, 90)}</div><div title="RAM ${fmt.pct(v.mem_pct)}">${bar(v.mem_pct, 85, 95)}</div></div>` : ""}
          ${v.alerts ? `<span class="badge b-warning">${v.alerts}</span>` : ""}</div>`;
        }).join("");
        return `<div class="panel"><div class="host-head"><div class="tile-ic" style="--c:var(--${h.state !== "connected" ? "down" : esc(h.status)})">${icon("layers")}</div>
          <div style="flex:1;min-width:0"><h3 class="click" data-node="${esc(h.id || "")}">${esc(h.name)}</h3><div class="muted">${esc(h.model)}, ${esc((h.version || "").replace(/ build.*/, ""))}${h.cluster ? ", " + esc(h.cluster) : ""}</div></div>
          <div style="text-align:right">${statusBadge(h.state !== "connected" ? "down" : h.status)}${h.maintenance ? `<div class="badge b-info" style="margin-top:4px">${t("d.maint")}</div>` : ""}</div></div>
          <div class="host-meters">${meter("CPU", h.cpu_pct, 75, 90)}${meter("RAM", h.mem_pct, 85, 95)}
            <div class="muted" style="font-size:12px">${t("vm.cores", { n: h.cores, u: Math.round(h.cpu_mhz_used / 1000), t: Math.round(h.cpu_mhz_total / 1000) })}</div>
            <div class="muted" style="font-size:12px">${t("vm.mem", { u: h.mem_used_gb, t: h.mem_gb, d: fmt.dur(h.uptime_s) })}</div></div>
          ${h.alerts.length ? `<div class="alist" style="margin-bottom:10px">${h.alerts.map((a) => `<div class="aitem" style="cursor:default"><span class="sev" style="background:var(--warning)"></span><div><b>${esc(a)}</b></div><span></span></div>`).join("")}</div>` : ""}
          <h4 class="muted" style="margin:8px 0 0;font-weight:400">${t("vm.vmsOn", { on: h.vms_on, n: h.vms.length })}</h4><div class="vmgrid">${vms}</div></div>`;
      }).join("");
      const ds = d.datastores.map((x) => `<div class="ds"><span><b>${esc(x.name)}</b> <span class="muted">${esc(x.type || "")}</span></span><span class="v"><b>${fmt.pct(x.used_pct)}</b></span>
        ${bar(x.used_pct, 80, 90)}<span class="muted" style="font-size:12px">${t("vm.dsFree", { f: fmt.gb(x.free_gb), c: fmt.gb(x.capacity_gb) })}</span></div>`).join("");
      const alarms = d.alarms.length ? `<div class="alist">${d.alarms.map((a) => `<div class="aitem" style="cursor:default"><span class="sev" style="background:var(--${a.status === "red" ? "down" : "warning"})"></span><div><b>${esc(a.alarm)}</b><div class="meta"><span>${esc(a.entity)}</span>${a.acknowledged ? `<span>${t("vm.acked")}</span>` : ""}</div></div><span></span></div>`).join("")}</div>`
        : calm(t("vm.noAlarm"));
      el.innerHTML = `<div class="grid g-main"><div class="stack">${hosts}</div>
        <div class="stack"><div class="panel"><h2>${t("vm.ds")}</h2>${ds || `<div class="muted">${t("vm.noDs")}</div>`}</div>
        <div class="panel"><h2>${t("vm.alarms")}</h2>${alarms}</div></div></div>`;
      bindNodes(el);
    },
  });

  // ================================================================ SWITCHS
  const speed = (m) => (m ? (m >= 1000 ? `${m / 1000} Gb/s` : `${m} Mb/s`) : "");
  App.register("switches", {
    async render(el) {
      const d = await api("api/switches");
      $("#page-sub").textContent = t("sw.sub", { n: d.switches.length }) + (d.snmp.configured ? t("sw.snmp") : "");
      const sw = d.switches.map((s) => {
        const named = s.ports.length >= 8 && s.ports.every((p) => /\d/.test(p.name));
        const grid = named ? `<div class="ports">${s.ports.map((p) => {
          const dev = p.devices[0]; const bad = p.devices.some((x) => ["down", "critical"].includes(x.status));
          const up = p.uplink || (p.mac_count > 6) || (p.devices.some((x) => ["switch", "network", "firewall", "router"].includes(x.role)));
          const cls = dev || p.vms ? `dev${bad ? " bad" : ""}${up ? " uplink" : ""}` : p.up ? "up" : "";
          const tip = `${p.name}${p.alias ? ` (${p.alias})` : ""} : ${p.devices.map((x) => x.name + (x.ip ? " " + x.ip : "")).join(", ") || (p.up ? t("sw.active") : t("sw.free"))}${p.vms ? ` + ${p.vms} VM` : ""}${p.speed_mbps ? `, ${speed(p.speed_mbps)}` : ""}${p.in_bps != null ? `, ↓ ${fmt.bps(p.in_bps)} ↑ ${fmt.bps(p.out_bps)}` : ""}`;
          return `<div class="port ${cls}" title="${esc(tip)}" ${dev ? `data-node="${esc(dev.id)}"` : ""}>${esc((p.name.match(/(\d+)\D*$/) || [, p.name])[1])}</div>`;
        }).join("")}</div>` : "";
        const rows = s.ports.filter((p) => p.devices.length || p.vms).map((p) => `<tr class="row" ${p.devices[0] ? `data-node="${esc(p.devices[0].id)}"` : ""}>
          <td class="mono">${esc(p.name)}</td><td>${p.devices.map((x) => `<div class="namecell">${lamp(x.status)}${roleIcon(x.role)}<b>${esc(x.name)}</b><span class="muted mono">${esc(x.ip || "")}</span></div>`).join("")}${p.vms ? `<span class="muted">${t("sw.vms", { n: p.vms })}</span>` : ""}</td>
          <td class="muted">${esc(p.alias || "")}</td><td class="muted">${speed(p.speed_mbps)}</td>
          <td class="num muted">${p.in_bps != null ? `↓ ${fmt.bps(p.in_bps)} ↑ ${fmt.bps(p.out_bps)}` : ""}</td><td class="muted">${esc(p.via.join(", "))}</td></tr>`).join("");
        return `<div class="panel"><div class="sw-head"><div class="tile-ic" style="--c:var(--${esc(s.status || "unknown")})">${icon("switch")}</div>
          <div style="flex:1"><h3 style="margin:0" class="click" data-node="${esc(s.id)}">${esc(s.name)}</h3><div class="muted" style="font-size:12.5px"><span class="mono">${esc(s.ip || t("sw.unknownIp"))}</span>${s.model ? ", " + esc(s.model) : ""}${s.site ? ", " + esc(s.site) : ""}</div></div>
          <div style="text-align:right">${statusBadge(s.status)}<div class="muted" style="font-size:12px;margin-top:4px">${t("sw.connected", { n: s.connected })}, ${s.snmp ? "SNMP" : t("sw.seenBy", { s: esc(s.sources.join(", ")) })}</div></div></div>
          ${grid}${named ? `<div class="legend" style="margin-bottom:12px"><span><i class="sq" style="--c:var(--info)"></i>${t("sw.legDev")}</span><span><i class="sq" style="--c:var(--magenta)"></i>${t("sw.legUp")}</span><span><i class="sq" style="--c:var(--up)"></i>${t("sw.legActive")}</span><span><i class="sq" style="--c:var(--line2)"></i>${t("sw.legFree")}</span></div>` : ""}
          <div style="max-height:380px;overflow:auto"><table class="t"><thead><tr><th>${t("col.port")}</th><th>${t("col.plugged")}</th><th>${t("col.desc")}</th><th>${t("col.speed")}</th><th>${t("col.traffic")}</th><th>${t("col.source")}</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
      }).join("");
      const detected = d.detected.length ? `<div class="panel"><h2>${t("sw.detected")}</h2><table class="t"><tbody>${d.detected.map((n) =>
        `<tr class="row" data-node="${esc(n.id)}"><td><div class="namecell">${lamp(n.status)}${roleIcon(n.role)}<b>${esc(n.name)}</b></div></td><td class="mono">${esc(n.ip || "")}</td><td class="muted">${esc(roleLabel(n))}</td><td class="muted">${esc(n.site || "")}</td></tr>`).join("")}</tbody></table></div>` : "";
      const errs = Object.entries(d.snmp.errors || {});
      const notice = !d.snmp.configured ? `<div class="notice"><h3>${t("sw.noticeTitle")}</h3>${t("sw.noticeBody")}
        ${errs.length ? `<div style="margin-top:8px;color:var(--warning)">${t("sw.snmpErr")}${errs.map(([k, v]) => esc(`${k} : ${v}`)).join(", ")}</div>` : ""}</div>` : "";
      el.innerHTML = `<div class="stack">${notice}${sw || `<div class="panel muted">${t("sw.none")}</div>`}${detected}</div>`;
      bindNodes(el);
    },
  });

  // ================================================================ INVENTAIRE
  const inv = { q: "", cat: "", status: "", sort: "ip", asc: true, lang: null };
  const ipKey = (ip) => (ip && /^\d+\.\d+\.\d+\.\d+$/.test(ip) ? ip.split(".").map((x) => x.padStart(3, "0")).join(".") : "zzz");
  App.register("inventory", {
    async render(el, first) {
      const d = await api("api/inventory");
      App.setFeatures(d.features);
      const rows = d.rows.filter((r) => !App.state.site || r.site === App.state.site).map((r) => Object.assign(r, { type: I18n.role(r.role, r.type) }));
      const cats = {}; rows.forEach((r) => { cats[r.type] = (cats[r.type] || 0) + 1; });
      if (first || !$("#inv-q") || inv.lang !== I18n.lang) {
        inv.lang = I18n.lang;
        const cols = [["status", "col.status"], ["name", "col.name"], ["ip", "col.ip"], ["mac", "col.mac"], ["vendor", "col.vendor"], ["type", "col.type"],
          ["os", "col.os"], ["site", "col.site"], ["switch", "col.switch"], ["latency_ms", "col.latency"], ["last_seen", "col.seen"]];
        el.innerHTML = `<div class="toolbar"><input id="inv-q" type="search" placeholder="${esc(t("inv.filter"))}" style="width:320px">
          <select id="inv-cat"></select><select id="inv-status"><option value="">${t("inv.allStates")}</option><option value="up">${t("status.up")}</option><option value="problem">${t("inv.problems")}</option><option value="absent">${t("inv.absent")}</option><option value="new">${t("inv.new")}</option></select>
          <span class="count" id="inv-count"></span><a class="chip" href="api/inventory.csv" download>${icon("download")}${t("inv.csv")}</a></div>
          <div class="panel" style="padding:0;overflow:auto;max-height:calc(100vh - 176px)"><table class="t" id="inv-t"><thead><tr>
          ${cols.map(([k, l]) => `<th data-k="${k}">${t(l)}</th>`).join("")}</tr></thead><tbody></tbody></table></div>`;
        $("#inv-q").value = inv.q; $("#inv-status").value = inv.status;
        $("#inv-q").addEventListener("input", (e) => { inv.q = e.target.value.toLowerCase(); draw(); });
        $("#inv-cat").addEventListener("change", (e) => { inv.cat = e.target.value; draw(); });
        $("#inv-status").addEventListener("change", (e) => { inv.status = e.target.value; draw(); });
        $$("#inv-t th").forEach((th) => th.addEventListener("click", () => { const k = th.dataset.k; inv.asc = inv.sort === k ? !inv.asc : true; inv.sort = k; draw(); }));
      }
      $("#inv-cat").innerHTML = `<option value="">${t("inv.allTypes")}</option>` + Object.entries(cats).sort((a, b) => b[1] - a[1]).map(([k, v]) => `<option value="${esc(k)}">${esc(k)} (${v})</option>`).join("");
      $("#inv-cat").value = inv.cat;
      function draw() {
        const r = rows.filter((x) => (!inv.cat || x.type === inv.cat)
          && (!inv.status || (inv.status === "problem" ? ["down", "critical", "warning"].includes(x.status) : inv.status === "absent" ? ["absent", "off"].includes(x.status) : inv.status === "new" ? x.new : x.status === inv.status))
          && (!inv.q || [x.name, x.ip, x.mac, x.vendor, x.os, x.dns, x.netbios, x.switch].some((v) => v && String(v).toLowerCase().includes(inv.q))));
        const k = inv.sort, dir = inv.asc ? 1 : -1;
        r.sort((a, b) => (k === "ip" ? ipKey(a.ip).localeCompare(ipKey(b.ip)) : String(a[k] ?? "").localeCompare(String(b[k] ?? ""), I18n.lang, { numeric: true })) * dir);
        $("#inv-count").textContent = t("inv.count", { n: r.length });
        $$("#inv-t th").forEach((th) => { th.classList.toggle("sorted", th.dataset.k === k); th.classList.toggle("asc", th.dataset.k === k && inv.asc); });
        $("#inv-t tbody").innerHTML = r.map((x) => `<tr class="row" data-node="${esc(x.id)}"><td>${statusBadge(x.status)}</td>
          <td><div class="namecell"><b>${esc(x.name)}</b>${x.new ? `<span class="badge b-info">${t("inv.newBadge")}</span>` : ""}${x.alerts ? `<span class="badge b-warning">${x.alerts}</span>` : ""}</div>${x.dns && x.dns !== x.name ? `<div class="muted" style="font-size:11.5px">${esc(x.dns)}</div>` : ""}</td>
          <td class="mono">${esc(x.ip || "")}</td><td class="mono muted">${esc(x.mac || "")}</td><td>${esc(x.vendor || "")}</td><td>${esc(x.type)}</td>
          <td class="muted">${esc(x.os || "")}</td><td class="muted">${esc(x.site || "")}</td><td>${x.switch ? `${esc(x.switch)} <span class="muted mono">${esc(x.port || "")}</span>` : ""}</td>
          <td class="num">${x.latency_ms != null ? fmt.ms(x.latency_ms) : ""}</td><td class="muted">${x.last_seen ? fmt.ago(x.last_seen) : ""}</td></tr>`).join("");
        bindNodes($("#inv-t"));
      }
      draw();
    },
  });

  // ================================================================ ALERTES
  const al = { sev: "", src: "" };
  App.register("alerts", {
    async render(el) {
      const d = await api("api/alerts");
      App.setFeatures(d.features);
      const all = d.alerts;
      const c = { critical: 0, warning: 0, info: 0 }; all.forEach((a) => { c[a.severity] = (c[a.severity] || 0) + 1; });
      App.setAlertCount(c);
      const list = all.filter((a) => (!al.sev || a.severity === al.sev) && (!al.src || a.source === al.src));
      const srcs = [...new Set(all.map((a) => a.source))];
      const f = d.features;
      const chip = (sev, key, n) => `<button class="chip ${al.sev === sev ? "on" : ""}" data-sev="${sev}">${t(key, { n })}</button>`;
      el.innerHTML = `<div class="toolbar">${chip("", "al.all", all.length)}${chip("critical", "al.critical", c.critical)}${chip("warning", "al.warning", c.warning)}${chip("info", "al.info", c.info)}
          <span style="width:12px"></span>${srcs.map((s) => `<button class="chip ${al.src === s ? "on" : ""}" data-src="${esc(s)}">${esc(s)}</button>`).join("")}
          <span class="count">${f.alertmanager_url ? `<a href="${esc(f.alertmanager_url)}/#/silences/new" target="_blank" rel="noopener">${t("al.silence")} ↗</a>` : ""}</span>
          ${f.ai ? `<button class="ai" id="al-ai">${App.svg("sparkle")}${t("al.ai")}</button>` : ""}</div>
        <div id="al-ai-out"></div>
        <div class="panel">${list.length ? `<div class="alist">${list.map((a) => alertItem(a, true)).join("")}</div>`
          : calm(t(al.sev || al.src ? "al.noneFilter" : "al.none"))}</div>`;
      $$("[data-sev]", el).forEach((b) => b.addEventListener("click", () => { al.sev = b.dataset.sev; App.state.current.render(el); }));
      $$("[data-src]", el).forEach((b) => b.addEventListener("click", () => { al.src = al.src === b.dataset.src ? "" : b.dataset.src; App.state.current.render(el); }));
      const b = $("#al-ai");
      if (b) b.addEventListener("click", async () => {
        b.disabled = true; $("#al-ai-out").innerHTML = `<div class="ai-box"><span class="spinner"></span>${t("d.aiRunning")}</div>`;
        try { $("#al-ai-out").innerHTML = App.aiBox(await App.post("api/ai/summary", { lang: I18n.lang })) + '<div style="height:14px"></div>'; } catch (e) { $("#al-ai-out").innerHTML = ""; }
        b.disabled = false;
      });
      bindNodes(el); App.hydrateIcons(el);
    },
  });

  // ================================================================ SERVICES
  App.register("services", {
    async render(el) {
      const d = await api("api/services");
      const st = (u) => statusBadge(u === 1 ? "up" : u === 0 ? "down" : "unknown");
      el.innerHTML = `<div class="grid g-2" style="align-items:start">
        <div class="panel"><h2>${t("svc.web")}</h2>${d.http.length ? `<table class="t"><thead><tr><th>${t("col.name")}</th><th>${t("col.status")}</th><th>${t("col.response")}</th><th>${t("col.code")}</th><th>${t("col.cert")}</th></tr></thead><tbody>${d.http.map((x) =>
          `<tr><td><b>${esc(x.name)}</b><div class="muted mono" style="font-size:11px">${esc(x.url)}</div></td><td>${st(x.up)}</td><td class="num">${x.duration_ms != null ? x.duration_ms + " ms" : "—"}</td><td>${x.code ?? "—"}</td>
           <td>${x.cert_days != null ? `<span class="badge ${x.cert_days < 15 ? "b-warning" : "b-up"}">${t("svc.days", { n: x.cert_days })}</span>` : "—"}</td></tr>`).join("")}</tbody></table>`
          : `<div class="muted">${t("svc.noHttp")}</div>`}</div>
        <div class="stack"><div class="panel"><h2>${t("svc.dns")}</h2><table class="t"><tbody>${d.dns.map((x) => `<tr><td><b>${esc(x.name)}</b> <span class="muted mono">${esc(x.ip)}</span></td><td>${st(x.up)}</td><td class="num">${x.duration_ms != null ? x.duration_ms + " ms" : "—"}</td></tr>`).join("") || `<tr><td class="muted">${t("svc.none")}</td></tr>`}</tbody></table></div>
        <div class="panel"><h2>${t("svc.inet")}</h2><table class="t"><tbody>${d.internet.map((x) => `<tr><td><b>${esc(x.name)}</b> <span class="muted mono">${esc(x.ip)}</span></td><td>${st(x.up)}</td><td class="num">${fmt.ms(x.latency_ms)}</td></tr>`).join("")}</tbody></table></div></div></div>`;
    },
  });

  App.init();
})();
