"""Découverte réseau : nmap (ping/ARP, ports, NetBIOS), traceroute, réseaux locaux, classification."""
import ipaddress
import json
import logging
import re
import subprocess
import xml.etree.ElementTree as ET

log = logging.getLogger("cockpit.scan")

IGNORED_IFACES = re.compile(r"^(lo|docker\d*|br-|veth|virbr|cni|flannel|cali|tun|wg|tailscale|zt)")


def _run(cmd, timeout):
    log.debug("exec: %s", " ".join(cmd))
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        log.warning("délai dépassé : %s", " ".join(cmd[:5]))
        return ""
    except FileNotFoundError:
        log.error("commande introuvable : %s", cmd[0])
        return ""
    if res.returncode != 0 and not res.stdout:
        log.warning("échec %s : %s", cmd[0], res.stderr.strip()[:300])
    return res.stdout


def local_networks():
    out = _run(["ip", "-j", "-4", "addr"], 10)
    nets = []
    try:
        for iface in json.loads(out or "[]"):
            if IGNORED_IFACES.match(iface.get("ifname", "")):
                continue
            for a in iface.get("addr_info", []):
                net = ipaddress.ip_interface(f"{a['local']}/{a['prefixlen']}").network
                if net.prefixlen < 20:
                    net = ipaddress.ip_interface(f"{a['local']}/24").network
                if net.prefixlen <= 30 and net not in nets:
                    nets.append(net)
    except (ValueError, KeyError) as e:
        log.warning("lecture des interfaces impossible : %s", e)
    return [str(n) for n in nets]


def default_gateway():
    out = _run(["ip", "-j", "-4", "route", "show", "default"], 10)
    try:
        routes = json.loads(out or "[]")
        return routes[0].get("gateway") if routes else None
    except ValueError:
        return None


def system_dns_servers():
    servers = []
    try:
        for line in open("/etc/resolv.conf", encoding="utf-8"):
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "nameserver" and not parts[1].startswith("127."):
                servers.append(parts[1])
    except OSError:
        pass
    return servers


# ---------------------------------------------------------------- nmap

def parse_nmap_xml(xml_text):
    """{ip: {ip, mac, vendor, hostname, ports, netbios, netbios_mac}} pour les hôtes 'up'."""
    hosts = {}
    if not xml_text.strip():
        return hosts
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        log.warning("XML nmap illisible : %s", e)
        return hosts
    for h in root.findall("host"):
        status = h.find("status")
        if status is None or status.get("state") != "up":
            continue
        rec = {"ip": None, "mac": None, "vendor": None, "hostname": None, "ports": [], "netbios": None}
        for addr in h.findall("address"):
            if addr.get("addrtype") == "ipv4":
                rec["ip"] = addr.get("addr")
            elif addr.get("addrtype") == "mac":
                rec["mac"] = addr.get("addr", "").lower()
                rec["vendor"] = addr.get("vendor")
        for hn in h.findall("hostnames/hostname"):
            if hn.get("type") in (None, "PTR", "user"):
                rec["hostname"] = hn.get("name")
                break
        for p in h.findall("ports/port"):
            st = p.find("state")
            if st is not None and st.get("state") == "open":
                rec["ports"].append(int(p.get("portid")))
        for sc in h.findall(".//script[@id='nbstat']"):
            out = sc.get("output", "")
            m = re.search(r"NetBIOS name:\s*([^,\s]+)", out)
            if m and m.group(1) not in ("<unknown>",):
                rec["netbios"] = m.group(1)
            m = re.search(r"NetBIOS MAC:\s*([0-9a-fA-F:]{17})(?:\s*\(([^)]*)\))?", out)
            if m and m.group(1) != "00:00:00:00:00:00":
                rec["netbios_mac"] = m.group(1).lower()
                if m.group(2):
                    rec["netbios_vendor"] = m.group(2)
        if rec["ip"]:
            hosts[rec["ip"]] = rec
    return hosts


def _dns_args(dns_servers):
    return ["--dns-servers", ",".join(dns_servers)] if dns_servers else []


def ping_sweep(subnet, exclude=(), dns_servers=()):
    cmd = ["nmap", "-sn", "-T4", "--max-retries", "1", "--host-timeout", "20s",
           "-PE", "-PP", "-PS22,80,135,443,445,3389", "-PA80,443"] + _dns_args(dns_servers)
    if exclude:
        cmd += ["--exclude", ",".join(exclude)]
    cmd += ["-oX", "-", str(subnet)]
    return parse_nmap_xml(_run(cmd, 900))


def port_scan(ips, ports, chunk=64):
    found = {}
    ips = list(ips)
    for i in range(0, len(ips), chunk):
        cmd = ["nmap", "-Pn", "-n", "-sS", "-T4", "--open", "--max-retries", "1",
               "--host-timeout", "60s", "-p", ",".join(str(p) for p in ports), "-oX", "-"] + ips[i:i + chunk]
        for ip, rec in parse_nmap_xml(_run(cmd, 900)).items():
            found[ip] = sorted(rec["ports"])
    return found


