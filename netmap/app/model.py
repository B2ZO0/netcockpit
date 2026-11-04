"""Modèle unifié : fusion des sources, arbre hiérarchique, états, vues (inventaire, VMware, switchs...)."""
import ipaddress
import re
import time
from datetime import datetime

import config as C
import snmp as S
from scanner import ROLE_LABELS, classify, is_private

RETAIN_SECONDS = 7 * 86400
IMPORTANT = {"firewall", "router", "gateway", "switch", "network", "wifi", "esxi", "hypervisor", "server", "dc", "nas", "vm"}
CATEGORY = {
    "server": "servers", "dc": "servers", "vm": "servers", "esxi": "servers", "hypervisor": "servers", "nas": "servers",
    "linux": "servers", "windows": "workstations", "device": "other", "mobile": "mobile",
    "printer": "printers", "phone": "phones", "camera": "cameras", "wifi": "network", "network": "network",
    "switch": "network", "firewall": "network", "router": "network", "gateway": "network", "other": "other",
}
CATEGORY_LABELS = {"servers": "Serveurs", "workstations": "Postes", "printers": "Imprimantes", "phones": "Téléphones IP",
                   "cameras": "Caméras", "network": "Réseau", "mobile": "Mobiles", "other": "Autres"}
SEV_RANK = {"critical": 3, "warning": 2, "info": 1}


def norm(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def short(name, strip=True):
    if not name:
        return None
    name = str(name).strip().rstrip(".")
    if strip and not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", name):
        name = name.split(".")[0]
    return name


def switch_name(name):
    if not name:
        return name
    name = re.sub(r"\(.*\)$", "", str(name)).strip()
    if re.fullmatch(r"[0-9a-fA-F:.-]{11,}", name) or re.fullmatch(r"\d+\.\d+\.\d+\.\d+", name):
        return name
    return name.split(".")[0]


def short_os(o):
    if not o:
        return o
    o = re.sub(r"^Microsoft\s+", "", str(o))
    o = re.sub(r"\s*\((64|32)-bit\)|\s+build-\d+|\s+or later", "", o)
    return o.replace("Other 3.x Linux", "Linux").strip()


def iso_ts(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def port_sort_key(name):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name or "")]


class Model:
    def __init__(self, cfg):
        self.cfg = cfg
        self.nodes = {}
        self.extra_edges = []
        self.switch_ports = {}      # switch_id -> {port_name: {...}}
        self.strip = cfg["names"].get("strip_domain", True)

    # ------------------------------------------------------------ primitives
    def node(self, nid, **kw):
        n = self.nodes.get(nid)
        if n is None:
            n = self.nodes[nid] = {"id": nid, "name": None, "ip": None, "role": "device", "sources": [], "parent": None,
                                   "link": None, "link_kind": None, "critical": False, "alert": False, "details": {},
                                   "alerts": [], "mac": None, "vendor": None, "dns": None, "netbios": None, "os": None,
                                   "ports": [], "site": None, "subnet": None}
        for k, v in kw.items():
            if v is None or v == "":
                continue
            if k == "source":
                if v not in n["sources"]:
                    n["sources"].append(v)
            elif k == "details":
                n["details"].update({a: b for a, b in v.items() if b not in (None, "", [])})
            elif k in ("critical", "alert"):
                n[k] = n[k] or bool(v)
            else:
                n[k] = v
        return n

    def by_ip(self, ip):
        return f"ip:{ip}"

    def set_parent(self, child, parent, label=None, kind="lan", force=False):
        if child not in self.nodes or parent not in self.nodes or child == parent:
            return
        n = self.nodes[child]
        if n["parent"] and not force:
            if n["parent"] != parent:
                self.extra_edges.append({"source": parent, "target": child, "label": label, "kind": kind})
            return
        # évite les cycles
        p = parent
        seen = set()
        while p:
            if p == child or p in seen:
                return
            seen.add(p)
            p = self.nodes[p]["parent"] if p in self.nodes else None
        n["parent"], n["link"], n["link_kind"] = parent, label, kind

    def find_name(self, name):
        if not name:
            return None
        key = short(name).lower()
        for n in self.nodes.values():
            for cand in (n.get("name"), n.get("dns"), n.get("netbios"), n.get("agent"), n["details"].get("vm_hostname")):
                if cand and short(cand).lower() == key:
                    return n["id"]
        return None

    def subnet_node(self, ip):
        site, subnet = C.site_of(self.cfg, ip)
        if subnet is None:
            subnet = "autres"
        nid = f"net:{subnet}"
        if nid not in self.nodes:
            known = site is not None
            self.node(nid, name=self.cfg["subnet_names"].get(subnet) or subnet, role="subnet", subnet=subnet,
                      site=site or "Autres réseaux",
                      details={"réseau": subnet, "scanné": "oui" if known else "non (hors plages déclarées)"})
        return nid

    def site_node(self, site):
        nid = f"site:{norm(site)}"
        if nid not in self.nodes:
            self.node(nid, name=site, role="site", site=site)
        return nid


