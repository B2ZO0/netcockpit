"""NetCockpit demo: a fully simulated two-site network (no real scan, no credentials needed).

    docker compose -f docker-compose.demo.yml up --build      -> http://localhost:8088
    or:  pip install pyyaml requests && python demo/demo.py

Everything (nmap, vCenter, SNMP, Zabbix, Prometheus, Alertmanager, Loki, AI) is simulated in-process.
All names and IP addresses are fictitious (RFC 1918 / RFC 5737 documentation ranges)."""
import json, math, os, random, re, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

random.seed(7)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
APP = next(p for p in (os.environ.get("COCKPIT_APP_DIR"), "/app/app", os.path.join(ROOT, "cockpit", "app")) if p and os.path.isdir(p))
CONFIG_SRC = next(p for p in ("/config/cockpit.example.yml", os.path.join(ROOT, "config", "cockpit.example.yml")) if os.path.isfile(p))
WORK = tempfile.mkdtemp(prefix="netcockpit-demo-")
WITH_SNMP = os.environ.get("DEMO_SNMP", "1") == "1"
PORT = os.environ.get("COCKPIT_PORT", "8088")
FAKE = "http://127.0.0.1:19090"
os.environ.update(COCKPIT_PORT=PORT, COCKPIT_CONFIG=f"{WORK}/cockpit.yml", COCKPIT_TARGETS_DIR=f"{WORK}/targets",
                  COCKPIT_DATA_DIR=f"{WORK}/data", PROMETHEUS_URL=FAKE, ALERTMANAGER_URL=FAKE, LOKI_URL=FAKE,
                  GRAFANA_PUBLIC_URL="http://localhost:3000", ZABBIX_URL=FAKE, ZABBIX_PUBLIC_URL="http://localhost:8081",
                  ZABBIX_ADMIN_PASSWORD="demo-password", ZABBIX_GRAFANA_PASSWORD="demo",
                  VCENTER_URL="https://vcenter.example.local/sdk", VCENTER_USER="readonly@vsphere.local", VCENTER_PASSWORD="demo",
                  AI_PROVIDER="openai", AI_BASE_URL=FAKE + "/v1", AI_MODEL="demo-model")
cfg = open(CONFIG_SRC, encoding="utf-8").read()
if WITH_SNMP:
    cfg = cfg.replace('community: ""          # or', 'community: "demo"      # or').replace(
        "devices: []            # IPs", "devices: [10.10.0.250, 10.10.0.251, 10.20.0.250]   # IPs")
cfg = cfg.replace("http_checks:\n", 'http_checks:\n  - { name: Intranet, url: "https://intranet.example.local" }\n  - { name: Public website, url: "https://www.example.com" }\n')
open(f"{WORK}/cockpit.yml", "w", encoding="utf-8").write(cfg)

sys.path.insert(0, APP)
import scanner, snmp

DEV = {}   # ip -> rec
def mac(i, j, pre="3c:52:82"): return f"{pre}:{i:02x}:{j:02x}:{random.randint(0,255):02x}"
def add(ip, vendor, ports, dns=None, nb=None, pre="00:11:22", local=True):
    DEV[ip] = {"ip": ip, "mac": mac(int(ip.split('.')[2]), int(ip.split('.')[3]), pre) if local else None,
               "vendor": vendor if local else None, "hostname": f"{dns}.example.local" if dns else None, "ports": ports,
               "netbios": nb, "_vendor": vendor, "_mac_pre": pre}

# Bâtiment 1 (local, ARP => MAC/constructeur)
add("10.10.0.254", "Fortinet", [22, 443], pre="00:09:0f")
add("10.10.0.10", "VMware", [53, 88, 135, 389, 445, 3389], "dc01", "DC01", "00:50:56")
add("10.10.0.11", "Hewlett Packard", [53, 88, 135, 389, 445, 3389], "dc02", "DC02", "94:57:a5")
for i, n in ((5, "esx01"), (6, "esx02")):
    add(f"10.10.0.{i}", "Dell Inc.", [22, 80, 443, 902], n, None, "b0:26:28")
