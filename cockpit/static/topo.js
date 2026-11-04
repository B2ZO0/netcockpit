/* Topologie : arbre Internet → passerelle → sites → réseaux → switchs → équipements → VM, plus la mini-carte de la vue d'ensemble */
"use strict";
const Topo = (() => {
  const { COLORS, esc, $, iconUri, fmt, store } = App;
  const MINOR = new Set(["workstations", "phones", "printers", "mobile", "other", "cameras"]);
  const INFRA = new Set(["internet", "isp", "firewall", "gateway", "router", "site", "subnet", "switch", "network", "esxi", "hypervisor", "dc", "wifi"]);
  const ORDER = { internet: 0, isp: 1, firewall: 2, router: 2, gateway: 2, site: 3, subnet: 4, switch: 5, network: 6, wifi: 7, esxi: 8,
    hypervisor: 8, dc: 9, server: 10, nas: 11, vm: 12, linux: 13, windows: 14, group: 20 };
  const opts = Object.assign({ group: true, vms: true, problems: false, ips: true }, store.get("topo", {}));
  const expanded = new Set();
  let cy = null, data = null, sig = "", blinkTimer = null;
  let mini = null;

  const nodeColor = (n) => (n.role === "subnet" ? COLORS.net : n.role === "site" ? COLORS.magenta : (COLORS[n.status] || COLORS.unknown));
  const nodeIcon = (n) => iconUri(n.role === "group" ? n.icon_role : n.role, n.role === "subnet" ? COLORS.net : n.role === "site" ? COLORS.magenta : COLORS.text);

  // ------------------------------------------------------------ styles (recalculés à chaque changement de thème)
  function styles(small) {
    const C = COLORS, f = small ? 1.35 : 1;
    return [
      { selector: "node", style: {
        width: 46, height: 46, "background-color": C.surface, "border-width": 3, "border-color": "data(color)",
        "background-image": "data(icon)", "background-width": "54%", "background-height": "54%",
        label: small ? "" : "data(label)", "text-wrap": "wrap", "text-max-width": 150, color: C.text, "font-size": 11.5 * f,
        "font-family": "B612, sans-serif", "text-valign": "bottom", "text-margin-y": 7, "line-height": 1.25,
        "text-background-color": C.bg, "text-background-opacity": 0.85, "text-background-padding": 2, "text-background-shape": "roundrectangle" } },
      { selector: 'node[role="internet"]', style: { width: 74, height: 74, "font-size": 14 * f, "font-weight": 700, "border-color": C.magenta } },
      { selector: 'node[role="isp"], node[role="firewall"], node[role="gateway"], node[role="router"]', style: { width: 60, height: 60, "font-weight": 700, "font-size": 12.5 * f } },
      { selector: 'node[role="site"]', style: { shape: "round-rectangle", width: 190, height: 52, "background-color": C.raised, "border-width": 2,
        label: "data(label)", "font-size": 14 * f, "font-weight": 700, "text-valign": "center", "text-halign": "center", "text-margin-y": 0, "text-margin-x": 16,
        "background-position-x": "14px", "background-width": 22, "background-height": 22, "text-background-opacity": 0 } },
      { selector: 'node[role="subnet"]', style: { shape: "round-rectangle", width: 180, height: 44, "background-color": C.raised, "border-width": 2,
        "font-size": 12.5 * f, "font-weight": 700, "text-valign": "center", "text-halign": "center", "text-margin-y": 0, "text-margin-x": 14,
        "background-position-x": "12px", "background-width": 20, "background-height": 20, "text-background-opacity": 0 } },
      { selector: 'node[role="switch"], node[role="network"], node[role="esxi"], node[role="hypervisor"]', style: { shape: "round-rectangle", width: 58, height: 50, "font-weight": 700 } },
      { selector: 'node[role="vm"]', style: { width: 36, height: 36, "font-size": 10.5, "border-width": 2.5 } },
      { selector: 'node[role="group"]', style: { shape: "round-rectangle", width: 150, height: 40, "border-style": "dashed",
        "border-width": 2, "text-valign": "center", "text-halign": "center", "text-margin-y": 0, "text-margin-x": 14, "font-size": 11.5,
        "background-position-x": "12px", "background-width": 18, "background-height": 18, "text-background-opacity": 0 } },
      { selector: "node.minor", style: { width: 32, height: 32, "font-size": 10, "border-width": 2 } },
      { selector: 'node[status="absent"], node[status="off"]', style: { opacity: 0.55, "border-style": "dashed" } },
      { selector: "node.problem", style: { "border-width": 5, color: C.down, "z-index": 10 } },
      { selector: "node.problem.blink", style: { "border-width": 12, "border-opacity": 0.45 } },
      { selector: "node:selected, node.hl", style: { "overlay-color": C.magenta, "overlay-opacity": 0.18, "overlay-padding": 9 } },
      { selector: "edge", style: { width: 1.6, "line-color": C.line2, "curve-style": "taxi", "taxi-direction": "downward", "taxi-turn": 34,
        label: "data(label)", "font-size": 9.5, "font-family": "B612 Mono, monospace", color: C.violet, "text-background-color": C.bg,
        "text-background-opacity": 0.9, "text-background-padding": 2, "text-opacity": 0, "source-endpoint": "outside-to-node", "target-endpoint": "outside-to-node" } },
      { selector: 'edge[kind="route"]', style: { width: 4, "line-color": C.magenta, "curve-style": "bezier" } },
      { selector: 'edge[kind="site"]', style: { width: 3, "line-color": C.violet } },
      { selector: 'edge[kind="switch"]', style: { width: 2.6, "line-color": C.violet, "line-opacity": 0.75 } },
      { selector: 'edge[kind="lan"]', style: { "line-style": "dashed", "line-dash-pattern": [4, 4], "line-color": C.line2 } },
      { selector: 'edge[kind="vm"]', style: { width: 1.2, "line-color": C.line2 } },
      { selector: 'edge[kind="extra"]', style: { "line-style": "dotted", "line-color": C.violet, "curve-style": "bezier" } },
      { selector: 'edge[status="down"]', style: { "line-color": C.down, "line-style": "dashed", width: 2.6 } },
      { selector: "edge.lbl", style: { "text-opacity": 1 } },
      { selector: ".faded", style: { opacity: 0.12 } },
    ].concat(small ? [{ selector: 'node[role="site"], node[role="subnet"]', style: { label: "data(short)", width: 170, height: 44, "font-size": 16, "text-max-width": 130, "text-wrap": "ellipsis" } },
      { selector: 'node[role="internet"], node[role="isp"], node[role="firewall"], node[role="gateway"], node[role="router"], node[role="switch"], node[role="esxi"], node.problem',
      style: { label: "data(short)", "font-size": 17, "text-max-width": 150, "text-wrap": "ellipsis", "text-margin-y": 6 } }] : []);
  }
  App.onRestyle(() => {
    [cy, mini].forEach((c) => {
      if (!c) return;
      c.style(styles(c === mini).concat(c === mini ? [{ selector: "edge", style: { "taxi-direction": "rightward", "taxi-turn": 40 } }] : []));
      c.nodes().forEach((n) => { const d = n.data("_n"); if (d) n.data({ color: nodeColor(d), icon: nodeIcon(d) }); });
    });
  });

  function build(container) {
    container.innerHTML = `
      <div id="topo"></div>
      <div class="topo-bar">
        <div class="floating">
          <label><input type="checkbox" id="o-group"> ${t("tp.group")}</label>
          <label><input type="checkbox" id="o-vms"> ${t("tp.vms")}</label>
          <label><input type="checkbox" id="o-ips"> ${t("tp.ips")}</label>
          <label><input type="checkbox" id="o-problems"> ${t("tp.problems")}</label>
        </div>
        <div class="floating"><button class="sm" id="o-fit">${t("tp.fit")}</button><button class="sm" id="o-png">${t("tp.png")}</button></div>
        <div class="floating topo-stats" id="topo-stats"></div>
      </div>
      <div class="floating topo-legend">
        <span>${App.lamp("up")}${t("status.up")}</span><span>${App.lamp("warning")}${t("status.warning")}</span><span>${App.lamp("down")}${t("status.down")}</span>
        <span>${App.lamp("absent")}${t("tp.legAbsent")}</span><span><i class="ln"></i>${t("tp.legSeen")}</span><span><i class="ln dash"></i>${t("tp.legLan")}</span>
        <span class="dim">${t("tp.hint")}</span>
      </div>`;
    for (const k of ["group", "vms", "ips", "problems"]) {
      const el = $(`#o-${k}`); el.checked = opts[k];
      el.addEventListener("change", () => { opts[k] = el.checked; store.set("topo", opts); sig = ""; draw(); });
    }
    $("#o-fit").addEventListener("click", () => cy && cy.animate({ fit: { padding: 50 } }, { duration: 400 }));
    $("#o-png").addEventListener("click", () => {
      const a = document.createElement("a"); a.href = cy.png({ full: true, scale: 2, bg: COLORS.bg });
      a.download = `topology-${new Date().toISOString().slice(0, 10)}.png`; a.click();
    });
    cy = cytoscape({ container: $("#topo"), wheelSensitivity: 0.25, minZoom: 0.05, maxZoom: 2.5, boxSelectionEnabled: false, style: styles(false) });
    cy.on("tap", "node", (e) => {
      const n = e.target;
      if (n.data("role") === "group") { const k = n.id(); expanded.has(k) ? expanded.delete(k) : expanded.add(k); sig = ""; draw(); return; }
      App.openNode(n.id());
    });
    cy.on("tap", (e) => { if (e.target === cy) cy.elements().removeClass("faded"); });
    cy.on("zoom", labels);
    clearInterval(blinkTimer);
    if (!matchMedia("(prefers-reduced-motion: reduce)").matches) blinkTimer = setInterval(() => cy && cy.nodes(".problem").toggleClass("blink"), 800);
  }

  function labels() { const z = cy.zoom() > 0.9; cy.edges().forEach((e) => e.toggleClass("lbl", z && !!e.data("label"))); }

  // ------------------------------------------------------------ préparation (groupes, filtres)
  function prepare(d) {
    const byId = new Map(d.nodes.map((n) => [n.id, n]));
    const kids = new Map();
    d.nodes.forEach((n) => { if (n.parent && byId.has(n.parent)) { if (!kids.has(n.parent)) kids.set(n.parent, []); kids.get(n.parent).push(n); } });
    const nodes = d.nodes.filter((n) => opts.vms || n.role !== "vm" || ["down", "critical", "warning"].includes(n.status));
    const keepIds = new Set(nodes.map((n) => n.id));
    const out = [], groups = new Map();
    for (const n of nodes) {
      const isLeaf = !kids.has(n.id);
      if (opts.group && MINOR.has(n.category) && isLeaf && n.parent) {
        const gid = `grp:${n.parent}:${n.category}`;
        const sib = (kids.get(n.parent) || []).filter((s) => s.category === n.category && !kids.has(s.id));
        if (sib.length >= 4 && !expanded.has(gid)) {
          if (!groups.has(gid)) groups.set(gid, { id: gid, parent: n.parent, role: "group", category: n.category, members: [], link_kind: n.link_kind });
          groups.get(gid).members.push(n); continue;
        }
      }
      out.push(n);
    }
    for (const g of groups.values()) {
      const c = { down: 0, absent: 0, warning: 0 };
      g.members.forEach((m) => { if (m.status === "down" || m.status === "critical") c.down++; else if (m.status === "absent" || m.status === "off") c.absent++; else if (m.status === "warning") c.warning++; });
      const [one, many] = t(`grp.${g.category}`) instanceof Array ? t(`grp.${g.category}`) : t("grp.other");
      g.name = `${g.members.length} ${g.members.length > 1 ? many : one}`;
      g.sub = [c.down && t("grp.down", { n: c.down }), c.warning && t("grp.warn", { n: c.warning }), c.absent && t("grp.absent", { n: c.absent })].filter(Boolean).join(", ");
      g.status = c.down ? "down" : c.warning ? "warning" : "up";
      g.icon_role = { workstations: "windows", phones: "phone", printers: "printer", cameras: "camera", mobile: "mobile" }[g.category] || "device";
      out.push(g);
    }
    if (opts.problems) {
      const keep = new Set(["internet"]);
      const byOut = new Map(out.map((n) => [n.id, n]));
      out.filter((n) => ["down", "critical", "warning"].includes(n.status) || (n.alerts && n.alerts.length)).forEach((n) => {
        let p = n.id; while (p && !keep.has(p)) { keep.add(p); p = byOut.get(p) && byOut.get(p).parent; }
      });
      return out.filter((n) => keep.has(n.id));
    }
    return out.filter((n) => !n.parent || keepIds.has(n.parent) || n.id.startsWith("grp:"));
  }

  // ------------------------------------------------------------ placement en arbre (maison)
  function layout(nodes) {
    const byId = new Map(nodes.map((n) => [n.id, n]));
    const kids = new Map();
    const roots = [];
    nodes.forEach((n) => {
      if (n.parent && byId.has(n.parent)) { if (!kids.has(n.parent)) kids.set(n.parent, []); kids.get(n.parent).push(n); }
      else roots.push(n);
    });
    const sortK = (a, b) => (ORDER[a.role] ?? 15) - (ORDER[b.role] ?? 15) || (b._size || 0) - (a._size || 0) || String(a.name).localeCompare(String(b.name), "fr", { numeric: true });
    const W = 150, H = 150, GW = 118, GH = 88;
    const pos = {};
    function size(n) {
      const ch = (kids.get(n.id) || []).sort(sortK);
      ch.forEach(size);
      n._size = ch.reduce((a, c) => a + (c._size || 1), 0) || 1;
      n._subs = ch.filter((c) => kids.has(c.id));
      n._leaves = ch.filter((c) => !kids.has(c.id));
      const nl = n._leaves.length;
      n._cols = nl >= 4 ? Math.min(nl, Math.max(2, Math.ceil(Math.sqrt(nl * (n._subs.length ? 1.2 : 2))))) : nl;
      n._blockW = nl ? n._cols * GW + (nl >= 4 ? 30 : 0) : 0;
      const minW = W + (n.role === "site" || n.role === "subnet" ? 60 : 0);
      n._w = Math.max(minW, n._subs.reduce((a, c) => a + c._w, 0) + n._blockW);
    }
    function place(n, x, depth) {
      const childXs = [];
      let cx = x + Math.max(0, (n._w - (n._subs.reduce((a, c) => a + c._w, 0) + n._blockW)) / 2);
      const half = Math.ceil(n._subs.length / 2);
      const left = n._subs.slice(0, half), right = n._subs.slice(half);
      left.forEach((c) => { place(c, cx, depth + 1); childXs.push(pos[c.id].x); cx += c._w; });
      if (n._leaves.length) {
        const cols = n._cols, bx = cx + (n._blockW - (cols - 1) * GW) / 2;
        n._leaves.forEach((c, i) => {
          pos[c.id] = { x: bx + (i % cols) * GW, y: (depth + 1) * H + Math.floor(i / cols) * GH };
          if (i < cols) childXs.push(pos[c.id].x);
        });
        cx += n._blockW;
      }
      right.forEach((c) => { place(c, cx, depth + 1); childXs.push(pos[c.id].x); cx += c._w; });
      pos[n.id] = { x: childXs.length ? (Math.min(...childXs) + Math.max(...childXs)) / 2 : x + n._w / 2, y: depth * H };
    }
    roots.sort(sortK);
    roots.forEach(size);
    let x = 0;
    roots.forEach((r) => { place(r, x, 0); x += r._w + 80; });
    return pos;
  }

  // ------------------------------------------------------------ rendu
  function label(n) {
    if (n.role === "group") return n.sub ? `${n.name}\n${n.sub}` : n.name;
    if (n.role === "site" || n.role === "subnet") return App.nm(n.name);
    const ip = opts.ips && n.ip && n.ip !== n.name ? `\n${n.ip}` : "";
    const lat = n.role === "isp" && n.latency_ms != null ? `, ${fmt.ms(n.latency_ms)}` : "";
    return `${App.nm(n.name)}${ip}${lat}`;
  }

  function sync(c, nodes, extra, pos) {
    const ids = new Set(nodes.map((n) => n.id));
    c.batch(() => {
      c.elements().forEach((el) => { if (!ids.has(el.isNode() ? el.id() : el.data("child"))) el.remove(); });
      nodes.forEach((n) => {
        const d = { id: n.id, label: label(n), short: App.nm(n.name) || "", role: n.role, status: n.status, color: nodeColor(n), icon: nodeIcon(n), _n: n };
        let el = c.getElementById(n.id);
        if (el.empty()) el = c.add({ group: "nodes", data: d, position: pos ? pos[n.id] : { x: 0, y: 0 } });
        else el.data(d);
        el.toggleClass("problem", n.status === "down" || n.status === "critical");
        el.toggleClass("minor", MINOR.has(n.category) && !["group", "site", "subnet", "internet", "isp"].includes(n.role));
      });
      nodes.forEach((n) => {
        if (n.parent && ids.has(n.parent)) {
          const eid = `e:${n.parent}>${n.id}`;
          const ed = { id: eid, source: n.parent, target: n.id, child: n.id, kind: n.link_kind || "lan", label: n.link || "",
            status: ["down", "critical"].includes(n.status) && n.role !== "group" ? "down" : "up" };
          const e = c.getElementById(eid); if (e.empty()) c.add({ group: "edges", data: ed }); else e.data(ed);
        }
      });
      (extra || []).forEach((x, i) => {
        if (!ids.has(x.source) || !ids.has(x.target)) return;
        const eid = `x:${i}:${x.source}>${x.target}`;
        if (c.getElementById(eid).empty()) c.add({ group: "edges", data: { id: eid, source: x.source, target: x.target, child: x.target, kind: "extra", label: x.label || "" } });
      });
    });
    if (pos) c.nodes().forEach((n) => { if (pos[n.id()]) n.position(pos[n.id()]); });
  }

  function draw() {
    if (!data || !cy) return;
    const nodes = prepare(data);
    const newSig = nodes.map((n) => n.id).sort().join("|");
    const relayout = newSig !== sig; sig = newSig;
    const pos = relayout ? layout(nodes) : null;
    sync(cy, nodes, data.extra_edges, pos);
    if (relayout) {
      cy.fit(undefined, 50);
      if (cy.zoom() < 0.62) {          // trop large : on garde une taille lisible, en haut de l'arbre
        cy.zoom(0.62);
        const bb = cy.elements().boundingBox();
        cy.pan({ x: cy.width() / 2 - ((bb.x1 + bb.x2) / 2) * cy.zoom(), y: 90 - bb.y1 * cy.zoom() });
      }
    }
    labels();
    const s = data.stats || {};
    $("#topo-stats").innerHTML = `<span><b>${s.total ?? 0}</b> <span class="muted">${t("tp.devices")}</span></span>
      <span style="color:var(--up)"><b>${s.up ?? 0}</b> ${t("tp.ok")}</span>
      <span style="color:${s.down ? "var(--down)" : "var(--muted)"}"><b>${s.down ?? 0}</b> ${t("tp.down")}</span>
      <span style="color:${s.warning ? "var(--warning)" : "var(--muted)"}"><b>${s.warning ?? 0}</b> ${t("tp.alerts")}</span>
      <span class="muted"><b>${s.absent ?? 0}</b> ${t("tp.absent")}</span>`;
  }

  function highlight(id) {
    if (!cy) return;
    cy.nodes().removeClass("hl");
    if (!id) return;
    const el = cy.getElementById(id);
    if (!el.empty()) { el.addClass("hl"); cy.animate({ center: { eles: el } }, { duration: 350 }); }
  }

  // ------------------------------------------------------------ mini-carte : l'ossature de l'infra + ce qui est en panne
  let miniSig = "";
  function drawMini(container, d) {
    if (!container) return;
    const byId = new Map(d.nodes.map((n) => [n.id, n]));
    const keep = (n) => INFRA.has(n.role) || ["down", "critical"].includes(n.status);
    const nodes = d.nodes.filter(keep).map((n) => {
      let p = n.parent;
      while (p && byId.has(p) && !keep(byId.get(p))) p = byId.get(p).parent;
      return Object.assign({}, n, { parent: p && byId.has(p) ? p : null });
    });
    if (!mini || mini.container() !== container) {
      if (mini) mini.destroy();
      mini = cytoscape({ container, style: styles(true).concat([{ selector: "edge", style: { "taxi-direction": "rightward", "taxi-turn": 40 } }]), userZoomingEnabled: false, userPanningEnabled: false, boxSelectionEnabled: false, autoungrabify: true });
      mini.on("tap", "node", (e) => App.openNode(e.target.id()));
      miniSig = "";
    }
    const s = nodes.map((n) => n.id).sort().join("|");
    let pos = s !== miniSig ? layout(nodes) : null;
    if (pos) Object.values(pos).forEach((q) => { const x = q.x; q.x = q.y * 1.4; q.y = x * 0.5; });   // arbre couché : de gauche à droite
    miniSig = s;
    sync(mini, nodes, [], pos);
    mini.resize(); mini.fit(undefined, 16);
  }
  function dropMini() { if (mini) { mini.destroy(); mini = null; } }

  App.register("topology", {
    full: true,
    async render(container, first) {
      if (first || !cy || !document.getElementById("topo")) { sig = ""; if (cy) cy.destroy(); build(container); }
      data = await App.api("api/graph");
      App.setFeatures(data.features);
      $("#page-sub").textContent = App.state.site ? t("tp.site", { s: App.state.site }) : t("top.allSites");
      draw();
    },
    leave() { clearInterval(blinkTimer); if (cy) { cy.destroy(); cy = null; } },
  });
  return { highlight, drawMini, dropMini };
})();