def display_name(n, ov=None):
    if ov and ov.get("name"):
        return ov["name"]
    return n.get("agent") or n["details"].get("vm_name") or n["details"].get("esx_name") or n.get("dns") or n.get("netbios") or n.get("name") or n.get("ip") or n["id"]


def build(cfg, scan, vc, snmp_state, agents, lldp, now=None):
    """Construit le modèle (sans les états en direct)."""
    now = now or time.time()
    m = Model(cfg)
    strip = m.strip
    last_scan = scan.get("last_scan") or 0
    scan_start = scan.get("scan_started") or last_scan

    # 1. Scan
    for ip, d in (scan.get("devices") or {}).items():
        if now - d.get("last_seen", now) > RETAIN_SECONDS:
            continue
        site, subnet = C.site_of(cfg, ip)
        role = classify(d)
        m.node(m.by_ip(ip), ip=ip, role=role, source="scan", mac=d.get("mac"), vendor=d.get("vendor") or d.get("netbios_vendor"),
               dns=short(d.get("hostname"), strip), netbios=d.get("netbios"), ports=d.get("ports") or [],
               site=site, subnet=subnet, first_seen=d.get("first_seen"), last_seen=d.get("last_seen"),
               present=d.get("last_seen", 0) >= scan_start - 5, new=bool(d.get("new")),
               details={"fqdn": d.get("hostname")})
        if role == "dc":
            m.nodes[m.by_ip(ip)]["critical"] = True

    # 2. Équipements déclarés
    for w in cfg["watch"]:
        ip = str(w.get("ip"))
        site, subnet = C.site_of(cfg, ip)
        m.node(m.by_ip(ip), ip=ip, role=w.get("role") or "other", name=w.get("name"), source="config",
               critical=True, alert=True, site=site, subnet=subnet, watch_name=w.get("name"))

    # 3. vCenter
    host_ids = {}
    if vc and vc.get("hosts"):
        for h in vc["hosts"]:
            ip = h["ips"][0] if h.get("ips") else None
            nid = m.by_ip(ip) if ip else f"esx:{norm(h['name'])}"
            site, subnet = C.site_of(cfg, ip) if ip else (None, None)
            m.node(nid, ip=ip, role="esxi", source="vcenter", critical=True, alert=True, site=site, subnet=subnet,
                   esxi=h, vc_state=h.get("state"), details={"esx_name": short(h["name"], strip)},
                   os=short_os(h.get("version")))
            host_ids[h["name"]] = nid
        for v in vc.get("vms") or []:
            ips = v.get("ips") or []
            known = [i for i in ips if C.site_of(cfg, i)[0]]
            ip = known[0] if known else (ips[0] if ips else None)
            nid = m.by_ip(ip) if ip else f"vm:{norm(v['name'])}"
            site, subnet = C.site_of(cfg, ip) if ip else (None, None)
            existing = m.nodes.get(nid)
            m.node(nid, ip=ip, role="vm", source="vcenter", alert=v.get("power") == "poweredOn", site=site, subnet=subnet,
                   vm=v, vm_power=v.get("power"), os=short_os(v.get("os")) or (existing or {}).get("os"),
                   mac=(existing or {}).get("mac") or ((v.get("macs") or [None])[0]), vendor=(existing or {}).get("vendor") or "VMware",
                   details={"vm_name": v["name"], "vm_hostname": v.get("hostname"),
                            "autres IP": ", ".join(i for i in ips if i != ip)})
            if v.get("host") in host_ids:
                m.set_parent(nid, host_ids[v["host"]], kind="vm", force=True)

    # 4. Agents (Alloy)
    for a in agents:
        nid = m.by_ip(a["ip"]) if a.get("ip") else (m.find_name(a["instance"]) or f"agent:{norm(a['instance'])}")
        existing = m.nodes.get(nid)
        role = existing["role"] if existing and existing["role"] in ("vm", "esxi", "dc", "nas") else "server"
        site, subnet = C.site_of(cfg, a.get("ip")) if a.get("ip") else (None, None)
        m.node(nid, ip=a.get("ip"), role=role, source="agent", alert=True, agent=a["instance"], agent_os=a.get("os"),
               agent_alive=a.get("alive"), site=site, subnet=subnet,
               os=None if existing and existing.get("os") else ("Windows" if a.get("os") == "windows" else "Linux"))

    # Surcharges manuelles
    for ip, ov in cfg["overrides"].items():
        nid = m.by_ip(ip)
        if nid in m.nodes and isinstance(ov, dict):
            if ov.get("role"):
                m.nodes[nid]["role"] = ov["role"]
            if ov.get("name"):
                m.nodes[nid]["override_name"] = ov["name"]

    # Noms affichés
    for n in m.nodes.values():
        if n["role"] in ("subnet", "site"):
            continue
        n["name"] = n.get("override_name") or n.get("watch_name") or display_name(n)

    # 5. Internet, opérateur, passerelles
    m.node("internet", name="Internet", role="internet", critical=True)
    gw = scan.get("gateway")
    top_lan = None
    paths = scan.get("paths") or {}
    for target, hops in paths.items():
        chain = []
        for hop in hops:
            if hop is None:
                continue
            if is_private(hop):
                chain.append(hop)
            else:
                isp = f"isp:{hop}"
                m.node(isp, ip=hop, name=f"Opérateur ({hop})", role="isp", source="traceroute")
                m.set_parent(isp, "internet", kind="route")
                parent = isp
                break
        else:
            parent = "internet"
        for i, hop in enumerate(reversed(chain)):
            hid = m.by_ip(hop)
            existing = m.nodes.get(hid)
            role = existing["role"] if existing and existing["role"] in ("firewall", "router", "network") else "gateway"
            site, subnet = C.site_of(cfg, hop)
            nm = existing["name"] if existing and existing.get("name") and existing["name"] != hop else (
                f"Passerelle {hop}" if hop == gw else f"Routeur {hop}")
            m.node(hid, ip=hop, role=role, name=nm, source="traceroute", critical=True, alert=True, site=site, subnet=subnet)
            m.set_parent(hid, parent, kind="route", force=True)
            parent = hid
        top_lan = top_lan or (m.by_ip(chain[0]) if chain else None)
    if gw and not top_lan:
        gid = m.by_ip(gw)
        site, subnet = C.site_of(cfg, gw)
        ex = m.nodes.get(gid)
        m.node(gid, ip=gw, role=ex["role"] if ex and ex["role"] in ("firewall", "router") else "gateway",
               name=ex["name"] if ex and ex.get("name") and ex["name"] != gw else f"Passerelle {gw}",
               critical=True, alert=True, site=site, subnet=subnet, source="route")
        m.set_parent(gid, "internet", kind="route", force=True)
        top_lan = gid
    top_lan = top_lan or "internet"

    # 6. Sites et réseaux
    multi_site = len(cfg["sites"]) > 1
    for s in cfg["sites"]:
        sid = m.site_node(s["name"]) if multi_site else None
        if sid:
            m.set_parent(sid, top_lan, kind="site", force=True)
        for net in s["subnets"]:
            nid = m.subnet_node(net.split("/")[0])
            m.set_parent(nid, sid or top_lan, kind="lan" if sid else "route", force=True)

    # 7. Switchs : CDP/LLDP vus par les ESXi (vCenter), LLDP des agents, SNMP
    def switch_id(name, ip):
        name = switch_name(name)
        if ip and m.by_ip(ip) in m.nodes:
            return m.by_ip(ip)
        if name:
            nid = f"sw:{norm(name)}"
            if nid in m.nodes:
                return nid
            for n in m.nodes.values():
                if n["role"] in ("switch", "network", "firewall", "router", "wifi") and n.get("name") and short(n["name"]).lower() == name.lower():
                    return n["id"]
        return None

    def ensure_switch(name, ip, model=None, via=None):
        name = switch_name(name)
        sid = switch_id(name, ip)
        if sid is None:
            sid = m.by_ip(ip) if ip else f"sw:{norm(name)}"
        site, subnet = C.site_of(cfg, ip) if ip else (None, None)
        ex = m.nodes.get(sid)
        role = ex["role"] if ex and ex["role"] in ("firewall", "router") else "switch"
        m.node(sid, ip=ip, role=role, source=(via or "lldp").lower(), alert=True, site=site, subnet=subnet,
               details={"modèle": model})
        n = m.nodes[sid]
        if not n.get("name") or n["name"] in (ip, sid) or (name and n["name"] == n.get("ip")):
            n["name"] = name or ip
        return sid

    def add_port(sid, port, target, via, extra=None):
        ports = m.switch_ports.setdefault(sid, {})
        p = ports.setdefault(port or "?", {"name": port or "?", "devices": [], "via": set()})
        if target and target not in p["devices"]:
            p["devices"].append(target)
        p["via"].add(via)
        if extra:
            p.update(extra)

    links = []
    for l in (vc or {}).get("links") or []:
        t = host_ids.get(l["host"])
        if t:
            sid = ensure_switch(l.get("switch"), l.get("switch_ip"), l.get("platform"), l.get("proto"))
            links.append((sid, f"{l.get('port')}", t, f"{l.get('proto')} (ESXi {l.get('nic')})"))
    for l in lldp:
        t = m.by_ip(l["ip"]) if l.get("ip") and m.by_ip(l["ip"]) in m.nodes else m.find_name(l.get("instance"))
        if t and (l.get("chassis_name") or l.get("chassis_id")):
            sid = ensure_switch(l.get("chassis_name") or l.get("chassis_id"), l.get("mgmt_ip") or None, None, l.get("protocol") or "LLDP")
            links.append((sid, l.get("port_descr") or l.get("port_id"), t, f"{l.get('protocol') or 'LLDP'} ({l.get('interface')})"))

    snmp_devices = (snmp_state or {}).get("devices") or []
    if snmp_devices:
        for d in snmp_devices:
            sid = ensure_switch(d["name"], d["ip"], d.get("descr"), "SNMP")
            m.nodes[sid]["snmp"] = True
            for p in d["ports"]:
                add_port(sid, p["name"], None, "SNMP", {"alias": p.get("alias"), "up": p.get("up"),
                                                        "speed_mbps": p.get("speed_mbps"), "mac_count": len(p.get("macs") or [])})
        mac_to_node = {}
        for n in m.nodes.values():
            if n.get("mac"):
                mac_to_node[n["mac"]] = n["id"]
            for mac in (n.get("vm") or {}).get("macs") or []:
                mac_to_node.setdefault(mac, n["id"])
        for d in snmp_devices:  # ARP des routeurs : MAC des réseaux distants
            for ip, mac in (d.get("arp") or {}).items():
                nid = m.by_ip(ip)
                if nid in m.nodes and not m.nodes[nid].get("mac"):
                    m.nodes[nid]["mac"] = mac
                mac_to_node.setdefault(mac, nid if nid in m.nodes else None)
        mac_to_node = {k: v for k, v in mac_to_node.items() if v}
        for sid, port, tid, proto in S.build_links(snmp_devices, mac_to_node, switch_id):
            links.append((sid, port, tid, f"SNMP ({proto})"))

    # Arbre des switchs : liens switch-switch, racine = le plus connecté
    sw_ids = {sid for sid, _, _, _ in links}
    sw_adj = {}
    for sid, port, tid, via in links:
        if m.nodes.get(tid, {}).get("role") == "vm":     # VM vue derrière son ESXi : comptée, pas listée
            p = m.switch_ports.setdefault(sid, {}).setdefault(port or "?", {"name": port or "?", "devices": [], "via": set()})
            p["vms"] = p.get("vms", 0) + 1
            continue
        add_port(sid, port, tid, via)
        if tid in sw_ids or (m.nodes.get(tid, {}).get("role") == "switch"):
            sw_adj.setdefault(sid, set()).add(tid)
            sw_adj.setdefault(tid, set()).add(sid)
    placed = set()
    for root in sorted(sw_adj, key=lambda s: -len(sw_adj[s])):
        if root in placed:
            continue
        m.set_parent(root, m.subnet_node(m.nodes[root].get("ip") or ""), kind="lan")
        queue = [root]
        placed.add(root)
        while queue:
            cur = queue.pop(0)
            for nb in sorted(sw_adj.get(cur, ())):
                if nb not in placed:
                    port = next((p for s, p, t, _ in links if s == cur and t == nb), None) or \
                        next((p for s, p, t, _ in links if s == nb and t == cur), None)
                    m.set_parent(nb, cur, label=port, kind="switch", force=True)
                    placed.add(nb)
                    queue.append(nb)
    for sid, port, tid, via in links:
        if tid in placed and m.nodes[tid]["parent"]:
            continue
        if m.nodes.get(tid, {}).get("role") == "vm":
            continue
        m.set_parent(tid, sid, label=port, kind="switch")
    for sid in sw_ids:
        if not m.nodes[sid]["parent"]:
            m.set_parent(sid, m.subnet_node(m.nodes[sid].get("ip") or ""), kind="lan")

    # 8. Le reste sous son réseau
    for nid, n in list(m.nodes.items()):
        if n["parent"] or n["role"] in ("internet", "site", "subnet"):
            continue
        m.set_parent(nid, m.subnet_node(n.get("ip") or ""), kind="lan")
    for nid, n in m.nodes.items():   # réseaux "autres" créés à la volée
        if n["role"] == "subnet" and not n["parent"]:
            m.set_parent(nid, top_lan, label="routé", kind="route")

    # Libellés, catégories, alertabilité
    for n in m.nodes.values():
        n["role_label"] = ROLE_LABELS.get(n["role"], n["role"])
        n["category"] = CATEGORY.get(n["role"], "other")
        if n["role"] in IMPORTANT and n["role"] != "vm":
            n["alert"] = n["alert"] or n["role"] in ("firewall", "router", "gateway", "esxi", "dc", "switch")
        if n["role"] in ("subnet", "site") or not n.get("site"):
            site, subnet = C.site_of(cfg, n.get("ip")) if n.get("ip") else (n.get("site"), n.get("subnet"))
            n["site"] = n.get("site") or site or ("Autres réseaux" if n.get("ip") else None)
            n["subnet"] = n.get("subnet") or subnet
    # le site des nœuds de structure : celui de leurs enfants
    for n in m.nodes.values():
        if n["role"] in ("internet", "isp"):
            n["site"] = None
    return m


