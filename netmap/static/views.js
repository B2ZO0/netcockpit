/* Vues : vue d'ensemble, VMware, switchs, inventaire, alertes, services */
"use strict";
(() => {
  const { COLORS, LABELS, icon, roleIcon, esc, $, $$, fmt, bar, meter, spark, donut, statusBadge, sevBadge, api } = App;
  const CAT_ICON = { servers: "server", workstations: "windows", printers: "printer", phones: "phone", cameras: "camera", network: "switch", mobile: "mobile", other: "monitor" };

  function bindNodes(root) { $$("[data-node]", root).forEach((el) => el.addEventListener("click", (e) => { e.stopPropagation(); App.openNode(el.dataset.node); })); }

  function alertItem(a) {
    const c = COLORS[a.severity] || COLORS.info;
    return `<div class="aitem" ${a.node ? `data-node="${esc(a.node)}"` : ""}><span class="sev" style="background:${c}"></span>
      <div><b>${esc(a.summary || a.name)}</b><div class="meta">${sevBadge(a.severity)}${a.node_name ? `<span>${esc(a.node_name)}${a.node_ip ? " · " + esc(a.node_ip) : ""}</span>` : ""}
      ${a.site ? `<span>${esc(a.site)}</span>` : ""}<span class="badge b-src">${esc(a.source)}</span></div></div>
      <div class="when">${a.since ? fmt.ago(a.since) : ""}</div></div>`;
  }

  // ================================================================ VUE D'ENSEMBLE
  App.register("overview", {
    async render(el) {
      const d = await api("api/overview");
      App.setFeatures(d.features); App.setAlertCount(d.alerts_count);
      const s = d.stats;
      $("#page-sub").textContent = App.state.site || "Tous les sites";
      const inetHop = d.internet_path.find((h) => h.role === "isp") || d.internet_path[d.internet_path.length - 2];
      const inetUp = (d.internet_path.find((h) => h.role === "internet") || {}).status;
      const ok = s.up + s.warning;
      const kpis = [
        `<div class="card kpi has-donut ${s.down ? "bad" : "good"}"><div class="lab">${icon("network")}Équipements</div><div class="val">${ok}<small>/ ${s.total} en ligne</small></div>
          <div class="sub">${s.down ? `<b style="color:#f87171">${s.down} en panne</b> · ` : ""}${s.absent} absents · ${s.off} éteints</div>
          <div class="spark">${donut([{ v: s.up, c: COLORS.up }, { v: s.warning, c: COLORS.warning }, { v: s.down, c: COLORS.down }, { v: s.absent + s.off, c: "#334155" }], 40, 7)}</div></div>`,
        `<div class="card kpi ${d.alerts_count.critical ? "bad" : d.alerts_count.warning ? "warn" : "good"} click" onclick="location.hash='#/alerts'"><div class="lab">${icon("bell")}Alertes</div>
          <div class="val">${d.alerts_count.critical + d.alerts_count.warning}</div><div class="sub">${d.alerts_count.critical} critique(s) · ${d.alerts_count.warning} attention · ${d.alerts_count.info} info</div></div>`,
        `<div class="card kpi has-spark ${inetUp === "down" ? "bad" : "good"}"><div class="lab">${icon("globe")}Internet</div><div class="val">${inetUp === "down" ? "Coupé" : inetHop && inetHop.latency_ms != null ? fmt.ms(inetHop.latency_ms) : "OK"}</div>
          <div class="sub">${inetHop ? esc(inetHop.name) : "chemin inconnu"}</div><div class="spark">${spark(d.internet_series, { w: 200, h: 30, color: "#4f8cff" })}</div></div>`,
        `<div class="card kpi ${d.agents.total && d.agents.alive < d.agents.total ? "bad" : ""}"><div class="lab">${icon("server")}Serveurs (agents)</div><div class="val">${d.agents.alive}<small>/ ${d.agents.total}</small></div>
          <div class="sub">${d.agents.total ? (d.agents.alive < d.agents.total ? `${d.agents.total - d.agents.alive} muet(s)` : "tous remontent") : "aucun agent installé"}</div></div>`,
        d.vmware ? `<div class="card kpi click ${d.vmware.hosts_ok < d.vmware.hosts ? "bad" : ""}" onclick="location.hash='#/vmware'"><div class="lab">${icon("layers")}VMware</div><div class="val">${d.vmware.vms_on}<small>VM / ${d.vmware.vms}</small></div>
          <div class="sub">${d.vmware.hosts_ok}/${d.vmware.hosts} ESXi · datastore max ${fmt.pct(d.vmware.datastore_max)}${d.vmware.alarms ? ` · <b style="color:#fbbf24">${d.vmware.alarms} alarme(s)</b>` : ""}</div></div>`
          : `<div class="card kpi"><div class="lab">${icon("layers")}VMware</div><div class="val" style="font-size:18px;margin-top:12px">Non connecté</div><div class="sub">Renseigne VCENTER_* dans .env</div></div>`,
        d.zabbix ? `<div class="card kpi ${d.zabbix.problems ? "warn" : "good"}"><div class="lab">${icon("alert")}Zabbix</div><div class="val">${d.zabbix.up ? d.zabbix.problems : "—"}<small>${d.zabbix.up ? "problème(s)" : ""}</small></div>
          <div class="sub">${d.zabbix.up ? "VMware natif + SNMP" : "injoignable"}</div></div>`
          : `<div class="card kpi"><div class="lab">${icon("clock")}Dernier scan</div><div class="val" style="font-size:22px;margin-top:10px">${fmt.time(d.features.last_scan)}</div><div class="sub">durée ${Math.round(d.features.scan_duration || 0)} s</div></div>`,
      ];
      const path = d.internet_path.slice();
      const pathHtml = path.map((h, i) => {
        const c = COLORS[h.status] || COLORS.unknown;
        const hop = `<div class="hop" data-node="${esc(h.id)}"><div class="ic" style="border-color:${c}">${roleIcon(h.role)}</div><b>${esc(h.name)}</b><small>${esc(h.ip || h.role_label)}</small></div>`;
        if (i === path.length - 1) return hop;
        const next = path[i + 1];
        const lat = next.role === "internet" ? (d.internet_series.length ? d.internet_series[d.internet_series.length - 1][1] : null) : next.latency_ms;
        return hop + `<div class="wire ${h.status === "down" || next.status === "down" ? "down" : ""}"><span>${lat != null ? fmt.ms(lat) : ""}</span></div>`;
      }).join("");
      const sites = d.sites.filter((x) => !App.state.site || x.name === App.state.site).map((st) => {
        const t = st.stats;
        const cats = st.categories.map((c) => `<div class="cat">${icon(CAT_ICON[c.key] || "monitor")}<div><b>${c.total}</b><small>${esc(c.label)}</small>${c.down ? `<span class="warnc">${c.down} en panne</span>` : c.warning ? `<span class="warnc" style="color:var(--warning)">${c.warning} alerte</span>` : c.absent ? `<small>${c.absent} absent(s)</small>` : ""}</div></div>`).join("");
        return `<div class="card site-card click" data-site="${esc(st.name)}"><div class="site-head">${donut([{ v: t.up, c: COLORS.up }, { v: t.warning, c: COLORS.warning }, { v: t.down, c: COLORS.down }, { v: t.absent + t.off, c: "#334155" }], 58, 9)}
          <div style="flex:1"><h3>${esc(st.name)}</h3><div class="nets">${st.subnets.map(esc).join(" · ") || "réseaux hors plages déclarées"}</div>
          <div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap"><span class="badge b-up"><span class="sdot s-up"></span>${t.up + t.warning} en ligne</span>${t.down ? `<span class="badge b-down">${t.down} en panne</span>` : ""}${st.alerts ? `<span class="badge b-warning">${st.alerts} alerte(s)</span>` : ""}</div></div>
          <span class="muted" style="font-size:12px">Voir la topologie →</span></div><div class="cats">${cats}</div></div>`;
      }).join("");
      const servers = d.servers.slice().sort((a, b) => Math.max(b.cpu || 0, b.mem || 0, b.disk || 0) - Math.max(a.cpu || 0, a.mem || 0, a.disk || 0)).slice(0, 8);
      const srvHtml = servers.length ? `<table class="t"><thead><tr><th>Serveur</th><th>CPU</th><th>RAM</th><th>Disque</th></tr></thead><tbody>${servers.map((x) =>
        `<tr class="row" data-node="${esc(x.id)}"><td><div class="namecell"><span class="sdot s-${x.status}"></span><b>${esc(x.name)}</b></div></td>
         <td style="width:22%">${bar(x.cpu, 75, 90)}<span class="muted" style="font-size:11px">${fmt.pct(x.cpu)}</span></td>
         <td style="width:22%">${bar(x.mem, 85, 95)}<span class="muted" style="font-size:11px">${fmt.pct(x.mem)}</span></td>
         <td style="width:22%">${bar(x.disk, 80, 90)}<span class="muted" style="font-size:11px">${fmt.pct(x.disk)}</span></td></tr>`).join("")}</tbody></table>`
        : `<div class="notice">Aucun agent installé pour l'instant : installe Alloy sur tes serveurs pour voir CPU, RAM, disques et logs ici.</div>`;
      const alerts = d.alerts.length ? `<div class="alist">${d.alerts.slice(0, 7).map(alertItem).join("")}</div>`
        : `<div class="empty-ok">${icon("check")}<b>Aucun problème en cours</b></div>`;
      const news = d.new_devices.length ? d.new_devices.slice(0, 6).map((n) => `<div class="aitem" data-node="${esc(n.id)}"><span class="sev" style="background:${COLORS.info}"></span><div><b>${esc(n.name)}</b><div class="meta"><span>${esc(n.ip)}</span><span>${esc(n.role_label)}</span><span>${esc(n.site || "")}</span></div></div><span></span></div>`).join("")
        : '<div class="muted">Aucun nouvel appareil depuis 24 h.</div>';
      const svc = d.services.length ? d.services.map((x) => `<div class="meter" style="grid-template-columns:1fr auto auto"><span><span class="sdot s-${x.up === 1 ? "up" : x.up === 0 ? "down" : "unknown"}"></span> ${esc(x.name)}</span>
        <span class="muted">${x.duration_ms != null ? x.duration_ms + " ms" : ""}</span><span class="${x.cert_days != null && x.cert_days < 15 ? "badge b-warning" : "muted"}">${x.cert_days != null ? "cert. " + x.cert_days + " j" : ""}</span></div>`).join("")
        : '<div class="muted">Ajoute tes sites web dans config/netmap.yml (http_checks).</div>';

      el.innerHTML = `
        <div class="grid g-kpi">${kpis.join("")}</div>
        <div class="card mt"><h2>${icon("globe")}Chemin vers Internet <span class="right muted">de ton réseau jusqu'à Internet · latence mesurée en continu</span></h2><div class="path">${pathHtml}</div></div>
        <div class="grid g-main mt">
          <div><div class="grid ${d.sites.length > 1 && !App.state.site ? "g-2" : ""}">${sites}</div>
            <div class="card mt"><h2>${icon("server")}Serveurs les plus chargés <span class="right"><a href="#/inventory">Inventaire →</a></span></h2>${srvHtml}</div></div>
          <div><div class="card"><h2>${icon("bell")}Problèmes en cours <span class="right"><a href="#/alerts">Tout voir →</a></span></h2>${alerts}</div>
            <div class="card mt"><h2>${icon("sparkle")}Nouveaux appareils (24 h)</h2><div class="alist">${news}</div></div>
            <div class="card mt"><h2>${icon("globe")}Services web</h2>${svc}</div></div>
        </div>`;
      bindNodes(el);
      $$(".site-card", el).forEach((c) => c.addEventListener("click", () => { App.state.site = c.dataset.site; App.store.set("site", c.dataset.site); location.hash = "#/topology"; }));
    },
  });

  // ================================================================ VMWARE
  App.register("vmware", {
    async render(el) {
      const d = await api("api/vmware");
      if (!d.configured) {
        el.innerHTML = `<div class="notice"><h3>vCenter n'est pas encore connecté</h3>Avec un compte en <b>lecture seule</b>, le cockpit affiche chaque ESXi, ses VM (CPU, RAM, IP, OS), les datastores, les alarmes vCenter, et sur quel switch / port chaque ESXi est branché (CDP/LLDP).
          <ol><li>Dans vCenter : crée un utilisateur (ex. <code>supervision@vsphere.local</code>) et donne-lui le rôle <b>Read-only</b> à la racine, propagé.</li>
          <li>Dans <code>.env</code> : renseigne <code>VCENTER_URL=https://ton-vcenter/sdk</code>, <code>VCENTER_USER</code>, <code>VCENTER_PASSWORD</code>.</li>
          <li>Relance <code>./setup.sh</code>.</li></ol></div>`;
        return;
      }
      const tot = d.hosts.reduce((a, h) => ({ vms: a.vms + h.vms.length, on: a.on + h.vms_on }), { vms: 0, on: 0 });
      $("#page-sub").textContent = `${d.hosts.length} ESXi · ${tot.on}/${tot.vms} VM allumées${d.up ? "" : " · vCenter injoignable : " + d.error}`;
      const hosts = d.hosts.map((h) => {
        const vms = h.vms.map((v) => `<div class="vm ${v.power !== "poweredOn" ? "off" : ""}" ${v.id ? `data-node="${esc(v.id)}"` : ""} title="${esc(v.os || "")}">
          <b><span class="sdot s-${v.power !== "poweredOn" ? "off" : v.status}"></span>${esc(v.name)}</b>
          <small>${esc(v.ip || (v.power !== "poweredOn" ? "éteinte" : "pas d'IP"))} · ${v.vcpu} vCPU · ${v.mem_gb} Go</small>
          ${v.power === "poweredOn" ? `<div class="mini"><div title="CPU ${fmt.pct(v.cpu_pct)}">${bar(v.cpu_pct, 75, 90)}</div><div title="RAM ${fmt.pct(v.mem_pct)}">${bar(v.mem_pct, 85, 95)}</div></div>` : ""}
          ${v.alerts ? `<span class="badge b-warning" style="position:absolute;top:6px;right:6px;padding:0 6px">${v.alerts}</span>` : ""}</div>`).join("");
        return `<div class="card"><div class="host-head"><div class="host-ic" style="border-color:${COLORS[h.status]}">${icon("layers")}</div>
          <div style="flex:1;min-width:0"><h3 class="click" data-node="${esc(h.id || "")}" style="cursor:pointer">${esc(h.name)}</h3><div class="muted">${esc(h.model)} · ${esc((h.version || "").replace(/ build.*/, ""))}${h.cluster ? " · " + esc(h.cluster) : ""}</div></div>
          <div style="text-align:right">${statusBadge(h.state !== "connected" ? "down" : h.status)}${h.maintenance ? '<div class="badge b-info" style="margin-top:4px">maintenance</div>' : ""}</div></div>
          <div class="host-meters">${meter("CPU", h.cpu_pct, 75, 90)}${meter("RAM", h.mem_pct, 85, 95)}
            <div class="muted" style="font-size:12px">${h.cores} cœurs · ${Math.round(h.cpu_mhz_used / 1000)} / ${Math.round(h.cpu_mhz_total / 1000)} GHz</div>
            <div class="muted" style="font-size:12px">${h.mem_used_gb} / ${h.mem_gb} Go · allumé depuis ${fmt.dur(h.uptime_s)}</div></div>
          ${h.alerts.length ? `<div class="alist" style="margin-bottom:10px">${h.alerts.map((a) => `<div class="aitem" style="cursor:default"><span class="sev" style="background:${COLORS.warning}"></span><div><b>${esc(a)}</b></div><span></span></div>`).join("")}</div>` : ""}
          <h2 style="margin:6px 0 0">${h.vms_on} VM allumées / ${h.vms.length}</h2><div class="vmgrid">${vms}</div></div>`;
      }).join("");
      const ds = d.datastores.map((x) => `<div class="ds"><b>${esc(x.name)} <span class="muted" style="font-weight:400">${esc(x.type || "")}</span></b>
        <div>${bar(x.used_pct, 80, 90)}</div><span class="muted"><b style="color:var(--text)">${fmt.pct(x.used_pct)}</b> · ${fmt.gb(x.free_gb)} libres sur ${fmt.gb(x.capacity_gb)}</span></div>`).join("");
      const alarms = d.alarms.length ? d.alarms.map((a) => `<div class="aitem" style="cursor:default"><span class="sev" style="background:${a.status === "red" ? COLORS.down : COLORS.warning}"></span><div><b>${esc(a.alarm)}</b><div class="meta"><span>${esc(a.entity)}</span>${a.acknowledged ? "<span>acquittée</span>" : ""}</div></div><span></span></div>`).join("")
        : `<div class="empty-ok">${icon("check")}<b>Aucune alarme vCenter</b></div>`;
      el.innerHTML = `<div class="grid g-main"><div class="hosts">${hosts}</div>
        <div><div class="card"><h2>${icon("database")}Datastores</h2>${ds || '<div class="muted">Aucun datastore</div>'}</div>
        <div class="card mt"><h2>${icon("bell")}Alarmes vCenter</h2><div class="alist">${alarms}</div></div></div></div>`;
      el.querySelector(".hosts").style.gridTemplateColumns = "1fr";
      bindNodes(el);
    },
  });

  // ================================================================ SWITCHS
  App.register("switches", {
    async render(el) {
      const d = await api("api/switches");
      $("#page-sub").textContent = `${d.switches.length} switch(s) cartographié(s)${d.snmp.configured ? " · SNMP actif" : ""}`;
      const sw = d.switches.map((s) => {
        const named = s.ports.length >= 8 && s.ports.every((p) => /\d/.test(p.name));
        const grid = named ? `<div class="ports">${s.ports.map((p) => {
          const dev = p.devices[0]; const bad = p.devices.some((x) => ["down", "critical"].includes(x.status));
          const up = p.uplink || (p.mac_count > 6) || (p.devices.some((x) => ["switch", "network", "firewall", "router"].includes(x.role)));
          const cls = dev || p.vms ? `dev${bad ? " bad" : ""}${up ? " uplink" : ""}` : p.up ? "up" : "";
          const tip = `${p.name}${p.alias ? " (" + p.alias + ")" : ""} : ${p.devices.map((x) => x.name + (x.ip ? " " + x.ip : "")).join(", ") || (p.up ? "actif" : "libre")}${p.vms ? ` + ${p.vms} VM` : ""}${p.speed_mbps ? ` · ${p.speed_mbps >= 1000 ? p.speed_mbps / 1000 + " Gb/s" : p.speed_mbps + " Mb/s"}` : ""}${p.in_bps != null ? ` · ↓ ${fmt.bps(p.in_bps)} ↑ ${fmt.bps(p.out_bps)}` : ""}`;
          return `<div class="port ${cls}" title="${esc(tip)}" ${dev ? `data-node="${esc(dev.id)}"` : ""}>${esc((p.name.match(/(\d+)\D*$/) || [, p.name])[1])}</div>`;
        }).join("")}</div>` : "";
        const rows = s.ports.filter((p) => p.devices.length || p.vms).map((p) => `<tr class="row" ${p.devices[0] ? `data-node="${esc(p.devices[0].id)}"` : ""}>
          <td class="mono">${esc(p.name)}</td><td>${p.devices.map((x) => `<div class="namecell"><span class="sdot s-${x.status}"></span>${roleIcon(x.role)}<b>${esc(x.name)}</b><span class="muted mono">${esc(x.ip || "")}</span></div>`).join("")}${p.vms ? `<span class="muted">+ ${p.vms} VM derrière l'ESXi</span>` : ""}</td>
          <td class="muted">${esc(p.alias || "")}</td><td class="muted">${p.speed_mbps ? (p.speed_mbps >= 1000 ? p.speed_mbps / 1000 + " Gb/s" : p.speed_mbps + " Mb/s") : ""}</td>
          <td class="num muted">${p.in_bps != null ? `↓ ${fmt.bps(p.in_bps)} · ↑ ${fmt.bps(p.out_bps)}` : ""}</td><td class="muted">${esc(p.via.join(", "))}</td></tr>`).join("");
        return `<div class="card sw"><div class="sw-head"><div class="host-ic" style="border-color:${COLORS[s.status] || COLORS.unknown}">${icon("switch")}</div>
          <div style="flex:1"><h3 style="margin:0;cursor:pointer" data-node="${esc(s.id)}">${esc(s.name)}</h3><div class="muted" style="font-size:12.5px">${esc(s.ip || "IP inconnue")}${s.model ? " · " + esc(s.model) : ""}${s.site ? " · " + esc(s.site) : ""}</div></div>
          <div style="text-align:right">${statusBadge(s.status)}<div class="muted" style="font-size:12px;margin-top:4px">${s.connected} équipement(s) · ${s.snmp ? "SNMP" : "vu par " + esc(s.sources.join(", "))}</div></div></div>
          ${grid}${named ? `<div class="legend" style="margin-bottom:12px"><span><i class="sq" style="background:rgba(79,140,255,.4)"></i>équipement identifié</span><span><i class="sq" style="background:rgba(124,92,255,.5)"></i>liaison / uplink</span><span><i class="sq" style="background:rgba(34,197,94,.35)"></i>actif, non identifié</span><span><i class="sq" style="background:#0b1222;border:1px solid var(--border)"></i>libre</span></div>` : ""}
          <div style="max-height:380px;overflow:auto"><table class="t"><thead><tr><th>Port</th><th>Branché</th><th>Description</th><th>Vitesse</th><th>Trafic</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
      }).join("");
      const detected = d.detected.length ? `<div class="card mt"><h2>${icon("switch")}Équipements réseau détectés sans détail de ports</h2><table class="t"><tbody>${d.detected.map((n) =>
        `<tr class="row" data-node="${esc(n.id)}"><td><div class="namecell"><span class="sdot s-${n.status}"></span>${roleIcon(n.role)}<b>${esc(n.name)}</b></div></td><td class="mono">${esc(n.ip || "")}</td><td class="muted">${esc(n.role_label)}</td><td class="muted">${esc(n.site || "")}</td></tr>`).join("")}</tbody></table></div>` : "";
      const notice = !d.snmp.configured ? `<div class="notice" style="margin-bottom:16px"><h3>Pour voir chaque port de chaque switch</h3>
        Aujourd'hui, les switchs sont reconnus grâce aux ESXi (CDP/LLDP via vCenter) et aux serveurs Linux (lldpd). Pour la carte complète (qui est branché sur quel port, trafic, ports en erreur),
        demande au prestataire un <b>accès SNMP v2c en lecture seule</b> depuis l'IP de la supervision, puis renseigne dans <code>config/netmap.yml</code> :
        <code>snmp.community</code> et <code>snmp.devices</code> (IP des switchs / firewall).
        ${Object.keys(d.snmp.errors || {}).length ? `<div style="margin-top:8px;color:#fbbf24">Erreurs SNMP : ${Object.entries(d.snmp.errors).map(([k, v]) => esc(k + " : " + v)).join(" · ")}</div>` : ""}</div>` : "";
      el.innerHTML = notice + (sw || `<div class="card muted">Aucun switch cartographié pour l'instant.</div>`) + detected;
      bindNodes(el);
    },
  });

  // ================================================================ INVENTAIRE
  const inv = { q: "", cat: "", status: "", sort: "ip", asc: true };
  const ipKey = (ip) => (ip && /^\d+\.\d+\.\d+\.\d+$/.test(ip) ? ip.split(".").map((x) => x.padStart(3, "0")).join(".") : "zzz");
  App.register("inventory", {
    async render(el, first) {
      const d = await api("api/inventory");
      App.setFeatures(d.features);
      let rows = d.rows.filter((r) => !App.state.site || r.site === App.state.site);
      const cats = {}; rows.forEach((r) => { cats[r.type] = (cats[r.type] || 0) + 1; });
      if (first || !$("#inv-q")) {
        el.innerHTML = `<div class="toolbar"><input id="inv-q" type="search" placeholder="Filtrer : nom, IP, MAC, constructeur, OS…" style="width:320px">
          <select id="inv-cat"></select><select id="inv-status"><option value="">Tous les états</option><option value="up">OK</option><option value="problem">Problèmes</option><option value="absent">Absents / éteints</option><option value="new">Nouveaux</option></select>
          <span class="count" id="inv-count"></span><a class="chip" href="api/inventory.csv" download>${icon("download")} Export CSV</a></div>
          <div class="card" style="padding:0;overflow:auto;max-height:calc(100vh - 170px)"><table class="t" id="inv-t"><thead><tr>
          <th data-k="status">État</th><th data-k="name">Nom</th><th data-k="ip">IP</th><th data-k="mac">MAC</th><th data-k="vendor">Constructeur</th><th data-k="type">Type</th>
          <th data-k="os">Système</th><th data-k="site">Site</th><th data-k="switch">Switch / port</th><th data-k="latency_ms">Latence</th><th data-k="last_seen">Vu</th></tr></thead><tbody></tbody></table></div>`;
        $("#inv-q").value = inv.q; $("#inv-status").value = inv.status;
        $("#inv-q").addEventListener("input", (e) => { inv.q = e.target.value.toLowerCase(); draw(); });
        $("#inv-cat").addEventListener("change", (e) => { inv.cat = e.target.value; draw(); });
        $("#inv-status").addEventListener("change", (e) => { inv.status = e.target.value; draw(); });
        $$("#inv-t th").forEach((th) => th.addEventListener("click", () => { const k = th.dataset.k; inv.asc = inv.sort === k ? !inv.asc : true; inv.sort = k; draw(); }));
      }
      $("#inv-cat").innerHTML = `<option value="">Tous les types</option>` + Object.entries(cats).sort((a, b) => b[1] - a[1]).map(([k, v]) => `<option value="${esc(k)}">${esc(k)} (${v})</option>`).join("");
      $("#inv-cat").value = inv.cat;
      function draw() {
        let r = rows.filter((x) => (!inv.cat || x.type === inv.cat)
          && (!inv.status || (inv.status === "problem" ? ["down", "critical", "warning"].includes(x.status) : inv.status === "absent" ? ["absent", "off"].includes(x.status) : inv.status === "new" ? x.new : x.status === inv.status))
          && (!inv.q || [x.name, x.ip, x.mac, x.vendor, x.os, x.dns, x.netbios, x.switch].some((v) => v && String(v).toLowerCase().includes(inv.q))));
        const k = inv.sort, dir = inv.asc ? 1 : -1;
        r.sort((a, b) => (k === "ip" ? ipKey(a.ip).localeCompare(ipKey(b.ip)) : String(a[k] ?? "").localeCompare(String(b[k] ?? ""), "fr", { numeric: true })) * dir);
        $("#inv-count").textContent = `${r.length} équipement(s)`;
        $$("#inv-t th").forEach((th) => { th.classList.toggle("sorted", th.dataset.k === k); th.classList.toggle("asc", th.dataset.k === k && inv.asc); });
        $("#inv-t tbody").innerHTML = r.map((x) => `<tr class="row" data-node="${esc(x.id)}"><td>${statusBadge(x.status)}</td>
          <td><div class="namecell"><b>${esc(x.name)}</b>${x.new ? '<span class="badge b-info">nouveau</span>' : ""}${x.alerts ? `<span class="badge b-warning">${x.alerts}</span>` : ""}</div>${x.dns && x.dns !== x.name ? `<div class="muted" style="font-size:11.5px">${esc(x.dns)}</div>` : ""}</td>
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
      el.innerHTML = `<div class="toolbar">
          <button class="chip ${!al.sev ? "on" : ""}" data-sev="">Toutes (${all.length})</button>
          <button class="chip ${al.sev === "critical" ? "on" : ""}" data-sev="critical">Critiques (${c.critical})</button>
          <button class="chip ${al.sev === "warning" ? "on" : ""}" data-sev="warning">Attention (${c.warning})</button>
          <button class="chip ${al.sev === "info" ? "on" : ""}" data-sev="info">Info (${c.info})</button>
          <span style="width:12px"></span>${srcs.map((s) => `<button class="chip ${al.src === s ? "on" : ""}" data-src="${esc(s)}">${esc(s)}</button>`).join("")}
          <span class="count">${f.alertmanager_url ? `<a href="${esc(f.alertmanager_url)}/#/silences/new" target="_blank">Mettre en silence ↗</a>` : ""}</span>
          ${f.ai ? `<button class="ai" id="al-ai">${App.svg("sparkle")}Analyser la situation</button>` : ""}</div>
        <div id="al-ai-out"></div>
        <div class="card">${list.length ? `<div class="alist">${list.map((a) => alertItem(a).replace('<div class="when">', `<div class="when">${a.description ? `<div style="max-width:360px;white-space:normal;text-align:right">${esc(a.description)}</div>` : ""}`)).join("")}</div>`
          : `<div class="empty-ok">${icon("check")}<b>Aucune alerte${al.sev || al.src ? " pour ce filtre" : " en cours"}</b></div>`}</div>`;
      $$("[data-sev]", el).forEach((b) => b.addEventListener("click", () => { al.sev = b.dataset.sev; App.state.current.render(el); }));
      $$("[data-src]", el).forEach((b) => b.addEventListener("click", () => { al.src = al.src === b.dataset.src ? "" : b.dataset.src; App.state.current.render(el); }));
      const b = $("#al-ai");
      if (b) b.addEventListener("click", async () => {
        b.disabled = true; $("#al-ai-out").innerHTML = '<div class="ai-box"><span class="spinner"></span> Analyse en cours…</div>';
        try { $("#al-ai-out").innerHTML = App.aiBox(await App.post("api/ai/summary", {})) + '<div style="height:14px"></div>'; } catch (e) { $("#al-ai-out").innerHTML = ""; }
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
      el.innerHTML = `<div class="grid g-2">
        <div class="card"><h2>${icon("globe")}Sites et applications web</h2>${d.http.length ? `<table class="t"><thead><tr><th>Nom</th><th>État</th><th>Réponse</th><th>Code</th><th>Certificat</th></tr></thead><tbody>${d.http.map((x) =>
          `<tr><td><b>${esc(x.name)}</b><div class="muted mono" style="font-size:11.5px">${esc(x.url)}</div></td><td>${st(x.up)}</td><td class="num">${x.duration_ms != null ? x.duration_ms + " ms" : "—"}</td><td>${x.code ?? "—"}</td>
           <td>${x.cert_days != null ? `<span class="badge ${x.cert_days < 15 ? "b-warning" : "b-up"}">${x.cert_days} jours</span>` : "—"}</td></tr>`).join("")}</tbody></table>`
          : '<div class="muted">Aucun contrôle HTTP : ajoute tes sites dans <code>config/netmap.yml</code> (http_checks).</div>'}</div>
        <div><div class="card"><h2>${icon("key")}Serveurs DNS</h2><table class="t"><tbody>${d.dns.map((x) => `<tr><td><b>${esc(x.name)}</b> <span class="muted mono">${esc(x.ip)}</span></td><td>${st(x.up)}</td><td class="num">${x.duration_ms != null ? x.duration_ms + " ms" : "—"}</td></tr>`).join("") || '<tr><td class="muted">Aucun</td></tr>'}</tbody></table></div>
        <div class="card mt"><h2>${icon("cloud")}Cibles Internet</h2><table class="t"><tbody>${d.internet.map((x) => `<tr><td><b>${esc(x.name)}</b> <span class="muted mono">${esc(x.ip)}</span></td><td>${st(x.up)}</td><td class="num">${fmt.ms(x.latency_ms)}</td></tr>`).join("")}</tbody></table></div></div></div>`;
    },
  });

  App.init();
})();
