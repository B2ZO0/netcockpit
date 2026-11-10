"""NetCockpit : découverte réseau, modèle unifié, API web, métriques Prometheus."""
import csv
import io
import ipaddress
import json
import logging
import mimetypes
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import ai
import auth
import config as C
import model as M
import scanner
import snmp as S
import sources as SRC
from proxmox import Proxmox, merge_states
from vcenter import VCenter
from zabbix import Zabbix

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("cockpit")

CFG = C.load()
if not CFG["sites"]:          # aucun réseau déclaré : on surveille le réseau local détecté
    _auto = scanner.local_networks()
    if _auto:
        CFG["sites"] = [{"name": "LAN", "subnets": _auto, "color": None, "auto": True}]
LOCK = threading.RLock()
RESCAN = threading.Event()
SCANNING = threading.Event()
STATE_FILE = C.DATA_DIR / "state.json"


# ---------------------------------------------------------------- état persistant du scan

def load_state():
    try:
        st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        st = {}
    for k, v in (("devices", {}), ("known_macs", {}), ("baseline_done", False), ("paths", {}), ("subnets", []),
                 ("gateway", None), ("last_scan", 0), ("scan_started", 0), ("scan_duration", 0), ("dcs", [])):
        st.setdefault(k, v)
    return st


SCAN = load_state()
SNMP_STATE = {"devices": [], "updated": 0, "errors": {}}


def save_state():
    C.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(SCAN, indent=1), encoding="utf-8")
    tmp.replace(STATE_FILE)


VC = VCenter(C.VCENTER_URL, C.VCENTER_USER, C.VCENTER_PASSWORD) if C.VCENTER_URL and C.VCENTER_PASSWORD else None
PVE = Proxmox(C.PROXMOX_URL, C.PROXMOX_TOKEN_ID, C.PROXMOX_TOKEN_SECRET, C.PROXMOX_VERIFY_TLS) \
    if C.PROXMOX_URL and C.PROXMOX_TOKEN_ID and C.PROXMOX_TOKEN_SECRET else None


def virt():
    """État de la virtualisation, toutes plateformes confondues (vCenter/ESXi et Proxmox VE), ou None."""
    return merge_states([x.state for x in (VC, PVE) if x])
ZBX = Zabbix(C.ZABBIX_URL, C.ZABBIX_ADMIN_PASSWORD) if C.ZABBIX_URL else None


# ---------------------------------------------------------------- données en direct

def collect_live():
    seen = SRC.prom('group by (instance, ip, os) (max_over_time(up{job=~"node|windows"}[1d]))') or []
    alive = {r["metric"].get("instance") for r in (SRC.prom('up{job=~"node|windows"} == 1') or [])}
    agents = [{"instance": r["metric"].get("instance"), "ip": r["metric"].get("ip") or None, "os": r["metric"].get("os"),
               "alive": r["metric"].get("instance") in alive} for r in seen if r["metric"].get("instance")]
    lldp = [r["metric"] for r in (SRC.prom("lldp_neighbor_info") or [])]
    icmp = SRC.prom_map('max by (instance) (probe_success{job="blackbox_icmp"})')
    tcp = SRC.prom_map('max by (instance) (probe_success{job="blackbox_tcp"})', strip_port=True)
    rtt = SRC.prom_map('max by (instance) (probe_icmp_duration_seconds{job="blackbox_icmp", phase="rtt"}) '
                       'and on (instance) (max by (instance) (probe_success{job="blackbox_icmp"}) == 1)')
    ever = SRC.prom_map('max by (instance) (max_over_time(probe_success{job="blackbox_icmp"}[1d]))')
    for ip, v in SRC.prom_map('max by (instance) (max_over_time(probe_success{job="blackbox_tcp"}[1d]))', strip_port=True).items():
        ever[ip] = max(ever.get(ip, 0), v)
    inet = SRC.prom('max(probe_success{job="blackbox_icmp", role="internet"})')
    metrics = {}
    for key, q in (("cpu", SRC.CPU), ("mem", SRC.MEM), ("disk", SRC.DISK), ("uptime", SRC.UPTIME)):
        for inst, v in SRC.prom_map(q).items():
            metrics.setdefault(inst, {})[key] = round(v, 1)
    return {"agents": agents, "agents_alive": alive, "lldp": lldp, "icmp": icmp, "tcp": tcp, "rtt": rtt, "ever_up": ever,
            "internet": int(float(inet[0]["value"][1])) if inet else None, "metrics": metrics, "alerts": collect_alerts()}