# ---------------------------------------------------------------- état en direct

def apply_live(m, live):
    """live: icmp, tcp, rtt, ever_up, agents_alive, metrics{instance:{cpu,mem,disk,uptime}}, alerts[]"""
    index = {}
    for n in m.nodes.values():
        for key in (n["id"], n.get("ip"), n.get("name"), n.get("agent"), n.get("dns"), n.get("netbios"),
                    n["details"].get("vm_name"), n["details"].get("esx_name"), n["details"].get("fqdn"),
                    (n.get("esxi") or {}).get("name")):
            if key:
                index.setdefault(str(key).lower(), n["id"])
                index.setdefault(short(str(key)).lower(), n["id"])

    for a in live.get("alerts", []):
        target = None
        for v in a.get("keys", []):
            if not v:
                continue
            v = str(v).lower()
            if v.count(":") == 1 and not v.startswith(("ip:", "sw:", "esx:", "vm:", "agent:", "isp:", "net:", "site:")):
                v = v.split(":")[0]
            target = index.get(v) or index.get(short(v).lower())
            if target:
                break
        a["node"] = target
        if target:
            m.nodes[target]["alerts"].append(a)

    metrics = live.get("metrics", {})
    for n in m.nodes.values():
        ip = n.get("ip")
        icmp = live["icmp"].get(ip) if ip else None
        tcp = live["tcp"].get(ip) if ip else None
        probes = [p for p in (icmp, tcp) if p is not None]
        ever = live["ever_up"].get(ip) if ip else None
        alive_agent = n.get("agent") in live["agents_alive"] if n.get("agent") else None

        if n["role"] in ("subnet", "site"):
            st = "net"
        elif n.get("vm_power") and n["vm_power"] != "poweredOn":
            st = "off"
        elif n.get("vc_state") and n["vc_state"] != "connected":
            st = "down"
        elif n["role"] == "internet":
            st = {1: "up", 0: "down"}.get(live.get("internet"), "unknown")
        elif probes and any(p == 1 for p in probes):
            st = "up"
        elif alive_agent or n.get("vc_state") == "connected":
            st = "up"
        elif probes:   # ne répond plus aux sondes
            if n.get("present") and not ever:
                st = "up"          # présent au scan (ARP) mais ne répond jamais au ping : normal pour lui
            elif n["alert"] and (ever or n["critical"]):
                st = "down"
            else:
                st = "absent"      # poste éteint, portable parti... : pas une panne
        elif alive_agent is False:
            st = "down"
        elif n.get("present"):
            st = "up"
        elif n.get("last_seen"):
            st = "absent"
        else:
            st = "unknown"

        worst = max((SEV_RANK.get(a.get("severity"), 0) for a in n["alerts"]), default=0)
        if st == "up" and worst >= 2:
            st = "critical" if worst == 3 else "warning"
        n["status"] = st
        rtt = live["rtt"].get(ip) if ip else None
        n["latency_ms"] = round(rtt * 1000, 1) if rtt is not None else None
        if n.get("agent") and n["agent"] in metrics:
            n["metrics"] = metrics[n["agent"]]
        elif n.get("vm") and n["vm"].get("power") == "poweredOn":
            n["metrics"] = {"cpu": n["vm"].get("cpu_pct"), "mem": n["vm"].get("mem_pct")}
        elif n.get("esxi"):
            n["metrics"] = {"cpu": n["esxi"].get("cpu_pct"), "mem": n["esxi"].get("mem_pct")}