add("10.10.0.7", "VMware", [22, 443], "vcenter", None, "00:50:56")
add("10.10.0.30", "Synology Incorporated", [22, 80, 443, 445, 5000], "nas01", "NAS01", "00:11:32")
add("10.10.0.31", "Hewlett Packard", [22, 135, 445, 3389], "srv-backup", "BACKUP01", "94:57:a5")
add("10.10.0.250", "Aruba, a Hewlett Packard Enterprise Company", [22, 23, 80, 443], None, None, "88:3a:30")
add("10.10.0.251", "Aruba, a Hewlett Packard Enterprise Company", [22, 80, 443], None, None, "88:3a:30")
add("10.10.0.245", "Ubiquiti Inc", [22, 443], None, None, "fc:ec:da")
add("10.10.0.246", "Ubiquiti Inc", [22, 443], None, None, "fc:ec:da")
add("10.10.0.60", "Kyocera Display", [80, 443, 9100], "prn-ground", None, "00:17:c8")
add("10.10.0.61", "Ricoh Company", [80, 443, 9100], "prn-finance", None, "00:26:73")
VMS = [("FILESRV01", "10.10.0.20", "esx01", "Microsoft Windows Server 2022 (64-bit)", 4, 16),
       ("APPSRV01", "10.10.0.21", "esx02", "Microsoft Windows Server 2022 (64-bit)", 8, 32),
       ("RDS01", "10.10.0.22", "esx02", "Microsoft Windows Server 2022 (64-bit)", 8, 48),
       ("SQL01", "10.10.0.23", "esx01", "Microsoft Windows Server 2019 (64-bit)", 8, 64),
       ("PRINTSRV01", "10.10.0.24", "esx02", "Microsoft Windows Server 2019 (64-bit)", 2, 8),
       ("glpi", "10.10.0.41", "esx01", "Debian GNU/Linux 12 (64-bit)", 2, 4),
       ("web01", "10.10.0.40", "esx02", "Ubuntu Linux (64-bit)", 2, 4),
       ("monitoring", "10.10.0.50", "esx01", "Debian GNU/Linux 12 (64-bit)", 4, 8),
       ("DC01", "10.10.0.10", "esx01", "Microsoft Windows Server 2022 (64-bit)", 2, 8),
       ("vcenter", "10.10.0.7", "esx01", "Other 3.x or later Linux (64-bit)", 4, 19),
       ("LEGACY-2012", "10.10.0.25", "esx02", "Microsoft Windows Server 2012 (64-bit)", 2, 8)]
for n, ip, h, o, c, r in VMS:
    if n in ("DC01", "vcenter", "LEGACY-2012"):
        continue
    w = "Windows" in o
    add(ip, "VMware", [135, 445, 3389] if w else [22, 80, 443], n.lower(), n if w else None, "00:50:56")
PCS1 = list(range(100, 124))
for i in PCS1:
    add(f"10.10.0.{i}", random.choice(["Dell Inc.", "Lenovo", "HP Inc."]), [135, 445], f"pc-{i:03d}", f"PC-A-{i:03d}", "3c:52:82")
for i in range(150, 156):
    add(f"10.10.0.{i}", "Yealink Network Technology", [80], None, None, "80:5e:c0")
# Bâtiment 2 (routé : pas de MAC par ARP ; NetBIOS donne nom + MAC des Windows)
add("10.20.0.250", "Aruba", [22, 80, 443], None, None, "88:3a:30", local=False)
add("10.20.0.245", "Ubiquiti", [22, 443], None, None, "fc:ec:da", local=False)
add("10.20.0.60", "Brother", [80, 9100], "prn-siteb", None, "00:80:77", local=False)
PCS2 = list(range(100, 118))
for i in PCS2:
    add(f"10.20.0.{i}", "Dell", [135, 445], f"pcb-{i:03d}", f"PC-B-{i:03d}", "3c:52:82", local=False)