def collect_alerts():
    out = []
    am = SRC.alertmanager_alerts()
    if am is None:   # repli : ALERTS de Prometheus (sans annotations)
        am = [{"labels": r["metric"], "annotations": {}, "startsAt": None, "fingerprint": None}
              for r in (SRC.prom('ALERTS{alertstate="firing"}') or [])]
    for a in am:
        lab = a.get("labels", {})
        if lab.get("alertname") in ("Watchdog", "ZabbixProbleme") or lab.get("severity") == "none":
            continue
        ann = a.get("annotations", {})
        out.append({"id": a.get("fingerprint") or lab.get("alertname"), "source": "Prometheus", "name": lab.get("alertname"),
                    "severity": lab.get("severity", "warning"), "summary": ann.get("summary") or lab.get("alertname"),
                    "description": ann.get("description"), "since": M.iso_ts(a.get("startsAt") or ""),
                    "keys": [lab.get(k) for k in ("node", "instance", "ip", "host", "esxhostname", "vmname", "vm", "entity", "datastore", "name")],
                    "labels": lab})
    if ZBX and ZBX.state["up"]:
        for p in ZBX.state["problems"]:
            out.append({"id": f"zbx:{p['eventid']}", "source": "Zabbix", "name": p["problem"], "severity": p["severity"],
                        "summary": f"{p['problem']}", "description": f"Zabbix · {p['severity_label']} · hôte {p['host']}"
                        + (" · acquitté" if p["acknowledged"] else ""), "since": p["since"], "keys": [p["host"]],
                        "labels": {"host": p["host"]}})
    return out


_cache = {"t": 0}


def current(force=False):
    """Modèle + données en direct (cache 15 s)."""
    with LOCK:
        if not force and _cache.get("model") and time.time() - _cache["t"] < 15:
            return _cache["model"], _cache["live"]
        live = collect_live()
        mdl = M.build(CFG, SCAN, virt(), SNMP_STATE, live["agents"], live["lldp"])
        M.apply_live(mdl, live)
        _cache.update(t=time.time(), model=mdl, live=live)
        return mdl, live


def detected_hypervisors():
    """Hyperviseurs vus par le scan mais pas encore connectés : {"vmware": [ip...], "proxmox": [ip...]}."""
    out = {"vmware": [], "proxmox": []}
    for ip, d in (SCAN.get("devices") or {}).items():
        ports = set(d.get("ports") or [])
        if not VC and {443, 902} <= ports:
            out["vmware"].append(ip)
        elif not PVE and 8006 in ports:
            out["proxmox"].append(ip)
    return {k: sorted(v, key=lambda i: [int(x) for x in i.split(".")])[:5] for k, v in out.items()}


def features():
    return {"vcenter": None if not VC else {"up": VC.state["up"], "error": VC.state["error"]},
            "proxmox": None if not PVE else {"up": PVE.state["up"], "error": PVE.state["error"]},
            "virt": bool(VC or PVE), "virt_detected": detected_hypervisors(),
            "zabbix": None if not ZBX else {"up": ZBX.state["up"], "error": ZBX.state["error"], "url": C.ZABBIX_PUBLIC_URL},
            "snmp": bool(CFG["snmp"]["community"]), "ai": ai.info(), "grafana_url": C.GRAFANA_URL,
            "alertmanager_url": C.ALERTMANAGER_PUBLIC_URL,
            "sites": [s["name"] for s in CFG["sites"]], "site_word": CFG.get("site_word"),
            "auto_sites": any(s.get("auto") for s in CFG["sites"]), "last_scan": SCAN.get("last_scan"),
            "scan_duration": SCAN.get("scan_duration"), "scanning": SCANNING.is_set(), "now": time.time()}


# ---------------------------------------------------------------- vues API

def overview(site=None):
    mdl, live = current()
    alerts = M.alerts_view(mdl, live["alerts"])
    if site:
        alerts = [a for a in alerts if a.get("site") == site]
    servers = []
    for n in mdl.nodes.values():
        if n.get("agent") and (not site or n.get("site") == site):
            mt = n.get("metrics") or {}
            servers.append({"id": n["id"], "name": n["name"], "ip": n.get("ip"), "status": n["status"], "os": n.get("os"),
                            "cpu": mt.get("cpu"), "mem": mt.get("mem"), "disk": mt.get("disk")})
    vc = virt()
    inet_series = SRC.prom_range('avg(probe_icmp_duration_seconds{job="blackbox_icmp", role="internet", phase="rtt"}) * 1000', hours=24)
    new = [M.public_node(n, light=True) for n in mdl.nodes.values() if n.get("new") and (not site or n.get("site") == site)]
    return {
        "features": features(), "stats": M.stats(mdl, site), "sites": M.sites_view(mdl, CFG),
        "internet_path": M.internet_path(mdl),
        "internet_series": inet_series[0]["points"] if inet_series else [],
        "alerts": alerts[:12], "alerts_count": {s: sum(1 for a in alerts if a["severity"] == s) for s in ("critical", "warning", "info")},
        "servers": servers,
        "agents": {"total": len(live["agents"]), "alive": len(live["agents_alive"])},
        "virt_detected": ", ".join(f"{lab} {ip}" for lab, k in (("VMware ESXi", "vmware"), ("Proxmox", "proxmox"))
                                   for ip in detected_hypervisors()[k][:2]) or None,
        "vmware": None if not vc else {"up": vc["up"], "hosts": len(vc["hosts"]),
                                       "hosts_ok": sum(1 for h in vc["hosts"] if h["state"] == "connected"),
                                       "vms": len(vc["vms"]), "vms_on": sum(1 for v in vc["vms"] if v["power"] == "poweredOn"),
                                       "alarms": len(vc.get("alarms") or []),
                                       "datastore_max": max((d.get("used_pct") or 0 for d in vc.get("datastores") or []), default=None)},
        "zabbix": None if not ZBX else {"up": ZBX.state["up"], "problems": len(ZBX.state["problems"])},
        "new_devices": new, "services": services()["http"],
        "undeclared": undeclared(mdl),
    }