def stats(m, site=None):
    s = {"total": 0, "up": 0, "down": 0, "warning": 0, "absent": 0, "off": 0, "unknown": 0}
    for n in m.nodes.values():
        if n["role"] in ("subnet", "site", "internet", "isp"):
            continue
        if site and n.get("site") != site:
            continue
        s["total"] += 1
        key = {"critical": "down", "warning": "warning"}.get(n["status"], n["status"])
        s[key] = s.get(key, 0) + 1
    return s


# ---------------------------------------------------------------- vues

def public_node(n, light=False):
    keep = ("id", "name", "ip", "role", "role_label", "category", "status", "parent", "link", "link_kind", "site", "subnet",
            "latency_ms", "critical", "new", "agent")
    out = {k: n.get(k) for k in keep}
    out["alerts"] = [{"name": a["name"], "severity": a["severity"], "summary": a.get("summary"), "source": a.get("source")}
                     for a in n["alerts"]]
    if not light:
        out.update({k: n.get(k) for k in ("mac", "vendor", "dns", "netbios", "os", "ports", "sources", "first_seen",
                                          "last_seen", "metrics", "details")})
    return out


def graph_view(m, site=None):
    nodes = []
    keep = set()
    if site:
        for n in m.nodes.values():
            if n.get("site") == site:
                p = n["id"]
                while p and p not in keep:     # garder le chemin vers Internet
                    keep.add(p)
                    p = m.nodes[p]["parent"] if p in m.nodes else None
        keep.add("internet")
    for n in m.nodes.values():
        if site and n["id"] not in keep:
            continue
        nodes.append(public_node(n, light=True))
    ids = {n["id"] for n in nodes}
    extra = [e for e in m.extra_edges if e["source"] in ids and e["target"] in ids]
    return {"nodes": nodes, "extra_edges": extra}