for i in range(150, 154):
    add(f"10.20.0.{i}", "Yealink", [80], None, None, "80:5e:c0", local=False)
ABSENT = {"10.10.0.117", "10.10.0.121", "10.20.0.111", "10.20.0.115", "10.10.0.153"}   # PC éteints
DOWN = {"10.10.0.24"}  # PRINTSRV01 en panne
NB_MAC = {ip: mac(int(ip.split('.')[2]), int(ip.split('.')[3]), "3c:52:82") for ip, d in DEV.items() if d["netbios"]}
for ip, d in DEV.items():
    if d["mac"] is None and d["netbios"]:
        pass

SWEEPS = [0]
def ping_sweep(subnet, exclude=(), dns_servers=()):
    pre = subnet.rsplit(".", 1)[0]
    out = {}
    SWEEPS[0] += 1
    first = SWEEPS[0] <= 2
    for ip, d in DEV.items():
        if ip.rsplit(".", 1)[0] == pre and (first or (ip not in ABSENT and ip not in DOWN)):
            out[ip] = {"ip": ip, "mac": d["mac"], "vendor": d["vendor"], "hostname": d["hostname"] if dns_servers else None,
                       "ports": [], "netbios": None}
    return out
scanner.ping_sweep = ping_sweep
scanner.port_scan = lambda ips, ports, chunk=64: {ip: DEV[ip]["ports"] for ip in ips}
scanner.netbios_scan = lambda ips, chunk=128: {ip: {"netbios": DEV[ip]["netbios"], "mac": NB_MAC.get(ip), "vendor": DEV[ip]["_vendor"]}
                                               for ip in ips if DEV[ip]["netbios"]}
scanner.reverse_dns = lambda ips, srv: {ip: DEV[ip]["hostname"] for ip in ips if DEV[ip]["hostname"]}
scanner.traceroute = lambda t, max_hops=20: ["10.10.0.254", "203.0.113.1"]
scanner.default_gateway = lambda: "10.10.0.254"

def macof(ip):
    return DEV[ip]["mac"] or NB_MAC.get(ip)

# ---------- SNMP simulé
SW = {"10.10.0.250": {"name": "SW-CORE", "n": 24}, "10.10.0.251": {"name": "SW-A-FLOOR1", "n": 48},
      "10.20.0.250": {"name": "SW-SITE-B", "n": 48}}
PLUG = {"10.10.0.250": {1: "10.10.0.5", 2: "10.10.0.5", 3: "10.10.0.6", 4: "10.10.0.6", 5: "10.10.0.11",
                          6: "10.10.0.30", 7: "10.10.0.31", 20: "10.10.0.245"},
        "10.10.0.251": {**{k: f"10.10.0.{100 + k - 1}" for k in range(1, 25)}, 30: "10.10.0.60", 31: "10.10.0.61",
                          **{32 + k: f"10.10.0.{150 + k}" for k in range(6)}, 40: "10.10.0.246"},
        "10.20.0.250": {**{k: f"10.20.0.{100 + k - 1}" for k in range(1, 19)}, 30: "10.20.0.60", 40: "10.20.0.245",
                           **{32 + k: f"10.20.0.{150 + k}" for k in range(4)}}}
UPL = {"10.10.0.250": {24: ("SW-A-FLOOR1", "1/1/48"), 22: ("SW-SITE-B", "1/1/48"), 23: ("FW-EDGE", "port1")},
       "10.10.0.251": {48: ("SW-CORE", "1/1/24")}, "10.20.0.250": {48: ("SW-CORE", "1/1/22")}}