def setup_status():
    """État de la mise en route : ce qui est fait, ce qui reste, pour l'écran « Mise en route »."""
    mdl, live = current()
    devices = [n for n in mdl.nodes.values() if n.get("ip") and n["role"] not in ("site", "subnet", "internet", "isp", "group")]
    named = [n for n in devices if n.get("name") and n["name"] != n.get("ip")]
    vc = virt()
    return {
        "sites": [{"name": s["name"], "subnets": s["subnets"]} for s in CFG["sites"]],
        "auto_sites": any(s.get("auto") for s in CFG["sites"]),
        "site_word": CFG.get("site_word"),
        "undeclared": undeclared(mdl),
        "scan": {"last": SCAN.get("last_scan"), "running": SCANNING.is_set(), "devices": len(devices)},
        "names": {"total": len(devices), "named": len(named), "dns": CFG["names"]["dns_servers"]},
        "vmware": {"configured": bool(VC or PVE), "detected": detected_hypervisors(), "platforms": [n for n, x in (("vmware", VC), ("proxmox", PVE)) if x], "up": bool(vc and vc["up"]), "error": vc and vc.get("error"),
                   "hosts": len(vc["hosts"]) if vc else 0, "vms": len(vc["vms"]) if vc else 0},
        "agents": {"total": len(live["agents"]), "alive": len(live["agents_alive"]),
                   "silent": sorted(a["instance"] for a in live["agents"] if not a["alive"])[:10]},
        "notifications": SRC.alertmanager_channels(),
        "zabbix": {"enabled": bool(ZBX), "up": bool(ZBX and ZBX.state["up"]), "error": ZBX and ZBX.state["error"]},
        "snmp": {"configured": bool(CFG["snmp"]["community"]), "devices": len(CFG["snmp"]["devices"]),
                 "errors": len(SNMP_STATE.get("errors") or {}) if isinstance(SNMP_STATE, dict) else 0},
        "http_checks": len(CFG["http_checks"]),
        "ai": bool(ai.info()),
        "install_dir": C.INSTALL_DIR or None,
    }


def undeclared(mdl):
    """Réseaux privés où des équipements ont été vus, mais qui ne sont rattachés à aucun site/bâtiment."""
    nets = {}
    for n in mdl.nodes.values():
        ip = n.get("ip")
        if n.get("site") != "Autres réseaux" or not ip or n["role"] in ("internet", "isp"):
            continue
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if a.is_private:
            k = str(ipaddress.ip_network(f"{ip}/24", strict=False))
            nets[k] = nets.get(k, 0) + 1
    return [{"subnet": k, "count": v} for k, v in sorted(nets.items(), key=lambda kv: -kv[1])][:8]


def services():
    http = []
    for h in CFG["http_checks"]:
        url = h.get("url")
        ok = SRC.prom_map(f'probe_success{{job="blackbox_http", instance="{url}"}}').get(url)
        dur = SRC.prom_map(f'probe_duration_seconds{{job="blackbox_http", instance="{url}"}}').get(url)
        cert = SRC.prom_map(f'(probe_ssl_earliest_cert_expiry{{job="blackbox_http", instance="{url}"}} - time()) / 86400').get(url)
        code = SRC.prom_map(f'probe_http_status_code{{job="blackbox_http", instance="{url}"}}').get(url)
        http.append({"name": h.get("name") or url, "url": url, "up": ok, "duration_ms": round(dur * 1000) if dur else None,
                     "cert_days": round(cert) if cert is not None else None, "code": int(code) if code else None})
    dns = []
    for d in CFG["dns_checks"]:
        ip = str(d.get("ip"))
        ok = SRC.prom_map(f'probe_success{{job="blackbox_dns", instance="{ip}"}}').get(ip)
        dur = SRC.prom_map(f'probe_duration_seconds{{job="blackbox_dns", instance="{ip}"}}').get(ip)
        dns.append({"name": d.get("name") or ip, "ip": ip, "up": ok, "duration_ms": round(dur * 1000) if dur else None})
    inet = []
    for t in CFG["internet_targets"]:
        ip = str(t["ip"])
        rtt = SRC.prom_map(f'probe_icmp_duration_seconds{{job="blackbox_icmp", instance="{ip}", phase="rtt"}}').get(ip)
        ok = SRC.prom_map(f'probe_success{{job="blackbox_icmp", instance="{ip}"}}').get(ip)
        inet.append({"name": t.get("name") or ip, "ip": ip, "up": ok, "latency_ms": round(rtt * 1000, 1) if rtt else None})
    return {"http": http, "dns": dns, "internet": inet}