def inventory(m):
    rows = []
    for n in m.nodes.values():
        if n["role"] in ("subnet", "site", "internet", "isp"):
            continue
        sw, port = None, None
        p = m.nodes.get(n.get("parent") or "")
        if p and n.get("link_kind") == "switch":
            sw, port = p["name"], n.get("link")
        rows.append({"id": n["id"], "status": n["status"], "name": n["name"], "dns": n.get("dns"), "netbios": n.get("netbios"),
                     "ip": n.get("ip"), "mac": n.get("mac"), "vendor": n.get("vendor"), "type": n["role_label"],
                     "category": n["category"], "site": n.get("site"), "subnet": n.get("subnet"), "switch": sw, "port": port,
                     "os": n.get("os"), "sources": ", ".join(n["sources"]), "first_seen": n.get("first_seen"),
                     "last_seen": n.get("last_seen"), "latency_ms": n.get("latency_ms"), "new": bool(n.get("new")),
                     "alerts": len(n["alerts"])})
    rows.sort(key=lambda r: [int(x) for x in r["ip"].split(".")] if r.get("ip") and re.fullmatch(r"[\d.]+", r["ip"]) else [999])
    return rows


def vmware_view(m, vc):
    if not vc:
        return {"configured": False}
    hosts = []
    for h in vc.get("hosts") or []:
        nid = next((n["id"] for n in m.nodes.values() if n.get("esxi") is h), None)
        vms = []
        for v in vc.get("vms") or []:
            if v.get("host") != h["name"]:
                continue
            vn = next((n for n in m.nodes.values() if n.get("vm") is v), None)
            vms.append(dict(v, id=vn["id"] if vn else None, status=vn["status"] if vn else "unknown",
                            agent=vn.get("agent") if vn else None, alerts=len(vn["alerts"]) if vn else 0,
                            name=v["name"], ip=v["ips"][0] if v.get("ips") else None))
        vms.sort(key=lambda x: (x["power"] != "poweredOn", x["name"].lower()))
        node = m.nodes.get(nid) or {}
        hosts.append(dict(h, id=nid, status=node.get("status", "unknown"), vms=vms,
                          alerts=[a.get("summary") for a in node.get("alerts", [])],
                          vms_on=sum(1 for v in vms if v["power"] == "poweredOn")))
    orphans = [v for v in vc.get("vms") or [] if not any(v.get("host") == h["name"] for h in vc.get("hosts") or [])]
    return {"configured": True, "up": vc.get("up"), "error": vc.get("error"), "hosts": hosts,
            "datastores": sorted(vc.get("datastores") or [], key=lambda d: -(d.get("used_pct") or 0)),
            "alarms": vc.get("alarms") or [], "orphans": len(orphans)}