def fake_walk(ip, community, oid, timeout=60):
    if ip not in SW:
        return {}
    sw = SW[ip]; n = sw["n"]
    O = snmp.OID
    if oid == O["sysName"]: return {"": sw["name"]}
    if oid == O["sysDescr"]: return {"": "Aruba JL075A 3810M-16SFP+-2-slot Switch, revision KB.16.10"}
    if oid == O["ifName"]: return {str(k): f"1/1/{k}" for k in range(1, n + 1)}
    if oid == O["ifAlias"]: return {str(k): ("UPLINK" if k in UPL[ip] else "") for k in range(1, n + 1)}
    if oid == O["ifHighSpeed"]: return {str(k): ("10000" if k in UPL[ip] else "1000") for k in range(1, n + 1)}
    if oid == O["ifOperStatus"]: return {str(k): ("1" if k in UPL[ip] or (k in PLUG[ip] and PLUG[ip][k] not in ABSENT) else "2") for k in range(1, n + 1)}
    if oid == O["basePortIfIndex"]: return {str(k): str(k) for k in range(1, n + 1)}
    if oid == O["qFdbPort"]:
        out = {}
        for port, dip in PLUG[ip].items():
            m = macof(dip)
            if m: out["1." + ".".join(str(int(x, 16)) for x in m.split(":"))] = str(port)
        for port in UPL[ip]:
            for j in range(12):
                out[f"1.2.0.0.{port}.{j}.1"] = str(port)
        # VMs derrière les ESXi
        if ip == "10.10.0.250":
            for k, (nm, vip, h, *_ ) in enumerate(VMS):
                out[f"1.0.80.86.16.{k}.9"] = "1" if h == "esx01" else "3"
            for j in range(8):
                out[f"1.0.80.86.17.{j}.9"] = "1"
        return out
    if oid == O["lldpLocPortId"]: return {str(k): f"1/1/{k}" for k in range(1, n + 1)}
    if oid == O["lldpRemSysName"]: return {f"0.{p}.1": v[0] for p, v in UPL[ip].items()}
    if oid == O["lldpRemPortId"]: return {f"0.{p}.1": v[1] for p, v in UPL[ip].items()}
    return {}
if WITH_SNMP:
    snmp.walk = fake_walk

# ---------- faux vCenter
class FakeVC:
    def __init__(s):
        hosts = []
        for i, n in ((5, "esx01"), (6, "esx02")):
            hosts.append({"moid": f"host-{i}", "name": f"{n}.example.local", "ips": [f"10.10.0.{i}"], "state": "connected",
                          "maintenance": False, "power": "poweredOn", "health": "green" if n == "esx01" else "yellow",
                          "model": "Dell Inc. PowerEdge R750", "version": "VMware ESXi 8.0.3 build-24022510", "cluster": "CL-PROD",
                          "cores": 32, "cpu_mhz_total": 32 * 2900, "cpu_mhz_used": int(32 * 2900 * (0.31 if n == "esx01" else 0.58)),
                          "cpu_pct": 31.0 if n == "esx01" else 58.4, "mem_gb": 512.0, "mem_used_gb": 301.5 if n == "esx01" else 452.3,
                          "mem_pct": 58.9 if n == "esx01" else 88.3, "uptime_s": 86400 * 41})
        vms = []
        for k, (nm, ip, h, o, c, r) in enumerate(VMS):
            on = nm != "LEGACY-2012"
            vms.append({"moid": f"vm-{k}", "name": nm, "ips": [ip] if on else [], "macs": [f"00:50:56:10:{k:02x}:09"],
                        "power": "poweredOn" if on else "poweredOff", "host": f"{h}.example.local", "hostname": nm.lower(), "os": o,
                        "tools": "guestToolsRunning" if on else "guestToolsNotRunning", "health": "green", "vcpu": c, "mem_gb": float(r),
                        "cpu_pct": round(random.uniform(3, 70), 1) if on else None, "mem_pct": round(random.uniform(30, 92), 1) if on else None,
                        "disk_gb": round(random.uniform(60, 900), 1), "uptime_s": 86400 * random.randint(1, 60) if on else None})
        s.state = {"up": True, "error": "", "updated": time.time(), "links": [], "hosts": hosts, "vms": vms,
                   "datastores": [{"name": "DS-SSD-01", "type": "VMFS", "accessible": True, "capacity_gb": 3840, "free_gb": 1210, "used_pct": 68.5, "hosts": ["esx01.example.local", "esx02.example.local"]},
                                  {"name": "DS-SSD-02", "type": "VMFS", "accessible": True, "capacity_gb": 3840, "free_gb": 420, "used_pct": 89.1, "hosts": ["esx01.example.local", "esx02.example.local"]},
                                  {"name": "NAS01-NFS", "type": "NFS", "accessible": True, "capacity_gb": 16000, "free_gb": 9800, "used_pct": 38.8, "hosts": ["esx01.example.local"]}],
                   "alarms": [{"entity": "esx02.example.local", "alarm": "Host memory usage", "status": "yellow", "acknowledged": False}]}
    def poll(s): return s.state
    def network_links(s):
        L = []
        for i, n, ports in ((5, "esx01", ["1/1/1", "1/1/2"]), (6, "esx02", ["1/1/3", "1/1/4"])):
            for k, p in enumerate(ports):
                L.append({"host": f"{n}.example.local", "host_ips": [f"10.10.0.{i}"], "nic": f"vmnic{k}", "proto": "LLDP",
                          "switch": "SW-CORE", "port": p, "switch_ip": "10.10.0.250", "platform": "Aruba JL075A 3810M"})
        s.state["links"] = L
        return L