def node_detail(nid):
    mdl, live = current()
    n = mdl.nodes.get(nid)
    if not n:
        return None
    d = M.public_node(n)
    d.update({k: n.get(k) for k in ("vm", "esxi", "present", "agent_os")})
    p = mdl.nodes.get(n.get("parent") or "")
    d["parent_name"] = p["name"] if p else None
    d["children"] = [{"id": c["id"], "name": c["name"], "status": c["status"], "role_label": c["role_label"], "ip": c.get("ip"),
                      "link": c.get("link")} for c in mdl.nodes.values() if c.get("parent") == nid][:200]
    ip = n.get("ip")
    if ip and n["role"] not in ("subnet", "site"):
        s = SRC.prom_range(f'max(probe_icmp_duration_seconds{{job="blackbox_icmp", instance="{ip}", phase="rtt"}}) * 1000', hours=24)
        d["latency_series"] = s[0]["points"] if s else []
        av = SRC.prom_map(f'avg_over_time(probe_success{{job="blackbox_icmp", instance="{ip}"}}[24h]) * 100')
        d["availability_24h"] = round(av[ip], 1) if ip in av else None
    if n.get("agent"):
        inst = n["agent"]
        cpu = SRC.prom_range(f'({SRC.CPU})', hours=24)
        mem = SRC.prom_range(f'({SRC.MEM})', hours=24)
        d["cpu_series"] = next((s["points"] for s in cpu if s["labels"].get("instance") == inst), [])
        d["mem_series"] = next((s["points"] for s in mem if s["labels"].get("instance") == inst), [])
        disks = SRC.prom(f'(1 - node_filesystem_avail_bytes{{instance="{inst}", fstype!~"tmpfs|overlay|squashfs|ramfs|nsfs|fuse.*"}} '
                         f'/ node_filesystem_size_bytes{{instance="{inst}", fstype!~"tmpfs|overlay|squashfs|ramfs|nsfs|fuse.*"}}) * 100') or []
        disks += SRC.prom(f'(1 - windows_logical_disk_free_bytes{{instance="{inst}", volume!~"HarddiskVolume.*"}} '
                          f'/ windows_logical_disk_size_bytes{{instance="{inst}", volume!~"HarddiskVolume.*"}}) * 100') or []
        d["disks"] = [{"name": r["metric"].get("mountpoint") or r["metric"].get("volume"), "pct": round(float(r["value"][1]), 1)} for r in disks]
        d["logs"] = SRC.loki_logs(f'{{host="{inst}"}}', hours=12, limit=40)
        d["errors_24h"] = SRC.loki_count(f'sum(count_over_time({{host="{inst}", level=~"err|crit|alert|emerg|error|critical"}}[24h]))')
    if n["id"] in mdl.switch_ports:
        sv = M.switches_view(mdl, traffic())
        d["switch"] = next((s for s in sv["switches"] if s["id"] == nid), None)
    feats = features()
    links = []
    g = feats["grafana_url"]
    if g and n.get("agent"):
        links += [("Métriques (Grafana)", f"{g}/d/serveur?var-instance={n['agent']}"), ("Logs (Grafana)", f"{g}/d/logs?var-host={n['agent']}")]
    if g and ip:
        links.append(("Historique réseau", f"{g}/d/reseau?var-node={nid}"))
    if feats["zabbix"] and feats["zabbix"]["url"]:
        links.append(("Zabbix", f"{feats['zabbix']['url']}/zabbix.php?action=problem.view&filter_set=1&name={n['name']}"))
    if ip and n["role"] in ("switch", "network", "firewall", "router", "gateway", "nas", "printer", "esxi", "wifi"):
        links.append(("Interface web", f"https://{ip}"))
    d["links"] = [{"label": a, "url": b} for a, b in links]
    return d


_traffic = {"t": 0, "data": {}}


def traffic():
    if time.time() - _traffic["t"] < 30:
        return _traffic["data"]
    data = {}
    for key, q in (("in", 'rate(ifHCInOctets{job="snmp"}[5m]) * 8'), ("out", 'rate(ifHCOutOctets{job="snmp"}[5m]) * 8')):
        for r in SRC.prom(q) or []:
            k = (r["metric"].get("instance"), r["metric"].get("ifName") or r["metric"].get("ifDescr"))
            data.setdefault(k, {})[key] = float(r["value"][1])
    _traffic.update(t=time.time(), data=data)
    return data


def nodegraph(hide_minor=True, site=None):
    mdl, _ = current()
    g = M.graph_view(mdl, site)
    minor = {"workstations", "phones", "printers", "mobile", "other", "cameras"}
    nodes, keep = [], set()
    colors = {"up": "#22c55e", "warning": "#f59e0b", "critical": "#ef4444", "down": "#ef4444", "off": "#475569",
              "absent": "#334155", "unknown": "#94a3b8", "net": "#3b82f6"}
    texts = {"up": "OK", "warning": "alerte", "critical": "critique", "down": "EN PANNE", "off": "éteint", "absent": "absent", "unknown": "?", "net": ""}
    for n in g["nodes"]:
        if hide_minor and n["category"] in minor and n["status"] in ("up", "absent"):
            continue
        keep.add(n["id"])
        st = n["status"]
        item = {"id": n["id"], "title": n["name"], "subTitle": n["role_label"] + (f" · {n['ip']}" if n.get("ip") else ""),
                "mainStat": f"{n['latency_ms']} ms" if n.get("latency_ms") is not None else texts.get(st, st),
                "secondaryStat": f"{len(n['alerts'])} alerte(s)" if n["alerts"] else "",
                "detail__statut": st, "detail__ip": n.get("ip") or ""}
        for s, c in colors.items():
            item[f"arc__{s}"] = 1 if st == s else 0
            item[f"arc__{s}_color"] = c
        nodes.append(item)
    edges = [{"id": f"{n['parent']}--{n['id']}", "source": n["parent"], "target": n["id"], "mainStat": n.get("link") or ""}
             for n in g["nodes"] if n.get("parent") in keep and n["id"] in keep]
    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------- cibles Prometheus