def depth(m, nid):
    d = 0
    while nid and nid in m.nodes and d < 50:
        nid = m.nodes[nid]["parent"]
        d += 1
    return d


def switches_view(m, traffic):
    out = []
    for sid, ports in m.switch_ports.items():
        n = m.nodes.get(sid)
        if not n:
            continue
        plist = []
        for pname, p in ports.items():
            devs = [m.nodes[d] for d in p["devices"] if d in m.nodes]
            t = traffic.get((n.get("ip"), pname), {})
            plist.append({"name": pname, "alias": p.get("alias"), "up": p.get("up", True if devs else None), "vms": p.get("vms", 0),
                          "speed_mbps": p.get("speed_mbps"), "mac_count": p.get("mac_count"),
                          "via": sorted(v for v in p["via"] if v != "SNMP") or sorted(p["via"]), "in_bps": t.get("in"), "out_bps": t.get("out"),
                          "devices": [{"id": d["id"], "name": d["name"], "ip": d.get("ip"), "status": d["status"],
                                       "role": d["role"], "role_label": d["role_label"]} for d in devs]})
        plist.sort(key=lambda p: port_sort_key(p["name"]))
        out.append({"id": sid, "name": n["name"], "ip": n.get("ip"), "status": n["status"], "role": n["role"],
                    "model": n["details"].get("modèle"), "snmp": bool(n.get("snmp")), "sources": n["sources"],
                    "site": n.get("site"), "ports": plist,
                    "connected": sum(len(p["devices"]) for p in plist), "depth": depth(m, sid)})
    out.sort(key=lambda s: (s["depth"], -s["connected"], s["name"] or ""))
    detected = [public_node(n, light=True) for n in m.nodes.values()
                if n["role"] in ("network", "wifi", "switch", "firewall", "router", "gateway") and n["id"] not in m.switch_ports]
    return {"switches": out, "detected": detected}