AGENTS = [("FILESRV01", "10.10.0.20", "windows"), ("APPSRV01", "10.10.0.21", "windows"), ("RDS01", "10.10.0.22", "windows"),
          ("SQL01", "10.10.0.23", "windows"), ("PRINTSRV01", "10.10.0.24", "windows"), ("DC01", "10.10.0.10", "windows"),
          ("DC02", "10.10.0.11", "windows"), ("BACKUP01", "10.10.0.31", "windows"), ("glpi", "10.10.0.41", "linux"),
          ("web01", "10.10.0.40", "linux"), ("monitoring", "10.10.0.50", "linux")]
MET = {a[0]: {"cpu": round(random.uniform(4, 60), 1), "mem": round(random.uniform(35, 85), 1), "disk": round(random.uniform(30, 80), 1),
              "uptime": 86400 * random.randint(2, 50)} for a in AGENTS}
MET["FILESRV01"]["disk"] = 93.4; MET["RDS01"]["cpu"] = 87.2; MET["SQL01"]["mem"] = 91.5
NOW = time.time()
ago = lambda minutes: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - minutes * 60))
AM = [
  {"labels": {"alertname": "AgentSilent", "severity": "critical", "instance": "PRINTSRV01", "os": "windows"}, "annotations": {"summary": "PRINTSRV01 stopped sending data", "description": "Server off, crashed, or the Alloy agent is stopped."}, "startsAt": ago(38), "fingerprint": "a1"},
  {"labels": {"alertname": "DeviceUnreachable", "severity": "warning", "node": "ip:10.10.0.24", "name": "PRINTSRV01", "role": "vm"}, "annotations": {"summary": "PRINTSRV01 (vm) does not answer ping"}, "startsAt": ago(37), "fingerprint": "a2"},
  {"labels": {"alertname": "WindowsDiskFull", "severity": "warning", "instance": "FILESRV01", "volume": "D:"}, "annotations": {"summary": "Disk D: is 93% full on FILESRV01"}, "startsAt": ago(190), "fingerprint": "a3"},
  {"labels": {"alertname": "CertificateExpiresSoon", "severity": "warning", "instance": "https://intranet.example.local", "name": "Intranet"}, "annotations": {"summary": "Intranet certificate expires in 9 days"}, "startsAt": ago(1500), "fingerprint": "a4"},
  {"labels": {"alertname": "NewDeviceOnNetwork", "severity": "info", "ip": "10.20.0.153", "vendor": "Yealink"}, "annotations": {"summary": "New device on the network: 10.20.0.153 (Yealink)"}, "startsAt": ago(25), "fingerprint": "a5"},
  {"labels": {"alertname": "Watchdog", "severity": "none"}, "annotations": {}, "startsAt": ago(600), "fingerprint": "w"},
]
ZPROB = [{"triggerid": "1", "description": "Datastore DS-SSD-02: Free space is low (less than 15%)", "priority": "3", "lastchange": str(int(NOW - 7200)),
          "hosts": [{"host": "vcenter", "name": "vCenter"}], "lastEvent": {"eventid": "901", "acknowledged": "0", "clock": str(int(NOW - 7200))}},
         {"triggerid": "2", "description": "esx02.example.local: Hypervisor memory utilization is high (over 85%)", "priority": "2", "lastchange": str(int(NOW - 3600)),
          "hosts": [{"host": "esx02", "name": "esx02.example.local"}], "lastEvent": {"eventid": "902", "acknowledged": "1", "clock": str(int(NOW - 3600))}}]