def write_json_atomic(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


PREFERRED_PORTS = [22, 443, 3389, 445, 53, 80, 8443, 902, 8006]


def write_targets():
    mdl, _ = current(force=True)
    icmp, tcp = [], []
    watch_ports = {str(w.get("ip")): w.get("port") for w in CFG["watch"] if w.get("port")}
    for n in mdl.nodes.values():
        ip = n.get("ip")
        if not ip or n["role"] in ("subnet", "site", "internet"):
            continue
        labels = {"node": n["id"], "name": n["name"] or ip, "role": n["role"], "site": n.get("site") or "",
                  "subnet": n.get("subnet") or "", "critical": str(n["critical"]).lower(),
                  "alert": str(n["alert"] and n["role"] != "isp").lower()}
        icmp.append({"targets": [ip], "labels": labels})
        port = watch_ports.get(ip) or next((p for p in PREFERRED_PORTS if p in (n.get("ports") or [])), None)
        if port and n["alert"]:
            tcp.append({"targets": [f"{ip}:{port}"], "labels": labels})
    for t in CFG["internet_targets"]:
        icmp.append({"targets": [str(t["ip"])], "labels": {"node": "internet", "name": t.get("name") or str(t["ip"]),
                                                           "role": "internet", "critical": "true", "alert": "false"}})
    http = [{"targets": [h["url"]], "labels": {"name": h.get("name") or h["url"]}} for h in CFG["http_checks"] if h.get("url")]
    dns = [{"targets": [str(d["ip"])], "labels": {"name": d.get("name") or str(d["ip"])}} for d in CFG["dns_checks"] if d.get("ip")]
    snmp_t = [{"targets": [d["ip"]], "labels": {"name": d["name"]}} for d in SNMP_STATE["devices"]]
    for name, data in (("icmp", icmp), ("tcp", tcp), ("http", http), ("dns", dns), ("snmp", snmp_t)):
        write_json_atomic(C.TARGETS_DIR / f"{name}.json", data)
    log.info("cibles : %d ping, %d TCP, %d HTTP, %d DNS, %d SNMP", len(icmp), len(tcp), len(http), len(dns), len(snmp_t))


# ---------------------------------------------------------------- scan

def do_scan():
    scfg = CFG["scan"]
    enabled = scfg.get("enabled", True) if C.SCAN_OVERRIDE is None else C.SCAN_OVERRIDE == "1"
    t0 = time.time()
    SCANNING.set()
    try:
        subnets = C.all_subnets(CFG) or scanner.local_networks()
        dns_servers = CFG["names"]["dns_servers"] or SCAN.get("dcs") or []
        gateway = scanner.default_gateway()
        found = {}
        if enabled:
            for s in subnets:
                log.info("scan de %s ...", s)
                found.update(scanner.ping_sweep(s, scfg["exclude"], dns_servers))
            if found:
                log.info("%d équipements actifs : ports ...", len(found))
                for ip, p in scanner.port_scan(found.keys(), scfg["ports"]).items():
                    found[ip]["ports"] = p
                if scfg.get("netbios", True):
                    log.info("noms NetBIOS ...")
                    for ip, nb in scanner.netbios_scan(found.keys()).items():
                        found[ip]["netbios"] = nb["netbios"]
                        if nb.get("mac") and not found[ip].get("mac"):
                            found[ip]["mac"] = nb["mac"]
                            found[ip]["netbios_vendor"] = nb.get("vendor")
            dcs = sorted(ip for ip, r in found.items() if {53, 88, 389} <= set(r.get("ports") or []))
            missing = [ip for ip, r in found.items() if not r.get("hostname")]
            if missing and (dns_servers or dcs):
                for ip, name in scanner.reverse_dns(missing, dns_servers or dcs).items():
                    found[ip]["hostname"] = name
        else:
            dcs = SCAN.get("dcs") or []
        paths = {t: scanner.traceroute(t) for t in CFG["traceroute_targets"]}
        if VC:
            VC.network_links()
        poll_snmp()
        now = time.time()
        with LOCK:
            baseline = SCAN["baseline_done"]
            for ip, rec in found.items():
                old = SCAN["devices"].get(ip, {})
                key = rec.get("mac") or f"ip:{ip}"
                is_new = False
                if key not in SCAN["known_macs"]:
                    SCAN["known_macs"][key] = now
                    is_new = baseline
                for k in ("hostname", "netbios", "mac", "vendor", "netbios_vendor"):
                    if not rec.get(k) and old.get(k):
                        rec[k] = old[k]
                if not rec.get("ports") and old.get("ports"):
                    rec["ports"] = old["ports"]
                rec.update(first_seen=old.get("first_seen", now), last_seen=now,
                           new_since=now if is_new else old.get("new_since"))
                SCAN["devices"][ip] = rec
            for ip in [ip for ip, d in SCAN["devices"].items() if now - d.get("last_seen", 0) > M.RETAIN_SECONDS]:
                del SCAN["devices"][ip]
            for d in SCAN["devices"].values():
                d["new"] = bool(d.get("new_since") and now - d["new_since"] < 86400)
            SCAN.update(subnets=subnets, gateway=gateway, paths=paths, last_scan=now, scan_started=t0,
                        scan_duration=round(now - t0, 1), baseline_done=baseline or enabled, dcs=dcs)
            save_state()
        log.info("scan terminé en %.0f s : %d actifs, %d connus, DC : %s", now - t0, len(found), len(SCAN["devices"]), dcs or "-")
    finally:
        SCANNING.clear()
    write_targets()


def poll_snmp():
    comm = CFG["snmp"]["community"]
    if not comm:
        return
    targets = list(CFG["snmp"]["devices"])
    if CFG["snmp"].get("try_discovered"):
        for ip, d in SCAN["devices"].items():
            if scanner.classify(d) in ("network", "firewall", "wifi") and ip not in targets:
                targets.append(ip)
    devices, errors = [], {}
    for ip in targets:
        try:
            d = S.poll_device(ip, comm)
            if d:
                devices.append(d)
            else:
                errors[ip] = "pas de réponse SNMP"
        except Exception as e:
            errors[ip] = str(e)[:150]
    SNMP_STATE.update(devices=devices, errors=errors, updated=time.time())
    log.info("SNMP : %d équipement(s) lus, %d en erreur", len(devices), len(errors))


def scan_loop():
    while True:
        try:
            do_scan()
        except Exception:
            log.exception("échec du scan")
        RESCAN.wait(max(5, int(CFG["scan"].get("interval_minutes", 30))) * 60)
        RESCAN.clear()


def vcenter_loop():
    while True:
        for src in (VC, PVE):
            if src:
                src.poll()
        try:
            write_targets()
        except Exception:
            log.exception("écriture des cibles")
        time.sleep(120)


def zabbix_loop():
    last_conf = last_sync = 0
    while True:
        if time.time() - last_conf > 6 * 3600 or not ZBX.state["configured"]:
            try:
                ZBX.configure(CFG)
                last_conf = time.time()
            except Exception as e:
                log.warning("configuration Zabbix impossible pour l'instant : %s", e)
                ZBX.token = None
        if ZBX.state["configured"] and SCAN.get("last_scan") and time.time() - last_sync > 1800:
            try:
                mdl, _ = current()
                ZBX.sync_hosts(list(mdl.nodes.values()))
                last_sync = time.time()
            except Exception as e:
                log.warning("synchronisation Zabbix : %s", e)
                ZBX.token = None
        ZBX.poll()
        time.sleep(60)


# ---------------------------------------------------------------- métriques

def _esc(v):
    return str(v if v is not None else "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _line(name, labels, value):
    lab = ",".join(f'{k}="{_esc(v)}"' for k, v in labels.items())
    return f"{name}{{{lab}}} {value}" if lab else f"{name} {value}"


def metrics_text():
    out = [_line("cockpit_last_scan_timestamp_seconds", {}, SCAN.get("last_scan") or 0),
           _line("cockpit_scan_duration_seconds", {}, SCAN.get("scan_duration") or 0)]
    mdl, _ = current()
    per = {}
    for n in mdl.nodes.values():
        if n["role"] in ("subnet", "site", "internet"):
            continue
        per[(n.get("site") or "", n.get("subnet") or "")] = per.get((n.get("site") or "", n.get("subnet") or ""), 0) + 1
        if n.get("ip"):
            out.append(_line("cockpit_device_info", {"ip": n["ip"], "name": n["name"], "mac": n.get("mac"), "vendor": n.get("vendor"),
                                                     "dns": n.get("dns"), "netbios": n.get("netbios"), "role": n["role_label"],
                                                     "site": n.get("site"), "subnet": n.get("subnet"), "os": n.get("os")}, 1))
        if n.get("new") and n.get("ip"):
            dev = SCAN["devices"].get(n["ip"], {})
            out.append(_line("cockpit_device_first_seen_timestamp_seconds",
                             {"ip": n["ip"], "mac": n.get("mac"), "vendor": n.get("vendor") or "inconnu",
                              "hostname": n["name"], "site": n.get("site")}, dev.get("new_since") or 0))
        val = {"up": 1, "warning": 1, "critical": 1, "down": 0, "off": 0, "absent": 0}.get(n["status"], -1)
        out.append(_line("cockpit_node_up", {"node": n["id"], "name": n["name"], "role": n["role"], "status": n["status"],
                                            "site": n.get("site"), "critical": str(n["critical"]).lower()}, val))
    for (site, subnet), c in per.items():
        out.append(_line("cockpit_devices", {"site": site, "subnet": subnet}, c))
    for k, v in M.stats(mdl).items():
        out.append(_line("cockpit_nodes", {"status": k}, v))
    if VC or PVE:
        st = virt()
        out.append(_line("cockpit_vmware_up", {"error": st.get("error")}, 1 if st["up"] else 0))
        if st["up"]:
            for h in st["hosts"]:
                lab = {"host": h["name"], "cluster": h.get("cluster") or ""}
                out.append(_line("cockpit_vmware_host_connected", dict(lab, state=h["state"]), 1 if h["state"] == "connected" else 0))
                out.append(_line("cockpit_vmware_host_maintenance", lab, 1 if h["maintenance"] else 0))
                if h.get("cpu_pct") is not None:
                    out.append(_line("cockpit_vmware_host_cpu_percent", lab, h["cpu_pct"]))
                if h.get("mem_pct") is not None:
                    out.append(_line("cockpit_vmware_host_mem_percent", lab, h["mem_pct"]))
            for v in st["vms"]:
                lab = {"vm": v["name"], "host": v.get("host") or ""}
                out.append(_line("cockpit_vmware_vm_powered_on", lab, 1 if v["power"] == "poweredOn" else 0))
                if v.get("cpu_pct") is not None and v["power"] == "poweredOn":
                    out.append(_line("cockpit_vmware_vm_cpu_percent", lab, v["cpu_pct"]))
                if v.get("mem_pct") is not None and v["power"] == "poweredOn":
                    out.append(_line("cockpit_vmware_vm_mem_percent", lab, v["mem_pct"]))
            for d in st.get("datastores") or []:
                lab = {"datastore": d["name"]}
                if d.get("used_pct") is not None:
                    out.append(_line("cockpit_vmware_datastore_used_percent", lab, d["used_pct"]))
                    out.append(_line("cockpit_vmware_datastore_free_bytes", lab, d["free_gb"] * 1073741824))
            seen = set()
            for a in st["alarms"]:
                if (a["entity"], a["alarm"]) in seen:
                    continue
                seen.add((a["entity"], a["alarm"]))
                out.append(_line("cockpit_vmware_alarm", {"entity": a["entity"], "alarm": a["alarm"], "status": a["status"]}, 1))
    if ZBX:
        out.append(_line("cockpit_zabbix_up", {}, 1 if ZBX.state["up"] else 0))
        for p in ZBX.state["problems"]:
            out.append(_line("cockpit_zabbix_problem", {"host": p["host"], "problem": p["problem"], "severity": p["severity"],
                                                       "priority": p["priority"]}, 1))
    if CFG["snmp"]["community"]:
        out.append(_line("cockpit_snmp_devices", {}, len(SNMP_STATE["devices"])))
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- HTTP

def inventory_csv():
    mdl, _ = current()
    rows = M.inventory(mdl)
    buf = io.StringIO()
    cols = ["status", "name", "dns", "netbios", "ip", "mac", "vendor", "type", "site", "subnet", "switch", "port", "os", "sources"]
    w = csv.writer(buf, delimiter=";")
    w.writerow(["État", "Nom", "DNS", "NetBIOS", "IP", "MAC", "Constructeur", "Type", "Site", "Réseau", "Switch", "Port", "OS", "Vu par"])
    for r in rows:
        w.writerow([r.get(c) or "" for c in cols])
    return "\ufeff" + buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    server_version = "cockpit/2.0"

    def log_message(self, fmt, *args):
        log.debug("%s - %s", self.address_string(), fmt % args)

    def _send(self, code, body, ctype="application/json; charset=utf-8", headers=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False, default=str)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "same-origin")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _gate(self, path):
        """True si la requête peut continuer ; sinon la réponse (401 ou page de connexion) est envoyée."""
        if auth.allowed(path, self.client_address[0], self.headers.get("Cookie")):
            return True
        if path.startswith("/api/"):
            self._send(401, {"error": "login required"})
        else:
            self._send(302, b"", "text/plain", {"Location": "/login"})
        return False

    def do_GET(self):
        url = urlparse(self.path)
        if not self._gate(url.path):
            return
        if url.path in ("/login", "/login/"):
            return self._send(200, (C.STATIC_DIR / "login.html").read_bytes(), "text/html; charset=utf-8",
                              {"Cache-Control": "no-store"})
        if url.path == "/api/auth":
            return self._send(200, {"required": auth.active(), "misconfigured": auth.misconfigured()})
        qs = {k: v[0] for k, v in parse_qs(url.query).items()}
        site = qs.get("site") or None
        try:
            p = url.path
            if p == "/api/overview":
                return self._send(200, overview(site))
            if p == "/api/graph":
                mdl, _ = current()
                return self._send(200, dict(M.graph_view(mdl, site), features=features(), stats=M.stats(mdl, site)))
            if p == "/api/inventory":
                mdl, _ = current()
                return self._send(200, {"rows": M.inventory(mdl), "features": features()})
            if p == "/api/inventory.csv":
                return self._send(200, inventory_csv(), "text/csv; charset=utf-8",
                                  {"Content-Disposition": 'attachment; filename="inventaire-reseau.csv"'})
            if p == "/api/vmware":
                mdl, _ = current()
                return self._send(200, M.vmware_view(mdl, virt()))
            if p == "/api/switches":
                mdl, _ = current()
                v = M.switches_view(mdl, traffic())
                v["snmp"] = {"configured": bool(CFG["snmp"]["community"]), "errors": SNMP_STATE["errors"]}
                return self._send(200, v)
            if p == "/api/alerts":
                mdl, live = current()
                return self._send(200, {"alerts": M.alerts_view(mdl, live["alerts"]), "features": features()})
            if p == "/api/services":
                return self._send(200, services())
            if p == "/api/node":
                d = node_detail(qs.get("id", ""))
                return self._send(200, d) if d else self._send(404, {"error": "équipement introuvable"})
            if p == "/api/setup":
                return self._send(200, setup_status())
            if p == "/api/features":
                return self._send(200, features())
            if p == "/api/nodegraph":
                return self._send(200, nodegraph(qs.get("hide_devices", "1") == "1", site))
            if p == "/metrics":
                return self._send(200, metrics_text(), "text/plain; version=0.0.4; charset=utf-8")
            if p in ("/health", "/-/healthy"):
                return self._send(200, {"ok": True})
            path = "index.html" if p in ("/", "") else p.lstrip("/")
            f = (C.STATIC_DIR / path).resolve()
            if C.STATIC_DIR in f.parents and f.is_file():
                ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                if ctype.startswith("text/") or ctype.endswith("javascript"):
                    ctype += "; charset=utf-8"
                return self._send(200, f.read_bytes(), ctype, {"Cache-Control": "no-cache"})
            return self._send(404, {"error": "introuvable"})
        except BrokenPipeError:
            pass
        except Exception as e:
            log.exception("erreur HTTP %s", self.path)
            return self._send(500, {"error": str(e)})

    def do_POST(self):
        url = urlparse(self.path)
        try:
            length = min(int(self.headers.get("Content-Length") or 0), 1_000_000)
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
        except ValueError:
            body = {}
        if url.path == "/api/login":
            if auth.misconfigured():
                return self._send(503, {"error": "no password set: run ./setup.sh"})
            ok, wait = auth.check_password(self.client_address[0], str(body.get("password") or ""))
            if wait:
                return self._send(429, {"error": "too many attempts", "retry_after": wait})
            if not ok:
                log.warning("connexion refusée depuis %s", self.client_address[0])
                return self._send(401, {"error": "wrong password"})
            token, age = auth.new_session()
            return self._send(200, {"ok": True}, headers={
                "Set-Cookie": f"{auth.COOKIE}={token}; Max-Age={age}; Path=/; HttpOnly; SameSite=Lax"})
        if url.path == "/api/logout":
            return self._send(200, {"ok": True}, headers={"Set-Cookie": f"{auth.COOKIE}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax"})
        if not self._gate(url.path):
            return
        try:
            if url.path == "/api/rescan":
                RESCAN.set()
                return self._send(202, {"ok": True})
            if url.path == "/api/ai/explain":
                d = node_detail(body.get("id", ""))
                if not d:
                    return self._send(404, {"error": "équipement introuvable"})
                return self._send(200, ai.explain_node(d, "en" if body.get("lang") == "en" else "fr"))
            if url.path == "/api/ai/summary":
                mdl, live = current()
                return self._send(200, ai.summarize(overview(), M.alerts_view(mdl, live["alerts"]), "en" if body.get("lang") == "en" else "fr"))
            return self._send(404, {"error": "introuvable"})
        except Exception as e:
            log.exception("erreur HTTP POST %s", self.path)
            return self._send(500, {"error": str(e)})


def main():
    log.info("cockpit démarré sur le port %d · sites : %s · vCenter : %s · Zabbix : %s · SNMP : %s · IA : %s",
             C.PORT, ", ".join(s["name"] for s in CFG["sites"]) or "auto", " + ".join(n for n, x in (("vCenter", VC), ("Proxmox", PVE)) if x) or "non",
             "oui" if ZBX else "non", "oui" if CFG["snmp"]["community"] else "non", (ai.info() or {}).get("provider", "non"))
    if auth.misconfigured():
        log.error("connexion activée mais COCKPIT_PASSWORD est vide : l'interface reste fermée. Lance ./setup.sh")
    elif not auth.active():
        log.warning("interface SANS mot de passe (COCKPIT_AUTH=off) : toute personne du réseau peut la consulter")
    C.TARGETS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        write_targets()
    except Exception:
        log.exception("écriture initiale des cibles")
    threading.Thread(target=scan_loop, daemon=True, name="scan").start()
    if VC or PVE:
        threading.Thread(target=vcenter_loop, daemon=True, name="vcenter").start()
    if ZBX:
        threading.Thread(target=zabbix_loop, daemon=True, name="zabbix").start()
    ThreadingHTTPServer(("0.0.0.0", C.PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