def alerts_view(m, alerts):
    out = []
    for a in alerts:
        n = m.nodes.get(a.get("node") or "")
        out.append(dict(a, node_name=n["name"] if n else None, node_ip=n.get("ip") if n else None,
                        site=n.get("site") if n else None))
    out.sort(key=lambda a: (-SEV_RANK.get(a["severity"], 0), -(a.get("since") or 0)))
    return out


def internet_path(m):
    path = []
    cur = None
    # premier nœud "route" sous les sites : la passerelle la plus basse
    lows = [n for n in m.nodes.values() if n.get("link_kind") == "route" and n["role"] not in ("subnet", "isp")]
    if lows:
        def dist(nid):
            d = 0
            while nid and nid != "internet":
                nid = m.nodes[nid]["parent"]
                d += 1
            return d
        cur = max(lows, key=lambda n: dist(n["id"]))["id"]
    while cur:
        n = m.nodes[cur]
        path.append({"id": n["id"], "name": n["name"], "ip": n.get("ip"), "role": n["role"], "role_label": n["role_label"],
                     "status": n["status"], "latency_ms": n.get("latency_ms")})
        cur = n["parent"]
    return path


def sites_view(m, cfg):
    out = []
    for s in cfg["sites"] + ([{"name": "Autres réseaux", "subnets": []}] if any(n.get("site") == "Autres réseaux" for n in m.nodes.values()) else []):
        nodes = [n for n in m.nodes.values() if n.get("site") == s["name"] and n["role"] not in ("subnet", "site")]
        cats = {}
        for n in nodes:
            c = cats.setdefault(n["category"], {"total": 0, "down": 0, "absent": 0, "warning": 0})
            c["total"] += 1
            if n["status"] in ("down", "critical"):
                c["down"] += 1
            elif n["status"] == "absent":
                c["absent"] += 1
            elif n["status"] == "warning":
                c["warning"] += 1
        out.append({"name": s["name"], "subnets": s["subnets"], "stats": stats(m, s["name"]),
                    "categories": [{"key": k, "label": CATEGORY_LABELS.get(k, k), **v} for k, v in
                                   sorted(cats.items(), key=lambda kv: -kv[1]["total"])],
                    "alerts": sum(len(n["alerts"]) for n in nodes)})
    return out