def targets(name):
    try:
        return json.load(open(os.path.join(os.environ["COCKPIT_TARGETS_DIR"], f"{name}.json")))
    except Exception:
        return []

def vec(rows): return {"status": "success", "data": {"resultType": "vector", "result": [{"metric": m, "value": [time.time(), str(v)]} for m, v in rows]}}
def mat(rows): return {"status": "success", "data": {"resultType": "matrix", "result": [{"metric": m, "values": v} for m, v in rows]}}
def series(base, amp, start, end, step):
    t = start; out = []
    while t <= end:
        out.append([t, str(round(max(0, base + amp * math.sin(t / 3600) + random.uniform(-amp / 3, amp / 3)), 3))]); t += step
    return out

def prom_query(q):
    icmp_ips = [t["targets"][0] for t in targets("icmp")]
    tcp_t = [t["targets"][0] for t in targets("tcp")]
    def up_ip(ip): return 0 if ip in ABSENT or ip in DOWN else 1
    if "max_over_time(up{" in q: return vec([({"instance": i, "ip": ip, "os": o}, 1) for i, ip, o in AGENTS])
    if q.startswith("up{"): return vec([({"instance": i, "ip": ip, "os": o}, 1) for i, ip, o in AGENTS if ip not in DOWN])
    if q == "lldp_neighbor_info": return vec([({"instance": "monitoring", "ip": "10.10.0.50", "interface": "ens192", "chassis_name": "esx01", "port_id": "vmnic0", "protocol": "LLDP"}, 1)][:0])
    if "max_over_time(probe_success{job=\"blackbox_icmp\"}" in q: return vec([({"instance": ip}, 0 if ip in ABSENT and ip.endswith(("117", "115")) else 1) for ip in icmp_ips])
    if "max_over_time(probe_success{job=\"blackbox_tcp\"}" in q: return vec([({"instance": t}, 1) for t in tcp_t])
    if 'probe_icmp_duration_seconds{job="blackbox_icmp", phase="rtt"}) and on' in q:
        return vec([({"instance": ip}, (0.018 if ip == "203.0.113.1" else 0.009 if ip in ("1.1.1.1", "8.8.8.8") else 0.0007 if ip.startswith("10.10.0.") else 0.0031)) for ip in icmp_ips if up_ip(ip)])
    if 'max by (instance) (probe_success{job="blackbox_icmp"})' in q: return vec([({"instance": ip}, up_ip(ip)) for ip in icmp_ips])
    if 'max by (instance) (probe_success{job="blackbox_tcp"})' in q: return vec([({"instance": t}, up_ip(t.split(":")[0])) for t in tcp_t])
    if 'role="internet"' in q: return vec([({}, 1)])
    for key, name in (("node_cpu_seconds_total", "cpu"), ("MemAvailable", "mem"), ("node_filesystem_avail", "disk"), ("boot_time", "uptime")):
        if key in q and "instance=" not in q:
            return vec([({"instance": i}, MET[i][name]) for i, ip, o in AGENTS if ip not in DOWN])
    if "instance=" in q and ("node_filesystem" in q or "windows_logical_disk" in q):
        inst = re.search(r'instance="([^"]+)"', q).group(1)
        if "windows_logical_disk" in q and dict((a[0], a[2]) for a in AGENTS).get(inst) == "windows":
            return vec([({"instance": inst, "volume": "C:"}, 61.2), ({"instance": inst, "volume": "D:"}, MET[inst]["disk"])])
        if "node_filesystem" in q and dict((a[0], a[2]) for a in AGENTS).get(inst) == "linux":
            return vec([({"instance": inst, "mountpoint": "/"}, MET[inst]["disk"]), ({"instance": inst, "mountpoint": "/var"}, 41.0)])
        return vec([])
    if "avg_over_time(probe_success" in q:
        ip = re.search(r'instance="([^"]+)"', q).group(1); return vec([({"instance": ip}, 0 if ip in DOWN else 99.7)])
    m = re.search(r'job="blackbox_http", instance="([^"]+)"', q)
    if m:
        url = m.group(1)
        if q.startswith("probe_success"): return vec([({"instance": url}, 1)])
        if q.startswith("probe_duration"): return vec([({"instance": url}, 0.182 if "intranet" in url else 0.341)])
        if "cert_expiry" in q: return vec([({"instance": url}, 9 if "intranet" in url else 74)])
        if "status_code" in q: return vec([({"instance": url}, 200)])
    m = re.search(r'job="blackbox_dns", instance="([^"]+)"', q)
    if m:
        return vec([({"instance": m.group(1)}, 1 if q.startswith("probe_success") else 0.004)])
    m = re.search(r'job="blackbox_icmp", instance="([^"]+)", phase="rtt"', q)
    if m: return vec([({"instance": m.group(1)}, 0.009)])
    m = re.search(r'probe_success\{job="blackbox_icmp", instance="([^"]+)"\}', q)
    if m: return vec([({"instance": m.group(1)}, 1)])
    if "ifHCInOctets" in q or "ifHCOutOctets" in q:
        rows = []
        for ip, ports in PLUG.items():
            for p in list(ports) + list(UPL[ip]):
                rows.append(({"instance": ip, "ifName": f"1/1/{p}"}, random.uniform(2e5, 4e8) if p in UPL[ip] else random.uniform(1e3, 8e7)))
        return vec(rows)
    return vec([])