def netbios_scan(ips, chunk=128):
    """Nom NetBIOS (machines Windows, NAS, imprimantes) + MAC, même à travers un routeur."""
    found = {}
    ips = list(ips)
    for i in range(0, len(ips), chunk):
        cmd = ["nmap", "-sU", "-Pn", "-n", "-p", "137", "--script", "nbstat", "--host-timeout", "15s",
               "--max-retries", "1", "-oX", "-"] + ips[i:i + chunk]
        for ip, rec in parse_nmap_xml(_run(cmd, 600)).items():
            if rec.get("netbios"):
                found[ip] = {"netbios": rec["netbios"], "mac": rec.get("netbios_mac"), "vendor": rec.get("netbios_vendor")}
    return found


def reverse_dns(ips, dns_servers):
    """Résolution inverse via un DNS précis (liste nmap -sL, aucun paquet vers les cibles)."""
    if not ips:
        return {}
    cmd = ["nmap", "-sL", "-R"] + _dns_args(dns_servers) + ["-oX", "-"] + list(ips)
    out = {}
    text = _run(cmd, 300)
    try:
        root = ET.fromstring(text) if text.strip() else None
    except ET.ParseError:
        root = None
    if root is None:
        return out
    for h in root.findall("host"):
        ip = next((a.get("addr") for a in h.findall("address") if a.get("addrtype") == "ipv4"), None)
        hn = h.find("hostnames/hostname")
        if ip and hn is not None and hn.get("name"):
            out[ip] = hn.get("name")
    return out


# ---------------------------------------------------------------- traceroute

TRACE_LINE = re.compile(r"^\s*(\d+)\s+(\S+)")


def parse_traceroute(text):
    hops = []
    for line in text.splitlines():
        m = TRACE_LINE.match(line)
        if not m:
            continue
        tok = m.group(2)
        try:
            ipaddress.ip_address(tok)
            hops.append(tok)
        except ValueError:
            hops.append(None)
    return hops


def traceroute(target, max_hops=20):
    hops = parse_traceroute(_run(["traceroute", "-n", "-I", "-q", "1", "-w", "1", "-m", str(max_hops), target], 90))
    while hops and (hops[-1] is None or hops[-1] == target):
        hops.pop()
    return hops


DOC_NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]


def is_private(ip):
    try:
        a = ipaddress.ip_address(ip)
        if any(a in n for n in DOC_NETS):      # plages de documentation : jamais sur un LAN
            return False
        return a.is_private or a in ipaddress.ip_network("100.64.0.0/10")
    except ValueError:
        return False


# ---------------------------------------------------------------- classification

VENDOR_ROLES = [
    (re.compile(r"fortinet|palo alto|sophos|stormshield|netasq|arkoon|watchguard|check ?point|sonicwall|barracuda|zscaler", re.I), "firewall"),
    (re.compile(r"ubiquiti|ruckus|aerohive|cambium|meraki|engenius", re.I), "wifi"),
    (re.compile(r"cisco|juniper|aruba|hewlett packard enterprise|netgear|d-link|tp-link|mikrotik|routerboard|extreme net|brocade|allied telesis|zyxel|huawei tech|edgecore|mellanox|alcatel-lucent ent|h3c|ruijie|dell emc network", re.I), "network"),
    (re.compile(r"synology|qnap|netapp|western digital|buffalo|asustor|drobo|terramaster", re.I), "nas"),
    (re.compile(r"brother|canon|kyocera|ricoh|xerox|epson|lexmark|konica|sharp|oki data|zebra|toshiba tec", re.I), "printer"),
    (re.compile(r"axis comm|hikvision|dahua|hanwha|vivotek|bosch security|milestone|uniview", re.I), "camera"),
    (re.compile(r"polycom|yealink|snom|grandstream|avaya|mitel|fanvil|gigaset|poly\b", re.I), "phone"),
    (re.compile(r"apple|samsung elec|xiaomi|oneplus|oppo|huawei device|motorola mob", re.I), "mobile"),
]

ROLE_LABELS = {
    "internet": "Internet", "isp": "Opérateur", "gateway": "Passerelle", "firewall": "Firewall",
    "router": "Routeur", "switch": "Switch", "network": "Équipement réseau", "wifi": "Borne Wi-Fi",
    "esxi": "ESXi", "hypervisor": "Hyperviseur", "vm": "VM", "server": "Serveur", "dc": "Contrôleur de domaine",
    "windows": "Poste Windows", "linux": "Linux", "nas": "NAS", "printer": "Imprimante", "camera": "Caméra",
    "phone": "Téléphone IP", "mobile": "Mobile", "device": "Équipement", "site": "Site", "subnet": "Réseau",
    "group": "Groupe", "other": "Autre",
}


def classify(dev):
    """Rôle d'un équipement découvert par scan (sans agent ni vCenter)."""
    ports = set(dev.get("ports") or [])
    vendor = dev.get("vendor") or dev.get("netbios_vendor") or ""
    if {53, 88, 389} <= ports:
        return "dc"
    for rx, role in VENDOR_ROLES:
        if rx.search(vendor):
            if role in ("network", "wifi") and ports & {3389, 445}:
                break
            return role
    if 902 in ports and 443 in ports:
        return "esxi"
    if 8006 in ports:
        return "hypervisor"
    if 9100 in ports and not ports & {22, 3389}:
        return "printer"
    if ports & {3389, 5985} or ports >= {135, 445}:
        return "windows"
    if 22 in ports:
        return "linux"
    if ports & {23, 161} and not ports & {445}:
        return "network"
    if dev.get("netbios"):
        return "windows"
    return "device"
