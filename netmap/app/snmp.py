"""Topologie des switchs par SNMP (lecture seule) : ports, LLDP/CDP, table des MAC, ARP.

Utilisé seulement si une communauté SNMP est fournie (accès en lecture demandé au prestataire)."""
import logging
import re
import subprocess

log = logging.getLogger("netmap.snmp")

OID = {
    "sysName": ".1.3.6.1.2.1.1.5.0",
    "sysDescr": ".1.3.6.1.2.1.1.1.0",
    "ifName": ".1.3.6.1.2.1.31.1.1.1.1",
    "ifAlias": ".1.3.6.1.2.1.31.1.1.1.18",
    "ifHighSpeed": ".1.3.6.1.2.1.31.1.1.1.15",
    "ifOperStatus": ".1.3.6.1.2.1.2.2.1.8",
    "basePortIfIndex": ".1.3.6.1.2.1.17.1.4.1.2",
    "qFdbPort": ".1.3.6.1.2.1.17.7.1.2.2.1.2",
    "dFdbPort": ".1.3.6.1.2.1.17.4.3.1.2",
    "lldpLocPortId": ".1.0.8802.1.1.2.1.3.7.1.3",
    "lldpLocPortDesc": ".1.0.8802.1.1.2.1.3.7.1.4",
    "lldpRemChassisId": ".1.0.8802.1.1.2.1.4.1.1.5",
    "lldpRemPortId": ".1.0.8802.1.1.2.1.4.1.1.7",
    "lldpRemPortDesc": ".1.0.8802.1.1.2.1.4.1.1.8",
    "lldpRemSysName": ".1.0.8802.1.1.2.1.4.1.1.9",
    "cdpAddress": ".1.3.6.1.4.1.9.9.23.1.2.1.1.4",
    "cdpDeviceId": ".1.3.6.1.4.1.9.9.23.1.2.1.1.6",
    "cdpDevicePort": ".1.3.6.1.4.1.9.9.23.1.2.1.1.7",
    "cdpPlatform": ".1.3.6.1.4.1.9.9.23.1.2.1.1.8",
    "arpPhys": ".1.3.6.1.2.1.4.22.1.2",
}


def _clean(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] == '"':
        v = v[1:-1]
    return v


def walk(ip, community, oid, timeout=60):
    """snmpwalk -> {suffixe_index: valeur}."""
    cmd = ["snmpwalk", "-v2c", "-c", community, "-On", "-Oq", "-t", "2", "-r", "1", ip, oid]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        log.debug("snmpwalk %s %s : %s", ip, oid, e)
        return {}
    res = {}
    base = oid.rstrip(".") + "."
    for line in out.splitlines():
        if not line.startswith("."):
            continue
        parts = line.split(" ", 1)
        key = parts[0]
        val = _clean(parts[1]) if len(parts) > 1 else ""
        if "No Such" in val or "No more variables" in val:
            continue
        if key == oid:
            res[""] = val
        elif key.startswith(base):
            res[key[len(base):]] = val
    return res


def get(ip, community, oid):
    return walk(ip, community, oid).get("")


def _hexmac(v):
    """'00 1B 54 00 10 02' / '0:1b:54:0:10:2' / '00:1b:...' -> '00:1b:54:00:10:02'."""
    parts = re.split(r"[\s:.-]+", v.strip())
    parts = [p for p in parts if p]
    if len(parts) == 6 and all(re.fullmatch(r"[0-9A-Fa-f]{1,2}", p) for p in parts):
        return ":".join(p.zfill(2) for p in parts).lower()
    return None


def _hexip(v):
    parts = [p for p in re.split(r"\s+", v.strip()) if p]
    if len(parts) == 4 and all(re.fullmatch(r"[0-9A-Fa-f]{2}", p) for p in parts):
        return ".".join(str(int(p, 16)) for p in parts)
    if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", v.strip()):
        return v.strip()
    return None