def prom_range(q, start, end, step):
    if "role=\"internet\"" in q: return mat([({}, series(9, 3, start, end, step))])
    if "probe_icmp_duration" in q: return mat([({}, series(0.8, 0.4, start, end, step))])
    if "node_cpu" in q: return mat([({"instance": i}, series(MET[i]["cpu"], 12, start, end, step)) for i, *_ in AGENTS])
    if "MemAvailable" in q: return mat([({"instance": i}, series(MET[i]["mem"], 4, start, end, step)) for i, *_ in AGENTS])
    return mat([])

LOGS = ["Le service Spouleur d'impression s'est arrêté de façon inattendue.", "The Windows Update service entered the running state.",
        "Échec de la connexion de l'utilisateur EXAMPLE\\intern : mot de passe incorrect.", "Disk D: reached 93% capacity.",
        "The time service is now synchronizing the system time with the time source DC01.example.local."]

CALLS = []
class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _j(self, obj, code=200):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path); qs = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/api/v1/query": return self._j(prom_query(qs.get("query", "")))
        if u.path == "/api/v1/query_range": return self._j(prom_range(qs["query"], float(qs["start"]), float(qs["end"]), float(qs["step"])))
        if u.path == "/api/v2/alerts": return self._j(AM)
        if u.path == "/loki/api/v1/query_range":
            vals = [[str(int((NOW - k * 600) * 1e9)), LOGS[k % len(LOGS)]] for k in range(12)]
            return self._j({"data": {"result": [{"stream": {"host": "x", "level": "error", "source": "Service Control Manager"}, "values": vals}]}})
        if u.path == "/loki/api/v1/query": return self._j({"data": {"result": [{"value": [0, "14"]}]}})
        if u.path == "/calls": return self._j(CALLS)
        self._j({}, 404)
    def do_POST(self):
        u = urlparse(self.path)
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if u.path == "/v1/chat/completions":
            en = "English" in json.dumps(body.get("messages", []))
            txt = ("### Diagnosis\nPRINTSRV01 no longer answers ping **and** its agent went silent at the same time, while vCenter still sees it powered on: "
                   "the VM is most likely **frozen** (guest OS hung) or its network adapter is disconnected.\n\n### Checks\n"
                   "1. Open the VM console in vCenter (`esx02`) and see whether Windows responds.\n"
                   "2. Check that the network adapter is **connected** in the VM settings.\n"
                   "3. The logs show *Print Spooler stopped* just before: restart the `Spooler` service if the VM answers.\n"
                   "4. Otherwise: `Restart Guest OS`, then a hard reset if needed.\n\n### Impact\nPrinting is blocked on both sites.") if en else (
                   "### Diagnostic\nPRINTSRV01 ne répond plus au ping **et** son agent s'est tu au même moment, alors que vCenter le voit allumé : "
                   "la VM est probablement **figée** (OS planté) ou sa carte réseau est déconnectée.\n\n### Vérifications\n"
                   "1. Ouvrir la console de la VM dans vCenter (`esx02`) et vérifier si Windows répond.\n"
                   "2. Vérifier que la carte réseau est **connectée** dans les paramètres de la VM.\n"
                   "3. Les logs montrent *Spouleur d'impression arrêté* juste avant : redémarrer le service `Spooler` si la VM répond.\n"
                   "4. Sinon : redémarrage de l'invité (`Restart Guest OS`), puis arrêt forcé si besoin.\n\n### Impact\nL'impression est bloquée sur les deux sites.")
            return self._j({"choices": [{"message": {"content": txt}}]})
        if u.path == "/api_jsonrpc.php":
            m = body["method"]; p = body.get("params") or {}
            CALLS.append((m, p))
            R = {"apiinfo.version": "7.0.22", "user.login": "tok", "user.get": [{"userid": "1"}], "host.get": [],
                 "hostinterface.update": {}, "usermacro.get": [], "usermacro.createglobal": {}, "hostgroup.get": [{"groupid": "5"}],
                 "hostgroup.create": {"groupids": ["9"]}, "template.get": [{"templateid": "100"}], "host.create": {"hostids": ["1"]},
                 "usergroup.get": [], "usergroup.create": {"usrgrpids": ["7"]}, "role.get": [{"roleid": "1"}],
                 "user.create": {"userids": ["3"]}, "user.update": {}, "drule.get": [], "drule.create": {"druleids": ["4"]},
                 "action.get": [], "action.create": {}, "trigger.get": ZPROB}
            if m == "user.login" and p.get("password") not in ("demo-password",):
                return self._j({"jsonrpc": "2.0", "error": {"message": "Incorrect", "data": "login"}, "id": body["id"]})
            return self._j({"jsonrpc": "2.0", "result": R.get(m, {}), "id": body["id"]})
        self._j({}, 404)

threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", 19090), Fake).serve_forever, daemon=True).start()
print(f"NetCockpit demo: http://localhost:{PORT}  (simulated network, nothing is scanned)", flush=True)
import main
main.VC = FakeVC()
threading.Timer(8, main.RESCAN.set).start()   # 2e scan : des postes "disparaissent" -> statut absent
main.main()