def poll_device(ip, community):
    """Lit un équipement réseau. Retourne None s'il ne répond pas en SNMP."""
    name = get(ip, community, OID["sysName"])
    if name is None:
        return None
    descr = get(ip, community, OID["sysDescr"]) or ""
    if_name = walk(ip, community, OID["ifName"])
    if_alias = walk(ip, community, OID["ifAlias"])
    if_speed = walk(ip, community, OID["ifHighSpeed"])
    if_oper = walk(ip, community, OID["ifOperStatus"])
    base = walk(ip, community, OID["basePortIfIndex"])           # bridgePort -> ifIndex

    ports = {}
    for idx, n in if_name.items():
        ports[idx] = {"ifindex": idx, "name": n, "alias": if_alias.get(idx, ""),
                      "speed_mbps": int(if_speed.get(idx, "0") or 0) if str(if_speed.get(idx, "0")).isdigit() else 0,
                      "up": str(if_oper.get(idx, "")).startswith(("1", "up")),
                      "macs": [], "neighbors": []}

    # Table des MAC (VLAN-aware puis classique)
    fdb = walk(ip, community, OID["qFdbPort"])
    entries = []
    for idx, bport in fdb.items():
        octets = idx.split(".")[-6:]
        if len(octets) == 6:
            entries.append((":".join(f"{int(o):02x}" for o in octets), bport))
    if not entries:
        for idx, bport in walk(ip, community, OID["dFdbPort"]).items():
            octets = idx.split(".")[-6:]
            if len(octets) == 6:
                entries.append((":".join(f"{int(o):02x}" for o in octets), bport))
    for mac, bport in entries:
        ifidx = base.get(bport, bport)
        if ifidx in ports and mac not in ports[ifidx]["macs"]:
            ports[ifidx]["macs"].append(mac)

    # LLDP : index = timeMark.localPort.remIndex ; localPort -> nom via lldpLocPortId/Desc ou ifIndex
    loc_id = walk(ip, community, OID["lldpLocPortId"])
    loc_desc = walk(ip, community, OID["lldpLocPortDesc"])
    rem_name = walk(ip, community, OID["lldpRemSysName"])
    rem_port = walk(ip, community, OID["lldpRemPortId"])
    rem_pdesc = walk(ip, community, OID["lldpRemPortDesc"])
    rem_chassis = walk(ip, community, OID["lldpRemChassisId"])
    by_name = {p["name"]: k for k, p in ports.items()}
    for idx in set(rem_name) | set(rem_chassis):
        parts = idx.split(".")
        if len(parts) < 3:
            continue
        lport = parts[1]
        pname = loc_id.get(lport) or loc_desc.get(lport)
        key = by_name.get(pname) or (lport if lport in ports else None)
        if key is None:
            key = f"lldp{lport}"
            ports[key] = {"ifindex": key, "name": pname or f"port {lport}", "alias": "", "speed_mbps": 0,
                          "up": True, "macs": [], "neighbors": []}
        ports[key]["neighbors"].append({
            "proto": "LLDP", "name": rem_name.get(idx) or rem_chassis.get(idx),
            "chassis_mac": _hexmac(rem_chassis.get(idx, "")),
            "port": rem_pdesc.get(idx) or rem_port.get(idx), "ip": None, "platform": None})

    # CDP : index = ifIndex.deviceIndex
    cdp_id = walk(ip, community, OID["cdpDeviceId"])
    cdp_port = walk(ip, community, OID["cdpDevicePort"])
    cdp_addr = walk(ip, community, OID["cdpAddress"])
    cdp_plat = walk(ip, community, OID["cdpPlatform"])
    for idx, dev in cdp_id.items():
        ifidx = idx.split(".")[0]
        if ifidx not in ports:
            continue
        name = re.sub(r"\(.*\)$", "", dev).strip()
        if any(n["name"] == name for n in ports[ifidx]["neighbors"]):
            continue
        ports[ifidx]["neighbors"].append({"proto": "CDP", "name": name, "chassis_mac": None,
                                          "port": cdp_port.get(idx), "ip": _hexip(cdp_addr.get(idx, "")),
                                          "platform": cdp_plat.get(idx)})

    # ARP (routeurs / switchs L3 / firewalls) : IP -> MAC, utile pour les réseaux distants
    arp = {}
    for idx, mac in walk(ip, community, OID["arpPhys"]).items():
        parts = idx.split(".")
        if len(parts) >= 5:
            m = _hexmac(mac)
            if m:
                arp[".".join(parts[-4:])] = m

    return {"ip": ip, "name": name, "descr": descr.splitlines()[0][:160] if descr else "",
            "ports": list(ports.values()), "arp": arp}


def build_links(switches, mac_to_node, switch_ids):
    """À partir des équipements SNMP : liens switch-switch (LLDP/CDP) et équipement-port (table MAC).

    switches    : liste retournée par poll_device
    mac_to_node : {mac: node_id}
    switch_ids  : fonction (nom, ip) -> node_id d'un switch connu ou None
    Retour : [(switch_node_id, port_name, target_node_id, proto)]
    """
    links = []
    for sw in switches:
        sid = switch_ids(sw["name"], sw["ip"])
        for p in sw["ports"]:
            # voisins LLDP/CDP connus = liens inter-équipements (uplinks)
            for nb in p["neighbors"]:
                tid = switch_ids(nb.get("name"), nb.get("ip"))
                if tid is None and nb.get("chassis_mac"):
                    tid = mac_to_node.get(nb["chassis_mac"])
                if tid and tid != sid:
                    links.append((sid, p["name"], tid, nb["proto"]))
            p["uplink"] = bool(p["neighbors"]) or len(p["macs"]) > 6
    # MAC apprises sur des ports d'accès (pas les uplinks) = équipement branché directement
    best = {}
    for sw in switches:
        sid = switch_ids(sw["name"], sw["ip"])
        for p in sw["ports"]:
            if p.get("uplink"):
                continue
            for mac in p["macs"]:
                tid = mac_to_node.get(mac)
                if not tid or tid == sid:
                    continue
                score = len(p["macs"])
                if tid not in best or score < best[tid][0]:
                    best[tid] = (score, sid, p["name"])
    for tid, (_, sid, pname) in best.items():
        links.append((sid, pname, tid, "MAC"))
    return links
